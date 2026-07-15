"""数据查询工具 — ontology_query_instances + ontology_complex_sql_execute + ontology_object_find"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding
from app.models.shared_ref import OntologySharedRef
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
from app.services.mcp_tools.mcp_config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, MAX_RETURN_ROWS
from app.services.mcp_tools.registry import MCPTool, register
from app.services.mcp_tools.resolve import resolve_ontology_id


def _safe_int(value: Any, default: int) -> int:
    """把外部传入(可能是字符串)的分页参数安全转成 int，失败回退默认值。

    JSON 常把 page_size/limit 传成字符串，直接参与 min()/比较会抛
    '<' not supported between int and str。
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_entity_in_ontology(db: Session, ontology_id: str, object_name: str) -> OntologyEntity | None:
    """在本体范围内按名称查找实体"""
    owned_ids = {r[0] for r in db.query(OntologyEntity.id).filter(
        OntologyEntity.ontology_id == ontology_id
    ).all()}
    shared_ids = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
        OntologySharedRef.target_ontology_id == ontology_id
    ).all()}
    all_ids = owned_ids | shared_ids

    return (
        db.query(OntologyEntity)
        .filter(OntologyEntity.name == object_name, OntologyEntity.id.in_(all_ids))
        .first()
    )


def _get_all_entities_in_ontology(db: Session, ontology_id: str) -> list[OntologyEntity]:
    """获取本体范围内所有实体"""
    owned_ids = {r[0] for r in db.query(OntologyEntity.id).filter(
        OntologyEntity.ontology_id == ontology_id
    ).all()}
    shared_ids = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
        OntologySharedRef.target_ontology_id == ontology_id
    ).all()}
    all_ids = owned_ids | shared_ids
    return db.query(OntologyEntity).filter(OntologyEntity.id.in_(all_ids)).all()


def _get_attr_mapping(db: Session, entity_id: str) -> dict[str, str]:
    """属性名 → 物理字段名"""
    attrs = db.query(EntityAttribute).filter(EntityAttribute.entity_id == entity_id).all()
    return {a.name: a.source_field or a.name for a in attrs}


# ── ontology_query_instances ───────────────────────────────

