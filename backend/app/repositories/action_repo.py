from __future__ import annotations

from app.models.rule import EntityAction
from app.models import OntologyEntity
from app.repositories.base import BaseRepository


class ActionRepository(BaseRepository[EntityAction]):
    model = EntityAction

    def list_with_filters(
        self,
        entity_id: str | None = None,
        status: str | None = None,
        type: str | None = None,
        search: str | None = None,
    ) -> list[EntityAction]:
        q = self.db.query(EntityAction)
        if entity_id:
            q = q.filter(EntityAction.entity_id == entity_id)
        if status:
            q = q.filter(EntityAction.status == status)
        if type:
            q = q.filter(EntityAction.type == type)
        if search:
            pattern = f"%{search}%"
            q = q.filter(EntityAction.name.ilike(pattern))
        return q.order_by(EntityAction.created_at.desc()).all()

    def get_entity_name(self, entity_id: str) -> str:
        entity = self.db.get(OntologyEntity, entity_id)
        return entity.name if entity else ""
