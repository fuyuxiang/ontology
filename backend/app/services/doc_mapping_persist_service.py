"""文档构建映射结果持久化服务 — preview + apply"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.entity import OntologyEntity, EntityAttribute
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.object_binding_service import ObjectBindingService


def preview_mappings(mapping_result: dict, db: Session) -> dict:
    asset_repo = AssetRepository(db)
    binding_repo = ObjectBindingRepository(db)
    items = []

    for entity_map in mapping_result.get("entities", []):
        entity_name = entity_map["name"]
        table_name = entity_map.get("table")
        confidence = entity_map.get("confidence", 0)

        entity = db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        entity_id = entity.id if entity else None

        asset = asset_repo.find_table_by_name(table_name) if table_name else None
        asset_id = asset.id if asset else None
        asset_registered = asset is not None

        conflict = None
        if entity_id and asset_id:
            existing = binding_repo.find_existing(entity_id, asset_id, "primary")
            if existing:
                conflict = {
                    "existing_binding_id": existing.id,
                    "existing_asset_name": asset.name if asset else None,
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
        register_asset = item.get("register_asset", False)
        table_name = item.get("table_name")
        field_mappings = item.get("field_mappings", [])

        if not entity_id:
            skipped += 1
            continue

        if register_asset and not asset_id:
            asset_id = _register_asset(table_name, db)

        if not asset_id:
            skipped += 1
            continue

        existing = ObjectBindingRepository(db).find_existing(entity_id, asset_id, "primary")
        if existing:
            if conflict_action == "overwrite":
                binding_svc.update(existing.id, field_mappings=field_mappings)
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
        )
        created += 1
        binding_ids.append(binding.id)

    return {"created": created, "updated": updated, "skipped": skipped, "binding_ids": binding_ids}


def _register_asset(table_name: str, db: Session) -> str | None:
    if not table_name:
        return None
    from app.services.data_plane.asset_service import AssetService
    svc = AssetService(db)
    asset = svc.register(
        name=table_name,
        kind="table",
        locator={"table": table_name},
        connection_id=_get_dwd_connection_id(db),
    )
    return asset.id


def _get_dwd_connection_id(db: Session) -> str | None:
    from app.models.connection import Connection
    conn = db.query(Connection).filter(
        Connection.enabled == True,
        Connection.database == "dwd",
    ).first()
    return conn.id if conn else None
