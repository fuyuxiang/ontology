"""各表 schema 迁移函数 — 幂等，可重复执行。"""
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import text

logger = logging.getLogger(__name__)


def _get_cols(inspector, table: str) -> set:
    return {c["name"] for c in inspector.get_columns(table)}


def _migrate_rename_schema_json(conn, inspector, tables):
    for tbl in ("ontology_entities", "ontology_version_entities"):
        if tbl in tables:
            cols = _get_cols(inspector, tbl)
            if "schema_json" in cols and "config_json" not in cols:
                conn.execute(text(f"ALTER TABLE {tbl} RENAME COLUMN schema_json TO config_json"))
    conn.commit()


def _migrate_datasources(conn, inspector, tables):
    if "datasources" not in tables:
        return
    cols = _get_cols(inspector, "datasources")
    _add = []
    if "table_name" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN table_name VARCHAR(200) DEFAULT ''")
    if "record_count" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN record_count INTEGER DEFAULT 0")
    if "enabled" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN enabled TINYINT(1) DEFAULT 0")
    if "source_category" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN source_category VARCHAR(20) DEFAULT 'database'")
    for col in ("file_path", "file_type"):
        if col not in cols:
            size = "500" if "path" in col else "20"
            _add.append(f"ALTER TABLE datasources ADD COLUMN {col} VARCHAR({size})")
    if "api_url" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN api_url VARCHAR(500)")
    if "api_method" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN api_method VARCHAR(10) DEFAULT 'GET'")
    if "api_headers" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN api_headers JSON")
    if "api_body" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN api_body TEXT")
    if "mq_topic" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN mq_topic VARCHAR(200)")
    if "mq_group" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN mq_group VARCHAR(200)")
    if "poll_interval" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN poll_interval INTEGER DEFAULT 60")
    if "parsed_content" not in cols:
        _add.append("ALTER TABLE datasources ADD COLUMN parsed_content TEXT")
    for stmt in _add:
        conn.execute(text(stmt))
    if "record_count" not in cols and "table_count" in cols:
        conn.execute(text("UPDATE datasources SET record_count = table_count"))
    conn.commit()


def _drop_business_rules(conn, inspector, tables):
    for tbl in ("business_rules", "ontology_version_rules"):
        if tbl in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
    conn.commit()


def _migrate_entity_actions(conn, inspector, tables):
    if "entity_actions" not in tables:
        return
    cols = _get_cols(inspector, "entity_actions")
    _add = []
    for col in ("parameters_json", "preconditions_json", "effects_json", "action_meta_json", "type_config", "output_schema"):
        if col not in cols:
            _add.append(f"ALTER TABLE entity_actions ADD COLUMN {col} JSON")
    if "description" not in cols:
        _add.append("ALTER TABLE entity_actions ADD COLUMN description TEXT")
    if "category" not in cols:
        _add.append("ALTER TABLE entity_actions ADD COLUMN category VARCHAR(20) DEFAULT 'domain'")
    if "action_type" not in cols:
        _add.append("ALTER TABLE entity_actions ADD COLUMN action_type VARCHAR(30)")
    if "updated_at" not in cols:
        _add.append("ALTER TABLE entity_actions ADD COLUMN updated_at DATETIME")
    for stmt in _add:
        conn.execute(text(stmt))
    if "type" in cols:
        try:
            conn.execute(text("ALTER TABLE entity_actions MODIFY COLUMN `type` VARCHAR(50) NULL"))
        except Exception:
            pass
    conn.commit()
    result = conn.execute(text("SELECT COUNT(*) FROM entity_actions WHERE category IS NULL OR action_type IS NULL"))
    legacy_count = result.scalar()
    if legacy_count and legacy_count > 0:
        conn.execute(text("UPDATE entity_actions SET category = 'domain', action_type = 'custom_script' WHERE category IS NULL OR action_type IS NULL"))
        conn.commit()


