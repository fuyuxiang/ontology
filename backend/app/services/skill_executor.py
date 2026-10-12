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


def execute_skill_tool_call(tool_type: str, tool_config: dict, params: dict, db: Session, *, context=None, user=None,
                            version_id=None, action_mode="simulation") -> dict:
    """Execute a function tool referenced by a skill."""
    if tool_type == "function":
        from app.services.function_executor import FunctionExecutor
        from app.services.function_runtime.models import ExecContext
        context = context or ExecContext(ontology_id=tool_config.get("ontology_id"),
            entity_ids=frozenset(tool_config["entity_ids"]) if tool_config.get("entity_ids") is not None else None,
            user=user, version_id=version_id, action_mode=action_mode)
        callable_name = tool_config.get("callable_name")
        func_id = tool_config.get("function_id")
        executor = FunctionExecutor(db)
        if context.version_id:
            from app.models.version_components import OntologyVersionFunction
            functions = db.query(OntologyVersionFunction).filter_by(version_id=context.version_id).all()
            matches = [f for f in functions if (callable_name and f.callable_name == callable_name)
                       or (func_id and f.source_function_id == func_id)]
            if len(matches) != 1:
                return {"success": False, "summary": "Function is not in the fixed release", "data": {}}
            result = executor.execute_snapshot(matches[0], params, context=context)
        elif callable_name:
            result = executor.execute_by_callable_name(callable_name, params, context.ontology_id, context=context)
        elif func_id:
            from app.models.function import OntologyFunction
            func = db.get(OntologyFunction, func_id)
            if not func:
                return {"success": False, "summary": f"Function {func_id} not found", "data": {}}
            result = executor.execute(func, params, context=context)
        else:
            return {"success": False, "summary": "Missing callable_name or function_id", "data": {}}

        summary = f"Function returned: {result.value}" if result.success else f"Error: {result.error}"
        if result.requested_write:
            summary = "Write preview; execution stopped before the write" if result.outcome == "simulated" else "Write awaiting confirmation; execution stopped before the write"
        return {
            "success": result.success,
            "summary": summary,
            "data": {"value": result.value, "execution_ms": result.execution_ms,
                     "requested_write": result.requested_write, "committed_writes": result.committed_writes},
            "outcome": result.outcome,
            "simulated": result.outcome == "simulated",
            "execution_complete": not bool(result.requested_write),
        }

    return {"success": False, "summary": f"Unknown tool type: {tool_type}", "data": {}}


def execute_generated_skill(skill, params: dict, db) -> dict:
    """Execute a generated skill by running its tools in sandbox."""
    from app.models.skill_tool import SkillTool
    from app.services.skill_sandbox import execute_in_sandbox

    tools = db.query(SkillTool).filter(SkillTool.skill_id == skill.id).all()
    if not tools:
        return {"success": False, "summary": "Skill has no executable tools", "data": {}}
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
