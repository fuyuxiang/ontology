from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyEntity(Base):
    __tablename__ = "ontology_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_cn: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    description: Mapped[str | None] = mapped_column(Text)
    schema_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))

    attributes: Mapped[list["EntityAttribute"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    rules: Mapped[list["BusinessRule"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    actions: Mapped[list["EntityAction"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


class EntityAttribute(Base):
    __tablename__ = "entity_attributes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    example: Mapped[str | None] = mapped_column(String(200))
    constraints_json: Mapped[dict | None] = mapped_column(JSON)

    entity: Mapped["OntologyEntity"] = relationship(back_populates="attributes")
