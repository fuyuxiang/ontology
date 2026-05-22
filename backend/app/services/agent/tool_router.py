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
            # 本体构建器（chat 模式）三件套
            "list_business_datasources": self._tool_list_business_datasources,
            "list_business_documents": self._tool_list_business_documents,
            "analyze_assets_for_ontology": self._tool_analyze_assets_for_ontology,
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

    # ── 本体构建器（chat 模式）三件套 ────────────────────────────

    def _tool_list_business_datasources(self, args: dict) -> tuple[Any, str, int]:
        """列出业务数据源（带前 3 张表名），返回 display_card=asset_picker。"""
        from app.services.datasource_utils import get_table_schema as _get_schema  # noqa: F401

        domain = str(args.get("domain", "")).strip()
        keywords = args.get("keywords") or []
        if not isinstance(keywords, list):
            keywords = []

        q = self.db.query(DataSource).filter(DataSource.enabled == True)  # noqa: E712
        rows = q.all()

        def matches(ds: DataSource) -> bool:
            blob = " ".join(filter(None, [
                ds.name or "", ds.description or "", ds.table_name or "", ds.database or "",
            ])).lower()
            if domain and domain.lower() not in blob:
                return False
            if keywords:
                return any(str(k).lower() in blob for k in keywords)
            return True

        items = []
        for ds in rows:
            if not matches(ds):
                continue
            tables = []
            try:
                # tables_json 可能是 list[str] 或 list[dict]
                t = getattr(ds, "tables_json", None) or []
                for x in t[:3]:
                    if isinstance(x, dict):
                        tables.append(x.get("table_name") or x.get("name") or "")
                    else:
                        tables.append(str(x))
            except Exception:
                pass
            if not tables and ds.table_name:
                tables = [ds.table_name]
            items.append({
                "id": ds.id, "name": ds.name, "description": ds.description or "",
                "table_count": len(tables) or (1 if ds.table_name else 0),
                "domain_tags": [],
                "sample_tables": [t for t in tables if t][:3],
            })

        result = {
            "items": items,
            "display_card": {
                "type": "asset_picker",
                "kind": "datasource",
                "title": f"为「{domain or '该业务'}」匹配到 {len(items)} 个数据源",
                "items": items,
            },
        }
        return result, f"匹配 {len(items)} 个数据源", len(items)

    def _tool_list_business_documents(self, args: dict) -> tuple[Any, str, int]:
        """列出业务文档库候选文档，返回 display_card=asset_picker。"""
        from app.models import BusinessDocument

        domain = str(args.get("domain", "")).strip()
        ds_ids = args.get("datasource_ids") or []
        rows = self.db.query(BusinessDocument).all()

        def matches(d: BusinessDocument) -> bool:
            if not domain:
                return True
            tags = " ".join(d.domain_tags or [])
            blob = f"{d.name or ''} {tags} {d.summary or ''}".lower()
            return domain.lower() in blob

        items = []
        for d in rows:
            if not matches(d):
                continue
            items.append({
                "id": d.id, "name": d.name, "file_type": d.file_type or "",
                "size_bytes": d.size_bytes or 0,
                "domain_tags": list(d.domain_tags or []),
                "summary": d.summary or "",
            })

        result = {
            "items": items,
            "linked_datasource_ids": list(ds_ids) if isinstance(ds_ids, list) else [],
            "display_card": {
                "type": "asset_picker",
                "kind": "document",
                "title": f"为「{domain or '该业务'}」匹配到 {len(items)} 份业务文档",
                "items": items,
            },
        }
        return result, f"匹配 {len(items)} 份文档", len(items)

    def _tool_analyze_assets_for_ontology(self, args: dict) -> tuple[Any, str, int]:
        """根据已选数据源 + 文档 + 上下文，让 LLM 抽取本体草稿（含规则/动作建议）。"""
        from app.services.datasource_utils import get_table_schema
        from app.models import BusinessDocument
        from app.config import settings as _settings
        from app.services.copilot import get_llm_client
        import json as _json
        import re as _re

        ds_ids = args.get("datasource_ids") or []
        doc_ids = args.get("document_ids") or []
        ctx = str(args.get("business_context") or "").strip()

        # 1. 拼数据源 schema
        ds_blocks: list[str] = []
        for did in ds_ids:
            ds = self.db.get(DataSource, did)
            if not ds:
                continue
            tables = []
            try:
                tables = list(getattr(ds, "tables_json", None) or [])
            except Exception:
                tables = []
            if not tables and ds.table_name:
                tables = [{"table_name": ds.table_name}]
            for t in tables[:5]:
                tname = t["table_name"] if isinstance(t, dict) else str(t)
                try:
                    cols = get_table_schema(ds, tname) or []
                except Exception:
                    cols = []
                col_lines = "\n".join(
                    f"  - {c.get('name')} ({c.get('type','?')}){' PK' if c.get('is_pk') else ''}: {c.get('comment') or ''}"
                    for c in cols[:30]
                )
                ds_blocks.append(f"### 数据源 {ds.name} · 表 {tname}\n{col_lines}")

        # 2. 拼文档正文
        doc_blocks: list[str] = []
        for did in doc_ids:
            d = self.db.get(BusinessDocument, did)
            if not d:
                continue
            doc_blocks.append(f"### 文档 {d.name}\n{(d.parsed_text or '')[:6000]}")

        prompt = """你是本体建模专家，要从用户提供的数据源 schema + 业务文档中抽取本体草稿。
术语规范：对象（Object）/ 属性（Property）/ 关系（Relation）/ 规则（Rule）/ 动作（Action）。

严格返回 JSON：
{
  "entities": [{"name":"PascalCase","display_name":"中文","tier":1|2|3,"description":"...","primary_key":"id","icon":"emoji","properties":[{"name":"snake_case","display_name":"中文","type":"string|number|date|boolean|enum","required":true|false,"description":"..."}]}],
  "relations": [{"name":"snake_case","display_name":"中文","from_entity":"对象英文名","to_entity":"对象英文名","cardinality":"1:1|1:N|N:N","description":"..."}],
  "suggested_rules": [{"name":"中文","description":"...","condition_hint":"...","action_hint":"...","target_entity":"对象英文名"}],
  "suggested_actions": [{"name":"中文","description":"...","trigger_hint":"...","effect_hint":"...","target_entity":"对象英文名"}]
}
不要输出其他文字。
"""
        user_content = (
            f"## 业务上下文\n{ctx or '（无）'}\n\n"
            f"## 数据源 Schema\n" + ("\n\n".join(ds_blocks) or "（无）") + "\n\n"
            f"## 业务文档\n" + ("\n\n".join(doc_blocks) or "（无）")
        )[:18000]

        client = get_llm_client()
        try:
            resp = client.chat.completions.create(
                model=_settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                max_tokens=6000,
                timeout=120,
            )
        except Exception as e:
            return {"error": f"LLM 调用失败: {e}"}, f"LLM 调用失败", 0

        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = _re.sub(r"^```\w*\n", "", text)
            text = _re.sub(r"\n```\s*$", "", text)
        try:
            data = _json.loads(text)
        except _json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < 0:
                return {"error": "LLM 返回不是合法 JSON"}, "解析失败", 0
            data = _json.loads(text[start: end + 1])

        ents = data.get("entities", []) or []
        rels = data.get("relations", []) or []
        s_rules = data.get("suggested_rules", []) or []
        s_actions = data.get("suggested_actions", []) or []
        result = {
            "entities": ents,
            "relations": rels,
            "suggested_rules": s_rules,
            "suggested_actions": s_actions,
        }
        summary = f"产出 {len(ents)} 对象 / {len(rels)} 关系 / {len(s_rules)} 规则建议 / {len(s_actions)} 动作建议"
        return result, summary, len(ents)
