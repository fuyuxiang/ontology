"""
Agent 服务 — 智能问答核心编排
LLM 规划工具调用 → 执行工具 → 收集推理链 → 返回答案
"""
import json
import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import OntologyEntity
from app.services.agent.prompt_builder import build_system_prompt
from app.services.agent.tool_router import ToolRouter
from app.services.agent_tools import agent_tool_definitions
from app.services.copilot import get_llm_client
from app.services.data_plane.entity_data_service import EntityDataService

logger = logging.getLogger(__name__)


class AgentService:
    MAX_TOOL_ROUNDS = 12

    def __init__(
        self,
        db: Session,
        system_prompt_prefix: str | None = None,
        model_name: str | None = None,
        model_config: dict | None = None,
        runtime_executor=None,
    ):
        self.db = db
        self._system_prompt_prefix = system_prompt_prefix
        self._model_name = model_name or settings.LLM_MODEL
        self._model_config = model_config or {}
        self.client = get_llm_client(
            api_key=self._model_config.get("api_key"),
            api_base=self._model_config.get("api_base"),
        )
        self._tool_router = ToolRouter(db, runtime_executor=runtime_executor)

    # ── public ──────────────────────────────────────────────

    def ask(
        self,
        question: str,
        entity_id: str | None = None,
        history: list[dict] | None = None,
    ) -> Generator[dict, None, None]:
        """Agent 循环，yield SSE 事件字典"""
        question = question.strip()
        if not question:
            yield {"type": "answer", "content": "请输入您的问题。", "suggestions": []}
            return

        system_prompt = build_system_prompt(self.db, entity_id, None)
        if self._system_prompt_prefix:
            system_prompt = self._system_prompt_prefix + "\n\n" + system_prompt
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for h in history or []:
            role = h.get("role")
            content = h.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})
        tool_runs: list[dict[str, Any]] = []
        tool_defs = agent_tool_definitions()

        temperature = self._model_config.get("temperature", 0)

        # 强制出答案标志：最后一轮或检测到重复打转时置位，
        # 关闭工具调用逼模型基于已有工具结果给出最终回答
        force_answer = False
        prev_tool_signature: str | None = None
        repeat_count = 0

        for _round in range(self.MAX_TOOL_ROUNDS):
            # 最后一轮预留给强制作答，避免跑满后只能扔一句道歉、丢弃已查数据
            if _round == self.MAX_TOOL_ROUNDS - 1:
                force_answer = True
            try:
                stream = self.client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    tools=tool_defs,
                    tool_choice="none" if force_answer else "auto",
                    temperature=temperature,
                    max_tokens=self._model_config.get("max_tokens", 4096),
                    stream=True,
                )
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                yield {"type": "answer", "content": f"AI 服务调用失败: {e}", "suggestions": []}
                return

            # 累积本轮流式输出：正文 buffer + 工具调用 delta
            text_buffer = ""
            emitted_len = 0  # 已通过 content 事件吐出的 answer 字符数
            tool_calls_acc: dict[int, dict[str, Any]] = {}
            try:
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # 累积工具调用分片
                    if delta and delta.tool_calls:
                        for tc in delta.tool_calls:
                            slot = tool_calls_acc.setdefault(
                                tc.index, {"id": "", "name": "", "arguments": ""}
                            )
                            if tc.id:
                                slot["id"] = tc.id
                            if tc.function and tc.function.name:
                                slot["name"] = tc.function.name
                            if tc.function and tc.function.arguments:
                                slot["arguments"] += tc.function.arguments
                    # 累积正文，并增量提取 answer 字段流式吐出
                    if delta and delta.content:
                        text_buffer += delta.content
                        if not tool_calls_acc:
                            answer_so_far = self._extract_answer_prefix(text_buffer)
                            if answer_so_far is not None and len(answer_so_far) > emitted_len:
                                yield {"type": "content", "content": answer_so_far[emitted_len:]}
                                emitted_len = len(answer_so_far)
            except Exception as e:
                logger.error(f"LLM 流式读取失败: {e}")
                yield {"type": "answer", "content": f"AI 服务调用失败: {e}", "suggestions": []}
                return

            # 本轮无工具调用 → 最终回答
            if not tool_calls_acc:
                answer, suggestions, actions = self._parse_final_answer(text_buffer)
                if tool_runs:
                    yield {"type": "tool_summary", "toolRuns": tool_runs}
                # 增量提取已覆盖大部分正文；若解析后的 answer 与已吐出内容不一致则补齐尾部
                if len(answer) > emitted_len:
                    yield {"type": "content", "content": answer[emitted_len:]}
                elif emitted_len == 0 and answer:
                    yield {"type": "content", "content": answer}
                yield {"type": "done", "suggestions": suggestions, "actions": actions}
                return

            # 有工具调用 → 拼装 assistant 消息并执行工具
            ordered = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]

            # 打转检测：本轮工具调用（名称+参数）与上一轮完全相同则计数，
            # 连续重复达 2 次说明模型没在收敛，下一轮强制作答避免空耗预算
            tool_signature = "|".join(
                f"{tc['name']}:{tc['arguments']}" for tc in ordered
            )
            if tool_signature == prev_tool_signature:
                repeat_count += 1
            else:
                repeat_count = 0
            prev_tool_signature = tool_signature
            if repeat_count >= 2:
                force_answer = True

            messages.append({
                "role": "assistant",
                "content": text_buffer or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in ordered
                ],
            })

            for tc in ordered:
                tool_name = tc["name"]
                try:
                    tool_args = json.loads(tc["arguments"] or "{}")
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
                    "tool_call_id": tc["id"],
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
    def _strip_reasoning(raw: str) -> str:
        """剥离推理类模型在正文前输出的 <think>...</think> 思维块。

        部分模型（如 deepseek-r1 系）会先吐 <think> 推理再给出 JSON 答复。
        若思维块尚未闭合（流式中途），则丢弃 <think> 之后的全部内容，
        避免把推理过程误当成 answer。
        """
        s = raw.lstrip()
        if not s.startswith("<think>"):
            return raw
        end = s.find("</think>")
        if end == -1:
            return ""  # 思维块还没结束，正文尚未开始
        return s[end + len("</think>"):].lstrip()

    @staticmethod
    def _extract_answer_prefix(buffer: str) -> str | None:
        """从尚未结束的 LLM JSON 输出中，增量提取 answer 字段已生成的文本。

        LLM 被要求输出 {"answer": "...", "suggestions": [...], ...}。
        在流式过程中 buffer 是半截 JSON，这里解析出 answer 字符串值的当前部分，
        正确处理转义字符；若 answer 尚未开始则返回 None。
        """
        # 先剥离 <think> 思维块，规范化全角引号，再去掉 ```json 代码块围栏
        raw = AgentService._strip_reasoning(buffer).lstrip()
        raw = AgentService._normalize_json_quotes(raw)
        if raw.startswith("```"):
            nl = raw.find("\n")
            if nl != -1:
                raw = raw[nl + 1:]
        key_idx = raw.find('"answer"')
        if key_idx == -1:
            return None
        # 定位 answer 值起始的引号
        colon = raw.find(":", key_idx + len('"answer"'))
        if colon == -1:
            return None
        q = raw.find('"', colon + 1)
        if q == -1:
            return None
        out: list[str] = []
        i = q + 1
        n = len(raw)
        while i < n:
            ch = raw[i]
            if ch == "\\":
                if i + 1 >= n:
                    break  # 转义符还没传完，停在此处
                nxt = raw[i + 1]
                mapping = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}
                if nxt in mapping:
                    out.append(mapping[nxt])
                    i += 2
                    continue
                if nxt == "u":
                    if i + 6 > n:
                        break  # \uXXXX 还没传完
                    try:
                        out.append(chr(int(raw[i + 2:i + 6], 16)))
                    except ValueError:
                        pass
                    i += 6
                    continue
                out.append(nxt)
                i += 2
                continue
            if ch == '"':
                break  # answer 字符串结束
            out.append(ch)
            i += 1
        return "".join(out)

    @staticmethod
    def _normalize_json_quotes(s: str) -> str:
        """将模型偶发输出的全角/弯引号规范化为标准 JSON 引号。

        部分模型会把 JSON 结构引号写成中文全角引号（“ ” ‘ ’），
        导致 json.loads 失败。规范化后可重试解析。
        """
        return (
            s.replace("“", '"').replace("”", '"')
            .replace("‘", "'").replace("’", "'")
        )

    @staticmethod
    def _parse_final_answer(content: str) -> tuple[str, list[str], list[dict]]:
        # 先剥离 <think> 思维块，避免污染 answer
        cleaned = AgentService._strip_reasoning(content)
        raw = cleaned.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 3:
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
        # 先按标准 JSON 解析；失败则规范化全角引号后重试
        parsed = None
        for candidate in (raw, AgentService._normalize_json_quotes(raw)):
            try:
                parsed = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if isinstance(parsed, dict):
            answer = str(parsed.get("answer", cleaned))
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
        # 解析仍失败：宽松提取 answer 文本，避免把 JSON 结构泄漏到正文
        loose = AgentService._extract_answer_prefix(
            AgentService._normalize_json_quotes(content)
        )
        if loose:
            return loose, [], []
        return cleaned, [], []

    def _extract_tool_detail(self, tool_name: str, args: dict, result: Any) -> dict | None:
        try:
            # ── 逻辑函数：展示调用了哪个逻辑函数 + 本体内部调用链 ──
            if tool_name == "ontology_run_logic":
                if isinstance(result, dict):
                    return {
                        "type": "logic_run",
                        "callable": args.get("callable_name", ""),
                        "params": args.get("params", {}),
                        "success": result.get("success", False),
                        "execution_ms": result.get("execution_ms"),
                        "call_trace": result.get("call_trace", []),
                        "error": result.get("error"),
                    }

            # ── 动作函数：展示调用了哪个动作函数 + 调用链 ──
            elif tool_name == "ontology_run_action":
                if isinstance(result, dict):
                    return {
                        "type": "action_run",
                        "callable": args.get("callable_name", ""),
                        "params": args.get("params", {}),
                        "success": result.get("success", False),
                        "execution_ms": result.get("execution_ms"),
                        "call_trace": result.get("call_trace", []),
                        "error": result.get("error"),
                    }

            # ── 本体实例查询：展示查了哪个本体对象、命中数据源/表、筛选条件 ──
            elif tool_name == "ontology_query_instances":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "instance_query",
                        "entity": result.get("entity", args.get("entity_name", "")),
                        "datasource": result.get("datasource", ""),
                        "table": result.get("table", ""),
                        "filters": args.get("filters", {}),
                        "row_count": result.get("rowCount", 0),
                    }

            # ── 属性映射：展示解析了哪些本体对象、映射到哪张表 ──
            elif tool_name == "ontology_get_attr_mapping":
                if isinstance(result, dict):
                    mappings = []
                    for name, m in result.items():
                        if isinstance(m, dict) and not m.get("error"):
                            mappings.append({"entity": name, "table": m.get("table", "")})
                    return {"type": "attr_mapping", "mappings": mappings}

            # ── 复杂 SQL：展示实际执行的查询语句与返回行数 ──
            elif tool_name == "ontology_complex_sql":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "sql_query",
                        "sql": args.get("sql", ""),
                        "row_count": result.get("rowCount", 0),
                    }

            # ── 本体模型：展示读取到的本体对象与关系概览 ──
            elif tool_name == "describe_ontology_model":
                if isinstance(result, dict):
                    ents = result.get("entities", []) or []
                    return {
                        "type": "ontology_model",
                        "entity_count": len(ents),
                        "relation_count": len(result.get("relations", []) or []),
                        "entities": [e.get("name_cn") or e.get("name", "") for e in ents[:12]],
                    }

            # ── 本体能力清单：展示可用逻辑/动作函数 ──
            elif tool_name == "ontology_list_capabilities":
                if isinstance(result, list):
                    return {
                        "type": "capabilities",
                        "functions": [
                            {"name": c.get("name", ""), "type": c.get("type", "")}
                            for c in result[:20]
                        ],
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

            elif tool_name == "list_business_datasources":
                if isinstance(result, dict):
                    return {
                        "type": "asset_picker",
                        "kind": "datasource",
                        "display_card": result.get("display_card"),
                    }

            elif tool_name == "list_business_documents":
                if isinstance(result, dict):
                    return {
                        "type": "asset_picker",
                        "kind": "document",
                        "display_card": result.get("display_card"),
                    }

            elif tool_name == "analyze_assets_for_ontology":
                if isinstance(result, dict) and not result.get("error"):
                    return {
                        "type": "ontology_draft",
                        "entities": result.get("entities", []),
                        "relations": result.get("relations", []),
                        "suggested_rules": result.get("suggested_rules", []),
                        "suggested_actions": result.get("suggested_actions", []),
                    }

        except Exception:
            pass
        return None
