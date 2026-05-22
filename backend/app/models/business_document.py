"""业务文档库 — /logic/documents 页面背后的存储模型。"""
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class BusinessDocument(Base):
    __tablename__ = "business_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), default="")
    file_path: Mapped[str | None] = mapped_column(String(500))
    parsed_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    domain_tags: Mapped[list | None] = mapped_column(JSON, default=list)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str | None] = mapped_column(String(36))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
