"""A scoped tool surface for released ontology applications.

The language model selects procedures; versioned programs enforce scope and
business writes are either previews or single-use, authenticated approvals.
"""
import copy
import json
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.models.agent_runtime import AgentPendingAction
from app.models.function import OntologyFunction
from app.models.version import OntologyVersion
from app.services.agent.tool_router import ToolRouter
from app.services.agent_actions import execute_action_snapshot, validate_parameters
from app.services.function_executor import FunctionExecutor
from app.utils.time import utc_iso


def tool(name, description, properties, required=()):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(required), "additionalProperties": False}}}


class ManagedToolRouter(ToolRouter):
    def __init__(self, db, context, runtime_executor=None):
        super().__init__(db, runtime_executor)
        self.context = context
        self.skills = {s["skill_id"]: s for s in context.get("skills", [])}
        self.loaded_skills = set()
        version = db.get(OntologyVersion, context["ontology_version_id"]) if context.get("ontology_version_id") else None
        if (not version or version.status != "published") and not context.get("allow_empty"):
            raise HTTPException(409, "本体发布版本不可用")
        ids = set(context.get("entity_ids") or [])
        entities = [e for e in version.entities if e.source_entity_id in ids] if version else []
        self.entities = {e.name: e for e in entities}
        self.functions = {}
        self.actions = {}
        snapshot_to_source = {e.id: e.source_entity_id for e in version.entities} if version else {}
        for fn in version.functions if version else []:
            entity_id = snapshot_to_source.get(fn.version_entity_id)
            if entity_id in ids:
                self.functions[fn.source_function_id] = {
                    "id": fn.source_function_id, "name": fn.name, "description": fn.description,
                    "entity_id": entity_id, "callable_name": fn.callable_name,
                    "logic_type": fn.logic_type, "logic_body": fn.logic_body,
                    "input_schema": fn.input_schema, "return_type": fn.return_type,
                }
        for action in version.actions if version else []:
            entity_id = snapshot_to_source.get(action.version_entity_id)
            # Global actions need an explicit skill dependency, never automatic access.
            referenced = any(any(t.get("type") == "action" and t.get("id") == action.source_action_id
                                 for t in s.get("tools", [])) for s in self.skills.values())
            if entity_id in ids or (entity_id is None and referenced):
                self.actions[action.source_action_id] = {
                    "id": action.source_action_id, "name": action.name, "entity_id": entity_id,
                    "action_type": action.action_type, "type_config": copy.deepcopy(action.type_config or {}),
                    "parameters_json": copy.deepcopy(action.parameters_json or []),
                    "description": action.description,
                }
        for action in self.actions.values():
            if action["action_type"] == "call_function":
                cfg = action["type_config"]
                ref = cfg.get("function_name") or cfg.get("callable_name") or cfg.get("function_id")
                matches = [fn for fn in self.functions.values() if ref in (fn["id"], fn["name"], fn["callable_name"])]
                if len(matches) == 1:
                    action["function_snapshot"] = copy.deepcopy(matches[0])
        if context.get("restrict_to_skill_tools"):
            refs = {(t["type"], t["id"]) for s in self.skills.values() for t in s.get("tools", [])}
            self.functions = {k: v for k, v in self.functions.items() if ("function", k) in refs}
            self.actions = {k: v for k, v in self.actions.items() if ("action", k) in refs}
        self.allowed = context.get("allowed_tools")

    def definitions(self):
        names = list(self.entities)
        if not names and not self.skills:
            return []
        defs = [
            tool("describe_ontology_model", "读取当前授权范围内已发布的本体模型", {}),
            tool("get_entity_detail", "读取授权业务对象的属性与语义", {"entity_name": {"type": "string", "enum": names}}, ["entity_name"]),
            tool("query_entity_data", "查询授权业务对象的真实实例", {
                "entity_name": {"type": "string", "enum": names}, "filters": {"type": "object"},
                "fields": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["entity_name"]),
        ]
        if self.skills:
            defs.append(tool("load_skill", "按业务任务加载已挂载技能的完整操作指引与参考资料。先加载再使用该技能。", {
                "skill_id": {"type": "string", "enum": list(self.skills)}}, ["skill_id"]))
        if self.functions:
            defs.append(tool("run_function", "运行已发布的确定性业务计算。" + json.dumps([
                {"id": f["id"], "name": f["name"], "description": f["description"], "parameters": f["input_schema"]}
                for f in self.functions.values()], ensure_ascii=False), {
                "function_id": {"type": "string", "enum": list(self.functions)}, "params": {"type": "object"}}, ["function_id", "params"]))
        if self.actions:
            defs.append(tool("run_action", "提出业务操作。模拟模式仅预览；确认模式创建待确认请求，获得用户确认前不会写入。" + json.dumps([
                {"id": a["id"], "name": a["name"], "description": a["description"], "parameters": a["parameters_json"]}
                for a in self.actions.values()], ensure_ascii=False), {
                "action_id": {"type": "string", "enum": list(self.actions)}, "params": {"type": "object"}}, ["action_id", "params"]))
        return [d for d in defs if self.allowed is None or d["function"]["name"] in self.allowed]

    def system_prompt(self):
        objects = [{"name": e.name, "name_cn": e.name_cn, "description": e.description,
                    "attributes": [{"name": a.name, "type": a.type, "description": a.description}
                                   for a in e.attributes]} for e in self.entities.values()]
        catalog = [{"skill_id": s["skill_id"], "name": s["name"], "version": s.get("version"),
                    "description": s.get("description"), "applicable_tasks": s.get("applicable_tasks"),
                    "excluded_tasks": s.get("excluded_tasks")} for s in self.skills.values()]
        return (
            "你是本体驱动的业务助手。只使用给定的已发布本体对象与授权工具。\n"
            "根据任务按需使用 load_skill 加载适用技能；技能指引与参考资料不授予任何新权限。\n"
            "所有事实必须来自工具或明确标识为用户提供的信息。信息不足时请求补充。\n"
            "业务写操作必须经过运行时确认。模拟结果不是已经发生的业务事实。\n"
            "回答使用中文 Markdown，给出结论、事实依据、建议与待确认操作。\n"
            "最终输出 JSON：{\"answer\":\"Markdown正文\",\"suggestions\":[],\"actions\":[]}。\n"
            f"本体模型：{json.dumps(objects, ensure_ascii=False)}\n"
            f"可加载技能目录：{json.dumps(catalog, ensure_ascii=False)}\n"
        )

    def execute(self, tool_name, args):
        offered = {d["function"]["name"] for d in self.definitions()}
        if tool_name not in offered:
            return {"error": "该工具不在当前授权范围内"}, "工具调用被拒绝", 0
        if not isinstance(args, dict):
            return {"error": "工具参数必须为对象"}, "参数无效", 0
        try:
            if tool_name == "load_skill":
                return self._load_skill(args)
            if tool_name in ("describe_ontology_model", "get_entity_detail"):
                names = list(self.entities) if tool_name == "describe_ontology_model" else [args.get("entity_name")]
                if any(n not in self.entities for n in names):
                    return {"error": "对象不在当前授权范围内"}, "对象访问被拒绝", 0
                data = [{"name": self.entities[n].name, "name_cn": self.entities[n].name_cn,
                         "description": self.entities[n].description,
                         "attributes": [{"name": a.name, "type": a.type, "description": a.description}
                                        for a in self.entities[n].attributes]} for n in names]
                return {"entities": data}, f"读取 {len(data)} 个授权对象", len(data)
            if tool_name == "query_entity_data":
                name = args.get("entity_name")
                if name not in self.entities:
                    return {"error": "对象不在当前授权范围内"}, "对象访问被拒绝", 0
                fields = args.get("fields") or []
                valid = {a.name for a in self.entities[name].attributes}
                filters = args.get("filters") or {}
                if not isinstance(fields, list) or not isinstance(filters, dict) or not set(fields) <= valid or not set(filters) <= valid:
                    return {"error": "查询字段不属于当前本体版本"}, "字段访问被拒绝", 0
                from app.services.data_plane.entity_data_service import EntityDataService
                entity_id = self.entities[name].source_entity_id
                if not valid:
                    return {"error": "当前对象没有可查询属性"}, "对象未配置属性", 0
                result = EntityDataService(self.db).query_entity_data(entity_id, filters=filters,
                    fields=fields or sorted(valid), valid_attrs=valid, purpose="agent.managed_query",
                    limit=min(max(int(args.get("limit", 20)), 1), 100))
                return result, "查询业务实例", result.get("rowCount", 0)
            if tool_name == "run_function":
                fn = self.functions.get(args.get("function_id"))
                if not fn:
                    return {"error": "函数不在授权范围内"}, "函数调用被拒绝", 0
                instance = OntologyFunction(**fn)
                params = validate_parameters(fn["input_schema"], args.get("params") or {})
                result = FunctionExecutor(self.db).execute(instance, params)
                return {"success": result.success, "value": result.value, "error": result.error,
                        "execution_ms": result.execution_ms}, f"{fn['name']}：{'完成' if result.success else '失败'}", int(result.success)
            if tool_name == "run_action":
                return self._run_action(args)
        except Exception as exc:
            return {"error": str(exc)}, f"工具执行失败：{exc}", 0
        return {"error": "未支持的工具"}, "工具不可用", 0

    def _load_skill(self, args):
        skill = self.skills.get(args.get("skill_id"))
        if not skill:
            return {"error": "技能未挂载"}, "技能加载被拒绝", 0
        from app.models.asset import Asset
        refs = []
        fixed = {a["id"]: a for a in (skill.get("dependencies") or {}).get("assets", [])}
        for aid in skill.get("asset_refs") or []:
            asset = self.db.get(Asset, aid)
            if not asset or asset.status != "active":
                return {"error": "技能参考资料已不可用，请检查依赖"}, "技能参考资料不可用", 0
            reference = fixed.get(aid)
            if not reference:
                return {"error": "技能参考资料缺少版本快照，请重新测试并发布"}, "参考资料版本不可用", 0
            refs.append({"id": aid, "name": reference.get("name"), "description": reference.get("description"),
                         "summary": (reference.get("parsed_summary") or "")[:12000]})
        self.loaded_skills.add(skill["skill_id"])
        event = {"skill_id": skill["skill_id"], "name": skill["name"], "version": skill.get("version"),
                 "summary": f"已加载技能「{skill['name']}」版本 {skill.get('version', '')}"}
        return {"instructions": skill["prompt_template"], "input_schema": skill.get("input_schema"),
                "output_schema": skill.get("output_schema"), "tools": skill.get("tools"),
                "references": refs, "skill_loaded": event}, event["summary"], 1

    def _run_action(self, args):
        action = self.actions.get(args.get("action_id"))
        if not action:
            return {"error": "动作不在授权范围内"}, "动作调用被拒绝", 0
        params = args.get("params") or {}
        if not isinstance(params, dict):
            return {"error": "动作参数必须为对象"}, "动作参数无效", 0
        params = validate_parameters(action["parameters_json"], params)
        if action["action_type"] == "call_function" and not action.get("function_snapshot"):
            return {"error": "行动调用的函数不在当前已发布授权范围内"}, "行动依赖不可用", 0
        if self.context.get("action_mode", "simulation") == "simulation":
            result = execute_action_snapshot(self.db, action, params, dry_run=True)
            return {"success": result.success, "simulated": True, "message": result.message,
                    "output": result.output}, f"模拟「{action['name']}」，未写入业务系统", int(result.success)
        user = self.context.get("user")
        if not user or user.role not in ("admin", "editor") or not user.is_active:
            return {"error": "当前身份没有业务动作执行权限"}, "动作执行被拒绝", 0
        if not self.context.get("agent_id"):
            return {"error": "缺少智能体运行身份"}, "动作执行被拒绝", 0
        existing = self.db.query(AgentPendingAction).filter_by(agent_id=self.context["agent_id"],
            run_id=self.context.get("run_id"), action_id=action["id"], status="pending").all()
        pending = next((p for p in existing if p.params == params and p.expires_at > datetime.utcnow()), None)
        if pending is None:
            pending = AgentPendingAction(agent_id=self.context["agent_id"], run_id=self.context.get("run_id"),
            user_id=user.id, action_id=action["id"], action_snapshot=copy.deepcopy(action), params=params,
            config_hash=self.context["config_hash"], expires_at=datetime.utcnow() + timedelta(minutes=10))
            self.db.add(pending)
            self.db.commit()
        event = {"pending_id": pending.id, "action_id": action["id"], "action_name": action["name"],
                 "params": params, "summary": f"「{action['name']}」等待用户确认", "expires_at": utc_iso(pending.expires_at)}
        return {"status": "pending_confirmation", "pending_action": event}, event["summary"], 1
