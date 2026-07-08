from sqlalchemy import inspect, text


def ensure_legacy_schema_compat(engine) -> None:
    with engine.connect() as conn:
        inspector = inspect(engine)

        if "business_rules" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("business_rules")}
            additions = {
                "conditions_json": "ALTER TABLE business_rules ADD COLUMN conditions_json JSON",
                "rule_meta_json": "ALTER TABLE business_rules ADD COLUMN rule_meta_json JSON",
                "description": "ALTER TABLE business_rules ADD COLUMN description TEXT DEFAULT ''",
                "tags": "ALTER TABLE business_rules ADD COLUMN tags JSON",
                "input_params": "ALTER TABLE business_rules ADD COLUMN input_params JSON",
                "output_schema": "ALTER TABLE business_rules ADD COLUMN output_schema JSON",
                "action_id": "ALTER TABLE business_rules ADD COLUMN action_id VARCHAR(36)",
            }

            for name, statement in additions.items():
                if name not in cols:
                    conn.execute(text(statement))

            conn.commit()

        if "ontology_functions" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("ontology_functions")}
            additions = {
                "source_path": "ALTER TABLE ontology_functions ADD COLUMN source_path VARCHAR(500) NULL",
                "func_name": "ALTER TABLE ontology_functions ADD COLUMN func_name VARCHAR(100) NULL",
                "checksum": "ALTER TABLE ontology_functions ADD COLUMN checksum VARCHAR(64) NULL",
                "registered_by": "ALTER TABLE ontology_functions ADD COLUMN registered_by VARCHAR(20) DEFAULT 'ui'",
            }

            for name, statement in additions.items():
                if name not in cols:
                    conn.execute(text(statement))

            conn.commit()
