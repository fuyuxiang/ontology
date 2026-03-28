"""
模块功能：
- 监督式单 agent，使用 LLM 规划并通过工具执行后端能力。
- 该文件位于 `backend/app/agent/service.py`，承载当前目录对应的核心服务编排逻辑，向 API、CLI 或其他模块暴露稳定调用入口。
- 文件中定义的核心类包括：`PlannerClient`, `SupervisorAgentService`。
"""

from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from app.agent.llm_client import LLMPlannerClient
from app.agent_tools import agent_tool_definitions
from app.services.semantic_service import SemanticService


class PlannerClient(Protocol):
    """
    功能：
    - Protocol for an injected planner client。
    - 该类定义在 `backend/app/agent/service.py` 中，用于组织与 `PlannerClient` 相关的数据或行为。
    """

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """
        功能：
        - Return one assistant message。

        输入：
        - `messages`: 发送给 LLM 的对话消息历史。
        - `tools`: 列表参数 `tools`，用于批量传入待处理的数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """


class SupervisorAgentService:
    """
    功能：
    - 使用 LLM 规划工具调用，再由稳定工具层执行。
    - 该类定义在 `backend/app/agent/service.py` 中，用于组织与 `SupervisorAgentService` 相关的数据或行为。
    """

    MAX_TOOL_ROUNDS = 8

    def __init__(self, service: SemanticService, planner: PlannerClient | None = None) -> None:
        """
        功能：
        - 初始化当前对象并准备后续调用所需的依赖、状态和缓存。

        输入：
        - `service`: 语义服务实例。
        - `planner`: LLM 规划客户端实现。

        输出：
        - 返回值: 无返回值；处理结果会通过更新对象状态、修改入参或其他副作用体现。
        """
        self.service = service
        self.planner = planner or LLMPlannerClient.from_settings(service.settings)

    def ask(
        self,
        question: str,
        *,
        actor_role: str = "ops_manager",
        actor_id: str = "agent-console",
        actor_area_id: str | None = None,
    ) -> dict[str, Any]:
        """
        功能：
        - 回答问题，并明确给出使用过的工具轨迹。

        输入：
        - `question`: 函数执行所需的 `question` 参数。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        prompt = question.strip()
        if not prompt:
            raise ValueError("question_required")

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": self._build_system_prompt(
                    actor_role=actor_role,
                    actor_id=actor_id,
                    actor_area_id=actor_area_id,
                ),
            },
            {"role": "user", "content": prompt},
        ]
        tool_runs: list[dict[str, Any]] = []
        collected_objects: list[dict[str, Any]] = []
        primary_object_type = "Summary"

        for _ in range(self.MAX_TOOL_ROUNDS):
            assistant_message = self._normalize_assistant_message(
                self.planner.complete(messages, tools=agent_tool_definitions())
            )
            messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls") or []
            if not tool_calls:
                final_payload = self._parse_final_payload(assistant_message.get("content"))
                return {
                    "mode": "supervised",
                    "question": prompt,
                    "answer": final_payload["answer"],
                    "toolRuns": tool_runs,
                    "suggestions": final_payload["suggestions"],
                    "primaryObjectType": final_payload["primaryObjectType"] or primary_object_type,
                    "objects": collected_objects,
                    "requiresConfirmation": final_payload["requiresConfirmation"],
                    "pendingAction": final_payload["pendingAction"],
                }

            for tool_call in tool_calls:
                tool_name, tool_args, tool_result = self._execute_tool_call(
                    tool_call,
                    tool_runs=tool_runs,
                    actor_role=actor_role,
                    actor_id=actor_id,
                    actor_area_id=actor_area_id,
                )
                new_objects, new_primary_type = self._extract_objects(
                    tool_name,
                    tool_args,
                    tool_result,
                    fallback_type=primary_object_type,
                )
                if new_objects:
                    collected_objects = new_objects
                primary_object_type = new_primary_type
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tool_call.get("id") or ""),
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )

        raise ValueError("llm_planning_exhausted")

    def _build_system_prompt(
        self,
        *,
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
    ) -> str:
        """
        功能：
        - 构建systemprompt。

        输入：
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        scenario = self.service.scenario
        object_model = self.service.describe_object_model()
        tool_catalog = self.service.describe_tool_catalog()
        open_case_count = int(self.service.operational_metrics.get("openCaseCount") or 0)
        return (
            "你是运营智能问答的规划器。你的职责是理解用户问题，选择合适的工具，"
            "并基于工具结果回答。不要凭空编造数据；如果没有工具结果支撑，就明确说明。"
            "\n"
            "你必须优先使用工具完成查询，不要用关键词分支或假设替代查询。"
            "\n"
            "只有当用户明确要求执行动作，且动作标识与对象标识已经足够时，才允许调用 execute_action。"
            "如果用户意图可能涉及动作但信息不够，或者需要再次确认，请不要执行动作，"
            "而是在最终 JSON 中把 requiresConfirmation 设为 true，并给出 pendingAction。"
            "\n"
            "最终答复必须只输出一个 JSON 对象，格式如下："
            '\n{"answer":"面向用户的简洁中文回答","primaryObjectType":"最相关对象类型","requiresConfirmation":false,'
            '"pendingAction":null,"suggestions":["最多三个后续问题建议"]}'
            "\n"
            "pendingAction 为 null 或对象："
            '\n{"actionId":"","actionLabel":"","caseId":"","entityId":"","actorRole":"","actorId":"","actorAreaId":""}'
            "\n"
            "如果已经执行了 execute_action，则 requiresConfirmation 必须为 false，pendingAction 必须为 null。"
            "\n"
            "场景上下文："
            f"\n{json.dumps({'scenario': scenario.name, 'scenarioKey': self.service.settings.scenario_key, 'primaryEntityLabel': scenario.primary_entity_label, 'openCaseCount': open_case_count}, ensure_ascii=False)}"
            "\n"
            f"对象模型：\n{json.dumps(object_model, ensure_ascii=False)}"
            "\n"
            f"工具目录：\n{json.dumps(tool_catalog, ensure_ascii=False)}"
            "\n"
            f"执行人上下文：\n{json.dumps({'actorRole': actor_role, 'actorId': actor_id, 'actorAreaId': actor_area_id or ''}, ensure_ascii=False)}"
        )

    def _normalize_assistant_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 规范化assistantmessage。

        输入：
        - `message`: 字典参数 `message`，承载键值形式的输入数据。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        content = self._normalize_content(message.get("content"))
        normalized: dict[str, Any] = {"role": "assistant", "content": content}
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            normalized["tool_calls"] = tool_calls
        return normalized

    def _normalize_content(self, content: Any) -> str:
        """
        功能：
        - 规范化content。

        输入：
        - `content`: 需要规范化、解析或回传的文本或结构化内容。

        输出：
        - 返回值: 返回字符串结果，供调用方继续展示、拼接或查询。
        """
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text)
            if chunks:
                return "\n".join(chunks)
        return json.dumps(content, ensure_ascii=False)

    def _execute_tool_call(
        self,
        tool_call: dict[str, Any],
        *,
        tool_runs: list[dict[str, Any]],
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
    ) -> tuple[str, dict[str, Any], Any]:
        """
        功能：
        - 执行工具call。

        输入：
        - `tool_call`: 单次工具调用描述对象。
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回元组结果，按既定顺序携带多个返回值。
        """
        function_payload = tool_call.get("function")
        if not isinstance(function_payload, dict):
            raise ValueError("llm_tool_call_missing_function")

        tool_name = str(function_payload.get("name") or "").strip()
        if not tool_name:
            raise ValueError("llm_tool_call_missing_name")

        tool_args = self._parse_tool_arguments(function_payload.get("arguments"))
        result = self._run_tool(
            tool_runs,
            tool_name,
            tool_args,
            actor_role=actor_role,
            actor_id=actor_id,
            actor_area_id=actor_area_id,
        )
        return tool_name, tool_args, result

    def _parse_tool_arguments(self, raw_arguments: Any) -> dict[str, Any]:
        """
        功能：
        - 解析工具arguments。

        输入：
        - `raw_arguments`: 尚未解析的参数原文。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        if raw_arguments is None or raw_arguments == "":
            return {}
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise ValueError("llm_tool_arguments_invalid_json") from exc
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("llm_tool_arguments_invalid")

    def _run_tool(
        self,
        tool_runs: list[dict[str, Any]],
        tool_name: str,
        arguments: dict[str, Any],
        *,
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
    ) -> Any:
        """
        功能：
        - 执行工具。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `tool_name`: 函数执行所需的 `tool_name` 参数。
        - `arguments`: 工具调用或函数执行参数。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回 `Any` 类型结果，供后续流程继续消费。
        """
        handlers = self._tool_handlers(
            tool_runs=tool_runs,
            actor_role=actor_role,
            actor_id=actor_id,
            actor_area_id=actor_area_id,
        )
        handler = handlers.get(tool_name)
        if handler is None:
            raise ValueError(f"unsupported_tool:{tool_name}")
        return handler(arguments)

    def _tool_handlers(
        self,
        *,
        tool_runs: list[dict[str, Any]],
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
    ) -> dict[str, Callable[[dict[str, Any]], Any]]:
        """
        功能：
        - 处理与 `_tool_handlers` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        return {
            "describe_object_model": lambda arguments: self._tool_describe_object_model(tool_runs, arguments),
            "query_objects": lambda arguments: self._tool_query_objects(tool_runs, arguments),
            "get_object": lambda arguments: self._tool_get_object(tool_runs, arguments),
            "run_semantic_query": lambda arguments: self._tool_run_semantic_query(tool_runs, arguments),
            "get_summary": lambda arguments: self._tool_get_summary(tool_runs, arguments),
            "execute_action": lambda arguments: self._tool_execute_action(
                tool_runs,
                arguments,
                actor_role=actor_role,
                actor_id=actor_id,
                actor_area_id=actor_area_id,
            ),
        }

    def _tool_describe_object_model(self, tool_runs: list[dict[str, Any]], arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """
        功能：
        - 处理与 `_tool_describe_object_model` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。

        输出：
        - 返回值: 返回列表结果，供调用方遍历、展示或继续筛选。
        """
        payload = self.service.describe_object_model()
        tool_runs.append(
            {
                "tool": "describe_object_model",
                "arguments": arguments,
                "summary": f"返回 {len(payload)} 个对象类型定义",
                "resultCount": len(payload),
            }
        )
        return payload

    def _tool_query_objects(self, tool_runs: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_tool_query_objects` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        object_type = str(arguments.get("object_type") or arguments.get("objectType") or "").strip()
        limit = int(arguments.get("limit") or 10)
        payload = self.service.query_objects(
            object_type,
            limit=limit,
            search=arguments.get("search"),
            filters=arguments.get("filters"),
        )
        tool_runs.append(
            {
                "tool": "query_objects",
                "arguments": {
                    "object_type": object_type,
                    "limit": limit,
                    "search": arguments.get("search"),
                    "filters": arguments.get("filters"),
                },
                "summary": f"返回 {payload['returned']}/{payload['total']} 个 {payload['objectType']} 对象",
                "resultCount": payload["returned"],
            }
        )
        return payload

    def _tool_get_object(self, tool_runs: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_tool_get_object` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        object_type = str(arguments.get("object_type") or arguments.get("objectType") or "").strip()
        object_id = str(arguments.get("object_id") or arguments.get("objectId") or "").strip()
        payload = self.service.get_object(object_type, object_id)
        tool_runs.append(
            {
                "tool": "get_object",
                "arguments": {"object_type": object_type, "object_id": object_id},
                "summary": "读取单对象详情",
                "resultCount": 0 if payload.get("error") else 1,
            }
        )
        return payload

    def _tool_run_semantic_query(self, tool_runs: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_tool_run_semantic_query` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        query = str(arguments.get("query") or "")
        payload = self.service.run_sparql(query)
        tool_runs.append(
            {
                "tool": "run_semantic_query",
                "arguments": {"query": "provided"},
                "summary": f"SPARQL 返回 {payload['rowCount']} 行",
                "resultCount": payload["rowCount"],
            }
        )
        return payload

    def _tool_get_summary(self, tool_runs: list[dict[str, Any]], arguments: dict[str, Any]) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_tool_get_summary` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        payload = self.service.get_summary()
        tool_runs.append(
            {
                "tool": "get_summary",
                "arguments": arguments,
                "summary": "读取概览指标",
                "resultCount": 1,
            }
        )
        return payload

    def _tool_execute_action(
        self,
        tool_runs: list[dict[str, Any]],
        arguments: dict[str, Any],
        *,
        actor_role: str,
        actor_id: str,
        actor_area_id: str | None,
    ) -> dict[str, Any]:
        """
        功能：
        - 处理与 `_tool_execute_action` 相关的逻辑。

        输入：
        - `tool_runs`: 工具执行轨迹列表，方法会向其中追加调用记录。
        - `arguments`: 工具调用或函数执行参数。
        - `actor_role`: 当前执行人的角色标识。
        - `actor_id`: 当前执行人的唯一标识。
        - `actor_area_id`: 当前执行人所属区域标识，可为空。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        action_id = str(arguments.get("action_id") or arguments.get("actionId") or "").strip()
        case_id = str(arguments.get("case_id") or arguments.get("caseId") or "").strip() or None
        entity_id = str(arguments.get("entity_id") or arguments.get("entityId") or "").strip() or None
        parameters = arguments.get("parameters")
        payload = self.service.execute_action(
            action_id=action_id,
            actor_role=actor_role,
            actor_id=actor_id,
            actor_area_id=actor_area_id,
            entity_id=entity_id,
            case_id=case_id,
            parameters=parameters if isinstance(parameters, dict) else None,
        )
        tool_runs.append(
            {
                "tool": "execute_action",
                "arguments": {
                    "action_id": action_id,
                    "case_id": case_id,
                    "entity_id": entity_id,
                    "parameters": parameters if isinstance(parameters, dict) else {},
                },
                "summary": f"执行动作 {action_id}",
                "resultCount": 1,
            }
        )
        return payload

    def _extract_objects(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_result: Any,
        *,
        fallback_type: str,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        功能：
        - 提取对象列表。

        输入：
        - `tool_name`: 函数执行所需的 `tool_name` 参数。
        - `tool_args`: 字典参数 `tool_args`，承载键值形式的输入数据。
        - `tool_result`: 函数执行所需的 `tool_result` 参数。
        - `fallback_type`: 函数执行所需的 `fallback_type` 参数。

        输出：
        - 返回值: 返回元组结果，按既定顺序携带多个返回值。
        """
        if tool_name == "query_objects" and isinstance(tool_result, dict):
            rows = tool_result.get("rows")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)], str(tool_result.get("objectType") or fallback_type)

        if tool_name == "get_object" and isinstance(tool_result, dict) and not tool_result.get("error"):
            object_type = str(tool_args.get("object_type") or tool_args.get("objectType") or fallback_type)
            return [tool_result], object_type

        if tool_name == "run_semantic_query" and isinstance(tool_result, dict):
            rows = tool_result.get("rows")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)], "SemanticQuery"

        if tool_name == "execute_action" and isinstance(tool_result, dict):
            case_payload = tool_result.get("case")
            if isinstance(case_payload, dict):
                return [case_payload], "RetentionCase"
            return [], "ActionExecution"

        return [], fallback_type

    def _parse_final_payload(self, content: str) -> dict[str, Any]:
        """
        功能：
        - 解析final返回载荷。

        输入：
        - `content`: 需要规范化、解析或回传的文本或结构化内容。

        输出：
        - 返回值: 返回字典结构，包含本次处理产生的结果数据。
        """
        suggestions = list(self.service.scenario.question_suggestions[:3])
        default_payload = {
            "answer": content.strip() or "未返回可解析答案。",
            "primaryObjectType": "Summary",
            "requiresConfirmation": False,
            "pendingAction": None,
            "suggestions": suggestions,
        }

        parsed = self._try_parse_json_object(content)
        if parsed is None:
            return default_payload

        answer = str(parsed.get("answer") or "").strip()
        if not answer:
            answer = default_payload["answer"]

        pending_action = parsed.get("pendingAction")
        if not isinstance(pending_action, dict):
            pending_action = None
        else:
            pending_action = {
                "actionId": str(pending_action.get("actionId") or ""),
                "actionLabel": str(pending_action.get("actionLabel") or ""),
                "caseId": str(pending_action.get("caseId") or ""),
                "entityId": str(pending_action.get("entityId") or ""),
                "actorRole": str(pending_action.get("actorRole") or ""),
                "actorId": str(pending_action.get("actorId") or ""),
                "actorAreaId": str(pending_action.get("actorAreaId") or ""),
            }

        raw_suggestions = parsed.get("suggestions")
        normalized_suggestions = [
            str(item).strip()
            for item in raw_suggestions
            if str(item).strip()
        ][:3] if isinstance(raw_suggestions, list) else suggestions

        return {
            "answer": answer,
            "primaryObjectType": str(parsed.get("primaryObjectType") or default_payload["primaryObjectType"]),
            "requiresConfirmation": bool(parsed.get("requiresConfirmation")),
            "pendingAction": pending_action,
            "suggestions": normalized_suggestions or suggestions,
        }

    def _try_parse_json_object(self, content: str) -> dict[str, Any] | None:
        """
        功能：
        - 处理与 `_try_parse_json_object` 相关的逻辑。

        输入：
        - `content`: 需要规范化、解析或回传的文本或结构化内容。

        输出：
        - 返回值: 返回处理结果；当目标不存在、未命中或无法解析时返回 `None`。
        """
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
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
