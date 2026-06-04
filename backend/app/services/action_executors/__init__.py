from .base import BaseActionExecutor, ExecutionResult
from .api_call import ApiCallExecutor
from .sql_exec import SqlExecExecutor
from .modify_attribute import ModifyAttributeExecutor
from .notification import NotificationExecutor
from .call_function import CallFunctionExecutor
from .custom_script import CustomScriptExecutor

EXECUTOR_REGISTRY: dict[str, type[BaseActionExecutor]] = {
    "api_call": ApiCallExecutor,
    "sql_exec": SqlExecExecutor,
    "modify_attribute": ModifyAttributeExecutor,
    "notification": NotificationExecutor,
    "call_function": CallFunctionExecutor,
    "custom_script": CustomScriptExecutor,
}


def get_executor(action_type: str) -> BaseActionExecutor:
    executor_cls = EXECUTOR_REGISTRY.get(action_type)
    if not executor_cls:
        raise ValueError(f"Unknown action type: {action_type}")
    return executor_cls()


def get_all_type_info() -> list[dict]:
    result = []
    for type_key, cls in EXECUTOR_REGISTRY.items():
        result.append({
            "type_key": type_key,
            "label": cls.get_label(),
            "description": cls.get_description(),
            "config_schema": cls.get_config_schema(),
        })
    return result
