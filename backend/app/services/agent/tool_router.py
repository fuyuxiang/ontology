"""
Agent 工具路由 — 工具分发与执行
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import OntologyEntity, EntityRelation, BusinessRule, DataSource
from app.services.datasource_utils import (
    get_table_schema as ds_get_table_schema,
    execute_readonly_sql,
)
from app.services.rule_engine import RuleEvaluator, ActionExecutor, RuleScreener

logger = logging.getLogger(__name__)


class ToolRouter:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, tool_name: str, args: dict) -> tuple[Any, str, int]:
        handlers = {
            "describe_ontology_model": self._tool_describe_ontology_model,
            "list_datasources": self._tool_list_datasources,
            "get_table_schema": self._tool_get_table_schema,
            "query_datasource": self._tool_query_datasource,
            "get_entity_detail": self._tool_get_entity_detail,
            "query_entity_data": self._tool_query_entity_data,
            "get_business_rules": self._tool_get_business_rules,
            "evaluate_rule": self._tool_evaluate_rule,
            "evaluate_all_rules": self._tool_evaluate_all_rules,
            "screen_users_by_rule": self._tool_screen_users_by_rule,
            "execute_action": self._tool_execute_action,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"未知工具: {tool_name}"}, f"未知工具 {tool_name}", 0
        try:
            return handler(args)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return {"error": str(e)}, f"执行失败: {e}", 0

    def _tool_describe_ontology_model(self, args: dict) -> tuple[Any, str, int]:
        entities = self.db.query(OntologyEntity).all()
        relations = self.db.query(EntityRelation).all()
        rules = self.db.query(BusinessRule).filter(BusinessRule.status == "active").all()

        tier_names = {1: "核心", 2: "领域", 3: "场景"}
        entity_list = []
        for e in entities:
            attrs = [{"name": a.name, "type": a.type, "description": a.description} for a in e.attributes]
            entity_list.append({
                "name": e.name, "name_cn": e.name_cn,
                "tier": e.tier, "tierLabel": tier_names.get(e.tier, ""),
                "attrCount": len(attrs), "attributes": attrs[:10],
            })
        rel_list = []
        entity_map = {e.id: e.name for e in entities}
        for r in relations:
            rel_list.append({
                "from": entity_map.get(r.from_entity_id, "?"),
                "to": entity_map.get(r.to_entity_id, "?"),
                "name": r.name, "cardinality": r.cardinality,
            })
        rule_list = [{
            "name": r.name, "condition": r.condition_expr, "action": r.action_desc,
            "entity": entity_map.get(r.entity_id, "?"),
        } for r in rules[:10]]
        result = {"entities": entity_list, "relations": rel_list, "rules": rule_list}
        return result, f"本体模型: {len(entity_list)} 实体, {len(rel_list)} 关系, {len(rules)} 规则", len(entity_list)

    def _tool_list_datasources(self, args: dict) -> tuple[Any, str, int]:
        datasources = self.db.query(DataSource).filter(DataSource.enabled == True).all()
        ds_list = [{
            "name": ds.name, "type": ds.type, "table_name": ds.table_name,
            "record_count": ds.record_count, "database": ds.database,
        } for ds in datasources]
        return ds_list, f"返回 {len(ds_list)} 个已启用数据源", len(ds_list)

    def _tool_get_table_schema(self, args: dict) -> tuple[Any, str, int]:
        ds_name = str(args.get("datasource_name", "")).strip()
        table_name = str(args.get("table_name", "")).strip()
        if not ds_name:
            return {"error": "需要提供 datasource_name"}, "参数不完整", 0
        ds = self.db.query(DataSource).filter(DataSource.name == ds_name, DataSource.enabled == True).first()
        if not ds:
            return {"error": f"数据源 '{ds_name}' 不存在或未启用"}, "数据源不可用", 0
        tbl = table_name or ds.table_name
        if not tbl:
            return {"error": "需要提供 table_name 或数据源需配置默认表"}, "表名缺失", 0
        columns = ds_get_table_schema(ds, tbl)
        return {"table": tbl, "columns": columns}, f"表 {tbl} 共 {len(columns)} 列", len(columns)

    def _tool_query_datasource(self, args: dict) -> tuple[Any, str, int]:
        ds_name = str(args.get("datasource_name", "")).strip()
        sql = str(args.get("sql", "")).strip()
        if not ds_name or not sql:
            return {"error": "需要提供 datasource_name 和 sql"}, "参数不完整", 0
        ds = self.db.query(DataSource).filter(DataSource.name == ds_name, DataSource.enabled == True).first()
        if not ds:
            return {"error": f"数据源 '{ds_name}' 不存在或未启用"}, "数据源不可用", 0
        result = execute_readonly_sql(ds, sql)
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0
        return result, f"查询返回 {result['rowCount']} 行", result["rowCount"]

    def _tool_get_entity_detail(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        if not entity_name:
            return {"error": "需要提供 entity_name"}, "参数不完整", 0
        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"实体 '{entity_name}' 不存在"}, "实体不存在", 0
        attrs = [{"name": a.name, "type": a.type, "description": a.description, "required": a.required} for a in entity.attributes]
        rels_from = self.db.query(EntityRelation).filter(EntityRelation.from_entity_id == entity.id).all()
        rels_to = self.db.query(EntityRelation).filter(EntityRelation.to_entity_id == entity.id).all()
        all_entities = {e.id: e.name for e in self.db.query(OntologyEntity).all()}
        relations = []
        for r in rels_from:
            relations.append({"direction": "out", "name": r.name, "target": all_entities.get(r.to_entity_id, "?"), "cardinality": r.cardinality})
        for r in rels_to:
            relations.append({"direction": "in", "name": r.name, "source": all_entities.get(r.from_entity_id, "?"), "cardinality": r.cardinality})
        rules = [{"name": r.name, "condition": r.condition_expr, "action": r.action_desc, "status": r.status} for r in entity.rules]
        result = {
            "name": entity.name, "name_cn": entity.name_cn, "tier": entity.tier,
            "description": entity.description or "",
            "attributes": attrs, "relations": relations, "rules": rules,
        }
        return result, f"返回实体 {entity.name_cn} 的详情", 1

    def _tool_query_entity_data(self, args: dict) -> tuple[Any, str, int]:
        """通过本体实体名查询真实实例数据，自动解析数据源"""
        entity_name = str(args.get("entity_name", "")).strip()
        filters = args.get("filters") or {}
        fields = args.get("fields") or []
        limit = min(int(args.get("limit", 20)), 200)

        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"本体中不存在实体 '{entity_name}'"}, "实体不存在", 0

        schema = entity.schema_json or {}
        ds_ref = schema.get("datasource_ref", "")
        if not ds_ref:
            return {"error": f"实体 '{entity_name}' 未关联数据源"}, "无数据源映射", 0

        ds = self.db.query(DataSource).filter(
            DataSource.name == ds_ref, DataSource.enabled == True
        ).first()
        if not ds:
            return {"error": f"数据源 '{ds_ref}' 不存在或未启用"}, "数据源不可用", 0
        if not ds.table_name:
            return {"error": f"数据源 '{ds_ref}' 未配置表名"}, "表名缺失", 0

        valid_attrs = {a.name for a in entity.attributes}
        select_cols = "*"
        if fields:
            valid_fields = [f for f in fields if f in valid_attrs]
            if valid_fields:
                select_cols = ", ".join(valid_fields)

        sql = f"SELECT {select_cols} FROM {ds.table_name}"

        where_parts = []
        for attr_name, value in filters.items():
            if attr_name not in valid_attrs:
                continue
            if isinstance(value, str):
                where_parts.append(f"{attr_name} = '{value}'")
            elif isinstance(value, (int, float)):
                where_parts.append(f"{attr_name} = {value}")
            elif isinstance(value, bool):
                where_parts.append(f"{attr_name} = {1 if value else 0}")

        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        result = execute_readonly_sql(ds, sql, limit)
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0

        result["entity"] = entity_name
        result["entity_cn"] = entity.name_cn
        result["datasource"] = ds_ref
        result["table"] = ds.table_name
        return result, f"通过本体 {entity.name_cn} 查询到 {result['rowCount']} 条记录", result["rowCount"]

    def _tool_get_business_rules(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        status = str(args.get("status", "active")).strip()
        query = self.db.query(BusinessRule)
        if status != "all":
            query = query.filter(BusinessRule.status == status)
        if entity_name:
            entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
            if entity:
                query = query.filter(BusinessRule.entity_id == entity.id)
            else:
                return {"error": f"实体 '{entity_name}' 不存在"}, f"实体不存在", 0
        rules = query.all()
        all_entities = {e.id: e.name for e in self.db.query(OntologyEntity).all()}
        rule_list = [{
            "name": r.name, "condition": r.condition_expr, "action": r.action_desc,
            "status": r.status, "priority": r.priority,
            "entity": all_entities.get(r.entity_id, "?"),
            "triggerCount": r.trigger_count,
            "has_structured_conditions": r.conditions_json is not None,
        } for r in rules]
        return rule_list, f"返回 {len(rule_list)} 条业务规则", len(rule_list)

    def _tool_evaluate_rule(self, args: dict) -> tuple[Any, str, int]:
        rule_name = str(args.get("rule_name", "")).strip()
        user_id = str(args.get("user_id", "")).strip()
        if not rule_name or not user_id:
            return {"error": "需要提供 rule_name 和 user_id"}, "参数不完整", 0

        rule = self.db.query(BusinessRule).filter(
            BusinessRule.name == rule_name,
            BusinessRule.status == "active",
        ).first()
        if not rule:
            return {"error": f"规则 '{rule_name}' 不存在或未激活"}, "规则不存在", 0
        if not rule.conditions_json:
            return {"error": f"规则 '{rule_name}' 没有结构化条件，无法评估"}, "无结构化条件", 0

        evaluator = RuleEvaluator(self.db)
        result = evaluator.evaluate(rule, user_id)
        self.db.commit()
        result_dict = RuleEvaluator._result_to_dict(result)
        summary = f"规则 '{rule_name}' {'触发' if result.triggered else '未触发'} (匹配 {result.matched_count}/{result.total_count})"
        return result_dict, summary, 1

    def _tool_evaluate_all_rules(self, args: dict) -> tuple[Any, str, int]:
        user_id = str(args.get("user_id", "")).strip()
        if not user_id:
            return {"error": "需要提供 user_id"}, "参数不完整", 0

        evaluator = RuleEvaluator(self.db)
        result = evaluator.evaluate_all(user_id)
        triggered = result["triggered_count"]
        total = result["evaluated_count"]
        risk = result["overall_risk"]
        summary = f"评估 {total} 条规则，{triggered} 条触发，综合风险: {risk}"
        return result, summary, total

    def _tool_screen_users_by_rule(self, args: dict) -> tuple[Any, str, int]:
        rule_name = str(args.get("rule_name", "")).strip()
        limit = int(args.get("limit", 50))
        if not rule_name:
            return {"error": "需要提供 rule_name"}, "参数不完整", 0

        screener = RuleScreener(self.db)
        result = screener.screen_by_name(rule_name, limit)
        if result.get("error"):
            return result, f"筛选失败: {result['error']}", 0
        matched = result.get("matched_users", 0)
        risk = result.get("risk_level", "")
        summary = f"根据规则 '{rule_name}' 筛选出 {matched} 个{risk}风险用户"
        return result, summary, matched

    def _tool_execute_action(self, args: dict) -> tuple[Any, str, int]:
        action_name = str(args.get("action_name", "")).strip()
        params = args.get("params", {})
        dry_run = args.get("dry_run", True)
        if not action_name:
            return {"error": "需要提供 action_name"}, "参数不完整", 0

        executor = ActionExecutor(self.db)
        result = executor.execute_by_name(action_name, params, dry_run)
        result_dict = {
            "action_name": result.action_name,
            "success": result.success,
            "message": result.message,
            "effects": result.effects,
            "precondition_results": result.precondition_results,
        }
        mode = "模拟执行" if dry_run else "执行"
        summary = f"{mode} '{action_name}' {'成功' if result.success else '失败'}"
        return result_dict, summary, 1
