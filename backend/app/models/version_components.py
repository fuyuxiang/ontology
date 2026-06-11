from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyVersionFunction(Base):
    __tablename__ = "ontology_version_functions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_function_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    return_type: Mapped[str] = mapped_column(String(50), default="string")
    input_schema: Mapped[dict | None] = mapped_column(JSON)
    logic_type: Mapped[str] = mapped_column(String(30), default="expression")
    logic_body: Mapped[str] = mapped_column(Text, default="")
    callable_name: Mapped[str] = mapped_column(String(100), default="")
    tags: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    version: Mapped["OntologyVersion"] = relationship(back_populates="functions")


class OntologyVersionRule(Base):
    __tablename__ = "ontology_version_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    condition_expr: Mapped[str] = mapped_column(Text, default="")
    conditions_json: Mapped[dict | None] = mapped_column(JSON)
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    input_params: Mapped[dict | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    tags: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    version: Mapped["OntologyVersion"] = relationship(back_populates="rules")


class OntologyVersionAction(Base):
    __tablename__ = "ontology_version_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_id: Mapped[str] = mapped_column(ForeignKey("ontology_versions.id", ondelete="CASCADE"))
    source_action_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_entity_id: Mapped[str | None] = mapped_column(
        ForeignKey("ontology_version_entities.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="domain")
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    type_config: Mapped[dict | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)
    parameters_json: Mapped[dict | None] = mapped_column(JSON)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    version: Mapped["OntologyVersion"] = relationship(back_populates="actions")


# Avoid circular import — OntologyVersion is defined in version.py
from app.models.version import OntologyVersion  # noqa: E402
