"""AssetService — Asset Catalog 资产管理。

职责：
- Asset CRUD（含 sql_view 注册时自动提取 dependencies）
- 5 种 document 接入：file / oss / directory / api / mq（替代旧 /datasources/{upload,api-source,oss-source,dir-source,mq-source}）
- 元数据探测：sync_schema / profile / preview（结构化）
- 反向引用查询：get_with_usage（左面板：Binding/Builder/Rule/Action 引用）
- 凭据：OSS/API/MQ 等带敏感凭据的接入 → 走 vault.store 写 ref（**不入库明文**）
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_usage import AssetUsage
from app.models.execution_log import ExecutionLog
from app.models.quality_metric import QualityMetric
from app.models.quality_rule import HealthStatus, QualityRule
from app.repositories.asset_repo import AssetRepository
from app.repositories.asset_usage_repo import AssetUsageRepository
from app.repositories.connection_repo import ConnectionRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane import sql_introspect
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.credential_vault import get_vault
from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)


# ── 主服务 ──────────────────────────────────────────────────────

class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AssetRepository(db)
        self.usage = AssetUsageRepository(db)
        self.bindings = ObjectBindingRepository(db)
        self.connections = ConnectionRepository(db)
        self.conn_svc = ConnectionService(db)
        self.vault = get_vault()
        self.bus = get_event_bus()

    # ── 树形结构 ──────────────────────────────────────
    def get_tree(self, connection_id: str | None = None) -> list[dict]:
        """返回 connection → table → columns 的树形结构。"""
        from app.models.connection import Connection

        assets = self.repo.list_active_structured()
        if connection_id:
            assets = [a for a in assets if a.connection_id == connection_id]

        conn_map: dict[str, dict] = {}
        for a in assets:
            cid = a.connection_id or "__none__"
            if cid not in conn_map:
                conn = self.db.query(Connection).get(cid) if cid != "__none__" else None
                conn_map[cid] = {
                    "connection_id": cid if cid != "__none__" else None,
                    "connection_name": conn.name if conn else "未关联连接",
                    "db_type": conn.type if conn else None,
                    "database": conn.database if conn else None,
                    "tables": [],
                }
            columns = []
            for col in (a.schema_snapshot or []):
                columns.append({
                    "name": col.get("name", ""),
                    "type": col.get("type", ""),
                    "comment": col.get("comment", ""),
                    "is_pk": col.get("is_pk", False),
                })
            conn_map[cid]["tables"].append({
                "asset_id": a.id,
                "table_name": a.locator.get("table", a.name) if isinstance(a.locator, dict) else a.name,
                "columns": columns,
            })

        return list(conn_map.values())

    # ── 通用 CRUD ──────────────────────────────────────
    def list(self, **filters) -> list[Asset]:
        return self.repo.list(**filters)

    def get(self, asset_id: str) -> Asset | None:
        return self.repo.get_by_id(asset_id)

    def get_by_alias(self, alias: str) -> Asset | None:
        return self.repo.find_by_alias(alias)

    def get_with_usage(self, asset_id: str) -> dict:
        asset = self.repo.get_by_id(asset_id)
        if not asset:
            return {}
        usages = self.usage.list_for_asset(asset_id)
        bindings_by_ot = []
        builder_sessions = []
        rules = []
        actions = []
        for u in usages:
            entry = {"id": u.used_by_id, "note": u.note}
            if u.used_by_kind == "object_binding":
                bindings_by_ot.append(entry)
            elif u.used_by_kind == "builder_session":
                builder_sessions.append(entry)
            elif u.used_by_kind == "rule":
                rules.append(entry)
            elif u.used_by_kind == "action":
                actions.append(entry)
        return {
            "asset": asset,
            "usage": {
                "bindings": bindings_by_ot,
                "builder_sessions": builder_sessions,
                "rules": rules,
                "actions": actions,
            },
            "ref_count": len(usages),
        }

    def register(self, *, name: str, kind: str, locator: dict,
                 connection_id: str | None = None, alias: str | None = None,
                 description: str | None = None, domain: str | None = None,
                 tags: list[str] | None = None, owner: str | None = None,
                 sensitivity_tags: dict | None = None,
                 refresh_policy: str = "on_demand", cache_ttl_seconds: int = 0,
                 user_id: str | None = None) -> Asset:
        if alias and self.repo.find_by_alias(alias):
            raise ValueError(f"alias 已存在: {alias}")
        if kind not in ("table", "sql_view", "document"):
            raise ValueError(f"非法 kind: {kind}")
        self._validate_locator(kind, locator)
        if kind == "document" and locator.get("source_type") == "file":
            # Uploaded files are already registered by the trusted upload ingress.
            # Generic catalog requests must not turn an arbitrary server path into
            # a downloadable/LLM-readable asset (including symlinks out of storage).
            from app.services.data_plane.storage_policy import storage_policy, managed_local_path
            policy = storage_policy(self.db)
            file_path = managed_local_path(self.db, locator.get("file_path"))
            if not file_path.is_file() or file_path.suffix.lower().lstrip(".") not in policy["allowed"]:
                raise ValueError("本地文档不存在或文件类型不允许，请使用文档上传入口")
            locator = {**locator, "file_path": str(file_path)}
        elif kind == "document" and locator.get("source_type") == "directory":
            from app.services.data_plane.storage_policy import managed_local_path
            directory_path = managed_local_path(self.db, locator.get("directory_path"), directory=True)
            if not directory_path.is_dir():
                raise ValueError("源目录不存在或不可读取")
            locator = {**locator, "directory_path": str(directory_path)}
        self._validate_refresh_policy(refresh_policy)
        if kind in {"table", "sql_view"} and not connection_id:
            raise ValueError("结构化资产必须指定数据源 connection_id")
        if kind == "sql_view" and not (locator.get("dependencies")):
            # 注册时自动提取依赖（来自 base table + sql 引用的表名）
            deps = set()
            base_id = locator.get("base_asset_id")
            if base_id:
                base = self.repo.get_by_id(base_id)
                if base and base.kind == "table":
                    t = (base.locator or {}).get("table")
                    if t:
                        deps.add(t)
            if locator.get("sql"):
                conn = self.connections.get_by_id(connection_id) if connection_id else None
                dialect = conn.type if conn else None
                sql = (locator["sql"] or "").replace("{{base}}", "_base_t_")
                for t in sql_introspect.extract_table_refs(sql, dialect=dialect):
                    if t and t != "_base_t_":
                        deps.add(t)
            locator["dependencies"] = sorted(deps)
            if not locator.get("required_params"):
                locator["required_params"] = sql_introspect.extract_placeholders(locator.get("sql") or "")

        asset = Asset(
            name=name, alias=alias, description=description,
            kind=kind, connection_id=connection_id, locator=locator,
            domain=domain, tags=tags or [], owner=owner,
            sensitivity_tags=sensitivity_tags or {},
            refresh_policy=refresh_policy, cache_ttl_seconds=cache_ttl_seconds,
            document_source_type=locator.get("source_type") if kind == "document" else None,
            status="active", created_by=user_id,
        )
        # Validate and capture source schema before making the catalog entry visible.
        if kind == "table" and connection_id:
            from app.connectors import ConnectorRegistry
            connection = self.conn_svc._must_get(connection_id)
            if not connection.enabled:
                raise ValueError("连接已禁用")
            connector = ConnectorRegistry.get(connection.type)
            with self.conn_svc.with_conn(connection_id) as raw:
                schema = connector.get_table_schema(raw, locator["table"], locator.get("database") or connection.database)
            if not schema:
                raise ValueError("源表不存在或没有可读取的字段")
            asset.schema_snapshot = schema
            asset.schema_synced_at = datetime.utcnow()
            asset.primary_key = [column["name"] for column in schema if column.get("is_pk")]
        elif kind == "sql_view":
            from app.connectors import ConnectorRegistry
            base = self.repo.get_by_id(locator["base_asset_id"])
            if not base or base.kind != "table" or base.status != "active" or base.connection_id != connection_id:
                raise ValueError("sql_view 必须引用同一活动连接的 table 资产")
            connection = self.conn_svc._must_get(connection_id)
            if not connection.enabled:
                raise ValueError("连接已禁用")
            connector = ConnectorRegistry.get(connection.type)
            quote = connector.quote_identifier()
            table = (base.locator or {}).get("table", "").replace(quote, quote + quote)
            sql = locator["sql"].replace("{{base}}", quote + table + quote)
            analysis = sql_introspect.introspect(sql, dialect=connection.type)
            if not analysis.ok or not analysis.is_select or analysis.is_dml or analysis.is_ddl:
                raise ValueError("sql_view 只能包含有效的只读单条查询")
            params = {name: None for name in locator.get("required_params") or []}
            alias = "_schema" if connection.type == "oracle" else "AS _schema"
            from app.services.data_plane.execute_service import _execute_with_deadline
            with self.conn_svc.with_conn(connection_id) as raw:
                result = _execute_with_deadline(connector, raw, f"SELECT * FROM ({sql.rstrip(';')}) {alias} WHERE 1=0", params, 5000)
            if not result.get("columns"):
                raise ValueError("sql_view 没有可读取的字段")
            asset.schema_snapshot = [{"name": name, "type": "unknown", "nullable": True, "is_pk": False}
                                     for name in result["columns"]]
            asset.schema_synced_at = datetime.utcnow()
        if kind == "document" and connection_id:
            self._preview_document(asset, 5, persist=False)
            asset.profile = {"source_refresh": {"status": "ok", "at": datetime.utcnow().isoformat(), "error": None}}
        self.repo.create(asset)
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.created", {"asset_id": asset.id, "kind": asset.kind})

        return asset

    def update(self, asset_id: str, **changes) -> Asset:
        asset = self._must_get(asset_id)
        # 不允许改 kind 或 locator 主体；只允许改 owner/tags/desc/sensitivity/cache/refresh
        ALLOWED = {"name", "description", "alias", "domain", "tags", "owner",
                   "sensitivity_tags", "refresh_policy", "cache_ttl_seconds"}
        if "refresh_policy" in changes and changes["refresh_policy"] is not None:
            self._validate_refresh_policy(changes["refresh_policy"])
        for k, v in changes.items():
            if k in ALLOWED and v is not None:
                setattr(asset, k, v)
        self.repo.commit()
        self.repo.refresh(asset)
        return asset

    def deprecate(self, asset_id: str, reason: str | None = None) -> Asset:
        asset = self._must_get(asset_id)
        asset.status = "deprecated"
        if reason:
            asset.description = (asset.description or "") + f"\n[deprecated] {reason}"
        from app.services.data_plane.object_binding_service import ObjectBindingService
        from app.services.data_plane.execute_service import ExecuteService
        bindings = ObjectBindingService(self.db)
        for binding in self.bindings.list(asset_id=asset_id, status="active"):
            binding.status = "needs_review"
            binding.review_reason = "资产已废弃，请重新绑定活动资产"
            bindings._clear_mirrored_attributes(binding, binding.field_mappings or [])
        ExecuteService.invalidate_cache_for_asset(asset_id)
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.deprecated", {"asset_id": asset.id, "reason": reason})
        return asset

    def delete(self, asset_id: str, *, cascade: bool = False) -> None:
        asset = self._must_get(asset_id)
        if not cascade:
            ref_count = self.usage.count_for_asset(asset_id)
            if ref_count > 0:
                raise ValueError(f"资产被 {ref_count} 处引用，无法删除")
            self.repo.delete(asset)
            self.repo.commit()
            return
        # 级联：连同对象绑定、质量规则/指标、引用台账一并强删
        self._cascade_cleanup(asset)
        self.repo.delete(asset)
        self.repo.commit()
        self.bus.emit("asset.deleted", {"asset_id": asset.id, "kind": asset.kind})

    def _cascade_cleanup(self, asset: Asset) -> None:
        """删除 Asset 前清理其全部下游依赖。

        SQLite 默认不强制外键，模型上的 ondelete 不生效，故在应用层手动级联。
        覆盖 6 张引用 assets.id 的表：
        - object_bindings：复用 ObjectBindingService.delete（触发 binding.deleted
          → 反写 EntityAttribute.source_* + 血缘弃用），保持兼容期逻辑一致
        - asset_usage：清剩余反向引用台账（builder_session / rule / action 等）
        - quality_rules + health_statuses：质量契约及其评估留痕
        - quality_metrics：质量指标历史
        - execution_logs：审计日志保留，仅置空 asset_id（等价 SET NULL）
        另：document(oss/api/mq) 资产的 vault 凭据一并清理。
        """
        from app.services.data_plane.object_binding_service import ObjectBindingService

        asset_id = asset.id
        binding_svc = ObjectBindingService(self.db)
        for b in self.bindings.list(asset_id=asset_id):
            binding_svc.delete(b.id)
        # 剩余反向引用台账（object_binding 已在上面随 binding 删除时清除）
        self.db.query(AssetUsage).filter(AssetUsage.asset_id == asset_id).delete()
        self.db.query(HealthStatus).filter(HealthStatus.asset_id == asset_id).delete()
        self.db.query(QualityRule).filter(QualityRule.asset_id == asset_id).delete()
        self.db.query(QualityMetric).filter(QualityMetric.asset_id == asset_id).delete()
        self.db.query(ExecutionLog).filter(ExecutionLog.asset_id == asset_id).update(
            {ExecutionLog.asset_id: None}
        )
        cred_ref = (asset.locator or {}).get("credential_ref")
        if cred_ref:
            try:
                self.vault.delete(cred_ref)
            except Exception:
                logger.exception("vault delete failed for ref=%s", cred_ref)
        self.db.flush()

    # ── 结构化资产元数据 ───────────────────────────────
    def sync_schema(self, asset_id: str) -> dict:
        asset = self._must_get(asset_id)
        if asset.kind not in ("table", "sql_view"):
            raise ValueError("仅 table / sql_view 资产支持 sync_schema")
        if not asset.connection_id:
            raise ValueError("Asset 未关联 connection")
        old = list(asset.schema_snapshot or [])
        if asset.kind == "table":
            new = self.conn_svc.get_table_schema(
                asset.connection_id, (asset.locator or {}).get("table", "")
            )
        else:
            # sql_view：跑 SELECT * FROM (sql) WHERE 1=0 取列描述
            from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
            base_id = (asset.locator or {}).get("base_asset_id")
            base = self.repo.get_by_id(base_id) if base_id else None
            if not base or base.kind != "table":
                raise ValueError("sql_view 缺少有效 base_asset_id")
            connection = self.conn_svc._must_get(asset.connection_id)
            alias = "_v" if connection.type == "oracle" else "AS _v"
            sample_sql = f"SELECT * FROM ({(asset.locator or {}).get('sql','')}) {alias} WHERE 1=0"
            placeholders = (asset.locator or {}).get("required_params") or []
            params = {p: None for p in placeholders}
            r = ExecuteService(self.db).execute(ExecuteRequest(
                asset_id=asset.id, sql=sample_sql, params=params,
                purpose="asset.sync_schema", bypass_cache=True,
            ))
            new = [{"name": c, "type": "unknown", "nullable": True, "is_pk": False, "comment": ""} for c in r.columns]
        diff = self._schema_diff(old, new)
        asset.schema_snapshot = new
        asset.schema_synced_at = datetime.utcnow()
        # 如果有主键且未设置，回填 primary_key
        pk = [c["name"] for c in new if c.get("is_pk")]
        if pk and not asset.primary_key:
            asset.primary_key = pk
        # Invalidate the binding in the same transaction as the schema change.
        # A process-local observer using another database session cannot guarantee this.
        broken_columns = set(diff["removed"]) | {c["name"] for c in diff["type_changed"]}
        if broken_columns:
            from app.services.data_plane.object_binding_service import ObjectBindingService
            binding_service = ObjectBindingService(self.db)
            source_bindings = self.bindings.list(asset_id=asset.id, status="active")
            primary_objects = {b.object_type_id for b in source_bindings if b.role == "primary"}
            for binding in source_bindings:
                used = {m.get("source_column") for m in binding.field_mappings or []} | {binding.id_column, binding.enrichment_source_column}
                if used & broken_columns:
                    binding.status = "needs_review"
                    binding.review_reason = f"asset schema changed: {diff}"
                    binding_service._clear_mirrored_attributes(binding, binding.field_mappings or [])
                    binding_service._remove_auto_rules(binding)
            for object_id in primary_objects:
                for enrichment in self.bindings.list(object_type_id=object_id, role="enrichment", status="active"):
                    if enrichment.primary_source_column in broken_columns:
                        enrichment.status = "needs_review"
                        enrichment.review_reason = f"primary 关联列 schema changed: {diff}"
                        binding_service._clear_mirrored_attributes(enrichment, enrichment.field_mappings or [])
                        binding_service._remove_auto_rules(enrichment)
            from app.repositories.lineage_edge_repo import LineageEdgeRepository
            for binding in source_bindings:
                if binding.status != "active" and not self.bindings.list(object_type_id=binding.object_type_id, asset_id=binding.asset_id, status="active"):
                    LineageEdgeRepository(self.db).deprecate_for_binding(binding.object_type_id, binding.asset_id)
            for object_id in primary_objects:
                for enrichment in self.bindings.list(object_type_id=object_id, role="enrichment", status="needs_review"):
                    if not self.bindings.list(object_type_id=object_id, asset_id=enrichment.asset_id, status="active"):
                        LineageEdgeRepository(self.db).deprecate_for_binding(object_id, enrichment.asset_id)
        from app.services.data_plane.execute_service import ExecuteService
        ExecuteService.invalidate_cache_for_asset(asset.id)
        self.repo.commit()
        self.repo.refresh(asset)
        if diff["added"] or diff["removed"] or diff["type_changed"]:
            self.bus.emit("asset.schema.changed", {"asset_id": asset.id, "diff": diff, "bindings_reviewed": True})
        return {"diff": diff, "schema_snapshot": new}

    def profile(self, asset_id: str) -> dict:
        """跑 row_count + 抽样 + 列空值率。统一通过 ExecuteService。"""
        from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
        asset = self._must_get(asset_id)
        if asset.kind not in ("table", "sql_view"):
            raise ValueError("仅 table / sql_view 资产支持 profile")
        exec_svc = ExecuteService(self.db)
        # 行数
        r = exec_svc.execute(ExecuteRequest(
            asset_id=asset.id, sql="SELECT COUNT(*) AS n FROM <asset>",
            params={}, purpose="asset.profile",
            bypass_cache=True,
        ))
        row_count = int(r.rows[0][0]) if r.rows else 0
        # 列空值率（仅前 8 列，避免大宽表压源端）
        null_ratios: dict[str, float] = {}
        for col in (asset.schema_snapshot or [])[:8]:
            cname = col.get("name")
            if not cname:
                continue
            from app.connectors import ConnectorRegistry
            quote = ConnectorRegistry.get(self.connections.get_by_id(asset.connection_id).type).quote_identifier()
            quoted = quote + cname.replace(quote, quote + quote) + quote
            rr = exec_svc.execute(ExecuteRequest(asset_id=asset.id,
                sql=f"SELECT SUM(CASE WHEN {quoted} IS NULL THEN 1 ELSE 0 END) AS nn FROM <asset>",
                params={}, purpose="asset.profile.null_ratio", bypass_cache=True))
            nulls = int(rr.rows[0][0] or 0) if rr.rows else 0
            null_ratios[cname] = (nulls / row_count) if row_count else 0
        profile = {
            "row_count": row_count,
            "null_ratio": null_ratios,
            "sampled_at": datetime.utcnow().isoformat(),
        }
        asset.profile = profile
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.profile.completed", {"asset_id": asset.id, "row_count": row_count})
        return profile

    def preview(self, asset_id: str, limit: int = 20) -> dict:
        from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
        asset = self._must_get(asset_id)
        if asset.status != "active":
            raise ValueError("资产不是活动状态，无法读取源数据")
        if asset.kind == "document":
            try:
                return self._preview_document(asset, limit)
            except Exception as exc:
                self.db.rollback()
                asset = self._must_get(asset_id)
                asset.profile = {**(asset.profile or {}), "source_refresh": {
                    **((asset.profile or {}).get("source_refresh") or {}), "status": "error",
                    "at": datetime.utcnow().isoformat(),
                    "error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}}
                self.db.commit()
                raise
        connection = self.conn_svc._must_get(asset.connection_id)
        alias = "_preview" if connection.type == "oracle" else "AS _preview"
        table_expr = f"({(asset.locator or {}).get('sql')}) {alias}" if asset.kind == "sql_view" else "<asset>"
        sql = f"SELECT * FROM {table_expr}"
        if connection.type in ("oracle", "sqlserver"):
            sql += " ORDER BY 1 OFFSET 0 ROWS FETCH NEXT :lim ROWS ONLY"
        else:
            sql += " LIMIT :lim"
        # sql_view 可能有 required_params；若无，仅 :lim
        req_params = (asset.locator or {}).get("required_params") or []
        params: dict[str, Any] = {p: None for p in req_params}
        params["lim"] = max(1, min(int(limit), 200))
        r = ExecuteService(self.db).execute(ExecuteRequest(
            asset_id=asset.id, sql=sql, params=params, purpose="asset.preview",
            bypass_cache=True,
        ))
        return {"columns": r.columns, "rows": r.rows, "rows_returned": r.rows_returned}

    # ── 5 种 document 注册 ──────────────────────────────
    def register_document_file(self, *, file_bytes: bytes, filename: str,
                               name: str | None = None, description: str | None = None,
                               domain: str | None = None, tags: list[str] | None = None,
                               user_id: str | None = None) -> Asset:
        ext = (filename or "").rsplit(".", 1)[-1].lower()
        from app.services.data_plane.storage_policy import storage_policy
        policy = storage_policy(self.db)
        if not filename or ext not in policy["allowed"]:
            raise ValueError(f"不允许的文件类型: {ext}")
        if len(file_bytes) > policy["max_bytes"]:
            raise ValueError("文件超过 storage.max_upload_mb 限制")
        type_map = {
            "pdf": "pdf",
            "doc": "word", "docx": "word",
            "xls": "excel", "xlsx": "excel",
            "ppt": "presentation", "pptx": "presentation",
            "png": "image", "jpg": "image", "jpeg": "image", "gif": "image",
            "mp4": "video", "avi": "video", "mov": "video",
            "txt": "text", "md": "text", "csv": "text",
        }
        file_type = type_map.get(ext, "other")
        save_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        summary = ""
        if file_type in ("pdf", "word", "excel", "presentation"):
            from app.services.doc_builder import parse_file_content
            try:
                summary = parse_file_content(filename, file_bytes)[:50_000]
            except Exception as exc:
                raise ValueError(f"文档解析失败（{file_type}）: {exc}") from exc
        elif file_type == "text" or ext in ("json", "owl", "rdf", "ttl"):
            summary = file_bytes.decode("utf-8", errors="replace")[:50_000]
        if policy["backend"] == "local":
            policy["local_path"].mkdir(parents=True, exist_ok=True)
            save_path = str(policy["local_path"] / save_name)
            with open(save_path, "xb") as f:
                f.write(file_bytes)
            locator = {"source_type": "file", "file_path": save_path, "file_type": file_type, "original_name": filename}
        else:
            if not all(policy[k] for k in ("endpoint", "bucket", "access_key", "secret_key")):
                raise ValueError("对象存储缺少 endpoint/bucket/access_key/secret_key；请配置存储项或 MINIO_* 环境变量")
            from app.connectors.s3 import S3Connector
            client = S3Connector()._client(policy, policy)
            client.put_object(Bucket=policy["bucket"], Key=save_name, Body=file_bytes)
            ref = self.vault.store({"access_key": policy["access_key"], "secret_key": policy["secret_key"]})
            locator = {"source_type": "oss", "endpoint": policy["endpoint"], "bucket": policy["bucket"],
                       "prefix": save_name, "object_key": save_name, "credential_ref": ref,
                       "file_type": file_type, "original_name": filename}
        try:
            return self._register_document(
            name=name or filename,
            locator=locator,
            parsed_summary=summary,
            description=description, domain=domain, tags=tags, user_id=user_id,
            )
        except Exception:
            if policy["backend"] == "local":
                Path(save_path).unlink(missing_ok=True)
            else:
                client.delete_object(Bucket=policy["bucket"], Key=save_name)
                self.vault.delete(ref)
            raise

    def register_document_oss(self, *, name: str, endpoint: str, bucket: str,
                              access_key: str, secret_key: str, prefix: str = "",
                              description: str | None = None, domain: str | None = None,
                              tags: list[str] | None = None, user_id: str | None = None) -> Asset:
        # 验连通性
        try:
            import boto3
            from botocore.config import Config as BotoConfig
            s3 = boto3.client(
                "s3", endpoint_url=endpoint,
                aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                config=BotoConfig(connect_timeout=5, retries={"max_attempts": 1}),
            )
            s3.head_bucket(Bucket=bucket)
        except Exception as e:
            raise RuntimeError(f"OSS 连接失败: {e}") from e
        cred_ref = self.vault.store({"access_key": access_key, "secret_key": secret_key})
        return self._register_document(
            name=name,
            locator={
                "source_type": "oss",
                "endpoint": endpoint, "bucket": bucket, "prefix": prefix,
                "credential_ref": cred_ref,
            },
            description=description, domain=domain, tags=tags, user_id=user_id,
        )

    def register_document_directory(self, *, name: str, directory_path: str,
                                    file_extensions: list[str] | None = None,
                                    description: str | None = None, domain: str | None = None,
                                    tags: list[str] | None = None,
                                    user_id: str | None = None) -> Asset:
        from app.services.data_plane.storage_policy import managed_local_path
        directory_path = str(managed_local_path(self.db, directory_path, directory=True))
        if not os.path.isdir(directory_path):
            raise RuntimeError(f"目录不存在或无法访问: {directory_path}")
        return self._register_document(
            name=name,
            locator={
                "source_type": "directory",
                "directory_path": directory_path,
                "file_extensions": file_extensions or [],
            },
            description=description, domain=domain, tags=tags, user_id=user_id,
        )

    def register_document_api(self, *, name: str, api_url: str, api_method: str = "GET",
                              api_headers: dict | None = None, api_body: str | None = None,
                              poll_interval: int = 60, description: str | None = None,
                              domain: str | None = None, tags: list[str] | None = None,
                              user_id: str | None = None) -> Asset:
        locator = {"source_type": "api", "api_url": api_url, "api_method": api_method,
                   "api_headers": api_headers or {}, "api_body": api_body, "poll_interval": poll_interval}
        self._validate_locator("document", locator)
        provisional = Asset(name=name, kind="document", document_source_type="api", status="active", locator=locator)
        preview = self._request_document_api(provisional, locator, {})[1][:50000]
        # 凭据：如果 headers 含 Authorization/Token，转入 vault
        cred_ref = None
        clean_headers = dict(api_headers or {})
        sensitive_headers = {}
        for k in list(clean_headers.keys()):
            if k.lower() in ("authorization", "x-api-key", "x-token", "cookie"):
                sensitive_headers[k] = clean_headers.pop(k)
        if sensitive_headers:
            cred_ref = self.vault.store({"headers": sensitive_headers})
        asset = self._register_document(
            name=name,
            locator={
                "source_type": "api",
                "api_url": api_url, "api_method": api_method,
                "api_headers": clean_headers, "api_body": api_body,
                "poll_interval": poll_interval,
                "credential_ref": cred_ref,
            },
            parsed_summary=preview,
            description=description, domain=domain, tags=tags, user_id=user_id,
        )
        return asset

    def register_document_mq(self, *, name: str, host: str, port: int = 9092,
                             topic: str, group: str = "ontology-consumer",
                             username: str = "", password: str = "",
                             poll_interval: int = 60, description: str | None = None,
                             domain: str | None = None, tags: list[str] | None = None,
                             user_id: str | None = None) -> Asset:
        from app.connectors.kafka import KafkaConnector
        params = {"host": host, "port": port}
        credentials = {"username": username, "password": password} if username or password else None
        topics = KafkaConnector().list_topics(params=params, credential=credentials)
        if topic not in topics:
            raise ValueError(f"Kafka topic 不存在或无权访问: {topic}")
        cred_ref = None
        if username or password:
            cred_ref = self.vault.store({"username": username, "password": password})
        return self._register_document(
            name=name,
            locator={
                "source_type": "mq",
                "host": host, "port": port,
                "topic": topic, "group": group,
                "poll_interval": poll_interval,
                "credential_ref": cred_ref,
            },
            description=description, domain=domain, tags=tags, user_id=user_id,
        )

    # ── 内部 ───────────────────────────────────────────
    def _register_document(self, *, name: str, locator: dict,
                           parsed_summary: str | None = None,
                           description: str | None = None, domain: str | None = None,
                           tags: list[str] | None = None,
                           user_id: str | None = None) -> Asset:
        self._validate_locator("document", locator)
        asset = Asset(
            name=name, kind="document", connection_id=None, locator=locator,
            description=description, domain=domain, tags=tags or [],
            document_source_type=locator.get("source_type"),
            parsed_summary=parsed_summary,
            status="active", created_by=user_id,
        )
        self.repo.create(asset)
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.created", {"asset_id": asset.id, "kind": "document",
                                         "source_type": locator.get("source_type")})
        return asset

    def _document_source(self, asset: Asset) -> tuple[str, dict, dict]:
        if asset.kind != "document" or asset.status != "active":
            raise ValueError("只能读取活动文档资产")
        st = asset.document_source_type or (asset.locator or {}).get("source_type")
        loc = dict(asset.locator or {})
        credentials = self.vault.fetch(loc["credential_ref"]) if loc.get("credential_ref") else {}
        if asset.connection_id:
            connection = self.conn_svc._must_get(asset.connection_id)
            if not connection.enabled:
                raise ValueError("文档数据源连接已禁用")
            expected = {"s3": "object_storage", "oss": "object_storage", "api": "api", "mq": "message_queue"}.get(st)
            if connection.category != expected:
                raise ValueError("文档来源与所选Connection类别不一致")
            credentials = self.vault.fetch(connection.credential_ref) if connection.credential_ref else {}
            loc = {**(connection.params or {}), **loc}
            loc.setdefault("host", connection.host)
            loc.setdefault("port", connection.port)
        if st in {"file", "directory"}:
            from app.services.data_plane.storage_policy import managed_local_path
            key = "file_path" if st == "file" else "directory_path"
            loc[key] = str(managed_local_path(self.db, loc.get(key), directory=st == "directory"))
        return st, loc, credentials

    def _parse_document_bytes(self, filename: str, raw: bytes) -> str:
        from app.services.data_plane.storage_policy import storage_policy
        if len(raw) > storage_policy(self.db)["max_bytes"]:
            raise ValueError("文档超过 storage.max_upload_mb 限制")
        ext = str(filename).rsplit(".", 1)[-1].lower()
        if ext in {"doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf"}:
            from app.services.doc_builder import parse_file_content
            return parse_file_content(filename, raw)
        if ext in {"txt", "md", "json", "csv", "owl", "rdf", "ttl"}:
            return raw.decode("utf-8", errors="replace")
        raise ValueError("此资产为非文本资源，无法用于文档正文构建")

    def _request_document_api(self, asset: Asset, loc: dict, credentials: dict) -> tuple[str, str]:
        import httpx
        from app.connectors.http_api import _build_client
        from app.services.data_plane.storage_policy import storage_policy
        if asset.connection_id:
            client = _build_client(loc, credentials)
            method, url, body = loc.get("method", "GET"), loc.get("path") or "/", loc.get("body")
        else:
            headers = {**(loc.get("api_headers") or {}), **credentials.get("headers", {})}
            client = httpx.Client(headers=headers, timeout=10)
            method, url, body = loc.get("api_method", "GET"), loc["api_url"], loc.get("api_body")
        maximum = storage_policy(self.db)["max_bytes"]
        with client:
            try:
                with client.stream(method, url, content=body) as response:
                    if not response.is_success:
                        raise ValueError(f"文档 API 抓取失败：HTTP {response.status_code}")
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        payload.extend(chunk)
                        if len(payload) > maximum:
                            raise ValueError("文档 API 正文超过 storage.max_upload_mb 限制")
                    return str(response.url).split("?", 1)[0], payload.decode(response.encoding or "utf-8", errors="replace")
            except httpx.HTTPError as exc:
                # httpx's URL can contain a query API key; do not expose it in UI/logs.
                raise RuntimeError(f"文档 API 抓取失败：{type(exc).__name__}") from None

    def read_document_content(self, asset: Asset) -> str:
        """Read actual, untruncated text. Catalog summaries remain limited to 50k chars.

        Directory/prefix catalogs are not document bodies. MQ is explicitly a bounded
        sample (max 200 messages) and never advances any group offset.
        """
        st, loc, credentials = self._document_source(asset)
        from app.services.data_plane.storage_policy import storage_policy
        maximum = storage_policy(self.db)["max_bytes"]
        if st == "file":
            path = Path(loc.get("file_path") or "")
            if not path.is_file():
                raise ValueError("文档源文件不存在或不可读取")
            with path.open("rb") as source:
                raw = source.read(maximum + 1)
            return self._parse_document_bytes(loc.get("original_name") or path.name, raw)
        if st in ("oss", "s3"):
            key = loc.get("key") or loc.get("object_key")
            if not key:
                raise ValueError("对象存储目录不是文档正文，请先选择明确的对象 key")
            from app.connectors.s3 import S3Connector
            response = S3Connector()._client(loc, credentials).get_object(Bucket=loc["bucket"], Key=key)
            source = response["Body"]
            try:
                raw = source.read(maximum + 1)
            finally:
                source.close()
            return self._parse_document_bytes(loc.get("original_name") or key, raw)
        if st == "api":
            return self._request_document_api(asset, loc, credentials)[1]
        if st == "mq":
            import json
            from app.connectors.kafka import KafkaConnector
            messages = KafkaConnector().sample_messages(params=loc, credential=credentials, limit=200)
            content = json.dumps(messages, ensure_ascii=False, default=str)
            if len(content.encode("utf-8")) > maximum:
                raise ValueError("消息正文超过 storage.max_upload_mb 限制")
            return content
        if st == "directory":
            raise ValueError("目录清单不是文档正文，请先注册或选择明确的文件")
        raise ValueError("不支持的文档来源")

    def _preview_document(self, asset: Asset, limit: int, *, persist: bool = True) -> dict:
        st, loc, credentials = self._document_source(asset)
        summary = None
        if st == "file":
            if loc.get("file_type") in {"image", "video", "other"}:
                if not Path(loc.get("file_path") or "").is_file():
                    raise ValueError("源文件不存在或不可读取")
                result = {"file_path": loc.get("file_path"), "file_type": loc.get("file_type"), "summary": ""}
            else:
                summary = self.read_document_content(asset)
                result = {"file_path": loc.get("file_path"), "file_type": loc.get("file_type"), "summary": summary[:5000]}
        elif st == "directory":
            root = Path(loc.get("directory_path", ""))
            if not root.is_dir():
                raise ValueError("源目录不存在或不可读取")
            extensions = {str(e).lower().lstrip(".") for e in loc.get("file_extensions", [])}
            entries = [p.name for p in sorted(root.iterdir())
                       if p.is_file() and (not extensions or p.suffix.lower().lstrip(".") in extensions)][:max(1, min(limit, 200))]
            result = {"directory_path": str(root), "files": entries}
        elif st in ("oss", "s3"):
            from app.connectors.s3 import S3Connector
            key = loc.get("key") or loc.get("object_key")
            objects = S3Connector().list_objects(params=loc, credential=credentials,
                prefix=key or loc.get("prefix", ""), limit=max(1, min(limit, 200)))
            if key:
                try:
                    summary = self.read_document_content(asset)
                except ValueError as exc:
                    if "非文本资源" not in str(exc):
                        raise
            result = {"endpoint": loc.get("endpoint"), "bucket": loc.get("bucket"),
                      "prefix": loc.get("prefix"), "objects": objects, "summary": (summary or "")[:5000]}
        elif st == "api":
            api_url, summary = self._request_document_api(asset, loc, credentials)
            result = {"api_url": api_url, "summary": summary[:5000]}
        elif st == "mq":
            from app.connectors.kafka import KafkaConnector
            import json
            messages = KafkaConnector().sample_messages(params=loc, credential=credentials, limit=max(1, min(limit, 200)))
            summary = json.dumps(messages, ensure_ascii=False, default=str)
            result = {"host": loc.get("host"), "topic": loc.get("topic"), "messages": messages}
        else:
            raise ValueError("不支持的文档来源")
        if summary is not None:
            asset.parsed_summary = summary[:50000]
        import hashlib
        previous = ((asset.profile or {}).get("source_refresh") or {})
        asset.profile = {**(asset.profile or {}), "source_refresh": {
            **previous, "status": "ok", "at": datetime.utcnow().isoformat(), "error": None,
            "content_sha256": hashlib.sha256(summary.encode()).hexdigest() if summary is not None else None}}
        if persist:
            self.db.add(asset)
            self.db.commit()
        return result

    def _validate_locator(self, kind: str, locator: dict) -> None:
        if kind == "table":
            if not (locator.get("table")):
                raise ValueError("table 资产 locator 必须含 table")
        elif kind == "sql_view":
            if not (locator.get("base_asset_id") and locator.get("sql")):
                raise ValueError("sql_view 资产 locator 必须含 base_asset_id 与 sql")
        elif kind == "document":
            st = locator.get("source_type")
            if st not in ("file", "oss", "s3", "directory", "api", "mq"):
                raise ValueError("document 资产 locator.source_type 非法")
            if st in {"api", "mq"}:
                interval = locator.get("poll_interval", 60)
                if isinstance(interval, bool) or not isinstance(interval, int) or interval < 10:
                    raise ValueError("poll_interval 必须为至少 10 秒的整数")
                if st == "mq" and not locator.get("topic"):
                    raise ValueError("消息来源必须指定 topic")

    @staticmethod
    def _validate_refresh_policy(policy: str) -> None:
        if policy not in {"on_demand", "hourly", "daily"}:
            raise ValueError("refresh_policy 必须为 on_demand/hourly/daily")

    @staticmethod
    def _schema_diff(old: list[dict], new: list[dict]) -> dict:
        old_map = {c["name"]: c for c in (old or [])}
        new_map = {c["name"]: c for c in (new or [])}
        added = sorted(set(new_map) - set(old_map))
        removed = sorted(set(old_map) - set(new_map))
        type_changed = []
        for name in set(new_map) & set(old_map):
            if (old_map[name].get("type") != new_map[name].get("type")):
                type_changed.append({"name": name,
                                     "old": old_map[name].get("type"),
                                     "new": new_map[name].get("type")})
        return {"added": added, "removed": removed, "type_changed": type_changed}

    def _must_get(self, asset_id: str) -> Asset:
        a = self.repo.get_by_id(asset_id)
        if not a:
            raise LookupError(f"资产不存在: {asset_id}")
        return a
