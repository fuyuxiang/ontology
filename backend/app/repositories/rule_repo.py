from __future__ import annotations

from app.models import BusinessRule, OntologyEntity
from app.repositories.base import BaseRepository


class RuleRepository(BaseRepository[BusinessRule]):
    model = BusinessRule

    def list_with_filters(
        self,
        entity_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
    ) -> list[BusinessRule]:
        q = self.db.query(BusinessRule)
        if entity_id:
            q = q.filter(BusinessRule.entity_id == entity_id)
        if status:
            q = q.filter(BusinessRule.status == status)
        if priority:
            q = q.filter(BusinessRule.priority == priority)
        if search:
            pattern = f"%{search}%"
            q = q.filter(BusinessRule.name.ilike(pattern) | BusinessRule.condition_expr.ilike(pattern))
        return q.order_by(BusinessRule.priority.desc(), BusinessRule.name).all()

    def get_entity_name(self, entity_id: str) -> str:
        entity = self.db.get(OntologyEntity, entity_id)
        return entity.name if entity else ""
