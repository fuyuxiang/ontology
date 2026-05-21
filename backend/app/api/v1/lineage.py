"""数据工坊 - 血缘大图 API。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.lineage_seed import (
    ROWS,
    CROSS_EDGES,
    FIELD_LINEAGE,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])


class LineageRowSchema(BaseModel):
    key: str
    source: str  # 多行文本以 \n 分隔
    etl: str
    ontologyId: str
    objectName: str
    ontologyLabel: str
    tier: int
    app: str


class CrossEdgeSchema(BaseModel):
    id: str
    source: str  # 本体节点 ontologyId
    target: str


class WorkshopGraph(BaseModel):
    rows: list[LineageRowSchema]
    crossEdges: list[CrossEdgeSchema] = Field(
        default_factory=list,
        description="本体层之间的横向虚线（业务概念派生）",
    )


class FieldMappingSchema(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    apiName: str
    type: str

    class Config:
        populate_by_name = True


class FieldLineageGroupSchema(BaseModel):
    source: str
    fields: list[FieldMappingSchema]


class FieldLineageResponse(BaseModel):
    ontologyId: str
    objectName: str
    ontologyLabel: str
    groups: list[FieldLineageGroupSchema]


@router.get("/workshop", response_model=WorkshopGraph)
def get_workshop_lineage() -> WorkshopGraph:
    """返回数据工坊血缘大图：行链路 + 本体层横向虚线。"""
    return WorkshopGraph(
        rows=[LineageRowSchema(**r) for r in ROWS],
        crossEdges=[CrossEdgeSchema(**e) for e in CROSS_EDGES],
    )


@router.get("/workshop/objects/{ontology_id}", response_model=FieldLineageResponse)
def get_object_field_lineage(ontology_id: str) -> FieldLineageResponse:
    """返回某个本体对象的字段级血缘（多张源表的字段映射）。"""
    row = next((r for r in ROWS if r["ontologyId"] == ontology_id), None)
    if row is None:
        raise HTTPException(404, f"本体对象 {ontology_id} 不存在血缘记录")

    raw_groups = FIELD_LINEAGE.get(ontology_id, [])
    groups = [
        FieldLineageGroupSchema(
            source=g["source"],
            fields=[
                FieldMappingSchema(
                    **{"from": f["from_"], "to": f["to"], "apiName": f["apiName"], "type": f["type"]}
                )
                for f in g["fields"]
            ],
        )
        for g in raw_groups
    ]

    return FieldLineageResponse(
        ontologyId=ontology_id,
        objectName=row["objectName"],
        ontologyLabel=row["ontologyLabel"],
        groups=groups,
    )
