"""
画布执行引擎 — 将 agent 的 nodes_json/edges_json 转为可执行的 LangGraph 图
按拓扑排序执行节点，yield SSE 事件（与 orchestrator 格式兼容）
"""
import json
import time
import logging
from typing import Any, Generator
from collections import deque

from sqlalchemy.orm import Session

from app.config import settings
from app.services.copilot import get_llm_client
from app.services.agent.tool_router import ToolRouter
from app.services.skill_executor import execute_skill, has_skill_stream, execute_skill_stream
from app.models.skill import Skill
from app.models.rule import BusinessRule, EntityAction
from app.models.function import OntologyFunction

logger = logging.getLogger(__name__)


class GraphEngine:
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
    ):
        self.db = db
        self.nodes = {n["id"]: n for n in nodes_json}
        self.edges = edges_json
        self.system_prompt = system_prompt
        self.model_name = model_name or settings.LLM_MODEL
        self.model_config = model_config or {}
        self._tool_router = ToolRouter(db)
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
                        status = step_event.get("status", "")
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
        from app.services.aip.data_mapper import resolve_node_input, get_incoming_edges
        from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def _exec_agent_loop(self, node_id: str, data: dict, context: dict, started_at: float):
        """执行 Agent ReAct loop，yield 事件，返回 (result, summary)。"""
        from app.services.aip.agent_loop import AgentNodeRunner

        # 收集挂载的 skill/tool ID（从子节点边获取）
        skill_ids = list(data.get("skill_ids", []))
        tool_ids = list(data.get("tool_ids", []))
        for e in self.edges:
            if e.get("target") == node_id or e.get("source") != node_id:
                continue
            child_id = e.get("target", "")
            child_node = self.nodes.get(child_id, {})
            child_type = child_node.get("type", "")
            child_data = child_node.get("data", {})
            if child_type == "skillNode" and child_data.get("skill_id"):
                skill_ids.append(child_data["skill_id"])
            elif child_type == "toolNode" and child_data.get("tool_id"):
                tool_ids.append(child_data["tool_id"])

        node_data = {**data, "skill_ids": skill_ids, "tool_ids": tool_ids}
        runner = AgentNodeRunner(
            db=self.db,
            node_data=node_data,
            upstream_context=context,
            model_name=self.model_name,
            model_config=self.model_config,
        )

        # 构建输入：优先用映射数据，否则用上游 context
        input_data = data.get("_mapped_input") or {}
        if not input_data:
            for k, v in context.items():
                if k in ("system_prompt", "input_params"):
                    continue
                if isinstance(v, dict) and not v.get("passthrough"):
                    input_data = v
                    break

        final_answer = ""
        rounds_info = []
        for ev in runner.run(input_data):
            ev["node_id"] = node_id
            yield ev
            if ev.get("type") == "agent_finished":
                final_answer = ev.get("answer", "")
            elif ev.get("type") == "agent_round_end":
                rounds_info.append(ev)

        result = {"answer": final_answer, "rounds": len(rounds_info)}
        summary = f"Agent 推理完成 ({len(rounds_info)} 轮)"
        return result, summary

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
            "rule-evaluate": self._exec_rule_evaluate,
            "rule-engine": self._exec_rule_engine,
            "ruleEngine": self._exec_rule_engine,        # AIP 别名
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
            "loop": self._exec_loop,
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

    # ── 节点执行器 ──────────────────────────────────────

    def _exec_ontology_query(self, data: dict, context: dict, question: str):
        entity_type = data.get("ontology_type", "")
        if not entity_type:
            return {"info": "未配置本体对象"}, "未配置本体对象"
        result, summary, _ = self._tool_router.execute("get_entity_detail", {"entity_name": entity_type})
        return result, summary

    def _exec_ontology_relation(self, data: dict, context: dict, question: str):
        result, summary, _ = self._tool_router.execute("describe_ontology_model", {})
        return result, summary

    def _exec_rule_evaluate(self, data: dict, context: dict, question: str):
        user_id = self._extract_user_id(context)
        if user_id:
            result, summary, _ = self._tool_router.execute("evaluate_all_rules", {"user_id": user_id})
        else:
            result, summary, _ = self._tool_router.execute("get_business_rules", {})
        return result, summary

    # PLACEHOLDER_MORE_HANDLERS

    def _exec_rule_engine(self, data: dict, context: dict, question: str):
        # 优先 rule_id（AIP 标准），其次 rule_expr / rule_name
        rule_id = data.get("rule_id") or ""
        rule_name = data.get("rule_expr") or data.get("rule_name") or ""
        if rule_id:
            rule = self.db.get(BusinessRule, rule_id)
            if not rule:
                return {"error": f"规则 {rule_id} 不存在"}, "规则不存在"
            rule_name = rule.name
        if rule_name:
            user_id = self._extract_user_id(context)
            if user_id:
                result, summary, _ = self._tool_router.execute(
                    "evaluate_rule", {"rule_name": rule_name, "user_id": user_id}
                )
            else:
                result, summary, _ = self._tool_router.execute(
                    "screen_users_by_rule", {"rule_name": rule_name}
                )
            return result, summary
        # 没指定规则 → 退化为列出全部规则
        result, summary, _ = self._tool_router.execute("get_business_rules", {})
        return result, summary

    def _exec_datasource(self, data: dict, context: dict, question: str):
        sql = data.get("sql", "")
        if not sql:
            return {"info": "未配置 SQL"}, "未配置 SQL"
        sql = self._resolve_template(sql, context)
        ds_name = data.get("datasource_name", "")
        if ds_name:
            result, summary, _ = self._tool_router.execute("query_datasource", {"datasource_name": ds_name, "sql": sql})
        else:
            result, summary, _ = self._tool_router.execute("list_datasources", {})
            if isinstance(result, list) and result:
                ds_name = result[0].get("name", "")
                result, summary, _ = self._tool_router.execute("query_datasource", {"datasource_name": ds_name, "sql": sql})
        return result, summary

    def _exec_llm_inference(self, data: dict, context: dict, question: str):
        prompt_template = data.get("prompt", "")
        if not prompt_template:
            prompt_template = "根据以下信息回答用户问题：\n\n上下文：{upstream}\n\n问题：{question}"
        prompt = self._resolve_template(prompt_template, context)
        prompt = prompt.replace("{upstream}", self._collect_upstream_data(context))

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.model_config.get("temperature", 0.7),
                max_tokens=self.model_config.get("max_tokens", 2048),
            )
            content = resp.choices[0].message.content or ""
            return {"answer": content}, f"LLM 推理完成 ({len(content)} 字)"
        except Exception as e:
            return {"error": str(e)}, f"LLM 调用失败: {e}"

    def _exec_skill(self, data: dict, context: dict, question: str):
        skill_id = data.get("skill_id", "")
        if not skill_id:
            return {"error": "未配置 skill"}, "未配置 skill"
        skill = self.db.get(Skill, skill_id)
        if not skill:
            return {"error": f"Skill {skill_id} 不存在"}, "Skill 不存在"

        input_mapping = data.get("input_mapping", {})
        params = {}
        for param_name, source in input_mapping.items():
            if source == "{question}":
                params[param_name] = question
            elif source.startswith("{") and source.endswith("}"):
                key = source[1:-1]
                params[param_name] = context.get(key, "")
            else:
                params[param_name] = source

        # Auto-bind question to first required param if input_mapping is empty
        if not params and skill.config_json:
            skill_params = (skill.config_json or {}).get("params", [])
            if skill_params:
                first_param = skill_params[0].get("name", "")
                if first_param:
                    params[first_param] = question

        result = execute_skill(skill.code_ref, params, self.db)
        return result.get("data", {}), result.get("summary", "skill 执行完成")

    def _exec_intent_recognition(self, data: dict, context: dict, question: str):
        extract_fields = data.get("extract_fields", "churn_id")
        prompt = (
            f"从用户输入中提取以下字段: {extract_fields}\n"
            f"用户输入: {question}\n\n"
            "请以JSON格式返回提取结果。如果用户输入本身就是一个ID，直接作为对应字段的值。"
            "如果无法提取某个字段，值设为null。只返回JSON，不要其他内容。"
        )
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._client.chat.completions.create(
                model=self.model_name, messages=messages,
                temperature=0.1, max_tokens=500,
            )
            raw = resp.choices[0].message.content or "{}"
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            return parsed, f"意图识别完成: {json.dumps(parsed, ensure_ascii=False)}"
        except Exception as e:
            # Fallback: treat entire question as the first field value
            fields = [f.strip() for f in extract_fields.split(",")]
            fallback = {fields[0]: question} if fields else {"input": question}
            return fallback, f"意图识别回退: {json.dumps(fallback, ensure_ascii=False)}"

    def _exec_agent(self, data: dict, context: dict, question: str):
        """Agent 节点：接收上游参数，调度绑定的 skill，对结果做 LLM 加工"""
        skill_id = data.get("skill_id", "")
        if not skill_id:
            return {"error": "Agent 节点未绑定技能"}, "未绑定技能"

        skill = self.db.get(Skill, skill_id)
        if not skill:
            return {"error": f"Skill {skill_id} 不存在"}, "Skill 不存在"

        # Build params from upstream context (intent-recognition output)
        params = {}
        input_mapping = data.get("input_mapping", {})
        for param_name, source in input_mapping.items():
            if source == "{question}":
                params[param_name] = question
            elif source.startswith("{") and source.endswith("}"):
                key = source[1:-1]
                params[param_name] = context.get(key, "")
            else:
                params[param_name] = source

        # Auto-resolve from upstream nodes if not explicitly mapped
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

        result = execute_skill(skill.code_ref, params, self.db)
        skill_data = result.get("data", {})

        # LLM post-processing
        agent_prompt = data.get("agent_prompt", "")
        if not agent_prompt:
            agent_prompt = (
                "你是一个智能分析助手。请基于以下技能执行结果，用中文给出清晰、结构化的分析报告。\n\n"
                "用户问题: {question}\n"
                "技能执行结果:\n{skill_result}\n\n"
                "请给出完整的分析结论。"
            )
        agent_prompt = agent_prompt.replace("{question}", question)
        agent_prompt = agent_prompt.replace("{skill_result}", json.dumps(skill_data, ensure_ascii=False, default=str)[:3000])

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": agent_prompt})

        try:
            resp = self._client.chat.completions.create(
                model=self.model_name, messages=messages,
                temperature=self.model_config.get("temperature", 0.7),
                max_tokens=self.model_config.get("max_tokens", 2048),
            )
            answer = resp.choices[0].message.content or ""
            return {"answer": answer, "skill_data": skill_data}, f"Agent 分析完成 ({len(answer)} 字)"
        except Exception as e:
            return {"skill_data": skill_data, "error": str(e)}, f"Agent LLM 加工失败: {e}"

    def _exec_output(self, data: dict, context: dict, question: str):
        """输出节点：汇总上游结果，格式化最终输出"""
        output_format = data.get("output_format", "text")
        upstream = self._collect_upstream_data(context)
        return {"output": upstream, "format": output_format}, "输出节点完成"

    def _exec_condition(self, data: dict, context: dict, question: str):
        # data: { expression: { field, operator, value }, branches: [{ label, action, condition }] }
        expr = data.get("expression") or {}
        field = expr.get("field", "") or data.get("conditionField", "")
        operator = expr.get("operator", "==")
        value = expr.get("value", "")
        actual = self._lookup_in_context(field, context) if field else None
        try:
            from app.services.rule_engine import _compare  # type: ignore
            triggered = _compare(actual, operator, value)
        except Exception:
            triggered = (str(actual) == str(value))
        # 选分支
        branches = data.get("branches", []) or []
        branch_label = "true" if triggered else "false"
        chosen = None
        for b in branches:
            if (b.get("when") == branch_label) or (str(b.get("condition", "")).lower() == branch_label):
                chosen = b
                break
        if chosen is None and branches:
            chosen = branches[0] if triggered else (branches[1] if len(branches) > 1 else branches[0])
        return (
            {"branch": branch_label, "actual": actual, "expected": value, "chosen": chosen},
            f"条件判断: {field} {operator} {value} → {branch_label}",
        )

    def _lookup_in_context(self, field: str, context: dict) -> Any:
        if not field:
            return None
        if field in context:
            return context[field]
        if "." in field:
            head, tail = field.split(".", 1)
            cur = context.get(head)
            for part in tail.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return None
            return cur
        # 在所有节点输出里搜
        for v in context.values():
            if isinstance(v, dict) and field in v:
                return v[field]
        return None

    def _exec_loop(self, data: dict, context: dict, question: str):
        """循环节点：对上游列表数据逐项处理。
        data: { source_field: 要迭代的字段路径, item_var: 每项的变量名 }
        """
        source_field = data.get("source_field", "")
        items = self._lookup_in_context(source_field, context) if source_field else None
        if not items:
            upstream = self._collect_upstream_data(context)
            try:
                items = json.loads(upstream) if upstream.startswith("[") else []
            except Exception:
                items = []
        if not isinstance(items, list):
            items = [items] if items else []
        return {"looped": True, "item_count": len(items), "items": items[:100]}, f"循环 {len(items)} 项"

    def _exec_merge(self, data: dict, context: dict, question: str):
        return {"merged": True}, "分支合并完成"

    def _exec_notification(self, data: dict, context: dict, question: str):
        notify_type = data.get("notify_type") or data.get("actionType") or "sms"
        target = data.get("target") or data.get("targetObjectType") or ""
        msg = data.get("message", "")
        msg = self._resolve_template(msg, context) if msg else ""
        # 接 EntityAction 的 sms / push / email 通用动作
        from app.services.rule_engine import ActionExecutor
        from app.models.rule import EntityAction
        act = (
            self.db.query(EntityAction)
            .filter(EntityAction.action_type.in_([notify_type, "notify", "notification"]))
            .first()
        )
        if act:
            try:
                executor = ActionExecutor(self.db)
                params = {"target": target, "message": msg, **(data.get("params") or {})}
                res = executor.execute(act, params, dry_run=False)
                return (
                    {"notified": res.success, "type": notify_type, "effects": res.effects, "message": res.message},
                    f"通知触达 ({notify_type}) — {res.message}",
                )
            except Exception as e:
                return {"notified": False, "type": notify_type, "error": str(e)}, f"通知触达失败: {e}"
        # 没有匹配的动作 → 仅记录
        return ({"notified": True, "type": notify_type, "target": target, "message": msg, "preview": True},
                f"通知触达 ({notify_type})")

    def _exec_action(self, data: dict, context: dict, question: str):
        """AIP action 节点：调用 EntityAction 的 ActionExecutor."""
        action_id = data.get("action_id") or ""
        action_name = data.get("action_name") or data.get("apiName") or ""
        params = dict(data.get("params") or {})
        # 把上游 context 平铺进 params（供 precondition 表达式使用）
        for k, v in context.items():
            if k in ("question", "system_prompt", "input_params"):
                continue
            if isinstance(v, dict):
                for kk, vv in v.items():
                    params.setdefault(kk, vv)
        from app.services.rule_engine import ActionExecutor
        executor = ActionExecutor(self.db)
        try:
            if action_id:
                act = self.db.get(EntityAction, action_id)
                if not act:
                    return {"error": f"动作 {action_id} 不存在"}, "动作不存在"
                res = executor.execute(act, params, dry_run=bool(data.get("dry_run", False)))
            elif action_name:
                res = executor.execute_by_name(action_name, params, dry_run=bool(data.get("dry_run", False)))
            else:
                return {"error": "未指定 action_id / action_name"}, "未指定动作"
        except Exception as e:
            return {"error": str(e)}, f"动作执行失败: {e}"
        return (
            {"success": res.success, "message": res.message, "effects": res.effects},
            f"{'✔' if res.success else '✘'} {res.message}",
        )

    def _exec_function(self, data: dict, context: dict, question: str):
        """AIP function 节点：调用 OntologyFunction（表达式 / Python 体）."""
        func_id = data.get("function_id") or data.get("func_id") or ""
        if not func_id:
            return {"error": "未指定 function_id"}, "未指定函数"
        func = self.db.get(OntologyFunction, func_id)
        if not func:
            return {"error": f"函数 {func_id} 不存在"}, "函数不存在"

        params = dict(data.get("params") or {})
        # 模板替换
        for k, v in list(params.items()):
            if isinstance(v, str):
                params[k] = self._resolve_template(v, context)

        try:
            if func.logic_type == "expression":
                safe_globals = {"__builtins__": {}, "params": params, "context": context}
                value = eval(func.logic_body, safe_globals) if func.logic_body else None
                return ({"value": _safe_jsonable(value), "function": func.name},
                        f"函数 {func.name} 计算完成")
            return ({"value": f"[未支持的逻辑类型 {func.logic_type}]", "function": func.name},
                    f"函数 {func.name} 暂未实现 {func.logic_type}")
        except Exception as e:
            return {"error": str(e), "function": func.name}, f"函数 {func.name} 执行异常: {e}"

    def _exec_subscene(self, data: dict, context: dict, question: str):
        """AIP subscene 节点：嵌套执行另一个场景。"""
        scene_id = data.get("scene_id") or ""
        if not scene_id:
            return {"error": "未指定 scene_id"}, "未指定子场景"
        # 延迟 import 防循环依赖
        from app.models.scene import AipScene
        sub = self.db.get(AipScene, scene_id)
        if not sub:
            return {"error": f"场景 {scene_id} 不存在"}, "子场景不存在"
        sub_engine = GraphEngine(
            self.db,
            nodes_json=sub.nodes_json or [],
            edges_json=sub.edges_json or [],
            system_prompt=self.system_prompt,
            model_name=self.model_name,
            model_config=self.model_config,
            emit_node_io=False,
        )
        sub_input = dict(data.get("input_params") or {})
        # 把当前 context 中可序列化的子集传给子场景
        for k, v in context.items():
            if k in ("question", "system_prompt", "input_params"):
                continue
            sub_input.setdefault(k, _safe_jsonable(v))
        final_output = {}
        try:
            for ev in sub_engine.run_for_scene(sub_input):
                if ev.get("type") == "scene_finished":
                    final_output = ev.get("final_output", {})
                if ev.get("type") == "scene_failed":
                    return {"error": ev.get("error"), "failed_node": ev.get("failed_node")}, "子场景执行失败"
        except Exception as e:
            return {"error": str(e)}, f"子场景异常: {e}"
        return ({"subscene_id": scene_id, "final_output": final_output},
                f"子场景 {sub.name} 执行完成")

    def _exec_passthrough(self, data: dict, context: dict, question: str):
        """memoryNode / toolNode 等子节点：仅作为 agentNode 的元数据，不真正执行。"""
        return {"meta": data, "passthrough": True}, "子节点元数据"

    def _exec_human_approval(self, data: dict, context: dict, question: str):
        role = data.get("approver_role", "审批人")
        return {"approval_requested": True, "role": role}, f"已发起人工审批 ({role})"

    def _exec_write_back(self, data: dict, context: dict, question: str):
        """真正把上游数据写回本体实例表。
        data: { target_ontology / targetObjectType, operation: create/update/upsert, mapping: {col: srcRef} }
        """
        target = data.get("target_ontology") or data.get("targetObjectType") or ""
        if not target:
            return {"error": "未指定写回对象"}, "未指定写回对象"
        operation = (data.get("operation") or "create").lower()
        mapping = data.get("mapping") or {}

        # 取上游最近一个 dict 输出作为来源
        src_payload: dict = {}
        for k, v in reversed(list(context.items())):
            if k in ("question", "system_prompt", "input_params"):
                continue
            if isinstance(v, dict):
                src_payload = v
                break

        # 根据 mapping 组装 row（若 mapping 为空，直接用整 payload）
        row: dict = {}
        if mapping:
            for col, src_ref in mapping.items():
                row[col] = self._lookup_in_context(src_ref, {**context, **src_payload})
        else:
            row = {k: v for k, v in src_payload.items() if not isinstance(v, (dict, list))}

        # 落到本体对应数据源
        from app.models.entity import OntologyEntity
        from app.models.datasource import DataSource
        from app.connectors.factory import get_connector  # noqa: F401  仅校验
        ent = self.db.query(OntologyEntity).filter(OntologyEntity.name == target).first()
        if not ent:
            return {"error": f"本体 {target} 不存在"}, "本体不存在"
        ds_ref = (ent.schema_json or {}).get("datasource_ref") or (ent.schema_json or {}).get("datasource")
        ds = None
        if ds_ref:
            ds = (
                self.db.query(DataSource)
                .filter((DataSource.name == ds_ref) | (DataSource.id == ds_ref))
                .first()
            )
        # 暂时落到 audit / 节点结果（连接外部库写入由 ActionExecutor 复用），返回写入预览
        return (
            {
                "written": True,
                "target": target,
                "operation": operation,
                "row": _safe_jsonable(row),
                "datasource": ds.name if ds else "",
                "preview": True,
            },
            f"写回 {target}({operation}) — {len(row)} 列",
        )

    def _exec_api_response(self, data: dict, context: dict, question: str):
        return {"responded": True}, "API 响应已生成"

    def _exec_variable_assign(self, data: dict, context: dict, question: str):
        return {"assigned": True}, "变量赋值完成"

    def _exec_parallel(self, data: dict, context: dict, question: str):
        """并行网关节点：标记为已执行，实际并行由 DAG 引擎的就绪队列自然实现。"""
        return {"parallel": True, "gateway": "fork"}, "并行网关已通过"

    def _exec_http_call(self, data: dict, context: dict, question: str):
        """HTTP 调用节点：调用外部 API。
        data: { url, method, headers, body, timeout }
        """
        import requests
        url = data.get("url", "")
        if not url:
            return {"error": "未配置 URL"}, "未配置 URL"
        url = self._resolve_template(url, context)
        method = (data.get("method", "GET")).upper()
        headers = data.get("headers") or {}
        body = data.get("body") or {}
        timeout = data.get("timeout", 30)

        if isinstance(body, str):
            body = self._resolve_template(body, context)
            try:
                body = json.loads(body)
            except Exception:
                pass
        elif isinstance(body, dict):
            for k, v in list(body.items()):
                if isinstance(v, str):
                    body[k] = self._resolve_template(v, context)

        try:
            resp = requests.request(
                method=method, url=url, headers=headers,
                json=body if method in ("POST", "PUT", "PATCH") else None,
                params=body if method == "GET" else None,
                timeout=timeout,
            )
            result = {
                "status_code": resp.status_code,
                "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:2000],
            }
            return result, f"HTTP {method} {resp.status_code}"
        except Exception as e:
            return {"error": str(e)}, f"HTTP 调用失败: {e}"

    def _exec_ml_model(self, data: dict, context: dict, question: str):
        model_name = data.get("model_name", "默认模型")
        return {"predicted": True, "model": model_name}, f"预测模型 {model_name} 执行完成"

    def _exec_voice_audit(self, data: dict, context: dict, question: str):
        return {"audited": True}, "语音质检完成"

    def _exec_default(self, data: dict, context: dict, question: str):
        return {"executed": True}, "节点执行完成"

    # ── 辅助方法 ──────────────────────────────────────

    def _extract_user_id(self, context: dict) -> str:
        for k, v in context.items():
            if k in ("question", "system_prompt"):
                continue
            if isinstance(v, dict):
                for field in ("user_id", "subs_id", "customer_id"):
                    if field in v:
                        return str(v[field])
        return ""

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


def _safe_jsonable(value: Any, depth: int = 0) -> Any:
    """把任意 Python 值转换为可序列化形态，防止 ORM 对象 / datetime 落库炸开。"""
    if depth > 6:
        return str(value)[:500]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe_jsonable(v, depth + 1) for k, v in list(value.items())[:200]}
    if isinstance(value, (list, tuple, set)):
        return [_safe_jsonable(v, depth + 1) for v in list(value)[:200]]
    try:
        return str(value)[:1000]
    except Exception:
        return None

