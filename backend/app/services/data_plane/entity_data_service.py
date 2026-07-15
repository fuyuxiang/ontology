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
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding
from app.repositories.asset_repo import AssetRepository
from app.repositories.object_binding_repo import ObjectBindingRepository
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.execute_service import (
    ExecuteBlocked,
    ExecuteRequest,
    ExecuteService,
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

    def get_attr_field_map(self, entity_id: str) -> dict[str, str]:
        """属性名 → 物理字段名。未配置 source_field 时回退为属性名本身。

        本体对外统一用属性名(本体语言),查询下发时必须翻译成物理列名，
        否则被重命名过的属性(如 related_order_no→order_id)会导致 Unknown column。
        """
        attrs = (
            self.db.query(EntityAttribute)
            .filter(EntityAttribute.entity_id == entity_id)
            .all()
        )
        return {a.name: (a.source_field or a.name) for a in attrs}

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

        try:
            limit = min(int(limit), 200)
        except (TypeError, ValueError):
            limit = 20

        # 属性名 → 物理字段名翻译层：本体对外用属性名，下发 SQL 必须用物理列名
        field_map = self.get_attr_field_map(entity_id)

        select_cols = "*"
        if fields:
            phys_fields = [
                field_map.get(f, f)
                for f in fields
                if not valid_attrs or f in valid_attrs
            ]
            if phys_fields:
                select_cols = ", ".join(phys_fields)

        sql = f"SELECT {select_cols} FROM {table_name}"

        where_parts: list[str] = []
        params: dict[str, Any] = {}
        for i, (attr_name, value) in enumerate((filters or {}).items()):
            if valid_attrs and attr_name not in valid_attrs:
                continue
            phys_col = field_map.get(attr_name, attr_name)
            param_key = f"p{i}"
            where_parts.append(f"{phys_col} = :{param_key}")
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

    def execute_ontology_sql(
        self,
        entities: list[OntologyEntity],
        sql: str,
        *,
        params: dict | None = None,
        purpose: str = "ontology_sql",
    ) -> dict:
        """执行以"本体对象名"书写的原生 SQL(支持多表 JOIN)。

        本体对外用对象名，物理层用真实表名。此前 complex_sql 既不重写对象名、
        白名单也只覆盖单个主 asset，导致：用对象名 → 表不存在；用物理表名多表
        JOIN → 第二张表不在白名单。这里统一：
        1) 把 SQL 中作为标识符出现的对象名替换成物理表名；
        2) 收集 SQL 实际引用到的所有 asset，主 asset 之外并入 additional_asset_ids；
        3) 走 ExecuteService(仍受 AST / 参数化 / 限流 / 审计 / 脱敏约束)。
        """
        if not entities:
            return {"error": "本体中没有可用的对象"}

        # 对象名(及中文名) → (asset, 物理表名)
        name_to_asset: dict[str, tuple[Asset, str]] = {}
        for ent in entities:
            resolved = self.resolve_entity_asset(ent.id)
            if not resolved:
                continue
            asset, _ = resolved
            table_name = self.get_table_name(asset)
            if not table_name:
                continue
            name_to_asset[ent.name] = (asset, table_name)
            if getattr(ent, "name_cn", None):
                name_to_asset[ent.name_cn] = (asset, table_name)

        if not name_to_asset:
            return {"error": "本体对象均未绑定可执行的数据资产"}

        rewritten_sql = sql
        referenced_assets: dict[str, Asset] = {}
        # 长名优先，避免 InstallOrder 被 InstallOrderItem 之类前缀误匹配
        for obj_name in sorted(name_to_asset, key=len, reverse=True):
            asset, table_name = name_to_asset[obj_name]
            pattern = re.compile(rf"(?<![\w.]){re.escape(obj_name)}(?![\w])")
            new_sql, n = pattern.subn(table_name, rewritten_sql)
            if n > 0:
                rewritten_sql = new_sql
                referenced_assets[asset.id] = asset

        if not referenced_assets:
            # SQL 未命中任何对象名，可能已直接写物理表名；退回全体候选做白名单
            for asset, _ in name_to_asset.values():
                referenced_assets[asset.id] = asset

        asset_ids = list(referenced_assets)
        primary_id = asset_ids[0]
        additional = asset_ids[1:]

        try:
            exec_result = self._exec_svc.execute(ExecuteRequest(
                asset_id=primary_id,
                sql=rewritten_sql,
                params=params or {},
                purpose=purpose,
                additional_asset_ids=additional or None,
            ))
            return {
                "columns": exec_result.columns,
                "rows": exec_result.rows,
                "rowCount": exec_result.rows_returned,
            }
        except ExecuteBlocked as e:
            return {"error": f"查询被拒绝：{e.detail or e.reason}"}
        except Exception as e:
            logger.warning("ontology sql execution failed: %s", e)
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
