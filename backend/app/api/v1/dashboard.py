from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import OntologyEntity, EntityRelation, BusinessRule, AuditLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    entity_count = db.query(func.count(OntologyEntity.id)).scalar() or 0
    relation_count = db.query(func.count(EntityRelation.id)).scalar() or 0
    rule_count = db.query(func.count(BusinessRule.id)).scalar() or 0
    active_rules = db.query(func.count(BusinessRule.id)).filter(BusinessRule.status == "active").scalar() or 0

    # Tier 分布
    tier_dist = []
    for tier, name in [(1, "核心对象"), (2, "领域对象"), (3, "场景对象")]:
        count = db.query(func.count(OntologyEntity.id)).filter(OntologyEntity.tier == tier).scalar() or 0
        pct = round(count / entity_count * 100) if entity_count > 0 else 0
        tier_dist.append({"tier": tier, "name": name, "count": count, "pct": pct})

    # 对象健康状态
    entities = db.query(OntologyEntity).order_by(OntologyEntity.tier, OntologyEntity.name).all()
    health = [{"id": e.id, "name": e.name, "tier": e.tier, "status": e.status} for e in entities]

    # 近期活动（从审计日志取最近10条）
    recent = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
    activities = []
    for a in recent:
        activities.append({
            "id": a.id,
            "type": a.action,
            "title": f"{a.action} {a.target_type}: {a.target_name}",
            "description": f"由 {a.user_name or '系统'} 操作",
            "time": a.timestamp.strftime("%Y-%m-%d %H:%M") if a.timestamp else "",
        })

    return {
        "entity_count": entity_count,
        "relation_count": relation_count,
        "rule_count": rule_count,
        "active_rule_count": active_rules,
        "tier_distribution": tier_dist,
        "health_status": health,
        "recent_activities": activities,
    }
