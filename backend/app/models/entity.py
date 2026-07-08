from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyEntity(Base):
    __tablename__ = "ontology_entities"
    __table_args__ = (
        UniqueConstraint("ontology_id", "name", name="uq_entity_ontology_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_cn: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    description: Mapped[str | None] = mapped_column(Text)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    scenario_codes: Mapped[list | None] = mapped_column(JSON)
    ontology_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str | None] = mapped_column(String(36))
    publish_config: Mapped[dict | None] = mapped_column(JSON)

    attributes: Mapped[list["EntityAttribute"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    actions: Mapped[list["EntityAction"]] = relationship(back_populates="entity", cascade="all, delete-orphan")
    functions: Mapped[list["OntologyFunction"]] = relationship(back_populates="entity", cascade="all, delete-orphan")


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
    source_table: Mapped[str | None] = mapped_column(String(200))
    source_field: Mapped[str | None] = mapped_column(String(200))
    data_status: Mapped[str] = mapped_column(String(20), default="未确认来源")
    shared_attribute_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ontology_shared_attributes.id", ondelete="SET NULL"), nullable=True)

    entity: Mapped["OntologyEntity"] = relationship(back_populates="attributes")
