from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    OntologyEntity, EntityAttribute, EntityRelation,
    BusinessRule, EntityAction, AuditLog,
)
from app.models.datasource import DataSource


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stats(self) -> dict:
        entity_count = self.db.query(func.count(OntologyEntity.id)).scalar() or 0
        relation_count = self.db.query(func.count(EntityRelation.id)).scalar() or 0
        rule_count = self.db.query(func.count(BusinessRule.id)).scalar() or 0
        active_rules = self.db.query(func.count(BusinessRule.id)).filter(BusinessRule.status == "active").scalar() or 0
        action_count = self.db.query(func.count(EntityAction.id)).scalar() or 0
        attr_count = self.db.query(func.count(EntityAttribute.id)).scalar() or 0
        ds_count = self.db.query(func.count(DataSource.id)).scalar() or 0

        tier_dist = []
        for tier, name in [(1, "核心对象"), (2, "领域对象"), (3, "场景对象")]:
            count = self.db.query(func.count(OntologyEntity.id)).filter(OntologyEntity.tier == tier).scalar() or 0
            pct = round(count / entity_count * 100) if entity_count > 0 else 0
            tier_dist.append({"tier": tier, "name": name, "count": count, "pct": pct})

        ns_rows = (
            self.db.query(
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

        rule_priority = []
        for p in ("high", "medium", "low"):
            cnt = self.db.query(func.count(BusinessRule.id)).filter(BusinessRule.priority == p).scalar() or 0
            rule_priority.append({"priority": p, "count": cnt})

        top_rules = (
            self.db.query(BusinessRule)
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

        entities = self.db.query(OntologyEntity).order_by(OntologyEntity.tier, OntologyEntity.name).all()
        health = [{"id": e.id, "name": e.name, "name_cn": e.name_cn, "tier": e.tier, "status": e.status} for e in entities]

        recent = self.db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(15).all()
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

        datasources = self.db.query(DataSource).all()
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
