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

from app.connectors import ConnectorRegistry
from app.models.connection import Connection
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

    def create(
        self,
        *,
        name: str,
        type: str,
        host: str,
        port: int,
        database: str = "",
        username: str,
        password: str,
        params: dict | None = None,
        writable: bool = False,
        pool_size: int = 4,
        rate_limit_qps: int = 20,
        description: str | None = None,
        user_id: str | None = None,
    ) -> Connection:
        if self.repo.find_by_name(name):
            raise ValueError(f"连接名称已存在: {name}")
        ConnectorRegistry.get(type)  # 触发不支持类型抛错
        ref = self.vault.store({"username": username, "password": password})
        conn = Connection(
            name=name, type=type, host=host, port=port, database=database,
            params=params, credential_ref=ref, credential_type="local-fernet",
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
        if password is not None:
            current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
            new_user = username if username is not None else current.get("username", "")
            self.vault.rotate(conn.credential_ref, {"username": new_user, "password": password})
            password_changed = True
        elif username is not None:
            current = self.vault.fetch(conn.credential_ref) if conn.credential_ref else {}
            self.vault.rotate(conn.credential_ref, {"username": username, "password": current.get("password", "")})
        self.repo.commit()
        self.repo.refresh(conn)
        if password_changed:
            _dispose_pool(conn.id)
            self.bus.emit("connection.updated.password", {"connection_id": conn.id})
        return conn

    def delete(self, conn_id: str) -> None:
        conn = self._must_get(conn_id)
        in_use = self.asset_repo.count_by_connection(conn_id)
        if in_use > 0:
            raise ValueError(f"连接被 {in_use} 个资产引用，无法删除")
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
        try:
            with self.with_conn(conn_id):
                ok = True
                msg = "连接成功"
        except Exception as e:
            ok = False
            msg = f"连接失败: {e}"
        latency_ms = int((time.time() - started) * 1000)
        conn.last_test_at = datetime.utcnow()
        conn.last_test_ok = ok
        conn.last_test_message = msg[:500]
        conn.status = "active" if ok else "error"
        self.repo.commit()
        if not ok:
            self.bus.emit("connection.test.failed", {"connection_id": conn.id, "message": msg})
        return {"success": ok, "message": msg, "latency_ms": latency_ms}

    def list_databases(self, conn_id: str) -> list[str]:
        conn = self._must_get(conn_id)
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

        ExecuteService 是这条 API 的唯一上层调用者。
        """
        conn = self._must_get(conn_id)
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
