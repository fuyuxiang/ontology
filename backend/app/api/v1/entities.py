from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import OntologyEntity, EntityAttribute, EntityRelation, BusinessRule, EntityAction
from app.schemas.entity import (
    EntityCreate, EntityUpdate, EntityDetail, EntityListItem,
    AttributeOut, AttributeMappingUpdate, RelationOut, RuleOut, ActionOut,
    FunctionBriefOut,
    GraphData, GraphNode, GraphEdge, FromDatasourceRequest,
    FileImportResult, OntologyPreviewResult,
)
from app.repositories import EntityRepository
from app.core.deps import get_current_user
from app.models.user import User
from app.services.audit import write_audit

router = APIRouter(prefix="/entities", tags=["entities"])


@router.get("", response_model=list[EntityListItem])
def list_entities(
    tier: int | None = None,
    status: str | None = None,
    search: str | None = None,
    namespace: str | None = None,
    db: Session = Depends(get_db),
):
    repo = EntityRepository(db)
    entities = repo.list_with_filters(tier=tier, status=status, search=search, namespace=namespace)

    result = []
    for e in entities:
        rel_count = repo.get_relation_count(e.id)
        result.append(EntityListItem(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status,
            attr_count=len(e.attributes),
            relation_count=rel_count,
            rule_count=len(e.rules),
            datasource_name=(e.config_json or {}).get("datasource_name"),
        ))
    return result


# ── 场景层级映射：namespace -> { layer_key: [entity_name, ...] } ──
_SCENE_LAYER_MAP: dict[str, dict[str, list[str]]] = {
    "s5": {
        "signal": [
            "MobileSubscriber", "PortabilityQuery",
            "UserContract", "UserArrears", "ComplaintWorkOrder",
        ],
        "aggregate": ["MonthlyBilling", "VoiceCallRecord", "ConvergencePackage"],
        "decision": ["RetentionRecord"],
    },
}


@router.get("/scene-layer-stats")
def get_scene_layer_stats(
    namespace: str = Query(..., description="场景命名空间，如 s5"),
    db: Session = Depends(get_db),
):
    """按层级统计场景实体、属性、关系、规则、动作数量。"""
    layer_map = _SCENE_LAYER_MAP.get(namespace)
    if not layer_map:
        raise HTTPException(status_code=404, detail=f"未找到命名空间 {namespace} 的层级映射")

    repo = EntityRepository(db)
    layer_labels = {"signal": "语义层", "aggregate": "动力层", "decision": "动态层"}
    result = []

    for layer_key in ("signal", "aggregate", "decision"):
        entity_names = layer_map.get(layer_key, [])
        entity_ids = [f"{namespace}_{n}" for n in entity_names]
        entity_count = len(entity_ids)
        counts = repo.get_scene_layer_counts(entity_ids)
        result.append({
            "key": layer_key,
            "label": layer_labels.get(layer_key, layer_key),
            "entityCount": entity_count,
            **counts,
        })

    return result


@router.get("/data-layer")
def get_data_layer(db: Session = Depends(get_db)):
    from app.models.asset import Asset
    from sqlalchemy import distinct
    rows = (
        db.query(
            EntityAttribute.entity_id,
            EntityAttribute.source_table,
        )
        .filter(EntityAttribute.source_table.isnot(None), EntityAttribute.source_table != '')
        .all()
    )
    # group by entity_id
    entity_tables: dict[str, str] = {}
    entity_field_counts: dict[str, int] = {}
    for r in rows:
        entity_tables[r.entity_id] = r.source_table
        entity_field_counts[r.entity_id] = entity_field_counts.get(r.entity_id, 0) + 1

    # build asset index by table_name
    all_assets = db.query(Asset).filter(Asset.status == "active").all()
    asset_by_table = {(a.locator or {}).get("table", ""): a for a in all_assets if (a.locator or {}).get("table")}

    from app.models import OntologyEntity
    result = []
    for entity_id, table_name in entity_tables.items():
        e = db.get(OntologyEntity, entity_id)
        if not e:
            continue
        asset = asset_by_table.get(table_name)
        record_count = (asset.profile or {}).get("row_count", 0) if asset else 0
        datasource_name = asset.name if asset else ''
        result.append({
            'entity_id': entity_id,
            'entity_name_cn': e.name_cn,
            'table_name': table_name,
            'field_count': entity_field_counts.get(entity_id, 0),
            'record_count': record_count,
            'datasource_name': datasource_name,
        })
    return result


