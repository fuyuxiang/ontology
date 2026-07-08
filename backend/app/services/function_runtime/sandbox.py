"""UnifiedSandbox: AST-based code validator and restricted execution environment."""
from __future__ import annotations

import ast
import logging
import signal
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


FORBIDDEN_IMPORTS = frozenset([
    "os", "sys", "subprocess", "shutil", "socket", "ctypes",
    "importlib", "pickle", "shelve", "multiprocessing", "threading",
    "signal", "pty", "fcntl", "resource", "tempfile", "glob",
    "pathlib", "io",
])

ALLOWED_IMPORTS = frozenset([
    "json", "re", "datetime", "math", "decimal", "collections",
    "typing", "functools", "itertools", "statistics", "copy", "dataclasses",
    "ontology_runtime",
])

FORBIDDEN_CALLS = frozenset([
    "open", "eval", "exec", "__import__", "compile",
    "globals", "locals", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
])

# Dunder attributes that are safe to access (common Python protocols)
ALLOWED_DUNDERS = frozenset([
    "__init__", "__str__", "__repr__", "__len__", "__iter__",
    "__next__", "__getitem__", "__setitem__", "__contains__",
    "__eq__", "__ne__", "__lt__", "__gt__", "__le__", "__ge__",
    "__hash__", "__bool__",
])

SAFE_BUILTINS = {
    "abs": abs, "max": max, "min": min, "round": round, "len": len,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "range": range, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "sorted": sorted, "reversed": reversed,
    "isinstance": isinstance, "print": print, "sum": sum,
    "True": True, "False": False, "None": None,
    "type": type, "hasattr": hasattr,
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


class _SandboxTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _SandboxTimeout("执行超时")


class UnifiedSandbox:
    """AST-based code validator and restricted execution environment."""

    def validate(self, code: str) -> ValidationResult:
        """Validate code via AST inspection: check imports and forbidden calls."""
        errors: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(valid=False, errors=[f"语法错误: {e}"])

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split(".")[0]
                    if mod in FORBIDDEN_IMPORTS:
                        errors.append(f"禁止导入模块: {mod} (line {node.lineno})")
                    elif mod not in ALLOWED_IMPORTS:
                        errors.append(f"不允许的模块: {mod} (line {node.lineno})")

            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[0]
                if mod in FORBIDDEN_IMPORTS:
                    errors.append(f"禁止导入模块: {mod} (line {node.lineno})")
                elif mod not in ALLOWED_IMPORTS:
                    errors.append(f"不允许的模块: {mod} (line {node.lineno})")

            elif isinstance(node, ast.Attribute):
                attr = node.attr
                if attr.startswith("__") and attr.endswith("__") and attr not in ALLOWED_DUNDERS:
                    errors.append(f"禁止访问 dunder 属性: {attr} (line {node.lineno})")

            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    errors.append(f"禁止调用: {node.func.id} (line {node.lineno})")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def execute(
        self, code: str, func_name: str, namespace: dict, timeout: int = 30
    ) -> Any:
        """Execute a function in a sandboxed environment with timeout."""
        validation = self.validate(code)
        if not validation.valid:
            raise ValueError(f"代码校验失败: {'; '.join(validation.errors)}")

        # Pre-import allowed modules
        allowed_modules = {}
        for mod in ALLOWED_IMPORTS:
            if _try_import(mod):
                allowed_modules[mod] = __import__(mod)

        # Build ontology_runtime shim (provides Function decorator and call_function)
        ontology_shim = _build_ontology_runtime_shim(namespace.get("call_function"))
        allowed_modules["ontology_runtime"] = ontology_shim

        # Build sandbox globals with restricted builtins
        def _safe_import(name, *args, **kwargs):
            top = name.split(".")[0]
            if top not in ALLOWED_IMPORTS:
                raise ImportError(f"不允许导入模块: {name}")
            if top == "ontology_runtime":
                return ontology_shim
            return __import__(name, *args, **kwargs)

        builtins = SAFE_BUILTINS.copy()
        builtins["__import__"] = _safe_import

        sandbox_globals: dict[str, Any] = {"__builtins__": builtins}
        sandbox_globals.update(allowed_modules)
        # Inject namespace items (call_function, etc.) into execution scope
        sandbox_globals.update(namespace)

        old_handler = None
        use_alarm = True
        try:
            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
        except ValueError:
            # Not in main thread — SIGALRM unavailable, degrade gracefully
            use_alarm = False
            logger.warning("sandbox: SIGALRM 不可用（非主线程），超时保护已降级")

        try:
            exec(code, sandbox_globals)  # noqa: S102
            if func_name not in sandbox_globals:
                raise ValueError(f"函数 '{func_name}' not found in code")
            result = sandbox_globals[func_name](namespace.get("params", {}))
            return result
        except _SandboxTimeout:
            raise TimeoutError(f"函数执行超时 (>{timeout}s)")
        finally:
            if use_alarm:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)


def _build_ontology_runtime_shim(call_function=None):
    """Build a fake ontology_runtime module for sandbox execution."""
    import types
    shim = types.ModuleType("ontology_runtime")

    def Function(**kwargs):
        """No-op decorator inside sandbox (metadata already extracted by watcher)."""
        def wrapper(func):
            return func
        return wrapper

    shim.Function = Function
    shim.call_function = call_function or (lambda name, params: None)
    return shim


def _try_import(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except ImportError:
        return False
