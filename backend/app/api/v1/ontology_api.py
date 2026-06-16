"""
本体语义 API — 根据本体 Schema 动态生成查询端点
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EntityRelation, OntologyEntity

router = APIRouter(prefix="/ontology-api", tags=["ontology-api"])


class EndpointParam(BaseModel):
    name: str
    type: str
    required: bool
    description: str


class EndpointInfo(BaseModel):
    method: str
    path: str
    shortPath: str
    description: str
    params: list[EndpointParam] = []


class EndpointGroup(BaseModel):
    entity: str
    entityCn: str
    endpoints: list[EndpointInfo]


class EndpointsResponse(BaseModel):
    groups: list[EndpointGroup]


@router.get("/endpoints", response_model=EndpointsResponse)
def list_endpoints(db: Session = Depends(get_db)):
    entities = db.query(OntologyEntity).filter(OntologyEntity.status == "published").all()
    groups = []
    for entity in entities:
        eps = [
            EndpointInfo(
                method="GET",
                path=f"/ontology-api/objects/{entity.name}",
                shortPath=f"/{entity.name}",
                description=f"查询 {entity.name_cn} 实例列表",
                params=[
                    EndpointParam(name="limit", type="integer", required=False, description="返回数量限制"),
                    EndpointParam(name="offset", type="integer", required=False, description="偏移量"),
                    EndpointParam(name="filter", type="string", required=False, description="过滤条件 JSON"),
                ],
            ),
            EndpointInfo(
                method="GET",
                path=f"/ontology-api/objects/{entity.name}/{{id}}",
                shortPath=f"/{entity.name}/{{id}}",
                description=f"获取单个 {entity.name_cn} 实例详情",
                params=[
                    EndpointParam(name="id", type="string", required=True, description="实例 ID"),
                ],
            ),
            EndpointInfo(
                method="GET",
                path=f"/ontology-api/objects/{entity.name}/{{id}}/relations",
                shortPath=f"/{entity.name}/{{id}}/relations",
                description=f"遍历 {entity.name_cn} 的关联实体",
                params=[
                    EndpointParam(name="id", type="string", required=True, description="实例 ID"),
                    EndpointParam(name="depth", type="integer", required=False, description="遍历深度 (默认1)"),
                    EndpointParam(name="rel_type", type="string", required=False, description="关系类型过滤"),
                ],
            ),
            EndpointInfo(
                method="POST",
                path=f"/ontology-api/objects/{entity.name}",
                shortPath=f"/{entity.name} [创建]",
                description=f"创建 {entity.name_cn} 实例",
                params=[
                    EndpointParam(name="data", type="object", required=True, description="实例数据 JSON"),
                ],
            ),
        ]
        groups.append(EndpointGroup(entity=entity.name, entityCn=entity.name_cn, endpoints=eps))
    return EndpointsResponse(groups=groups)


class OntologyQueryRequest(BaseModel):
    entity_name: str
    filters: dict | None = None
    relations: list[str] | None = None
    depth: int = 1
    limit: int = 50
    offset: int = 0


@router.post("/query")
def ontology_query(req: OntologyQueryRequest, db: Session = Depends(get_db)):
    entity = db.query(OntologyEntity).filter(OntologyEntity.name == req.entity_name).first()
    if not entity:
        from fastapi import HTTPException
        raise HTTPException(404, f"实体 {req.entity_name} 不存在")

    result = {
        "entity": {"name": entity.name, "name_cn": entity.name_cn, "tier": entity.tier},
        "instances": [],
        "relations": [],
    }

    if req.relations or req.depth > 0:
        rels = db.query(EntityRelation).filter(
            (EntityRelation.from_entity_id == entity.id) | (EntityRelation.to_entity_id == entity.id)
        ).all()
        result["relations"] = [
            {"name": r.name, "rel_type": r.rel_type, "from_entity_id": r.from_entity_id, "to_entity_id": r.to_entity_id, "cardinality": r.cardinality}
            for r in rels
        ]

    return result


class RuleExecuteRequest(BaseModel):
    rule_id: str
    entity_id: str
    context: dict | None = None


@router.post("/execute-rule")
def execute_rule(req: RuleExecuteRequest, db: Session = Depends(get_db)):
    from app.models.rule import BusinessRule
    rule = db.query(BusinessRule).filter(BusinessRule.id == req.rule_id).first()
    if not rule:
        from fastapi import HTTPException
        raise HTTPException(404, "规则不存在")
    return {"rule": rule.name, "entity_id": req.entity_id, "result": "executed", "output": {}}
