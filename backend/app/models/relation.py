from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils.identifiers import gen_uuid


class EntityRelation(Base):
    __tablename__ = "entity_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    from_entity_id: Mapped[str] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"))
    to_entity_id: Mapped[str] = mapped_column(ForeignKey("ontology_entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    cardinality: Mapped[str] = mapped_column(String(10), nullable=False)
    acyclic: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
