"""
启动时 Schema 兼容迁移 — 从 main.py lifespan 提取。

NOTE: 这是临时方案。正式环境应迁移到 Alembic 版本化迁移框架。
"""
import logging
from sqlalchemy import inspect as sa_inspect, Engine

from .schema_compat import (
    _migrate_rename_schema_json,
    _migrate_datasources,
    _drop_business_rules,
    _migrate_entity_actions,
    _migrate_entity_attributes,
    _migrate_agents,
    _migrate_aip_scenes,
    _migrate_audit_log,
    _migrate_skills,
    _migrate_ontology_entities,
    _migrate_users,
    _migrate_ontology_functions,
    _migrate_ontology_isolation,
)

logger = logging.getLogger(__name__)


def run_startup_migrations(engine: Engine) -> None:
    """执行所有启动时的 schema 兼容迁移（幂等）。"""
    inspector = sa_inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        _migrate_rename_schema_json(conn, inspector, tables)
        _migrate_datasources(conn, inspector, tables)
        _drop_business_rules(conn, inspector, tables)
        _migrate_entity_actions(conn, inspector, tables)
        _migrate_entity_attributes(conn, inspector, tables)
        _migrate_agents(conn, inspector, tables)
        _migrate_aip_scenes(conn, inspector, tables)
        _migrate_audit_log(conn, inspector, tables)
        _migrate_skills(conn, inspector, tables)
        _migrate_ontology_entities(conn, inspector, tables)
        _migrate_users(conn, inspector, tables)
        _migrate_ontology_functions(conn, inspector, tables)
        _migrate_ontology_isolation(conn, inspector, tables)

    logger.info("Schema 兼容迁移完成")
