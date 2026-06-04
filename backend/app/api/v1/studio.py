"""
本体工作室（OntologyStudio）后端接口 — 输出 v3.1 schema 格式
对齐 fttr-frontend 的 tbox/abox/rbox/capability/stats 数据契约

数据来源：OntologyEntity + EntityAttribute + EntityRelation + BusinessRule + EntityAction + OntologyFunction
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
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

    # 数据源索引：按主表名查 record_count
    from app.models.asset import Asset
    all_assets = db.query(Asset).filter(Asset.status == "active").all()
    ds_by_table = {(a.locator or {}).get("table", ""): a for a in all_assets if (a.locator or {}).get("table")}

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

        # 实例数：从主映射表的 asset.profile.row_count 推算
        primary_tables = [a.source_table for a in e.attributes if a.source_table]
        abox_scale = 0
        if primary_tables:
            ds = ds_by_table.get(primary_tables[0])
            if ds:
                abox_scale = (ds.profile or {}).get("row_count", 0) or 0

        object_types.append({
            "apiName": e.name,
            "displayName": e.name_cn,
            "id": e.id,
            "primaryKey": _primary_key_of(e),
            "titleProperty": _title_property_of(e),
            "tier": e.tier,
            "scenarioCode": _scenario_of(e),
            "status": e.status,
            "visibility": "PROMINENT",
            "iriPattern": f"ontology:{e.name}/{{id}}",
            "aboxScale": abox_scale,
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
    """A-box 断言层：基于属性映射推算实例数 + 字段覆盖率"""
    entities = db.query(OntologyEntity).all()

    # 一次性加载所有 asset，按 table_name 建索引
    from app.models.asset import Asset
    all_assets = db.query(Asset).filter(Asset.status == "active").all()
    ds_by_table: dict[str, Asset] = {}
    for a in all_assets:
        tbl = (a.locator or {}).get("table")
        if tbl:
            ds_by_table[tbl] = a

    hydration = []
    individuals_total = 0
    by_object: dict[str, int] = {}
    for e in entities:
        # 同一对象的属性可能映射到多个表，取第一张表的 record_count 当实例数
        mapped_attrs = [a for a in e.attributes if a.source_field]
        populated_attrs = [a for a in mapped_attrs if a.data_status == "已确认"]
        primary_table: str | None = None
        instance_count = 0
        backing_source = ""
        if mapped_attrs:
            tables = [a.source_table for a in mapped_attrs if a.source_table]
            if tables:
                primary_table = tables[0]
                ds = ds_by_table.get(primary_table)
                if ds:
                    instance_count = (ds.profile or {}).get("row_count", 0) or 0
                    backing_source = ds.name
                else:
                    backing_source = primary_table

        # 水合等级
        total = len(e.attributes)
        if not mapped_attrs:
            level = "none"
        elif primary_table and instance_count > 0 and len(populated_attrs) == total:
            level = "full"
        elif primary_table and instance_count > 0:
            level = "partial"
        else:
            level = "mapping"

        coverage = len(mapped_attrs) / total if total > 0 else 0
        hydration.append({
            "objectTypeApiName": e.name,
            "level": level,
            "instanceCount": instance_count,
            "propertyCompleteness": {
                "total": total,
                "mapped": len(mapped_attrs),
                "populated": len(populated_attrs),
                "coverage": round(coverage, 4),
            },
            "backingSource": backing_source,
            "primaryTable": primary_table,
        })
        individuals_total += instance_count
        by_object[e.name] = instance_count

    return {
        "kind": "abox",
        "version": _SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "source": "datasources.record_count via attribute.source_table",
        "meta": {
            "individualCount": individuals_total,
            "linkCount": 0,
            "scenarios": _all_scenarios(entities),
            "byObjectType": by_object,
        },
        "individuals": [],
        "hydration": hydration,
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
        meta = a.action_meta_json or {}
        desc = (meta.get("description") if isinstance(meta, dict) else None) or ""
        action_list.append({
            "apiName": f"{ent.name}.{a.name}" if ent else a.name,
            "shortApiName": a.name,
            "displayName": a.name,
            "boundObjectType": ent.name if ent else None,
            "scenarioCode": _scenario_of(ent) if ent else "core",
            "kind": "ACTION",
            "returnType": "void",
            "inputProperties": [p.get("name") for p in (a.parameters_json or []) if isinstance(p, dict)],
            "outputProperties": [e.get("property") for e in (a.effects_json or []) if isinstance(e, dict)],
            "writesState": True,
            "implRef": f"action_executor::{a.name}",
            "description": desc,
            "actionType": a.type,
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

    from app.models.asset import Asset
    all_assets = db.query(Asset).filter(Asset.status == "active").all()
    ds_by_table = {(a.locator or {}).get("table", ""): a for a in all_assets if (a.locator or {}).get("table")}

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

    # ABox 真实数据
    abox_total = 0
    abox_by_object: dict[str, int] = {}
    abox_by_scenario: dict[str, int] = {}
    for e in entities:
        primary_tables = [a.source_table for a in e.attributes if a.source_table]
        count = 0
        if primary_tables:
            ds = ds_by_table.get(primary_tables[0])
            if ds:
                count = (ds.profile or {}).get("row_count", 0) or 0
        abox_total += count
        abox_by_object[e.name] = count
        sc = _scenario_of(e)
        abox_by_scenario[sc] = abox_by_scenario.get(sc, 0) + count

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
            "individualCount": abox_total,
            "linkCount": 0,
            "byObjectType": abox_by_object,
            "byScenario": abox_by_scenario,
            "bySourceRef": {},
        },
        "validation": {
            "passed": 0,
            "failed": 0,
            "checks": [],
        },
    }


# ─── 实时事件流：聚合 traces + audit_log + 规则触发 ──────────────────

@router.get("/events")
def get_events(limit: int = 30, db: Session = Depends(get_db)) -> dict[str, Any]:
    """聚合本体平台的实时事件，供数字孪生视图的事件流卡片消费"""
    from app.models.trace import AgentTrace
    from app.models.audit import AuditLog
    from app.models.agent import Agent

    events: list[dict[str, Any]] = []

    # 1. Agent traces（智能体调用记录）
    traces = db.query(AgentTrace).order_by(AgentTrace.created_at.desc()).limit(limit).all()
    agent_names = {a.id: a.name for a in db.query(Agent).all()}
    for t in traces:
        events.append({
            "id": f"trace-{t.id}",
            "ts": t.created_at.isoformat() if t.created_at else "",
            "type": "skill" if t.status == "ok" else "alert",
            "icon": "✦" if t.status == "ok" else "▲",
            "desc": f"{agent_names.get(t.agent_id, '智能体')} {'完成' if t.status == 'ok' else '异常'}: {(t.output_text or t.input_text or '')[:60]}",
        })

    # 2. AuditLog（实体/规则/动作的 CRUD）
    audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    for a in audits:
        type_map = {"entity": "state_change", "rule": "rule", "action": "skill", "agent": "skill"}
        icon_map = {"entity": "●", "rule": "◇", "action": "✦", "agent": "▸"}
        action_label = {"create": "创建", "update": "更新", "delete": "删除", "publish": "发布"}.get(a.action, a.action)
        events.append({
            "id": f"audit-{a.id}",
            "ts": a.timestamp.isoformat() if a.timestamp else "",
            "type": type_map.get(a.target_type, "state_change"),
            "icon": icon_map.get(a.target_type, "●"),
            "desc": f"{a.user_name or '系统'} {action_label} {a.target_type} {a.target_name}",
        })

    # 3. 高频触发规则（trigger_count Top N）
    rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.trigger_count > 0)
        .filter(BusinessRule.last_triggered.isnot(None))
        .order_by(BusinessRule.last_triggered.desc())
        .limit(10)
        .all()
    )
    for r in rules:
        if r.last_triggered:
            events.append({
                "id": f"rule-{r.id}",
                "ts": r.last_triggered.isoformat(),
                "type": "rule",
                "icon": "◇",
                "desc": f"规则 {r.name} 触发 (累计 {r.trigger_count} 次)",
            })

    # 时间倒序合并裁剪
    events.sort(key=lambda e: e["ts"], reverse=True)
    return {
        "generatedAt": _now_iso(),
        "total": len(events),
        "events": events[:limit],
    }


# ─── AI 业务解读（OntologyNarrator）─────────────────────────────────

class NarratorRequest(BaseModel):
    apiName: str
    displayName: str
    tier: int
    instanceCount: int = 0
    propCount: int = 0
    relCount: int = 0
    ruleCount: int = 0
    actionCount: int = 0
    kpiSummary: str = ""


# 14 个核心对象的 hardcoded fallback 文案（LLM 不可用时用）
_NARRATOR_FALLBACK = {
    "Customer": "客户是整个业务的核心主体。客户与订单、产品、地址、分群都有直接关联，是所有推理链的起点。建议关注 ARPU 中价值区间——这是转化率最高的黄金区间。",
    "Order": "订单记录了客户的每一笔交易行为。订单连接了客户和产品，是衡量策略效果的核心指标。通过分析订单数据，可以追溯哪个渠道、哪个话术、哪个产品组合带来了最高转化。",
    "Product": "产品是策略的核心载体。低门槛产品更容易促成转化。产品与客户分群通过匹配规则关联，不同分群推荐不同产品。",
    "InstallOrder": "装机订单是宽带退单稽核的关键起点。它连接了客户、地址、工程师、派单记录，是归因分析的核心证据来源。",
    "InstallChurn": "装机退单是退单稽核的核心对象。通过 35 项证据推理（E1-E35），系统自动给出归因结论：客户责任 / 工程师责任 / 业务责任 / 第三方责任 / 异常情况。",
    "DispatchRecord": "派单记录承载了工程师与工单的派遣关系，是工程师责任归因的核心证据。",
    "EngineerCall": "工程师与客户的通话录音，经过语音质检后产出客户意向、工程师服务质量等关键证据。",
    "Channel": "渠道定义了触达通路。不同渠道的转化率和覆盖面差异显著。当前策略是多渠道协同——先线上预热，再线下跟进。",
    "Staff": "员工是触达和服务的核心执行力量。客户经理人均管户百余户，他们的执行效率直接影响转化。",
    "RegionalOrg": "组织架构覆盖各盟市分公司。不同分公司的渗透率和转化率差异显著，需要将经验向其他盟市推广。",
}


@router.post("/narrator/explain")
def narrator_explain(req: NarratorRequest) -> dict[str, Any]:
    """对本体对象生成业务解读（fttr OntologyNarrator 复刻）"""
    tier_label = {1: "核心层", 2: "领域层", 3: "场景层"}.get(req.tier, "未知层")
    prompt = f"""你是 Agentic Ontology 智能本体平台的业务解说员。请用简洁生动的中文，对以下本体对象进行全方位业务解读。

