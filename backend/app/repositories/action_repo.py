from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.repositories.base import BaseRepository


class ActionRepository(BaseRepository[EntityAction]):
    model = EntityAction

    def __init__(self, db: Session):
        super().__init__(db)

    def list_with_filters(self, entity_id=None, status=None, action_type=None, category=None, search=None):
        query = select(EntityAction)
        if entity_id:
            query = query.where(EntityAction.entity_id == entity_id)
        if status:
            query = query.where(EntityAction.status == status)
        if action_type:
            query = query.where(EntityAction.action_type == action_type)
        if category:
            query = query.where(EntityAction.category == category)
        if search:
            query = query.where(EntityAction.name.ilike(f"%{search}%"))
        query = query.order_by(EntityAction.created_at.desc())
        return self.db.execute(query).scalars().all()

    def get_entity_name(self, entity_id: str) -> str | None:
        from app.models.entity import OntologyEntity
        entity = self.db.get(OntologyEntity, entity_id)
        return entity.name if entity else None
