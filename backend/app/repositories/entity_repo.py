from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import OntologyEntity, EntityAttribute, EntityRelation, BusinessRule, EntityAction
from app.repositories.base import BaseRepository


class EntityRepository(BaseRepository[OntologyEntity]):
    model = OntologyEntity

    def list_with_filters(
        self,
        tier: int | None = None,
        status: str | None = None,
        search: str | None = None,
        namespace: str | None = None,
    ) -> list[OntologyEntity]:
        q = self.db.query(OntologyEntity)
        if tier:
            q = q.filter(OntologyEntity.tier == tier)
        if status:
            q = q.filter(OntologyEntity.status == status)
        if namespace:
            q = q.filter(OntologyEntity.id.like(f"{namespace}_%"))
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                OntologyEntity.name.ilike(pattern) | OntologyEntity.name_cn.ilike(pattern)
            )
        return q.order_by(OntologyEntity.tier, OntologyEntity.name).all()

    def get_relation_count(self, entity_id: str) -> int:
        return self.db.query(func.count(EntityRelation.id)).filter(
            (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)
        ).scalar() or 0

    def get_all_relations(self) -> list[EntityRelation]:
        return self.db.query(EntityRelation).all()

    def get_scene_layer_counts(self, entity_ids: list[str]) -> dict:
        attr_count = self.db.query(func.count(EntityAttribute.id)).filter(
            EntityAttribute.entity_id.in_(entity_ids)
        ).scalar() or 0
        rel_count = self.db.query(func.count(EntityRelation.id)).filter(
            EntityRelation.from_entity_id.in_(entity_ids) | EntityRelation.to_entity_id.in_(entity_ids)
        ).scalar() or 0
        rule_count = self.db.query(func.count(BusinessRule.id)).filter(
            BusinessRule.entity_id.in_(entity_ids)
        ).scalar() or 0
        action_count = self.db.query(func.count(EntityAction.id)).filter(
            EntityAction.entity_id.in_(entity_ids)
        ).scalar() or 0
        return {
            "attrCount": attr_count,
            "relationCount": rel_count,
            "ruleCount": rule_count,
            "actionCount": action_count,
        }
