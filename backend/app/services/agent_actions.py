"""Validate declared parameters and execute the exact reviewed action snapshot."""
import copy

from app.models.function import OntologyFunction
from app.services.action_executors import run_executor_sync
from app.services.action_executors.base import ExecutionResult
from app.services.function_executor import FunctionExecutor


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
    }
    for definition in definitions or []:
        if not isinstance(definition, dict) or not definition.get("name"):
            continue
        key = definition["name"]
        if key not in params:
            if "default" in definition:
                params[key] = copy.deepcopy(definition["default"])
            elif definition.get("required"):
                raise ValueError(f"缺少必填参数：{key}")
            else:
                continue
        value = params[key]
        predicate = predicates.get(definition.get("type"))
        if predicate and not predicate(value):
            raise ValueError(f"参数 {key} 类型应为 {definition['type']}")
        if definition.get("enum") and value not in definition["enum"]:
            raise ValueError(f"参数 {key} 不在允许值范围内")
    return params


def execute_action_snapshot(db, action, params, *, dry_run):
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
        result = FunctionExecutor(db).execute(OntologyFunction(**function), mapped)
        return ExecutionResult(result.success, result.error or "执行成功",
                               {"function_id": function["id"], "result": result.value})
    return run_executor_sync(action["action_type"], action.get("type_config") or {}, params, dry_run=dry_run)
