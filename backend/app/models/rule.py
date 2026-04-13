from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.entity import gen_uuid


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity: Mapped["app.models.entity.OntologyEntity"] = relationship(back_populates="rules")  # type: ignore[name-defined]


class EntityAction(Base):
    __tablename__ = "entity_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    impact_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped["app.models.entity.OntologyEntity"] = relationship(back_populates="actions")  # type: ignore[name-defined]
