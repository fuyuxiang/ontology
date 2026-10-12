"""Pure mapping expressions using the Function sandbox's AST safety checks."""
import ast
import math

FUNCTIONS = {"abs": abs, "max": max, "min": min, "round": round, "len": len,
             "int": int, "float": float, "str": str, "bool": bool}


def validate_transform(expression):
    if not expression:
        return None
    if not isinstance(expression, str) or len(expression) > 2000:
        raise ValueError("transform 必须为不超过2000字的表达式")
    from app.services.function_runtime.sandbox import UnifiedSandbox
    validation = UnifiedSandbox().validate(expression)
    if not validation.valid:
        raise ValueError("transform 安全检查失败: " + "; ".join(validation.errors))
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("transform 必须为单个表达式") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 200:
        raise ValueError("transform 表达式过于复杂")
    for node in nodes:
        if isinstance(node, ast.Name) and node.id not in {"value", *FUNCTIONS}:
            raise ValueError(f"transform 不允许引用 {node.id}；原值使用 value")
        if isinstance(node, (ast.Attribute, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.NamedExpr)):
            raise ValueError("transform 不允许属性访问、赋值或循环表达式")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS):
            raise ValueError("transform 只能调用 Function expression 的纯函数")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            if not isinstance(node.right, ast.Constant) or not isinstance(node.right.value, (int, float)) or abs(node.right.value) > 100:
                raise ValueError("transform 幂运算指数必须是绝对值不超过100的常量")
    return compile(tree, "<mapping-transform>", "eval")


def apply_transform(value, expression):
    if not expression:
        return value
    try:
        validate_transform(expression)
        from app.services.function_runtime.sandbox import UnifiedSandbox
        result = UnifiedSandbox().execute_expression(expression, {"value": value, **FUNCTIONS}, timeout=2)
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("非有限数值")
        if isinstance(result, (str, list, dict, tuple)) and len(result) > 1_000_000:
            raise ValueError("转换结果过大")
        return result
    except Exception as exc:
        raise ValueError(f"transform 转换失败: {type(exc).__name__}: {exc}") from exc
