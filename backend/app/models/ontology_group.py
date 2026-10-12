from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class OntologyGroup(Base):
    __tablename__ = "ontology_groups"
    __table_args__ = (UniqueConstraint("ontology_id", "name", name="uq_ontology_group_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ontology_id: Mapped[str] = mapped_column(ForeignKey("scenario_dict.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
