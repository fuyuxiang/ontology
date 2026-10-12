from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.database import get_db
from app.models import OntologyEntity, ScenarioDict, OntologyVersion, OntologySharedRef, OntologyGroup, SharedAttribute
from app.models.user import User
from app.repositories.entity_repo import EntityRepository
from app.schemas.scenario import ScenarioCreate, ScenarioOut, ScenarioUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
def list_scenarios(db: Session = Depends(get_db)):
    scenarios = (
        db.query(ScenarioDict)
        .order_by(ScenarioDict.sort_order, ScenarioDict.created_at)
        .all()
    )
    stats = EntityRepository(db).get_ontology_stats()
    published = {row.ontology_id: row for row in db.query(OntologyVersion).filter(
        OntologyVersion.is_active.is_(True), OntologyVersion.status == "published").all()}
    empty = {"entity_count": 0, "relation_count": 0, "logic_count": 0, "action_count": 0}
    return [
        ScenarioOut.model_validate(sc).model_copy(update={**stats.get(sc.id, empty),
            "active_version_id": published[sc.id].id if sc.id in published else None,
            "version_number": published[sc.id].version_number if sc.id in published else None})
        for sc in scenarios
    ]


@router.post("", response_model=ScenarioOut, status_code=201)
def create_scenario(
    data: ScenarioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    exists = db.query(ScenarioDict).filter(ScenarioDict.code == data.code).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"场景代码 {data.code} 已存在")
    sc = ScenarioDict(
        code=data.code, name=data.name, color=data.color,
        description=data.description, sort_order=data.sort_order,
    )
    db.add(sc)
    db.flush()
    write_audit(
        db, user_id=user.id, user_name=user.name,
        action="create", target_type="scenario", target_id=sc.id, target_name=sc.name,
    )
    db.commit()
    db.refresh(sc)
    return sc


@router.put("/{scenario_id}", response_model=ScenarioOut)
def update_scenario(
    scenario_id: str,
    data: ScenarioUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    sc = db.get(ScenarioDict, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="场景不存在")
    if data.code is not None and data.code != sc.code:
        if db.query(ScenarioDict).filter(ScenarioDict.code == data.code, ScenarioDict.id != sc.id).first():
            raise HTTPException(409, "场景代码已存在")
        old_code = sc.code
        for entity in db.query(OntologyEntity):
            if old_code in (entity.scenario_codes or []):
                entity.scenario_codes = [data.code if code == old_code else code for code in entity.scenario_codes]
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(sc, k, v)
    write_audit(
        db, user_id=user.id, user_name=user.name,
        action="update", target_type="scenario", target_id=sc.id, target_name=sc.name,
    )
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    sc = db.get(ScenarioDict, scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail="场景不存在")
    owned = db.query(OntologyEntity).filter_by(ontology_id=sc.id).count()
    versions = db.query(OntologyVersion).filter_by(ontology_id=sc.id).count()
    if owned or versions:
        raise HTTPException(409, detail={"message": "本体仍包含对象或历史版本，不能删除", "entities": owned, "versions": versions})
    # 引用检查：是否仍被本体对象引用
    referenced = [
        e.name_cn
        for e in db.query(OntologyEntity).all()
        if sc.code in (e.scenario_codes or [])
    ]
    if referenced:
        preview = "、".join(referenced[:5])
        more = f" 等 {len(referenced)} 个对象" if len(referenced) > 5 else ""
        raise HTTPException(
            status_code=400,
            detail=f"场景仍被对象引用（{preview}{more}），请先解除引用后再删除",
        )
    write_audit(
        db, user_id=user.id, user_name=user.name,
        action="delete", target_type="scenario", target_id=sc.id, target_name=sc.name,
    )
    db.query(OntologySharedRef).filter((OntologySharedRef.source_ontology_id == sc.id) | (OntologySharedRef.target_ontology_id == sc.id)).delete(synchronize_session=False)
    db.query(OntologyGroup).filter_by(ontology_id=sc.id).delete()
    db.query(SharedAttribute).filter_by(ontology_id=sc.id).delete()
    db.delete(sc)
    db.commit()
