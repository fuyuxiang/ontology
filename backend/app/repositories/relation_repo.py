from __future__ import annotations

from app.models import EntityRelation, OntologyEntity
from app.repositories.base import BaseRepository


class RelationRepository(BaseRepository[EntityRelation]):
    model = EntityRelation

    def list_by_entity(self, entity_id: str | None = None) -> list[EntityRelation]:
        q = self.db.query(EntityRelation)
        if entity_id:
            q = q.filter(
                (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)
            )
        return q.all()

    def get_entity_name(self, entity_id: str) -> str:
        e = self.db.get(OntologyEntity, entity_id)
        return e.name if e else ""
