from datetime import datetime

from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.entity import gen_uuid


class AuditLog(Base):
    """Append-only 审计日志（借鉴 clawhub JSONL 模式）"""
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36))
    user_name: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_name: Mapped[str] = mapped_column(String(200), default="")
    changes_json: Mapped[list | None] = mapped_column(JSON)
    snapshot_before: Mapped[dict | None] = mapped_column(JSON)
    snapshot_after: Mapped[dict | None] = mapped_column(JSON)
