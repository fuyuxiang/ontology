"""Dependency impact of editing/deleting callable components."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.agent import Agent
from app.models.skill import Skill
from app.models.version import OntologyVersion
from app.models.version_components import OntologyVersionFunction, OntologyVersionAction

router = APIRouter(prefix="/impact-analysis", tags=["impact-analysis"])


def _references(value, target_id, key):
    if isinstance(value, dict):
        if value.get(key) == target_id or (value.get("type") == key.removesuffix("_id") and value.get("id") == target_id):
            return True
        return any(_references(child, target_id, key) for child in value.values())
    if isinstance(value, list):
        return any(_references(child, target_id, key) for child in value)
    return False


def _impact(db, kind, target_id):
    model = OntologyVersionFunction if kind == "function" else OntologyVersionAction
    source = model.source_function_id if kind == "function" else model.source_action_id
    versions = db.query(OntologyVersion).join(model, model.version_id == OntologyVersion.id).filter(source == target_id).all()
    skills = [skill for skill in db.query(Skill).all() if _references(skill.tools, target_id, kind + "_id")]
    agents = [agent for agent in db.query(Agent).all() if _references(agent.tools_config, target_id, kind + "_id") or _references(agent.nodes_json, target_id, kind + "_id")]
    return {"published_versions": [{"id": v.id, "version_number": v.version_number, "name": v.name, "status": v.status} for v in versions],
            "referencing_workflows": [{"id": a.id, "name": a.name} for a in agents],
            "referencing_skills": [{"id": s.id, "name": s.name} for s in skills],
            "safe_to_delete": not (versions or skills or agents)}


@router.get("/functions/{function_id}")
def function_impact(function_id: str, db: Session = Depends(get_db)):
    return _impact(db, "function", function_id)


@router.get("/actions/{action_id}")
def action_impact(action_id: str, db: Session = Depends(get_db)):
    return _impact(db, "action", action_id)
