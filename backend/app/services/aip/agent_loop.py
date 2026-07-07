"""
AIP Agent 节点执行器 — 本体驱动的 ReAct Loop

Agent 节点在流程编排中的执行逻辑：
1. 从节点配置读取绑定的本体对象类型 + 挂载的 Skill/Tool
2. 自动将本体中对应的规则/函数/动作 + 手动挂载的 Skill/Tool 注册为 LLM function-calling tools
3. 构建本体上下文（实体描述 + 关系 + 实例数据）
4. 启动 ReAct loop：LLM 推理 → 选 Tool → 执行 → 观察结果 → 循环直到 LLM 认为完成
5. yield 每轮的 SSE 事件（供前端追溯展示）
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config import settings
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.function import OntologyFunction
from app.models.action import EntityAction
from app.models.skill import Skill
from app.services.agent.tool_router import ToolRouter
from app.services.copilot import get_llm_client
from app.services.skill_executor import execute_skill

logger = logging.getLogger(__name__)

MAX_ROUNDS_DEFAULT = 5
MAX_ROUNDS_HARD_LIMIT = 12


class AgentNodeRunner:
    """本体驱动的 Agent 节点执行器。"""

    def __init__(
        self,
        db: Session,
        node_data: dict,
        upstream_context: dict,
        model_name: str | None = None,
        model_config: dict | None = None,
    ):
        self.db = db
        self.node_data = node_data
        self.upstream_context = upstream_context
        self.model_name = model_name or settings.LLM_MODEL
        self.model_config = model_config or {}
        self._client = get_llm_client(
            api_key=self.model_config.get("api_key"),
            api_base=self.model_config.get("api_base"),
        )
        self._tool_router = ToolRouter(db)

        self.max_rounds = min(
            node_data.get("max_rounds", MAX_ROUNDS_DEFAULT),
            MAX_ROUNDS_HARD_LIMIT,
        )
        self.entity_types: list[str] = node_data.get("objectTypes", [])
        self.skill_ids: list[str] = node_data.get("skill_ids", [])
        self.tool_ids: list[str] = node_data.get("tool_ids", [])
        self.system_prompt = node_data.get("system_prompt", "")
        self.agent_role = node_data.get("agentRole", "")

        self.tools_schema: list[dict] = []
        self._tool_dispatch: dict[str, callable] = {}
        self._build_tools()

    def _build_tools(self):
        """从本体 + 挂载的 Skill/Tool 构建 function-calling tools."""
        # 1. 本体驱动：为绑定的对象类型注册规则/函数/动作
        for entity_name in self.entity_types:
            entity = (
                self.db.query(OntologyEntity)
                .filter(OntologyEntity.name == entity_name)
                .first()
            )
            if not entity:
                continue
            self._register_entity_tools(entity)

        # 2. 挂载的 Skill
        for sid in self.skill_ids:
            skill = self.db.get(Skill, sid)
            if skill:
                self._register_skill_tool(skill)

        # 3. 通用本体查询工具
        self._register_builtin_tools()

    def _register_entity_tools(self, entity: OntologyEntity):
        """将实体下的函数/动作注册为 Tool。"""
        # 函数
        functions = self.db.query(OntologyFunction).filter(
            OntologyFunction.entity_id == entity.id
        ).all()
        for func in functions:
            tool_name = f"compute_{func.name}"
            self.tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"计算函数「{func.name}」: {func.description or ''}",
                    "parameters": func.input_schema or {"type": "object", "properties": {}},
                },
            })
            self._tool_dispatch[tool_name] = lambda params, _f=func: self._exec_function(_f, params)

        # 动作
        actions = self.db.query(EntityAction).filter(
            EntityAction.entity_id == entity.id
        ).all()
        for act in actions:
            tool_name = f"action_{act.name}"
            self.tools_schema.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"执行动作「{act.name}」: {act.description or ''}",
                    "parameters": {
                        "type": "object",
                        "properties": {p.get("name", "param"): {"type": "string", "description": p.get("description", "")} for p in (act.parameters_json or [])},
                    },
                },
            })
            self._tool_dispatch[tool_name] = lambda params, _a=act: self._exec_action(_a, params)

    def _register_skill_tool(self, skill: Skill):
        """将 Skill 注册为 Tool。"""
        tool_name = f"skill_{skill.code_ref}"
        params_schema = {"type": "object", "properties": {}, "required": []}
        if skill.config_json and skill.config_json.get("params"):
            for p in skill.config_json["params"]:
                params_schema["properties"][p["name"]] = {
                    "type": p.get("type", "string"),
                    "description": p.get("description", ""),
                }
                if p.get("required"):
                    params_schema["required"].append(p["name"])

        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"技能「{skill.name}」: {skill.description or ''}",
                "parameters": params_schema,
            },
        })
        self._tool_dispatch[tool_name] = lambda params, _s=skill: self._exec_skill(_s, params)

    def _register_builtin_tools(self):
        """注册通用内置工具。"""
        self.tools_schema.append({
            "type": "function",
            "function": {
                "name": "query_ontology_data",
                "description": "查询本体对象的实例数据",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_name": {"type": "string", "description": "本体对象名称"},
                        "filters": {"type": "string", "description": "过滤条件 JSON"},
                    },
                    "required": ["entity_name"],
                },
            },
        })
        self._tool_dispatch["query_ontology_data"] = self._exec_query_ontology

    # ─── Tool 执行器 ─────────────────────────────────────────

    def _exec_function(self, func: OntologyFunction, params: dict) -> dict:
        try:
            if func.logic_type == "expression" and func.logic_body:
                safe_globals = {"__builtins__": {}, "params": params}
                value = eval(func.logic_body, safe_globals)
                return {"value": value, "function": func.name}
            return {"error": f"未支持的逻辑类型 {func.logic_type}"}
        except Exception as e:
            return {"error": str(e)}

    def _exec_action(self, action: EntityAction, params: dict) -> dict:
        from app.services.action_executors import run_executor_sync
        try:
            res = run_executor_sync(action.action_type, action.type_config or {}, params, dry_run=False)
            return {"success": res.success, "message": res.message, "effects": res.output or {}}
        except Exception as e:
            return {"error": str(e)}

    def _exec_skill(self, skill: Skill, params: dict) -> dict:
        result = execute_skill(skill.code_ref, params, self.db)
        return result.get("data", result)

    def _exec_query_ontology(self, params: dict) -> dict:
        entity_name = params.get("entity_name", "")
        filters = params.get("filters", "")
        if filters and isinstance(filters, str):
            try:
                filters = json.loads(filters)
            except Exception:
                filters = {}
        result, _, _ = self._tool_router.execute("query_entity_data", {
            "entity_name": entity_name,
            **({"filters": filters} if filters else {}),
        })
        return result if isinstance(result, dict) else {"result": result}

    # ─── ReAct Loop ──────────────────────────────────────────

    def run(self, input_data: dict) -> Generator[dict, None, None]:
        """执行 ReAct loop，yield 每轮的事件。"""
        messages = self._build_initial_messages(input_data)

        for round_num in range(1, self.max_rounds + 1):
            round_start = time.time()

            yield {
                "type": "agent_round_start",
                "round": round_num,
                "max_rounds": self.max_rounds,
            }

            try:
                resp = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=self.tools_schema if self.tools_schema else None,
                    tool_choice="auto" if self.tools_schema else None,
                    temperature=self.model_config.get("temperature", 0.3),
                    max_tokens=self.model_config.get("max_tokens", 2048),
                )
            except Exception as e:
                yield {"type": "agent_error", "round": round_num, "error": str(e)}
                return

            choice = resp.choices[0]
            msg = choice.message

            # LLM 决定不再调用工具 → 结束
            if not msg.tool_calls:
                final_content = msg.content or ""
                yield {
                    "type": "agent_round_end",
                    "round": round_num,
                    "thought": final_content,
                    "tool_call": None,
                    "observation": None,
                    "duration_ms": int((time.time() - round_start) * 1000),
                    "is_final": True,
                }
                yield {
                    "type": "agent_finished",
                    "answer": final_content,
                    "total_rounds": round_num,
                }
                return

            # 有 tool_calls → 逐个执行
            messages.append(msg.model_dump())
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    fn_args = {}

                handler = self._tool_dispatch.get(fn_name)
                if handler:
                    try:
                        observation = handler(fn_args)
                    except Exception as e:
                        observation = {"error": str(e)}
                else:
                    observation = {"error": f"未知工具 {fn_name}"}

                obs_str = json.dumps(observation, ensure_ascii=False, default=str)[:3000]
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": obs_str,
                })

                yield {
                    "type": "agent_round_end",
                    "round": round_num,
                    "thought": msg.content or "",
                    "tool_call": {"name": fn_name, "arguments": fn_args},
                    "observation": observation,
                    "duration_ms": int((time.time() - round_start) * 1000),
                    "is_final": False,
                }

        # 超过最大轮次
        yield {
            "type": "agent_finished",
            "answer": "Agent 达到最大推理轮次限制，返回当前结果。",
            "total_rounds": self.max_rounds,
        }

    def _build_initial_messages(self, input_data: dict) -> list[dict]:
        """构建初始 messages。"""
        system_parts = []
        if self.system_prompt:
            system_parts.append(self.system_prompt)
        if self.agent_role:
            system_parts.append(f"你的角色: {self.agent_role}")

        # 本体上下文
        entity_desc = self._build_entity_context()
        if entity_desc:
            system_parts.append(f"你可以操作以下本体对象:\n{entity_desc}")

        system_parts.append(
            "你是一个本体驱动的智能分析 Agent。根据输入数据和可用工具，"
            "逐步推理并调用工具来完成任务。当你已经获得足够信息时，直接输出最终结论。"
        )

        messages = [{"role": "system", "content": "\n\n".join(system_parts)}]

        # 用户消息：上游传入的数据
        user_content = json.dumps(input_data, ensure_ascii=False, default=str)[:4000]
        messages.append({"role": "user", "content": f"请基于以下输入数据完成分析:\n\n{user_content}"})

        return messages

    def _build_entity_context(self) -> str:
        """构建本体对象的描述上下文。"""
        parts = []
        for entity_name in self.entity_types:
            entity = (
                self.db.query(OntologyEntity)
                .filter(OntologyEntity.name == entity_name)
                .first()
            )
            if not entity:
                continue
            attrs = self.db.query(EntityAttribute).filter(
                EntityAttribute.entity_id == entity.id
            ).all()
            attr_list = ", ".join(f"{a.name}({a.attr_type})" for a in attrs[:15])
            parts.append(f"- {entity.name}({entity.name_cn or ''}): {entity.description or ''} | 属性: {attr_list}")
        return "\n".join(parts)
