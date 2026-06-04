"""
本体发布影响分析 — 计算破坏性变更并标记受影响的下游对象
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.scene import AipScene
from app.models.agent import Agent
from app.models.version import OntologyVersion, OntologyVersionEntity


def compute_breaking_changes(
    old_entities: list[dict],
    new_entities: list[dict],
) -> list[dict]:
    if not old_entities:
        return []

    new_by_source = {e["source_entity_id"]: e["name"] for e in new_entities}
    changes = []

    for old in old_entities:
        sid = old["source_entity_id"]
        if sid not in new_by_source:
            changes.append({
                "entity_name": old["name"],
                "change_type": "deleted",
                "source_entity_id": sid,
            })
        elif new_by_source[sid] != old["name"]:
            changes.append({
                "entity_name": old["name"],
                "change_type": "renamed",
                "new_name": new_by_source[sid],
                "source_entity_id": sid,
            })

    return changes


def find_affected_scenes(
    scenes: list[dict],
    changes: list[dict],
) -> list[str]:
    affected_names = {c["entity_name"] for c in changes}
    result = []
    for scene in scenes:
        bindings = scene.get("ontology_bindings") or []
        if any(name in affected_names for name in bindings):
            result.append(scene["id"])
    return result


def find_affected_agents(
    agents: list[dict],
    changes: list[dict],
) -> list[str]:
    affected_ids = {c["source_entity_id"] for c in changes}
    result = []
    for agent in agents:
        entity_ids = agent.get("entity_ids") or []
        if any(eid in affected_ids for eid in entity_ids):
            result.append(agent["id"])
    return result


def mark_stale_dependents(
    old_version: OntologyVersion | None,
    new_version: OntologyVersion,
    db: Session,
) -> dict:
    old_entities = []
    if old_version:
        old_entities = [
            {"source_entity_id": ve.source_entity_id, "name": ve.name}
            for ve in old_version.entities
        ]

    new_entities = [
        {"source_entity_id": ve.source_entity_id, "name": ve.name}
        for ve in new_version.entities
    ]

    changes = compute_breaking_changes(old_entities, new_entities)
    if not changes:
        return {"breaking_changes": [], "affected_scenes": 0, "affected_agents": 0}

    stale_detail = {
        "version_id": new_version.id,
        "published_at": datetime.utcnow().isoformat(),
        "breaking_changes": changes,
    }

    scenes = db.query(AipScene).filter(AipScene.ontology_bindings.isnot(None)).all()
    scene_dicts = [{"id": s.id, "ontology_bindings": s.ontology_bindings} for s in scenes]
    affected_scene_ids = find_affected_scenes(scene_dicts, changes)

    if affected_scene_ids:
        db.query(AipScene).filter(AipScene.id.in_(affected_scene_ids)).update(
            {"ontology_stale": True, "ontology_stale_detail": stale_detail},
            synchronize_session="fetch",
        )

    agents = db.query(Agent).filter(Agent.entity_ids.isnot(None)).all()
    agent_dicts = [{"id": a.id, "entity_ids": a.entity_ids} for a in agents]
    affected_agent_ids = find_affected_agents(agent_dicts, changes)

    if affected_agent_ids:
        db.query(Agent).filter(Agent.id.in_(affected_agent_ids)).update(
            {"ontology_stale": True, "ontology_stale_detail": stale_detail},
            synchronize_session="fetch",
        )

    return {
        "breaking_changes": changes,
        "affected_scenes": len(affected_scene_ids),
        "affected_agents": len(affected_agent_ids),
    }
