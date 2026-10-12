import json as _json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import require_user
from app.database import get_db
from app.models import EntityAttribute, EntityRelation, OntologyEntity, ScenarioDict, OntologyGroup, SharedAttribute
from app.models.object_binding import ObjectBinding
from app.models.quality_rule import QualityRule
from app.models.user import User
from app.repositories import EntityRepository
from app.schemas.entity import (
    ActionOut,
    AttributeBase,
    AttributeMappingUpdate,
    AttributeOut,
    EntityCreate,
    EntityDetail,
    EntityListItem,
    EntityUpdate,
    FileImportResult,
    FromDatasourceRequest,
    FunctionBriefOut,
    GraphData,
    GraphEdge,
    GraphNode,
    OntologyPreviewResult,
    RelationOut,
)
from app.services.audit import write_audit
from app.utils.identifiers import gen_uuid
from app.services.copilot import get_llm_client

router = APIRouter(prefix="/entities", tags=["entities"])


def _get_rule_counts(db: Session, entity_ids: list[str]) -> dict[str, int]:
    if not entity_ids:
        return {}
    rows = (
        db.query(
            ObjectBinding.object_type_id,
            func.count(func.distinct(QualityRule.id)),
        )
        .join(QualityRule, QualityRule.asset_id == ObjectBinding.asset_id)
        .filter(
            ObjectBinding.object_type_id.in_(entity_ids),
            ObjectBinding.status == "active",
            QualityRule.enabled.is_(True),
        )
        .group_by(ObjectBinding.object_type_id)
        .all()
    )
    return {entity_id: count for entity_id, count in rows}


@router.get("", response_model=list[EntityListItem])
def list_entities(
    tier: int | None = None,
    status: str | None = None,
    search: str | None = None,
    namespace: str | None = None,
    ontology_id: str | None = None,
    db: Session = Depends(get_db),
):
    repo = EntityRepository(db)
    entities = repo.list_with_filters(
        tier=tier, status=status, search=search, namespace=namespace, ontology_id=ontology_id
    )

    # 标记共享实体
    shared_ids = repo.get_shared_entity_ids(ontology_id) if ontology_id else set()

    entity_ids = [e.id for e in entities]
    rel_counts = repo.get_relation_counts(entity_ids)
    rule_counts = _get_rule_counts(db, entity_ids)

    result = []
    for e in entities:
        result.append(EntityListItem(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status,
            attr_count=len(e.attributes),
            relation_count=rel_counts.get(e.id, 0),
            function_count=len(e.functions),
            action_count=len(e.actions),
            rule_count=rule_counts.get(e.id, 0),
            datasource_name=(e.config_json or {}).get("datasource_name"),
            scenario_codes=e.scenario_codes,
            is_shared=e.id in shared_ids,
        ))
    return result


@router.get("/data-layer")
def get_data_layer(ontology_id: str | None = None, db: Session = Depends(get_db)):
    from app.models.asset import Asset
    query = db.query(ObjectBinding, OntologyEntity, Asset).join(
        OntologyEntity, ObjectBinding.object_type_id == OntologyEntity.id).join(
        Asset, ObjectBinding.asset_id == Asset.id).filter(ObjectBinding.status == "active")
    if ontology_id:
        query = query.filter(OntologyEntity.ontology_id == ontology_id)
    result = []
    for binding, e, asset in query.all():
        result.append({
            'entity_id': e.id,
            'entity_name_cn': e.name_cn,
            'asset_id': asset.id,
            'binding_id': binding.id,
            'table_name': (asset.locator or {}).get('table', ''),
            'field_count': len(binding.field_mappings or []),
            'record_count': (asset.profile or {}).get('row_count', 0),
            'datasource_name': asset.name,
        })
    return result


