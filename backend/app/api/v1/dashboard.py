from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Any

from app.database import get_db
from app.models import OntologyEntity, EntityAttribute, EntityRelation, BusinessRule, EntityAction, AuditLog
from app.models.datasource import DataSource
from app.models.dashboard_config import DashboardConfig

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DEFAULT_CARDS = [
    {"key": "analytics", "title": "ANALYTICS & WORKFLOWS", "enabled": True,
     "items": [
         {"type": "dynamic", "field": "entity_count", "label": "个实体"},
         {"type": "dynamic", "field": "relation_count", "label": "条关系"},
         {"type": "dynamic", "field": "rule_count", "label": "条规则"},
         {"type": "dynamic", "field": "active_rule_count", "label": "条活跃规则"},
     ]},
    {"key": "automations", "title": "AUTOMATIONS", "enabled": True,
     "items": [{"type": "top_rules", "count": 4}]},
    {"key": "products", "title": "PRODUCTS & SDKs", "enabled": True,
     "items": [
         {"type": "static", "text": "Ontology Center"},
         {"type": "static", "text": "AI Copilot"},
         {"type": "static", "text": "AIP Workflow"},
         {"type": "static", "text": "API Gateway"},
     ]},
    {"key": "datasources", "title": "DATA SOURCES", "enabled": True,
     "items": [{"type": "datasources", "count": 8}]},
    {"key": "logic", "title": "LOGIC SOURCES", "enabled": True,
     "items": [{"type": "rule_priority"}]},
    {"key": "actions", "title": "SYSTEMS OF ACTION", "enabled": True,
     "items": [{"type": "recent_activities", "count": 5}]},
]


class ConfigBody(BaseModel):
    cards_config: list[Any]
    refresh_interval: int = 30


@router.get("/config")
def get_config(db: Session = Depends(get_db)):
    cfg = db.get(DashboardConfig, "default")
    if not cfg:
        return {"cards_config": DEFAULT_CARDS, "refresh_interval": 30}
    return {"cards_config": cfg.cards_config or DEFAULT_CARDS, "refresh_interval": cfg.refresh_interval}


@router.put("/config")
def save_config(body: ConfigBody, db: Session = Depends(get_db)):
    cfg = db.get(DashboardConfig, "default")
    if not cfg:
        cfg = DashboardConfig(id="default")
        db.add(cfg)
    cfg.cards_config = body.cards_config
    cfg.refresh_interval = body.refresh_interval
    db.commit()
    return {"ok": True}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    entity_count = db.query(func.count(OntologyEntity.id)).scalar() or 0
    relation_count = db.query(func.count(EntityRelation.id)).scalar() or 0
    rule_count = db.query(func.count(BusinessRule.id)).scalar() or 0
    active_rules = db.query(func.count(BusinessRule.id)).filter(BusinessRule.status == "active").scalar() or 0
    action_count = db.query(func.count(EntityAction.id)).scalar() or 0
    attr_count = db.query(func.count(EntityAttribute.id)).scalar() or 0
    ds_count = db.query(func.count(DataSource.id)).scalar() or 0

    # Tier 分布
    tier_dist = []
    for tier, name in [(1, "核心对象"), (2, "领域对象"), (3, "场景对象")]:
        count = db.query(func.count(OntologyEntity.id)).filter(OntologyEntity.tier == tier).scalar() or 0
        pct = round(count / entity_count * 100) if entity_count > 0 else 0
        tier_dist.append({"tier": tier, "name": name, "count": count, "pct": pct})

    # 命名空间分布
    ns_rows = (
        db.query(
            func.substr(OntologyEntity.name, 1, func.instr(OntologyEntity.name, ".") - 1).label("ns"),
            func.count(OntologyEntity.id).label("cnt"),
        )
        .filter(OntologyEntity.name.contains("."))
        .group_by("ns")
        .order_by(func.count(OntologyEntity.id).desc())
        .limit(8)
        .all()
    )
    ns_dist = [{"ns": r.ns or "default", "count": r.cnt} for r in ns_rows]

    # 规则优先级分布
    rule_priority = []
    for p in ("high", "medium", "low"):
        cnt = db.query(func.count(BusinessRule.id)).filter(BusinessRule.priority == p).scalar() or 0
        rule_priority.append({"priority": p, "count": cnt})

    # 规则触发 TOP5
    top_rules = (
        db.query(BusinessRule)
        .filter(BusinessRule.trigger_count > 0)
        .order_by(BusinessRule.trigger_count.desc())
        .limit(5)
        .all()
    )
    top_rules_data = [
        {"id": r.id, "name": r.name, "trigger_count": r.trigger_count,
         "status": r.status, "priority": r.priority}
        for r in top_rules
    ]

    # 对象健康状态
    entities = db.query(OntologyEntity).order_by(OntologyEntity.tier, OntologyEntity.name).all()
    health = [{"id": e.id, "name": e.name, "name_cn": e.name_cn, "tier": e.tier, "status": e.status} for e in entities]

    # 近期活动
    recent = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(15).all()
    activities = []
    for a in recent:
        activities.append({
            "id": a.id,
            "type": a.action,
            "target_type": a.target_type,
            "target_name": a.target_name,
            "user": a.user_name or "系统",
            "time": a.timestamp.strftime("%m-%d %H:%M") if a.timestamp else "",
        })

    # 数据源列表
    datasources = db.query(DataSource).all()
    ds_list = [{"id": d.id, "name": d.name, "type": d.type, "status": d.status} for d in datasources]

    return {
        "entity_count": entity_count,
        "relation_count": relation_count,
        "rule_count": rule_count,
        "active_rule_count": active_rules,
        "action_count": action_count,
        "attr_count": attr_count,
        "datasource_count": ds_count,
        "tier_distribution": tier_dist,
        "ns_distribution": ns_dist,
        "rule_priority": rule_priority,
        "top_rules": top_rules_data,
        "health_status": health,
        "recent_activities": activities,
        "datasources": ds_list,
    }
