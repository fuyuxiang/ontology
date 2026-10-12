"""Validate declared parameters and execute the exact reviewed action snapshot."""
import copy
import json
from datetime import date, datetime

from app.models.function import OntologyFunction
from app.services.action_executors import run_executor_sync
from app.services.action_executors.base import ExecutionResult
from app.services.function_executor import FunctionExecutor
from app.services.function_runtime.models import ExecContext


def validate_parameters(definitions, values):
    if not isinstance(values, dict):
        raise ValueError("能力参数必须为对象")
    params = copy.deepcopy(values)
    predicates = {
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "int": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "float": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "bool": lambda x: isinstance(x, bool),
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "json": lambda x: isinstance(x, (dict, list)),
        "date": lambda x: isinstance(x, str),
        "datetime": lambda x: isinstance(x, str),
    }
    for definition in definitions or []:
        if not isinstance(definition, dict) or not definition.get("name"):
            continue
        key = definition["name"]
        if key not in params:
            if "default" in definition:
                params[key] = copy.deepcopy(definition["default"])
            elif "default_value" in definition and definition["default_value"] is not None:
                default = copy.deepcopy(definition["default_value"])
                if isinstance(default, str) and definition.get("type") in {
                        "integer", "int", "number", "float", "boolean", "bool", "object", "array", "json"}:
                    try:
                        default = json.loads(default)
                    except ValueError:
                        raise ValueError(f"参数 {key} 的 default_value 不是有效类型值") from None
                params[key] = default
            elif definition.get("required"):
                raise ValueError(f"缺少必填参数：{key}")
            else:
                continue
        value = params[key]
        predicate = predicates.get(definition.get("type"))
        if predicate and not predicate(value):
            raise ValueError(f"参数 {key} 类型应为 {definition['type']}")
        if definition.get("type") in {"date", "datetime"}:
            try:
                (date if definition["type"] == "date" else datetime).fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise ValueError(f"参数 {key} 必须为 ISO {definition['type']} 字符串") from None
        if definition.get("enum") and value not in definition["enum"]:
            raise ValueError(f"参数 {key} 不在允许值范围内")
    return params


def action_execution_context(action, *, user=None, dry_run=False):
    scope = action.get("_runtime_scope") or {}
    ids = scope.get("entity_ids")
    if ids is None and action.get("entity_id"):
        ids = [action["entity_id"]]
    return ExecContext(ontology_id=action.get("ontology_id"), version_id=action.get("version_id"),
        entity_ids=frozenset(ids) if ids is not None else None,
        function_ids=frozenset(scope["function_ids"]) if scope.get("function_ids") is not None else None,
        allowed_tools=frozenset(scope["allowed_tools"]) if scope.get("allowed_tools") is not None else None,
        user=user, action_mode="simulation" if dry_run else "execute")


def execute_action_snapshot(db, action, params, *, dry_run, context=None):
    context = context or action_execution_context(action, dry_run=dry_run)
    params = validate_parameters(action.get("parameters_json"), params)
    if action["action_type"] == "call_function":
        function = action.get("function_snapshot")
        if not function:
            return ExecutionResult(False, "行动调用的函数不在当前已发布授权范围内")
        mapping = (action.get("type_config") or {}).get("param_mapping") or {}
        mapped = {k: params.get(v, v) for k, v in mapping.items()} if mapping else params
        mapped = validate_parameters(function.get("input_schema"), mapped)
        if dry_run:
            return ExecutionResult(True, "模拟调用固定版本函数", {"function_id": function["id"], "params": mapped})
        result = FunctionExecutor(db).execute_snapshot(function, mapped, version_id=function.get("version_id"), context=context)
        return ExecutionResult(result.success, result.error or "执行成功",
                               {"function_id": function["id"], "result": result.value, "outcome": result.outcome,
                                "committed_writes": result.committed_writes})
    config = copy.deepcopy(action.get("type_config") or {})
    if action.get("version_entity_id"):
        config["_version_entity_id"] = action["version_entity_id"]
    if action["action_type"] in {"custom_script", "call_function"}:
        config["_exec_context"] = context
    return run_executor_sync(action["action_type"], config, params, dry_run=dry_run, db=db)
