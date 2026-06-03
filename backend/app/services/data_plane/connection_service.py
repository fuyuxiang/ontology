"""ConnectionService — 连接生命周期 + 凭据加密 + 连接池。

职责：
- 创建/更新/删除/测试 Connection
- 凭据明文一次性进入（API 层），立即 vault.store；DB 中只存 ref
- 维护进程内的连接池缓存（每个 Connection 一个轻量 dict 池）
- 提供 list_databases / list_tables 元数据探测（无副作用）
- 引用计数检查（删除前查 Asset 数量）

关键约束：
- 任何调用方都不应该直接拿到 password 明文；password 仅在本服务内部 _open() 时
  从 vault 取出，传给 connector.connect()，连接对象返回后明文即丢
- ExecuteService 只通过 with_conn() 拿连接，不接触 password
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

from sqlalchemy.orm import Session

from app.connectors import ConnectorRegistry, DATABASE_TYPES
from app.models.connection import (
    Connection, CATEGORY_DATABASE, CATEGORY_OBJECT_STORAGE,
    CATEGORY_FILE_TRANSFER, CATEGORY_MESSAGE_QUEUE, CATEGORY_API,
)
from app.repositories.asset_repo import AssetRepository
from app.repositories.connection_repo import ConnectionRepository
from app.services.data_plane.credential_vault import get_vault
from app.services.data_plane.event_bus import get_event_bus

logger = logging.getLogger(__name__)


# ── 连接池：按 connection_id 维护一个简单的 LIFO 栈 ──────────────
# 不引入 SQLAlchemy engine（异构数据库 driver 各异），自己实现极简池：
# - 每个连接最多空闲 _MAX_IDLE_SECONDS 后关闭
# - 池容量上限按 Connection.pool_size
# - 借用与归还：with_conn() 上下文管理器


_MAX_IDLE_SECONDS = 300


class _PooledConn:
    __slots__ = ("conn", "released_at")

    def __init__(self, conn: Any) -> None:
        self.conn = conn
        self.released_at = time.time()


class _ConnectionPool:
    def __init__(self, capacity: int) -> None:
        self._stack: list[_PooledConn] = []
        self._capacity = max(1, capacity)
        self._lock = threading.Lock()

    def borrow(self) -> Any | None:
        with self._lock:
            while self._stack:
                pooled = self._stack.pop()
                if time.time() - pooled.released_at > _MAX_IDLE_SECONDS:
                    self._safe_close(pooled.conn)
                    continue
                return pooled.conn
        return None

    def release(self, conn: Any) -> None:
        with self._lock:
            if len(self._stack) >= self._capacity:
                self._safe_close(conn)
                return
            self._stack.append(_PooledConn(conn))

    def dispose(self) -> None:
        with self._lock:
            stack, self._stack = self._stack, []
        for p in stack:
            self._safe_close(p.conn)

    @staticmethod
    def _safe_close(conn: Any) -> None:
        try:
            conn.close()
        except Exception:
            logger.exception("connection close failed")


# 进程内单例：connection_id → _ConnectionPool
_pools: dict[str, _ConnectionPool] = {}
_pools_lock = threading.Lock()


def _get_pool(conn_id: str, capacity: int) -> _ConnectionPool:
    with _pools_lock:
        pool = _pools.get(conn_id)
        if pool is None:
            pool = _ConnectionPool(capacity)
            _pools[conn_id] = pool
        return pool


def _dispose_pool(conn_id: str) -> None:
    with _pools_lock:
        pool = _pools.pop(conn_id, None)
    if pool:
        pool.dispose()


# ── 服务 ────────────────────────────────────────────────────────

class ConnectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ConnectionRepository(db)
        self.asset_repo = AssetRepository(db)
        self.vault = get_vault()
        self.bus = get_event_bus()

    # ── CRUD ────────────────────────────────────────────
    def list(self, **filters) -> list[Connection]:
        return self.repo.list(**filters)

    def get(self, conn_id: str) -> Connection | None:
        return self.repo.get_by_id(conn_id)

    def get_credential_mask(self, conn_id: str) -> dict:
        """返回遮罩后的凭据，密码类字段显示 **** ，非敏感字段显示前4后4。"""
        conn = self._must_get(conn_id)
        if not conn.credential_ref:
            return {}
        raw = self.vault.fetch(conn.credential_ref)
        if not raw:
            return {}
        masked: dict = {}
        secret_keys = {"password", "secret_key", "secret", "token", "value"}
        for k, v in raw.items():
            sv = str(v) if v else ""
            if k in secret_keys or "secret" in k.lower() or "password" in k.lower():
                masked[k] = "••••••••"
            elif len(sv) > 8:
                masked[k] = sv[:4] + "••••" + sv[-4:]
            else:
                masked[k] = sv
        return masked

    def create(
        self,
        *,
        name: str,
        type: str,
        category: str | None = None,
        host: str = "",
        port: int = 0,
        database: str = "",
        username: str = "",
        password: str = "",
        params: dict | None = None,
        credential: dict | None = None,
        writable: bool = False,
        pool_size: int = 4,
        rate_limit_qps: int = 20,
        description: str | None = None,
        user_id: str | None = None,
    ) -> Connection:
        if self.repo.find_by_name(name):
            raise ValueError(f"连接名称已存在: {name}")
        category = category or (CATEGORY_DATABASE if type in DATABASE_TYPES else None)
        if not category:
            raise ValueError(f"无法推断 category，请显式指定。type={type}")
        ConnectorRegistry.get_by_category(category, type)  # 触发不支持类型抛错
        # DB 类沿用 username/password 顶级参数；其他类用 credential dict
        cred_payload: dict = {}
        if category == CATEGORY_DATABASE:
            cred_payload = {"username": username, "password": password}
        else:
            cred_payload = dict(credential or {})
            if username:
                cred_payload.setdefault("username", username)
            if password:
                cred_payload.setdefault("password", password)
        ref = self.vault.store(cred_payload) if cred_payload else ""
        conn = Connection(
            name=name, category=category, type=type,
            host=host or "", port=port or 0, database=database,
            params=params, credential_ref=ref, credential_type="plain",
            writable=writable, pool_size=pool_size, rate_limit_qps=rate_limit_qps,
            description=description, status="active", enabled=True,
            created_by=user_id,
        )
        self.repo.create(conn)
        self.repo.commit()
        self.repo.refresh(conn)
        self.bus.emit("connection.created", {"connection_id": conn.id})
        return conn

    def update(
        self,
        conn_id: str,
        *,
        name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
        params: dict | None = None,
        credential: dict | None = None,
        writable: bool | None = None,
        pool_size: int | None = None,
        rate_limit_qps: int | None = None,
        description: str | None = None,
        enabled: bool | None = None,
    ) -> Connection:
        conn = self._must_get(conn_id)
        password_changed = False
        if name is not None and name != conn.name:
            if self.repo.find_by_name(name):
                raise ValueError(f"连接名称已存在: {name}")
            conn.name = name
        for k, v in dict(host=host, port=port, database=database,
                         params=params, writable=writable, pool_size=pool_size,
                         rate_limit_qps=rate_limit_qps, description=description,
                         enabled=enabled).items():
            if v is not None:
                setattr(conn, k, v)
        if conn.category == CATEGORY_DATABASE:
            if password is not None:
                current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                new_user = username if username is not None else current.get("username", "")
                conn.credential_ref = self.vault.rotate(conn.credential_ref, {"username": new_user, "password": password})
                password_changed = True
            elif username is not None:
                current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                conn.credential_ref = self.vault.rotate(conn.credential_ref, {"username": username, "password": current.get("password", "")})
        else:
            if credential is not None:
                cred_payload = dict(credential)
                if username:
                    cred_payload["username"] = username
                if password:
                    cred_payload["password"] = password
                current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                if cred_payload != current:
                    if conn.credential_ref:
                        conn.credential_ref = self.vault.rotate(conn.credential_ref, cred_payload)
                    else:
                        conn.credential_ref = self.vault.store(cred_payload)
                    if cred_payload.get("password") != current.get("password"):
                        password_changed = True
            elif password is not None or username is not None:
                current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                if username is not None:
                    current["username"] = username
                if password is not None:
                    current["password"] = password
                old = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                if current != old:
                    if conn.credential_ref:
                        conn.credential_ref = self.vault.rotate(conn.credential_ref, current)
                    else:
                        conn.credential_ref = self.vault.store(current)
                    if current.get("password") != old.get("password"):
                        password_changed = True
        self.repo.commit()
        self.repo.refresh(conn)
        if password_changed:
            _dispose_pool(conn.id)
            self.bus.emit("connection.updated.password", {"connection_id": conn.id})
        return conn

    def delete(self, conn_id: str, *, cascade: bool = False) -> None:
        conn = self._must_get(conn_id)
        assets = self.asset_repo.list(connection_id=conn_id, status=None)
        if assets and not cascade:
            raise ValueError(f"连接被 {len(assets)} 个资产引用，无法删除")
        if assets and cascade:
            # 懒加载避免与 AssetService 循环引用；逐个级联删资产（含对象绑定/质量规则等）
            from app.services.data_plane.asset_service import AssetService
            asset_svc = AssetService(self.db)
            for a in assets:
                asset_svc.delete(a.id, cascade=True)
        if conn.credential_ref:
            try:
                self.vault.delete(conn.credential_ref)
            except Exception:
                logger.exception("vault delete failed for ref=%s", conn.credential_ref)
        _dispose_pool(conn.id)
        self.repo.delete(conn)
        self.repo.commit()

    def toggle(self, conn_id: str) -> Connection:
        conn = self._must_get(conn_id)
        conn.enabled = not conn.enabled
        self.repo.commit()
        self.repo.refresh(conn)
        return conn

    # ── 测试 / 元数据探测 ────────────────────────────────
    def test(self, conn_id: str) -> dict:
        conn = self._must_get(conn_id)
        started = time.time()
        if conn.category == CATEGORY_DATABASE:
            try:
                with self.with_conn(conn_id):
                    ok, msg = True, "连接成功"
            except Exception as e:
                ok, msg = False, f"连接失败: {e}"
        else:
            try:
                connector = ConnectorRegistry.get_by_category(conn.category, conn.type)
                cred = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
                ok, msg = connector.test(params=conn.params or {}, credential=cred)
            except Exception as e:
                ok, msg = False, f"连接失败: {e}"
        latency_ms = int((time.time() - started) * 1000)
        conn.last_test_at = datetime.utcnow()
        conn.last_test_ok = ok
        conn.last_test_message = msg[:500]
        conn.status = "active" if ok else "error"
        self.repo.commit()
        if not ok:
            self.bus.emit("connection.test.failed", {"connection_id": conn.id, "message": msg})
        return {"success": ok, "message": msg, "latency_ms": latency_ms}

    # ── 浏览：按 category 分发 ─────────────────────────────
    def list_objects(self, conn_id: str, *, prefix: str = "", limit: int = 200) -> list[dict]:
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_OBJECT_STORAGE:
            raise ValueError(f"list_objects 仅适用对象存储，当前 category={conn.category}")
        connector = ConnectorRegistry.get_by_category(conn.category, conn.type)
        cred = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
        return connector.list_objects(params=conn.params or {}, credential=cred,
                                      prefix=prefix, limit=limit)

    def list_paths(self, conn_id: str, *, path: str = "/", limit: int = 200) -> list[dict]:
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_FILE_TRANSFER:
            raise ValueError(f"list_paths 仅适用文件传输，当前 category={conn.category}")
        connector = ConnectorRegistry.get_by_category(conn.category, conn.type)
        cred = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
        params = dict(conn.params or {})
        params.setdefault("host", conn.host)
        params.setdefault("port", conn.port)
        return connector.list_paths(params=params, credential=cred, path=path, limit=limit)

    def list_topics(self, conn_id: str) -> list[str]:
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_MESSAGE_QUEUE:
            raise ValueError(f"list_topics 仅适用消息队列，当前 category={conn.category}")
        connector = ConnectorRegistry.get_by_category(conn.category, conn.type)
        cred = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
        return connector.list_topics(params=conn.params or {}, credential=cred)

    def list_databases(self, conn_id: str) -> list[str]:
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_DATABASE:
            return [conn.database] if conn.database else []
        connector = ConnectorRegistry.get(conn.type)
        if not hasattr(connector, "list_databases"):
            return [conn.database] if conn.database else []
        with self.with_conn(conn_id) as raw:
            try:
                return connector.list_databases(raw)
            except Exception as e:
                logger.warning("list_databases failed: %s", e)
                return [conn.database] if conn.database else []

    def list_tables(self, conn_id: str, database: str | None = None) -> list[str]:
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_DATABASE:
            raise ValueError(f"list_tables 仅适用数据库，当前 category={conn.category}")
        connector = ConnectorRegistry.get(conn.type)
        with self.with_conn(conn_id) as raw:
            return connector.list_tables(raw, database or conn.database)

    def get_table_schema(self, conn_id: str, table_name: str, database: str | None = None) -> list[dict]:
        conn = self._must_get(conn_id)
        connector = ConnectorRegistry.get(conn.type)
        with self.with_conn(conn_id) as raw:
            return connector.get_table_schema(raw, table_name, database or conn.database)

    # ── 内部：借连接 ────────────────────────────────────
    @contextmanager
    def with_conn(self, conn_id: str) -> Iterator[Any]:
        """从池里借一条连接；用完自动归还（异常时关闭）。

        仅 category=database 的连接走该路径；ExecuteService 是唯一上层调用者。
        """
        conn = self._must_get(conn_id)
        if conn.category != CATEGORY_DATABASE:
            raise RuntimeError(f"with_conn 仅适用数据库连接，当前 category={conn.category}")
        if not conn.enabled:
            raise RuntimeError(f"连接已禁用: {conn.name}")
        pool = _get_pool(conn.id, conn.pool_size)
        raw = pool.borrow()
        if raw is None:
            connector = ConnectorRegistry.get(conn.type)
            cred = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
            raw = connector.connect(
                host=conn.host, port=conn.port,
                username=cred.get("username", ""),
                password=cred.get("password", ""),
                database=conn.database or "",
            )
        broken = False
        try:
            yield raw
        except Exception:
            broken = True
            raise
        finally:
            if broken:
                try:
                    raw.close()
                except Exception:
                    pass
            else:
                pool.release(raw)

    def _must_get(self, conn_id: str) -> Connection:
        c = self.repo.get_by_id(conn_id)
        if not c:
            raise LookupError(f"连接不存在: {conn_id}")
        return c