@router.get("/graph", response_model=GraphData)
def get_full_graph(db: Session = Depends(get_db)):
    repo = EntityRepository(db)
    entities = repo.list_with_filters()
    relations = repo.get_all_relations()

    nodes = []
    for e in entities:
        rc = sum(1 for r in relations if r.from_entity_id == e.id or r.to_entity_id == e.id)
        nodes.append(GraphNode(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status, relation_count=rc,
            action_count=len(e.actions),
            rule_count=len(e.rules),
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
    user: User | None = Depends(get_current_user),
):
    from app.models.asset import Asset
    from app.services.data_plane.connection_service import ConnectionService

    asset = db.get(Asset, body.datasource_id)
    if not asset:
        raise HTTPException(status_code=404, detail="数据源不存在")

    if not asset.connection_id:
        raise HTTPException(status_code=400, detail="资产未关联连接")
    columns = ConnectionService(db).get_table_schema(asset.connection_id, body.table_name)
    if not columns:
        raise HTTPException(status_code=400, detail="表无列信息")

    table_pascal = body.table_name.replace("_", " ").title().replace(" ", "")
    eid = f"{body.namespace}_{table_pascal}" if body.namespace else table_pascal

    repo = EntityRepository(db)
    if repo.get_by_id(eid):
        raise HTTPException(status_code=409, detail=f"实体 {eid} 已存在")

    pk_cols = [c["name"] for c in columns if c.get("is_pk")]
    primary_key = pk_cols[0] if pk_cols else None

    entity = OntologyEntity(
        id=eid,
        name=table_pascal,
        name_cn=body.name_cn,
        tier=body.tier,
        status="active",
        description=f"从数据源 {asset.name} 的表 {body.table_name} 自动生成",
        config_json={
            "datasource_id": asset.id,
            "datasource_name": asset.name,
            "table_name": body.table_name,
            "primary_key": primary_key,
        },
        created_by=user.id if user else None,
    )
    db.add(entity)

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
    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="create", target_type="entity",
        target_id=eid, target_name=table_pascal,
        snapshot_after={"source": "datasource", "datasource": asset.name, "table": body.table_name},
    )
    db.commit()
    return get_entity(eid, db)


# ── M2: 从 Asset 创建本体（自动落 ObjectBinding）──────────────

class FromAssetRequest(BaseModel):
    asset_id: str
    name_cn: str
    tier: int = 1
    namespace: str = ""


@router.post("/from-asset", response_model=EntityDetail, status_code=201)
def create_from_asset(
    body: FromAssetRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
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

    table_name = (asset.locator or {}).get("table") or asset.name
    table_pascal = table_name.replace("_", " ").title().replace(" ", "")
    eid = f"{body.namespace}_{table_pascal}" if body.namespace else table_pascal

    repo = EntityRepository(db)
    if repo.get_by_id(eid):
        raise HTTPException(status_code=409, detail=f"实体 {eid} 已存在")

    pk_cols = [c["name"] for c in columns if c.get("is_pk")]
    primary_key = pk_cols[0] if pk_cols else None

    entity = OntologyEntity(
        id=eid,
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
        created_by=user.id if user else None,
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
        user_id=user.id if user else None,
    )

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
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
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    """从文件导入本体：支持 json / owl / ttl 格式。"""
    from app.services.file_import import parse_json_ontology, parse_owl_ontology

    if file_type not in ("json", "owl", "ttl"):
        raise HTTPException(status_code=400, detail="file_type 必须为 json、owl 或 ttl")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        if file_type == "json":
            import json as _json
            data = _json.loads(content.decode("utf-8"))
            result = parse_json_ontology(data, namespace, db)
        elif file_type == "owl":
            result = parse_owl_ontology(content, "xml", db)
        else:
            result = parse_owl_ontology(content, "turtle", db)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
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
    )


@router.post("/preview-file", response_model=OntologyPreviewResult)
async def preview_from_file(
    file: UploadFile = File(...),
    file_type: str = Form(...),
    namespace: str = Form(""),
):
    """预览本体文件：仅解析为草稿结构，不落库、不写审计。供模版构建使用。"""
    from app.services.file_import import preview_json_ontology

    if file_type != "json":
        raise HTTPException(status_code=400, detail="预览目前仅支持 json 格式")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    try:
        import json as _json
        data = _json.loads(content.decode("utf-8"))
        preview = preview_json_ontology(data, namespace)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

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
            to_entity_id=r.to_entity_id, to_entity_name=to_e.name_cn if to_e else "",
            to_entity_tier=to_e.tier if to_e else 1,
            cardinality=r.cardinality, acyclic=r.acyclic, description=r.description,
        ))

    return EntityDetail(
        id=entity.id, name=entity.name, name_cn=entity.name_cn,
        tier=entity.tier, status=entity.status, description=entity.description,
        config_json=entity.config_json,
        attributes=[AttributeOut.model_validate(a) for a in entity.attributes],
        relations=rel_list,
        rules=[RuleOut(
            id=r.id, name=r.name, entity_id=r.entity_id, entity_name=entity.name,
            condition_expr=r.condition_expr, action_desc=r.action_desc,
            status=r.status, priority=r.priority,
            trigger_count=r.trigger_count, last_triggered=r.last_triggered,
        ) for r in entity.rules],
        actions=[ActionOut.model_validate(a) for a in entity.actions],
        functions=[FunctionBriefOut.model_validate(f) for f in entity.functions],
        created_at=entity.created_at, updated_at=entity.updated_at,
        created_by=entity.created_by,
    )


