"""
Prompt 模板管理 API
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.utils.identifiers import gen_uuid

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


# ── Schemas ──

class TemplateBase(BaseModel):
    name: str
    description: str = ""
    category: str = "通用"
    content: str
    variables: list[dict] | None = None
    tags: list[str] | None = None
    status: str = "active"


class TemplateOut(TemplateBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}




# ── Routes ──

@router.get("", response_model=list[TemplateOut])
def list_templates(
    category: str | None = None,
    status: str | None = "active",
    db: Session = Depends(get_db),
):

    q = db.query(PromptTemplate)
    if category:
        q = q.filter(PromptTemplate.category == category)
    if status:
        q = q.filter(PromptTemplate.status == status)
    return q.order_by(desc(PromptTemplate.created_at)).all()


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    return t


@router.post("", response_model=TemplateOut)
def create_template(body: TemplateBase, db: Session = Depends(get_db)):
    t = PromptTemplate(id=gen_uuid(), **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: str, body: TemplateBase, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(404, "模板不存在")
    db.delete(t)
    db.commit()
    return {"ok": True}
