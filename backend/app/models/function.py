from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyFunction(Base):
    __tablename__ = "ontology_functions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str | None] = mapped_column(ForeignKey("ontology_entities.id", ondelete="SET NULL"), nullable=True)
    entity_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    return_type: Mapped[str] = mapped_column(String(50), default="string")
    input_schema: Mapped[list | None] = mapped_column(JSON)
    logic_type: Mapped[str] = mapped_column(String(30), default="expression")
    logic_body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    tags: Mapped[list | None] = mapped_column(JSON)
    callable_name: Mapped[str] = mapped_column(String(100), default="")
    is_derived_property: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_executed: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity: Mapped["app.models.entity.OntologyEntity"] = relationship(back_populates="functions")  # type: ignore[name-defined]