def _migrate_entity_attributes(conn, inspector, tables):
    if "entity_attributes" not in tables:
        return
    cols = _get_cols(inspector, "entity_attributes")
    _add = []
    if "source_table" not in cols:
        _add.append("ALTER TABLE entity_attributes ADD COLUMN source_table VARCHAR(200)")
    if "source_field" not in cols:
        _add.append("ALTER TABLE entity_attributes ADD COLUMN source_field VARCHAR(200)")
    if "data_status" not in cols:
        _add.append("ALTER TABLE entity_attributes ADD COLUMN data_status VARCHAR(20) DEFAULT '未确认来源'")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_agents(conn, inspector, tables):
    if "agents" not in tables:
        return
    cols = _get_cols(inspector, "agents")
    _add = []
    for col in ("nodes_json", "edges_json", "ontology_stale_detail"):
        if col not in cols:
            _add.append(f"ALTER TABLE agents ADD COLUMN {col} JSON")
    if "ontology_version_id" not in cols:
        _add.append("ALTER TABLE agents ADD COLUMN ontology_version_id VARCHAR(36)")
    if "ontology_stale" not in cols:
        _add.append("ALTER TABLE agents ADD COLUMN ontology_stale TINYINT(1) NOT NULL DEFAULT 0")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_aip_scenes(conn, inspector, tables):
    if "aip_scenes" not in tables:
        return
    cols = _get_cols(inspector, "aip_scenes")
    _add = []
    if "ontology_version_id" not in cols:
        _add.append("ALTER TABLE aip_scenes ADD COLUMN ontology_version_id VARCHAR(36)")
    if "ontology_stale" not in cols:
        _add.append("ALTER TABLE aip_scenes ADD COLUMN ontology_stale TINYINT(1) NOT NULL DEFAULT 0")
    if "ontology_stale_detail" not in cols:
        _add.append("ALTER TABLE aip_scenes ADD COLUMN ontology_stale_detail JSON")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_audit_log(conn, inspector, tables):
    if "audit_log" not in tables:
        return
    cols = _get_cols(inspector, "audit_log")
    if "details" not in cols:
        conn.execute(text("ALTER TABLE audit_log ADD COLUMN details TEXT"))
    if "status" not in cols:
        conn.execute(text("ALTER TABLE audit_log ADD COLUMN status VARCHAR(16) DEFAULT 'success'"))
    conn.commit()


def _migrate_skills(conn, inspector, tables):
    if "skills" not in tables:
        return
    cols = _get_cols(inspector, "skills")
    _add = []
    if "current_version" not in cols:
        _add.append("ALTER TABLE skills ADD COLUMN current_version INTEGER DEFAULT 0")
    for col in ("input_schema", "output_schema", "tools", "test_cases", "asset_refs"):
        if col not in cols:
            _add.append(f"ALTER TABLE skills ADD COLUMN {col} JSON")
    if "prompt_template" not in cols:
        _add.append("ALTER TABLE skills ADD COLUMN prompt_template TEXT")
    if "created_by" not in cols:
        _add.append("ALTER TABLE skills ADD COLUMN created_by VARCHAR(100) DEFAULT ''")
    if "reviewed_by" not in cols:
        _add.append("ALTER TABLE skills ADD COLUMN reviewed_by VARCHAR(100) DEFAULT ''")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_ontology_entities(conn, inspector, tables):
    if "ontology_entities" not in tables:
        return
    cols = _get_cols(inspector, "ontology_entities")
    if "publish_config" not in cols:
        conn.execute(text("ALTER TABLE ontology_entities ADD COLUMN publish_config JSON"))
        conn.commit()
    if "scenario_codes" not in cols:
        conn.execute(text("ALTER TABLE ontology_entities ADD COLUMN scenario_codes JSON"))
        conn.commit()

    # 版本快照实体表同步补列
    if "ontology_version_entities" in tables:
        ve_cols = _get_cols(inspector, "ontology_version_entities")
        if "scenario_codes" not in ve_cols:
            conn.execute(text("ALTER TABLE ontology_version_entities ADD COLUMN scenario_codes JSON"))
            conn.commit()


def _migrate_users(conn, inspector, tables):
    if "users" not in tables:
        return
    cols = _get_cols(inspector, "users")
    _add = []
    if "email" not in cols:
        _add.append("ALTER TABLE users ADD COLUMN email VARCHAR(100)")
    if "is_active" not in cols:
        _add.append("ALTER TABLE users ADD COLUMN is_active TINYINT(1) DEFAULT 1")
    if "last_login_at" not in cols:
        _add.append("ALTER TABLE users ADD COLUMN last_login_at DATETIME")
    if "updated_at" not in cols:
        _add.append("ALTER TABLE users ADD COLUMN updated_at DATETIME")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_ontology_functions(conn, inspector, tables):
    if "ontology_functions" not in tables:
        return
    cols = _get_cols(inspector, "ontology_functions")
    _add = []
    if "callable_name" not in cols:
        _add.append("ALTER TABLE ontology_functions ADD COLUMN callable_name VARCHAR(100)")
    if "tags" not in cols:
        _add.append("ALTER TABLE ontology_functions ADD COLUMN tags JSON")
    if "is_derived_property" not in cols:
        _add.append("ALTER TABLE ontology_functions ADD COLUMN is_derived_property TINYINT NOT NULL DEFAULT 0")
    else:
        _add.append("ALTER TABLE ontology_functions ALTER COLUMN is_derived_property SET DEFAULT 0")
    if "entity_ids" not in cols:
        _add.append("ALTER TABLE ontology_functions ADD COLUMN entity_ids JSON")
    for stmt in _add:
        conn.execute(text(stmt))
    conn.commit()


