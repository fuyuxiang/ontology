from __future__ import annotations

from typing import Any

from app.connectors.base import (
    BaseConnector,
    DataSourceConnector,
    ObjectStorageConnector,
    FileTransferConnector,
    MessageQueueConnector,
    HTTPApiConnector,
)


# DB 类 type 集合（保留旧 ConnectorRegistry.get(type) 单参签名兼容）
DATABASE_TYPES = {"mysql", "postgresql", "oracle", "sqlserver", "hive", "clickhouse"}


class ConnectorRegistry:
    """按 (category, type) 双键注册的连接器登记处。

    历史 API：ConnectorRegistry.get("mysql") 仍然可用——回退到 category=database。
    新 API：ConnectorRegistry.get_by_category("object_storage", "s3").
    """

    _by_kt: dict[tuple[str, str], type] = {}
    _by_type: dict[str, type] = {}  # 老 API：仅 DB 类有效

    @classmethod
    def register(cls, db_type: str, *, category: str = "database"):
        def decorator(connector_cls: type):
            cls._by_kt[(category, db_type)] = connector_cls
            if category == "database":
                cls._by_type[db_type] = connector_cls
            return connector_cls
        return decorator

    @classmethod
    def get(cls, db_type: str) -> Any:
        connector_cls = cls._by_type.get(db_type)
        if not connector_cls:
            raise ValueError(f"不支持的数据源类型: {db_type}（需要 category=database）")
        return connector_cls()

    @classmethod
    def get_by_category(cls, category: str, type_: str) -> Any:
        connector_cls = cls._by_kt.get((category, type_))
        if not connector_cls:
            raise ValueError(f"不支持的连接器: category={category} type={type_}")
        return connector_cls()

    @classmethod
    def list_supported(cls) -> dict[str, list[str]]:
        """返回 {category: [type, ...]} 给前端建表/校验用。"""
        out: dict[str, list[str]] = {}
        for (cat, t) in cls._by_kt.keys():
            out.setdefault(cat, []).append(t)
        for v in out.values():
            v.sort()
        return out


# Import connectors to trigger registration
from app.connectors.mysql import MySQLConnector  # noqa: F401,E402
from app.connectors.postgresql import PostgreSQLConnector  # noqa: F401,E402
from app.connectors.oracle import OracleConnector  # noqa: F401,E402
from app.connectors.sqlserver import SQLServerConnector  # noqa: F401,E402
from app.connectors.s3 import S3Connector  # noqa: F401,E402
from app.connectors.ftp import FTPConnector, SFTPConnector  # noqa: F401,E402
from app.connectors.kafka import KafkaConnector  # noqa: F401,E402
from app.connectors.http_api import HTTPApiConnector as _HTTPApiConn  # noqa: F401,E402

# 手动注册 — DB connector 内部用 @ConnectorRegistry.register 装饰器
ConnectorRegistry._by_kt[("object_storage", "s3")] = S3Connector
ConnectorRegistry._by_kt[("file_transfer", "ftp")] = FTPConnector
ConnectorRegistry._by_kt[("file_transfer", "sftp")] = SFTPConnector
ConnectorRegistry._by_kt[("message_queue", "kafka")] = KafkaConnector
ConnectorRegistry._by_kt[("api", "rest")] = _HTTPApiConn

__all__ = [
    "ConnectorRegistry",
    "BaseConnector",
    "DataSourceConnector",
    "ObjectStorageConnector",
    "FileTransferConnector",
    "MessageQueueConnector",
    "HTTPApiConnector",
    "DATABASE_TYPES",
]
