from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import OntologyEntity, EntityAttribute, EntityRelation, BusinessRule, EntityAction, AuditLog
from app.models.datasource import DataSource

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
