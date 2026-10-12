"""UnifiedSandbox: AST-based code validator and restricted execution environment."""
from __future__ import annotations

import ast
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from decimal import localcontext
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

RUNTIME_EXPORTS = frozenset({"Function", "call_function", "query_object", "query_objects", "update_object",
    "get_object", "call_find", "call_check_attr_mapping", "call_complex_sql", "execute_logic", "execute_action", "export_to_minio"})

FORBIDDEN_CALLS = frozenset([
    "open", "eval", "exec", "__import__", "compile",
    "globals", "locals", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
])

SAFE_BUILTINS = {
    "abs": abs, "max": max, "min": min, "round": round, "len": len,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "range": range, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "sorted": sorted, "reversed": reversed,
    "isinstance": isinstance, "print": print, "sum": sum,
    "True": True, "False": False, "None": None,
    "type": lambda value: type(value), "hasattr": lambda value, name: not str(name).startswith("_") and hasattr(value, name),
    "all": all, "any": any, "next": next, "repr": repr, "slice": slice,
    "frozenset": frozenset, "object": object, "Exception": Exception,
    "__build_class__": __build_class__,
    "ValueError": ValueError, "TypeError": TypeError, "RuntimeError": RuntimeError,
}

# Standard modules contain public references to host modules and reflective
# helpers. Expose explicit data-processing APIs, never the real module object.
MODULE_EXPORTS = {
    "json": "dumps loads JSONDecodeError",
    "re": "compile search match fullmatch findall finditer sub subn split escape IGNORECASE MULTILINE DOTALL VERBOSE ASCII",
    "datetime": "datetime date time timedelta timezone tzinfo MINYEAR MAXYEAR",
    "math": "acos acosh asin asinh atan atan2 atanh ceil comb copysign cos cosh degrees dist erf erfc exp expm1 fabs factorial floor fmod frexp fsum gamma gcd hypot isclose isfinite isinf isnan isqrt ldexp lgamma log log10 log1p log2 modf perm pow prod radians remainder sin sinh sqrt tan tanh trunc e pi tau inf nan",
    "decimal": "Decimal Context getcontext localcontext InvalidOperation DivisionByZero ROUND_CEILING ROUND_DOWN ROUND_FLOOR ROUND_HALF_DOWN ROUND_HALF_EVEN ROUND_HALF_UP ROUND_UP ROUND_05UP",
    "collections": "Counter defaultdict deque OrderedDict namedtuple ChainMap",
    "typing": "Any Optional Union List Dict Tuple Set FrozenSet Literal Iterable Iterator Callable Mapping Sequence",
    "functools": "reduce partial lru_cache wraps total_ordering cmp_to_key",
    "itertools": "accumulate chain combinations combinations_with_replacement compress count cycle dropwhile filterfalse groupby islice pairwise permutations product repeat starmap takewhile tee zip_longest",
    "statistics": "mean fmean geometric_mean harmonic_mean median median_low median_high median_grouped mode multimode quantiles pstdev pvariance stdev variance NormalDist StatisticsError",
    "copy": "copy deepcopy",
    "dataclasses": "dataclass field fields asdict astuple replace is_dataclass",
}


def _data_modules():
    import types
    modules = {}
    for name, exports in MODULE_EXPORTS.items():
        source = __import__(name)
        facade = types.ModuleType(name)
        for attribute in exports.split():
            if hasattr(source, attribute):
                setattr(facade, attribute, getattr(source, attribute))
        modules[name] = facade
    return modules


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


