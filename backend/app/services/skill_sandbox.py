"""Generated skills share the runtime's restricted imports and deadlines."""
from __future__ import annotations

from typing import Any

from app.services.function_runtime.sandbox import UnifiedSandbox


class CodeValidationError(Exception):
    pass


def validate_code(code: str) -> list[str]:
    return UnifiedSandbox().validate(code).errors


def execute_in_sandbox(code: str, func_name: str, params: dict, context: dict | None = None) -> Any:
    violations = validate_code(code)
    if violations:
        raise CodeValidationError(f"Code validation failed: {'; '.join(violations)}")
    namespace = dict(context or {})
    if any(str(key).startswith("_") for key in namespace):
        raise CodeValidationError("Context cannot replace execution builtins")
    namespace["params"] = params
    return UnifiedSandbox().execute(code, func_name, namespace, keyword_params=True)
