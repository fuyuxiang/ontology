import ast
import contextlib
import io
import signal

from .base import BaseActionExecutor, ExecutionResult

SAFE_BUILTINS = {
    "print": print, "len": len, "str": str, "int": int, "float": float,
    "bool": bool, "list": list, "dict": dict, "tuple": tuple, "set": set,
    "range": range, "enumerate": enumerate, "zip": zip, "map": map,
    "filter": filter, "sorted": sorted, "min": min, "max": max,
    "sum": sum, "abs": abs, "round": round, "isinstance": isinstance,
    "type": type, "hasattr": hasattr, "getattr": getattr,
    "True": True, "False": False, "None": None,
}

EXEC_TIMEOUT_SECONDS = 5


def _check_imports(script: str) -> str | None:
    try:
        tree = ast.parse(script)
    except SyntaxError as e:
        return f"语法错误: {e}"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return f"禁止使用 import 语句 (line {node.lineno})"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "__import__":
                return f"禁止使用 __import__ (line {node.lineno})"
    return None


class _TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _TimeoutError("脚本执行超时")


class CustomScriptExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        script = type_config.get("script", "")

        if dry_run:
            return ExecutionResult(
                success=True,
                message="[Dry Run] Would execute custom Python script",
                output={"script_length": len(script), "params": params},
            )

        violation = _check_imports(script)
        if violation:
            return ExecutionResult(
                success=False,
                message=f"脚本安全检查失败: {violation}",
                output={"error": violation},
            )

        stdout_capture = io.StringIO()
        local_vars = {"params": params, "result": {}}
        sandbox_globals = {"__builtins__": SAFE_BUILTINS}

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(EXEC_TIMEOUT_SECONDS)
        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(script, sandbox_globals, local_vars)
            return ExecutionResult(
                success=True,
                message="Script executed successfully",
                output=local_vars.get("result", {}),
            )
        except _TimeoutError:
            return ExecutionResult(
                success=False,
                message=f"脚本执行超时 (>{EXEC_TIMEOUT_SECONDS}s)",
                output={"error": "timeout"},
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Script error: {str(e)}",
                output={"error": str(e), "stdout": stdout_capture.getvalue()},
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

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
