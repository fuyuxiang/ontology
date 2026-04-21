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
    repo = DashboardRepository(db)
    return repo.get_stats()
