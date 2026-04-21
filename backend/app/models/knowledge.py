import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    kb_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), default="other")  # pdf|word|excel|image|video|other
    file_path: Mapped[str | None] = mapped_column(String(500))
    size: Mapped[int] = mapped_column(Integer, default=0)
    parsed_content: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ready")  # ready|parsing|error
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
