from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EntityRelation, OntologyEntity
from app.models.entity import gen_uuid
from app.core.deps import get_current_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/relations", tags=["relations"])


class RelationCreate(BaseModel):
    from_entity_id: str
    to_entity_id: str
    name: str
    rel_type: str = "has_many"
    cardinality: str = "1:N"
    description: str | None = None


class RelationOut(BaseModel):
    id: str
    from_entity_id: str
    from_entity_name: str
    to_entity_id: str
    to_entity_name: str
    name: str
    rel_type: str
    cardinality: str
    description: str | None


@router.get("", response_model=list[RelationOut])
def list_relations(entity_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(EntityRelation)
    if entity_id:
        q = q.filter((EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id))
    rels = q.all()
    result = []
    for r in rels:
        f = db.get(OntologyEntity, r.from_entity_id)
        t = db.get(OntologyEntity, r.to_entity_id)
        result.append(RelationOut(
            id=r.id, from_entity_id=r.from_entity_id, from_entity_name=f.name if f else "",
            to_entity_id=r.to_entity_id, to_entity_name=t.name if t else "",
            name=r.name, rel_type=r.rel_type, cardinality=r.cardinality, description=r.description,
        ))
    return result


@router.post("", response_model=RelationOut, status_code=201)
def create_relation(
    data: RelationCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    f = db.get(OntologyEntity, data.from_entity_id)
    t = db.get(OntologyEntity, data.to_entity_id)
    if not f or not t:
        raise HTTPException(status_code=400, detail="源实体或目标实体不存在")

    rel = EntityRelation(
        id=gen_uuid(), from_entity_id=data.from_entity_id, to_entity_id=data.to_entity_id,
        name=data.name, rel_type=data.rel_type, cardinality=data.cardinality, description=data.description,
    )
    db.add(rel)
    write_audit(
        db, user_id=user.id if user else None, user_name=user.name if user else None,
        action="create", target_type="relation", target_id=rel.id, target_name=f"{f.name} -> {t.name}",
    )
    db.commit()
    return RelationOut(
        id=rel.id, from_entity_id=rel.from_entity_id, from_entity_name=f.name,
        to_entity_id=rel.to_entity_id, to_entity_name=t.name,
        name=rel.name, rel_type=rel.rel_type, cardinality=rel.cardinality, description=rel.description,
    )


@router.delete("/{relation_id}", status_code=204)
def delete_relation(
    relation_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    rel = db.get(EntityRelation, relation_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    write_audit(
        db, user_id=user.id if user else None, user_name=user.name if user else None,
        action="delete", target_type="relation", target_id=rel.id, target_name=rel.name,
    )
    db.delete(rel)
    db.commit()
