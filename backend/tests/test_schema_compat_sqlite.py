"""SQLite startup migrations must not emit MySQL/Postgres-only ALTER COLUMN DDL."""

from unittest.mock import MagicMock

from sqlalchemy import create_engine, inspect, text

from app.migrations.schema_compat import _migrate_ontology_functions


def test_sqlite_existing_is_derived_property_skips_set_default():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE ontology_functions (
                id VARCHAR(36) PRIMARY KEY,
                is_derived_property TINYINT NOT NULL
            )
            """
        ))
    inspector = inspect(engine)
    with engine.connect() as conn:
        _migrate_ontology_functions(conn, inspector, set(inspector.get_table_names()))

    cols = {c["name"] for c in inspect(engine).get_columns("ontology_functions")}
    assert "is_derived_property" in cols


def test_sqlite_adds_is_derived_property_when_missing():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE ontology_functions (
                id VARCHAR(36) PRIMARY KEY
            )
            """
        ))
    inspector = inspect(engine)
    with engine.connect() as conn:
        _migrate_ontology_functions(conn, inspector, set(inspector.get_table_names()))

    cols = {c["name"] for c in inspect(engine).get_columns("ontology_functions")}
    assert "is_derived_property" in cols


def test_mysql_sets_default_when_is_derived_property_exists():
    conn = MagicMock()
    conn.dialect.name = "mysql"
    inspector = MagicMock()
    inspector.get_columns.return_value = [{"name": "is_derived_property"}]

    _migrate_ontology_functions(conn, inspector, {"ontology_functions"})

    executed_sql = " ".join(str(call.args[0]) for call in conn.execute.call_args_list)
    assert "ALTER COLUMN is_derived_property SET DEFAULT 0" in executed_sql
