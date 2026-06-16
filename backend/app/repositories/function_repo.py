from __future__ import annotations

from app.models.function import OntologyFunction
from app.models import OntologyEntity
from app.repositories.base import BaseRepository


class FunctionRepository(BaseRepository[OntologyFunction]):
    model = OntologyFunction

    def list_with_filters(
        self,
        entity_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[OntologyFunction]:
        q = self.db.query(OntologyFunction)
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