@router.get("/graph", response_model=GraphData)
def get_full_graph(db: Session = Depends(get_db)):
    repo = EntityRepository(db)
    entities = repo.list_with_filters()
    relations = repo.get_all_relations()
    rule_counts = _get_rule_counts(db, [e.id for e in entities])

    nodes = []
    for e in entities:
        rc = sum(1 for r in relations if r.from_entity_id == e.id or r.to_entity_id == e.id)
        nodes.append(GraphNode(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status, relation_count=rc,
            action_count=len(e.actions),
            rule_count=rule_counts.get(e.id, 0),
            function_count=len(e.functions),
        ))

    edges = []
    entity_map = {e.id: e for e in entities}
    for r in relations:
        f = entity_map.get(r.from_entity_id)
        t = entity_map.get(r.to_entity_id)
        if f and t:
            edges.append(GraphEdge(
                from_id=f.id, from_name=f.name_cn,
                to_id=t.id, to_name=t.name_cn,
                label=r.name, cardinality=r.cardinality,
            ))

    return GraphData(nodes=nodes, edges=edges)


@router.get("/{entity_id}/lineage", response_model=GraphData)
def get_entity_lineage(
    entity_id: str,
    depth: int = Query(default=2, ge=1, le=5),
    db: Session = Depends(get_db),
):
    """BFS traversal to get N-hop neighborhood of an entity."""
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    visited_ids: set[str] = set()
    frontier: set[str] = {entity_id}
    collected_rels: list[EntityRelation] = []

    for _ in range(depth):
        if not frontier:
            break
        rels = db.query(EntityRelation).filter(
            (EntityRelation.from_entity_id.in_(frontier)) |
            (EntityRelation.to_entity_id.in_(frontier))
        ).all()
        visited_ids.update(frontier)
        next_frontier: set[str] = set()
        for r in rels:
            if r not in collected_rels:
                collected_rels.append(r)
            if r.from_entity_id not in visited_ids:
                next_frontier.add(r.from_entity_id)
            if r.to_entity_id not in visited_ids:
                next_frontier.add(r.to_entity_id)
        frontier = next_frontier

    visited_ids.update(frontier)
    all_entities = db.query(OntologyEntity).filter(OntologyEntity.id.in_(visited_ids)).all()
    entity_map = {e.id: e for e in all_entities}

    nodes = []
    for e in all_entities:
        rc = sum(1 for r in collected_rels if r.from_entity_id == e.id or r.to_entity_id == e.id)
        nodes.append(GraphNode(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status, relation_count=rc,
        ))

    edges = []
    for r in collected_rels:
        f = entity_map.get(r.from_entity_id)
        t = entity_map.get(r.to_entity_id)
        if f and t:
            edges.append(GraphEdge(
                from_id=f.id, from_name=f.name_cn,
                to_id=t.id, to_name=t.name_cn,
                label=r.name, cardinality=r.cardinality,
            ))

    return GraphData(nodes=nodes, edges=edges)


# ── DB 类型 → 本体类型映射 ──
_TYPE_MAP = {
    "varchar": "string", "char": "string", "text": "string", "longtext": "string",
    "mediumtext": "string", "tinytext": "string", "nvarchar": "string", "nchar": "string",
    "int": "number", "integer": "number", "bigint": "number", "smallint": "number",
    "tinyint": "number", "float": "number", "double": "number", "decimal": "number",
    "numeric": "number", "real": "number", "number": "number",
    "boolean": "boolean", "bool": "boolean", "bit": "boolean",
    "date": "date", "datetime": "date", "timestamp": "date", "datetime2": "date",
    "timestamp without time zone": "date", "timestamp with time zone": "date",
    "json": "json", "jsonb": "json",
}


def _map_db_type(db_type: str) -> str:
    t = db_type.lower().split("(")[0].strip()
    return _TYPE_MAP.get(t, "string")