@register
class QueryInstancesTool(MCPTool):
    name = "ontology_query_instances"
    description = "查询某对象类存储在物理数据源中的实例数据。支持 WHERE 过滤和分页。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "object_name": {"type": "string", "description": "对象类英文名"},
                "user_id": {"type": "string"},
                "where_sql": {"type": "string", "description": "SQL WHERE 片段，列名须为物理字段名"},
                "where_params": {"type": "array", "items": {}, "description": "占位参数"},
                "return_attrs": {"type": "array", "items": {"type": "string"}, "description": "返回的物理字段名列表"},
                "order_by": {"type": "string", "description": "排序表达式"},
                "page_size": {"type": "integer"},
                "page_token": {"type": "integer"},
            },
            "required": ["ontology_name", "object_name", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        object_name = arguments["object_name"]

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        entity = _get_entity_in_ontology(db, ontology_id, object_name)
        if not entity:
            return {"error": f"对象 '{object_name}' 在本体中不存在"}

        svc = EntityDataService(db)
        result = svc.resolve_entity_asset(entity.id)
        if not result:
            return {"error": f"实体 '{object_name}' 未绑定数据源"}

        asset, binding = result
        table_name = svc.get_table_name(asset)
        if not table_name:
            return {"error": f"实体 '{object_name}' 的资产未配置表名"}

        page_size = min(_safe_int(arguments.get("page_size"), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
        page_token = _safe_int(arguments.get("page_token"), 0)
        return_attrs = arguments.get("return_attrs")
        where_sql = arguments.get("where_sql", "")
        where_params = arguments.get("where_params") or []
        order_by = arguments.get("order_by", "")

        select_cols = "*"
        if return_attrs:
            select_cols = ", ".join(return_attrs)

        sql = f"SELECT {select_cols} FROM {table_name}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        sql += f" LIMIT {page_size}"
        if page_token:
            sql += f" OFFSET {page_token}"

        params = {f"p{i}": v for i, v in enumerate(where_params)}

        exec_svc = ExecuteService(db)
        try:
            req = ExecuteRequest(
                asset_id=asset.id,
                sql=sql,
                params=params,
                purpose=f"mcp.query_instances.{ontology_name}.{object_name}",
                timeout_ms=30000,
                user_id=arguments.get("user_id"),
            )
            exec_result = exec_svc.execute(req)
            items = [
                {col: row[i] for i, col in enumerate(exec_result.columns)}
                for row in exec_result.rows
            ]
            return {
                "items": items,
                "page_size": page_size,
                "next_page_token": page_token + page_size if len(items) == page_size else None,
                "total_count": len(items),
            }
        except Exception as e:
            return {"error": str(e)}


# ── ontology_complex_sql_execute ───────────────────────────

@register
class ComplexSqlTool(MCPTool):
    name = "ontology_complex_sql_execute"
    description = "执行复杂的原生 SQL 查询（CTE/子查询/窗口函数/多 JOIN）。SQL 中表名可用本体对象名，列名必须用物理字段名。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "user_id": {"type": "string"},
                "sql": {"type": "string", "description": "完整 SELECT SQL"},
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "SQL 中 %s 占位符参数",
                },
                "page_size": {"type": "integer"},
                "page_token": {"type": "integer"},
            },
            "required": ["ontology_name", "user_id", "sql"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        sql = arguments["sql"].replace("\n", " ").strip()
        params_list = arguments.get("params") or []
        page_size = min(_safe_int(arguments.get("page_size"), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
        page_token = _safe_int(arguments.get("page_token"), 0)

        entities = _get_all_entities_in_ontology(db, ontology_id)
        if not entities:
            return {"error": "本体中没有可用的对象"}

        # 分页：SQL 未显式带 LIMIT 时补上
        paginated_sql = sql
        if "LIMIT" not in sql.upper():
            paginated_sql += f" LIMIT {page_size}"
            if page_token:
                paginated_sql += f" OFFSET {page_token}"

        # 对象名→物理表名重写 + 多表白名单，统一走 EntityDataService.execute_ontology_sql
        svc = EntityDataService(db)
        result = svc.execute_ontology_sql(
            entities,
            paginated_sql,
            params={f"p{i}": v for i, v in enumerate(params_list)},
            purpose=f"mcp.complex_sql.{ontology_name}",
        )
        if "error" in result:
            return {"error": result["error"]}

        columns = result["columns"]
        items = [dict(zip(columns, row)) for row in result["rows"]]
        return {
            "items": items,
            "page_size": page_size,
            "next_page_token": page_token + page_size if len(items) == page_size else None,
            "total_count": len(items),
        }


# ── ontology_object_find ───────────────────────────────────

@register
class ObjectFindTool(MCPTool):
    name = "ontology_object_find"
    description = "对象级数据查询，自动解析实体对应的数据源和表，支持按属性过滤。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "object_name": {"type": "string"},
                "user_id": {"type": "string"},
                "filters": {"type": "object", "description": "属性过滤条件 {属性名: 值}"},
                "fields": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
            "required": ["ontology_name", "object_name", "user_id"],
            "additionalProperties": False,
        }

    async def execute(self, arguments: dict, **ctx: Any) -> Any:
        db: Session = ctx["db"]
        ontology_name = arguments["ontology_name"]
        object_name = arguments["object_name"]

        ontology_id = resolve_ontology_id(db, ontology_name)
        if not ontology_id:
            return {"error": f"本体 '{ontology_name}' 不存在"}

        entity = _get_entity_in_ontology(db, ontology_id, object_name)
        if not entity:
            return {"error": f"对象 '{object_name}' 不存在"}

        svc = EntityDataService(db)
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        limit = min(_safe_int(arguments.get("limit"), 50), 200)
        valid_attrs = set(_get_attr_mapping(db, entity.id).keys())

        return svc.query_entity_data(
            entity.id,
            filters=filters,
            fields=fields,
            limit=limit,
            purpose=f"mcp.object_find.{ontology_name}.{object_name}",
            valid_attrs=valid_attrs,
        )