def _migrate_ontology_isolation(conn, inspector, tables):
    """添加 ontology_id 列并迁移数据（幂等）。"""
    # --- ontology_entities ---
    if "ontology_entities" in tables:
        cols = _get_cols(inspector, "ontology_entities")
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE ontology_entities ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- ontology_functions ---
    if "ontology_functions" in tables:
        cols = _get_cols(inspector, "ontology_functions")
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE ontology_functions ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- entity_actions ---
    if "entity_actions" in tables:
        cols = _get_cols(inspector, "entity_actions")
        if "ontology_id" not in cols:
            conn.execute(text(
                "ALTER TABLE entity_actions ADD COLUMN ontology_id VARCHAR(36)"
            ))
            conn.commit()

    # --- entity_attributes: shared_attribute_id ---
    if "entity_attributes" in tables:
        cols = _get_cols(inspector, "entity_attributes")
        if "shared_attribute_id" not in cols:
            conn.execute(text(
                "ALTER TABLE entity_attributes ADD COLUMN shared_attribute_id VARCHAR(36)"
            ))
            conn.commit()

    # --- 数据迁移: 按 scenario_codes 分配 ontology_id ---
    if "ontology_entities" in tables and "scenario_dict" in tables:
        # 获取第一个 scenario 作为默认
        result = conn.execute(text("SELECT id FROM scenario_dict ORDER BY sort_order LIMIT 1"))
        row = result.fetchone()
        default_id = row[0] if row else None

        if default_id:
            # 处理有 scenario_codes 的实体
            entities = conn.execute(text(
                "SELECT id, scenario_codes FROM ontology_entities WHERE ontology_id IS NULL"
            )).fetchall()

            for eid, codes_raw in entities:
                codes = json.loads(codes_raw) if codes_raw else []
                if codes:
                    # 获取第一个 code 对应的 scenario id
                    sc = conn.execute(text(
                        "SELECT id FROM scenario_dict WHERE code = :code"
                    ), {"code": codes[0]}).fetchone()
                    ontology_id = sc[0] if sc else default_id
                else:
                    ontology_id = default_id

                conn.execute(text(
                    "UPDATE ontology_entities SET ontology_id = :oid WHERE id = :eid"
                ), {"oid": ontology_id, "eid": eid})

                # 多 scenario_codes 的创建共享引用
                if len(codes) > 1 and "ontology_shared_refs" in tables:
                    for code in codes[1:]:
                        sc = conn.execute(text(
                            "SELECT id FROM scenario_dict WHERE code = :code"
                        ), {"code": code}).fetchone()
                        if sc:
                            ref_id = str(uuid.uuid4())
                            # Check if already exists
                            existing = conn.execute(text(
                                "SELECT id FROM ontology_shared_refs "
                                "WHERE target_ontology_id = :tgt AND entity_id = :eid"
                            ), {"tgt": sc[0], "eid": eid}).fetchone()
                            if not existing:
                                conn.execute(text(
                                    "INSERT INTO ontology_shared_refs "
                                    "(id, source_ontology_id, target_ontology_id, entity_id, shared_at) "
                                    "VALUES (:id, :src, :tgt, :eid, :now)"
                                ), {"id": ref_id, "src": ontology_id, "tgt": sc[0], "eid": eid,
                                    "now": datetime.utcnow()})

            conn.commit()

            # functions: 跟随 entity 或归入默认
            if "ontology_functions" in tables:
                conn.execute(text("""
                    UPDATE ontology_functions SET ontology_id = (
                        SELECT ontology_id FROM ontology_entities
                        WHERE ontology_entities.id = ontology_functions.entity_id
                    ) WHERE entity_id IS NOT NULL AND ontology_id IS NULL
                """))
                conn.execute(text(
                    "UPDATE ontology_functions SET ontology_id = :default WHERE ontology_id IS NULL"
                ), {"default": default_id})
                conn.commit()

            # actions: 跟随 entity 或归入默认
            if "entity_actions" in tables:
                conn.execute(text("""
                    UPDATE entity_actions SET ontology_id = (
                        SELECT ontology_id FROM ontology_entities
                        WHERE ontology_entities.id = entity_actions.entity_id
                    ) WHERE entity_id IS NOT NULL AND ontology_id IS NULL
                """))
                conn.execute(text(
                    "UPDATE entity_actions SET ontology_id = :default WHERE ontology_id IS NULL"
                ), {"default": default_id})
                conn.commit()

    logger.info("本体隔离迁移完成")
