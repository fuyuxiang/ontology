"""数据查询工具 — ontology_query_instances + ontology_complex_sql_execute + ontology_object_find"""
from __future__ import annotations

from typing import Any
from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models.entity import EntityAttribute, OntologyEntity
from app.models.shared_ref import OntologySharedRef
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.execute_service import ExecuteRequest, ExecuteService
from app.services.mcp_tools.mcp_config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
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


def _get_entity_in_ontology(db: Session, ontology_id: str, object_name: str, version_id=None) -> OntologyEntity | None:
    """在本体范围内按名称查找实体"""
    matches = [e for e in _get_all_entities_in_ontology(db, ontology_id, version_id) if e.name == object_name]
    return matches[0] if len(matches) == 1 else None


def _get_all_entities_in_ontology(db: Session, ontology_id: str, version_id=None) -> list[OntologyEntity]:
    """获取本体范围内所有实体"""
    from app.models.version import OntologyVersion
    versions = db.query(OntologyVersion).filter_by(ontology_id=ontology_id, status="published")
    version = versions.filter_by(id=version_id).first() if version_id else versions.filter_by(is_active=True).first()
    if version:
        return [SimpleNamespace(id=e.source_entity_id, name=e.name, name_cn=e.name_cn,
                                attributes=e.attributes, version_entity=e) for e in version.entities]
    if version_id:
        raise ValueError("指定本体发布版本不存在")
    owned_ids = {r[0] for r in db.query(OntologyEntity.id).filter(
        OntologyEntity.ontology_id == ontology_id
    ).all()}
    shared_ids = {r[0] for r in db.query(OntologySharedRef.entity_id).filter(
        OntologySharedRef.target_ontology_id == ontology_id
    ).all()}
    all_ids = owned_ids | shared_ids
    return db.query(OntologyEntity).filter(OntologyEntity.id.in_(all_ids)).all()


def _entity_service(db, entity):
    if getattr(entity, "version_entity", None):
        from app.services.version_entity_data import VersionEntityDataService
        return VersionEntityDataService(db, entity.version_entity)
    return EntityDataService(db)


class _OntologyDataService(EntityDataService):
    def __init__(self, db, entities):
        super().__init__(db)
        self.entities = {entity.id: entity for entity in entities}
    def resolve_entity_asset(self, entity_id):
        return _entity_service(self.db, self.entities[entity_id]).resolve_entity_asset(entity_id)
    def get_attr_field_map(self, entity_id):
        return _entity_service(self.db, self.entities[entity_id]).get_attr_field_map(entity_id)


def _positional_sql(sql, values):
    for i in range(len(values)):
        token = "%s" if "%s" in sql else "?"
        if token in sql:
            sql = sql.replace(token, f":p{i}", 1)
    return sql


def _paginate_sql(sql, page_size, page_token, dialect):
    """Preserve explicit native pagination; append the connector's dialect."""
    import sqlglot
    from app.services.data_plane.sql_introspect import _dialect_name
    sql = sql.strip().rstrip(';')
    tree = sqlglot.parse_one(sql, read=_dialect_name(dialect))
    if tree.args.get('limit') or tree.args.get('offset'):
        return sql
    if dialect in {'sqlserver', 'oracle'}:
        if dialect == 'sqlserver' and not tree.args.get('order'):
            sql += ' ORDER BY (SELECT NULL)'
        return sql + f' OFFSET {page_token} ROWS FETCH NEXT {page_size} ROWS ONLY'
    return sql + f' LIMIT {page_size} OFFSET {page_token}'


def _binding_predicate(condition, values, dialect):
    import sqlglot
    from sqlglot import exp, Dialect
    from app.services.data_plane.sql_introspect import _dialect_name
    dialect_name = _dialect_name(dialect)
    parsed = sqlglot.parse_one(_positional_sql(condition, values), read=dialect_name, into=exp.Condition)
    # Connectors own driver parameter conversion. PostgreSQL's normal SQL
    # generator emits pyformat placeholders, which that layer would escape.
    class NamedGenerator(Dialect.get_or_raise(dialect_name).generator_class):
        def placeholder_sql(self, expression):
            return ":" + expression.name if expression.this else "?"
    return "(" + NamedGenerator(dialect=dialect_name, comments=False).generate(parsed) + ")"


def _get_attr_mapping(db: Session, entity_id: str) -> dict[str, str]:
    """属性名 → 物理字段名"""
    attrs = db.query(EntityAttribute).filter(EntityAttribute.entity_id == entity_id).all()
    return {a.name: a.source_field or a.name for a in attrs}


# ── ontology_query_instances ───────────────────────────────

