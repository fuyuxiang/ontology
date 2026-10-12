"""Published ontology instance API consumed by the generated SDKs."""
from __future__ import annotations

import json
from collections import deque
from typing import Annotated
from urllib.parse import quote, urlencode
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.version import OntologyVersion, OntologyVersionEntity
from app.services.version_entity_data import VersionEntityDataService

router = APIRouter(prefix="/ontology-api", tags=["ontology-api"])


def _published_entities(db, ontology_id=None, version_id=None):
    query = db.query(OntologyVersionEntity).join(OntologyVersion).filter(OntologyVersion.status == "published")
    if version_id:
        query = query.filter(OntologyVersion.id == version_id)
    else:
        query = query.filter(OntologyVersion.is_active.is_(True))
    if ontology_id:
        query = query.filter(OntologyVersion.ontology_id == ontology_id)
    return query.all()


def _resolve(db, name, ontology_id=None, version_id=None):
    entities = _published_entities(db, ontology_id, version_id)
    exact = [e for e in entities if name in (e.id, e.source_entity_id)]
    matches = exact or [e for e in entities if e.name == name]
    if not matches:
        raise HTTPException(404, "对象不在指定的已发布本体版本中")
    if len(matches) != 1:
        raise HTTPException(400, "对象名称在多个本体中存在，请指定 ontology_id 或使用对象 ID")
    return matches[0]


def _id_attr(db, entity):
    svc = VersionEntityDataService(db, entity)
    snapshot = entity.binding_snapshot or {}
    pk = snapshot.get("id_column")
    fields = svc.get_attr_field_map(entity.source_entity_id)
    keys = [name for name, physical in fields.items() if physical == pk]
    if len(keys) != 1:
        raise HTTPException(409, "发布对象必须绑定并映射唯一实例 ID 列")
    return keys[0]


def _rows(db, entity, filters=None, limit=50, offset=0):
    try:
        result = VersionEntityDataService(db, entity).query_entity_data(entity.source_entity_id, filters=filters, limit=limit, offset=offset, purpose="ontology_api")
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result.get("error"):
        raise HTTPException(422, result["error"])
    id_attr = _id_attr(db, entity)
    rows = [dict(zip(result["columns"], row)) for row in result["rows"]]
    for row in rows:
        row.setdefault("id", row.get(id_attr))
    return rows


def _one(db, entity, record_id):
    rows = _rows(db, entity, {_id_attr(db, entity): record_id}, 2)
    if not rows:
        raise HTTPException(404, "业务实例不存在")
    if len(rows) != 1:
        raise HTTPException(409, "实例 ID 非唯一")
    return rows[0]


@router.get("/endpoints")
def list_endpoints(ontology_id: str | None = None, db: Session = Depends(get_db)):
    groups = []
    for entity in _published_entities(db, ontology_id):
        try:
            id_property = _id_attr(db, entity)
        except HTTPException:
            id_property = None
        base = f"/ontology-api/objects/{entity.source_entity_id}"
        endpoints = []
        for method, suffix, desc in [("GET", "", "实例列表"), ("GET", "/{id}", "实例详情"),
                                     ("GET", "/{id}/relations", "关联实例"), ("POST", "", "创建实例")]:
            endpoints.append({"method": method, "path": base + suffix, "shortPath": f"/{entity.name}" + suffix,
                              "description": f"{entity.name_cn} {desc}", "params": []})
        groups.append({"entity": entity.name, "entityCn": entity.name_cn, "entity_id": entity.source_entity_id,
                       "ontology_id": entity.version.ontology_id, "version_id": entity.version_id,
                       "id_property": id_property, "instance_api_available": id_property is not None, "endpoints": endpoints})
    return {"groups": groups}


class OntologyQueryRequest(BaseModel):
    entity_name: str
    ontology_id: str | None = None
    version_id: str | None = None
    filters: dict | None = None
    relations: list[str] | None = None
    depth: int = Field(1, ge=0, le=5)
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


@router.post("/query")
def ontology_query(req: OntologyQueryRequest, db: Session = Depends(get_db)):
    entity = _resolve(db, req.entity_name, req.ontology_id, req.version_id)
    rels = [r for r in entity.version.relations if entity.id in (r.from_version_entity_id, r.to_version_entity_id)
            and (not req.relations or r.name in req.relations)]
    return {"entity": {"name": entity.name, "name_cn": entity.name_cn, "tier": entity.tier, "id_property": _id_attr(db, entity)},
            "instances": _rows(db, entity, req.filters, req.limit, req.offset),
            "relations": [{"name": r.name, "rel_type": r.rel_type, "cardinality": r.cardinality,
                           "from_entity_id": r.from_entity.source_entity_id, "to_entity_id": r.to_entity.source_entity_id}
                          for r in rels] if req.depth else []}


@router.get("/objects/{entity_name}")
def list_objects(entity_name: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 filter: str | None = None, ontology_id: str | None = None, version_id: str | None = None,
                 db: Session = Depends(get_db)):
    try:
        filters = json.loads(filter) if filter else {}
        if not isinstance(filters, dict):
            raise ValueError("filter 必须为 JSON 对象")
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "filter 必须为有效 JSON 对象") from exc
    return _rows(db, _resolve(db, entity_name, ontology_id, version_id), filters, limit, offset)


@router.get("/objects/{entity_name}/{record_id}")
def get_object(entity_name: str, record_id: str, ontology_id: str | None = None, version_id: str | None = None,
               db: Session = Depends(get_db)):
    return _one(db, _resolve(db, entity_name, ontology_id, version_id), record_id)


