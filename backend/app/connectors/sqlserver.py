from __future__ import annotations

from typing import Any

from app.connectors import ConnectorRegistry


@ConnectorRegistry.register("sqlserver")
class SQLServerConnector:

    def connect(self, *, host: str, port: int, username: str,
                password: str, database: str) -> Any:
        import pymssql
        return pymssql.connect(
            server=host, port=port, user=username,
            password=password, database=database, login_timeout=5,
        )

    def close(self, conn: Any) -> None:
        conn.close()

    def quote_identifier(self) -> str:
        return '"'

    def list_tables(self, conn: Any, database: str) -> list[str]:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return tables

    def preview_table(self, conn: Any, table_name: str, limit: int = 20) -> dict:
        cur = conn.cursor()
        cur.execute(f'SELECT TOP {limit} * FROM "{table_name}"')
        columns = [desc[0] for desc in cur.description]
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        return {"table": table_name, "columns": columns, "rows": rows}

    def get_table_schema(self, conn: Any, table_name: str, database: str) -> list[dict]:
        cur = conn.cursor()
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
        return columns

    def execute_sql(self, conn: Any, sql: str) -> dict:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        return {"columns": columns, "rows": rows, "rowCount": len(rows)}
