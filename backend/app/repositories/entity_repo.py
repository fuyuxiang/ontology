from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app.models import EntityRelation, OntologyEntity
from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.models.shared_ref import OntologySharedRef
from app.repositories.base import BaseRepository


class EntityRepository(BaseRepository[OntologyEntity]):
    model = OntologyEntity

    def list_with_filters(
        self,
        tier: int | None = None,
        status: str | None = None,
        search: str | None = None,
        namespace: str | None = None,
        ontology_id: str | None = None,
    ) -> list[OntologyEntity]:
        q = self.db.query(OntologyEntity).options(
            selectinload(OntologyEntity.attributes),
            selectinload(OntologyEntity.functions),
            selectinload(OntologyEntity.actions),
        )
        if ontology_id:
            # 自有实体
            owned_ids = self.db.query(OntologyEntity.id).filter(
                OntologyEntity.ontology_id == ontology_id
            )
            # 共享进来的实体
            shared_ids = self.db.query(OntologySharedRef.entity_id).filter(
                OntologySharedRef.target_ontology_id == ontology_id
            )
            q = q.filter(OntologyEntity.id.in_(owned_ids.union(shared_ids)))
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

    def get_shared_entity_ids(self, ontology_id: str) -> set[str]:
        """返回被共享进当前本体的实体 ID 集合。"""
        rows = self.db.query(OntologySharedRef.entity_id).filter(
            OntologySharedRef.target_ontology_id == ontology_id
        ).all()
        return {r[0] for r in rows}

    def get_relation_count(self, entity_id: str) -> int:
        return self.db.query(func.count(EntityRelation.id)).filter(
            (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)
        ).scalar() or 0

    def get_relation_counts(self, entity_ids: list[str]) -> dict[str, int]:
        if not entity_ids:
            return {}
        id_set = set(entity_ids)
        rows = self.db.query(
            EntityRelation.from_entity_id, EntityRelation.to_entity_id
        ).filter(
            EntityRelation.from_entity_id.in_(id_set)
            | EntityRelation.to_entity_id.in_(id_set)
        ).all()
        counts: dict[str, int] = {}
        for fid, tid in rows:
            endpoints = {fid} if fid == tid else {fid, tid}
            for eid in endpoints:
                if eid in id_set:
                    counts[eid] = counts.get(eid, 0) + 1
        return counts

    def get_all_relations(self) -> list[EntityRelation]:
        return self.db.query(EntityRelation).all()

    def get_ontology_stats(self) -> dict[str, dict[str, int]]:
        """按本体聚合对象/关系/逻辑/动作数量，返回 {ontology_id: {...}}。

        归属规则与 FunctionRepository / ActionRepository.list_with_filters 保持一致：
        自有实体（entity.ontology_id）+ 被共享进来的实体（ontology_shared_refs），
        逻辑与动作按「自身 ontology_id ∪ 所属实体的本体范围」计入。
        """
        # 实体 -> 本体归属映射（自有 + 共享，一个实体可属于多个本体）
        entity_scope: dict[str, set[str]] = {}
        owned = self.db.query(OntologyEntity.id, OntologyEntity.ontology_id).filter(
            OntologyEntity.ontology_id.isnot(None)
        ).all()
        for eid, oid in owned:
            entity_scope.setdefault(eid, set()).add(oid)

        shared = self.db.query(
            OntologySharedRef.entity_id, OntologySharedRef.target_ontology_id
        ).all()
        for eid, oid in shared:
            entity_scope.setdefault(eid, set()).add(oid)

        stats: dict[str, dict[str, int]] = {}

        def bucket(oid: str) -> dict[str, int]:
            return stats.setdefault(
                oid,
                {"entity_count": 0, "relation_count": 0, "logic_count": 0, "action_count": 0},
            )

        for oids in entity_scope.values():
            for oid in oids:
                bucket(oid)["entity_count"] += 1

        # 关系：两端实体同属一个本体才计入该本体，避免跨本体关系被双边重复统计
        relations = self.db.query(
            EntityRelation.from_entity_id, EntityRelation.to_entity_id
        ).all()
        for fid, tid in relations:
            for oid in entity_scope.get(fid, set()) & entity_scope.get(tid, set()):
                bucket(oid)["relation_count"] += 1

        self._accumulate_owned(
            bucket, entity_scope,
            self.db.query(OntologyFunction.entity_id, OntologyFunction.ontology_id).all(),
            "logic_count",
        )
        self._accumulate_owned(
            bucket, entity_scope,
            self.db.query(EntityAction.entity_id, EntityAction.ontology_id).all(),
            "action_count",
        )
        return stats

    @staticmethod
    def _accumulate_owned(bucket, entity_scope, rows, key: str) -> None:
        """把逻辑/动作记录累加到所属本体。

        与 list_with_filters 的 OR 条件同义：记录归属 = 自身 ontology_id ∪ 所属实体的本体范围。
        """
        for entity_id, own_ontology_id in rows:
            targets: set[str] = set()
            if entity_id:
                targets |= entity_scope.get(entity_id, set())
            if own_ontology_id:
                targets.add(own_ontology_id)
            for oid in targets:
                bucket(oid)[key] += 1

