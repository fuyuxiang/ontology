from __future__ import annotations

from typing import Any

from app.connectors.base import DataSourceConnector


class ConnectorRegistry:
    _connectors: dict[str, type] = {}

    @classmethod
    def register(cls, db_type: str):
        def decorator(connector_cls: type):
            cls._connectors[db_type] = connector_cls
            return connector_cls
        return decorator

    @classmethod
    def get(cls, db_type: str) -> DataSourceConnector:
        connector_cls = cls._connectors.get(db_type)
        if not connector_cls:
            raise ValueError(f"不支持的数据源类型: {db_type}")
        return connector_cls()


# Import connectors to trigger registration
from app.connectors.mysql import MySQLConnector  # noqa: F401,E402
from app.connectors.postgresql import PostgreSQLConnector  # noqa: F401,E402
from app.connectors.oracle import OracleConnector  # noqa: F401,E402
from app.connectors.sqlserver import SQLServerConnector  # noqa: F401,E402

__all__ = ["ConnectorRegistry", "DataSourceConnector"]
