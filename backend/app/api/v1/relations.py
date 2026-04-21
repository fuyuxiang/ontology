from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EntityRelation
from app.utils.identifiers import gen_uuid
from app.schemas.relation import RelationCreate, RelationOut
from app.repositories import RelationRepository
from app.core.deps import get_current_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/relations", tags=["relations"])


@router.get("", response_model=list[RelationOut])
def list_relations(entity_id: str | None = None, db: Session = Depends(get_db)):
    repo = RelationRepository(db)
    rels = repo.list_by_entity(entity_id)
    result = []
    for r in rels:
        result.append(RelationOut(
            id=r.id,
            from_entity_id=r.from_entity_id,
            from_entity_name=repo.get_entity_name(r.from_entity_id),
            to_entity_id=r.to_entity_id,
            to_entity_name=repo.get_entity_name(r.to_entity_id),
            name=r.name, rel_type=r.rel_type,
            cardinality=r.cardinality, description=r.description,
        ))
    return result


@router.post("", response_model=RelationOut, status_code=201)
def create_relation(
    data: RelationCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = RelationRepository(db)
    f_name = repo.get_entity_name(data.from_entity_id)
    t_name = repo.get_entity_name(data.to_entity_id)
    if not f_name or not t_name:
        raise HTTPException(status_code=400, detail="源实体或目标实体不存在")

    rel = EntityRelation(
        id=gen_uuid(), from_entity_id=data.from_entity_id, to_entity_id=data.to_entity_id,
        name=data.name, rel_type=data.rel_type, cardinality=data.cardinality, description=data.description,
    )
    repo.create(rel)
    write_audit(
        db, user_id=user.id if user else None, user_name=user.name if user else None,
        action="create", target_type="relation", target_id=rel.id, target_name=f"{f_name} -> {t_name}",
    )
    repo.commit()
    return RelationOut(
        id=rel.id, from_entity_id=rel.from_entity_id, from_entity_name=f_name,
        to_entity_id=rel.to_entity_id, to_entity_name=t_name,
        name=rel.name, rel_type=rel.rel_type, cardinality=rel.cardinality, description=rel.description,
    )


@router.delete("/{relation_id}", status_code=204)
def delete_relation(
    relation_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = RelationRepository(db)
    rel = repo.get_by_id(relation_id)
    if not rel:
        raise HTTPException(status_code=404, detail="关系不存在")
    write_audit(
        db, user_id=user.id if user else None, user_name=user.name if user else None,
        action="delete", target_type="relation", target_id=rel.id, target_name=rel.name,
    )
    repo.delete(rel)
    repo.commit()
