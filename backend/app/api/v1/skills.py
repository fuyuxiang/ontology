"""Skills CRUD API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.skill import Skill

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    skill_type: Optional[str] = "custom"
    config_json: Optional[dict] = None
    code_ref: Optional[str] = ""


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config_json: Optional[dict] = None
    code_ref: Optional[str] = None
    status: Optional[str] = None


def _skill_out(s: Skill) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "skill_type": s.skill_type,
        "config_json": s.config_json or {},
        "code_ref": s.code_ref,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("")
def list_skills(db: Session = Depends(get_db)):
    return [_skill_out(s) for s in db.query(Skill).filter(Skill.status == "active").all()]


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
