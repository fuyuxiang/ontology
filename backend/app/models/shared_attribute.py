from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint

from app.database import Base


def _gen_uuid() -> str:
    return uuid.uuid4().hex


class SharedAttribute(Base):
    __tablename__ = "ontology_shared_attributes"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_cn = Column(String(100), nullable=True)
    data_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("ontology_id", "name", name="uq_shared_attr_ontology_name"),
    )
