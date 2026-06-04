from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class BusinessRule(Base):
    __tablename__ = "business_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    condition_expr: Mapped[str] = mapped_column(Text, nullable=False)
    action_desc: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime)
    conditions_json: Mapped[list | None] = mapped_column(JSON)
    rule_meta_json: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list | None] = mapped_column(JSON)
    input_params: Mapped[list | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    action_id: Mapped[str | None] = mapped_column(ForeignKey("entity_actions.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity: Mapped["app.models.entity.OntologyEntity"] = relationship(back_populates="rules")  # type: ignore[name-defined]


class EntityAction(Base):
    __tablename__ = "entity_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"), nullable=True)
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
