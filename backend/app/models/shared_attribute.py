from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class SharedAttribute(Base):
    __tablename__ = "ontology_shared_attributes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ontology_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_cn: Mapped[str | None] = mapped_column(String(100))
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ontology_id", "name", name="uq_shared_attr_ontology_name"),
    )
