from __future__ import annotations

from app.models import OntologyEntity
from app.models.function import OntologyFunction
from app.models.shared_ref import OntologySharedRef
from app.repositories.base import BaseRepository


class FunctionRepository(BaseRepository[OntologyFunction]):
    model = OntologyFunction

    def list_with_filters(
        self,
        entity_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        ontology_id: str | None = None,
    ) -> list[OntologyFunction]:
        q = self.db.query(OntologyFunction)
        if ontology_id:
            # 直接归属 + 通过 entity 归属
            entity_ids_in_scope = self.db.query(OntologyEntity.id).filter(
                OntologyEntity.ontology_id == ontology_id
            )
            shared_entity_ids = self.db.query(OntologySharedRef.entity_id).filter(
                OntologySharedRef.target_ontology_id == ontology_id
            )
            all_entity_ids = entity_ids_in_scope.union(shared_entity_ids)
            q = q.filter(
                (OntologyFunction.ontology_id == ontology_id) |
                (OntologyFunction.entity_id.in_(all_entity_ids))
            )
        if entity_id:
            q = q.filter(OntologyFunction.entity_id == entity_id)
        if status:
            q = q.filter(OntologyFunction.status == status)
        if search:
            pattern = f"%{search}%"
            q = q.filter(OntologyFunction.name.ilike(pattern) | OntologyFunction.description.ilike(pattern))
        return q.order_by(OntologyFunction.created_at.desc()).all()

    def get_entity_name(self, entity_id: str | None) -> str:
        if not entity_id:
            return ""
        entity = self.db.get(OntologyEntity, entity_id)
        return entity.name if entity else ""
