"""
Agent 服务 — 智能问答核心编排
LLM 规划工具调用 → 执行工具 → 收集推理链 → 返回答案
"""
import json
import logging
from typing import Any, Generator

from sqlalchemy.orm import Session

from app.config import settings
from app.models import OntologyEntity, EntityRelation, BusinessRule, DataSource
from app.services.agent_tools import agent_tool_definitions, agent_tool_catalog
from app.services.copilot import get_llm_client, build_ontology_context
from app.services.datasource_utils import (
    get_table_schema as ds_get_table_schema,
    execute_readonly_sql,
)
from app.services.rule_engine import RuleEvaluator, ActionExecutor, RuleScreener

logger = logging.getLogger(__name__)


class AgentService:
    MAX_TOOL_ROUNDS = 8

    def __init__(self, db: Session):
        self.db = db
        self.client = get_llm_client()

    # ── public ──────────────────────────────────────────────

    def ask(self, question: str, entity_id: str | None = None) -> Generator[dict, None, None]:
        """Agent 循环，yield SSE 事件字典"""
        question = question.strip()
        if not question:
            yield {"type": "answer", "content": "请输入您的问题。", "suggestions": []}
            return

        system_prompt = self._build_system_prompt(entity_id)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        tool_runs: list[dict[str, Any]] = []

        for _round in range(self.MAX_TOOL_ROUNDS):
            try:
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    tools=agent_tool_definitions(),
                    tool_choice="auto",
                    temperature=0,
                    max_tokens=4096,
                )
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                yield {"type": "answer", "content": f"AI 服务调用失败: {e}", "suggestions": []}
                return

            choice = response.choices[0]
            assistant_msg = choice.message

            # 没有工具调用 → 流式输出最终回答
            if not assistant_msg.tool_calls:
                content = assistant_msg.content or ""
                answer, suggestions, actions = self._parse_final_answer(content)
                # 先发送推理链汇总
                if tool_runs:
                    yield {"type": "tool_summary", "toolRuns": tool_runs}
                # 流式逐段发送 answer 内容
                chunk_size = 20
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "content", "content": answer[i:i + chunk_size]}
                # 发送完成信号、建议和动作
                yield {"type": "done", "suggestions": suggestions, "actions": actions}
                return

            # 有工具调用 → 逐个执行
            messages.append(self._serialize_assistant_message(assistant_msg))

            for tool_call in assistant_msg.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                yield {"type": "tool_start", "tool": tool_name, "arguments": tool_args}

                result, summary, result_count = self._execute_tool(tool_name, tool_args)

                # 提取本体上下文详情
                detail = self._extract_tool_detail(tool_name, tool_args, result)

                tool_runs.append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "summary": summary,
                    "resultCount": result_count,
                })

                yield {
                    "type": "tool_result",
                    "tool": tool_name,
                    "summary": summary,
                    "resultCount": result_count,
                    "detail": detail,
                }

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # 超过最大轮次
        yield {"type": "content", "content": "抱歉，推理轮次已达上限，请尝试简化问题。"}
        yield {"type": "done", "suggestions": []}

    # ── system prompt ───────────────────────────────────────

    def _build_system_prompt(self, entity_id: str | None) -> str:
        ontology_ctx = build_ontology_context(self.db, entity_id)
        tool_catalog = json.dumps(agent_tool_catalog(), ensure_ascii=False)

        # 构建数据源摘要
        datasources = self.db.query(DataSource).filter(DataSource.enabled == True).all()
        ds_lines = []
        for ds in datasources:
            ds_lines.append(f"- {ds.name} (类型: {ds.type}, 表: {ds.table_name}, 记录数: {ds.record_count})")
        ds_summary = "\n".join(ds_lines) if ds_lines else "暂无已启用的数据源"

        return (
            "你是本体驱动的智能问答助手。你必须严格基于本体模型进行推理和回答。\n"
            "\n"
            "## 核心原则（必须遵守）\n"
            "\n"
            "1. **规则优先**：任何涉及判断、评估、筛选、风险、预警的问题，第一步必须先找规则（get_business_rules），理解规则定义了什么条件\n"
            "2. **规则驱动数据查询**：需要查数据时，不要自己写 SQL。根据规则条件中引用的实体和字段，使用 screen_users_by_rule（批量筛选）或 query_entity_data（通过本体查数据）\n"
            "3. **禁止绕过本体**：不要直接用 query_datasource 写 SQL 查询，除非 query_entity_data 和 screen_users_by_rule 都无法满足需求\n"
            "4. **输出可执行动作**：当推理结果需要后续操作时（如触发维系策略、发送通知等），必须在回答中输出对应的动作\n"
            "5. **不要凭空编造数据**，所有数据必须通过工具查询获取\n"
            "\n"
            "## 推理流程（严格按此顺序）\n"
            "\n"
            "### 场景A：批量筛选类问题（如'有哪些高风险用户？'）\n"
            "```\n"
            "Step 1: 找规则 → get_business_rules 找到相关规则（如'高风险携转预警规则'）\n"
            "Step 2: 规则驱动筛选 → screen_users_by_rule 根据规则条件自动查数据源，返回命中用户\n"
            "Step 3: 输出结果 + 动作按钮（如'对这些用户触发维系策略'）\n"
            "```\n"
            "\n"
            "### 场景B：单用户评估类问题（如'张三有风险吗？'）\n"
            "```\n"
            "Step 1: 找规则 → get_business_rules 找到相关规则\n"
            "Step 2: 查用户数据 → query_entity_data 通过本体实体查用户信息\n"
            "Step 3: 规则评估 → evaluate_all_rules 用本体规则评估该用户\n"
            "Step 4: 输出结果 + 动作按钮\n"
            "```\n"
            "\n"
            "### 场景C：数据查询类问题（如'查看用户信息'）\n"
            "```\n"
            "Step 1: 本体理解 → get_entity_detail 找到相关实体和属性\n"
            "Step 2: 通过本体查数据 → query_entity_data\n"
            "Step 3: 输出结果\n"
            "```\n"
            "\n"
            "## 回答格式\n"
            "\n"
            "最终回答必须输出 JSON 对象：\n"
            '{"answer": "中文回答（markdown格式）", "suggestions": ["建议问题1", "建议问题2"], '
            '"actions": [{"name": "动作显示名", "action_name": "动作英文名或中文名", "params": {"参数名": "参数值"}, "description": "动作说明"}]}\n'
            "\n"
            "- answer: 包含推理过程和结论，引用具体的本体实体名、规则名、属性名\n"
            "- actions: 当推理结果需要后续操作时必须输出。如果没有需要执行的动作则为空数组\n"
            "- 回答要简洁，不超过 500 字\n"
            "\n"
            f"## 已启用的数据源\n{ds_summary}\n"
            "\n"
            f"## 工具目录\n{tool_catalog}\n"
            "\n"
            f"{ontology_ctx}"
        )

    # ── message serialization ───────────────────────────────

    @staticmethod
    def _serialize_assistant_message(msg) -> dict[str, Any]:
        """将 OpenAI SDK 的 assistant message 序列化为 dict"""
        result: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return result

    # ── final answer parsing ────────────────────────────────

    @staticmethod
    def _parse_final_answer(content: str) -> tuple[str, list[str], list[dict]]:
        """从 LLM 最终输出中解析 answer、suggestions 和 actions"""
        raw = content.strip()
        # 尝试提取 JSON
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 3:
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                answer = str(parsed.get("answer", content))
                suggestions = parsed.get("suggestions", [])
                if isinstance(suggestions, list):
                    suggestions = [str(s) for s in suggestions[:3]]
                else:
                    suggestions = []
                actions = parsed.get("actions", [])
                if isinstance(actions, list):
                    actions = [a for a in actions if isinstance(a, dict)]
                else:
                    actions = []
                return answer, suggestions, actions
        except json.JSONDecodeError:
            pass
        return content, [], []

    # ── tool execution ──────────────────────────────────────

    def _extract_tool_detail(self, tool_name: str, args: dict, result: Any) -> dict | None:
        """从工具执行结果中提取本体上下文详情，用于前端推理链展示"""
        try:
            if tool_name == "get_business_rules":
                if isinstance(result, list):
                    rules = []
                    for r in result:
                        rules.append({
                            "name": r.get("name", ""),
                            "has_conditions": r.get("has_structured_conditions", False),
                            "entity": r.get("entity", ""),
                        })
                    return {"type": "rules", "rules": rules}

            elif tool_name == "screen_users_by_rule":
                if isinstance(result, dict) and not result.get("error"):
                    # 收集涉及的实体和数据源
                    rule_name = args.get("rule_name", "")
                    rule = self.db.query(BusinessRule).filter(BusinessRule.name == rule_name).first()
                    entities_involved = []
                    if rule and rule.conditions_json:
                        seen = set()
                        for cond in rule.conditions_json:
                            field = cond.get("field", "")
                            if "." in field:
                                ename = field.split(".")[0]
                                if ename not in seen:
                                    seen.add(ename)
                                    entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == ename).first()
                                    if entity:
                                        ds_ref = (entity.schema_json or {}).get("datasource_ref", "")
                                        entities_involved.append({
                                            "entity": ename,
                                            "entity_cn": entity.name_cn,
                                            "datasource": ds_ref,
                                        })
                    return {
                        "type": "screen",
                        "rule_name": result.get("rule_name", ""),
                        "risk_level": result.get("risk_level", ""),
                        "match_mode": result.get("match_mode", ""),
                        "conditions_count": result.get("conditions_count", 0),
                        "matched_users": result.get("matched_users", 0),
                        "entities_involved": entities_involved,
                        "conditions": [c.get("display", "") for c in (rule.conditions_json or [])] if rule else [],
                    }

            elif tool_name == "evaluate_all_rules":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "evaluate",
                        "user_id": result.get("user_id", ""),
                        "overall_risk": result.get("overall_risk", ""),
                        "triggered_count": result.get("triggered_count", 0),
                        "evaluated_count": result.get("evaluated_count", 0),
                    }

            elif tool_name == "evaluate_rule":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "evaluate_single",
                        "rule_name": result.get("rule_name", ""),
                        "triggered": result.get("triggered", False),
                        "matched_count": result.get("matched_count", 0),
                        "total_count": result.get("total_count", 0),
                        "risk_level": result.get("risk_level", ""),
                    }

            elif tool_name == "query_entity_data":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "entity_query",
                        "entity": result.get("entity", ""),
                        "entity_cn": result.get("entity_cn", ""),
                        "datasource": result.get("datasource", ""),
                        "table": result.get("table", ""),
                        "row_count": result.get("rowCount", 0),
                    }

            elif tool_name == "execute_action":
                if isinstance(result, dict):
                    return {
                        "type": "action",
                        "action_name": result.get("action_name", ""),
                        "success": result.get("success", False),
                        "effects": result.get("effects", []),
                    }

            elif tool_name == "get_entity_detail":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "entity_detail",
                        "entity": result.get("name", ""),
                        "entity_cn": result.get("name_cn", ""),
                        "attr_count": len(result.get("attributes", [])),
                        "relation_count": len(result.get("relations", [])),
                        "rule_count": len(result.get("rules", [])),
                    }

        except Exception:
            pass
        return None

    def _execute_tool(self, tool_name: str, args: dict) -> tuple[Any, str, int]:
        """执行工具，返回 (result, summary, resultCount)"""
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

    # ── tool handlers ───────────────────────────────────────

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
                "description": e.description or "",
                "attributes": attrs,
            })

        relation_list = []
        for r in relations:
            from_e = next((e for e in entities if e.id == r.from_entity_id), None)
            to_e = next((e for e in entities if e.id == r.to_entity_id), None)
            if from_e and to_e:
                relation_list.append({
                    "from": from_e.name, "to": to_e.name,
                    "name": r.name, "cardinality": r.cardinality,
                })

        rule_list = [{"name": r.name, "condition": r.condition_expr, "action": r.action_desc} for r in rules[:20]]

        result = {"entities": entity_list, "relations": relation_list, "rules": rule_list}
        return result, f"返回 {len(entity_list)} 个实体、{len(relation_list)} 个关系、{len(rule_list)} 条规则", len(entity_list)

    def _tool_list_datasources(self, args: dict) -> tuple[Any, str, int]:
        datasources = self.db.query(DataSource).filter(DataSource.enabled == True).all()
        ds_list = [{
            "name": ds.name, "type": ds.type, "host": ds.host,
            "database": ds.database, "table_name": ds.table_name,
            "record_count": ds.record_count,
        } for ds in datasources]
        return ds_list, f"返回 {len(ds_list)} 个已启用数据源", len(ds_list)

    def _tool_get_table_schema(self, args: dict) -> tuple[Any, str, int]:
        ds_name = str(args.get("datasource_name", "")).strip()
        ds = self.db.query(DataSource).filter(DataSource.name == ds_name).first()
        if not ds:
            return {"error": f"数据源 '{ds_name}' 不存在"}, f"数据源不存在", 0
        if not ds.enabled:
            return {"error": f"数据源 '{ds_name}' 未启用"}, f"数据源未启用", 0
        columns = ds_get_table_schema(ds, ds.table_name)
        return {"table": ds.table_name, "columns": columns}, f"返回 {len(columns)} 个列定义", len(columns)

    def _tool_query_datasource(self, args: dict) -> tuple[Any, str, int]:
        ds_name = str(args.get("datasource_name", "")).strip()
        sql = str(args.get("sql", "")).strip()
        limit = int(args.get("limit", 50))
        ds = self.db.query(DataSource).filter(DataSource.name == ds_name).first()
        if not ds:
            return {"error": f"数据源 '{ds_name}' 不存在"}, f"数据源不存在", 0
        if not ds.enabled:
            return {"error": f"数据源 '{ds_name}' 未启用"}, f"数据源未启用", 0
        result = execute_readonly_sql(ds, sql, limit)
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0
        return result, f"返回 {result['rowCount']} 条记录", result["rowCount"]

    def _tool_get_entity_detail(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"实体 '{entity_name}' 不存在"}, f"实体不存在", 0
        attrs = [{"name": a.name, "type": a.type, "description": a.description, "required": a.required} for a in entity.attributes]
        # 查关系
        rels_from = self.db.query(EntityRelation).filter(EntityRelation.from_entity_id == entity.id).all()
        rels_to = self.db.query(EntityRelation).filter(EntityRelation.to_entity_id == entity.id).all()
        all_entities = {e.id: e.name for e in self.db.query(OntologyEntity).all()}
        relations = []
        for r in rels_from:
            relations.append({"direction": "out", "name": r.name, "target": all_entities.get(r.to_entity_id, "?"), "cardinality": r.cardinality})
        for r in rels_to:
            relations.append({"direction": "in", "name": r.name, "source": all_entities.get(r.from_entity_id, "?"), "cardinality": r.cardinality})
        # 查规则
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

        # 1. 通过本体找到实体
        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"本体中不存在实体 '{entity_name}'"}, "实体不存在", 0

        # 2. 通过实体的 schema_json 找到数据源
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

        # 3. 构建 SQL — 基于本体属性，不是手写
        valid_attrs = {a.name for a in entity.attributes}
        select_cols = "*"
        if fields:
            valid_fields = [f for f in fields if f in valid_attrs]
            if valid_fields:
                select_cols = ", ".join(valid_fields)

        sql = f"SELECT {select_cols} FROM {ds.table_name}"

        # 4. 基于本体属性构建 WHERE 条件
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

        # 5. 执行查询
        result = execute_readonly_sql(ds, sql, limit)
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0

        # 6. 返回结果，附带本体元信息
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
