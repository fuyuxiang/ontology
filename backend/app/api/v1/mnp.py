"""携号转网数据查询 API — 全部通过 ExecuteService.execute_alias 走唯一闸口。

业务侧不再 import datasource_utils；不再拼 SQL；所有查询通过预先注册的
sql_view alias（mnp.*）执行，由 /execute 闸口统一参数化、限流、缓存、审计。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.data_plane.execute_service import (
    ExecuteBlocked, ExecuteService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mnp", tags=["mnp"])


def _exec(db: Session) -> ExecuteService:
    return ExecuteService(db)


def _scalar(svc: ExecuteService, alias: str, params: dict, *, purpose: str = "mnp.dashboard"):
    try:
        r = svc.execute_alias(alias, params, purpose=purpose)
    except ExecuteBlocked:
        raise
    except LookupError as e:
        raise HTTPException(503, f"业务资产未就绪：{e}")
    return r.rows[0][0] if r.rows else 0


def _rows_as_dicts(svc: ExecuteService, alias: str, params: dict, *, purpose: str):
    try:
        r = svc.execute_alias(alias, params, purpose=purpose)
    except LookupError as e:
        raise HTTPException(503, f"业务资产未就绪：{e}")
    cols = r.columns
    return [{cols[i]: row[i] for i in range(len(cols))} for row in r.rows]


def _first_dict(svc: ExecuteService, alias: str, params: dict, *, purpose: str):
    rows = _rows_as_dicts(svc, alias, params, purpose=purpose)
    return rows[0] if rows else {}


@router.get("/stats")
def get_mnp_stats(db: Session = Depends(get_db)):
    """携转预警统计概览"""
    svc = _exec(db)
    total_users = _scalar(svc, "mnp.user_count", {})
    query_users = _scalar(svc, "mnp.query_user_count", {})
    maintain_total = _scalar(svc, "mnp.maintain_total", {})
    maintain_success = _scalar(svc, "mnp.maintain_success", {})
    complaint_total = _scalar(svc, "mnp.complaint_total", {})
    owe_users = _scalar(svc, "mnp.owe_users", {})
    return {
        "total_users": total_users,
        "query_users": query_users,
        "maintain_total": maintain_total,
        "maintain_success": maintain_success,
        "maintain_rate": round(maintain_success / maintain_total * 100, 1) if maintain_total else 0,
        "complaint_total": complaint_total,
        "owe_users": owe_users,
    }


@router.get("/risk-users")
def get_risk_users(db: Session = Depends(get_db)):
    """风险用户列表 — 关联用户信息+携转查询+费用+维挽。

    走 sql_view alias `mnp.risk_users`（同 connection 内的 JOIN 视图，已在 seed
    阶段登记并由 sql_introspect 提取依赖加入白名单）。
    """
    svc = _exec(db)
    try:
        r = svc.execute_alias("mnp.risk_users", {}, purpose="mnp.risk_users")
    except LookupError as e:
        raise HTTPException(503, f"业务资产未就绪：{e}")
    cols = r.columns
    return {
        "columns": cols,
        "rows": r.rows,
        "items": [{cols[i]: row[i] for i in range(len(cols))} for row in r.rows],
        "rowCount": r.rows_returned,
    }


@router.get("/risk-users/{user_id}")
def get_risk_user_detail(user_id: str, db: Session = Depends(get_db)):
    """单个用户的完整画像（参数化绑定，杜绝注入）。"""
    svc = _exec(db)
    user_info = _first_dict(svc, "mnp.user_profile", {"uid": user_id}, purpose="mnp.profile")
    charge = _first_dict(svc, "mnp.user_charge", {"uid": user_id}, purpose="mnp.profile")
    contracts = _rows_as_dicts(svc, "mnp.user_contracts", {"uid": user_id}, purpose="mnp.profile")
    queries = _rows_as_dicts(svc, "mnp.user_queries", {"uid": user_id}, purpose="mnp.profile")
    device = str(user_info.get("device_number", ""))
    maintains = (
        _rows_as_dicts(svc, "mnp.user_maintains_by_device", {"device": device}, purpose="mnp.profile")
        if device else []
    )
    complaints = (
        _rows_as_dicts(svc, "mnp.user_complaints_by_device", {"device": device}, purpose="mnp.profile")
        if device else []
    )
    voice = _first_dict(svc, "mnp.user_voice_stats", {"uid": user_id}, purpose="mnp.profile")
    owe = _first_dict(svc, "mnp.user_owe_by_subs", {"uid": user_id}, purpose="mnp.profile")
    return {
        "user_info": user_info,
        "charge": charge,
        "contracts": contracts,
        "queries": queries,
        "maintains": maintains,
        "complaints": complaints,
        "voice_stats": voice,
        "owe": owe,
    }


@router.get("/maintain-stats")
def get_maintain_stats(db: Session = Depends(get_db)):
    """维挽统计 — 按转网原因和维挽结果分组"""
    svc = _exec(db)
    by_reason = _rows_as_dicts(svc, "mnp.maintain_by_reason", {}, purpose="mnp.maintain_stats")
    by_product = _rows_as_dicts(svc, "mnp.maintain_by_product", {}, purpose="mnp.maintain_stats")
    return {"by_reason": by_reason, "by_product": by_product}
