from datetime import datetime, timedelta

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.monitor import Alert, LLMCallRecord, ServiceMetric


class MonitorRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Service Metrics ──

    def save_metric(self, service_name: str, status: str, response_ms: float | None = None,
                    cpu_percent: float | None = None, memory_percent: float | None = None,
                    disk_percent: float | None = None) -> ServiceMetric:
        m = ServiceMetric(
            service_name=service_name, status=status, response_ms=response_ms,
            cpu_percent=cpu_percent, memory_percent=memory_percent, disk_percent=disk_percent,
        )
        self.db.add(m)
        self.db.commit()
        return m

    def get_latest_metrics(self) -> list[ServiceMetric]:
        """Get the latest metric for each service."""
        subq = (
            self.db.query(
                ServiceMetric.service_name,
                func.max(ServiceMetric.id).label("max_id"),
            )
            .group_by(ServiceMetric.service_name)
            .subquery()
        )
        rows = (
            self.db.query(ServiceMetric)
            .join(subq, ServiceMetric.id == subq.c.max_id)
            .all()
        )
        return rows

    def get_metric_history(self, hours: int = 1, service_name: str | None = None) -> list[ServiceMetric]:
        """Get metric history for the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        q = self.db.query(ServiceMetric).filter(ServiceMetric.collected_at >= since)
        if service_name:
            q = q.filter(ServiceMetric.service_name == service_name)
        return q.order_by(ServiceMetric.collected_at.asc()).all()

    # ── LLM Calls ──

    def save_llm_call(self, caller_module: str, model_name: str | None = None,
                      prompt_tokens: int | None = None, completion_tokens: int | None = None,
                      latency_ms: float | None = None, success: bool = True) -> LLMCallRecord:
        r = LLMCallRecord(
            caller_module=caller_module, model_name=model_name,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=latency_ms, success=success,
        )
        self.db.add(r)
        self.db.commit()
        return r

    def get_llm_stats_24h(self) -> dict:
        """Get LLM call statistics for the last 24 hours."""
        since = datetime.utcnow() - timedelta(hours=24)
        rows = (
            self.db.query(
                LLMCallRecord.caller_module,
                func.count(LLMCallRecord.id).label("count"),
                func.sum(LLMCallRecord.prompt_tokens).label("total_prompt_tokens"),
                func.sum(LLMCallRecord.completion_tokens).label("total_completion_tokens"),
                func.avg(LLMCallRecord.latency_ms).label("avg_latency_ms"),
            )
            .filter(LLMCallRecord.created_at >= since)
            .group_by(LLMCallRecord.caller_module)
            .all()
        )
        total = sum(r.count for r in rows)
        by_module = {}
        for r in rows:
            by_module[r.caller_module] = {
                "count": r.count,
                "total_prompt_tokens": int(r.total_prompt_tokens or 0),
                "total_completion_tokens": int(r.total_completion_tokens or 0),
                "avg_latency_ms": round(float(r.avg_latency_ms or 0), 1),
            }
        return {"total_24h": total, "by_module": by_module}

    # ── Alerts ──

    def create_alert(self, level: str, service_name: str, message: str) -> Alert:
        a = Alert(level=level, service_name=service_name, message=message)
        self.db.add(a)
        self.db.commit()
        self.db.refresh(a)
        return a

    def get_alerts(self, limit: int = 20, resolved: bool | None = None,
                   level: str | None = None) -> list[Alert]:
        q = self.db.query(Alert)
        if resolved is not None:
            q = q.filter(Alert.resolved == resolved)
        if level:
            q = q.filter(Alert.level == level)
        return q.order_by(desc(Alert.created_at)).limit(limit).all()

    def resolve_alert(self, alert_id: int) -> Alert | None:
        a = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if a:
            a.resolved = True
            a.resolved_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(a)
        return a

    # ── Cleanup ──

    def cleanup_old_metrics(self, days: int = 7):
        cutoff = datetime.utcnow() - timedelta(days=days)
        self.db.query(ServiceMetric).filter(ServiceMetric.collected_at < cutoff).delete()
        self.db.commit()

    def cleanup_old_alerts(self, days: int = 30):
        cutoff = datetime.utcnow() - timedelta(days=days)
        self.db.query(Alert).filter(Alert.created_at < cutoff).delete()
        self.db.commit()