@router.get("/objects/{entity_name}/{record_id}/relations")
def get_relations(entity_name: str, record_id: str, depth: Annotated[int, Query(ge=1, le=5)] = 1, rel_type: str | None = None,
                  ontology_id: str | None = None, version_id: str | None = None, db: Session = Depends(get_db),
                  limit: Annotated[int, Query(ge=1, le=200)] = 100,
                  offset: Annotated[int, Query(ge=0)] = 0, relation_id: str | None = None,
                  max_nodes: Annotated[int, Query(ge=1, le=10000)] = 1000):
    """Page each incident relation; preserve the legacy array/instances shape.

    offset applies to the initial node only. A page link pins the published
    version, source record and relation, so clients can retrieve every omitted
    instance even when a bounded multi-hop traversal is incomplete.
    """
    entity = _resolve(db, entity_name, ontology_id, version_id)
    initial = _one(db, entity, record_id)
    identity_properties = {}

    def instance_id(source, row):
        if source.id not in identity_properties:
            identity_properties[source.id] = _id_attr(db, source)
        return row.get(identity_properties[source.id])

    result, queue, visited = [], deque([(entity, initial, 0)]), set()
    scheduled = {(entity.id, str(instance_id(entity, initial)))}
    reasons, continuations = set(), []

    def continuation(source, source_id, remaining_depth, **paging):
        params = {"version_id": source.version_id, "depth": remaining_depth, "limit": limit, "max_nodes": max_nodes, **paging}
        if rel_type:
            params["rel_type"] = rel_type
        path = f"/ontology-api/objects/{quote(source.source_entity_id, safe='')}/{quote(str(source_id), safe='')}/relations"
        return path + "?" + urlencode(params)

    def field_map(version_entity):
        snapshot = version_entity.binding_snapshot or {}
        mapped = {mapping.get("attribute_id"): mapping.get("source_column")
                  for source in [snapshot] + (snapshot.get("enrichments") or [])
                  for mapping in source.get("field_mappings") or []}
        return {a.name: mapped[a.source_attribute_id] for a in version_entity.attributes
                if mapped.get(a.source_attribute_id)}

    while queue:
        current, instance, level = queue.popleft()
        key = (current.id, str(instance_id(current, instance)))
        if key in visited or level >= depth:
            continue
        visited.add(key)
        for relation in current.version.relations:
            forward = relation.from_version_entity_id == current.id
            if not forward and relation.to_version_entity_id != current.id:
                continue
            if rel_type and rel_type not in (relation.rel_type, relation.name):
                continue
            if level == 0 and relation_id and relation_id not in (relation.id, relation.source_relation_id):
                continue
            target = relation.to_entity if forward else relation.from_entity
            source_field = relation.source_field if forward else relation.target_field
            target_field = relation.target_field if forward else relation.source_field
            if not source_field or not target_field:
                raise HTTPException(409, f"关系 {relation.name} 未配置实例关联字段")
            source_map, target_map = field_map(current), field_map(target)
            source_attr = source_field if source_field in source_map else next((k for k,v in source_map.items() if v == source_field), None)
            target_attr = target_field if target_field in target_map else next((k for k,v in target_map.items() if v == target_field), None)
            if not source_attr or not target_attr:
                raise HTTPException(409, f"关系 {relation.name} 关联字段不在发布映射中")
            value = instance.get(source_attr)
            page_offset = offset if level == 0 else 0
            linked = [] if value is None else _rows(db, target, {target_attr: value}, limit, page_offset)
            has_more = bool(value is not None and len(linked) == limit
                            and _rows(db, target, {target_attr: value}, 1, page_offset + limit))
            next_page = (continuation(current, instance_id(current, instance), depth - level,
                                      relation_id=relation.id, offset=page_offset + limit) if has_more else None)
            if has_more:
                reasons.add("pagination")
                continuations.append(next_page)
            result.append({"relation": relation.name, "entity": target.name, "entity_id": target.source_entity_id,
                           "relation_id": relation.id, "source_entity_id": current.source_entity_id,
                           "source_record_id": instance_id(current, instance), "direction": "outgoing" if forward else "incoming",
                           "instances": linked, "depth": level + 1,
                           "pagination": {"limit": limit, "offset": page_offset, "has_more": has_more,
                                          "next_offset": page_offset + limit if has_more else None, "next": next_page}})
            if level + 1 < depth:
                for row in linked:
                    linked_key = (target.id, str(instance_id(target, row)))
                    if linked_key in scheduled:
                        continue
                    if len(scheduled) >= max_nodes:
                        reasons.add("node_limit")
                        continuations.append(continuation(target, instance_id(target, row), depth - level - 1))
                        continue
                    scheduled.add(linked_key)
                    queue.append((target, row, level + 1))
    traversal = {"visited_nodes": len(visited), "max_nodes": max_nodes, "truncated": bool(reasons),
                 "reasons": sorted(reasons), "continuations": list(dict.fromkeys(continuations))}
    for item in result:
        item["traversal"] = traversal
    return result


@router.post("/objects/{entity_name}", status_code=201)
def create_object(entity_name: str, data: dict, ontology_id: str | None = None, version_id: str | None = None,
                  db: Session = Depends(get_db)):
    entity = _resolve(db, entity_name, ontology_id, version_id)
    from app.services.object_mutation_service import ObjectMutationService
    try:
        return ObjectMutationService(db, entity).create(entity.source_entity_id, data)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
