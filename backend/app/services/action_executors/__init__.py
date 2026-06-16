import asyncio

from .api_call import ApiCallExecutor
from .base import BaseActionExecutor, ExecutionResult
from .call_function import CallFunctionExecutor
from .custom_script import CustomScriptExecutor
from .modify_attribute import ModifyAttributeExecutor
from .notification import NotificationExecutor
from .sql_exec import SqlExecExecutor

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


def run_executor_sync(action_type: str, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
    """Synchronous wrapper for executing an action in a sync context."""
    executor = get_executor(action_type)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, executor.execute(type_config, params, dry_run))
                return future.result()
        else:
            return loop.run_until_complete(executor.execute(type_config, params, dry_run))
    except RuntimeError:
        return asyncio.run(executor.execute(type_config, params, dry_run))
