"""
Snapshot service: copies active Function/Action records into versioned
snapshot tables when a version is published.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.models.version_components import (
    OntologyVersionAction,
    OntologyVersionFunction,
)

logger = logging.getLogger(__name__)


def _remap_attr_ids(items: list[dict] | None, attr_map: dict[str, str]) -> list[dict] | None:
    """Return a deep-copied list with attribute_id replaced by version_attribute_id.

    For each dict in *items*:
    - Pop ``attribute_id`` (if present).
    - Set ``version_attribute_id`` to the mapped version ID, or None when unknown.
    Items without ``attribute_id`` are passed through unchanged.
    """
    if items is None:
        return None
    result = []
    for raw in items:
        item = copy.deepcopy(raw)
        if "attribute_id" in item:
            src_id = item.pop("attribute_id")
            item["version_attribute_id"] = attr_map.get(src_id)
        result.append(item)
    return result


def snapshot_components_for_version(db: Session, version: Any) -> dict:
    """Create snapshot records for all active Functions/Actions in *version*.

    Parameters
    ----------
    db:
        SQLAlchemy session (already open; caller owns commit/rollback).
    version:
        An ``OntologyVersion`` instance with ``.entities`` eagerly loaded and
        each entity's ``.attributes`` also loaded.

    Returns
    -------
    dict
        ``{"functions_count": N, "actions_count": N}``
    """
    functions_count = 0
    actions_count = 0

    for version_entity in version.entities:
        # Build attribute mapping: source_attribute_id -> version_attribute_id
        attr_map: dict[str, str] = {
            attr.source_attribute_id: attr.id
            for attr in version_entity.attributes
        }

        entity_id = version_entity.source_entity_id

        # --- Functions -------------------------------------------------------
        functions = (
            db.query(OntologyFunction)
            .filter(
                OntologyFunction.entity_id == entity_id,
                OntologyFunction.status == "active",
            )
            .all()
        )
        for fn in functions:
            snap = OntologyVersionFunction(
                version_id=version.id,
                source_function_id=fn.id,
                version_entity_id=version_entity.id,
                name=fn.name,
                description=fn.description,
                return_type=fn.return_type,
                input_schema=_remap_attr_ids(fn.input_schema, attr_map),
                logic_type=fn.logic_type,
                logic_body=fn.logic_body,
                callable_name=fn.callable_name,
                tags=fn.tags,
            )
            db.add(snap)
            functions_count += 1

        # --- Domain actions --------------------------------------------------
        actions = (
            db.query(EntityAction)
            .filter(
                EntityAction.entity_id == entity_id,
                EntityAction.status == "active",
            )
            .all()
        )
        for action in actions:
            snap = OntologyVersionAction(
                version_id=version.id,
                source_action_id=action.id,
                version_entity_id=version_entity.id,
                name=action.name,
                category=action.category,
                action_type=action.action_type,
                type_config=action.type_config,
                description=action.description,
                parameters_json=_remap_attr_ids(action.parameters_json, attr_map),
                output_schema=action.output_schema,
            )
            db.add(snap)
            actions_count += 1

    # --- System-level actions (entity_id is None, category="system") ---------
    system_actions = (
        db.query(EntityAction)
        .filter(
            EntityAction.category == "system",
            EntityAction.entity_id == None,  # noqa: E711
            EntityAction.status == "active",
        )
        .all()
    )
    for action in system_actions:
        snap = OntologyVersionAction(
            version_id=version.id,
            source_action_id=action.id,
            version_entity_id=None,
            name=action.name,
            category=action.category,
            action_type=action.action_type,
            type_config=action.type_config,
            description=action.description,
            parameters_json=_remap_attr_ids(action.parameters_json, {}),
            output_schema=action.output_schema,
        )
        db.add(snap)
        actions_count += 1

    db.flush()
    logger.info(
        "Version %s snapshot: %d functions, %d actions",
        version.id,
        functions_count,
        actions_count,
    )
    return {
        "functions_count": functions_count,
        "actions_count": actions_count,
    }
