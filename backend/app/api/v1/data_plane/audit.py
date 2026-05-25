"""/audit — 执行日志审计 API（数据集成模块"执行审计"页背后的接口）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.execution_log_repo import ExecutionLogRepository
from app.schemas.data_plane import ExecutionLogOut, ExecutionStatsOut

router = APIRouter(prefix="/audit", tags=["data-plane:audit"])


@router.get("/executions", response_model=list[ExecutionLogOut])
def list_executions(
    asset_id: str | None = None,
    purpose: str | None = None,
    blocked: bool | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return ExecutionLogRepository(db).list(
        asset_id=asset_id, purpose=purpose, blocked=blocked,
        since=since, until=until, limit=limit, offset=offset,
    )


@router.get("/executions/{log_id}", response_model=ExecutionLogOut)
def get_execution(log_id: str, db: Session = Depends(get_db)):
    log = ExecutionLogRepository(db).get_by_id(log_id)
    if not log:
        raise HTTPException(404, "执行记录不存在")
    return log


@router.get("/stats", response_model=ExecutionStatsOut)
def get_stats(db: Session = Depends(get_db)):
    return ExecutionLogRepository(db).stats_24h()
