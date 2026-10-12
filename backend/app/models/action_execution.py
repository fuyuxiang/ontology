"""Durable action dispatch ledger; retries never silently repeat side effects."""
from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.utils.identifiers import gen_uuid


class ActionExecution(Base):
    __tablename__ = "action_executions"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_action_execution_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    action_id: Mapped[str] = mapped_column(String(36), index=True)
    ontology_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON)
    message: Mapped[str] = mapped_column(Text, default="")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


def recover_interrupted_actions(db):
    """A new single-server lifecycle cannot infer a lost dispatch outcome.

    Preserve the idempotency key and require receipt reconciliation instead of
    automatically replaying business writes after a crash/restart.
    """
    rows = db.query(ActionExecution).filter_by(state="executing").all()
    for row in rows:
        row.state = "unknown"
        row.message = "服务启动时发现中断执行；请核对业务实例或外部回执，原幂等键不会重新发送"
        row.output = {**(row.output or {}), "outcome": "unknown"}
        row.finished_at = datetime.utcnow()
    db.commit()
    return len(rows)
