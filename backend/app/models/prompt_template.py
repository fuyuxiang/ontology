"""Prompt 模板模型"""
from datetime import datetime
from sqlalchemy import String, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.utils.identifiers import gen_uuid


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="通用")  # 通用/稽核/预警/根因/续约
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list | None] = mapped_column(JSON)  # [{name, description, default}]
    tags: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
