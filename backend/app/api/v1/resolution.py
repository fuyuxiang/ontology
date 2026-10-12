"""Resolve real source instances through the object's authoritative active binding."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors import ConnectorRegistry
from app.database import get_db
from app.models import EntityAttribute, OntologyEntity
from app.models.asset import Asset
from app.models.connection import Connection
from app.models.object_binding import ObjectBinding
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService

router = APIRouter(prefix="/resolution", tags=["resolution"])


class ResolvableEntity(BaseModel):
    entity_id: str
    ontology_id: str | None = None
    entity_name: str
    entity_name_cn: str
    tier: int
    attr_count: int
    mapped_count: int
    sources: list[dict]


class SourceField(BaseModel):
    attribute_id: str
    attribute_name: str
    attribute_type: str
    source_table: str
    source_field: str
    data_status: str
    asset_id: str


class SourceDataPreview(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int
    page: int
    page_size: int
    table_name: str
    datasource_name: str
    asset_id: str


class ResolutionStats(BaseModel):
    entity_id: str
    asset_id: str
    total_rows: int
    distinct_identifier_rows: int | None
    null_identifier_rows: int | None
    completeness: float


def _bindings(db, entity_id):
    return db.query(ObjectBinding, Asset).join(Asset, Asset.id == ObjectBinding.asset_id).filter(
        ObjectBinding.object_type_id == entity_id, ObjectBinding.status == "active", Asset.status == "active",
        ObjectBinding.role.in_(["primary", "enrichment"])).all()


def _mapped(db, entity_id, binding):
    attrs = {attr.id: attr for attr in db.query(EntityAttribute).filter_by(entity_id=entity_id)}
    return [(attrs[m["attribute_id"]], m["source_column"]) for m in binding.field_mappings or []
            if m.get("attribute_id") in attrs and m.get("source_column")]


def _source(db, entity_id, *, asset_id=None, table_name=None):
    if not db.get(OntologyEntity, entity_id):
        raise HTTPException(404, "实体不存在")
    matches = [(b, a) for b, a in _bindings(db, entity_id)
               if (not asset_id or a.id == asset_id) and (not table_name or (a.locator or {}).get("table") == table_name)]
    if not matches:
        raise HTTPException(400, "实体没有匹配的活动数据绑定")
    if not asset_id and not table_name:
        matches = [(b, a) for b, a in matches if b.role == "primary"] or matches
    if len(matches) != 1:
        raise HTTPException(409, "实体有多个匹配来源，请指定 asset_id")
    binding, asset = matches[0]
    connection = db.get(Connection, asset.connection_id)
    if not connection or not connection.enabled:
        raise HTTPException(409, "绑定的连接不可用")
    mapped = _mapped(db, entity_id, binding)
    if not mapped:
        raise HTTPException(400, "绑定没有可解析的映射字段")
    quote = ConnectorRegistry.get(connection.type).quote_identifier()
    def quoted(name):
        return quote + name.replace(quote, quote + quote) + quote
    source = "<asset>" if asset.kind == "table" else f"({asset.locator['sql']}) AS _resolution"
    where = f" WHERE ({binding.filter_expr})" if binding.filter_expr else ""
    return binding, asset, connection, mapped, quoted, source, where


def _query(db, asset_id, sql):
    try:
        return ExecuteService(db).execute(ExecuteRequest(asset_id=asset_id, sql=sql,
            purpose="resolution.query", bypass_cache=True))
    except Exception as exc:
        raise HTTPException(400, f"实体来源查询失败：{exc}") from exc


@router.get("/entities", response_model=list[ResolvableEntity])
def list_resolvable_entities(ontology_id: str | None = None, db: Session = Depends(get_db)):
    entities = db.query(OntologyEntity)
    if ontology_id:
        entities = entities.filter_by(ontology_id=ontology_id)
    result = []
    for entity in entities:
        sources, mapped_ids = [], set()
        for binding, asset in _bindings(db, entity.id):
            fields = _mapped(db, entity.id, binding)
            mapped_ids.update(attr.id for attr, _ in fields)
            sources.append({"asset_id": asset.id, "table_name": (asset.locator or {}).get("table", asset.name),
                            "datasource_name": asset.name, "datasource_id": asset.id, "field_count": len(fields)})
        if sources:
            result.append(ResolvableEntity(entity_id=entity.id, ontology_id=entity.ontology_id, entity_name=entity.name,
                entity_name_cn=entity.name_cn, tier=entity.tier, attr_count=len(entity.attributes),
                mapped_count=len(mapped_ids), sources=sources))
    return result


@router.get("/entities/{entity_id}/fields", response_model=list[SourceField])
def get_entity_source_fields(entity_id: str, db: Session = Depends(get_db)):
    if not db.get(OntologyEntity, entity_id):
        raise HTTPException(404, "实体不存在")
    return [SourceField(attribute_id=attr.id, attribute_name=attr.name, attribute_type=attr.type,
                source_table=(asset.locator or {}).get("table", asset.name), source_field=column,
                asset_id=asset.id, data_status="已确认来源")
            for binding, asset in _bindings(db, entity_id) for attr, column in _mapped(db, entity_id, binding)]


@router.get("/entities/{entity_id}/preview", response_model=SourceDataPreview)
def preview_source_data(entity_id: str, table_name: str | None = Query(None), asset_id: str | None = Query(None),
                        page: int = Query(1, ge=1), page_size: int = Query(20, ge=5, le=200),
                        db: Session = Depends(get_db)):
    binding, asset, connection, mapped, quoted, source, where = _source(db, entity_id, asset_id=asset_id, table_name=table_name)
    count = _query(db, asset.id, f"SELECT COUNT(*) FROM {source}{where}")
    sql = f"SELECT {', '.join(quoted(column) for _, column in mapped)} FROM {source}{where}"
    offset = (page - 1) * page_size
    if connection.type in ("oracle", "sqlserver"):
        sql += f" ORDER BY 1 OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"
    else:
        sql += f" LIMIT {page_size} OFFSET {offset}"
    result = _query(db, asset.id, sql)
    return SourceDataPreview(columns=[column for _, column in mapped], rows=result.rows,
        total_rows=count.rows[0][0], page=page, page_size=page_size, asset_id=asset.id,
        table_name=(asset.locator or {}).get("table", asset.name), datasource_name=asset.name)


@router.get("/entities/{entity_id}/stats", response_model=ResolutionStats)
def get_resolution_stats(entity_id: str, identifier_field: str | None = Query(None), asset_id: str | None = Query(None),
                         db: Session = Depends(get_db)):
    binding, asset, connection, mapped, quoted, source, where = _source(db, entity_id, asset_id=asset_id)
    column_types = {column["name"]: column.get("type", "") for column in asset.schema_snapshot or []}
    def missing(column):
        q = quoted(column)
        return f"{q} IS NULL" + (f" OR {q} = ''" if any(t in column_types.get(column, "").lower() for t in ("char", "text", "clob")) else "")
    valid_columns = {column for _, column in mapped}
    names = {attr.name: column for attr, column in mapped}
    identifier = names.get(identifier_field, identifier_field) if identifier_field else binding.id_column
    if identifier and identifier not in valid_columns:
        raise HTTPException(400, "标识字段必须属于当前绑定的已映射属性")
    complete_cells = " + ".join(f"SUM(CASE WHEN {missing(column)} THEN 0 ELSE 1 END)" for _, column in mapped)
    expressions = f"COUNT(*), {complete_cells}"
    if identifier:
        expressions += f", COUNT(DISTINCT {quoted(identifier)}), SUM(CASE WHEN {missing(identifier)} THEN 1 ELSE 0 END)"
    result = _query(db, asset.id, f"SELECT {expressions} FROM {source}{where}").rows[0]
    total, cells = int(result[0]), result[1] or 0
    return ResolutionStats(entity_id=entity_id, asset_id=asset.id, total_rows=total,
        distinct_identifier_rows=int(result[2]) if identifier else None,
        null_identifier_rows=int(result[3] or 0) if identifier else None,
        completeness=round(cells / (total * len(mapped)), 4) if total else 0)
