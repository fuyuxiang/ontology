"""
Agent 服务 — 智能问答核心编排
LLM 规划工具调用 → 执行工具 → 收集推理链 → 返回答案
"""
import json
import logging
from typing import Any, Generator

from sqlalchemy.orm import Session

from app.config import settings
from app.models import OntologyEntity, BusinessRule
from app.services.agent_tools import agent_tool_definitions, AGENT_TOOL_SPECS
from app.services.copilot import get_llm_client
from app.services.agent.prompt_builder import build_system_prompt
from app.services.agent.tool_router import ToolRouter

logger = logging.getLogger(__name__)


class AgentService:
    MAX_TOOL_ROUNDS = 8

    def __init__(
        self,
        db: Session,
        system_prompt_prefix: str | None = None,
        model_name: str | None = None,
        model_config: dict | None = None,
    ):
        self.db = db
        self._system_prompt_prefix = system_prompt_prefix
        self._model_name = model_name or settings.LLM_MODEL
        self._model_config = model_config or {}
        self.client = get_llm_client(
            api_key=self._model_config.get("api_key"),
            api_base=self._model_config.get("api_base"),
        )
        self._tool_router = ToolRouter(db)

    # ── public ──────────────────────────────────────────────

    def ask(self, question: str, entity_id: str | None = None) -> Generator[dict, None, None]:
        """Agent 循环，yield SSE 事件字典"""
        question = question.strip()
        if not question:
            yield {"type": "answer", "content": "请输入您的问题。", "suggestions": []}
            return

        system_prompt = build_system_prompt(self.db, entity_id, None)
        if self._system_prompt_prefix:
            system_prompt = self._system_prompt_prefix + "\n\n" + system_prompt
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        tool_runs: list[dict[str, Any]] = []
        tool_defs = agent_tool_definitions()

        temperature = self._model_config.get("temperature", 0)

        for _round in range(self.MAX_TOOL_ROUNDS):
            try:
                response = self.client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    tools=tool_defs,
                    tool_choice="auto",
                    temperature=temperature,
                    max_tokens=self._model_config.get("max_tokens", 4096),
                )
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                yield {"type": "answer", "content": f"AI 服务调用失败: {e}", "suggestions": []}
                return

            choice = response.choices[0]
            assistant_msg = choice.message

            if not assistant_msg.tool_calls:
                content = assistant_msg.content or ""
                answer, suggestions, actions = self._parse_final_answer(content)
                if tool_runs:
                    yield {"type": "tool_summary", "toolRuns": tool_runs}
                chunk_size = 20
                for i in range(0, len(answer), chunk_size):
                    yield {"type": "content", "content": answer[i:i + chunk_size]}
                yield {"type": "done", "suggestions": suggestions, "actions": actions}
                return

            messages.append(self._serialize_assistant_message(assistant_msg))

            for tool_call in assistant_msg.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_args = {}

                yield {"type": "tool_start", "tool": tool_name, "arguments": tool_args}

                result, summary, result_count = self._tool_router.execute(tool_name, tool_args)
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

        yield {"type": "content", "content": "抱歉，推理轮次已达上限，请尝试简化问题。"}
        yield {"type": "done", "suggestions": []}

    # ── helpers ─────────────────────────────────────────────

    @staticmethod
    def _serialize_assistant_message(msg: Any) -> dict[str, Any]:
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

    @staticmethod
    def _parse_final_answer(content: str) -> tuple[str, list[str], list[dict]]:
        raw = content.strip()
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

    def _extract_tool_detail(self, tool_name: str, args: dict, result: Any) -> dict | None:
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
