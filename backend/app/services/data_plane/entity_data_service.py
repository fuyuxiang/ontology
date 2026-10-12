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

from app.connectors import ConnectorRegistry
from app.models.connection import Connection
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
        """Only explicit primary mappings become physical SELECT columns."""
        attrs = (
            self.db.query(EntityAttribute)
            .filter(EntityAttribute.entity_id == entity_id)
            .all()
        )
        resolved = self.resolve_entity_asset(entity_id)
        if not resolved:
            return {}
        asset, binding = resolved
        mapping = {fm.get("attribute_id"): fm.get("source_column") for fm in binding.field_mappings or []}
        columns = {c.get("name") for c in asset.schema_snapshot or []}
        # Bindings are authoritative, with no source_field compatibility fallback.
        return {a.name: col for a in attrs
                if (col := mapping.get(a.id))
                and (not columns or col in columns)}

    def get_query_attribute_names(self, entity_id: str) -> dict[str, str]:
        return {attribute.id: attribute.name for attribute in self.db.query(EntityAttribute).filter_by(entity_id=entity_id).all()}

    def get_query_attribute_specs(self, entity_id: str) -> dict[str, dict]:
        return {attribute.name: {"type": attribute.type, "required": attribute.required,
                                 "enum": (attribute.constraints_json or {}).get("enum")}
                for attribute in self.db.query(EntityAttribute).filter_by(entity_id=entity_id).all()}

    def resolve_entity_enrichments(self, entity_id: str) -> list[tuple[Asset, ObjectBinding]]:
        return [(self.db.get(Asset, binding.asset_id), binding)
                for binding in self._binding_repo.list(object_type_id=entity_id, role="enrichment")
                if binding.status != "deprecated"]

    def _source_sql(self, asset: Asset) -> str:
        connection = self.db.get(Connection, asset.connection_id)
        alias = "_enrichment" if connection and connection.type == "oracle" else "AS _enrichment"
        return "<asset>" if asset.kind == "table" else f"({(asset.locator or {}).get('sql') or ''}) {alias}"

    def _quote(self, asset: Asset, column: str) -> str:
        connection = self.db.get(Connection, asset.connection_id)
        if not connection:
            raise ValueError("数据资产缺少有效连接")
        if column not in {c.get("name") for c in asset.schema_snapshot or []}:
            raise ValueError(f"源关联或映射字段不存在: {column}")
        quote = ConnectorRegistry.get(connection.type).quote_identifier()
        return quote + column.replace(quote, quote + quote) + quote

    def _assert_unique_join_key(self, asset, binding, key, *, purpose):
        column = self._quote(asset, key)
        clauses = [f"{column} IS NOT NULL"]
        if binding.filter_expr:
            clauses.append(f"({binding.filter_expr})")
        sql = f"SELECT {column}, COUNT(*) FROM {self._source_sql(asset)} WHERE {' AND '.join(clauses)} GROUP BY {column} HAVING COUNT(*) > 1"
        connection = self.db.get(Connection, asset.connection_id)
        sql += f" ORDER BY {column} OFFSET 0 ROWS FETCH NEXT 1 ROWS ONLY" if connection.type in {"oracle", "sqlserver"} else " LIMIT 1"
        result = self._exec_svc.execute(ExecuteRequest(asset_id=asset.id, sql=sql, params={}, purpose=purpose, bypass_cache=True))
        if result.rows:
            raise ValueError(f"一对一关联列 {key} 存在重复匹配，请修复源数据后重试")

    def _join_enrichment_rows(self, rows, columns, entries, *, purpose):
        merged = [dict(zip(columns, row)) for row in rows]
        for index, (asset, binding, mapping) in enumerate(entries):
            hidden = f"__join_primary_{index}"
            keys = list(dict.fromkeys(row.get(hidden) for row in merged if row.get(hidden) is not None))
            lookup = {}
            if keys:
                key_column = self._quote(asset, binding.enrichment_source_column)
                names = list(mapping)
                physical = [self._quote(asset, mapping[name]) for name in names]
                params = {f"join_{i}": value for i, value in enumerate(keys)}
                placeholders = ', '.join(':' + name for name in params)
                clauses = [f"{key_column} IN ({placeholders})"]
                if binding.filter_expr:
                    clauses.append(f"({binding.filter_expr})")
                sql = f"SELECT {', '.join([key_column, *physical])} FROM {self._source_sql(asset)} WHERE {' AND '.join(clauses)}"
                result = self._exec_svc.execute(ExecuteRequest(asset_id=asset.id, sql=sql, params=params, purpose=purpose, bypass_cache=True, apply_sensitivity=False))
                for raw in result.rows:
                    key = raw[0]
                    if key in lookup:
                        raise ValueError("一对一 enrichment 关联出现重复匹配，未返回不完整实例")
                    lookup[key] = dict(zip(names, raw[1:]))
            for row in merged:
                row.update(lookup.get(row.get(hidden), {name: None for name in mapping}))
        return merged

    def query_entity_data(self, entity_id: str, *, filters: dict | None = None,
                          fields: list[str] | None = None, limit: int = 20, offset: int = 0,
                          purpose: str = "entity_data_query", valid_attrs: set[str] | None = None) -> dict:
        try:
            resolved = self.resolve_entity_asset(entity_id)
            if not resolved:
                return {"error": f"实体 '{entity_id}' 未绑定活动主数据资产"}
            primary_asset, primary_binding = resolved
            primary_map = self.get_attr_field_map(entity_id)
            names_by_id = self.get_query_attribute_names(entity_id)
            entries, all_map = [], dict(primary_map)
            transformations = {names_by_id[m["attribute_id"]]: m["transform"]
                               for m in primary_binding.field_mappings or []
                               if m.get("attribute_id") in names_by_id and m.get("transform")}
            self._validate_transform_keys(primary_asset, primary_binding)
            for asset, binding in self.resolve_entity_enrichments(entity_id):
                if asset:
                    self._validate_transform_keys(asset, binding)
                mapping = {names_by_id[m.get("attribute_id")]: m.get("source_column")
                           for m in (binding.field_mappings or []) if m.get("attribute_id") in names_by_id}
                for name in mapping:
                    if name in all_map:
                        raise ValueError(f"属性 {name} 被多个来源重复映射，请确认唯一属性来源")
                all_map.update(mapping)
                transformations.update({names_by_id[m["attribute_id"]]: m["transform"]
                    for m in binding.field_mappings or [] if m.get("attribute_id") in names_by_id and m.get("transform")})
                entries.append((asset, binding, mapping))
            allowed = set(all_map) if valid_attrs is None else set(all_map) & valid_attrs
            selected = list(dict.fromkeys(fields)) if fields else [name for name in all_map if name in allowed]
            invalid = (set(selected) | set(filters or {})) - allowed
            if invalid:
                return {"error": f"属性未定义或未绑定: {', '.join(sorted(invalid))}"}
            needed = set(selected) | set(filters or {})
            transformations = {name: expression for name, expression in transformations.items() if name in needed}
            entries = [entry for entry in entries if set(entry[2]) & needed]
            if not entries and not transformations:
                return self._query_primary_data(entity_id, filters=filters, fields=fields, limit=limit,
                                                offset=offset, purpose=purpose, valid_attrs=valid_attrs)
            limit, offset = max(1, min(int(limit), 200)), max(0, int(offset))
            for asset, binding, mapping in entries:
                if not asset or asset.status != "active" or binding.status != "active":
                    raise ValueError("enrichment 数据绑定或资产尚未审核/已失效，请修复后重试")
                if not binding.primary_source_column or not binding.enrichment_source_column:
                    raise ValueError("enrichment 缺少明确关联列，请配置后重新审核")
                self._quote(primary_asset, binding.primary_source_column)
                self._quote(asset, binding.enrichment_source_column)
                self._assert_unique_join_key(primary_asset, primary_binding, binding.primary_source_column, purpose=purpose + ".primary_key_check")
                self._assert_unique_join_key(asset, binding, binding.enrichment_source_column, purpose=purpose + ".enrichment_key_check")
            hidden_fields = {f"__join_primary_{i}": binding.primary_source_column for i, (_, binding, _) in enumerate(entries)}
            primary_fields = list(dict.fromkeys(name for name in [*selected, *(filters or {})] if name in primary_map))
            primary_filters = {k: v for k, v in (filters or {}).items() if k in primary_map and k not in transformations}
            enrichment_filters = {k: v for k, v in (filters or {}).items() if k not in primary_map or k in transformations}
            fetched_fields = [*primary_fields, *hidden_fields]
            # Enrichment filtering must precede pagination. For distinct connections
            # scan bounded pages; reaching the guard is an explicit error, never a
            # silently truncated successful query.
            scan_offset = 0 if enrichment_filters else offset
            matches = []
            while True:
                batch_limit = 200 if enrichment_filters else limit
                result = self._query_primary_data(entity_id, filters=primary_filters, fields=fetched_fields,
                    limit=batch_limit, offset=scan_offset, purpose=purpose, _physical_fields=hidden_fields, _unredacted=True)
                if result.get("error"):
                    return result
                rows = self._join_enrichment_rows(result["rows"], result["columns"], entries, purpose=purpose + ".enrichment")
                from app.services.data_plane.mapping_transform import apply_transform
                from app.services.agent_actions import validate_parameters
                specs = self.get_query_attribute_specs(entity_id) if transformations else {}
                for row in rows:
                    for name, expression in transformations.items():
                        row[name] = apply_transform(row.get(name), expression)
                        if row[name] is None and specs.get(name, {}).get("required"):
                            raise ValueError(f"transform 转换后必填属性 {name} 为空")
                        if row[name] is not None:
                            validate_parameters([{"name": name, **specs.get(name, {})}], {name: row[name]})
                matches.extend(row for row in rows if all(row.get(key) == value for key, value in enrichment_filters.items()))
                if not enrichment_filters or len(matches) >= offset + limit or len(result["rows"]) < batch_limit:
                    break
                scan_offset += batch_limit
                if scan_offset >= 10000:
                    raise ValueError("转换或跨源过滤扫描超过10000行，请先增加原始主资产过滤条件")
            if enrichment_filters:
                matches = matches[offset:offset + limit]
            from app.services.data_plane.execute_service import _redact_value
            levels = {name: (primary_asset.sensitivity_tags or {}).get(column) for name, column in primary_map.items()}
            for asset, _, mapping in entries:
                levels.update({name: (asset.sensitivity_tags or {}).get(column) for name, column in mapping.items()})
            return {"columns": selected, "rows": [[_redact_value(row.get(name), levels[name]) if levels.get(name) else row.get(name)
                for name in selected] for row in matches], "rowCount": len(matches)}
        except Exception as exc:
            logger.warning("entity enrichment query failed: %s", type(exc).__name__)
            return {"error": f"实例关联查询失败：{exc}"}

    @staticmethod
    def _validate_transform_keys(asset, binding):
        from app.services.data_plane.mapping_transform import validate_transform
        primary_keys = set(getattr(binding, "asset_primary_keys", None) or asset.primary_key or []) | {getattr(binding, "id_column", None)}
        for mapping in binding.field_mappings or []:
            if mapping.get("transform"):
                validate_transform(mapping["transform"])
                if mapping.get("source_column") in primary_keys:
                    raise ValueError("主键字段禁止 transform，请修复旧绑定后重新审核")

    def _query_primary_data(
        self,
        entity_id: str,
        *,
        filters: dict | None = None,
        fields: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        purpose: str = "entity_data_query",
        valid_attrs: set[str] | None = None,
        _physical_fields: dict[str, str] | None = None,
        _unredacted: bool = False,
    ) -> dict:
        result = self.resolve_entity_asset(entity_id)
        if not result:
            return {"error": f"实体 '{entity_id}' 未绑定数据资产，请先在数据集成中创建 ObjectBinding"}
        asset, binding = result
        table_name = self.get_table_name(asset)
        if not table_name and asset.kind != "sql_view":
            return {"error": f"资产 '{asset.name}' 未配置表名（locator.table 为空）"}

        try:
            limit = max(1, min(int(limit), 200))
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            return {"error": "limit/offset 必须为整数"}

        # 属性名 → 物理字段名翻译层：本体对外用属性名，下发 SQL 必须用物理列名
        field_map = {**self.get_attr_field_map(entity_id), **(_physical_fields or {})}

        allowed = set(field_map) if valid_attrs is None else set(field_map) & valid_attrs
        selected = list(dict.fromkeys(fields)) if fields else [name for name in field_map if name in allowed]
        invalid = (set(selected) | set(filters or {})) - allowed
        if invalid:
            return {"error": f"属性未定义或未绑定: {', '.join(sorted(invalid))}"}
        if not selected:
            return {"error": "对象没有可查询的已映射属性"}
        connection = self.db.get(Connection, asset.connection_id) if asset.connection_id else None
        if not connection:
            return {"error": "数据资产缺少有效连接"}
        quote = ConnectorRegistry.get(connection.type).quote_identifier()
        def quoted(name):
            return quote + name.replace(quote, quote + quote) + quote
        select_cols = ", ".join(quoted(field_map[f]) for f in selected)
        alias = "_entity" if connection.type == "oracle" else "AS _entity"
        source = "<asset>" if asset.kind == "table" else f"({(asset.locator or {}).get('sql') or ''}) {alias}"
        sql = f"SELECT {select_cols} FROM {source}"

        where_parts: list[str] = []
        params: dict[str, Any] = {}
        for i, (attr_name, value) in enumerate((filters or {}).items()):
            phys_col = quoted(field_map[attr_name])
            param_key = f"p{i}"
            if value is None:
                where_parts.append(f"{phys_col} IS NULL")
            else:
                where_parts.append(f"{phys_col} = :{param_key}")
                params[param_key] = value

        if binding.filter_expr:
            where_parts.append(f"({binding.filter_expr})")

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        order_column = binding.id_column
        if order_column and order_column in {c.get("name") for c in asset.schema_snapshot or []}:
            sql += f" ORDER BY {quoted(order_column)}"
        if connection.type in ("oracle", "sqlserver"):
            if connection.type == "sqlserver" and not order_column:
                sql += " ORDER BY (SELECT NULL)"
            sql += f" OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"
        else:
            sql += f" LIMIT {limit} OFFSET {offset}"

        try:
            exec_result = self._exec_svc.execute(ExecuteRequest(
                asset_id=asset.id, sql=sql, params=params, purpose=purpose, bypass_cache=bool(_physical_fields) or _unredacted,
                apply_sensitivity=not (bool(_physical_fields) or _unredacted),
            ))
            return {
                "columns": selected,
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
        # 长名优先，避免短名被长名前缀误匹配
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
            return {"error": "需要提供 table_name 或资产需配置表（locator.table）"}
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