@router.post("", response_model=EntityDetail, status_code=201)
def create_entity(
    data: EntityCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    entity = OntologyEntity(
        name=data.name, name_cn=data.name_cn, tier=data.tier,
        status=data.status, description=data.description,
        config_json=data.config_json,
        created_by=user.id if user else None,
    )
    for attr in data.attributes:
        entity.attributes.append(EntityAttribute(**attr.model_dump()))
    db.add(entity)
    db.flush()

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="create", target_type="entity",
        target_id=entity.id, target_name=entity.name,
        snapshot_after={"name": entity.name, "tier": entity.tier},
    )
    db.commit()
    # 通知 AIP 事件总线
    try:
        from app.services.aip.event_bus import publish as aip_publish
        aip_publish(entity.name, "created", {"id": entity.id, "name": entity.name})
    except Exception:
        pass
    return get_entity(entity.id, db)


@router.put("/{entity_id}", response_model=EntityDetail)
def update_entity(
    entity_id: str, data: EntityUpdate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        col = field if field != "name_cn" else "name_cn"
        old = getattr(entity, col)
        if old != value:
            changes.append({"field": field, "oldValue": old, "newValue": value})
            setattr(entity, col, value)

    if changes:
        write_audit(
            db, user_id=user.id if user else None,
            user_name=user.name if user else None,
            action="update", target_type="entity",
            target_id=entity.id, target_name=entity.name,
            changes=changes,
        )
    repo.commit()
    if changes:
        try:
            from app.services.aip.event_bus import publish as aip_publish
            aip_publish(entity.name, "updated", {"id": entity.id, "name": entity.name})
        except Exception:
            pass
    return get_entity(entity.id, db)


@router.put("/{entity_id}/attribute-mappings", response_model=EntityDetail)
def update_attribute_mappings(
    entity_id: str,
    items: list[AttributeMappingUpdate],
    db: Session = Depends(get_db),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    attr_map = {a.id: a for a in entity.attributes}
    for item in items:
        attr = attr_map.get(item.attribute_id)
        if not attr:
            continue
        attr.source_table = item.source_table
        attr.source_field = item.source_field
        attr.data_status = item.data_status

    repo.commit()
    return get_entity(entity.id, db)


@router.delete("/{entity_id}", status_code=204)
def delete_entity(
    entity_id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    repo = EntityRepository(db)
    entity = repo.get_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

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
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="delete", target_type="entity",
        target_id=entity.id, target_name=entity.name,
        snapshot_before={"name": entity.name, "tier": entity.tier},
    )
    entity_name = entity.name
    entity_id_v = entity.id
    repo.delete(entity)
    repo.commit()
    try:
        from app.services.aip.event_bus import publish as aip_publish
        aip_publish(entity_name, "deleted", {"id": entity_id_v, "name": entity_name})
    except Exception:
        pass


# ── 删除属性 ──────────────────────────────────────────────────


@router.delete("/{entity_id}/attributes/{attribute_id}", status_code=204)
def delete_attribute(
    entity_id: str,
    attribute_id: str,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
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
                binding.field_mappings = updated
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(binding, "field_mappings")

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="delete", target_type="attribute",
        target_id=attr.id, target_name=attr.name,
        snapshot_before={"entity_id": entity_id, "name": attr.name, "type": attr.type},
    )

    db.delete(attr)
    db.commit()


# ── AI 智能提取本体 ──────────────────────────────────────────

from pydantic import BaseModel
from app.services.copilot import get_llm_client
from app.config import settings
import json as _json


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
):
    if not text and not file:
        raise HTTPException(400, "请提供文本或文件")

    content = text or ""
    if file:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")

    if not content.strip():
        raise HTTPException(400, "内容为空")

    client = get_llm_client()
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _EXTRACT_PROMPT},
            {"role": "user", "content": content[:8000]},
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
    except _json.JSONDecodeError:
        raise HTTPException(500, "AI 返回格式异常，请重试")

    return _ExtractResult(**data)
