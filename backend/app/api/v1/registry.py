"""Registry API — unified view of active rules and functions for skill integration."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BusinessRule, OntologyEntity
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

def _build_ref_counts(db: Session) -> tuple[dict[str, int], dict[str, int]]:
    """Return (rule_refs, function_refs) dicts mapping id -> reference count."""
    rule_refs: dict[str, int] = {}
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
            if "rule_id" in tool:
                rid = tool["rule_id"]
                rule_refs[rid] = rule_refs.get(rid, 0) + 1
            if "function_id" in tool:
                fid = tool["function_id"]
                func_refs[fid] = func_refs.get(fid, 0) + 1

    # Count references to functions from BusinessRule.conditions_json
    rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()
    for rule in rules:
        conditions = rule.conditions_json
        if not isinstance(conditions, list):
            continue
        for cond in conditions:
            if not isinstance(cond, dict):
                continue
            if "function_id" in cond:
                fid = cond["function_id"]
                func_refs[fid] = func_refs.get(fid, 0) + 1

    return rule_refs, func_refs


def _entity_map(db: Session) -> dict[str, str]:
    """Return entity id -> display name mapping."""
    entities = db.query(OntologyEntity).all()
    return {e.id: (e.name_cn or e.name) for e in entities}


def _rule_to_item(rule: BusinessRule, entity_name: str, ref_count: int) -> RegistryItem:
    output_info = ""
    if rule.output_schema and isinstance(rule.output_schema, dict):
        output_info = rule.output_schema.get("type", "") or rule.output_schema.get("description", "")
    return RegistryItem(
        id=rule.id,
        type="rule",
        name=rule.name,
        callable_name="",
        description=rule.description or "",
        entity_id=rule.entity_id,
        entity_name=entity_name,
        tags=rule.tags or [],
        input_params=rule.input_params or [],
        output_info=output_info,
        ref_count=ref_count,
    )


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
    """List all active rules and functions as registry items."""
    rule_refs, func_refs = _build_ref_counts(db)
    emap = _entity_map(db)

    items: list[RegistryItem] = []

    # Collect rules
    if type is None or type == "rule":
        q = db.query(BusinessRule).filter(BusinessRule.status == "active")
        if entity_id:
            q = q.filter(BusinessRule.entity_id == entity_id)
        for rule in q.all():
            if search and search.lower() not in rule.name.lower() and search.lower() not in (rule.description or "").lower():
                continue
            if tags:
                rule_tags = rule.tags or []
                if not any(t in rule_tags for t in tags):
                    continue
            entity_name = emap.get(rule.entity_id, "")
            items.append(_rule_to_item(rule, entity_name, rule_refs.get(rule.id, 0)))

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
    """List active rules and functions grouped by entity."""
    rule_refs, func_refs = _build_ref_counts(db)
    emap = _entity_map(db)

    groups: dict[str | None, RegistryGroup] = {}

    def _get_or_create_group(eid: str | None, ename: str) -> RegistryGroup:
        if eid not in groups:
            groups[eid] = RegistryGroup(entity_id=eid, entity_name=ename, items=[])
        return groups[eid]

    # Rules
    for rule in db.query(BusinessRule).filter(BusinessRule.status == "active").all():
        if search and search.lower() not in rule.name.lower() and search.lower() not in (rule.description or "").lower():
            continue
        entity_name = emap.get(rule.entity_id, "")
        grp = _get_or_create_group(rule.entity_id, entity_name)
        grp.items.append(_rule_to_item(rule, entity_name, rule_refs.get(rule.id, 0)))

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
    """Get references — which skills/rules use this rule or function."""
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

    # For functions, also check BusinessRule.conditions_json
    if item_type == "function":
        rules = db.query(BusinessRule).filter(BusinessRule.status == "active").all()
        for rule in rules:
            conditions = rule.conditions_json
            if not isinstance(conditions, list):
                continue
            for cond in conditions:
                if isinstance(cond, dict) and cond.get("function_id") == item_id:
                    references.append({
                        "ref_type": "rule",
                        "ref_id": rule.id,
                        "ref_name": rule.name,
                    })
                    break  # count each rule once

    return {
        "item_id": item_id,
        "item_type": item_type,
        "references": references,
    }
