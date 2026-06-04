"""EntityDataService — 通过 ObjectBinding 从本体实体查询实际数据的统一入口。

替代旧的 DataSource + datasource_ref 方案。所有需要"给定实体，查其实例数据"的场景
都应通过本服务，而非直接依赖 DataSource 模型。

查询路径：
    entity_id → ObjectBinding(role=primary) → Asset → Connection → ExecuteService
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.entity import OntologyEntity
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.execute_service import (
    ExecuteBlocked, ExecuteRequest, ExecuteResult, ExecuteService,
)

logger = logging.getLogger(__name__)


class EntityDataService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._binding_repo = ObjectBindingRepository(db)
        self._asset_repo = AssetRepository(db)
        self._exec_svc = ExecuteService(db)
        self._conn_svc = ConnectionService(db)

    def resolve_entity_asset(self, entity_id: str) -> tuple[Asset, ObjectBinding] | None:
        binding = self._binding_repo.get_primary(entity_id)
        if not binding:
            return None
        asset = self.db.get(Asset, binding.asset_id)
        if not asset or asset.status != "active":
            return None
        return asset, binding

    def get_table_name(self, asset: Asset) -> str:
        return (asset.locator or {}).get("table") or ""

    def query_entity_data(
        self,
        entity_id: str,
        *,
        filters: dict | None = None,
        fields: list[str] | None = None,
        limit: int = 20,
        purpose: str = "entity_data_query",
        valid_attrs: set[str] | None = None,
    ) -> dict:
        result = self.resolve_entity_asset(entity_id)
        if not result:
            return {"error": f"实体 '{entity_id}' 未绑定数据资产，请先在数据集成中创建 ObjectBinding"}
        asset, binding = result
        table_name = self.get_table_name(asset)
        if not table_name:
            return {"error": f"资产 '{asset.name}' 未配置表名（locator.table 为空）"}

        limit = min(limit, 200)
        select_cols = "*"
        if fields and valid_attrs:
            valid_fields = [f for f in fields if f in valid_attrs]
            if valid_fields:
                select_cols = ", ".join(valid_fields)

        sql = f"SELECT {select_cols} FROM {table_name}"

        where_parts: list[str] = []
        params: dict[str, Any] = {}
        for i, (attr_name, value) in enumerate(( filters or {}).items()):
            if valid_attrs and attr_name not in valid_attrs:
                continue
            param_key = f"p{i}"
            where_parts.append(f"{attr_name} = :{param_key}")
            params[param_key] = value

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        sql += f" LIMIT {limit}"

        try:
            exec_result = self._exec_svc.execute(ExecuteRequest(
                asset_id=asset.id, sql=sql, params=params, purpose=purpose,
            ))
            return {
                "columns": exec_result.columns,
                "rows": exec_result.rows,
                "rowCount": exec_result.rows_returned,
            }
        except ExecuteBlocked as e:
            return {"error": f"查询被拒绝：{e.detail or e.reason}"}
        except LookupError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.warning("entity data query failed: %s", e)
            return {"error": f"查询执行失败：{e}"}

    def execute_sql_on_entity(
        self,
        entity_id: str,
        sql: str,
        *,
        params: dict | None = None,
        purpose: str = "entity_sql",
    ) -> dict:
        result = self.resolve_entity_asset(entity_id)
        if not result:
            return {"error": f"实体 '{entity_id}' 未绑定数据资产"}
        asset, binding = result
        try:
            exec_result = self._exec_svc.execute(ExecuteRequest(
                asset_id=asset.id, sql=sql, params=params or {}, purpose=purpose,
            ))
            return {
                "columns": exec_result.columns,
                "rows": exec_result.rows,
                "rowCount": exec_result.rows_returned,
            }
        except ExecuteBlocked as e:
            return {"error": f"查询被拒绝：{e.detail or e.reason}"}
        except Exception as e:
            logger.warning("entity sql execution failed: %s", e)
            return {"error": f"执行失败：{e}"}

    def execute_sql_on_asset(
        self,
        asset_name: str,
        sql: str,
        *,
        params: dict | None = None,
        purpose: str = "asset_sql",
    ) -> dict:
        asset = (
            self.db.query(Asset)
            .filter(Asset.name == asset_name, Asset.status == "active")
            .first()
        )
        if not asset:
            asset = self._asset_repo.find_by_alias(asset_name)
        if not asset:
            return {"error": f"资产 '{asset_name}' 不存在或未启用"}
        try:
            exec_result = self._exec_svc.execute(ExecuteRequest(
                asset_id=asset.id, sql=sql, params=params or {}, purpose=purpose,
            ))
            return {
                "columns": exec_result.columns,
                "rows": exec_result.rows,
                "rowCount": exec_result.rows_returned,
            }
        except ExecuteBlocked as e:
            return {"error": f"查询被拒绝：{e.detail or e.reason}"}
        except Exception as e:
            logger.warning("asset sql execution failed: %s", e)
            return {"error": f"执行失败：{e}"}

    def get_table_schema_for_entity(self, entity_id: str) -> list[dict] | dict:
        result = self.resolve_entity_asset(entity_id)
        if not result:
            return {"error": f"实体 '{entity_id}' 未绑定数据资产"}
        asset, binding = result
        if not asset.connection_id:
            return {"error": f"资产 '{asset.name}' 未关联连接"}
        table_name = self.get_table_name(asset)
        if not table_name:
            return {"error": f"资产 '{asset.name}' 未配置表名"}
        return self._conn_svc.get_table_schema(asset.connection_id, table_name)

    def get_table_schema_for_asset(self, asset_name: str, table_name: str = "") -> list[dict] | dict:
        asset = (
            self.db.query(Asset)
            .filter(Asset.name == asset_name, Asset.status == "active")
            .first()
        )
        if not asset:
            asset = self._asset_repo.find_by_alias(asset_name)
        if not asset:
            return {"error": f"资产 '{asset_name}' 不存在或未启用"}
        if not asset.connection_id:
            return {"error": f"资产 '{asset_name}' 未关联连接"}
        tbl = table_name or self.get_table_name(asset)
        if not tbl:
            return {"error": f"需要提供 table_name 或资产需配置表（locator.table）"}
        return self._conn_svc.get_table_schema(asset.connection_id, tbl)

    def list_assets(self, *, kind: str | None = None) -> list[dict]:
        q = self.db.query(Asset).filter(Asset.status == "active")
        if kind:
            q = q.filter(Asset.kind == kind)
        else:
            q = q.filter(Asset.kind.in_(["table", "sql_view"]))
        assets = q.all()
        return [{
            "id": a.id,
            "name": a.name,
            "alias": a.alias,
            "kind": a.kind,
            "table_name": (a.locator or {}).get("table", ""),
            "connection_id": a.connection_id,
            "description": a.description or "",
        } for a in assets]
