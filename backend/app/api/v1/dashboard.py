from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditLog,
    EntityAction,
    EntityRelation,
    OntologyEntity,
)
from app.models.agent import Agent
from app.models.asset import Asset
from app.models.dashboard_config import DashboardConfig
from app.models.function import OntologyFunction

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DEFAULT_CARDS = [
    {"key": "analytics", "title": "ANALYTICS & WORKFLOWS", "enabled": True,
     "items": [
         {"type": "dynamic", "field": "entity_count", "label": "个实体"},
         {"type": "dynamic", "field": "relation_count", "label": "条关系"},
         {"type": "dynamic", "field": "function_count", "label": "个函数"},
         {"type": "dynamic", "field": "action_count", "label": "个动作"},
     ]},
    {"key": "products", "title": "PRODUCTS & SDKs", "enabled": True,
     "items": [
         {"type": "static", "text": "Ontology Center"},
         {"type": "static", "text": "AI Copilot"},
         {"type": "static", "text": "AIP Workflow"},
         {"type": "static", "text": "API Gateway"},
     ]},
    {"key": "datasources", "title": "DATA SOURCES", "enabled": True,
     "items": [{"type": "datasources", "count": 8}]},
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


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_stats(self):
        db = self.db
        entity_count = db.query(func.count(OntologyEntity.id)).scalar() or 0
        relation_count = db.query(func.count(EntityRelation.id)).scalar() or 0
        action_count = db.query(func.count(EntityAction.id)).scalar() or 0
        function_count = db.query(func.count(OntologyFunction.id)).scalar() or 0
        datasource_count = db.query(func.count(Asset.id)).filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"])).scalar() or 0

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        today_action_executions = db.query(func.count(AuditLog.id)).filter(
            AuditLog.target_type == "action",
            AuditLog.action == "execute",
            AuditLog.timestamp >= today_start,
        ).scalar() or 0

        today_function_calls = db.query(func.count(AuditLog.id)).filter(
            AuditLog.target_type == "function",
            AuditLog.timestamp >= today_start,
        ).scalar() or 0

        agent_count = db.query(func.count(Agent.id)).scalar() or 0
        agent_active = db.query(func.count(Agent.id)).filter(Agent.status == "published").scalar() or 0

        datasources = db.query(Asset).filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"])).limit(8).all()
        recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "action_count": action_count,
            "function_count": function_count,
            "datasource_count": datasource_count,
            "today_action_executions": today_action_executions,
            "today_function_calls": today_function_calls,
            "agent_count": agent_count,
            "agent_active": agent_active,
            "datasources": [
                {"id": d.id, "name": d.name, "type": d.type, "status": d.status}
                for d in datasources
            ],
            "recent_activities": [
                {"id": l.id, "action": l.action, "target_type": l.target_type,
                 "target_name": l.target_name, "user_name": l.user_name,
                 "created_at": l.timestamp.isoformat() if l.timestamp else None}
                for l in recent_logs
            ],
        }


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    repo = DashboardRepository(db)
    return repo.get_stats()
