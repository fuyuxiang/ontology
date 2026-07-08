"""
画布执行引擎 — 将 agent 的 nodes_json/edges_json 转为可执行的 LangGraph 图
按拓扑排序执行节点，yield SSE 事件（与 orchestrator 格式兼容）
"""
import json
import logging
import time
from collections import deque
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.skill import Skill
from app.services.agent.graph_handlers import NodeHandlersMixin, _safe_jsonable
from app.services.agent.tool_router import ToolRouter
from app.services.copilot import get_llm_client
from app.services.skill_executor import execute_skill_stream, has_skill_stream

logger = logging.getLogger(__name__)


class GraphEngine(NodeHandlersMixin):
    """将画布 nodes_json + edges_json 编译为可执行图并运行"""

    def __init__(
        self,
        db: Session,
        nodes_json: list[dict],
        edges_json: list[dict],
        system_prompt: str = "",
        model_name: str | None = None,
        model_config: dict | None = None,
        emit_node_io: bool = False,
        runtime_executor=None,
    ):
        self.db = db
        self.nodes = {n["id"]: n for n in nodes_json}
        self.edges = edges_json
        self.system_prompt = system_prompt
        self.model_name = model_name or settings.LLM_MODEL
        self.model_config = model_config or {}
        self._tool_router = ToolRouter(db, runtime_executor=runtime_executor)
        self._client = get_llm_client(
            api_key=self.model_config.get("api_key"),
            api_base=self.model_config.get("api_base"),
        )
        # 当 True 时，每个节点会额外 yield 结构化的 node_started/node_finished/node_failed 事件，
        # 包含输入/输出/耗时等真实数据，给 AIP 场景执行落库使用
        self.emit_node_io = emit_node_io
        # 收集每个节点的真实 IO（供调用方落库）
        self.node_io: dict[str, dict] = {}


    def run(self, question: str) -> Generator[dict, None, None]:
        """按拓扑排序执行画布节点，yield SSE 事件"""
        topo_order = self._topological_sort()
        if not topo_order:
            yield {"type": "content", "content": "画布为空或存在循环依赖，无法执行。"}
            yield {"type": "done", "suggestions": []}
            return

        context: dict[str, Any] = {"question": question, "system_prompt": self.system_prompt}
        tool_runs: list[dict] = []

        for node_id in topo_order:
            node = self.nodes[node_id]
            ntype = node.get("type", "")
            data = node.get("data", {})
            label = data.get("label", ntype)

            node_started_at = time.time()
            if self.emit_node_io:
                yield {
                    "type": "node_started",
                    "node_id": node_id,
                    "node_type": ntype,
                    "label": label,
                    "started_at": node_started_at,
                }

            # Skill nodes with streaming support: yield per-step events
            if ntype == "skill" and data.get("skill_id"):
                skill = self.db.get(Skill, data["skill_id"])
                if skill and has_skill_stream(skill.code_ref):
                    input_mapping = data.get("input_mapping", {})
                    params = {}
                    for param_name, source in input_mapping.items():
                        if source == "{question}":
                            params[param_name] = question
                        elif source.startswith("{") and source.endswith("}"):
                            params[param_name] = context.get(source[1:-1], "")
                        else:
                            params[param_name] = source

                    # Auto-bind question to first required param if input_mapping is empty
                    if not params and skill.config_json:
                        skill_params = (skill.config_json or {}).get("params", [])
                        if skill_params:
                            first_param = skill_params[0].get("name", "")
                            if first_param:
                                params[first_param] = question

                    last_data = {}
                    last_summary = ""
                    for step_event in execute_skill_stream(skill.code_ref, params, self.db):
                        step = step_event.get("step", "")
                        step_label = step_event.get("label", label)
                        step_summary = step_event.get("summary", "")
                        step_data = step_event.get("data")

                        if step == "error":
                            yield {"type": "tool_start", "tool": f"[{label}]", "arguments": {"node_type": ntype, "node_id": node_id}}
                            yield {"type": "tool_result", "tool": f"[{label}]", "summary": step_event.get("message", "错误"), "resultCount": 0, "detail": None}
                            tool_runs.append({"tool": f"[{label}]", "arguments": {"node_type": ntype}, "summary": step_event.get("message", "错误"), "resultCount": 0})
                            break
                        elif step == "result":
                            last_data = step_event.get("data", {})
                            last_summary = step_summary
                        else:
                            yield {"type": "tool_start", "tool": f"[{step_label}]", "arguments": {"node_type": "skill_step", "node_id": node_id, "step": step}}
                            yield {"type": "tool_result", "tool": f"[{step_label}]", "summary": step_summary, "resultCount": 1, "detail": step_data}
                            tool_runs.append({"tool": f"[{step_label}]", "arguments": {"node_type": "skill_step", "step": step}, "summary": step_summary, "resultCount": 1})

                    context[node_id] = last_data
                    self._record_node_io(node_id, ntype, label, params, last_data, last_summary, node_started_at, status="success")
                    if self.emit_node_io:
                        yield self._make_node_finished_event(node_id, ntype, label, last_data, last_summary, node_started_at)
                    continue

            # Agent nodes with streaming skill: yield per-step events then LLM post-process
            if ntype == "agent" and data.get("skill_id"):
                skill = self.db.get(Skill, data["skill_id"])
                if skill and has_skill_stream(skill.code_ref):
                    # Resolve params from upstream context
                    params = {}
                    input_mapping = data.get("input_mapping", {})
                    for param_name, source in input_mapping.items():
                        if source == "{question}":
                            params[param_name] = question
                        elif source.startswith("{") and source.endswith("}"):
                            params[param_name] = context.get(source[1:-1], "")
                        else:
                            params[param_name] = source

                    if not params:
                        skill_params = (skill.config_json or {}).get("params", [])
                        for sp in skill_params:
                            pname = sp.get("name", "")
                            if not pname:
                                continue
                            for nid, val in context.items():
                                if nid in ("question", "system_prompt"):
                                    continue
                                if isinstance(val, dict) and pname in val:
                                    params[pname] = str(val[pname])
                                    break
                            if pname not in params:
                                params[pname] = question

                    last_data = {}
                    for step_event in execute_skill_stream(skill.code_ref, params, self.db):
                        step = step_event.get("step", "")
                        step_label = step_event.get("label", label)
                        step_summary = step_event.get("summary", "")
                        step_data = step_event.get("data")

                        if step == "error":
                            yield {"type": "tool_start", "tool": f"[{label}]", "arguments": {"node_type": ntype, "node_id": node_id}}
                            yield {"type": "tool_result", "tool": f"[{label}]", "summary": step_event.get("message", "错误"), "resultCount": 0, "detail": None}
                            tool_runs.append({"tool": f"[{label}]", "arguments": {"node_type": ntype}, "summary": step_event.get("message", ""), "resultCount": 0})
                            break
                        elif step == "result":
                            last_data = step_event.get("data", {})
                        else:
                            yield {"type": "tool_start", "tool": f"[{step_label}]", "arguments": {"node_type": "skill_step", "node_id": node_id, "step": step}}
                            yield {"type": "tool_result", "tool": f"[{step_label}]", "summary": step_summary, "resultCount": 1, "detail": step_data}
                            tool_runs.append({"tool": f"[{step_label}]", "arguments": {"node_type": "skill_step", "step": step}, "summary": step_summary, "resultCount": 1})

                    context[node_id] = {"skill_data": last_data}
                    self._record_node_io(node_id, ntype, label, params, {"skill_data": last_data}, "agent skill 流式完成", node_started_at, status="success")
                    if self.emit_node_io:
                        yield self._make_node_finished_event(node_id, ntype, label, {"skill_data": last_data}, "agent skill 流式完成", node_started_at)
                    continue

            yield {"type": "tool_start", "tool": f"[{label}]", "arguments": {"node_type": ntype, "node_id": node_id}}

            failed = False
            try:
                result, summary = self._execute_node(ntype, data, context, question)
                context[node_id] = result
            except Exception as e:
                logger.error(f"节点 {node_id} ({ntype}) 执行失败: {e}")
                result = {"error": str(e)}
                summary = f"执行失败: {e}"
                context[node_id] = result
                failed = True

            tool_runs.append({"tool": f"[{label}]", "arguments": {"node_type": ntype}, "summary": summary, "resultCount": 1})
            yield {"type": "tool_result", "tool": f"[{label}]", "summary": summary, "resultCount": 1, "detail": None}
            self._record_node_io(node_id, ntype, label, data, result, summary, node_started_at, status="failed" if failed else "success")
            if self.emit_node_io:
                if failed:
                    yield self._make_node_failed_event(node_id, ntype, label, result.get("error", summary), node_started_at)
                else:
                    yield self._make_node_finished_event(node_id, ntype, label, result, summary, node_started_at)

        if tool_runs:
            yield {"type": "tool_summary", "toolRuns": tool_runs}

        final_answer = self._generate_final_answer(context, question)
        chunk_size = 20
        for i in range(0, len(final_answer), chunk_size):
            yield {"type": "content", "content": final_answer[i:i + chunk_size]}
        yield {"type": "done", "suggestions": self._generate_suggestions(context, question), "actions": []}

    def run_for_scene(self, input_params: dict | None = None) -> Generator[dict, None, None]:
        """AIP 场景模式入口：就绪队列执行，支持条件分支路由、并行、数据映射。"""

        from app.services.aip.data_mapper import get_incoming_edges, resolve_node_input

        self.emit_node_io = True
        if not self.nodes:
            yield {"type": "scene_failed", "error": "画布为空"}
            return

        context: dict[str, Any] = {
            "system_prompt": self.system_prompt,
            "input_params": input_params or {},
        }
        for k, v in (input_params or {}).items():
            context[k] = v

        # 构建 DAG 依赖关系
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        children: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        parent_edges: dict[str, list[dict]] = {nid: [] for nid in self.nodes}
        for e in self.edges:
            src, tgt = e.get("source"), e.get("target")
            if src in children and tgt in in_degree:
                children[src].append(tgt)
                in_degree[tgt] += 1
                parent_edges[tgt].append(e)

        # 状态追踪
        executed: set[str] = set()
        skipped: set[str] = set()
        ready = deque(nid for nid, deg in in_degree.items() if deg == 0)

        active_nodes = [nid for nid in self.nodes if self.nodes[nid].get("type") not in ("skillNode", "memoryNode", "toolNode")]
        yield {
            "type": "scene_started",
            "total_nodes": len(active_nodes),
            "input_params": input_params or {},
        }

        while ready:
            node_id = ready.popleft()
            if node_id in skipped or node_id in executed:
                self._propagate_ready(node_id, children, in_degree, executed, skipped, ready)
                continue

            node = self.nodes[node_id]
            ntype = node.get("type", "")
            data = node.get("data", {})
            label = data.get("label", ntype)
            node_started_at = time.time()

            # 跳过元数据子节点
            if ntype in ("memoryNode", "toolNode", "skillNode"):
                context[node_id] = {"meta": data, "passthrough": True}
                executed.add(node_id)
                self._propagate_ready(node_id, children, in_degree, executed, skipped, ready)
                continue

            yield {
                "type": "node_started",
                "node_id": node_id,
                "node_type": ntype,
                "label": label,
                "started_at": node_started_at,
            }

            # 数据映射：从入边的 mapping 配置组装输入
            incoming = get_incoming_edges(node_id, self.edges)
            mapped_input = resolve_node_input(node_id, incoming, context)
            if mapped_input:
                data = {**data, "_mapped_input": mapped_input}

            try:
                # Agent 节点特殊处理：使用 ReAct Loop
                if ntype in ("agentNode",) and self._should_use_agent_loop(data):
                    result, summary = yield from self._exec_agent_loop(node_id, data, context, node_started_at)
                else:
                    result, summary = self._execute_node(ntype, data, context, "")

                context[node_id] = result
                self._record_node_io(node_id, ntype, label, data, result, summary, node_started_at, status="success")
                yield self._make_node_finished_event(node_id, ntype, label, result, summary, node_started_at)
                executed.add(node_id)

                # 条件分支路由：标记未命中分支的下游为 skipped
                if ntype == "condition":
                    self._route_condition_branches(node_id, result, children, skipped, context)

            except Exception as e:
                logger.error(f"[scene] 节点 {node_id} ({ntype}) 执行失败: {e}")
                err = {"error": str(e)}
                context[node_id] = err
                self._record_node_io(node_id, ntype, label, data, err, str(e), node_started_at, status="failed")
                yield self._make_node_failed_event(node_id, ntype, label, str(e), node_started_at)
                executed.add(node_id)
                if data.get("on_error", "continue") == "stop":
                    yield {"type": "scene_failed", "failed_node": node_id, "error": str(e)}
                    return

            # 推进后续就绪节点
            self._propagate_ready(node_id, children, in_degree, executed, skipped, ready)

        final_output = self._collect_final_output(context)
        yield {"type": "scene_finished", "final_output": final_output, "node_io": self.node_io}

    def _propagate_ready(self, node_id: str, children: dict, in_degree: dict,
                         executed: set, skipped: set, ready: deque):
        """节点完成/跳过后，更新下游入度，就绪的加入队列。"""
        for child in children.get(node_id, []):
            in_degree[child] -= 1
            if in_degree[child] <= 0 and child not in executed and child not in skipped:
                ready.append(child)

    def _route_condition_branches(self, node_id: str, result: dict,
                                  children: dict, skipped: set, context: dict):
        """条件节点执行后，根据结果标记未命中的分支为 skipped。"""
        branch_label = result.get("branch", "true")
        outgoing = [e for e in self.edges if e.get("source") == node_id]

        for edge in outgoing:
            target = edge.get("target", "")
            handle = edge.get("sourceHandle", "")
            # sourceHandle 格式: "branch-true" / "branch-false" / "branch-0" / "branch-1" 等
            if handle and handle.startswith("branch-"):
                edge_branch = handle.replace("branch-", "")
                if edge_branch != branch_label and edge_branch != str(branch_label):
                    self._skip_subtree(target, children, skipped)

    def _skip_subtree(self, node_id: str, children: dict, skipped: set):
        """递归跳过某节点及其所有后续节点（条件分支未命中路径）。"""
        if node_id in skipped:
            return
        skipped.add(node_id)
        self.node_io[node_id] = {
            "node_id": node_id,
            "node_type": self.nodes.get(node_id, {}).get("type", ""),
            "label": self.nodes.get(node_id, {}).get("data", {}).get("label", ""),
            "status": "skipped",
            "input": {},
            "output": {"skipped": True},
            "summary": "条件分支未命中，已跳过",
            "started_at": time.time(),
            "finished_at": time.time(),
            "duration_ms": 0,
        }
        for child in children.get(node_id, []):
            # 只跳过该分支独有的下游（如果有其他入边不来自被跳过的节点，则不跳过）
            other_parents = [e for e in self.edges if e.get("target") == child and e.get("source") != node_id and e.get("source") not in skipped]
            if not other_parents:
                self._skip_subtree(child, children, skipped)

    def _should_use_agent_loop(self, data: dict) -> bool:
        """判断 Agent 节点是否应使用 ReAct loop（有绑定本体类型或 skill）。"""
        return bool(data.get("objectTypes")) or bool(data.get("skill_ids"))
    def _record_node_io(
        self, node_id: str, ntype: str, label: str,
        input_data: dict, output_data: Any, summary: str,
        started_at: float, status: str,
    ) -> None:
        finished_at = time.time()
        # output 可能是非 dict 的原子值
        if not isinstance(output_data, dict):
            output_data = {"value": output_data}
        self.node_io[node_id] = {
            "node_id": node_id,
            "node_type": ntype,
            "label": label,
            "status": status,
            "input": _safe_jsonable(input_data),
            "output": _safe_jsonable(output_data),
            "summary": summary,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": int((finished_at - started_at) * 1000),
        }

    def _make_node_finished_event(self, node_id, ntype, label, result, summary, started_at):
        ev = self.node_io.get(node_id, {})
        return {
            "type": "node_finished",
            "node_id": node_id,
            "node_type": ntype,
            "label": label,
            "summary": summary,
            "output": ev.get("output"),
            "duration_ms": ev.get("duration_ms", 0),
        }

    def _make_node_failed_event(self, node_id, ntype, label, error, started_at):
        ev = self.node_io.get(node_id, {})
        return {
            "type": "node_failed",
            "node_id": node_id,
            "node_type": ntype,
            "label": label,
            "error": error,
            "duration_ms": ev.get("duration_ms", 0),
        }

    def _collect_final_output(self, context: dict) -> dict:
        # 优先：标记为 type=output / api-response / write-back 的最后一个节点
        prefer_types = ("output", "api-response", "write-back", "writebackOntology", "actionSystem")
        for nid in reversed(list(self.nodes.keys())):
            node = self.nodes[nid]
            if node.get("type") in prefer_types and nid in context:
                val = context[nid]
                if isinstance(val, dict):
                    return val
                return {"value": val}
        # 否则取最后一个非 input/system 的 context
        for k in reversed(list(context.keys())):
            if k in ("question", "system_prompt", "input_params"):
                continue
            val = context[k]
            if isinstance(val, dict):
                return val
        return {}


    def _topological_sort(self) -> list[str]:
        in_degree: dict[str, int] = {nid: 0 for nid in self.nodes}
        children: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for e in self.edges:
            src, tgt = e.get("source"), e.get("target")
            if src in children and tgt in in_degree:
                children[src].append(tgt)
                in_degree[tgt] += 1

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for child in children.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return order

    def _execute_node(self, ntype: str, data: dict, context: dict, question: str) -> tuple[Any, str]:
        handlers = {
            "ontology-query": self._exec_ontology_query,
            "ontologyQuery": self._exec_ontology_query,  # AIP 别名
            "ontology-relation": self._exec_ontology_relation,
            "datasource": self._exec_datasource,
            "llm-inference": self._exec_llm_inference,
            "llmAgent": self._exec_llm_inference,        # AIP 别名
            "skill": self._exec_skill,
            "skillNode": self._exec_skill,               # AIP 别名
            "intent-recognition": self._exec_intent_recognition,
            "agent": self._exec_agent,
            "agentNode": self._exec_agent,               # AIP 别名
            "output": self._exec_output,
            "condition": self._exec_condition,
            "loop": self._exec_loop,
            "merge": self._exec_merge,
            "notification": self._exec_notification,
            "human-approval": self._exec_human_approval,
            "write-back": self._exec_write_back,
            "writebackOntology": self._exec_write_back,  # AIP 别名
            "api-response": self._exec_api_response,
            "variable-assign": self._exec_variable_assign,
            "parallel": self._exec_parallel,
            "ml-model": self._exec_ml_model,
            "voice-audit": self._exec_voice_audit,
            # AIP 新增
            "action": self._exec_action,
            "actionSystem": self._exec_action,
            "function": self._exec_function,
            "subscene": self._exec_subscene,
            "memoryNode": self._exec_passthrough,        # 子节点：仅作为元数据挂在 agent 上
            "toolNode": self._exec_passthrough,
            "skillNode": self._exec_passthrough,
            "httpCall": self._exec_http_call,
        }
        handler = handlers.get(ntype, self._exec_default)
        return handler(data, context, question)

    def _resolve_template(self, template: str, context: dict) -> str:
        """替换模板中的 {变量} 占位符"""
        import re
        def replacer(m):
            key = m.group(1)
            if key == "question":
                return context.get("question", "")
            for nid, val in context.items():
                if nid == key and isinstance(val, str):
                    return val
                if isinstance(val, dict) and key in val:
                    return str(val[key])
            return m.group(0)
        return re.sub(r'\{(\w+(?:\.\w+)?)\}', replacer, template)

    def _collect_upstream_data(self, context: dict) -> str:
        """收集上游节点的执行结果作为上下文"""
        parts = []
        for k, v in context.items():
            if k in ("question", "system_prompt"):
                continue
            if isinstance(v, dict):
                parts.append(json.dumps(v, ensure_ascii=False, default=str)[:2000])
            elif isinstance(v, str) and v:
                parts.append(v[:2000])
        return "\n".join(parts) if parts else "无上游数据"
    # ── 辅助方法 ──────────────────────────────────────

    def _generate_final_answer(self, context: dict, question: str) -> str:
        upstream = self._collect_upstream_data(context)
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": (
            f"用户问题: {question}\n\n"
            f"以下是编排流程各节点的执行结果:\n{upstream}\n\n"
            "请基于以上执行结果，用中文给出完整、准确的回答。"
        )})
        try:
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.model_config.get("temperature", 0.7),
                max_tokens=self.model_config.get("max_tokens", 2048),
            )
            return resp.choices[0].message.content or "执行完成，但未生成回答。"
        except Exception as e:
            return f"流程执行完成，但生成回答时出错: {e}"

    def _generate_suggestions(self, context: dict, question: str) -> list[str]:
        return ["查看更多详情", "换一个用户分析", "导出分析报告"]
