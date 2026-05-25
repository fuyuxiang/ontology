"""
数据源工具函数 — 已迁移到 Data Plane（ConnectionService + ExecuteService）。

本模块在 M2 期间是兼容层：
- get_connection / list_tables / preview_table / get_table_schema：走 ConnectorRegistry，
  暂保留旧调用入口（仅供"系统启动 / 元数据探测 / 临时查询"使用）。
- execute_readonly_sql：内部转发到 ExecuteService.execute_on_connection。
  · 老调用方传入 DataSource，本模块解析为对应 Connection（按 host/port/db/user 匹配 legacy_datasource_id）。
  · 走 6 道闸门：AST + 参数化 + 限流 + 审计 + 脱敏。
  · 不再支持任意 SQL 注入风险写法 —— 调用方仍应使用参数化或迁移到 alias。
"""
import logging
import re
from typing import Any

from sqlalchemy.orm import Session as _Session

from app.connectors import ConnectorRegistry
from app.models.datasource import DataSource

logger = logging.getLogger(__name__)

_FORBIDDEN_SQL_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)


def get_connection(ds: DataSource) -> Any | None:
    """根据数据源类型创建数据库连接"""
    try:
        connector = ConnectorRegistry.get(ds.type)
    except ValueError:
        return None
    return connector.connect(
        host=ds.host, port=ds.port, username=ds.username,
        password=ds.password, database=ds.database,
    )


def list_tables(ds: DataSource) -> list[str]:
    """获取数据源下所有表名"""
    try:
        connector = ConnectorRegistry.get(ds.type)
    except ValueError:
        return []
    conn = connector.connect(
        host=ds.host, port=ds.port, username=ds.username,
        password=ds.password, database=ds.database,
    )
    try:
        return connector.list_tables(conn, ds.database)
    finally:
        connector.close(conn)


def preview_table(ds: DataSource, table_name: str) -> dict:
    """查询指定表前 20 条数据"""
    try:
        connector = ConnectorRegistry.get(ds.type)
    except ValueError:
        raise RuntimeError(f"不支持的数据源类型: {ds.type}")
    conn = connector.connect(
        host=ds.host, port=ds.port, username=ds.username,
        password=ds.password, database=ds.database,
    )
    try:
        return connector.preview_table(conn, table_name)
    finally:
        connector.close(conn)


def get_table_schema(ds: DataSource, table_name: str) -> list[dict]:
    """查询表的列元数据"""
    try:
        connector = ConnectorRegistry.get(ds.type)
    except ValueError:
        raise RuntimeError(f"不支持的数据源类型: {ds.type}")
    conn = connector.connect(
        host=ds.host, port=ds.port, username=ds.username,
        password=ds.password, database=ds.database,
    )
    try:
        return connector.get_table_schema(conn, table_name, ds.database)
    finally:
        connector.close(conn)


def execute_readonly_sql(ds: DataSource, sql: str, limit: int = 50) -> dict:
    """执行只读 SQL 查询。

    M2 兼容层：自动转发到 ExecuteService.execute_on_connection（通过 legacy_datasource_id
    或同 host/port/db 匹配 Connection）。失败则回落到旧 connector 直连。
    """
    sql = sql.strip().rstrip(";")
    if _FORBIDDEN_SQL_PATTERN.match(sql):
        return {"error": "仅允许 SELECT 查询，禁止执行修改操作"}

    limit = min(limit, 200)
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"

    # 尝试走 Data Plane（统一闸口 + 审计）
    forwarded = _try_forward_to_execute_service(ds, sql)
    if forwarded is not None:
        return forwarded

    # 兜底：旧 connector 直连
    try:
        connector = ConnectorRegistry.get(ds.type)
    except ValueError:
        return {"error": f"不支持的数据源类型: {ds.type}"}
    try:
        conn = connector.connect(
            host=ds.host, port=ds.port, username=ds.username,
            password=ds.password, database=ds.database,
        )
        try:
            return connector.execute_sql(conn, sql)
        finally:
            connector.close(conn)
    except Exception as e:
        logger.warning(f"SQL 执行失败: {e}")
        return {"error": str(e)}


def _try_forward_to_execute_service(ds: DataSource, sql: str) -> dict | None:
    """把老 DataSource 调用转发到 ExecuteService.execute_on_connection。

    返回 dict 表示已成功转发；None 表示找不到对应 Connection，调用方走 fallback。
    """
    try:
        from app.database import SessionLocal
        from app.repositories.connection_repo import ConnectionRepository
        from app.services.data_plane.execute_service import (
            ExecuteBlocked, ExecuteService,
        )
    except Exception:
        return None
    db = SessionLocal()
    try:
        repo = ConnectionRepository(db)
        # 优先按 legacy_datasource_id 反查（迁移脚本写入）
        from app.models.asset import Asset
        asset = db.query(Asset).filter(Asset.legacy_datasource_id == ds.id).first()
        connection_id = asset.connection_id if asset and asset.connection_id else None
        if not connection_id:
            # 按 host/port/database/username 推断
            for c in repo.list(type=ds.type):
                if (c.host == ds.host and c.port == ds.port
                        and (c.database or "") == (ds.database or "")):
                    connection_id = c.id
                    break
        if not connection_id:
            return None
        try:
            r = ExecuteService(db).execute_on_connection(
                connection_id=connection_id,
                sql=sql, params={},
                purpose="legacy.datasource_utils",
                write=False,
            )
            return {"columns": r.columns, "rows": r.rows, "rowCount": r.rows_returned}
        except ExecuteBlocked as e:
            return {"error": f"被拒绝：{e.reason}"}
        except Exception as e:
            logger.warning("forward to ExecuteService failed: %s", e)
            return None
    finally:
        db.close()
