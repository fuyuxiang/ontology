"""SkillVersion 模型 — 技能版本快照"""
from datetime import datetime
from sqlalchemy import String, Text, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.utils.identifiers import gen_uuid


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    change_log: Mapped[str] = mapped_column(Text, default="")
    published_by: Mapped[str] = mapped_column(String(100), default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
