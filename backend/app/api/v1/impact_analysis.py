"""Impact analysis API — check what depends on a given F/R/A before deletion."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scene import AipScene
from app.models.skill import Skill
from app.models.skill_tool_ref import SkillToolRef
from app.models.version import OntologyVersion
from app.models.version_components import (
    OntologyVersionAction,
    OntologyVersionFunction,
    OntologyVersionRule,
)

router = APIRouter(prefix="/impact-analysis", tags=["impact-analysis"])


def _analyze(db: Session, ref_type: str, source_id: str) -> dict:
    # 1. Find which published versions contain a snapshot of this source
    if ref_type == "function":
        snapshot_ids = [r[0] for r in db.query(OntologyVersionFunction.id).filter(
            OntologyVersionFunction.source_function_id == source_id).all()]
        version_ids = [r[0] for r in db.query(OntologyVersionFunction.version_id).filter(
            OntologyVersionFunction.source_function_id == source_id).distinct().all()]
    elif ref_type == "rule":
        snapshot_ids = [r[0] for r in db.query(OntologyVersionRule.id).filter(
            OntologyVersionRule.source_rule_id == source_id).all()]
        version_ids = [r[0] for r in db.query(OntologyVersionRule.version_id).filter(
            OntologyVersionRule.source_rule_id == source_id).distinct().all()]
    else:
        snapshot_ids = [r[0] for r in db.query(OntologyVersionAction.id).filter(
            OntologyVersionAction.source_action_id == source_id).all()]
        version_ids = [r[0] for r in db.query(OntologyVersionAction.version_id).filter(
            OntologyVersionAction.source_action_id == source_id).distinct().all()]

    # Get version names
    versions = db.query(OntologyVersion).filter(OntologyVersion.id.in_(version_ids)).all() if version_ids else []
    published_versions = [f"v{v.version_number}" for v in versions]

    # 2. Find workflows (AipScene) that reference these snapshots
    referencing_workflows = []
    if snapshot_ids:
        scenes = db.query(AipScene).filter(AipScene.nodes_json.isnot(None)).all()
        snapshot_set = set(snapshot_ids)
        for scene in scenes:
            for node in (scene.nodes_json or []):
                data = node.get("data", {}) if isinstance(node, dict) else {}
                if data.get("ref_id") in snapshot_set:
                    referencing_workflows.append({
                        "id": scene.id, "name": scene.name,
                        "version": scene.ontology_version_id
                    })
                    break

    # 3. Find skills that reference these snapshots
    referencing_skills = []
    if snapshot_ids:
        refs = db.query(SkillToolRef).filter(SkillToolRef.ref_id.in_(snapshot_ids)).all()
        for ref in refs:
            skill = db.query(Skill).filter(Skill.id == ref.skill_id).first()
            if skill:
                referencing_skills.append({
                    "id": skill.id, "name": skill.name, "version": ref.version_id
                })

    return {
        "published_versions": published_versions,
        "referencing_workflows": referencing_workflows,
        "referencing_skills": referencing_skills,
        "safe_to_delete": True,
        "message": "删除草稿源不影响已发布版本的运行，但该组件将不会出现在未来新版本中",
    }


@router.get("/functions/{function_id}")
def function_impact(function_id: str, db: Session = Depends(get_db)):
    return _analyze(db, "function", function_id)


@router.get("/rules/{rule_id}")
def rule_impact(rule_id: str, db: Session = Depends(get_db)):
    return _analyze(db, "rule", rule_id)


@router.get("/actions/{action_id}")
def action_impact(action_id: str, db: Session = Depends(get_db)):
    return _analyze(db, "action", action_id)
