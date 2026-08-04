"""
内置 Skill 执行器 — 通用调度层。

- 注册表：SKILL_REGISTRY / SKILL_STREAM_REGISTRY
- 执行入口：execute_skill / execute_skill_stream / has_skill_stream
- 生成型 skill：execute_generated_skill（沙箱运行用户定义的 tool 代码）
- 工具桥接：execute_skill_tool_call / build_ontology_tools

平台层不内置任何业务实现。具体业务能力应由用户在前端「函数定义 / 动作定义」页
创建 OntologyFunction / EntityAction，或在「Skill 构建」里生成 Skill 后再执行。
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SKILL_REGISTRY: dict[str, Any] = {}
SKILL_STREAM_REGISTRY: dict[str, Any] = {}


def register_skill(code_ref: str):
    def decorator(fn):
        SKILL_REGISTRY[code_ref] = fn
        return fn
    return decorator


def register_skill_stream(code_ref: str):
    def decorator(fn):
        SKILL_STREAM_REGISTRY[code_ref] = fn
        return fn
    return decorator


def has_skill_stream(code_ref: str) -> bool:
    return code_ref in SKILL_STREAM_REGISTRY


def execute_skill(code_ref: str, params: dict, db: Session) -> dict:
    fn = SKILL_REGISTRY.get(code_ref)
    if fn:
        try:
            return fn(params, db)
        except Exception as e:
            logger.error(f"Skill {code_ref} 执行失败: {e}")
            return {"success": False, "summary": f"执行失败: {e}", "data": {}}
    from app.models.skill import Skill
    skill = db.query(Skill).filter(
        Skill.code_ref == code_ref,
        Skill.skill_type == "generated",
        Skill.status == "active",
    ).first()
    if skill:
        return execute_generated_skill(skill, params, db)
    return {"success": False, "summary": f"未知 skill: {code_ref}", "data": {}}


def execute_skill_stream(code_ref: str, params: dict, db: Session):
    fn = SKILL_STREAM_REGISTRY.get(code_ref)
    if not fn:
        result = execute_skill(code_ref, params, db)
        yield {
            "step": "result", "status": "complete",
            "summary": result.get("summary", ""),
            "data": result.get("data", {}),
        }
        return
    try:
        yield from fn(params, db)
    except Exception as e:
        logger.error(f"Skill stream {code_ref} 执行失败: {e}")
        yield {"step": "error", "status": "error", "message": str(e)}


def execute_skill_tool_call(tool_type: str, tool_config: dict, params: dict, db: Session) -> dict:
    """Execute a function tool referenced by a skill."""
    if tool_type == "function":
        from app.services.function_executor import FunctionExecutor
        callable_name = tool_config.get("callable_name")
        func_id = tool_config.get("function_id")
        executor = FunctionExecutor(db)
        if callable_name:
            result = executor.execute_by_callable_name(callable_name, params)
        elif func_id:
            from app.models.function import OntologyFunction
            func = db.get(OntologyFunction, func_id)
            if not func:
                return {"success": False, "summary": f"Function {func_id} not found", "data": {}}
            result = executor.execute(func, params)
        else:
            return {"success": False, "summary": "Missing callable_name or function_id", "data": {}}

        return {
            "success": result.success,
            "summary": f"Function returned: {result.value}" if result.success else f"Error: {result.error}",
            "data": {"value": result.value, "execution_ms": result.execution_ms},
        }

    return {"success": False, "summary": f"Unknown tool type: {tool_type}", "data": {}}


def execute_generated_skill(skill, params: dict, db) -> dict:
    """Execute a generated skill by running its tools in sandbox."""
    from app.models.skill_tool import SkillTool
    from app.services.skill_sandbox import execute_in_sandbox

    tools = db.query(SkillTool).filter(SkillTool.skill_id == skill.id).all()
    results = {}
    for tool in tools:
        try:
            output = execute_in_sandbox(tool.code, tool.name, params)
            results[tool.name] = {"success": True, "output": output}
        except Exception as e:
            results[tool.name] = {"success": False, "error": str(e)}

    return {
        "success": all(r["success"] for r in results.values()),
        "summary": f"Executed {len(tools)} tools",
        "data": results,
    }


def build_ontology_tools(skill_id: str, db: Session) -> list[dict]:
    """Build LLM tool definitions from skill's ontology component refs."""
    from app.models.skill_tool_ref import SkillToolRef
    from app.models.version_components import (
        OntologyVersionAction,
        OntologyVersionFunction,
    )

    refs = db.query(SkillToolRef).filter(SkillToolRef.skill_id == skill_id).all()
    tools = []

    for ref in refs:
        if ref.ref_type == "function":
            comp = db.query(OntologyVersionFunction).filter(
                OntologyVersionFunction.id == ref.ref_id
            ).first()
            if not comp:
                continue
            params_list = comp.input_schema or []
        elif ref.ref_type == "action":
            comp = db.query(OntologyVersionAction).filter(
                OntologyVersionAction.id == ref.ref_id
            ).first()
            if not comp:
                continue
            params_list = comp.parameters_json or []
        else:
            continue

        properties = {}
        required = []
        for p in params_list:
            prop_type = _map_type(p.get("type", "string"))
            properties[p["name"]] = {"type": prop_type}
            if p.get("description"):
                properties[p["name"]]["description"] = p["description"]
            if p.get("required"):
                required.append(p["name"])

        tools.append({
            "type": "function",
            "function": {
                "name": ref.alias,
                "description": ref.description or getattr(comp, "description", "") or comp.name,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
            "_meta": {
                "ref_type": ref.ref_type,
                "ref_id": ref.ref_id,
            },
        })

    return tools


def _map_type(t: str) -> str:
    mapping = {
        "string": "string", "text": "string",
        "number": "number", "integer": "integer", "int": "integer",
        "float": "number", "decimal": "number",
        "boolean": "boolean", "bool": "boolean",
        "date": "string", "datetime": "string",
    }
    return mapping.get(t.lower(), "string")