@register
class QueryInstancesTool(MCPTool):
    name = "ontology_query_instances"
    description = "查询对象类的物理源实例，WHERE、返回字段、排序均使用物理字段；不应用映射transform。需要转换后的本体属性值时使用ontology_object_find。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "version_id": {"type": "string"},
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

        entity = _get_entity_in_ontology(db, ontology_id, object_name, arguments.get("version_id"))
        if not entity:
            return {"error": f"对象 '{object_name}' 在本体中不存在"}

        svc = _entity_service(db, entity)
        result = svc.resolve_entity_asset(entity.id)
        if not result:
            return {"error": f"实体 '{object_name}' 未绑定数据源"}

        asset, binding = result
        table_name = svc.get_table_name(asset)
        if not table_name:
            return {"error": f"实体 '{object_name}' 的资产未配置表名"}

        page_size = max(1, min(_safe_int(arguments.get("page_size"), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
        page_token = max(0, _safe_int(arguments.get("page_token"), 0))
        return_attrs = arguments.get("return_attrs")
        where_sql = arguments.get("where_sql", "")
        where_params = arguments.get("where_params") or []
        order_by = arguments.get("order_by", "")

        allowed_columns = set(svc.get_attr_field_map(entity.id).values())
        selected = return_attrs or sorted(allowed_columns)
        if not selected or set(selected) - allowed_columns:
            return {"error": "返回字段必须属于当前发布本体映射"}
        from app.connectors import ConnectorRegistry
        from app.models.connection import Connection
        connection = db.get(Connection, asset.connection_id)
        quote = ConnectorRegistry.get(connection.type).quote_identifier()
        select_cols = ", ".join(quote + col.replace(quote, quote + quote) + quote for col in selected)

        sql = f"SELECT {select_cols} FROM {table_name}"
        predicates = []
        try:
            import sqlglot
            for condition in (where_sql, binding.filter_expr):
                if condition:
                    # Parse each predicate separately before combining it. OR,
                    # comments and malformed fragments cannot escape the
                    # mandatory binding filter through SQL concatenation.
                    predicates.append(_binding_predicate(condition, where_params, connection.type))
        except (ValueError, sqlglot.errors.ParseError) as exc:
            return {"error": f"无效的查询过滤条件: {exc}"}
        if predicates:
            sql += " WHERE " + " AND ".join(predicates)
        if order_by:
            sql += f" ORDER BY {order_by}"
        sql = _positional_sql(sql, where_params)
        sql = _paginate_sql(sql, page_size, page_token, connection.type)
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
                "value_semantics": "physical_source",
                "transform_applied": False,
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
    description = "执行物理源只读 SQL（CTE/子查询/窗口函数/多 JOIN）。表名可用本体对象名，列名必须用物理字段名；聚合、过滤和排序基于源原值，不应用映射transform。转换后的本体属性值使用ontology_object_find。"

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology_name": {"type": "string"},
                "version_id": {"type": "string"},
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
        page_size = max(1, min(_safe_int(arguments.get("page_size"), DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE))
        page_token = max(0, _safe_int(arguments.get("page_token"), 0))

        sql = _positional_sql(sql, params_list)
        entities = _get_all_entities_in_ontology(db, ontology_id, arguments.get("version_id"))
        if not entities:
            return {"error": "本体中没有可用的对象"}

        # 对象名→物理表名重写 + 多表白名单，统一走 EntityDataService.execute_ontology_sql
        svc = _OntologyDataService(db, entities)
        resolved = svc.resolve_entity_asset(entities[0].id)
        if not resolved:
            return {"error": "对象未绑定可执行资产"}
        from app.models.connection import Connection
        connection = db.get(Connection, resolved[0].connection_id)
        if not connection:
            return {"error": "资产连接不存在"}
        paginated_sql = _paginate_sql(sql, page_size, page_token, connection.type)
        result = svc.execute_ontology_sql(
            entities,
            paginated_sql,
            params={f"p{i}": v for i, v in enumerate(params_list)},
            purpose=f"mcp.complex_sql.{ontology_name}",
        )
        if "error" in result:
            return {"error": result["error"]}

        columns = result["columns"]
        items = [dict(zip(columns, row, strict=True)) for row in result["rows"]]
        return {
            "items": items,
            "value_semantics": "physical_source",
            "transform_applied": False,
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
                "version_id": {"type": "string"},
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

        entity = _get_entity_in_ontology(db, ontology_id, object_name, arguments.get("version_id"))
        if not entity:
            return {"error": f"对象 '{object_name}' 不存在"}

        svc = _entity_service(db, entity)
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        limit = min(_safe_int(arguments.get("limit"), 50), 200)
        # Attribute authorization includes frozen enrichment attributes. The
        # common query service checks actual binding, join and transform rules.
        valid_attrs = {attribute.name for attribute in entity.attributes}

        return svc.query_entity_data(
            entity.id,
            filters=filters,
            fields=fields,
            limit=limit,
            purpose=f"mcp.object_find.{ontology_name}.{object_name}",
            valid_attrs=valid_attrs,
        )
