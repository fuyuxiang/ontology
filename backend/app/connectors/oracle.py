from __future__ import annotations

from typing import Any

from app.connectors import ConnectorRegistry


@ConnectorRegistry.register("oracle")
class OracleConnector:

    def connect(self, *, host: str, port: int, username: str,
                password: str, database: str) -> Any:
        import oracledb
        return oracledb.connect(
            user=username, password=password,
            dsn=f"{host}:{port}/{database}",
        )

    def close(self, conn: Any) -> None:
        conn.close()

    def quote_identifier(self) -> str:
        return '"'

    def list_tables(self, conn: Any, database: str) -> list[str]:
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        return tables

    def preview_table(self, conn: Any, table_name: str, limit: int = 20) -> dict:
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM "{table_name}" WHERE ROWNUM <= {limit}')
        columns = [desc[0] for desc in cur.description]
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        return {"table": table_name, "columns": columns, "rows": rows}

    def get_table_schema(self, conn: Any, table_name: str, database: str) -> list[dict]:
        raise RuntimeError(f"暂不支持 oracle 的 schema 查询")

    def execute_sql(self, conn: Any, sql: str) -> dict:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()]
        cur.close()
        return {"columns": columns, "rows": rows, "rowCount": len(rows)}
