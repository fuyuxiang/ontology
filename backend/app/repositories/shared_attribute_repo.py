from __future__ import annotations

from app.models.shared_attribute import SharedAttribute
from app.repositories.base import BaseRepository


class SharedAttributeRepository(BaseRepository[SharedAttribute]):
    model = SharedAttribute

    def list_by_ontology(self, ontology_id: str) -> list[SharedAttribute]:
        return self.db.query(SharedAttribute).filter(
            SharedAttribute.ontology_id == ontology_id
        ).order_by(SharedAttribute.name).all()

    def find_by_name(self, ontology_id: str, name: str) -> SharedAttribute | None:
        return self.db.query(SharedAttribute).filter(
            SharedAttribute.ontology_id == ontology_id,
            SharedAttribute.name == name,
        ).first()
