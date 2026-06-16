"""SkillToolRef 模型 — 技能对已发布本体组件（Function/Rule/Action）的引用"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class SkillToolRef(Base):
    __tablename__ = "skill_tool_refs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ontology_versions.id"), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(20), nullable=False)
    ref_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    param_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
