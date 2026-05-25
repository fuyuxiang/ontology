"""LineageService — 本体侧血缘。

血缘范围：Asset → ObjectType → Action（不画上游 Connection→Asset，不画上游 ETL）。
事件订阅：
- binding.created/updated → upsert (asset → object_type, binds_to)
- binding.deleted → 标 weight=0
- execution.completed → 按 purpose 白名单写 ad-hoc 边
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.repositories.lineage_edge_repo import LineageEdgeRepository

logger = logging.getLogger(__name__)


# 仅这些 purpose 前缀会让 execution.completed 写血缘 ad-hoc 边。
# 避免 probe.* 等"治理动作"也产生大量节点。
LINEAGE_PURPOSE_PREFIXES = ("mnp.", "scene.", "scenes.", "action.write", "ontology.", "copilot.")


class LineageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = LineageEdgeRepository(db)

    # ── 写边 ───────────────────────────────────────────
    def upsert_binding(self, asset_id: str, object_type_id: str, *, via_module: str = "binding") -> None:
        self.repo.upsert(
            source_kind="asset", source_id=asset_id,
            target_kind="object_type", target_id=object_type_id,
            relation="binds_to", via_module=via_module,
        )
        self.db.commit()

    def deprecate_binding(self, asset_id: str, object_type_id: str) -> None:
        self.repo.deprecate_for_binding(object_type_id, asset_id)
        self.db.commit()

    def upsert_execution(self, asset_id: str, purpose: str) -> None:
        if not asset_id or not purpose:
            return
        if not any(purpose.startswith(p) for p in LINEAGE_PURPOSE_PREFIXES):
            return
        # 解析 purpose 形式为 "<domain>.<feature>" → object_type_id 留空，
        # 这里写 source=asset, target=object_type(by purpose 标签)，
        # 只在 binding 已存在时强化 weight；其余通过 ObjectBinding 写入主路径。
        # 简化：仅累加 ExecutionLog 已有 binds_to 边的 weight（找该 asset 的所有 binding）。
        from app.repositories.object_binding_repo import ObjectBindingRepository
        bindings = ObjectBindingRepository(self.db).list_for_asset(asset_id)
        for b in bindings:
            self.repo.upsert(
                source_kind="asset", source_id=asset_id,
                target_kind="object_type", target_id=b.object_type_id,
                relation="reads", via_module="execute", via_purpose=purpose,
            )
        self.db.commit()

    # ── 查询 ───────────────────────────────────────────
    def get_for_asset(self, asset_id: str, depth: int = 2) -> dict:
        return self._collect("asset", asset_id, depth)

    def get_for_object_type(self, ot_id: str, depth: int = 2) -> dict:
        return self._collect("object_type", ot_id, depth)

    def _collect(self, kind: str, node_id: str, depth: int) -> dict:
        edges, nodes = self.repo.find_neighbors(kind, node_id, depth=depth)
        node_payload = [{"kind": k, "id": i} for k, i in nodes]
        edge_payload = [{
            "source": {"kind": e.source_kind, "id": e.source_id},
            "target": {"kind": e.target_kind, "id": e.target_id},
            "relation": e.relation,
            "via_module": e.via_module,
            "via_purpose": e.via_purpose,
            "weight": e.weight,
        } for e in edges]
        return {"nodes": node_payload, "edges": edge_payload}
