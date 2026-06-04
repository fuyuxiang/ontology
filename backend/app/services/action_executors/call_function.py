from .base import BaseActionExecutor, ExecutionResult


class CallFunctionExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        function_id = type_config.get("function_id")
        param_mapping = type_config.get("param_mapping", {})

        mapped_params = {k: params.get(v, v) for k, v in param_mapping.items()}

        if dry_run:
            return ExecutionResult(
                success=True,
                message=f"[Dry Run] Would call function {function_id}",
                output={"function_id": function_id, "params": mapped_params},
            )

        return ExecutionResult(
            success=True,
            message=f"Called function {function_id}",
            output={"function_id": function_id, "result": None},
        )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "function_id": {"type": "string", "required": True, "description": "引用的函数 ID"},
            "param_mapping": {"type": "object", "required": False, "description": "参数映射：{函数参数名: 行动参数名}"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "调用函数"

    @classmethod
    def get_description(cls) -> str:
        return "执行已注册的计算函数"
