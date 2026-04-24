"""
实体解析 API — 将映射后的源数据解析为可用的本体实体实例
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from pydantic import BaseModel
from typing import Any
import logging

from app.database import get_db
from app.models import OntologyEntity, EntityAttribute, EntityRelation, DataSource
from app.services.datasource_utils import execute_readonly_sql, get_connection, get_table_schema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resolution", tags=["resolution"])


# ── Schema ──

class ResolvableEntity(BaseModel):
    entity_id: str
    entity_name: str
    entity_name_cn: str
    tier: int
    attr_count: int
    mapped_count: int
    sources: list[dict]  # [{table_name, datasource_name, datasource_id, field_count}]


class SourceField(BaseModel):
    attribute_id: str
    attribute_name: str
    attribute_type: str
    source_table: str
    source_field: str
    data_status: str


class SourceDataPreview(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    page: int
    page_size: int
    table_name: str
    datasource_name: str


class ResolutionStats(BaseModel):
    entity_id: str
    total_rows: int
    distinct_identifier_rows: int | None
    null_identifier_rows: int | None
    completeness: float  # 0-1


# ── APIs ──

@router.get("/entities", response_model=list[ResolvableEntity])
def list_resolvable_entities(db: Session = Depends(get_db)):
    """列出所有可解析的实体（有已映射属性的实体）"""
    rows = (
        db.query(
            EntityAttribute.entity_id,
            EntityAttribute.source_table,
            func.count().label("field_count"),
        )
        .filter(
            EntityAttribute.source_table.isnot(None),
            EntityAttribute.source_table != "",
        )
        .group_by(EntityAttribute.entity_id, EntityAttribute.source_table)
        .all()
    )

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r.entity_id, []).append({
            "table_name": r.source_table,
            "field_count": r.field_count,
        })

    result: list[ResolvableEntity] = []
    for entity_id, tables in grouped.items():
        entity = db.get(OntologyEntity, entity_id)
        if not entity:
            continue

        # enrich with datasource info
        enriched_sources = []
        for t in tables:
            ds = db.query(DataSource).filter(DataSource.table_name == t["table_name"]).first()
            enriched_sources.append({
                "table_name": t["table_name"],
                "datasource_name": ds.name if ds else "",
                "datasource_id": ds.id if ds else "",
                "field_count": t["field_count"],
            })

        total_attrs = len(entity.attributes)
        mapped_count = sum(s["field_count"] for s in enriched_sources)

        result.append(ResolvableEntity(
            entity_id=entity_id,
            entity_name=entity.name,
            entity_name_cn=entity.name_cn,
            tier=entity.tier,
            attr_count=total_attrs,
            mapped_count=mapped_count,
            sources=enriched_sources,
        ))

    return result


@router.get("/entities/{entity_id}/fields", response_model=list[SourceField])
def get_entity_source_fields(entity_id: str, db: Session = Depends(get_db)):
    """获取实体的所有映射字段信息"""
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    result = []
    for attr in entity.attributes:
        if attr.source_table and attr.source_field:
            result.append(SourceField(
                attribute_id=attr.id,
                attribute_name=attr.name,
                attribute_type=attr.type,
                source_table=attr.source_table,
                source_field=attr.source_field,
                data_status=attr.data_status or "未确认来源",
            ))
    return result


@router.get("/entities/{entity_id}/preview", response_model=SourceDataPreview)
def preview_source_data(
    entity_id: str,
    table_name: str | None = Query(None, description="指定来源表名；不传则选第一个"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=200),
    db: Session = Depends(get_db),
):
    """预览实体映射来源表的实际数据"""
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 找出已映射的源表和字段
    mapped_attrs: list[EntityAttribute] = [
        a for a in entity.attributes if a.source_table and a.source_field
    ]
    if not mapped_attrs:
        raise HTTPException(status_code=400, detail="该实体没有已映射的来源字段")

    # 按 table 分组
    table_fields: dict[str, list[EntityAttribute]] = {}
    for a in mapped_attrs:
        table_fields.setdefault(a.source_table, []).append(a)

    target_table = table_name or next(iter(table_fields.keys()))
    fields = table_fields.get(target_table)
    if not fields:
        raise HTTPException(status_code=400, detail=f"表 {target_table} 没有映射到该实体")

    # 查数据源
    ds = db.query(DataSource).filter(DataSource.table_name == target_table).first()
    if not ds:
        raise HTTPException(status_code=400, detail=f"未找到表 {target_table} 对应的数据源")

    # 查数据
    col_names = [f.source_field for f in fields]
    cols_str = ", ".join(f"`{c}`" for c in col_names)

    count_sql = f"SELECT COUNT(*) FROM `{target_table}`"
    count_result = execute_readonly_sql(ds, count_sql)
    total_rows = count_result["rows"][0][0] if count_result.get("rows") else 0

    offset = (page - 1) * page_size
    data_sql = f"SELECT {cols_str} FROM `{target_table}` LIMIT {page_size} OFFSET {offset}"
    data_result = execute_readonly_sql(ds, data_sql)

    rows = data_result.get("rows", []) if not data_result.get("error") else []

    return SourceDataPreview(
        columns=col_names,
        rows=rows,
        total_rows=total_rows,
        page=page,
        page_size=page_size,
        table_name=target_table,
        datasource_name=ds.name,
    )


@router.get("/entities/{entity_id}/stats", response_model=ResolutionStats)
def get_resolution_stats(
    entity_id: str,
    identifier_field: str | None = Query(None, description="实体标识字段"),
    db: Session = Depends(get_db),
):
    """获取实体解析统计信息"""
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    mapped_attrs = [a for a in entity.attributes if a.source_table and a.source_field]
    if not mapped_attrs:
        raise HTTPException(status_code=400, detail="该实体没有已映射的来源字段")

    # 取第一个 source_table
    table_name = mapped_attrs[0].source_table
    ds = db.query(DataSource).filter(DataSource.table_name == table_name).first()
    if not ds:
        raise HTTPException(status_code=400, detail=f"未找到数据源")

    count_sql = f"SELECT COUNT(*) FROM `{table_name}`"
    count_result = execute_readonly_sql(ds, count_sql)
    total_rows = count_result["rows"][0][0] if count_result.get("rows") else 0

    # 统计已映射字段的完整度
    mapped_field_names = [a.source_field for a in mapped_attrs]
    non_null_count = 0
    distinct_id_rows = None
    null_id_rows = None

    if mapped_field_names:
        null_checks = " + ".join(f"CASE WHEN `{f}` IS NULL OR `{f}` = '' THEN 1 ELSE 0 END" for f in mapped_field_names)
        completeness_sql = f"SELECT COUNT(*) - ({null_checks}) FROM `{table_name}`"
        comp_result = execute_readonly_sql(ds, completeness_sql)
        non_null_cells = comp_result["rows"][0][0] if comp_result.get("rows") else 0
        total_cells = total_rows * len(mapped_field_names)
        completeness = non_null_cells / total_cells if total_cells > 0 else 0
    else:
        completeness = 0

    if identifier_field:
        distinct_sql = f"SELECT COUNT(DISTINCT `{identifier_field}`) FROM `{table_name}`"
        distinct_result = execute_readonly_sql(ds, distinct_sql)
        distinct_id_rows = distinct_result["rows"][0][0] if distinct_result.get("rows") else 0

        null_sql = f"SELECT COUNT(*) FROM `{table_name}` WHERE `{identifier_field}` IS NULL OR `{identifier_field}` = ''"
        null_result = execute_readonly_sql(ds, null_sql)
        null_id_rows = null_result["rows"][0][0] if null_result.get("rows") else 0

    return ResolutionStats(
        entity_id=entity_id,
        total_rows=total_rows,
        distinct_identifier_rows=distinct_id_rows,
        null_identifier_rows=null_id_rows,
        completeness=round(completeness, 4),
    )
