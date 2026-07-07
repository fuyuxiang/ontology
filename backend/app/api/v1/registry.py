"""Registry API — unified view of active rules and functions for skill integration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OntologyEntity
from app.models.function import OntologyFunction
from app.models.skill import Skill

router = APIRouter(prefix="/registry", tags=["registry"])


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class RegistryItem(BaseModel):
    id: str
    type: str  # "rule" or "function"
    name: str
    callable_name: str = ""
    description: str = ""
    entity_id: str | None = None
    entity_name: str = ""
    tags: list[str] = []
    input_params: list[dict] = []
    output_info: str = ""
    ref_count: int = 0


class RegistryGroup(BaseModel):
    entity_id: str | None
    entity_name: str
    items: list[RegistryItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_ref_counts(db: Session) -> dict[str, int]:
    """Return function_refs dict mapping id -> reference count."""
    func_refs: dict[str, int] = {}

    # Count references from Skill.tools (JSON list of dicts)
    skills = db.query(Skill).filter(Skill.status == "active").all()
    for skill in skills:
        tools = skill.tools
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            if "function_id" in tool:
                fid = tool["function_id"]
                func_refs[fid] = func_refs.get(fid, 0) + 1

    return func_refs


def _entity_map(db: Session) -> dict[str, str]:
    """Return entity id -> display name mapping."""
    entities = db.query(OntologyEntity).all()
    return {e.id: (e.name_cn or e.name) for e in entities}


def _func_to_item(func: OntologyFunction, entity_name: str, ref_count: int) -> RegistryItem:
    output_info = func.return_type or ""
    return RegistryItem(
        id=func.id,
        type="function",
        name=func.name,
        callable_name=func.callable_name or "",
        description=func.description or "",
        entity_id=func.entity_id,
        entity_name=entity_name,
        tags=func.tags or [],
        input_params=func.input_schema or [],
        output_info=output_info,
        ref_count=ref_count,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/items", response_model=list[RegistryItem])
def list_registry_items(
    type: str | None = Query(None, description="Filter by type: 'rule' or 'function'"),
    entity_id: str | None = Query(None),
    search: str | None = Query(None),
    tags: list[str] = Query(default=[]),
    db: Session = Depends(get_db),
):
    """List all active functions as registry items."""
    func_refs = _build_ref_counts(db)
    emap = _entity_map(db)

    items: list[RegistryItem] = []

    # Collect functions
    if type is None or type == "function":
        q = db.query(OntologyFunction).filter(OntologyFunction.status == "active")
        if entity_id:
            q = q.filter(OntologyFunction.entity_id == entity_id)
        for func in q.all():
            if search and search.lower() not in func.name.lower() and search.lower() not in (func.description or "").lower():
                continue
            if tags:
                func_tags = func.tags or []
                if not any(t in func_tags for t in tags):
                    continue
            entity_name = emap.get(func.entity_id or "", "")
            items.append(_func_to_item(func, entity_name, func_refs.get(func.id, 0)))

    return items


@router.get("/grouped", response_model=list[RegistryGroup])
def list_registry_grouped(
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List active functions grouped by entity."""
    func_refs = _build_ref_counts(db)
    emap = _entity_map(db)

    groups: dict[str | None, RegistryGroup] = {}

    def _get_or_create_group(eid: str | None, ename: str) -> RegistryGroup:
        if eid not in groups:
            groups[eid] = RegistryGroup(entity_id=eid, entity_name=ename, items=[])
        return groups[eid]

    # Functions
    for func in db.query(OntologyFunction).filter(OntologyFunction.status == "active").all():
        if search and search.lower() not in func.name.lower() and search.lower() not in (func.description or "").lower():
            continue
        entity_name = emap.get(func.entity_id or "", "")
        grp = _get_or_create_group(func.entity_id, entity_name)
        grp.items.append(_func_to_item(func, entity_name, func_refs.get(func.id, 0)))

    return list(groups.values())


@router.get("/refs/{item_type}/{item_id}")
def get_item_refs(
    item_type: str,
    item_id: str,
    db: Session = Depends(get_db),
):
    """Get references — which skills use this function."""
    references: list[dict] = []

    # Check Skill.tools references
    skills = db.query(Skill).filter(Skill.status == "active").all()
    key = "rule_id" if item_type == "rule" else "function_id"
    for skill in skills:
        tools = skill.tools
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if isinstance(tool, dict) and tool.get(key) == item_id:
                references.append({
                    "ref_type": "skill",
                    "ref_id": skill.id,
                    "ref_name": skill.name,
                })
                break  # count each skill once

    return {
        "item_id": item_id,
        "item_type": item_type,
        "references": references,
    }
