from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DataSourceConnector(Protocol):
    """异构数据源连接器协议"""

    def connect(self, *, host: str, port: int, username: str,
                password: str, database: str) -> Any: ...

    def close(self, conn: Any) -> None: ...

    def list_tables(self, conn: Any, database: str) -> list[str]: ...

    def list_databases(self, conn: Any) -> list[str]: ...

    def preview_table(self, conn: Any, table_name: str, limit: int = 20) -> dict: ...

    def get_table_schema(self, conn: Any, table_name: str, database: str) -> list[dict]: ...

    def execute_sql(self, conn: Any, sql: str) -> dict: ...

    def execute_sql_with_params(self, conn: Any, sql: str, params: dict) -> dict:
        """参数化执行（驱动层绑定，杜绝注入）。

        sql 中占位符为 :name 风格；各 connector 在内部转成本驱动需要的形式。
        params 是 {name: value} 字典；按 sql 中出现顺序展开为 driver 实际参数。
        """
        ...

    def quote_identifier(self) -> str: ...

