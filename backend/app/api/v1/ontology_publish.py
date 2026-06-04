"""
本体版本发布 API — 版本管理、一致性校验、审批流程、回滚
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.core.deps import get_current_user
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.relation import EntityRelation
from app.models.version import (
    OntologyVersion, OntologyVersionEntity,
    OntologyVersionAttribute, OntologyVersionRelation,
)
from app.models.user import User
from app.models.scene import AipScene
from app.models.agent import Agent
from app.services.ontology_impact import (
    mark_stale_dependents, compute_breaking_changes,
    find_affected_scenes, find_affected_agents,
)

router = APIRouter(prefix="/ontology-publish", tags=["ontology-publish"])


# ─── Pydantic schemas ───────────────────────────────────────────────

class CreateVersionRequest(BaseModel):
    name: str
    description: str | None = None

class UpdateVersionRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class AddEntitiesRequest(BaseModel):
    entity_ids: list[str]

class RejectRequest(BaseModel):
    reason: str

class ApproveRequest(BaseModel):
    pass


# ─── 版本 CRUD ──────────────────────────────────────────────────────

@router.get("/versions")
def list_versions(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(OntologyVersion).order_by(OntologyVersion.version_number.desc())
    if status:
        q = q.filter(OntologyVersion.status == status)
    versions = q.all()
    return [_version_summary(v, db) for v in versions]


@router.get("/versions/active")
def get_active_version(db: Session = Depends(get_db)):
    v = db.query(OntologyVersion).filter(OntologyVersion.is_active == True).first()
    if not v:
        return None
    return _version_detail(v, db)


@router.get("/versions/{version_id}")
def get_version(version_id: str, db: Session = Depends(get_db)):
    v = db.query(OntologyVersion).filter(OntologyVersion.id == version_id).first()
    if not v:
        raise HTTPException(404, "版本不存在")
    return _version_detail(v, db)


@router.post("/versions")
def create_version(req: CreateVersionRequest, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    max_num = db.query(func.max(OntologyVersion.version_number)).scalar() or 0
    version = OntologyVersion(
        version_number=max_num + 1,
        name=req.name,
        description=req.description,
        status="draft",
        created_by=user.id if user else None,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return _version_summary(version, db)


@router.put("/versions/{version_id}")
def update_version(version_id: str, req: UpdateVersionRequest, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "draft":
        raise HTTPException(400, "只能编辑草稿状态的版本")
    if req.name is not None:
        v.name = req.name
    if req.description is not None:
        v.description = req.description
    db.commit()
    return _version_summary(v, db)


@router.delete("/versions/{version_id}")
def delete_version(version_id: str, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "draft":
        raise HTTPException(400, "只能删除草稿状态的版本")
    db.delete(v)
    db.commit()
    return {"message": "版本已删除"}


# ─── 实体管理 ────────────────────────────────────────────────────────

@router.post("/versions/{version_id}/entities")
def add_entities(version_id: str, req: AddEntitiesRequest, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "draft":
        raise HTTPException(400, "只能在草稿状态添加实体")

    existing_source_ids = {ve.source_entity_id for ve in v.entities}
    added = []

    for eid in req.entity_ids:
        if eid in existing_source_ids:
            continue
        entity = db.query(OntologyEntity).options(
            joinedload(OntologyEntity.attributes)
        ).filter(OntologyEntity.id == eid).first()
        if not entity:
            continue

        ve = OntologyVersionEntity(
            version_id=v.id,
            source_entity_id=entity.id,
            name=entity.name,
            name_cn=entity.name_cn,
            tier=entity.tier,
            description=entity.description,
            config_json=entity.config_json,
            publish_config=entity.publish_config,
        )
        db.add(ve)
        db.flush()

        for attr in entity.attributes:
            va = OntologyVersionAttribute(
                version_entity_id=ve.id,
                source_attribute_id=attr.id,
                name=attr.name,
                type=attr.type,
                description=attr.description or "",
                required=attr.required,
                example=attr.example,
                constraints_json=attr.constraints_json,
                source_table=attr.source_table,
                source_field=attr.source_field,
                data_status=attr.data_status or "未确认来源",
            )
            db.add(va)

        added.append(eid)
        existing_source_ids.add(eid)

    _sync_relations(v, db)
    db.commit()
    return {"added": len(added), "total": len(v.entities)}


@router.delete("/versions/{version_id}/entities/{entity_id}")
def remove_entity(version_id: str, entity_id: str, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "draft":
        raise HTTPException(400, "只能在草稿状态移除实体")

    ve = db.query(OntologyVersionEntity).filter(
        OntologyVersionEntity.version_id == v.id,
        OntologyVersionEntity.source_entity_id == entity_id,
    ).first()
    if not ve:
        raise HTTPException(404, "该实体不在此版本中")

    db.delete(ve)
    _sync_relations(v, db)
    db.commit()
    return {"message": "实体已移除"}


# ─── 一致性检查 ──────────────────────────────────────────────────────

@router.get("/versions/{version_id}/check")
def consistency_check(version_id: str, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    source_ids = {ve.source_entity_id for ve in v.entities}

    entity_issues = []
    relation_issues = []

    for ve in v.entities:
        readiness = _check_readiness_for_version_entity(ve)
        if readiness["issues"]:
            entity_issues.append({
                "entity_id": ve.source_entity_id,
                "entity_name": ve.name_cn,
                "issues": readiness["issues"],
            })

    all_relations = db.query(EntityRelation).filter(
        (EntityRelation.from_entity_id.in_(source_ids)) |
        (EntityRelation.to_entity_id.in_(source_ids))
    ).all()

    for rel in all_relations:
        from_in = rel.from_entity_id in source_ids
        to_in = rel.to_entity_id in source_ids
        if from_in and not to_in:
            to_entity = db.query(OntologyEntity).filter(OntologyEntity.id == rel.to_entity_id).first()
            relation_issues.append({
                "relation_name": rel.name,
                "from_entity": rel.from_entity_id,
                "to_entity": rel.to_entity_id,
                "to_entity_name": to_entity.name_cn if to_entity else "未知",
                "issue": f"关系 \"{rel.name}\" 的目标实体 \"{to_entity.name_cn if to_entity else '未知'}\" 未包含在版本中",
            })
        elif to_in and not from_in:
            from_entity = db.query(OntologyEntity).filter(OntologyEntity.id == rel.from_entity_id).first()
            relation_issues.append({
                "relation_name": rel.name,
                "from_entity": rel.from_entity_id,
                "to_entity": rel.to_entity_id,
                "from_entity_name": from_entity.name_cn if from_entity else "未知",
                "issue": f"关系 \"{rel.name}\" 的来源实体 \"{from_entity.name_cn if from_entity else '未知'}\" 未包含在版本中",
            })

    passed = len(entity_issues) == 0 and len(relation_issues) == 0
    summary = "所有检查通过" if passed else f"{len(entity_issues)} 个实体问题, {len(relation_issues)} 个关系问题"

    return {
        "passed": passed,
        "entity_issues": entity_issues,
        "relation_issues": relation_issues,
        "summary": summary,
    }


# ─── 影响面预览 ──────────────────────────────────────────────────────

@router.get("/versions/{version_id}/impact")
def preview_impact(version_id: str, db: Session = Depends(get_db)):
    """预览某版本发布后的影响面（不执行实际标记）"""
    v = _get_version(version_id, db)

    old_active = db.query(OntologyVersion).filter(
        OntologyVersion.is_active == True, OntologyVersion.id != v.id
    ).first()

    old_entities = []
    if old_active:
        old_ve = db.query(OntologyVersionEntity).filter(
            OntologyVersionEntity.version_id == old_active.id
        ).all()
        old_entities = [
            {"source_entity_id": ve.source_entity_id, "name": ve.name}
            for ve in old_ve
        ]

    new_entities = [
        {"source_entity_id": ve.source_entity_id, "name": ve.name}
        for ve in v.entities
    ]

    changes = compute_breaking_changes(old_entities, new_entities)
    if not changes:
        return {"breaking_changes": [], "affected_scenes": [], "affected_agents": []}

    scenes = db.query(AipScene).filter(AipScene.ontology_bindings.isnot(None)).all()
    scene_dicts = [{"id": s.id, "ontology_bindings": s.ontology_bindings, "name": s.name} for s in scenes]
    affected_scene_ids = set(find_affected_scenes(scene_dicts, changes))
    affected_scenes_info = [{"id": s.id, "name": s.name} for s in scenes if s.id in affected_scene_ids]

    agents = db.query(Agent).filter(Agent.entity_ids.isnot(None)).all()
    agent_dicts = [{"id": a.id, "entity_ids": a.entity_ids, "name": a.name} for a in agents]
    affected_agent_ids = set(find_affected_agents(agent_dicts, changes))
    affected_agents_info = [{"id": a.id, "name": a.name} for a in agents if a.id in affected_agent_ids]

    return {
        "breaking_changes": changes,
        "affected_scenes": affected_scenes_info,
        "affected_agents": affected_agents_info,
    }


# ─── 审批流程 ────────────────────────────────────────────────────────

@router.post("/versions/{version_id}/submit")
def submit_for_approval(version_id: str, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "draft":
        raise HTTPException(400, "只有草稿状态可以提交审批")
    if not v.entities:
        raise HTTPException(400, "版本中没有实体，无法提交")

    check = consistency_check(version_id, db)
    if not check["passed"]:
        raise HTTPException(400, f"一致性检查未通过: {check['summary']}")

    v.status = "pending_approval"
    v.submitted_at = datetime.utcnow()
    db.commit()
    return {"message": "已提交审批", "status": "pending_approval"}


@router.post("/versions/{version_id}/approve")
def approve_version(version_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    v = _get_version(version_id, db)
    if v.status != "pending_approval":
        raise HTTPException(400, "只有待审批状态可以通过")

    old_active = db.query(OntologyVersion).filter(
        OntologyVersion.is_active == True, OntologyVersion.id != v.id
    ).first()

    db.query(OntologyVersion).filter(OntologyVersion.is_active == True).update({"is_active": False})
    v.status = "published"
    v.is_active = True
    v.published_at = datetime.utcnow()
    v.approved_by = user.id if user else None

    published_entity_ids = [ve.source_entity_id for ve in v.entities]
    if published_entity_ids:
        db.query(OntologyEntity).filter(
            OntologyEntity.status == "published"
        ).update({"status": "active"})
        db.query(OntologyEntity).filter(
            OntologyEntity.id.in_(published_entity_ids)
        ).update({"status": "published"})

    impact = mark_stale_dependents(old_active, v, db)

    db.commit()
    return {
        "message": f"版本 v{v.version_number} 已发布",
        "status": "published",
        "impact": impact,
    }


@router.post("/versions/{version_id}/reject")
def reject_version(version_id: str, req: RejectRequest, db: Session = Depends(get_db)):
    v = _get_version(version_id, db)
    if v.status != "pending_approval":
        raise HTTPException(400, "只有待审批状态可以驳回")

    v.status = "rejected"
    v.rejected_at = datetime.utcnow()
    v.reject_reason = req.reason
    db.commit()
    return {"message": "版本已驳回", "status": "rejected"}


# ─── 回滚 ────────────────────────────────────────────────────────────

@router.post("/versions/{version_id}/rollback")
def rollback_to_version(version_id: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    target = _get_version(version_id, db)
    if target.status != "published":
        raise HTTPException(400, "只能回滚到已发布的版本")

    max_num = db.query(func.max(OntologyVersion.version_number)).scalar() or 0
    new_version = OntologyVersion(
        version_number=max_num + 1,
        name=f"回滚自 v{target.version_number}",
        description=f"从版本 v{target.version_number} ({target.name}) 回滚",
        status="pending_approval",
        created_by=user.id if user else None,
        submitted_at=datetime.utcnow(),
        rollback_from=target.version_number,
    )
    db.add(new_version)
    db.flush()

    entity_id_map = {}
    for ve in target.entities:
        new_ve = OntologyVersionEntity(
            version_id=new_version.id,
            source_entity_id=ve.source_entity_id,
            name=ve.name,
            name_cn=ve.name_cn,
            tier=ve.tier,
            description=ve.description,
            config_json=ve.config_json,
            publish_config=ve.publish_config,
        )
        db.add(new_ve)
        db.flush()
        entity_id_map[ve.id] = new_ve.id

        for attr in ve.attributes:
            new_attr = OntologyVersionAttribute(
                version_entity_id=new_ve.id,
                source_attribute_id=attr.source_attribute_id,
                name=attr.name,
                type=attr.type,
                description=attr.description,
                required=attr.required,
                example=attr.example,
                constraints_json=attr.constraints_json,
                source_table=attr.source_table,
                source_field=attr.source_field,
                data_status=attr.data_status,
            )
            db.add(new_attr)

    for rel in target.relations:
        new_from = entity_id_map.get(rel.from_version_entity_id)
        new_to = entity_id_map.get(rel.to_version_entity_id)
        if new_from and new_to:
            new_rel = OntologyVersionRelation(
                version_id=new_version.id,
                source_relation_id=rel.source_relation_id,
                from_version_entity_id=new_from,
                to_version_entity_id=new_to,
                name=rel.name,
                rel_type=rel.rel_type,
                cardinality=rel.cardinality,
                acyclic=rel.acyclic,
                description=rel.description,
            )
            db.add(new_rel)

    db.commit()
    db.refresh(new_version)
    return _version_summary(new_version, db)


# ─── 兼容旧接口 ──────────────────────────────────────────────────────

@router.get("/status")
def list_publish_status(db: Session = Depends(get_db)):
    entities = db.query(OntologyEntity).all()
    result = []
    for entity in entities:
        attrs = entity.attributes or []
        total_attrs = len(attrs)
        mapped_attrs = sum(1 for a in attrs if a.source_table and a.source_field)
        has_datasource = mapped_attrs > 0
        mapping_ratio = mapped_attrs / total_attrs if total_attrs > 0 else 0.0
        rels = db.query(EntityRelation).filter(
            (EntityRelation.from_entity_id == entity.id) | (EntityRelation.to_entity_id == entity.id)
        ).count()
        issues = []
        if not has_datasource:
            issues.append("未绑定数据源")
        if total_attrs == 0:
            issues.append("未定义任何属性")
        elif mapping_ratio < 0.5:
            issues.append(f"属性映射不完整（{mapped_attrs}/{total_attrs}）")
        result.append({
            "id": entity.id,
            "name": entity.name,
            "name_cn": entity.name_cn,
            "tier": entity.tier,
            "status": entity.status,
            "publish_config": entity.publish_config,
            "readiness": {
                "has_datasource": has_datasource,
                "mapped_attrs": mapped_attrs,
                "total_attrs": total_attrs,
                "mapping_ratio": round(mapping_ratio, 2),
                "has_relations": rels > 0,
                "issues": issues,
                "ready": len(issues) == 0,
            },
        })
    return result


# ─── 内部工具函数 ────────────────────────────────────────────────────

def _get_version(version_id: str, db: Session) -> OntologyVersion:
    v = db.query(OntologyVersion).options(
        joinedload(OntologyVersion.entities).joinedload(OntologyVersionEntity.attributes),
        joinedload(OntologyVersion.relations),
    ).filter(OntologyVersion.id == version_id).first()
    if not v:
        raise HTTPException(404, "版本不存在")
    return v


def _version_summary(v: OntologyVersion, db: Session) -> dict:
    entity_count = db.query(OntologyVersionEntity).filter(
        OntologyVersionEntity.version_id == v.id
    ).count()
    return {
        "id": v.id,
        "version_number": v.version_number,
        "name": v.name,
        "description": v.description,
        "status": v.status,
        "entity_count": entity_count,
        "created_by": v.created_by,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "submitted_at": v.submitted_at.isoformat() if v.submitted_at else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "is_active": v.is_active,
        "rollback_from": v.rollback_from,
    }


def _version_detail(v: OntologyVersion, db: Session) -> dict:
    entities = db.query(OntologyVersionEntity).filter(
        OntologyVersionEntity.version_id == v.id
    ).all()
    relations = db.query(OntologyVersionRelation).filter(
        OntologyVersionRelation.version_id == v.id
    ).all()

    entity_list = []
    for ve in entities:
        attrs = db.query(OntologyVersionAttribute).filter(
            OntologyVersionAttribute.version_entity_id == ve.id
        ).all()
        total = len(attrs)
        mapped = sum(1 for a in attrs if a.source_table and a.source_field)
        entity_list.append({
            "id": ve.id,
            "source_entity_id": ve.source_entity_id,
            "name": ve.name,
            "name_cn": ve.name_cn,
            "tier": ve.tier,
            "description": ve.description,
            "attribute_count": total,
            "mapped_count": mapped,
            "readiness": _check_readiness_for_version_entity(ve),
        })

    relation_list = [{
        "id": r.id,
        "name": r.name,
        "rel_type": r.rel_type,
        "cardinality": r.cardinality,
        "from_entity_id": r.from_version_entity_id,
        "to_entity_id": r.to_version_entity_id,
    } for r in relations]

    return {
        **_version_summary(v, db),
        "rejected_at": v.rejected_at.isoformat() if v.rejected_at else None,
        "reject_reason": v.reject_reason,
        "approved_by": v.approved_by,
        "entities": entity_list,
        "relations": relation_list,
    }


def _check_readiness_for_version_entity(ve: OntologyVersionEntity) -> dict:
    attrs = ve.attributes or []
    total_attrs = len(attrs)
    mapped_attrs = sum(1 for a in attrs if a.source_table and a.source_field)
    has_datasource = mapped_attrs > 0
    mapping_ratio = mapped_attrs / total_attrs if total_attrs > 0 else 0.0

    issues = []
    if not has_datasource:
        issues.append("未绑定数据源")
    if total_attrs == 0:
        issues.append("未定义任何属性")
    elif mapping_ratio < 0.5:
        issues.append(f"属性映射不完整（{mapped_attrs}/{total_attrs}）")

    return {
        "has_datasource": has_datasource,
        "mapped_attrs": mapped_attrs,
        "total_attrs": total_attrs,
        "mapping_ratio": round(mapping_ratio, 2),
        "issues": issues,
        "ready": len(issues) == 0,
    }


def _sync_relations(v: OntologyVersion, db: Session):
    db.query(OntologyVersionRelation).filter(
        OntologyVersionRelation.version_id == v.id
    ).delete()

    source_id_to_ve = {ve.source_entity_id: ve for ve in v.entities}
    source_ids = set(source_id_to_ve.keys())

    if not source_ids:
        return

    relations = db.query(EntityRelation).filter(
        EntityRelation.from_entity_id.in_(source_ids),
        EntityRelation.to_entity_id.in_(source_ids),
    ).all()

    for rel in relations:
        from_ve = source_id_to_ve[rel.from_entity_id]
        to_ve = source_id_to_ve[rel.to_entity_id]
        vr = OntologyVersionRelation(
            version_id=v.id,
            source_relation_id=rel.id,
            from_version_entity_id=from_ve.id,
            to_version_entity_id=to_ve.id,
            name=rel.name,
            rel_type=rel.rel_type,
            cardinality=rel.cardinality,
            acyclic=rel.acyclic if hasattr(rel, 'acyclic') else False,
            description=rel.description,
        )
        db.add(vr)
