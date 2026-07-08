from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class EntityAction(Base):
    __tablename__ = "entity_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"), nullable=True)
    ontology_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="domain")
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    type_config: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    impact_count: Mapped[int | None] = mapped_column(Integer)
    parameters_json: Mapped[list | None] = mapped_column(JSON)
    output_schema: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, onupdate=datetime.utcnow)

    entity: Mapped["app.models.entity.OntologyEntity"] = relationship(back_populates="actions")  # type: ignore[name-defined]
