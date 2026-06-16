"""SkillTool 模型 — 技能中的可执行工具（Python代码）"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class SkillTool(Base):
    __tablename__ = "skill_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code: Mapped[str] = mapped_column(Text, default="")
    code_type: Mapped[str] = mapped_column(String(20), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
