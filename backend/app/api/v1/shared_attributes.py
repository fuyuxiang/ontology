from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.shared_attribute import SharedAttribute
from app.repositories.shared_attribute_repo import SharedAttributeRepository

router = APIRouter(tags=["shared-attributes"])


class SharedAttrCreate(BaseModel):
    ontology_id: str
    name: str
    name_cn: str | None = None
    data_type: str
    description: str | None = None
    config_json: dict | None = None


class SharedAttrUpdate(BaseModel):
    name: str | None = None
    name_cn: str | None = None
    data_type: str | None = None
    description: str | None = None
    config_json: dict | None = None


class SharedAttrOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ontology_id: str
    name: str
    name_cn: str | None = None
    data_type: str
    description: str | None = None
    config_json: dict | None = None


@router.get("/shared-attributes", response_model=list[SharedAttrOut])
async def list_shared_attributes(ontology_id: str, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    return repo.list_by_ontology(ontology_id)


@router.post("/shared-attributes", response_model=SharedAttrOut)
async def create_shared_attribute(body: SharedAttrCreate, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    if repo.find_by_name(body.ontology_id, body.name):
        raise HTTPException(status_code=409, detail="该本体下已存在同名共享属性")
    attr = SharedAttribute(**body.model_dump())
    repo.create(attr)
    repo.commit()
    repo.refresh(attr)
    return attr


@router.put("/shared-attributes/{attr_id}", response_model=SharedAttrOut)
async def update_shared_attribute(attr_id: str, body: SharedAttrUpdate, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    attr = repo.get_by_id(attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="共享属性不存在")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(attr, key, val)
    repo.commit()
    repo.refresh(attr)
    return attr


@router.delete("/shared-attributes/{attr_id}")
async def delete_shared_attribute(attr_id: str, db: Session = Depends(get_db)):
    repo = SharedAttributeRepository(db)
    attr = repo.get_by_id(attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="共享属性不存在")
    repo.delete(attr)
    repo.commit()
    return {"detail": "已删除"}
