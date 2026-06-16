from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class SystemConfig(Base):
    """系统配置项 — key-value 存储，按 group 分组"""
    __tablename__ = "system_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    group: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # basic / auth / storage / ai / notification
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by: Mapped[str | None] = mapped_column(String(100))
