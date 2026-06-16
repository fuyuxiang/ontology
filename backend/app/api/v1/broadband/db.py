"""
宽带装机退单稽核 — DB 访问层
数据源：通过 Data Plane Connection（默认名 bb_audit_db）走 ExecuteService 执行；
DB 配置 / 凭据 / 限流 / 缓存 / 审计 / 列级脱敏全部由数据集成模块统一管理。
"""
import hashlib
import re
import uuid
from datetime import date as _date
from datetime import datetime as _dt
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories.connection_repo import ConnectionRepository
from app.services.data_plane.execute_service import (
    ExecuteBlocked,
    ExecuteService,
)

# 业务连接由 seed_business_assets 自动注册。
_BB_CONN_NAME = "bb_audit_db"
_BB_CONN_ID_CACHE: str | None = None


# ── 工具：%s 参数 → :p0/:p1/... + dict ───────────────────────────

_PYFORMAT = re.compile(r"%s")


def _to_named(sql: str, args) -> tuple[str, dict]:
    if args is None:
        return sql, {}
    if isinstance(args, dict):
        return sql, dict(args)
    if not isinstance(args, (list, tuple)):
        args = (args,)
    placeholders = []
    out = []
    last = 0
    idx = 0
    for m in _PYFORMAT.finditer(sql):
        out.append(sql[last:m.start()])
        out.append(f":p{idx}")
        placeholders.append(f"p{idx}")
        idx += 1
        last = m.end()
    out.append(sql[last:])
    if idx != len(args):
        raise ValueError(f"参数数量不匹配: 占位符 {idx}, 实参 {len(args)}")
    return "".join(out), {f"p{i}": args[i] for i in range(idx)}


def _ser_value(v: Any) -> Any:
    if isinstance(v, _dt):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, _date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _ser(row: dict) -> dict:
    return {k: _ser_value(v) for k, v in row.items()}


# ── 通过 Data Plane 走的等价 helper ───────────────────────────────

def _resolve_connection_id(db: Session) -> str:
    # 业务连接(bb_audit_db)注册后 id 稳定不变,缓存成功结果避免每次请求重复查库。
    # 仅缓存成功值；未就绪时不缓存,以便连接注册后能正常解析。
    global _BB_CONN_ID_CACHE
    if _BB_CONN_ID_CACHE is not None:
        return _BB_CONN_ID_CACHE
    repo = ConnectionRepository(db)
    conn = repo.find_by_name(_BB_CONN_NAME)
    if not conn:
        raise HTTPException(503, f"业务连接未就绪：{_BB_CONN_NAME}")
    _BB_CONN_ID_CACHE = conn.id
    return _BB_CONN_ID_CACHE


def _query(sql: str, args=None, *, write: bool = False, purpose: str = "scene.bb") -> list[dict]:
    """走 ExecuteService.execute_on_connection；返回 list[dict] 保持原 API 语义。"""
    db = SessionLocal()
    try:
        conn_id = _resolve_connection_id(db)
        named_sql, params = _to_named(sql, args)
        try:
            r = ExecuteService(db).execute_on_connection(
                connection_id=conn_id,
                sql=named_sql, params=params,
                purpose=purpose, write=write,
            )
        except ExecuteBlocked as e:
            raise HTTPException(400, f"SQL 被拒绝：{e.reason} {e.detail}") from e
        cols = r.columns
        return [{cols[i]: row[i] for i in range(len(cols))} for row in r.rows]
    finally:
        db.close()

def _query_one(sql: str, args=None) -> dict | None:
    rows = _query(sql, args)
    return rows[0] if rows else None


def _scalar(sql: str, args=None):
    r = _query_one(sql, args)
    if not r:
        return 0
    return list(r.values())[0]


def _execute(sql: str, args=None) -> int:
    """写入：返回 rowcount。"""
    db = SessionLocal()
    try:
        conn_id = _resolve_connection_id(db)
        named_sql, params = _to_named(sql, args)
        try:
            r = ExecuteService(db).execute_on_connection(
                connection_id=conn_id,
                sql=named_sql, params=params,
                purpose="scene.bb.write", write=True,
            )
        except ExecuteBlocked as e:
            raise HTTPException(400, f"写入被拒绝：{e.reason} {e.detail}") from e
        return r.rows_returned
    finally:
        db.close()


# ── 写入辅助 ────────────────────────────────────────────

def _insert_trail(churn_id: str, event_type: str, event_detail: str, operator: str = "system"):
    tid = f"TRL{hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]}"
    _execute(
        "INSERT INTO bb_audit_trail (trail_id, churn_id, event_type, event_detail, operator) "
        "VALUES (%s, %s, %s, %s, %s)",
        (tid, churn_id, event_type, event_detail, operator)
    )

