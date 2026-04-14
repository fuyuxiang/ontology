from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import OntologyEntity, EntityAttribute, EntityRelation
from app.schemas.entity import (
    EntityCreate, EntityUpdate, EntityDetail, EntityListItem,
    AttributeOut, RelationOut, RuleOut, ActionOut,
    GraphData, GraphNode, GraphEdge, FromDatasourceRequest,
)
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
    q = db.query(OntologyEntity)
    if tier:
        q = q.filter(OntologyEntity.tier == tier)
    if status:
        q = q.filter(OntologyEntity.status == status)
    if namespace:
        q = q.filter(OntologyEntity.id.like(f"{namespace}_%"))
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            OntologyEntity.name.ilike(pattern) | OntologyEntity.name_cn.ilike(pattern)
        )
    entities = q.order_by(OntologyEntity.tier, OntologyEntity.name).all()

    result = []
    for e in entities:
        rel_count = db.query(func.count(EntityRelation.id)).filter(
            (EntityRelation.from_entity_id == e.id) | (EntityRelation.to_entity_id == e.id)
        ).scalar() or 0
        result.append(EntityListItem(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status,
            attr_count=len(e.attributes),
            relation_count=rel_count,
            rule_count=len(e.rules),
            datasource_name=(e.schema_json or {}).get("datasource_name"),
        ))
    return result


@router.get("/graph", response_model=GraphData)
def get_full_graph(db: Session = Depends(get_db)):
    entities = db.query(OntologyEntity).all()
    relations = db.query(EntityRelation).all()

    nodes = []
    for e in entities:
        rc = sum(1 for r in relations if r.from_entity_id == e.id or r.to_entity_id == e.id)
        nodes.append(GraphNode(
            id=e.id, name=e.name, name_cn=e.name_cn,
            tier=e.tier, status=e.status, relation_count=rc,
        ))

    edges = []
    entity_map = {e.id: e for e in entities}
    for r in relations:
        f = entity_map.get(r.from_entity_id)
        t = entity_map.get(r.to_entity_id)
        if f and t:
            edges.append(GraphEdge(
                from_id=f.id, from_name=f.name,
                to_id=t.id, to_name=t.name,
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
    entity = db.get(OntologyEntity, entity_id)
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
                from_id=f.id, from_name=f.name,
                to_id=t.id, to_name=t.name,
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
    from app.models.datasource import DataSource
    from app.api.v1.datasources import _get_table_schema

    ds = db.get(DataSource, body.datasource_id)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    columns = _get_table_schema(ds, body.table_name)
    if not columns:
        raise HTTPException(status_code=400, detail="表无列信息")

    # 生成实体 ID
    table_pascal = body.table_name.replace("_", " ").title().replace(" ", "")
    eid = f"{body.namespace}_{table_pascal}" if body.namespace else table_pascal

    if db.get(OntologyEntity, eid):
        raise HTTPException(status_code=409, detail=f"实体 {eid} 已存在")

    # 识别主键
    pk_cols = [c["name"] for c in columns if c.get("is_pk")]
    primary_key = pk_cols[0] if pk_cols else None

    entity = OntologyEntity(
        id=eid,
        name=table_pascal,
        name_cn=body.name_cn,
        tier=body.tier,
        status="active",
        description=f"从数据源 {ds.name} 的表 {body.table_name} 自动生成",
        schema_json={
            "datasource_id": ds.id,
            "datasource_name": ds.name,
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
        snapshot_after={"source": "datasource", "datasource": ds.name, "table": body.table_name},
    )
    db.commit()
    return get_entity(eid, db)


@router.get("/{entity_id}", response_model=EntityDetail)
def get_entity(entity_id: str, db: Session = Depends(get_db)):
    entity = db.get(OntologyEntity, entity_id)
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
            from_entity_id=r.from_entity_id, from_entity_name=from_e.name if from_e else "",
            to_entity_id=r.to_entity_id, to_entity_name=to_e.name if to_e else "",
            to_entity_tier=to_e.tier if to_e else 1,
            cardinality=r.cardinality, acyclic=r.acyclic, description=r.description,
        ))

    return EntityDetail(
        id=entity.id, name=entity.name, name_cn=entity.name_cn,
        tier=entity.tier, status=entity.status, description=entity.description,
        schema_json=entity.schema_json,
        attributes=[AttributeOut.model_validate(a) for a in entity.attributes],
        relations=rel_list,
        rules=[RuleOut(
            id=r.id, name=r.name, entity_id=r.entity_id, entity_name=entity.name,
            condition_expr=r.condition_expr, action_desc=r.action_desc,
            status=r.status, priority=r.priority,
            trigger_count=r.trigger_count, last_triggered=r.last_triggered,
        ) for r in entity.rules],
        actions=[ActionOut.model_validate(a) for a in entity.actions],
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
        schema_json=data.schema_json,
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
    return get_entity(entity.id, db)


@router.put("/{entity_id}", response_model=EntityDetail)
def update_entity(
    entity_id: str, data: EntityUpdate,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    entity = db.get(OntologyEntity, entity_id)
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
    db.commit()
    return get_entity(entity.id, db)


@router.delete("/{entity_id}", status_code=204)
def delete_entity(
    entity_id: str,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    entity = db.get(OntologyEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    write_audit(
        db, user_id=user.id if user else None,
        user_name=user.name if user else None,
        action="delete", target_type="entity",
        target_id=entity.id, target_name=entity.name,
        snapshot_before={"name": entity.name, "tier": entity.tier},
    )
    db.delete(entity)
    db.commit()