class _SandboxTimeout(BaseException):
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
                    mod = alias.name
                    if mod in FORBIDDEN_IMPORTS:
                        errors.append(f"禁止导入模块: {mod} (line {node.lineno})")
                    elif mod not in ALLOWED_IMPORTS:
                        errors.append(f"不允许的模块: {mod} (line {node.lineno})")

            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in FORBIDDEN_IMPORTS:
                    errors.append(f"禁止导入模块: {mod} (line {node.lineno})")
                elif mod not in ALLOWED_IMPORTS:
                    errors.append(f"不允许的模块: {mod} (line {node.lineno})")
                elif node.level or any(alias.name == "*" or alias.name.startswith("_") or
                    (mod != "ontology_runtime" and alias.name not in MODULE_EXPORTS[mod].split()) or
                    (mod == "ontology_runtime" and alias.name not in RUNTIME_EXPORTS)
                    for alias in node.names):
                    errors.append(f"不允许的模块成员: {mod} (line {node.lineno})")

            elif isinstance(node, ast.Attribute):
                attr = node.attr
                if attr.startswith("_"):
                    errors.append(f"禁止访问 dunder 属性: {attr} (line {node.lineno})")
                elif attr in {"format", "format_map", "mro"}:
                    errors.append(f"禁止反射访问: {attr}；字符串格式化请使用 f-string (line {node.lineno})")

            elif isinstance(node, ast.ExceptHandler) and node.type is None:
                errors.append(f"异常捕获必须指定 Exception 或业务异常类型 (line {node.lineno})")

            elif isinstance(node, ast.Name) and node.id.startswith("_"):
                errors.append(f"禁止访问私有名称: {node.id} (line {node.lineno})")

            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    errors.append(f"禁止调用: {node.func.id} (line {node.lineno})")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def execute_expression(self, expression: str, namespace: dict, timeout: int = 2) -> Any:
        """Run one validated expression with explicit inputs and the same deadline."""
        tree = ast.parse(expression, mode="eval")
        validation = self.validate(expression)
        if not validation.valid:
            raise ValueError("表达式安全检查失败: " + "; ".join(validation.errors))
        return self.execute("def evaluate(params):\n    return " + ast.unparse(tree.body),
                            "evaluate", namespace, timeout=timeout)

    def execute(
        self, code: str, func_name: str, namespace: dict, timeout: int = 30, *, keyword_params: bool = False,
        runtime_helpers: dict | None = None
    ) -> Any:
        """Execute a function in a sandboxed environment with timeout."""
        validation = self.validate(code)
        if not validation.valid:
            raise ValueError(f"代码校验失败: {'; '.join(validation.errors)}")

        if any(str(key).startswith("_") for key in namespace):
            raise ValueError("执行上下文不能覆盖私有名称")
        if timeout <= 0:
            raise TimeoutError("函数执行超时")
        allowed_modules = _data_modules()

        # Build ontology_runtime shim (provides Function decorator and call_function)
        ontology_helpers = {
            k: namespace[k] for k in ("query_object", "query_objects", "update_object") if k in namespace
        }
        ontology_shim = _build_ontology_runtime_shim(namespace.get("call_function"), ontology_helpers, runtime_helpers)
        allowed_modules["ontology_runtime"] = ontology_shim

        # Build sandbox globals with restricted builtins
        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            # datetime's C methods import their implementation dependencies.
            # Source imports and import-call aliases are rejected by validation;
            # these modules never enter user globals.
            if not level and not fromlist and name in {"time", "_strptime"}:
                return __import__(name)
            if level or name not in allowed_modules:
                raise ImportError(f"不允许导入模块: {name}")
            return allowed_modules[name]

        builtins = SAFE_BUILTINS.copy()
        builtins["__import__"] = _safe_import

        sandbox_globals: dict[str, Any] = {"__builtins__": builtins, "__name__": "ontology_sandbox"}
        sandbox_globals.update(allowed_modules)
        # Inject namespace items (call_function, etc.) into execution scope
        sandbox_globals.update(namespace)
        # Give dataclasses a real, execution-local module for forward annotated
        # fields without registering user code under a shared global name.
        import types
        execution_name = f"ontology_sandbox_{id(sandbox_globals)}"
        execution_module = types.ModuleType(execution_name)
        execution_module.__dict__.update(sandbox_globals)
        sandbox_globals = execution_module.__dict__
        sandbox_globals["__name__"] = execution_name

        # Worker-thread execution (API and Agent) cannot install SIGALRM. A
        # deadline trace still terminates Python loops there and nested calls
        # restore the outer trace rather than disabling its timeout.
        old_trace = sys.gettrace()
        deadline = min(time.monotonic() + timeout, getattr(old_trace, "deadline", float("inf")))
        def deadline_trace(frame, event, arg):
            # A one-line optimized loop can emit no repeated line events.
            # Opcode tracing prevents it bypassing the worker-thread deadline.
            frame.f_trace_opcodes = True
            if time.monotonic() >= deadline:
                raise _SandboxTimeout("执行超时")
            return deadline_trace
        deadline_trace.deadline = deadline
        sys.settrace(deadline_trace)
        old_handler = None
        old_timer = None
        timer_started = time.monotonic()
        use_alarm = False
        try:
            old_handler = signal.getsignal(signal.SIGALRM)
            signal.signal(signal.SIGALRM, _timeout_handler)
            old_timer = signal.getitimer(signal.ITIMER_REAL)
            remaining = max(0.001, deadline - time.monotonic())
            signal.setitimer(signal.ITIMER_REAL, min(remaining, old_timer[0]) if old_timer[0] else remaining)
            use_alarm = True
        except (ValueError, AttributeError):
            # Not in main thread — SIGALRM unavailable, degrade gracefully
            use_alarm = False
            logger.debug("sandbox: 非主线程使用 Python deadline trace")

        try:
            sys.modules[execution_module.__name__] = execution_module
            # decimal.getcontext() is mutable and otherwise survives into the
            # next request served by this thread. Keep business precision local.
            with localcontext():
                exec(compile(code, "<ontology-sandbox>", "exec", dont_inherit=True), sandbox_globals)  # noqa: S102
                if func_name not in sandbox_globals:
                    raise ValueError(f"函数 '{func_name}' not found in code")
                func = sandbox_globals[func_name]
                result = func(**namespace.get("params", {})) if keyword_params else func(namespace.get("params", {}))
                return result
        except _SandboxTimeout as err:
            raise TimeoutError(f"函数执行超时 (>{timeout}s)") from err
        finally:
            sys.settrace(old_trace)
            sys.modules.pop(execution_module.__name__, None)
            if use_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, old_handler)
                if old_timer and old_timer[0]:
                    signal.setitimer(signal.ITIMER_REAL, max(0.001, old_timer[0] - (time.monotonic() - timer_started)), old_timer[1])


def _build_ontology_runtime_shim(call_function=None, ontology_helpers=None, runtime_helpers=None):
    """Build an isolated ontology_runtime module for sandbox execution."""
    import types
    shim = types.ModuleType("ontology_runtime")

    def Function(**kwargs):
        """No-op decorator inside sandbox (metadata already extracted by watcher)."""
        def wrapper(func):
            return func
        return wrapper

    shim.Function = Function
    def unavailable(name):
        def invoke(*args, **kwargs):
            raise RuntimeError(f"当前执行入口未提供 {name} 能力")
        return invoke
    shim.call_function = call_function or unavailable("call_function")

    helpers = ontology_helpers or {}
    shim.query_object = helpers.get("query_object", unavailable("query_object"))
    shim.query_objects = helpers.get("query_objects", unavailable("query_objects"))
    shim.update_object = helpers.get("update_object", unavailable("update_object"))
    for name in RUNTIME_EXPORTS - {"Function", "call_function", "query_object", "query_objects", "update_object"}:
        setattr(shim, name, (runtime_helpers or {}).get(name, unavailable(name)))
    return shim
