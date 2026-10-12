"""文档构建映射结果持久化服务 — preview + apply"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.models.entity import EntityAttribute, OntologyEntity
from app.models.asset import Asset
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.object_binding_service import ObjectBindingService


def preview_mappings(mapping_result: dict, db: Session, ontology_id: str | None = None) -> dict:
    asset_repo = AssetRepository(db)
    binding_repo = ObjectBindingRepository(db)
    items = []

    for entity_map in mapping_result.get("entities", []):
        entity_name = entity_map["name"]
        table_name = entity_map.get("table")
        confidence = entity_map.get("confidence", 0)

        entity = db.query(OntologyEntity).filter(
            OntologyEntity.name == entity_name, OntologyEntity.ontology_id == ontology_id,
        ).first()
        entity_id = entity.id if entity else None

        asset = asset_repo.get_by_id(entity_map.get("asset_id") or table_name) if entity_map.get("asset_id") or table_name else None
        if not asset and table_name and not entity_map.get("asset_id"):
            candidates = db.query(Asset).filter(Asset.status == "active", Asset.kind.in_(["table", "sql_view"])).all()
            matches = [row for row in candidates if (row.locator or {}).get("table") == table_name]
            if not matches:
                matches = [row for row in candidates if row.name == table_name]
            if len(matches) > 1:
                raise ValueError(f"数据表 {table_name} 对应多个资产，请选择明确的 asset_id")
            asset = matches[0] if matches else None
        if asset and asset.status != "active":
            raise ValueError(f"资产 {asset.id} 不可用")
        asset_id = asset.id if asset else None
        asset_registered = asset is not None

        conflict = None
        if entity_id:
            existing = next(iter(binding_repo.list(object_type_id=entity_id, role="primary")), None)
            if existing:
                existing_asset = asset_repo.get_by_id(existing.asset_id)
                conflict = {
                    "existing_binding_id": existing.id,
                    "existing_asset_name": existing_asset.name if existing_asset else None,
                }

        field_mappings = []
        for prop in entity_map.get("properties", []):
            attr = None
            if entity_id:
                attr = db.query(EntityAttribute).filter(
                    EntityAttribute.entity_id == entity_id,
                    EntityAttribute.name == prop["name"],
                ).first()
            field_mappings.append({
                "attribute_name": prop["name"],
                "attribute_id": attr.id if attr else None,
                "source_column": prop.get("field"),
                "confidence": prop.get("confidence", 0),
            })

        items.append({
            "entity_name": entity_name,
            "entity_id": entity_id,
            "table_name": table_name,
            "asset_id": asset_id,
            "asset_registered": asset_registered,
            "confidence": confidence,
            "conflict": conflict,
            "field_mappings": field_mappings,
        })

    return {"items": items}


def apply_mappings(items: list[dict], db: Session) -> dict:
    binding_svc = ObjectBindingService(db)
    created = 0
    updated = 0
    skipped = 0
    binding_ids = []

    for item in items:
        entity_id = item.get("entity_id")
        asset_id = item.get("asset_id")
        conflict_action = item.get("conflict_action")
        field_mappings = item.get("field_mappings", [])

        if not entity_id or not asset_id:
            raise ValueError("映射缺少实体或资产 ID，不能落库")
        entity = db.get(OntologyEntity, entity_id)
        if not entity:
            raise LookupError(f"实体不存在: {entity_id}")

        existing = next(iter(ObjectBindingRepository(db).list(object_type_id=entity_id, role="primary")), None)
        if existing:
            if conflict_action == "overwrite":
                binding_svc.prepare_data_replacement(entity_id, {(asset_id, "primary")})
                existing = binding_svc.repo.find_existing(entity_id, asset_id, "primary")
                id_column = _mapped_primary_key(db, entity, field_mappings)
                if existing:
                    binding_svc.update(existing.id, field_mappings=field_mappings, id_column=id_column,
                                       status="active", review_reason=None)
                else:
                    existing = binding_svc.create(object_type_id=entity_id, asset_id=asset_id,
                                                  role="primary", field_mappings=field_mappings, id_column=id_column)
                updated += 1
                binding_ids.append(existing.id)
            else:
                skipped += 1
            continue

        binding = binding_svc.create(
            object_type_id=entity_id,
            asset_id=asset_id,
            role="primary",
            field_mappings=field_mappings,
            id_column=_mapped_primary_key(db, entity, field_mappings),
        )
        created += 1
        binding_ids.append(binding.id)

    return {"created": created, "updated": updated, "skipped": skipped, "binding_ids": binding_ids}


def _mapped_primary_key(db, entity, mappings):
    primary_name = (entity.config_json or {}).get("primary_key")
    primary = db.query(EntityAttribute).filter_by(entity_id=entity.id, name=primary_name).first()
    return next((m.get("source_column") for m in mappings if primary and m.get("attribute_id") == primary.id), None)


def binding_fingerprint(db: Session, entity_id: str) -> str:
    """Bind a keep decision to the exact persisted mapping, including join rules."""
    entity = db.get(OntologyEntity, entity_id)
    rows = ObjectBindingRepository(db).list(object_type_id=entity_id)
    state = {
        "primary_key": (entity.config_json or {}).get("primary_key"),
        "attributes": sorted((a.id, a.name) for a in db.query(EntityAttribute).filter_by(entity_id=entity_id)),
        "bindings": [{"id": b.id, "asset_id": b.asset_id, "role": b.role, "status": b.status,
                      "id_column": b.id_column, "field_mappings": b.field_mappings,
                      "filter_expr": b.filter_expr, "primary_source_column": b.primary_source_column,
                      "enrichment_source_column": b.enrichment_source_column}
                     for b in sorted(rows, key=lambda b: b.id) if b.role in {"primary", "enrichment"}],
    }
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def effective_mapping_item(db: Session, entity_id: str, conflict_action: str | None = None) -> dict:
    """Return the mapping that actually survived apply, rather than the LLM candidate."""
    entity = db.get(OntologyEntity, entity_id)
    bindings = [b for b in ObjectBindingRepository(db).list(object_type_id=entity_id)
                if b.role in {"primary", "enrichment"} and b.status != "deprecated"]
    bindings.sort(key=lambda b: (b.role != "primary", b.id))
    primary = next((b for b in bindings if b.role == "primary"), None)
    asset = db.get(Asset, primary.asset_id) if primary else None
    sources = {m["attribute_id"]: (b.asset_id, m) for b in bindings for m in b.field_mappings or []}
    fields = []
    for attr in db.query(EntityAttribute).filter_by(entity_id=entity_id):
        source_asset_id, mapping = sources.get(attr.id, (None, {}))
        fields.append({"attribute_name": attr.name, "attribute_id": attr.id,
                       "source_asset_id": source_asset_id, "source_column": mapping.get("source_column"),
                       "transform": mapping.get("transform"), "confidence": 1,
                       "type": attr.type, "required": attr.required, "description": attr.description})
    primary_key = (entity.config_json or {}).get("primary_key")
    if not primary_key and primary:
        keys = [f["attribute_name"] for f in fields
                if f["source_asset_id"] == primary.asset_id and f["source_column"] == primary.id_column]
        primary_key = keys[0] if len(keys) == 1 else None
    return {"entity_name": entity.name, "entity_id": entity.id, "asset_id": primary.asset_id if primary else None,
            "table_name": (asset.locator or {}).get("table") if asset else None,
            "asset_registered": asset is not None, "confidence": 1, "conflict_action": conflict_action,
            "backing_asset_ids": [b.asset_id for b in bindings], "id_column": primary.id_column if primary else None,
            "primary_key": primary_key,
            "enrichment_bindings": [{"asset_id": b.asset_id, "primary_source_column": b.primary_source_column,
                                     "enrichment_source_column": b.enrichment_source_column}
                                    for b in bindings if b.role == "enrichment"],
            "field_mappings": fields}


def validate_kept_mappings(body, db: Session, user_id: str) -> set[str]:
    """A candidate, stale receipt, or later edit cannot silently override keep."""
    from fastapi import HTTPException
    from app.models.builder_document_session import BuilderDocumentSession
    if not body.document_session_id:
        return set()
    record = db.get(BuilderDocumentSession, body.document_session_id)
    if not record or record.user_id != user_id:
        raise HTTPException(404, "文档映射会话不存在或不可访问")
    receipt = (record.payload or {}).get("mapping_receipt")
    if not receipt or receipt.get("ontology_id") != body.ontology_id:
        raise HTTPException(409, "文档映射尚未确认，请返回映射步骤确认")
    kept = receipt.get("kept_entities", {})
    objects = {obj.name: obj for obj in body.objects}
    for entity_id, fingerprint in kept.items():
        entity = db.get(OntologyEntity, entity_id)
        if not entity or entity.ontology_id != body.ontology_id or binding_fingerprint(db, entity_id) != fingerprint:
            raise HTTPException(409, "已保留映射发生变更，请返回映射步骤重新确认")
        obj = objects.get(entity.name)
        if not obj:
            continue
        effective = effective_mapping_item(db, entity_id)
        expected = {f["attribute_name"]: (f["source_asset_id"], f["source_column"], f["transform"])
                    for f in effective["field_mappings"]}
        supplied = {p.name: (p.source_asset_id, p.source_column, p.transform) for p in obj.properties}
        joins = [r.model_dump() for r in obj.enrichment_bindings]
        if (expected != supplied or obj.backing_asset_ids != effective["backing_asset_ids"]
                or obj.primaryKey != effective["primary_key"]
                or sorted(joins, key=lambda r: r["asset_id"]) != sorted(effective["enrichment_bindings"], key=lambda r: r["asset_id"])):
            raise HTTPException(409, "本次选择保留旧映射；如需修改，请返回映射步骤选择覆盖并重新确认")
    return set(kept)
