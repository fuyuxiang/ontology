from .base import BaseActionExecutor, ExecutionResult


class CallFunctionExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        function_name = type_config.get("function_name") or type_config.get("callable_name") or type_config.get("function_id", "")
        param_mapping = type_config.get("param_mapping", {})
        mapped_params = {k: params.get(v, v) for k, v in param_mapping.items()} if param_mapping else params

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would call function {function_name}",
                output={"function_name": function_name, "params": mapped_params},
            )

        from app.database import SessionLocal
        from app.services.function_runtime.executor import FunctionRuntimeExecutor
        from app.services.function_runtime.registry import FunctionRegistry
        from app.services.function_runtime.sandbox import UnifiedSandbox

        db = SessionLocal()
        try:
            registry = FunctionRegistry(db)
            registry.sync_from_db()
            sandbox = UnifiedSandbox()
            runtime = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=db)
            result = runtime.execute(function_name, mapped_params)
            return ExecutionResult(
                success=result.success,
                message=result.error or "执行成功",
                output={"function_name": function_name, "result": result.result},
            )
        finally:
            db.close()

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "function_name": {"type": "string", "required": True, "description": "函数 callable_name"},
            "param_mapping": {"type": "object", "required": False, "description": "参数映射：{函数参数名: 行动参数名}"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "调用函数"

    @classmethod
    def get_description(cls) -> str:
        return "执行已注册的逻辑/动作函数"
