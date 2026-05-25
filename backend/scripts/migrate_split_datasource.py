"""M1 数据迁移脚本 — 将旧 DataSource / BusinessDocument 拆分到 Connection / Asset。

执行：python -m backend.scripts.migrate_split_datasource [--dry-run]

幂等：通过 Asset.legacy_datasource_id / legacy_business_document_id 反查；
重跑只补缺失，不重复创建。

迁移规则：
- DataSource(source_category='database')，按 (type, host, port, database, username) 聚合 → 1 条 Connection
  - 该组每条 DataSource → 1 条 Asset(kind=table, locator={"table": ds.table_name})
  - 旧 password 明文 → vault.store；UPDATE datasources SET password=''
- DataSource(source_category in 'file/api/mq')：
  - file_type='oss'  → Asset(kind=document, source_type=oss)
  - type='directory' → Asset(kind=document, source_type=directory)
  - source_category='api'  → Asset(kind=document, source_type=api)
  - source_category='mq'   → Asset(kind=document, source_type=mq)
  - 其他 file_type   → Asset(kind=document, source_type=file)
- BusinessDocument → Asset(kind=document, source_type=file)
- EntityAttribute.source_table/source_field → 推导出对应的 ObjectBinding（每个 (entity_id, table_name) 一条 binding）
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401 触发模型注册

from app.models.asset import Asset
from app.models.business_document import BusinessDocument
from app.models.connection import Connection
from app.models.datasource import DataSource
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.asset_usage_repo import AssetUsageRepository
from app.repositories.connection_repo import ConnectionRepository
from app.services.data_plane.credential_vault import get_vault

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrate")


@dataclass
class Stats:
    connections_created: int = 0
    assets_table_created: int = 0
    assets_document_created: int = 0
    bindings_created: int = 0
    passwords_rekeyed: int = 0
    skipped_existing: int = 0


def main(dry_run: bool = False) -> int:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    stats = Stats()
    try:
        _migrate_db_sources(db, stats, dry_run)
        db.flush()
        _migrate_non_db_sources(db, stats, dry_run)
        db.flush()
        _migrate_business_documents(db, stats, dry_run)
        db.flush()
        _migrate_attribute_mappings(db, stats, dry_run)
        if not dry_run:
            db.commit()
            _rekey_passwords_post(db, stats)
        else:
            db.rollback()
    except Exception:
        db.rollback()
        logger.exception("迁移失败，已回滚")
        return 1
    finally:
        db.close()

    logger.info("=== 迁移结果 ===")
    logger.info("Connection 新建: %d", stats.connections_created)
    logger.info("Asset(table) 新建: %d", stats.assets_table_created)
    logger.info("Asset(document) 新建: %d", stats.assets_document_created)
    logger.info("ObjectBinding 新建: %d", stats.bindings_created)
    logger.info("已存在跳过: %d", stats.skipped_existing)
    logger.info("密码重密钥化: %d", stats.passwords_rekeyed)
    if dry_run:
        logger.info("(dry-run，所有写入已回滚)")
    return 0


# ── 1. database 类 DataSource → Connection + Asset(table) ───────

def _migrate_db_sources(db, stats: Stats, dry_run: bool) -> None:
    rows = db.query(DataSource).filter(
        (DataSource.source_category == "database") | (DataSource.source_category == "")
    ).all()
    # 数据库类型识别
    db_types = {"mysql", "postgresql", "oracle", "sqlserver", "hive", "clickhouse"}
    db_rows = [r for r in rows if (r.type or "").lower() in db_types]

    grouped: dict[tuple, list[DataSource]] = defaultdict(list)
    for ds in db_rows:
        key = (ds.type, ds.host, ds.port, ds.database or "", ds.username or "")
        grouped[key].append(ds)

    repo = ConnectionRepository(db)
    asset_repo = AssetRepository(db)
    vault = get_vault()

    for (typ, host, port, database, username), items in grouped.items():
        # 找已迁移 connection（按 type+host+port+database+username name 推断）
        proposed_name = _connection_name(typ, host, port, database, items[0].name)
        existing_conn = repo.find_by_name(proposed_name)
        if existing_conn:
            conn = existing_conn
            stats.skipped_existing += 1
        else:
            password = items[0].password or ""
            ref = vault.store({"username": username, "password": password})
            conn = Connection(
                name=proposed_name,
                type=typ, host=host, port=port, database=database,
                credential_ref=ref, credential_type="local-fernet",
                description=items[0].description or f"自旧 DataSource 迁移（{len(items)} 张表）",
                status="active", enabled=True, writable=False,
            )
            db.add(conn)
            db.flush()
            stats.connections_created += 1

        # 每张表注册 Asset(kind=table)
        for ds in items:
            if not ds.table_name:
                continue
            existing = asset_repo.find_by_legacy_datasource(ds.id)
            if existing:
                stats.skipped_existing += 1
                continue
            asset = Asset(
                name=ds.name or ds.table_name,
                alias=None,
                kind="table",
                connection_id=conn.id,
                locator={"table": ds.table_name},
                description=ds.description,
                domain=None, tags=[],
                refresh_policy="on_demand",
                cache_ttl_seconds=0,
                status="active",
                legacy_datasource_id=ds.id,
            )
            # 行数沿用旧 record_count 作为快速 profile
            if ds.record_count:
                asset.profile = {"row_count": int(ds.record_count), "sampled_at": None}
            db.add(asset)
            stats.assets_table_created += 1


def _connection_name(typ: str, host: str, port: int, database: str, fallback: str) -> str:
    if database:
        return f"{typ}@{host}:{port}/{database}"
    return f"{typ}@{host}:{port}/{fallback or 'default'}"


# ── 2. 非 database 类 DataSource → Asset(document) ──────────────

_NON_DB_CATEGORIES = {"file", "api", "mq"}


def _migrate_non_db_sources(db, stats: Stats, dry_run: bool) -> None:
    rows = db.query(DataSource).filter(
        DataSource.source_category.in_(list(_NON_DB_CATEGORIES))
    ).all()
    asset_repo = AssetRepository(db)
    vault = get_vault()

    for ds in rows:
        if asset_repo.find_by_legacy_datasource(ds.id):
            stats.skipped_existing += 1
            continue
        source_type, locator = _build_document_locator(ds, vault)
        if source_type is None:
            continue
        asset = Asset(
            name=ds.name or ds.id,
            kind="document",
            connection_id=None,
            locator=locator,
            description=ds.description,
            domain=None, tags=[],
            document_source_type=source_type,
            parsed_summary=ds.parsed_content,
            status="active",
            legacy_datasource_id=ds.id,
        )
        db.add(asset)
        stats.assets_document_created += 1


def _build_document_locator(ds: DataSource, vault) -> tuple[str | None, dict]:
    cat = ds.source_category
    if cat == "file":
        # OSS / 普通文件 / 目录
        if ds.file_type == "oss":
            params = ds.params or {}
            cred_ref = vault.store({
                "access_key": params.get("access_key", ""),
                "secret_key": params.get("secret_key", ""),
            })
            return "oss", {
                "source_type": "oss",
                "endpoint": params.get("endpoint", ds.host),
                "bucket": params.get("bucket", ""),
                "prefix": params.get("prefix", ""),
                "credential_ref": cred_ref,
            }
        if ds.type == "directory" or ds.file_type == "directory":
            params = ds.params or {}
            return "directory", {
                "source_type": "directory",
                "directory_path": ds.file_path or "",
                "file_extensions": params.get("file_extensions", []),
            }
        return "file", {
            "source_type": "file",
            "file_path": ds.file_path or "",
            "file_type": ds.file_type or "other",
        }
    if cat == "api":
        cred_ref = None
        sensitive_headers = {}
        clean_headers = dict(ds.api_headers or {})
        for k in list(clean_headers.keys()):
            if k.lower() in ("authorization", "x-api-key", "x-token", "cookie"):
                sensitive_headers[k] = clean_headers.pop(k)
        if sensitive_headers:
            cred_ref = vault.store({"headers": sensitive_headers})
        return "api", {
            "source_type": "api",
            "api_url": ds.api_url or "",
            "api_method": ds.api_method or "GET",
            "api_headers": clean_headers,
            "api_body": ds.api_body,
            "poll_interval": ds.poll_interval or 60,
            "credential_ref": cred_ref,
        }
    if cat == "mq":
        cred_ref = None
        if ds.username or ds.password:
            cred_ref = vault.store({"username": ds.username or "", "password": ds.password or ""})
        return "mq", {
            "source_type": "mq",
            "host": ds.host,
            "port": ds.port,
            "topic": ds.mq_topic or "",
            "group": ds.mq_group or "ontology-consumer",
            "poll_interval": ds.poll_interval or 60,
            "credential_ref": cred_ref,
        }
    return None, {}


# ── 3. BusinessDocument → Asset(document, file) ─────────────────

def _migrate_business_documents(db, stats: Stats, dry_run: bool) -> None:
    asset_repo = AssetRepository(db)
    for doc in db.query(BusinessDocument).all():
        if asset_repo.find_by_legacy_business_document(doc.id):
            stats.skipped_existing += 1
            continue
        summary = doc.summary or (doc.parsed_text or "")[:50_000]
        asset = Asset(
            name=doc.name,
            kind="document",
            connection_id=None,
            locator={
                "source_type": "file",
                "file_path": doc.file_path or "",
                "file_type": doc.file_type or "other",
            },
            description=None,
            domain=None,
            tags=list(doc.domain_tags or []),
            document_source_type="file",
            parsed_summary=summary,
            status="active",
            legacy_business_document_id=doc.id,
        )
        db.add(asset)
        stats.assets_document_created += 1


# ── 4. EntityAttribute.source_table/source_field → ObjectBinding ─

def _migrate_attribute_mappings(db, stats: Stats, dry_run: bool) -> None:
    attrs = db.query(EntityAttribute).filter(
        EntityAttribute.source_table.isnot(None),
        EntityAttribute.source_table != "",
    ).all()
    if not attrs:
        return

    # 按 (entity_id, table_name) 分组
    by_pair: dict[tuple[str, str], list[EntityAttribute]] = defaultdict(list)
    for a in attrs:
        by_pair[(a.entity_id, a.source_table)].append(a)

    asset_repo = AssetRepository(db)
    usage = AssetUsageRepository(db)

    for (entity_id, table_name), atts in by_pair.items():
        # 找该表所属的 Asset（迁移到 Asset 后）
        # 我们无法精确知道是哪个 connection 的同名表；优先匹配第一个 kind=table 的同名 Asset
        candidates = [a for a in db.query(Asset).filter(Asset.kind == "table").all()
                      if (a.locator or {}).get("table") == table_name]
        if not candidates:
            logger.warning("属性映射 %s.%s 对应的 table 资产不存在，跳过", entity_id[:8], table_name)
            continue
        asset = candidates[0]  # 同名表多次时取第一个；运维可后续手工调整
        existing = (
            db.query(ObjectBinding)
            .filter(ObjectBinding.object_type_id == entity_id,
                    ObjectBinding.asset_id == asset.id,
                    ObjectBinding.role == "primary")
            .first()
        )
        if existing:
            stats.skipped_existing += 1
            continue
        binding = ObjectBinding(
            object_type_id=entity_id,
            asset_id=asset.id,
            role="primary",
            field_mappings=[
                {"attribute_id": a.id, "source_column": a.source_field, "transform": None}
                for a in atts if a.source_field
            ],
            id_column=None,
            status="active",
        )
        db.add(binding)
        db.flush()
        usage.upsert(asset.id, "object_binding", binding.id, note="role=primary (migrated)")
        stats.bindings_created += 1


# ── 5. 把所有迁移成功的 DataSource 明文密码清零 ──────────────────

def _rekey_passwords_post(db, stats: Stats) -> None:
    """迁移已 commit 后，把旧 datasources 表里的明文 password 清空。"""
    res = db.execute(text("UPDATE datasources SET password = '' WHERE password IS NOT NULL AND password != ''"))
    stats.passwords_rekeyed = res.rowcount or 0
    db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只统计、不写入；事务回滚")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run))
