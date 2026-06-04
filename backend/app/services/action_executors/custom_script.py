import io
import contextlib
from .base import BaseActionExecutor, ExecutionResult


class CustomScriptExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        script = type_config.get("script", "")

        if dry_run:
            return ExecutionResult(
                success=True,
                message="[Dry Run] Would execute custom Python script",
                output={"script_length": len(script), "params": params},
            )

        stdout_capture = io.StringIO()
        local_vars = {"params": params, "result": {}}

        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(script, {"__builtins__": __builtins__}, local_vars)
            return ExecutionResult(
                success=True,
                message="Script executed successfully",
                output=local_vars.get("result", {}),
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Script error: {str(e)}",
                output={"error": str(e), "stdout": stdout_capture.getvalue()},
            )

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "script": {"type": "string", "required": True, "description": "Python 脚本内容，通过 params 字典获取输入，结果写入 result 字典"},
        }

    @classmethod
    def get_label(cls) -> str:
        return "自定义脚本"

    @classmethod
    def get_description(cls) -> str:
        return "运行自定义 Python 脚本"
