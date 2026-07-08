from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologySharedRef(Base):
    __tablename__ = "ontology_shared_refs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    source_ontology_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    target_ontology_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("ontology_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    shared_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    shared_by: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        UniqueConstraint("target_ontology_id", "entity_id", name="uq_shared_ref_target_entity"),
    )

    source_ontology = relationship("ScenarioDict", foreign_keys=[source_ontology_id])
    target_ontology = relationship("ScenarioDict", foreign_keys=[target_ontology_id])
    entity = relationship("OntologyEntity", foreign_keys=[entity_id])