@router.post("/from-datasource", response_model=EntityDetail, status_code=201)
def create_from_datasource(
    body: FromDatasourceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    from app.models.asset import Asset
    asset = db.get(Asset, body.datasource_id)
    if not asset:
        raise HTTPException(404, "资产不存在")
    if (asset.locator or {}).get("table") != body.table_name:
        raise HTTPException(422, "table_name 必须与所选资产一致")
    return create_from_asset(FromAssetRequest(
        asset_id=asset.id, name_cn=body.name_cn, tier=body.tier,
        namespace=body.namespace, ontology_id=body.ontology_id,
    ), db, user)


# ── M2: 从 Asset 创建本体（自动落 ObjectBinding）──────────────

class FromAssetRequest(BaseModel):
    ontology_id: str
    asset_id: str
    name_cn: str
    tier: int = 1
    namespace: str = ""


@router.post("/from-asset", response_model=EntityDetail, status_code=201)
def create_from_asset(
    body: FromAssetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """从 Asset（kind=table）创建 OntologyEntity，并自动建立 primary ObjectBinding。

    与老 /entities/from-datasource 的区别：
    - 输入是 asset_id（Asset Catalog 的强类型引用），不再依赖 DataSource.id + table_name
    - 创建后自动写 ObjectBinding，把每个 EntityAttribute 与 Asset.schema_snapshot 的列对应起来
    - binding.created 事件会同步反写 EntityAttribute.source_table/source_field（兼容期）
    """
    from app.models.asset import Asset
    from app.services.data_plane.asset_service import AssetService
    from app.services.data_plane.object_binding_service import ObjectBindingService

    asset = db.get(Asset, body.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.kind != "table":
        raise HTTPException(status_code=400, detail="仅 kind=table 资产支持从中创建本体对象")

    # 确保 schema_snapshot 已就绪
    if not asset.schema_snapshot:
        AssetService(db).sync_schema(asset.id)
        db.refresh(asset)
    columns = asset.schema_snapshot or []
    if not columns:
        raise HTTPException(status_code=400, detail="资产无列信息（请先同步 Schema）")

    if not db.get(ScenarioDict, body.ontology_id):
        raise HTTPException(404, "本体不存在")
    table_name = (asset.locator or {}).get("table") or asset.name
    table_pascal = table_name.replace("_", " ").title().replace(" ", "")
    eid = gen_uuid()

    repo = EntityRepository(db)
    if db.query(OntologyEntity).filter_by(ontology_id=body.ontology_id, name=table_pascal).first():
        raise HTTPException(409, "当前本体内已存在同名实体")

    pk_cols = [c["name"] for c in columns if c.get("is_pk")]
    primary_key = pk_cols[0] if pk_cols else None

    entity = OntologyEntity(
        id=eid,
        ontology_id=body.ontology_id,
        name=table_pascal,
        name_cn=body.name_cn,
        tier=body.tier,
        status="active",
        description=f"从 Asset {asset.name} 自动生成",
        config_json={
            "asset_id": asset.id,
            "asset_alias": asset.alias,
            "table_name": table_name,
            "primary_key": primary_key,
        },
        created_by=user.id,
    )
    db.add(entity)
    field_mappings = []
    for col in columns:
        attr = EntityAttribute(
            entity_id=eid,
            name=col["name"],
            type=_map_db_type(col["type"]),
            description=col.get("comment") or col["name"],
            required=not col.get("nullable", True),
        )
        db.add(attr)
        db.flush()
        field_mappings.append({
            "attribute_id": attr.id,
            "source_column": col["name"],
            "transform": None,
        })

    # 落 ObjectBinding（primary）
    ObjectBindingService(db).create(
        object_type_id=eid,
        asset_id=asset.id,
        role="primary",
        field_mappings=field_mappings,
        id_column=primary_key,
        user_id=user.id,
    )

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="create", target_type="entity",
        target_id=eid, target_name=table_pascal,
        snapshot_after={"source": "asset", "asset_id": asset.id},
    )
    db.commit()
    return get_entity(eid, db)

@router.post("/from-file", response_model=FileImportResult, status_code=201)
async def create_from_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    namespace: str = Form(""),
    ontology_id: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """从文件导入本体：支持 json / owl / ttl 格式。"""
    from app.services.file_import import parse_json_ontology, parse_owl_ontology

    if file_type not in ("json", "owl", "ttl"):
        raise HTTPException(status_code=400, detail="file_type 必须为 json、owl 或 ttl")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    _ontology_id = ontology_id or None
    if _ontology_id and not db.get(ScenarioDict, _ontology_id):
        raise HTTPException(404, "本体不存在")

    try:
        if file_type == "json":
            import json as _json
            data = _json.loads(content.decode("utf-8"))
            from app.core.permissions import has_permission
            from app.schemas.action import ACTION_TYPES
            action_specs = data.get("action_types", data.get("actions", []))
            if any((action.get("action_type") or action.get("type")) in ACTION_TYPES for action in action_specs) and not has_permission(user, "rule:write", db):
                raise HTTPException(403, "导入可执行动作需要 rule:write 权限")
            result = parse_json_ontology(data, namespace, db, ontology_id=_ontology_id)
        elif file_type == "owl":
            result = parse_owl_ontology(content, "xml", db, ontology_id=_ontology_id)
        else:
            result = parse_owl_ontology(content, "turtle", db, ontology_id=_ontology_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}") from e

    if result.errors:
        db.rollback()
        raise HTTPException(422, detail={"message": "导入包含无法解析的引用，未保存任何内容", "errors": result.errors})

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="import", target_type="file",
        target_id=file.filename or "unknown",
        target_name=file.filename or "unknown",
        snapshot_after={
            "file_type": file_type,
            "entities_created": result.entities_created,
            "relations_created": result.relations_created,
        },
    )
    db.commit()

    return FileImportResult(
        entities_created=result.entities_created,
        entities_skipped=result.entities_skipped,
        attributes_created=result.attributes_created,
        relations_created=result.relations_created,
        rules_created=result.rules_created,
        actions_created=result.actions_created,
        errors=result.errors,
        warnings=result.warnings,
    )


@router.post("/preview-file", response_model=OntologyPreviewResult)
async def preview_from_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    namespace: str = Form(""),
):
    """预览本体文件：仅解析为草稿结构，不落库、不写审计。供模版构建使用。

    支持 json（V1.1 本体规范）、xlsx/xls（对象信息+对象关系信息 Excel 模板）
    与 owl/rdf/xml/ttl（标准本体文件）。
    """
    from app.services.file_import import preview_json_ontology, preview_owl_ontology

    ft = (file_type or "").lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        if ft in ("xlsx", "xls"):
            from app.services.excel_import import preview_excel_ontology
            from starlette.concurrency import run_in_threadpool
            preview = await run_in_threadpool(preview_excel_ontology, content, namespace)
        elif ft == "json":
            import json as _json
            data = _json.loads(content.decode("utf-8"))
            preview = preview_json_ontology(data, namespace)
        elif ft in ("owl", "rdf", "xml"):
            preview = preview_owl_ontology(content, "xml", namespace)
        elif ft == "ttl":
            preview = preview_owl_ontology(content, "turtle", namespace)
        else:
            raise HTTPException(status_code=400, detail="预览仅支持 json / xlsx / owl / ttl 格式")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}") from e

    return OntologyPreviewResult(**preview)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(entity_id: str, db: Session = Depends(get_db)):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    rels = db.query(EntityRelation).filter(
        (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)
    ).all()

    rel_list = []
    for r in rels:
        from_e = db.get(OntologyEntity, r.from_entity_id)
        to_e = db.get(OntologyEntity, r.to_entity_id)
        rel_list.append(RelationOut(
            id=r.id, name=r.name, rel_type=r.rel_type,
            from_entity_id=r.from_entity_id, from_entity_name=from_e.name_cn if from_e else "",
            from_entity_tier=from_e.tier if from_e else 1,
            to_entity_id=r.to_entity_id, to_entity_name=to_e.name_cn if to_e else "",
            to_entity_tier=to_e.tier if to_e else 1,
            cardinality=r.cardinality, acyclic=r.acyclic, description=r.description,
            source_field=r.source_field, target_field=r.target_field,
        ))

    return EntityDetail(
        id=entity.id, ontology_id=entity.ontology_id, name=entity.name, name_cn=entity.name_cn,
        tier=entity.tier, status=entity.status, description=entity.description,
        config_json=entity.config_json,
        scenario_codes=entity.scenario_codes,
        attributes=[AttributeOut.model_validate(a) for a in entity.attributes],
        relations=rel_list,
        actions=[ActionOut.model_validate(a) for a in entity.actions],
        functions=[FunctionBriefOut.model_validate(f) for f in entity.functions],
        created_at=entity.created_at, updated_at=entity.updated_at,
        created_by=entity.created_by,
    )


