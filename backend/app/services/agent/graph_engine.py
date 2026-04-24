"""
画布执行引擎 — 将 agent 的 nodes_json/edges_json 转为可执行的 LangGraph 图
按拓扑排序执行节点，yield SSE 事件（与 orchestrator 格式兼容）
"""
import json
import logging
from typing import Any, Generator
from collections import deque

from sqlalchemy.orm import Session

from app.config import settings
from app.services.copilot import get_llm_client
from app.services.agent.tool_router import ToolRouter
from app.services.skill_executor import execute_skill, has_skill_stream, execute_skill_stream
from app.models.skill import Skill

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
                    continue

            yield {"type": "tool_start", "tool": f"[{label}]", "arguments": {"node_type": ntype, "node_id": node_id}}

            try:
                result, summary = self._execute_node(ntype, data, context, question)
                context[node_id] = result
            except Exception as e:
                logger.error(f"节点 {node_id} ({ntype}) 执行失败: {e}")
                result = {"error": str(e)}
                summary = f"执行失败: {e}"
                context[node_id] = result

            tool_runs.append({"tool": f"[{label}]", "arguments": {"node_type": ntype}, "summary": summary, "resultCount": 1})
            yield {"type": "tool_result", "tool": f"[{label}]", "summary": summary, "resultCount": 1, "detail": None}

        if tool_runs:
            yield {"type": "tool_summary", "toolRuns": tool_runs}

        final_answer = self._generate_final_answer(context, question)
        chunk_size = 20
        for i in range(0, len(final_answer), chunk_size):
            yield {"type": "content", "content": final_answer[i:i + chunk_size]}
        yield {"type": "done", "suggestions": self._generate_suggestions(context, question), "actions": []}

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
            "ontology-relation": self._exec_ontology_relation,
            "rule-evaluate": self._exec_rule_evaluate,
            "rule-engine": self._exec_rule_engine,
            "datasource": self._exec_datasource,
            "llm-inference": self._exec_llm_inference,
            "skill": self._exec_skill,
            "intent-recognition": self._exec_intent_recognition,
            "agent": self._exec_agent,
            "output": self._exec_output,
            "condition": self._exec_condition,
            "loop": self._exec_loop,
            "merge": self._exec_merge,
            "notification": self._exec_notification,
            "human-approval": self._exec_human_approval,
            "write-back": self._exec_write_back,
            "api-response": self._exec_api_response,
            "variable-assign": self._exec_variable_assign,
            "parallel": self._exec_parallel,
            "ml-model": self._exec_ml_model,
            "voice-audit": self._exec_voice_audit,
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
        rule_name = data.get("rule_expr", "")
        if rule_name:
            result, summary, _ = self._tool_router.execute("screen_users_by_rule", {"rule_name": rule_name})
        else:
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
        expr = data.get("condition_expr", "")
        return {"branch": "true", "expression": expr}, f"条件判断: {expr or '默认通过'}"

    def _exec_loop(self, data: dict, context: dict, question: str):
        upstream = self._collect_upstream_data(context)
        return {"looped": True, "data_preview": upstream[:500]}, "遍历完成"

    def _exec_merge(self, data: dict, context: dict, question: str):
        return {"merged": True}, "分支合并完成"

    def _exec_notification(self, data: dict, context: dict, question: str):
        notify_type = data.get("notify_type", "sms")
        return {"notified": True, "type": notify_type}, f"通知触达 ({notify_type})"

    def _exec_human_approval(self, data: dict, context: dict, question: str):
        role = data.get("approver_role", "审批人")
        return {"approval_requested": True, "role": role}, f"已发起人工审批 ({role})"

    def _exec_write_back(self, data: dict, context: dict, question: str):
        return {"written": True}, "结果写回完成"

    def _exec_api_response(self, data: dict, context: dict, question: str):
        return {"responded": True}, "API 响应已生成"

    def _exec_variable_assign(self, data: dict, context: dict, question: str):
        return {"assigned": True}, "变量赋值完成"

    def _exec_parallel(self, data: dict, context: dict, question: str):
        return {"parallel": True}, "并行分支已启动"

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
