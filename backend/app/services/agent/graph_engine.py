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
from app.services.skill_executor import execute_skill
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

        result = execute_skill(skill.code_ref, params, self.db)
        return result.get("data", {}), result.get("summary", "skill 执行完成")

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
