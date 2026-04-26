"""
数据源工具函数 — 从 datasources API 提取的共享逻辑
供 agent_service 和 datasources API 共同使用

公开 API 保持不变：get_connection, list_tables, preview_table, get_table_schema, execute_readonly_sql
内部实现委托给 ConnectorRegistry 中注册的各数据库连接器。
"""
import logging
import re
from typing import Any

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
    """执行只读 SQL 查询，拒绝 DML/DDL，自动加 LIMIT"""
    sql = sql.strip().rstrip(";")
    if _FORBIDDEN_SQL_PATTERN.match(sql):
        return {"error": "仅允许 SELECT 查询，禁止执行修改操作"}

    limit = min(limit, 200)
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"

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
