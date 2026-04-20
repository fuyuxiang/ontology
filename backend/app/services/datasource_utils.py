"""
数据源工具函数 — 从 datasources API 提取的共享逻辑
供 agent_service 和 datasources API 共同使用
"""
import logging
import re
from app.models.datasource import DataSource

logger = logging.getLogger(__name__)

# 禁止的 SQL 关键词（DML/DDL）
_FORBIDDEN_SQL_PATTERN = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC)\b",
    re.IGNORECASE,
)


def get_connection(ds: DataSource):
    """根据数据源类型创建数据库连接"""
    if ds.type == "mysql":
        import pymysql
        return pymysql.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=ds.password, database=ds.database, connect_timeout=5,
            charset='utf8mb4',
        )
    elif ds.type == "postgresql":
        import psycopg2
        return psycopg2.connect(
            host=ds.host, port=ds.port, user=ds.username,
            password=ds.password, dbname=ds.database, connect_timeout=5,
        )
    elif ds.type == "oracle":
        import oracledb
        return oracledb.connect(
            user=ds.username, password=ds.password,
            dsn=f"{ds.host}:{ds.port}/{ds.database}",
        )
    elif ds.type == "sqlserver":
        import pymssql
        return pymssql.connect(
            server=ds.host, port=ds.port, user=ds.username,
            password=ds.password, database=ds.database, login_timeout=5,
        )
    return None


def list_tables(ds: DataSource) -> list[str]:
    """获取数据源下所有表名"""
    conn = get_connection(ds)
    if not conn:
        return []
    cur = conn.cursor()
    if ds.type == "mysql":
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
            (ds.database,),
        )
    elif ds.type == "postgresql":
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
        )
    elif ds.type == "oracle":
        cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
    elif ds.type == "sqlserver":
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name"
        )
    else:
        cur.close()
        conn.close()
        return []
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return tables


def preview_table(ds: DataSource, table_name: str) -> dict:
    """查询指定表前 20 条数据"""
    conn = get_connection(ds)
    if not conn:
        raise RuntimeError(f"不支持的数据源类型: {ds.type}")
    cur = conn.cursor()
    quote = "`" if ds.type == "mysql" else '"'
    cur.execute(f"SELECT * FROM {quote}{table_name}{quote} LIMIT 20")
    columns = [desc[0] for desc in cur.description]
    rows = [list(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"table": table_name, "columns": columns, "rows": rows}


def get_table_schema(ds: DataSource, table_name: str) -> list[dict]:
    """查询表的列元数据"""
    conn = get_connection(ds)
    if not conn:
        raise RuntimeError(f"不支持的数据源类型: {ds.type}")
    cur = conn.cursor()
    if ds.type == "mysql":
        cur.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable, c.column_comment,
                   CASE WHEN kcu.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name AND kcu.constraint_name = 'PRIMARY'
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """, (ds.database, table_name))
    elif ds.type == "postgresql":
        cur.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable,
                   COALESCE(pgd.description, '') as column_comment,
                   CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM information_schema.columns c
            LEFT JOIN pg_catalog.pg_statio_all_tables st ON st.relname = c.table_name AND st.schemaname = c.table_schema
            LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
            LEFT JOIN (
                SELECT kcu.column_name FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY' AND kcu.table_name = %s
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_schema = 'public' AND c.table_name = %s
            ORDER BY c.ordinal_position
        """, (table_name, table_name))
    elif ds.type == "sqlserver":
        cur.execute("""
            SELECT c.COLUMN_NAME, c.DATA_TYPE, c.IS_NULLABLE, '' as column_comment,
                   CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' AND ku.TABLE_NAME = %s
            ) pk ON pk.COLUMN_NAME = c.COLUMN_NAME
            WHERE c.TABLE_NAME = %s
            ORDER BY c.ORDINAL_POSITION
        """, (table_name, table_name))
    else:
        cur.close()
        conn.close()
        raise RuntimeError(f"暂不支持 {ds.type} 的 schema 查询")

    columns = []
    for row in cur.fetchall():
        columns.append({
            "name": row[0],
            "type": row[1],
            "nullable": row[2] in ("YES", "yes", True),
            "comment": row[3] or "",
            "is_pk": bool(row[4]),
        })
    cur.close()
    conn.close()
    return columns


def execute_readonly_sql(ds: DataSource, sql: str, limit: int = 50) -> dict:
    """执行只读 SQL 查询，拒绝 DML/DDL，自动加 LIMIT"""
    sql = sql.strip().rstrip(";")
    if _FORBIDDEN_SQL_PATTERN.match(sql):
        return {"error": "仅允许 SELECT 查询，禁止执行修改操作"}

    # 自动加 LIMIT（如果用户 SQL 中没有）
    limit = min(limit, 200)
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"

    try:
        conn = get_connection(ds)
        if not conn:
            return {"error": f"不支持的数据源类型: {ds.type}"}
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return {"columns": columns, "rows": rows, "rowCount": len(rows)}
    except Exception as e:
        logger.warning(f"SQL 执行失败: {e}")
        return {"error": str(e)}
