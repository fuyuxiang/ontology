from __future__ import annotations

from typing import Any

from app.connectors import ConnectorRegistry


@ConnectorRegistry.register("mysql")
class MySQLConnector:

    def connect(self, *, host: str, port: int, username: str,
                password: str, database: str) -> Any:
        import pymysql
        return pymysql.connect(
            host=host, port=port, user=username,
            password=password, database=database,
            connect_timeout=5, charset="utf8mb4",
        )

    def close(self, conn: Any) -> None:
        conn.close()

    def quote_identifier(self) -> str:
        return "`"

    def list_tables(self, conn: Any, database: str) -> list[str]:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY table_name",
            (database,),
        )
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return tables

    def preview_table(self, conn: Any, table_name: str, limit: int = 20) -> dict:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM `{table_name}` LIMIT {limit}")
        columns = [desc[0] for desc in cur.description]
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        return {"table": table_name, "columns": columns, "rows": rows}

    def get_table_schema(self, conn: Any, table_name: str, database: str) -> list[dict]:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable, c.column_comment,
                   CASE WHEN kcu.column_name IS NOT NULL THEN 1 ELSE 0 END as is_pk
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name AND kcu.constraint_name = 'PRIMARY'
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
        """, (database, table_name))
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
