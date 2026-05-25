"""ExecutionLog 仓库 — /execute 审计日志。"""
from __future__ import annotations

from datetime import datetime

from app.models.execution_log import ExecutionLog
from app.repositories.base import BaseRepository


class ExecutionLogRepository(BaseRepository[ExecutionLog]):
    model = ExecutionLog

    def list(
        self,
        *,
        asset_id: str | None = None,
        purpose: str | None = None,
        blocked: bool | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionLog]:
        q = self.db.query(ExecutionLog)
        if asset_id:
            q = q.filter(ExecutionLog.asset_id == asset_id)
        if purpose:
            q = q.filter(ExecutionLog.purpose == purpose)
        if blocked is not None:
            q = q.filter(ExecutionLog.blocked == blocked)
        if since:
            q = q.filter(ExecutionLog.started_at >= since)
        if until:
            q = q.filter(ExecutionLog.started_at < until)
        return q.order_by(ExecutionLog.started_at.desc()).offset(offset).limit(limit).all()

    def stats_24h(self) -> dict:
        from sqlalchemy import func
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(hours=24)
        rows = self.db.query(
            func.count(ExecutionLog.id),
            func.sum(ExecutionLog.cache_hit.cast(__import__("sqlalchemy").Integer)),
            func.sum(ExecutionLog.blocked.cast(__import__("sqlalchemy").Integer)),
            func.avg(ExecutionLog.duration_ms),
        ).filter(ExecutionLog.started_at >= since).one()
        total, cache_hits, blocked, avg_dur = rows
        total = total or 0
        return {
            "total": total,
            "cache_hit_rate": (cache_hits or 0) / total if total else 0,
            "blocked_rate": (blocked or 0) / total if total else 0,
            "avg_duration_ms": float(avg_dur or 0),
        }
