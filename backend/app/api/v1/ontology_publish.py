"""
本体发布 API — 就绪检查、能力配置、发布/取消发布
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entity import OntologyEntity, EntityAttribute
from app.models import EntityRelation

router = APIRouter(prefix="/ontology-publish", tags=["ontology-publish"])


class ReadinessCheck(BaseModel):
    has_datasource: bool
    mapped_attrs: int
    total_attrs: int
    mapping_ratio: float
    has_relations: bool
    issues: list[str]
    ready: bool


class PublishConfig(BaseModel):
    capabilities: list[str] = ["query", "relations"]
    access_level: str = "api_key"


class EntityPublishStatus(BaseModel):
    id: str
    name: str
    name_cn: str
    tier: int
    status: str
    publish_config: dict | None
    readiness: ReadinessCheck


class PublishRequest(BaseModel):
    entity_id: str
    config: PublishConfig


@router.get("/status")
def list_publish_status(db: Session = Depends(get_db)):
    entities = db.query(OntologyEntity).all()
    result = []
    for entity in entities:
        readiness = _check_readiness(entity, db)
        result.append({
            "id": entity.id,
            "name": entity.name,
            "name_cn": entity.name_cn,
            "tier": entity.tier,
            "status": entity.status,
            "publish_config": entity.publish_config,
            "readiness": readiness,
        })
    return result


@router.get("/status/{entity_id}")
def get_publish_status(entity_id: str, db: Session = Depends(get_db)):
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(404, "实体不存在")
    readiness = _check_readiness(entity, db)
    return {
        "id": entity.id,
        "name": entity.name,
        "name_cn": entity.name_cn,
        "tier": entity.tier,
        "status": entity.status,
        "publish_config": entity.publish_config,
        "readiness": readiness,
    }


@router.post("/publish")
def publish_entity(req: PublishRequest, db: Session = Depends(get_db)):
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == req.entity_id).first()
    if not entity:
        raise HTTPException(404, "实体不存在")

    readiness = _check_readiness(entity, db)
    if not readiness["ready"]:
        raise HTTPException(400, f"实体未就绪: {'; '.join(readiness['issues'])}")

    entity.status = "published"
    entity.publish_config = {
        "capabilities": req.config.capabilities,
        "access_level": req.config.access_level,
        "published_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    db.commit()
    return {"message": f"实体 {entity.name_cn} 已发布", "status": "published"}


@router.post("/unpublish/{entity_id}")
def unpublish_entity(entity_id: str, db: Session = Depends(get_db)):
    entity = db.query(OntologyEntity).filter(OntologyEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(404, "实体不存在")
    entity.status = "active"
    entity.publish_config = None
    db.commit()
    return {"message": f"实体 {entity.name_cn} 已取消发布", "status": "active"}


def _check_readiness(entity: OntologyEntity, db: Session) -> dict:
    issues = []
    attrs = entity.attributes or []
    total_attrs = len(attrs)
    mapped_attrs = sum(1 for a in attrs if a.source_table and a.source_field)
    has_datasource = mapped_attrs > 0
    mapping_ratio = mapped_attrs / total_attrs if total_attrs > 0 else 0.0

    rels = db.query(EntityRelation).filter(
        (EntityRelation.from_entity_id == entity.id) | (EntityRelation.to_entity_id == entity.id)
    ).count()
    has_relations = rels > 0

    if not has_datasource:
        issues.append("未绑定数据源（无属性完成字段映射）")
    if total_attrs == 0:
        issues.append("未定义任何属性")
    elif mapping_ratio < 0.5:
        issues.append(f"属性映射不完整（{mapped_attrs}/{total_attrs}，低于50%）")

    ready = len(issues) == 0

    return {
        "has_datasource": has_datasource,
        "mapped_attrs": mapped_attrs,
        "total_attrs": total_attrs,
        "mapping_ratio": round(mapping_ratio, 2),
        "has_relations": has_relations,
        "issues": issues,
        "ready": ready,
    }
