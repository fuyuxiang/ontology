import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db_compat import ensure_legacy_schema_compat


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE business_rules (
              id VARCHAR(36) PRIMARY KEY,
              entity_id VARCHAR(36),
              name VARCHAR(200) NOT NULL,
              condition_expr TEXT NOT NULL,
              action_desc TEXT NOT NULL,
              status VARCHAR(20) DEFAULT 'active',
              priority VARCHAR(10) DEFAULT 'medium',
              trigger_count INTEGER DEFAULT 0,
              last_triggered DATETIME,
              created_at DATETIME,
              updated_at DATETIME
            )
        """))

    ensure_legacy_schema_compat(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("business_rules")}
    expected = {
        "conditions_json",
        "rule_meta_json",
        "description",
        "tags",
        "input_params",
        "output_schema",
        "action_id",
    }
    missing = expected - columns
    assert not missing, f"missing migrated columns: {sorted(missing)}"
    print("legacy schema compatibility adds missing business_rules columns")


if __name__ == "__main__":
    main()
