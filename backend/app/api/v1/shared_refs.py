from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.shared_ref import OntologySharedRef
from app.repositories.entity_repo import EntityRepository
from app.repositories.shared_ref_repo import SharedRefRepository

router = APIRouter(tags=["shared-refs"])


class ShareRequest(BaseModel):
    target_ontology_id: str
    entity_id: str


class SharedRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_ontology_id: str
    target_ontology_id: str
    entity_id: str
    shared_at: str | None = None
    shared_by: str | None = None


@router.post("/ontology/{ontology_id}/share", response_model=SharedRefOut)
async def share_entity(ontology_id: str, body: ShareRequest, db: Session = Depends(get_db)):
    entity_repo = EntityRepository(db)
    entity = entity_repo.get_by_id(body.entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    if entity.ontology_id != ontology_id:
        raise HTTPException(status_code=403, detail="只能共享自己本体的实体")
    if body.target_ontology_id == ontology_id:
        raise HTTPException(status_code=400, detail="不能共享给自己的本体")

    repo = SharedRefRepository(db)
    existing = repo.find_ref(body.target_ontology_id, body.entity_id)
    if existing:
        raise HTTPException(status_code=409, detail="该实体已共享到目标本体")

    ref = OntologySharedRef(
        source_ontology_id=ontology_id,
        target_ontology_id=body.target_ontology_id,
        entity_id=body.entity_id,
    )
    repo.create(ref)
    repo.commit()
    repo.refresh(ref)
    return ref


@router.delete("/ontology/{ontology_id}/share/{ref_id}")
async def unshare_entity(ontology_id: str, ref_id: str, db: Session = Depends(get_db)):
    repo = SharedRefRepository(db)
    ref = repo.get_by_id(ref_id)
    if not ref or ref.source_ontology_id != ontology_id:
        raise HTTPException(status_code=404, detail="共享引用不存在")
    repo.delete(ref)
    repo.commit()
    return {"detail": "已取消共享"}


@router.get("/ontology/{ontology_id}/shared")
async def list_shared(ontology_id: str, direction: str = Query("both"), db: Session = Depends(get_db)):
    repo = SharedRefRepository(db)
    result = {"shared_out": [], "shared_in": []}
    if direction in ("out", "both"):
        result["shared_out"] = [SharedRefOut.model_validate(r) for r in repo.list_by_source(ontology_id)]
    if direction in ("in", "both"):
        result["shared_in"] = [SharedRefOut.model_validate(r) for r in repo.list_by_target(ontology_id)]
    return result
