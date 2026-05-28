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
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_usage import AssetUsage
from app.models.business_document import BusinessDocument
from app.repositories.asset_repo import AssetRepository
from app.repositories.asset_usage_repo import AssetUsageRepository
from app.repositories.connection_repo import ConnectionRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane import sql_introspect
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.credential_vault import get_vault
from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)


_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


# ── 文档解析 ─────────────────────────────────────────────────────

def _parse_document_summary(path: str, file_type: str, max_chars: int = 50_000) -> str:
    """解析文档为纯文本摘要（限 50KB）。失败返回空字符串。"""
    try:
        if file_type == "pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
                return text[:max_chars]
        if file_type == "word":
            from docx import Document
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs)[:max_chars]
        if file_type == "excel":
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    lines.append("\t".join(str(c) if c is not None else "" for c in row))
            return "\n".join(lines)[:max_chars]
    except Exception:
        logger.exception("文档解析失败: %s", path)
        return ""
    return ""


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
        self.repo.create(asset)
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.created", {"asset_id": asset.id, "kind": asset.kind})

        # 自动同步 schema（仅 table 类型；失败不阻断创建）
        if asset.kind == "table" and asset.connection_id:
            try:
                self.sync_schema(asset.id)
                self.repo.refresh(asset)
            except Exception as e:
                logger.warning(
                    "auto sync_schema failed for asset %s (%s): %s",
                    asset.id, asset.name, e,
                )

        return asset

    def update(self, asset_id: str, **changes) -> Asset:
        asset = self._must_get(asset_id)
        # 不允许改 kind 或 locator 主体；只允许改 owner/tags/desc/sensitivity/cache/refresh
        ALLOWED = {"name", "description", "alias", "domain", "tags", "owner",
                   "sensitivity_tags", "refresh_policy", "cache_ttl_seconds"}
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
        self.repo.commit()
        self.repo.refresh(asset)
        self.bus.emit("asset.deprecated", {"asset_id": asset.id, "reason": reason})
        return asset

    def delete(self, asset_id: str) -> None:
        asset = self._must_get(asset_id)
        ref_count = self.usage.count_for_asset(asset_id)
        if ref_count > 0:
            raise ValueError(f"资产被 {ref_count} 处引用，无法删除")
        self.repo.delete(asset)
        self.repo.commit()

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
            from app.services.data_plane.execute_service import ExecuteService, ExecuteRequest
            base_id = (asset.locator or {}).get("base_asset_id")
            base = self.repo.get_by_id(base_id) if base_id else None
            if not base or base.kind != "table":
                raise ValueError("sql_view 缺少有效 base_asset_id")
            sample_sql = f"SELECT * FROM ({(asset.locator or {}).get('sql','')}) AS _v WHERE 1=0"
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
        self.repo.commit()
        self.repo.refresh(asset)
        if diff["added"] or diff["removed"] or diff["type_changed"]:
            self.bus.emit("asset.schema.changed", {"asset_id": asset.id, "diff": diff})
        return {"diff": diff, "schema_snapshot": new}

    def profile(self, asset_id: str) -> dict:
        """跑 row_count + 抽样 + 列空值率。统一通过 ExecuteService。"""
        from app.services.data_plane.execute_service import ExecuteService, ExecuteRequest
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
            try:
                rr = exec_svc.execute(ExecuteRequest(
                    asset_id=asset.id,
                    sql=f"SELECT SUM(CASE WHEN {cname} IS NULL THEN 1 ELSE 0 END) AS nn FROM <asset>",
                    params={}, purpose="asset.profile.null_ratio",
                    bypass_cache=True,
                ))
                nulls = int(rr.rows[0][0]) if rr.rows else 0
                null_ratios[cname] = (nulls / row_count) if row_count else 0
            except Exception:
                continue
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
        from app.services.data_plane.execute_service import ExecuteService, ExecuteRequest
        asset = self._must_get(asset_id)
        if asset.kind == "document":
            return self._preview_document(asset, limit)
        sql = "SELECT * FROM <asset> LIMIT :lim"
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
        type_map = {
            "pdf": "pdf",
            "doc": "word", "docx": "word",
            "xls": "excel", "xlsx": "excel",
            "png": "image", "jpg": "image", "jpeg": "image", "gif": "image",
            "mp4": "video", "avi": "video", "mov": "video",
            "txt": "text", "md": "text", "csv": "text",
        }
        file_type = type_map.get(ext, "other")
        save_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        save_path = os.path.join(_UPLOAD_DIR, save_name)
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        summary = _parse_document_summary(save_path, file_type) if file_type in ("pdf", "word", "excel") else ""
        return self._register_document(
            name=name or filename,
            locator={"source_type": "file", "file_path": save_path, "file_type": file_type, "original_name": filename},
            parsed_summary=summary,
            description=description, domain=domain, tags=tags, user_id=user_id,
        )

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
            raise RuntimeError(f"OSS 连接失败: {e}")
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
        # 试探一次
        preview = ""
        status_ok = True
        try:
            import httpx
            resp = httpx.request(api_method, api_url, headers=api_headers or {},
                                 content=api_body, timeout=10)
            preview = resp.text[:2000]
            status_ok = resp.status_code < 400
        except Exception as e:
            preview = f"[抓取失败] {e}"
            status_ok = False
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
            parsed_summary=preview if status_ok else None,
            description=description, domain=domain, tags=tags, user_id=user_id,
        )
        return asset

    def register_document_mq(self, *, name: str, host: str, port: int = 9092,
                             topic: str, group: str = "ontology-consumer",
                             username: str = "", password: str = "",
                             poll_interval: int = 60, description: str | None = None,
                             domain: str | None = None, tags: list[str] | None = None,
                             user_id: str | None = None) -> Asset:
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

    def _preview_document(self, asset: Asset, limit: int) -> dict:
        st = asset.document_source_type
        loc = asset.locator or {}
        if st == "file":
            return {"file_path": loc.get("file_path"), "file_type": loc.get("file_type"),
                    "summary": (asset.parsed_summary or "")[:5000]}
        if st == "directory":
            try:
                entries = sorted(os.listdir(loc.get("directory_path", "")))[:limit]
                return {"directory_path": loc.get("directory_path"), "files": entries}
            except Exception as e:
                return {"directory_path": loc.get("directory_path"), "error": str(e)}
        if st == "oss":
            return {"endpoint": loc.get("endpoint"), "bucket": loc.get("bucket"),
                    "prefix": loc.get("prefix"), "note": "对象存储清单延迟拉取"}
        if st == "api":
            return {"api_url": loc.get("api_url"), "summary": (asset.parsed_summary or "")[:5000]}
        if st == "mq":
            return {"host": loc.get("host"), "topic": loc.get("topic"),
                    "note": "MQ 消息样本由后台 consumer 异步采样"}
        return {"summary": (asset.parsed_summary or "")[:2000]}

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
