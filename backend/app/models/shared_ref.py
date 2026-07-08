from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def _gen_uuid() -> str:
    return uuid.uuid4().hex


class OntologySharedRef(Base):
    __tablename__ = "ontology_shared_refs"

    id = Column(String(36), primary_key=True, default=_gen_uuid)
    source_ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    target_ontology_id = Column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    entity_id = Column(String(36), ForeignKey("ontology_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    shared_by = Column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("target_ontology_id", "entity_id", name="uq_shared_ref_target_entity"),
    )

    source_ontology = relationship("ScenarioDict", foreign_keys=[source_ontology_id])
    target_ontology = relationship("ScenarioDict", foreign_keys=[target_ontology_id])
    entity = relationship("OntologyEntity", foreign_keys=[entity_id])