@router.post("", response_model=EntityDetail, status_code=201)
def create_entity(
    data: EntityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if data.status == "published":
        raise HTTPException(422, "请通过本体版本发布流程发布对象")
    if not db.get(ScenarioDict, data.ontology_id):
        raise HTTPException(404, "本体不存在")
    if db.query(OntologyEntity).filter_by(ontology_id=data.ontology_id, name=data.name).first():
        raise HTTPException(409, "当前本体内已存在同名对象")
    names = [a.name for a in data.attributes]
    if len(names) != len(set(names)):
        raise HTTPException(422, "属性名称不能重复")
    for attribute in data.attributes:
        if attribute.shared_attribute_id:
            shared = db.get(SharedAttribute, attribute.shared_attribute_id)
            if not shared or shared.ontology_id != data.ontology_id:
                raise HTTPException(422, "共享属性不属于当前本体")
            attribute.type = shared.data_type
            attribute.description = shared.description or attribute.description
    entity = OntologyEntity(
        name=data.name, name_cn=data.name_cn, tier=data.tier,
        status=data.status, description=data.description,
        config_json=data.config_json,
        scenario_codes=data.scenario_codes,
        ontology_id=data.ontology_id,
        created_by=user.id,
    )
    for attr in data.attributes:
        entity.attributes.append(EntityAttribute(**attr.model_dump()))
    db.add(entity)
    db.flush()
    mappings = [AttributeMappingUpdate(attribute_id=a.id, source_table=a.source_table, source_field=a.source_field)
                for a in entity.attributes if a.source_table or a.source_field]
    if mappings:
        _sync_attribute_mappings(db, entity, mappings, user.id)

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="create", target_type="entity",
        target_id=entity.id, target_name=entity.name,
        snapshot_after={"name": entity.name, "tier": entity.tier},
    )
    db.commit()
    return get_entity(entity.id, db)


