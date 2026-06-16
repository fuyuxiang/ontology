import ast
from dataclasses import dataclass, field

ALLOWED_MODULES = {"math", "datetime", "json", "re", "decimal", "collections"}
FORBIDDEN_CALLS = {"open", "eval", "exec", "__import__", "compile", "globals", "locals", "getattr", "setattr", "delattr"}


@dataclass
class Violation:
    line: int
    reason: str


@dataclass
class ValidationResult:
    safe: bool
    violations: list[Violation] = field(default_factory=list)


def validate_code(code: str) -> ValidationResult:
    violations: list[Violation] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ValidationResult(safe=False, violations=[Violation(line=e.lineno or 1, reason=f"Syntax error: {e.msg}")])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".")[0]
                if module_root not in ALLOWED_MODULES:
                    violations.append(Violation(line=node.lineno, reason=f"Forbidden import: {alias.name}"))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root not in ALLOWED_MODULES:
                    violations.append(Violation(line=node.lineno, reason=f"Forbidden import: {node.module}"))

        elif isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in FORBIDDEN_CALLS:
                violations.append(Violation(line=node.lineno, reason=f"Forbidden call: {func_name}"))

    return ValidationResult(safe=len(violations) == 0, violations=violations)


def _get_call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""
