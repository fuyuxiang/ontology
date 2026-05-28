from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseConnector(Protocol):
    """所有连接器的最小公约数协议。

    每个 connector 都必须能 test()，返回 (ok, message)。
    各 category 的具体能力由子协议或鸭子类型决定。
    """

    category: str  # database | object_storage | file_transfer | message_queue | api
    type: str

    def test(self, *, params: dict, credential: dict | None) -> tuple[bool, str]:
        """检测连通性。不抛异常，返回 (ok, msg)。"""
        ...


@runtime_checkable
class DataSourceConnector(Protocol):
    """关系型数据库连接器协议（category=database）。"""

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


@runtime_checkable
class ObjectStorageConnector(Protocol):
    """对象存储连接器协议（category=object_storage）。"""
    def list_objects(self, *, params: dict, credential: dict | None,
                     prefix: str = "", limit: int = 200) -> list[dict]: ...


@runtime_checkable
class FileTransferConnector(Protocol):
    """文件传输连接器协议（category=file_transfer）。"""
    def list_paths(self, *, params: dict, credential: dict | None,
                   path: str = "/", limit: int = 200) -> list[dict]: ...


@runtime_checkable
class MessageQueueConnector(Protocol):
    """消息队列连接器协议（category=message_queue）。"""
    def list_topics(self, *, params: dict, credential: dict | None) -> list[str]: ...


@runtime_checkable
class HTTPApiConnector(Protocol):
    """HTTP API 连接器协议（category=api）。"""
    def probe(self, *, params: dict, credential: dict | None) -> dict: ...