@router.put("/{entity_id}", response_model=EntityDetail)
def update_entity(
    entity_id: str, data: EntityUpdate,
    ontology_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 写入保护：共享实体只读
    if ontology_id:
        shared_ids = repo.get_shared_entity_ids(ontology_id)
        if entity.id in shared_ids:
            raise HTTPException(status_code=403, detail="共享实体为只读，不可修改")
        if entity.ontology_id and entity.ontology_id != ontology_id:
            raise HTTPException(status_code=403, detail="无权修改其他本体的实体")

    if data.name and data.name != entity.name and db.query(OntologyEntity).filter_by(ontology_id=entity.ontology_id, name=data.name).first():
        raise HTTPException(409, "当前本体内已存在同名对象")
    if data.status == "published" and entity.status != "published":
        raise HTTPException(422, "请通过本体版本发布流程发布对象")
    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        col = field if field != "name_cn" else "name_cn"
        old = getattr(entity, col)
        if old != value:
            changes.append({"field": field, "oldValue": old, "newValue": value})
            setattr(entity, col, value)

    if changes:
        write_audit(
            db, user_id=user.id,
            user_name=user.name,
            action="update", target_type="entity",
            target_id=entity.id, target_name=entity.name,
            changes=changes,
        )
    repo.commit()
    return get_entity(entity.id, db)


@router.put("/{entity_id}/attribute-mappings", response_model=EntityDetail)
def update_attribute_mappings(
    entity_id: str,
    items: list[AttributeMappingUpdate],
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    attr_map = {a.id: a for a in entity.attributes}
    for item in items:
        attr = attr_map.get(item.attribute_id)
        if not attr:
            raise HTTPException(422, "映射属性不属于当前对象")
    _sync_attribute_mappings(db, entity, items, user.id)
    write_audit(db, user_id=user.id, user_name=user.name, action="update",
                target_type="entity_mapping", target_id=entity.id, target_name=entity.name)

    repo.commit()
    return get_entity(entity.id, db)


def _sync_attribute_mappings(db, entity, items, user_id):
    """Legacy mapping entry writes the authoritative binding in the same transaction."""
    from app.models.asset import Asset
    from app.services.data_plane.object_binding_service import ObjectBindingService
    service = ObjectBindingService(db)
    bindings = service.list(object_type_id=entity.id, status=None)
    updates = {b.id: list(b.field_mappings or []) for b in bindings}
    new_by_asset = {}
    for item in items:
        if bool(item.source_table) != bool(item.source_field):
            raise HTTPException(422, "源表和源字段必须同时填写或清空")
        for bid, mappings in updates.items():
            updates[bid] = [m for m in mappings if m.get("attribute_id") != item.attribute_id]
        if not item.source_table:
            continue
        if item.asset_id:
            asset = db.get(Asset, item.asset_id)
            if not asset or (asset.locator or {}).get("table") != item.source_table:
                raise HTTPException(422, "所选资产与源表不一致")
        else:
            bound_assets = [db.get(Asset, b.asset_id) for b in bindings if b.status == "active"]
            candidates = [a for a in bound_assets if a and (a.locator or {}).get("table") == item.source_table]
            if not candidates:
                candidates = [a for a in db.query(Asset).filter_by(status="active", kind="table")
                              if (a.locator or {}).get("table") == item.source_table]
            candidates = list({a.id: a for a in candidates}.values())
            if len(candidates) != 1:
                raise HTTPException(422, "源表无法唯一定位资产，请提供 asset_id")
            asset = candidates[0]
        mapping = {"attribute_id": item.attribute_id, "source_column": item.source_field, "transform": None}
        binding = next((b for b in bindings if b.asset_id == asset.id and b.status == "active"), None)
        if binding:
            updates[binding.id].append(mapping)
        else:
            new_by_asset.setdefault(asset.id, []).append(mapping)
    try:
        for binding in bindings:
            if updates[binding.id] != (binding.field_mappings or []):
                service.update(binding.id, field_mappings=updates[binding.id])
        for asset_id, mappings in new_by_asset.items():
            # The first data asset is primary. Additional sources enrich the object.
            role = "primary" if not service.repo.get_primary(entity.id) else "enrichment"
            service.create(object_type_id=entity.id, asset_id=asset_id, role=role,
                           field_mappings=mappings, user_id=user_id)
    except (ValueError, LookupError) as exc:
        raise HTTPException(422, str(exc)) from exc


def _validate_attribute(db, entity, data, attribute_id=None):
    data.name = data.name.strip()
    if not data.name or len(data.name) > 100:
        raise HTTPException(422, "属性名称不能为空且最多 100 个字符")
    existing = db.query(EntityAttribute).filter_by(entity_id=entity.id, name=data.name).first()
    if existing and existing.id != attribute_id:
        raise HTTPException(409, "对象内已存在同名属性")
    if data.shared_attribute_id:
        shared = db.get(SharedAttribute, data.shared_attribute_id)
        if not shared or shared.ontology_id != entity.ontology_id:
            raise HTTPException(422, "共享属性不属于当前本体")
        data.type = shared.data_type
        data.description = shared.description or data.description


@router.post("/{entity_id}/attributes", response_model=AttributeOut, status_code=201)
def create_attribute(entity_id: str, data: AttributeBase, db: Session = Depends(get_db),
                     user: User = Depends(require_user)):
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        raise HTTPException(404, "对象不存在")
    _validate_attribute(db, entity, data)
    attr = EntityAttribute(entity_id=entity_id, **data.model_dump())
    db.add(attr)
    db.flush()
    if data.source_table or data.source_field:
        _sync_attribute_mappings(db, entity, [AttributeMappingUpdate(attribute_id=attr.id,
                                  source_table=data.source_table, source_field=data.source_field)], user.id)
    write_audit(db, user_id=user.id, user_name=user.name, action="create", target_type="attribute",
                target_id=attr.id, target_name=attr.name)
    db.commit()
    return attr


@router.put("/{entity_id}/attributes/{attribute_id}", response_model=AttributeOut)
def update_attribute(entity_id: str, attribute_id: str, data: AttributeBase,
                     db: Session = Depends(get_db), user: User = Depends(require_user)):
    entity = db.get(OntologyEntity, entity_id)
    attr = db.get(EntityAttribute, attribute_id)
    if not entity or not attr or attr.entity_id != entity_id:
        raise HTTPException(404, "对象或属性不存在")
    _validate_attribute(db, entity, data, attribute_id)
    previous_name = attr.name
    mapping_changed = (attr.source_table, attr.source_field) != (data.source_table, data.source_field)
    for key, value in data.model_dump().items():
        setattr(attr, key, value)
    if mapping_changed:
        _sync_attribute_mappings(db, entity, [AttributeMappingUpdate(attribute_id=attr.id,
                                  source_table=data.source_table, source_field=data.source_field)], user.id)
    if previous_name != attr.name:
        for relation in db.query(EntityRelation).filter(
            (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)):
            if relation.from_entity_id == entity_id and relation.source_field == previous_name:
                relation.source_field = attr.name
            if relation.to_entity_id == entity_id and relation.target_field == previous_name:
                relation.target_field = attr.name
    write_audit(db, user_id=user.id, user_name=user.name, action="update", target_type="attribute",
                target_id=attr.id, target_name=attr.name)
    db.commit()
    return attr


@router.delete("/{entity_id}", status_code=204)
def delete_entity(
    entity_id: str,
    force: bool = Query(False),
    ontology_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 写入保护：共享实体只读
    if ontology_id:
        shared_ids = repo.get_shared_entity_ids(ontology_id)
        if entity.id in shared_ids:
            raise HTTPException(status_code=403, detail="共享实体为只读，不可删除")
        if entity.ontology_id and entity.ontology_id != ontology_id:
            raise HTTPException(status_code=403, detail="无权删除其他本体的实体")

    if entity.status == "published":
        raise HTTPException(status_code=403, detail="已发布的对象不可删除，请先取消发布")

    from app.models.object_binding import ObjectBinding
    bindings = db.query(ObjectBinding).filter(ObjectBinding.object_type_id == entity_id).all()
    relations = db.query(EntityRelation).filter(
        (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)
    ).all()
    attr_count = db.query(func.count(EntityAttribute.id)).filter(
        EntityAttribute.entity_id == entity_id
    ).scalar() or 0

    if not force and (bindings or relations):
        raise HTTPException(status_code=409, detail={
            "message": "该对象存在关联引用，确认删除将同时清除以下关联",
            "bindings": len(bindings),
            "relations": len(relations),
            "attributes": attr_count,
        })

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="delete", target_type="entity",
        target_id=entity.id, target_name=entity.name,
        snapshot_before={"name": entity.name, "tier": entity.tier},
    )
    for group in db.query(OntologyGroup).filter_by(ontology_id=entity.ontology_id):
        if entity.id in (group.entity_ids or []):
            group.entity_ids = [eid for eid in group.entity_ids if eid != entity.id]
    from app.services.data_plane.object_binding_service import ObjectBindingService
    from app.models.shared_ref import OntologySharedRef
    for binding in bindings:
        ObjectBindingService(db).delete(binding.id)
    for relation in relations:
        db.delete(relation)
    db.query(OntologySharedRef).filter_by(entity_id=entity_id).delete(synchronize_session=False)
    repo.delete(entity)
    repo.commit()


# ── 删除属性 ──────────────────────────────────────────────────


@router.delete("/{entity_id}/attributes/{attribute_id}", status_code=204)
def delete_attribute(
    entity_id: str,
    attribute_id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    from app.models.object_binding import ObjectBinding

    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    if entity.status == "published":
        raise HTTPException(status_code=403, detail="已发布版本中的属性不可删除")

    attr = db.get(EntityAttribute, attribute_id)
    if not attr or attr.entity_id != entity_id:
        raise HTTPException(status_code=404, detail="属性不存在")

    bindings = db.query(ObjectBinding).filter(
        ObjectBinding.object_type_id == entity_id
    ).all()
    references = []
    for binding in bindings:
        for mapping in (binding.field_mappings or []):
            if mapping.get("attribute_id") == attribute_id:
                references.append({
                    "type": "field_mapping",
                    "binding_id": binding.id,
                    "asset_id": binding.asset_id,
                    "source_column": mapping.get("source_column"),
                })

    if references and not force:
        raise HTTPException(status_code=409, detail={
            "message": f"该属性被 {len(references)} 个映射引用，请确认是否强制删除",
            "references": references,
        })

    if references:
        for binding in bindings:
            original = binding.field_mappings or []
            updated = [m for m in original if m.get("attribute_id") != attribute_id]
            if len(updated) != len(original):
                from app.services.data_plane.object_binding_service import ObjectBindingService
                ObjectBindingService(db).update(binding.id, field_mappings=updated)

    for relation in db.query(EntityRelation).filter(
        (EntityRelation.from_entity_id == entity_id) | (EntityRelation.to_entity_id == entity_id)):
        if relation.from_entity_id == entity_id and relation.source_field == attr.name:
            relation.source_field = None
        if relation.to_entity_id == entity_id and relation.target_field == attr.name:
            relation.target_field = None

    write_audit(
        db, user_id=user.id,
        user_name=user.name,
        action="delete", target_type="attribute",
        target_id=attr.id, target_name=attr.name,
        snapshot_before={"entity_id": entity_id, "name": attr.name, "type": attr.type},
    )

    db.delete(attr)
    db.commit()
    # Long-lived editor/test sessions may disable expire_on_commit. A later
    # entity cascade must not revisit the already deleted attribute instance.
    db.expire(entity, ["attributes"])


# ── AI 智能提取本体 ──────────────────────────────────────────

class _ExtractedAttr(BaseModel):
    name: str
    type: str = "string"
    description: str = ""


class _ExtractedEntity(BaseModel):
    name: str
    name_cn: str
    tier: int = 2
    description: str = ""
    attributes: list[_ExtractedAttr] = []


class _ExtractedRelation(BaseModel):
    from_entity: str
    to_entity: str
    name: str
    rel_type: str = "has_many"
    cardinality: str = "1:N"


class _ExtractResult(BaseModel):
    entities: list[_ExtractedEntity] = []
    relations: list[_ExtractedRelation] = []


_EXTRACT_PROMPT = """你是本体建模专家。请从以下文本中提取本体实体、属性和关系。

要求：
1. 每个实体需要英文名(PascalCase)、中文名、层级(1=核心/2=领域/3=场景)、描述
2. 每个属性需要名称(snake_case)、类型(string/number/boolean/date/json/ref/computed)、描述
3. 关系需要源实体、目标实体、关系名、类型(has_one/has_many/belongs_to/many_to_many)、基数(1:1/1:N/N:1/N:N)

严格返回JSON格式，不要包含其他文字：
{"entities": [{"name": "...", "name_cn": "...", "tier": 2, "description": "...", "attributes": [{"name": "...", "type": "string", "description": "..."}]}], "relations": [{"from_entity": "...", "to_entity": "...", "name": "...", "rel_type": "has_many", "cardinality": "1:N"}]}

文本内容：
"""


@router.post("/ai-extract", response_model=_ExtractResult)
async def ai_extract_entities(
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not text and not file:
        raise HTTPException(400, "请提供文本或文件")

    content = text or ""
    if file:
        from app.services.data_plane.storage_policy import storage_policy
        from app.services.doc_builder import parse_file_content
        policy = storage_policy(db)
        if (file.filename or "").rsplit(".", 1)[-1].lower() not in policy["allowed"]:
            raise HTTPException(422, "存储配置不允许该文档类型")
        raw = await file.read(policy["max_bytes"] + 1)
        if len(raw) > policy["max_bytes"]:
            raise HTTPException(413, "文档超过配置的上传大小限制")
        try:
            content = parse_file_content(file.filename or "", raw)
        except Exception as exc:
            raise HTTPException(422, "无法解析文档内容") from exc

    if not content.strip():
        raise HTTPException(400, "内容为空")
    if len(content) > 8000:
        raise HTTPException(413, "提取内容超过 8000 字符，请拆分文档后重试")

    from app.services.llm_resolver import get_model_name
    client = get_llm_client(db=db, scene="ontology")
    resp = client.chat.completions.create(
        model=get_model_name(db, scene="ontology"),
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=0,
        max_tokens=4096,
    )

    raw_text = resp.choices[0].message.content or "{}"
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        data = _json.loads(raw_text)
    except _json.JSONDecodeError as e:
        raise HTTPException(500, "AI 返回格式异常，请重试") from e

    if not isinstance(data, dict) or not data.get("entities"):
        raise HTTPException(502, "AI 未生成有效对象")
    result = _ExtractResult(**data)
    names = {entity.name for entity in result.entities}
    if any(not entity.attributes for entity in result.entities) or any(
        relation.from_entity not in names or relation.to_entity not in names for relation in result.relations
    ):
        raise HTTPException(502, "AI 对象属性或关系引用不完整")
    return result
