"""技能版本管理服务"""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.skill_version import SkillVersion

logger = logging.getLogger(__name__)


def publish_skill(skill: Skill, change_log: str, published_by: str, db: Session) -> SkillVersion:
    """Publish current skill state as a new version."""
    new_version = skill.current_version + 1

    snapshot = {
        "name": skill.name,
        "description": skill.description,
        "input_schema": skill.input_schema,
        "output_schema": skill.output_schema,
        "prompt_template": skill.prompt_template,
        "tools": skill.tools,
        "test_cases": skill.test_cases,
        "asset_refs": skill.asset_refs,
    }

    version = SkillVersion(
        skill_id=skill.id,
        version=new_version,
        snapshot=snapshot,
        change_log=change_log,
        published_by=published_by,
    )
    db.add(version)

    skill.current_version = new_version
    skill.status = "active"
    skill.reviewed_by = published_by
    db.commit()
    db.refresh(version)
    return version


def rollback_skill(skill: Skill, target_version: int, db: Session) -> Skill:
    """Rollback skill to a previous version."""
    version = db.query(SkillVersion).filter(
        SkillVersion.skill_id == skill.id,
        SkillVersion.version == target_version,
    ).first()
    if not version:
        raise ValueError(f"Version {target_version} not found")

    snap = version.snapshot
    skill.name = snap["name"]
    skill.description = snap["description"]
    skill.input_schema = snap.get("input_schema")
    skill.output_schema = snap.get("output_schema")
    skill.prompt_template = snap.get("prompt_template", "")
    skill.tools = snap.get("tools")
    skill.test_cases = snap.get("test_cases")
    skill.asset_refs = snap.get("asset_refs")
    skill.current_version = target_version
    skill.status = "active"
    db.commit()
    db.refresh(skill)
    return skill


def list_versions(skill_id: str, db: Session) -> list[dict]:
    """List all versions for a skill."""
    versions = db.query(SkillVersion).filter(
        SkillVersion.skill_id == skill_id
    ).order_by(SkillVersion.version.desc()).all()
    return [
        {
            "id": v.id,
            "version": v.version,
            "change_log": v.change_log,
            "published_by": v.published_by,
            "published_at": v.published_at.isoformat() if v.published_at else None,
        }
        for v in versions
    ]
