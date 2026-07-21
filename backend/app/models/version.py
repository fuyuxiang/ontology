from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid

if TYPE_CHECKING:
    # 仅供类型检查/静态分析识别字符串 relationship 的目标类;
    # 运行时由 SQLAlchemy registry 解析前向引用,不在此处 import(避免与 version_components 循环导入)。
    from app.models.version_components import (
        OntologyVersionAction,
        OntologyVersionFunction,
    )


class OntologyVersion(Base):
    __tablename__ = "ontology_versions"
    __table_args__ = (
        UniqueConstraint("ontology_id", "version_number", name="uq_version_ontology_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ontology_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("scenario_dict.id"), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[str | None] = mapped_column(String(36))
    approved_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    rollback_from: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    entities: Mapped[list["OntologyVersionEntity"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    relations: Mapped[list["OntologyVersionRelation"]] = relationship(
        back_populates="version", cascade="all, delete-orphan",
        foreign_keys="OntologyVersionRelation.version_id"
    )
    functions: Mapped[list["OntologyVersionFunction"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )
    actions: Mapped[list["OntologyVersionAction"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class OntologyVersionEntity(Base):
    __tablename__ = "ontology_version_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_cn: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    publish_config: Mapped[dict | None] = mapped_column(JSON)
    scenario_codes: Mapped[list | None] = mapped_column(JSON)

    version: Mapped["OntologyVersion"] = relationship(back_populates="entities")
    attributes: Mapped[list["OntologyVersionAttribute"]] = relationship(
        back_populates="version_entity", cascade="all, delete-orphan"
    )


class OntologyVersionAttribute(Base):
    __tablename__ = "ontology_version_attributes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    source_attribute_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    example: Mapped[str | None] = mapped_column(String(200))
    constraints_json: Mapped[dict | None] = mapped_column(JSON)
    source_table: Mapped[str | None] = mapped_column(String(200))
    source_field: Mapped[str | None] = mapped_column(String(200))
    data_status: Mapped[str] = mapped_column(String(20), default="未确认来源")

    version_entity: Mapped["OntologyVersionEntity"] = relationship(back_populates="attributes")


class OntologyVersionRelation(Base):
    __tablename__ = "ontology_version_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_relation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    from_version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    to_version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(10), nullable=False)
    acyclic: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)

    version: Mapped["OntologyVersion"] = relationship(
        back_populates="relations", foreign_keys=[version_id]
    )
    from_entity: Mapped["OntologyVersionEntity"] = relationship(
        foreign_keys=[from_version_entity_id]
    )
    to_entity: Mapped["OntologyVersionEntity"] = relationship(
        foreign_keys=[to_version_entity_id]
    )
