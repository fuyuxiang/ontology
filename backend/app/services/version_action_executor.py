"""Execute immutable published actions through the common executors."""
import asyncio
from types import SimpleNamespace
from app.models.version_components import OntologyVersionFunction
from app.services.function_executor import FunctionExecutor
from app.services.action_executors import get_executor
from app.services.action_executors.base import ExecutionResult
from app.services.agent_actions import validate_parameters


async def execute_version_action(db, action, params, dry_run=False, *, context=None):
    restricted = isinstance(action, dict)
    if restricted:
        action = SimpleNamespace(**action)
    params = validate_parameters(action.parameters_json, params)
    config = dict(action.type_config or {})
    config["_version_entity_id"] = action.version_entity_id
    config["version_id"] = action.version_id
    if action.action_type == "call_function":
        if restricted:
            frozen = getattr(action, "function_snapshot", None)
            if not frozen:
                return ExecutionResult(False, "行动调用的函数不在当前已发布授权范围内")
            mapping = config.get("param_mapping") or {}
            mapped = {k: params.get(v, v) for k, v in mapping.items()} if mapping else params
            if dry_run:
                return ExecutionResult(True, "模拟调用固定版本函数", {"params": mapped})
            result = FunctionExecutor(db).execute_snapshot(frozen, mapped, version_id=action.version_id, context=context)
            return ExecutionResult(result.success, result.error or "执行成功", {"result": result.value, "outcome": result.outcome,
                "committed_writes": result.committed_writes})
        name = config.get("function_name") or config.get("callable_name") or config.get("function_id")
        functions = db.query(OntologyVersionFunction).filter_by(version_id=action.version_id).all()
        matches = [fn for fn in functions if name in (fn.callable_name, fn.name, fn.source_function_id)]
        if len(matches) != 1:
            return ExecutionResult(False, "行动调用的函数不在当前已发布版本中")
        mapping = config.get("param_mapping") or {}
        mapped = {k: params.get(v, v) for k, v in mapping.items()} if mapping else params
        if dry_run:
            return ExecutionResult(True, "模拟调用固定版本函数", {"params": mapped, "function_id": matches[0].source_function_id})
        result = FunctionExecutor(db).execute_snapshot(matches[0], mapped, context=context)
        return ExecutionResult(result.success, result.error or "执行成功", {"result": result.value, "outcome": result.outcome,
            "committed_writes": result.committed_writes})
    if action.action_type == "custom_script" and context is not None:
        config["_exec_context"] = context
    return await get_executor(action.action_type, db=db).execute(config, params, dry_run)


def run_version_action_sync(db, action, params, dry_run=False):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(execute_version_action(db, action, params, dry_run))
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(execute_version_action(db, action, params, dry_run))).result()
