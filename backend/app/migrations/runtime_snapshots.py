"""Add executable workspace snapshot fields without inventing historical code."""
from sqlalchemy import inspect, text


def migrate_runtime_snapshots(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    additions = {"source_code": "TEXT", "func_name": "VARCHAR(100)",
                 "checksum": "VARCHAR(64)", "ontology_id": "VARCHAR(36)", "entity_ids": "JSON"}
    with engine.begin() as conn:
        for table, fields in {"ontology_version_functions": additions,
                              "ontology_versions": {"components_frozen": "BOOLEAN DEFAULT FALSE"},
                              "ontology_version_entities": {"binding_snapshot": "JSON"},
                              "entity_relations": {"source_field": "VARCHAR(100)", "target_field": "VARCHAR(100)"},
                              "ontology_version_relations": {"source_field": "VARCHAR(100)", "target_field": "VARCHAR(100)"}}.items():
            if table not in tables:
                continue
            columns = {c["name"] for c in inspector.get_columns(table)}
            for name, typ in fields.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
