"""Protect one active primary per object, including existing ambiguous data."""
from sqlalchemy import inspect, text


def migrate_binding_integrity(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "object_bindings" not in tables:
        return
    columns = {c["name"] for c in inspector.get_columns("object_bindings")}
    indexes = {i["name"] for i in inspector.get_indexes("object_bindings")}
    with engine.begin() as conn:
        if "active_primary_key" not in columns:
            conn.execute(text("ALTER TABLE object_bindings ADD COLUMN active_primary_key VARCHAR(36)"))
        for column in ("primary_source_column", "enrichment_source_column"):
            if column not in columns:
                conn.execute(text(f"ALTER TABLE object_bindings ADD COLUMN {column} VARCHAR(120)"))
        legacy_enrichments = conn.execute(text("SELECT id,object_type_id FROM object_bindings WHERE role='enrichment' AND status='active' AND (primary_source_column IS NULL OR enrichment_source_column IS NULL)")).all()
        for binding_id, object_id in legacy_enrichments:
            conn.execute(text("UPDATE object_bindings SET status='needs_review', review_reason=:reason WHERE id=:id"),
                {"id": binding_id, "reason": "补充绑定缺少明确关联列，请配置 primary_source_column 与 enrichment_source_column 后重新确认"})
            if "entity_attributes" in tables and "field_mappings" in columns:
                import json
                raw = conn.execute(text("SELECT field_mappings FROM object_bindings WHERE id=:id"), {"id": binding_id}).scalar()
                mappings = json.loads(raw) if isinstance(raw, str) else raw or []
                for mapping in mappings:
                    conn.execute(text("UPDATE entity_attributes SET source_table=NULL, source_field=NULL, data_status=:status WHERE id=:id AND entity_id=:object"),
                        {"id": mapping.get("attribute_id"), "object": object_id, "status": "未确认来源"})
            if "quality_rules" in tables:
                rule_ids = conn.execute(text("SELECT id FROM quality_rules WHERE description=:description"), {"description": f"auto:binding:{binding_id}"}).scalars().all()
                for rule_id in rule_ids:
                    if "health_statuses" in tables:
                        conn.execute(text("DELETE FROM health_statuses WHERE rule_id=:id"), {"id": rule_id})
                    conn.execute(text("DELETE FROM quality_rules WHERE id=:id"), {"id": rule_id})
        if legacy_enrichments and "lineage_edges" in tables:
            conn.execute(text("UPDATE lineage_edges SET weight=0 WHERE relation='binds_to' AND source_kind='asset' AND target_kind='object_type' AND NOT EXISTS (SELECT 1 FROM object_bindings b WHERE b.asset_id=lineage_edges.source_id AND b.object_type_id=lineage_edges.target_id AND b.status='active')"))
        ambiguous = conn.execute(text("SELECT object_type_id FROM object_bindings WHERE role='primary' AND status='active' GROUP BY object_type_id HAVING COUNT(*)>1")).scalars().all()
        # Selecting an arbitrary source would corrupt object identity. Require explicit
        # mapping review of every conflicting source and invalidate legacy shortcuts.
        for object_id in ambiguous:
            conn.execute(text("UPDATE object_bindings SET status='needs_review', review_reason=:reason, active_primary_key=NULL WHERE object_type_id=:id AND role='primary' AND status='active'"),
                {"id": object_id, "reason": "存在多个活动主绑定，请明确选择源资产后重新确认映射"})
            if "entity_attributes" in tables:
                conn.execute(text("UPDATE entity_attributes SET source_table=NULL, source_field=NULL, data_status=:status WHERE entity_id=:id"),
                    {"id": object_id, "status": "未确认来源"})
        conn.execute(text("UPDATE object_bindings SET active_primary_key=CASE WHEN role='primary' AND status='active' THEN object_type_id ELSE NULL END"))
        if "uq_binding_active_primary" not in indexes:
            conn.execute(text("CREATE UNIQUE INDEX uq_binding_active_primary ON object_bindings(active_primary_key)"))
