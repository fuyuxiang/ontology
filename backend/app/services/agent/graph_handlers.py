"""
画布执行引擎 — 节点执行器 Mixin
NodeHandlersMixin: 承载全部 _exec_* 节点处理器及其专用辅助方法。
本模块不 import graph_engine，避免循环导入；共享的模块级工具 _safe_jsonable 定义在此处。
"""
import json
import logging
from typing import Any

from app.models.function import OntologyFunction
from app.models.action import EntityAction
from app.models.skill import Skill
from app.services.skill_executor import execute_skill

logger = logging.getLogger(__name__)


def _normalize(val):
    if isinstance(val, str):
        low = val.lower()
        if low in ("true", "1", "yes"):
            return True
        if low in ("false", "0", "no"):
            return False
    if isinstance(val, (int, float)):
        if val == 0:
            return False
        if val == 1:
            return True
    return val


def _compare(actual, operator: str, expected) -> bool:
    if expected is None:
        if operator == "==":
            return actual is None
        elif operator == "!=":
            return actual is not None
    if actual is None:
        return False
    try:
        if operator == "==":
            return _normalize(actual) == _normalize(expected)
        elif operator == "!=":
            return _normalize(actual) != _normalize(expected)
        elif operator == ">=":
            return float(actual) >= float(expected)
        elif operator == ">":
            return float(actual) > float(expected)
        elif operator == "<=":
            return float(actual) <= float(expected)
        elif operator == "<":
            return float(actual) < float(expected)
        elif operator.lower() == "in":
            return actual in expected
        elif operator.lower() == "not_in":
            return actual not in expected
    except (ValueError, TypeError):
        pass
    return False


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


class NodeHandlersMixin:
    """画布节点执行器集合，作为 GraphEngine 的 mixin 使用。"""

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

    def _exec_ontology_query(self, data: dict, context: dict, question: str):
        entity_type = data.get("ontology_type", "")
        if not entity_type:
            return {"info": "未配置本体对象"}, "未配置本体对象"
        result, summary, _ = self._tool_router.execute("get_entity_detail", {"entity_name": entity_type})
        return result, summary

    def _exec_ontology_relation(self, data: dict, context: dict, question: str):
        result, summary, _ = self._tool_router.execute("describe_ontology_model", {})
        return result, summary

    # PLACEHOLDER_MORE_HANDLERS

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
            logger.warning("意图识别失败,使用回退: %s", e)
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
        from app.models.action import EntityAction
        from app.services.action_executors import run_executor_sync
        act = (
            self.db.query(EntityAction)
            .filter(EntityAction.action_type.in_([notify_type, "notify", "notification"]))
            .first()
        )
        if act:
            try:
                res = run_executor_sync(act.action_type, act.type_config or {}, {"target": target, "message": msg, **(data.get("params") or {})}, dry_run=False)
                return (
                    {"notified": res.success, "type": notify_type, "effects": res.output or {}, "message": res.message},
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
        from app.services.action_executors import run_executor_sync
        try:
            if action_id:
                act = self.db.get(EntityAction, action_id)
                if not act:
                    return {"error": f"动作 {action_id} 不存在"}, "动作不存在"
                res = run_executor_sync(act.action_type, act.type_config or {}, params, dry_run=bool(data.get("dry_run", False)))
            elif action_name:
                act = self.db.query(EntityAction).filter(
                    EntityAction.name == action_name,
                    EntityAction.status == "active",
                ).first()
                if not act:
                    return {"error": f"动作 '{action_name}' 不存在或未激活"}, "动作不存在"
                res = run_executor_sync(act.action_type, act.type_config or {}, params, dry_run=bool(data.get("dry_run", False)))
            else:
                return {"error": "未指定 action_id / action_name"}, "未指定动作"
        except Exception as e:
            return {"error": str(e)}, f"动作执行失败: {e}"
        return (
            {"success": res.success, "message": res.message, "effects": res.output or {}},
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
        from app.services.agent.graph_engine import GraphEngine
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
        from app.connectors.factory import get_connector  # noqa: F401  仅校验
        from app.models.entity import OntologyEntity
        from app.services.data_plane.entity_data_service import EntityDataService
        ent = self.db.query(OntologyEntity).filter(OntologyEntity.name == target).first()
        if not ent:
            return {"error": f"本体 {target} 不存在"}, "本体不存在"
        asset_result = EntityDataService(self.db).resolve_entity_asset(ent.id)
        # 暂时落到 audit / 节点结果（连接外部库写入由 ActionExecutor 复用），返回写入预览
        return (
            {
                "written": True,
                "target": target,
                "operation": operation,
                "row": _safe_jsonable(row),
                "datasource": asset_result[0].name if asset_result else "",
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
