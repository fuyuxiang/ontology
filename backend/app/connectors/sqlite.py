"""Real local database connector, constrained to the configured data directory."""
import sqlite3
from pathlib import Path
from urllib.parse import quote

from app.config import settings
from app.connectors import ConnectorRegistry


@ConnectorRegistry.register("sqlite")
class SQLiteConnector:
    category = "database"
    type = "sqlite"

    def connect(self, *, host="", port=0, username="", password="", database=""):
        root = Path(settings.LOCAL_DATA_ROOT).resolve()
        file = Path(database).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            raise ValueError("SQLite 源必须是 LOCAL_DATA_ROOT 内已存在的数据库文件")
        connection = sqlite3.connect(f"file:{quote(str(file))}?mode=rw", uri=True, check_same_thread=False, timeout=10)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def close(self, conn):
        conn.close()

    def quote_identifier(self):
        return '"'

    def list_databases(self, conn):
        return [row[2] for row in conn.execute("PRAGMA database_list")]

    def list_tables(self, conn, database=""):
        return [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    def get_table_schema(self, conn, table_name, database=""):
        safe_name = table_name.replace('"', '""')
        return [{"name": row[1], "type": row[2] or "TEXT", "nullable": not bool(row[3] or row[5]),
                 "is_pk": bool(row[5]), "comment": ""} for row in conn.execute(f'PRAGMA table_info("{safe_name}")')]

    def preview_table(self, conn, table_name, limit=20):
        table = table_name.replace('"', '""')
        result = self.execute_sql_with_params(conn, f'SELECT * FROM "{table}" LIMIT :limit', {"limit": limit})
        return {"table": table_name, **result}

    def execute_sql(self, conn, sql):
        return self.execute_sql_with_params(conn, sql, {})

    def execute_sql_with_params(self, conn, sql, params):
        cur = conn.execute(sql, params)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()] if cur.description else []
        affected = cur.rowcount
        cur.close()
        return {"columns": columns, "rows": rows, "rowCount": len(rows), "rowsAffected": affected}
