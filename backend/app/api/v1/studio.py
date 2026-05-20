"""
本体工作室（OntologyStudio）后端接口 — 输出 v3.1 schema 格式
对齐 fttr-frontend 的 tbox/abox/rbox/capability/stats 数据契约

数据来源：OntologyEntity + EntityAttribute + EntityRelation + BusinessRule + EntityAction + OntologyFunction
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.relation import EntityRelation
from app.models.rule import BusinessRule, EntityAction
from app.models.function import OntologyFunction

router = APIRouter(prefix="/studio", tags=["studio"])


_TIER_LABEL = {1: "核心", 2: "领域", 3: "场景"}
_SCHEMA_VERSION = "V3.1"


# ─── TBox: 术语层 ────────────────────────────────────────────────────

@router.get("/tbox")
def get_tbox(db: Session = Depends(get_db)) -> dict[str, Any]:
    """T-box 术语层：所有对象类型 + 属性 + 关系类型的 schema 定义"""
    entities = db.query(OntologyEntity).all()
    relations = db.query(EntityRelation).all()

    entity_map = {e.id: e for e in entities}

    object_types = []
    for e in entities:
        properties = []
        for a in e.attributes:
            properties.append({
                "apiName": a.name,
                "displayName": a.name,
                "dataType": _normalize_data_type(a.type),
                "physicalName": a.source_field or a.name,
                "required": a.required,
                "isDerived": False,
                "description": a.description or "",
                "valueConstraint": a.constraints_json,
                "enum": None,
                "sourceColumn": a.source_field,
                "sourceTable": a.source_table,
                "dataStatus": a.data_status,
            })

        object_types.append({
            "apiName": e.name,
            "displayName": e.name_cn,
            "primaryKey": _primary_key_of(e),
            "titleProperty": _title_property_of(e),
            "tier": e.tier,
            "scenarioCode": _scenario_of(e),
            "status": e.status,
            "visibility": "PROMINENT",
            "iriPattern": f"ontology:{e.name}/{{id}}",
            "aboxScale": 0,  # 由 abox 接口计算
            "dataSource": _data_source_of(e),
            "description": e.description or "",
            "remarks": [],
            "properties": properties,
            "ruleCount": len(e.rules),
            "actionCount": len(e.actions),
            "functionCount": len(e.functions),
        })

    link_types = []
    for r in relations:
        src = entity_map.get(r.from_entity_id)
        tgt = entity_map.get(r.to_entity_id)
        if not src or not tgt:
            continue
        link_types.append({
            "apiName": r.name,
            "displayName": r.description or r.name,
            "source": src.name,
            "target": tgt.name,
            "cardinality": r.cardinality,
            "relType": r.rel_type,
            "acyclic": r.acyclic,
            "description": r.description or "",
        })

    tier_breakdown = {f"Tier{t}": [e.name for e in entities if e.tier == t] for t in (1, 2, 3)}
    prop_count = sum(len(e.attributes) for e in entities)

    return {
        "kind": "tbox",
        "version": _SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "source": "ontology_entities + entity_attributes + entity_relations",
        "meta": {
            "objectTypeCount": len(entities),
            "propertyCount": prop_count,
            "linkTypeCount": len(link_types),
            "scenarios": _all_scenarios(entities),
            "tierBreakdown": tier_breakdown,
        },
        "objectTypes": object_types,
        "linkTypes": link_types,
    }


# ─── ABox: 断言层 ────────────────────────────────────────────────────

@router.get("/abox")
def get_abox(db: Session = Depends(get_db)) -> dict[str, Any]:
    """A-box 断言层：实例数据 + 水合状态。

    当前我们尚无真实实例表，输出实例 = 0 但保留对象/关系列表，
    给前端"未水合"状态使用。后续接入 poc-service-api 的真实数据。
    """
    entities = db.query(OntologyEntity).all()
    return {
        "kind": "abox",
        "version": _SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "source": "live (placeholder, awaiting POC integration)",
        "meta": {
            "individualCount": 0,
            "linkCount": 0,
            "scenarios": _all_scenarios(entities),
        },
        "individuals": [],
        "hydration": [
            {
                "objectTypeApiName": e.name,
                "level": "none",
                "instanceCount": 0,
                "propertyCompleteness": {
                    "total": len(e.attributes),
                    "mapped": sum(1 for a in e.attributes if a.source_field),
                    "populated": 0,
                    "coverage": 0.0,
                },
                "backingSource": _data_source_of(e),
            }
            for e in entities
        ],
    }


# ─── RBox: 规则层 ────────────────────────────────────────────────────

@router.get("/rbox")
def get_rbox(db: Session = Depends(get_db)) -> dict[str, Any]:
    """R-box 规则层：业务规则定义"""
    rules = db.query(BusinessRule).all()
    entities = db.query(OntologyEntity).all()
    entity_map = {e.id: e for e in entities}

    rule_list = []
    for r in rules:
        ent = entity_map.get(r.entity_id) if r.entity_id else None
        meta = r.rule_meta_json or {}
        category = (meta.get("category") if isinstance(meta, dict) else None) or "INFERENCE"
        rule_list.append({
            "rule_id": r.id,
            "display_name": r.name,
            "category": category,
            "priority": r.priority,
            "condition": r.conditions_json or r.condition_expr,
            "action": {
                "reason": r.action_desc,
                "type": "annotate",
            },
            "applicable_objects": [ent.name] if ent else [],
            "scenarioCode": _scenario_of(ent) if ent else "core",
            "status": r.status,
            "trigger_count": r.trigger_count,
        })

    family_summary: dict[str, int] = {}
    for r in rule_list:
        family = r["category"]
        family_summary[family] = family_summary.get(family, 0) + 1

    return {
        "kind": "rbox",
        "version": _SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "source": "business_rules",
        "meta": {
            "ruleFamilyCount": len(family_summary),
            "ruleCount": len(rule_list),
            "scenarios": _all_scenarios(entities),
        },
        "rules": rule_list,
        "ruleFamilies": [
            {"familyId": k, "displayName": k, "ruleCount": v} for k, v in family_summary.items()
        ],
        "constraints": [],
    }


# ─── Capability: 行为层（actions + functions） ────────────────────────

@router.get("/capability")
def get_capability(db: Session = Depends(get_db)) -> dict[str, Any]:
    actions = db.query(EntityAction).all()
    functions = db.query(OntologyFunction).all()
    entities = db.query(OntologyEntity).all()
    entity_map = {e.id: e for e in entities}

    action_list = []
    for a in actions:
        ent = entity_map.get(a.entity_id)
        action_list.append({
            "apiName": f"{ent.name}.{a.name}" if ent else a.name,
            "shortApiName": a.name,
            "displayName": a.name,
            "boundObjectType": ent.name if ent else None,
            "scenarioCode": _scenario_of(ent) if ent else "core",
            "kind": "ACTION",
            "returnType": "void",
            "inputProperties": [],
            "outputProperties": [],
            "writesState": True,
            "implRef": f"action_executor::{a.name}",
            "description": a.description or "",
        })

    function_list = []
    for f in functions:
        ent = entity_map.get(f.entity_id) if f.entity_id else None
        function_list.append({
            "apiName": f"{ent.name}.{f.name}" if ent else f.name,
            "shortApiName": f.name,
            "displayName": f.name,
            "boundObjectType": ent.name if ent else None,
            "scenarioCode": _scenario_of(ent) if ent else "core",
            "kind": "FUNCTION",
            "returnType": f.return_type or "string",
            "isDerived": f.is_derived_property,
            "logicType": f.logic_type,
            "description": f.description or "",
        })

    return {
        "kind": "capability",
        "version": _SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "source": "entity_actions + ontology_functions",
        "meta": {
            "actionCount": len(action_list),
            "functionCount": len(function_list),
            "skillCount": 0,
            "toolCount": 0,
            "modelCount": 0,
            "scenarios": _all_scenarios(entities),
        },
        "actions": action_list,
        "functions": function_list,
        "skills": [],
        "tools": [],
        "models": [],
    }


# ─── Stats: 汇总指标 ─────────────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    entities = db.query(OntologyEntity).all()
    relations = db.query(EntityRelation).all()
    rules = db.query(BusinessRule).all()
    actions = db.query(EntityAction).all()
    functions = db.query(OntologyFunction).all()

    prop_count = sum(len(e.attributes) for e in entities)

    tier_breakdown = {f"Tier{t}": [e.name for e in entities if e.tier == t] for t in (1, 2, 3)}
    scenario_breakdown: dict[str, int] = {}
    for e in entities:
        sc = _scenario_of(e)
        scenario_breakdown[sc] = scenario_breakdown.get(sc, 0) + 1

    rule_family: dict[str, int] = {}
    for r in rules:
        meta = r.rule_meta_json or {}
        family = (meta.get("category") if isinstance(meta, dict) else None) or "INFERENCE"
        rule_family[family] = rule_family.get(family, 0) + 1

    return {
        "generatedAt": _now_iso(),
        "elapsedSeconds": 0,
        "tbox": {
            "objectTypeCount": len(entities),
            "propertyCount": prop_count,
            "linkTypeCount": len(relations),
            "tierBreakdown": tier_breakdown,
            "scenarioBreakdown": scenario_breakdown,
        },
        "capability": {
            "actionCount": len(actions),
            "functionCount": len(functions),
            "skillCount": 0,
            "toolCount": 0,
            "modelCount": 0,
            "scenarioBreakdown": scenario_breakdown,
        },
        "rbox": {
            "ruleFamilyCount": len(rule_family),
            "ruleCount": len(rules),
            "byFamily": rule_family,
            "scenarioBreakdown": scenario_breakdown,
        },
        "abox": {
            "individualCount": 0,
            "linkCount": 0,
            "byObjectType": {},
            "byScenario": {},
            "bySourceRef": {},
        },
        "validation": {
            "passed": 0,
            "failed": 0,
            "checks": [],
        },
    }


# ─── 内部辅助 ────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scenario_of(e: OntologyEntity | None) -> str:
    """从 entity 的 publish_config / schema_json 中提取场景代码，缺省按 tier 推断"""
    if not e:
        return "core"
    cfg = e.publish_config or {}
    if isinstance(cfg, dict) and cfg.get("scenarioCode"):
        return cfg["scenarioCode"]
    sj = e.schema_json or {}
    if isinstance(sj, dict) and sj.get("scenarioCode"):
        return sj["scenarioCode"]
    return "core" if e.tier in (1, 2) else "s1"


def _all_scenarios(entities: list[OntologyEntity]) -> list[str]:
    return sorted({_scenario_of(e) for e in entities})


def _primary_key_of(e: OntologyEntity) -> str:
    for a in e.attributes:
        if a.required and a.name.endswith("_id"):
            return a.name
    if e.attributes:
        return e.attributes[0].name
    return "id"


def _title_property_of(e: OntologyEntity) -> str:
    for a in e.attributes:
        if "name" in a.name.lower() or "title" in a.name.lower():
            return a.name
    return _primary_key_of(e)


def _data_source_of(e: OntologyEntity) -> str:
    tables = sorted({a.source_table for a in e.attributes if a.source_table})
    return " + ".join(tables) if tables else ""


def _normalize_data_type(t: str | None) -> str:
    if not t:
        return "String"
    return {
        "string": "String", "number": "Number", "boolean": "Boolean",
        "date": "Date", "json": "Json", "ref": "Reference",
        "computed": "Computed", "enum": "Enum",
    }.get(t.lower(), t.capitalize())
