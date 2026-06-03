"""技能代码安全校验与沙箱执行"""
from __future__ import annotations

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket",
    "requests", "urllib", "http", "ftplib", "smtplib",
    "ctypes", "importlib", "pathlib", "glob", "tempfile",
}

ALLOWED_MODULES = {
    "json", "re", "datetime", "math", "collections",
    "itertools", "functools", "decimal", "statistics",
    "typing", "dataclasses",
}


class CodeValidationError(Exception):
    pass


def validate_code(code: str) -> list[str]:
    """AST-level static analysis. Returns list of violation messages."""
    violations = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    violations.append(f"Forbidden import: {mod}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    violations.append(f"Forbidden import from: {mod}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ("exec", "eval", "compile", "__import__"):
                    violations.append(f"Forbidden builtin call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ("system", "popen", "exec"):
                    violations.append(f"Forbidden method call: {node.func.attr}")
    return violations


def execute_in_sandbox(code: str, func_name: str, params: dict, context: dict | None = None) -> Any:
    """Execute a function from code string in a restricted namespace."""
    violations = validate_code(code)
    if violations:
        raise CodeValidationError(f"Code validation failed: {'; '.join(violations)}")

    namespace: dict[str, Any] = {"__builtins__": _safe_builtins()}
    if context:
        namespace.update(context)

    exec(code, namespace)

    if func_name not in namespace:
        raise CodeValidationError(f"Function '{func_name}' not found in code")

    func = namespace[func_name]
    return func(**params)


def _safe_builtins() -> dict:
    """Restricted builtins — no file/network/exec access."""
    import builtins
    safe = {}
    allowed = [
        "abs", "all", "any", "bool", "dict", "enumerate", "filter",
        "float", "frozenset", "getattr", "hasattr", "int", "isinstance",
        "issubclass", "len", "list", "map", "max", "min", "next",
        "print", "range", "repr", "reversed", "round", "set", "slice",
        "sorted", "str", "sum", "tuple", "type", "zip", "None", "True", "False",
    ]
    for name in allowed:
        if hasattr(builtins, name):
            safe[name] = getattr(builtins, name)
    return safe
