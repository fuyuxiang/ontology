"""LineageEdge 仓库。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.models.lineage_edge import LineageEdge
from app.repositories.base import BaseRepository


class LineageEdgeRepository(BaseRepository[LineageEdge]):
    model = LineageEdge

    def upsert(
        self,
        *,
        source_kind: str,
        source_id: str,
        target_kind: str,
        target_id: str,
        relation: str,
        via_module: str | None = None,
        via_purpose: str | None = None,
    ) -> LineageEdge:
        existing = (
            self.db.query(LineageEdge)
            .filter(
                LineageEdge.source_kind == source_kind,
                LineageEdge.source_id == source_id,
                LineageEdge.target_kind == target_kind,
                LineageEdge.target_id == target_id,
                LineageEdge.relation == relation,
                LineageEdge.via_module == via_module,
            )
            .first()
        )
        now = datetime.utcnow()
        if existing:
            existing.weight = (existing.weight or 1) + 1
            existing.last_seen_at = now
            if via_purpose and not existing.via_purpose:
                existing.via_purpose = via_purpose
            return existing
        edge = LineageEdge(
            source_kind=source_kind,
            source_id=source_id,
            target_kind=target_kind,
            target_id=target_id,
            relation=relation,
            via_module=via_module,
            via_purpose=via_purpose,
            first_seen_at=now,
            last_seen_at=now,
        )
        self.db.add(edge)
        self.db.flush()
        return edge

    def find_neighbors(
        self,
        node_kind: str,
        node_id: str,
        depth: int = 2,
    ) -> tuple[list[LineageEdge], set[tuple[str, str]]]:
        """返回 BFS 收集到的边集合 + 节点集合（最多 depth 层）。"""
        seen_nodes: set[tuple[str, str]] = {(node_kind, node_id)}
        edges: list[LineageEdge] = []
        frontier = [(node_kind, node_id)]
        for _ in range(max(0, depth)):
            if not frontier:
                break
            next_frontier: list[tuple[str, str]] = []
            for k, i in frontier:
                rows = (
                    self.db.query(LineageEdge)
                    .filter(or_(
                        (LineageEdge.source_kind == k) & (LineageEdge.source_id == i),
                        (LineageEdge.target_kind == k) & (LineageEdge.target_id == i),
                    ))
                    .all()
                )
                for e in rows:
                    edges.append(e)
                    s = (e.source_kind, e.source_id)
                    t = (e.target_kind, e.target_id)
                    for node in (s, t):
                        if node not in seen_nodes:
                            seen_nodes.add(node)
                            next_frontier.append(node)
            frontier = next_frontier
        # 去重
        unique = {(e.source_kind, e.source_id, e.target_kind, e.target_id, e.relation, e.via_module): e for e in edges}
        return list(unique.values()), seen_nodes

    def deprecate_for_binding(self, object_type_id: str, asset_id: str) -> None:
        """binding 删除时，把对应的 binds_to 边标 weight=0（保留历史而非真删）。"""
        edge = (
            self.db.query(LineageEdge)
            .filter(
                LineageEdge.source_kind == "asset",
                LineageEdge.source_id == asset_id,
                LineageEdge.target_kind == "object_type",
                LineageEdge.target_id == object_type_id,
                LineageEdge.relation == "binds_to",
            )
            .first()
        )
        if edge:
            edge.weight = 0
            edge.last_seen_at = datetime.utcnow()
