"""Skill 模型 — 可复用的业务技能"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    skill_type: Mapped[str] = mapped_column(String(20), default="builtin")
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code_ref: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    input_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    test_cases: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    asset_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    reviewed_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
