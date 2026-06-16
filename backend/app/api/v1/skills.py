"""Skills CRUD API"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.skill import Skill
from app.models.skill_tool_ref import SkillToolRef

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str
    description: str | None = ""
    skill_type: str | None = "custom"
    config_json: dict | None = None
    code_ref: str | None = ""


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config_json: dict | None = None
    code_ref: str | None = None
    status: str | None = None


def _skill_out(s: Skill) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "skill_type": s.skill_type,
        "config_json": s.config_json or {},
        "code_ref": s.code_ref,
        "status": s.status,
        "current_version": s.current_version,
        "input_schema": s.input_schema,
        "output_schema": s.output_schema,
        "prompt_template": s.prompt_template or "",
        "tools": s.tools,
        "test_cases": s.test_cases,
        "asset_refs": s.asset_refs,
        "created_by": s.created_by or "",
        "reviewed_by": s.reviewed_by or "",
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
def list_skills(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Skill)
    if status:
        q = q.filter(Skill.status == status)
    else:
        q = q.filter(Skill.status.in_(["active", "draft"]))
    return [_skill_out(s) for s in q.all()]


@router.post("", status_code=201)
def create_skill(body: SkillCreate, db: Session = Depends(get_db)):
    s = Skill(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return _skill_out(s)


@router.get("/{sid}")
def get_skill(sid: str, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    return _skill_out(s)


@router.put("/{sid}")
def update_skill(sid: str, body: SkillUpdate, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return _skill_out(s)


@router.delete("/{sid}")
def delete_skill(sid: str, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    db.delete(s)
    db.commit()
    return {"ok": True}


from app.services.skill_version_service import (
    list_versions,
    rollback_skill,
)


@router.get("/{sid}/versions")
def get_versions(sid: str, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    return list_versions(sid, db)


class RollbackRequest(BaseModel):
    target_version: int


@router.post("/{sid}/rollback")
def rollback(sid: str, body: RollbackRequest, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    try:
        rollback_skill(s, body.target_version, db)
        return _skill_out(s)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{sid}/deprecate")
def deprecate(sid: str, db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Skill not found")
    s.status = "deprecated"
    db.commit()
    return _skill_out(s)


# ---------------------------------------------------------------------------
# SkillToolRef endpoints
# ---------------------------------------------------------------------------

class SkillToolRefCreate(BaseModel):
    version_id: str
    ref_type: str
    ref_id: str
    alias: str
    description: str = ""
    param_override: dict | None = None


@router.get("/{skill_id}/tool-refs")
def list_tool_refs(skill_id: str, db: Session = Depends(get_db)):
    refs = db.query(SkillToolRef).filter(SkillToolRef.skill_id == skill_id).all()
    return [{"id": r.id, "ref_type": r.ref_type, "ref_id": r.ref_id,
             "alias": r.alias, "description": r.description,
             "version_id": r.version_id, "param_override": r.param_override}
            for r in refs]


@router.post("/{skill_id}/tool-refs")
def add_tool_ref(skill_id: str, req: SkillToolRefCreate, db: Session = Depends(get_db)):
    ref = SkillToolRef(
        skill_id=skill_id,
        version_id=req.version_id,
        ref_type=req.ref_type,
        ref_id=req.ref_id,
        alias=req.alias,
        description=req.description,
        param_override=req.param_override,
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id, "alias": ref.alias}


@router.delete("/{skill_id}/tool-refs/{ref_id}")
def remove_tool_ref(skill_id: str, ref_id: str, db: Session = Depends(get_db)):
    ref = db.query(SkillToolRef).filter(
        SkillToolRef.id == ref_id, SkillToolRef.skill_id == skill_id
    ).first()
    if ref:
        db.delete(ref)
        db.commit()
    return {"message": "ok"}
