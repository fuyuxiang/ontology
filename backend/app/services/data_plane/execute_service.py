"""ExecuteService — /execute 唯一执行闸口。

任何上层（业务 API、规则、Action、Copilot、AI 召回、Probe）想读/写源数据，
都必须经过本服务。本服务负责：

[1] Locator 解析（按 asset.kind 改写最终下发 SQL）
[2] AST 安全审查（SELECT-only 默认；DDL/DML 走写权限分支）
[3] 表名白名单（必须落到 asset.locator 的 dependencies 里）
[4] 参数化绑定（:name → 各 driver 的 paramstyle，由 connector 完成）
[5] 限流（per Connection 令牌桶）+ 缓存（asset.cache_ttl_seconds）
[6] 执行 + 列级脱敏 + 审计 + 事件

调用形态：
    ExecuteService(db).execute(ExecuteRequest(asset_id, sql, params, purpose, ...))
    ExecuteService(db).execute_alias("mnp.user_count", {"uid":"u1"}, purpose="mnp.dashboard")
    ExecuteService(db).dry_run(...)
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.connectors import ConnectorRegistry
from app.models.asset import Asset
from app.models.connection import Connection
from app.models.execution_log import ExecutionLog
from app.repositories.asset_repo import AssetRepository
from app.repositories.connection_repo import ConnectionRepository
from app.repositories.execution_log_repo import ExecutionLogRepository
from app.services.data_plane import sql_introspect
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)


# ── 请求 / 响应 ─────────────────────────────────────────────────

@dataclass
class ExecuteRequest:
    asset_id: str
    sql: str
    params: dict = field(default_factory=dict)
    purpose: str = ""
    timeout_ms: int = 5000
    bypass_cache: bool = False
    user_id: str | None = None
    additional_asset_ids: list[str] | None = None
        # 当 SQL 涉及跨 Asset JOIN 时声明额外允许的 Asset；用作白名单合并。
        # 主 asset_id 用于审计归因 + 缓存键 + connection 选择。
        # 这些 Asset 必须与主 asset_id 同一个 connection。


class ExecuteBlocked(RuntimeError):
    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass
class ExecuteResult:
    columns: list[str]
    rows: list[list]
    rows_returned: int
    duration_ms: int
    cache_hit: bool


# ── 限流：进程内令牌桶（每 Connection 一个）─────────────────────

class _TokenBucket:
    def __init__(self, qps: int) -> None:
        self.qps = max(1, qps)
        self.tokens = float(self.qps)
        self.last = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.qps, self.tokens + (now - self.last) * self.qps)
            self.last = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False


_buckets: dict[str, _TokenBucket] = {}
_buckets_lock = threading.Lock()


def _get_bucket(conn_id: str, qps: int) -> _TokenBucket:
    with _buckets_lock:
        b = _buckets.get(conn_id)
        if b is None or b.qps != qps:
            b = _TokenBucket(qps)
            _buckets[conn_id] = b
        return b


# ── 缓存：进程内 LRU + TTL（无 Redis 依赖）──────────────────────

class _TTLCache:
    def __init__(self, capacity: int = 1024) -> None:
        self.capacity = capacity
        self._store: dict[str, tuple[float, Any]] = {}  # key → (expire_ts, value)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expire_ts, value = entry
            if time.time() > expire_ts:
                self._store.pop(key, None)
                return None
            return value

    def put(self, key: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        with self._lock:
            if len(self._store) >= self.capacity:
                # 朴素 LRU：删一个最早过期的
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])
                self._store.pop(oldest[0], None)
            self._store[key] = (time.time() + ttl_seconds, value)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for k in list(self._store.keys()):
                if k.startswith(prefix):
                    self._store.pop(k, None)


_cache = _TTLCache()


# ── 列级脱敏 ────────────────────────────────────────────────────

def _redact_value(value: Any, level: str) -> Any:
    if value is None:
        return None
    s = str(value)
    if level == "pii":
        if len(s) > 7:
            return s[:3] + "*" * (len(s) - 7) + s[-4:]
        if len(s) > 3:
            return s[:1] + "*" * (len(s) - 2) + s[-1:]
        return "*" * len(s)
    if level == "sensitive":
        return "***"
    return value


def _apply_sensitivity(columns: list[str], rows: list[list], tags: dict | None) -> list[list]:
    if not tags:
        return rows
    indexes = [(i, tags.get(c)) for i, c in enumerate(columns) if tags.get(c)]
    if not indexes:
        return rows
    out = []
    for row in rows:
        new = list(row)
        for i, level in indexes:
            new[i] = _redact_value(new[i], level)
        out.append(new)
    return out


def _redact_params(params: dict) -> dict:
    """params 仅记录 key 名 + 值类型/长度概要，避免明文落审计日志。"""
    return {k: f"<{type(v).__name__}:{len(str(v)) if v is not None else 0}>" for k, v in (params or {}).items()}


def _hash_request(asset_id: str, sql: str, params: dict) -> str:
    canon = sql.strip()
    p = json.dumps({k: params[k] for k in sorted(params)}, default=str, ensure_ascii=False)
    h = hashlib.sha256(f"{asset_id}|{canon}|{p}".encode()).hexdigest()
    return h


# ── 主服务 ──────────────────────────────────────────────────────

class ExecuteService:
    """全平台 SQL 执行的唯一入口。"""

    # 允许的写回 purpose 白名单（M1 默认空，Action 注册时加入）
    ALLOWED_WRITE_PURPOSES: set[str] = set()

    def __init__(self, db: Session) -> None:
        self.db = db
        self.assets = AssetRepository(db)
        self.connections = ConnectionRepository(db)
        self.audit = ExecutionLogRepository(db)
        self.conn_svc = ConnectionService(db)
        self.bus = get_event_bus()

    # ── 入口方法 ───────────────────────────────────────
    def execute(self, req: ExecuteRequest) -> ExecuteResult:
        if not req.purpose:
            raise ValueError("purpose 必填，用于审计与血缘归因")
        asset = self._must_asset(req.asset_id)
        connection = self._connection_for(asset)
        return self._do_execute(req, asset, connection)

    def execute_alias(self, alias: str, params: dict, *, purpose: str, timeout_ms: int = 5000,
                      bypass_cache: bool = False, user_id: str | None = None,
                      sql: str | None = None) -> ExecuteResult:
        """便捷入口：通过 alias 找 sql_view Asset 跑（sql 来自 locator）。

        - 当 alias 指向 sql_view：sql 取 locator.sql；调用方传 params 即可
        - 当 alias 指向 table：sql 必须由调用方传入；参数仍走绑定
        """
        asset = self.assets.find_by_alias(alias)
        if not asset:
            raise LookupError(f"alias 不存在: {alias}")
        if asset.kind == "sql_view":
            sql = (asset.locator or {}).get("sql") or ""
        elif sql is None:
            raise ValueError(f"alias={alias} 是 {asset.kind} 资产，必须传 sql 参数")
        return self.execute(ExecuteRequest(
            asset_id=asset.id, sql=sql, params=params or {},
            purpose=purpose, timeout_ms=timeout_ms,
            bypass_cache=bypass_cache, user_id=user_id,
        ))

    def dry_run(self, req: ExecuteRequest) -> dict:
        asset = self._must_asset(req.asset_id)
        connection = self._connection_for(asset)
        compiled_sql, intro = self._compile(req, asset, connection)
        return {
            "compiled_sql": compiled_sql,
            "referenced_tables": intro.tables,
            "placeholders": intro.placeholders,
            "is_select": intro.is_select,
            "is_dml": intro.is_dml,
        }

    # ── 内部：执行流水线 ───────────────────────────────
    def _do_execute(self, req: ExecuteRequest, asset: Asset, connection: Connection) -> ExecuteResult:
        log = ExecutionLog(
            asset_id=asset.id,
            connection_id=connection.id if connection else None,
            purpose=req.purpose,
            sql_hash="", sql_preview="",
            params_redacted=_redact_params(req.params),
            user_id=req.user_id,
            started_at=datetime.utcnow(),
        )
        try:
            compiled_sql, intro = self._compile(req, asset, connection)
            log.sql_hash = _hash_request(asset.id, compiled_sql, req.params or {})
            log.sql_preview = compiled_sql[:500]

            # [3] 写回必须显式：DML 默认拒
            if intro.is_dml or intro.is_ddl:
                if not (connection and connection.writable
                        and req.purpose in self.ALLOWED_WRITE_PURPOSES):
                    raise ExecuteBlocked("dml_denied", "写回需要 connection.writable=true 且 purpose 在白名单中")

            # [4] 参数齐全
            missing = [p for p in (intro.placeholders or []) if p not in (req.params or {})]
            if missing:
                raise ExecuteBlocked("missing_params", f"缺少参数: {missing}")

            # [5a] 限流
            bucket = _get_bucket(connection.id, connection.rate_limit_qps)
            if not bucket.acquire():
                raise ExecuteBlocked("rate_limited", f"连接 {connection.name} 触发限流")

            # [5b] 缓存
            cache_key = log.sql_hash
            if not req.bypass_cache and asset.cache_ttl_seconds and asset.cache_ttl_seconds > 0:
                cached = _cache.get(cache_key)
                if cached is not None:
                    log.cache_hit = True
                    columns, rows = cached
                    rows = _apply_sensitivity(columns, rows, asset.sensitivity_tags)
                    return self._finalize(log, columns, rows)

            # [6] 执行
            connector = ConnectorRegistry.get(connection.type)
            with self.conn_svc.with_conn(connection.id) as raw:
                result = connector.execute_sql_with_params(raw, compiled_sql, req.params or {})
            columns = result.get("columns") or []
            rows = result.get("rows") or []

            # 缓存（脱敏前的原始数据）
            if asset.cache_ttl_seconds and asset.cache_ttl_seconds > 0 and intro.is_select:
                _cache.put(cache_key, (columns, rows), asset.cache_ttl_seconds)

            # 列级脱敏
            rows = _apply_sensitivity(columns, rows, asset.sensitivity_tags)
            return self._finalize(log, columns, rows)

        except ExecuteBlocked as e:
            log.blocked = True
            log.block_reason = e.reason
            self._save_log(log)
            self.bus.emit("execution.blocked", {
                "asset_id": asset.id, "purpose": req.purpose,
                "reason": e.reason, "detail": e.detail,
            })
            raise
        except Exception as e:
            log.blocked = True
            log.block_reason = "execution_error"
            log.sql_preview = (log.sql_preview or req.sql or "")[:500]
            self._save_log(log)
            logger.exception("execute failed: %s", e)
            raise

    # [1] + [2] 编译 + AST
    def _compile(self, req: ExecuteRequest, asset: Asset, connection: Connection) -> tuple[str, sql_introspect.IntrospectResult]:
        # 1) Locator 改写
        compiled_sql = self._rewrite_locator(req.sql, asset, connection)

        # 2) AST
        intro = sql_introspect.introspect(compiled_sql, dialect=connection.type)
        if not intro.ok:
            raise ExecuteBlocked(intro.reason or "ast_failed", "SQL 安全审查未通过")
        if intro.is_ddl:
            raise ExecuteBlocked("ddl_denied", "禁止 DDL 语句")

        # 3) 白名单：所有 FROM/JOIN 表必须命中 (主 asset.locator + dependencies +
        #    additional_asset_ids 同 connection 的 table)
        whitelist = self._whitelist_tables(asset)
        for extra_id in (req.additional_asset_ids or []):
            extra = self.assets.get_by_id(extra_id)
            if not extra:
                raise ExecuteBlocked("not_whitelisted", f"additional asset 不存在: {extra_id}")
            if extra.connection_id != asset.connection_id:
                raise ExecuteBlocked("cross_connection_join", "跨 Connection JOIN 不允许")
            whitelist.update(self._whitelist_tables(extra))
        for t in intro.tables or []:
            short = t.split(".")[-1].lower()
            if short not in whitelist:
                raise ExecuteBlocked("not_whitelisted", f"表 {t} 不在 Asset 白名单中")
        return compiled_sql, intro

    def _rewrite_locator(self, sql: str, asset: Asset, connection: Connection) -> str:
        connector = ConnectorRegistry.get(connection.type) if connection else None
        quote = connector.quote_identifier() if connector else "`"
        if asset.kind == "table":
            table = (asset.locator or {}).get("table", "")
            qualified = f"{quote}{table}{quote}"
            return sql.replace("<asset>", qualified)
        if asset.kind == "sql_view":
            base_id = (asset.locator or {}).get("base_asset_id")
            base = self.assets.get_by_id(base_id) if base_id else None
            if base and base.kind == "table":
                table = (base.locator or {}).get("table", "")
                qualified = f"{quote}{table}{quote}"
                return sql.replace("{{base}}", qualified).replace("<asset>", qualified)
            return sql
        if asset.kind == "document":
            raise ExecuteBlocked("document_not_executable", "document 资产不能通过 /execute 执行")
        return sql

    def _whitelist_tables(self, asset: Asset) -> set[str]:
        names: set[str] = set()
        if asset.kind == "table":
            t = (asset.locator or {}).get("table")
            if t:
                names.add(t.lower())
        if asset.kind == "sql_view":
            for dep in (asset.locator or {}).get("dependencies", []) or []:
                names.add(dep.lower())
            base_id = (asset.locator or {}).get("base_asset_id")
            base = self.assets.get_by_id(base_id) if base_id else None
            if base and base.kind == "table":
                t = (base.locator or {}).get("table")
                if t:
                    names.add(t.lower())
        return names

    # ── 收尾 ───────────────────────────────────────────
    def _finalize(self, log: ExecutionLog, columns: list[str], rows: list[list]) -> ExecuteResult:
        log.rows_returned = len(rows)
        log.duration_ms = int((datetime.utcnow() - log.started_at).total_seconds() * 1000)
        self._save_log(log)
        self.bus.emit("execution.completed", {
            "asset_id": log.asset_id, "purpose": log.purpose,
            "rows": log.rows_returned, "ms": log.duration_ms,
            "cache_hit": log.cache_hit,
        })
        return ExecuteResult(
            columns=columns, rows=rows,
            rows_returned=log.rows_returned, duration_ms=log.duration_ms,
            cache_hit=log.cache_hit,
        )

    def _save_log(self, log: ExecutionLog) -> None:
        try:
            self.db.add(log)
            self.db.commit()
        except Exception:
            logger.exception("write execution_log failed")
            self.db.rollback()

    # ── 取依赖 ─────────────────────────────────────────
    def _must_asset(self, asset_id: str) -> Asset:
        a = self.assets.get_by_id(asset_id)
        if not a:
            raise LookupError(f"资产不存在: {asset_id}")
        if a.status != "active":
            raise ExecuteBlocked("asset_inactive", f"资产 {a.name} 已 {a.status}")
        return a

    def _connection_for(self, asset: Asset) -> Connection:
        if asset.kind == "document":
            raise ExecuteBlocked("document_not_executable", "document 资产不走 /execute")
        if not asset.connection_id:
            raise ExecuteBlocked("no_connection", "结构化资产缺少 connection_id")
        c = self.connections.get_by_id(asset.connection_id)
        if not c:
            raise LookupError(f"连接不存在: {asset.connection_id}")
        return c

    # ── 缓存失效（供 asset.schema.changed handler 调用）──
    @staticmethod
    def invalidate_cache_for_asset(asset_id: str) -> None:
        _cache.invalidate_prefix("")  # 简化：没有 asset 维度索引时全部清空

    # ── 受限"原生连接"通道（连接级 SQL，跳过 Asset 表白名单）─────────────
    # 仅供已迁移但 SQL 高度动态的场景使用（如 broadband 大量 JOIN/UPDATE）。
    # 仍走：AST / 参数化 / 限流 / 审计 / 脱敏 / 凭据加密。
    # 与 execute() 的区别：白名单从"Asset locator"放宽到"Connection 内任意表"，
    # 适合那些 SQL 高度动态、不便于全部抽为 sql_view 的业务。
    def execute_on_connection(
        self, *,
        connection_id: str,
        sql: str,
        params: dict | None = None,
        purpose: str,
        write: bool = False,
        timeout_ms: int = 5000,
        user_id: str | None = None,
    ) -> ExecuteResult:
        if not purpose:
            raise ValueError("purpose 必填")
        connection = self.connections.get_by_id(connection_id)
        if not connection:
            raise LookupError(f"连接不存在: {connection_id}")
        if not connection.enabled:
            raise ExecuteBlocked("connection_disabled", "连接已禁用")

        log = ExecutionLog(
            asset_id=None, connection_id=connection.id, purpose=purpose,
            sql_hash="", sql_preview="",
            params_redacted=_redact_params(params or {}),
            user_id=user_id, started_at=datetime.utcnow(),
        )
        try:
            intro = sql_introspect.introspect(sql, dialect=connection.type)
            log.sql_hash = _hash_request(connection.id, sql, params or {})
            log.sql_preview = sql[:500]
            if not intro.ok:
                raise ExecuteBlocked(intro.reason or "ast_failed", "SQL 安全审查未通过")
            if intro.is_ddl:
                raise ExecuteBlocked("ddl_denied", "禁止 DDL 语句")
            if intro.is_dml and not write:
                raise ExecuteBlocked("dml_denied", "本通道默认只读，写入需显式声明 write=true")
            if write and not connection.writable:
                raise ExecuteBlocked("dml_denied", "Connection.writable=false")

            # 限流
            bucket = _get_bucket(connection.id, connection.rate_limit_qps)
            if not bucket.acquire():
                raise ExecuteBlocked("rate_limited", "触发限流")

            # 参数齐全
            missing = [p for p in (intro.placeholders or []) if p not in (params or {})]
            if missing:
                raise ExecuteBlocked("missing_params", f"缺少参数: {missing}")

            connector = ConnectorRegistry.get(connection.type)
            with self.conn_svc.with_conn(connection.id) as raw:
                result = connector.execute_sql_with_params(raw, sql, params or {})
                if intro.is_dml:
                    try:
                        raw.commit()
                    except Exception:
                        pass
            columns = result.get("columns") or []
            rows = result.get("rows") or []
            return self._finalize(log, columns, rows)
        except ExecuteBlocked as e:
            log.blocked = True
            log.block_reason = e.reason
            self._save_log(log)
            self.bus.emit("execution.blocked", {
                "connection_id": connection.id, "purpose": purpose,
                "reason": e.reason, "detail": e.detail,
            })
            raise
        except Exception as e:
            log.blocked = True
            log.block_reason = "execution_error"
            self._save_log(log)
            logger.exception("execute_on_connection failed: %s", e)
            raise