对象：{req.displayName}（{req.apiName}）
层级：Tier {req.tier}（{tier_label}）
实例数：{req.instanceCount}｜属性数：{req.propCount}｜关系数：{req.relCount}｜规则数：{req.ruleCount}｜动作数：{req.actionCount}
业务指标：{req.kpiSummary or '暂无'}

请从以下维度解读（每个维度 1-2 句话，总共不超过 150 字）：
1. 业务角色：这个对象在业务中扮演什么角色？
2. 关键价值：它的核心业务价值是什么？
3. 当前状态：基于数据，当前业务状态如何？
4. 关联影响：它与哪些对象的关系最关键？
5. 推荐关注：当前最需要关注什么？

用口语化的方式，像一个资深业务专家在给新同事介绍。不要用 markdown 格式。"""

    try:
        from app.services.copilot import get_llm_client
        client = get_llm_client()
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
        )
        content = response.choices[0].message.content or ""
        # 剥离推理模型的 <think>...</think> 块
        import re
        content = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
        if content:
            return {"source": "llm", "content": content}
    except Exception as e:
        print(f"narrator LLM failed: {e}")

    # Fallback 到 hardcoded 模板
    fallback = _NARRATOR_FALLBACK.get(
        req.apiName,
        f"{req.displayName} 是本体中的{tier_label}对象，当前有 {req.instanceCount} 个实例。"
        f"它在业务中承担重要角色，与多个对象存在关联关系。"
        f"建议点击查看详情面板了解更多属性和规则信息。"
    )
    return {"source": "fallback", "content": fallback}


# ─── 数据刷新：手动触发所有 asset 实例计数 ──────────────────────
def refresh_counts(db: Session = Depends(get_db)) -> dict[str, Any]:
    """触发所有启用的数据资产重新统计 row_count，刷新 A-Box 实例数"""
    from app.models.asset import Asset
    from app.services.data_plane.entity_data_service import EntityDataService

    assets = db.query(Asset).filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"])).all()
    results = []
    success = 0
    svc = EntityDataService(db)
    for asset in assets:
        table_name = (asset.locator or {}).get("table")
        if not table_name:
            results.append({"id": asset.id, "name": asset.name, "status": "skip", "message": "未关联数据表"})
            continue
        r = svc.execute_sql_on_asset(asset.name, f"SELECT COUNT(*) FROM `{table_name}`", purpose="refresh_counts")
        if r.get("error"):
            results.append({"id": asset.id, "name": asset.name, "status": "error", "message": r["error"]})
            continue
        count = r["rows"][0][0] if r.get("rows") else 0
        profile = asset.profile or {}
        profile["row_count"] = count
        asset.profile = profile
        success += 1
        results.append({"id": asset.id, "name": asset.name, "status": "ok", "count": count})
    db.commit()
    return {
        "refreshedAt": _now_iso(),
        "total": len(assets),
        "success": success,
        "results": results,
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
