# Function Runtime 独立服务化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将函数运行时抽离为独立模块 `services/function_runtime/`，支持 @Function 装饰器自动注册、Agent 通过 run_logic/run_action 调用用户函数、函数间互调。

**Architecture:** 新建 `backend/app/services/function_runtime/` 包含 6 个文件（models, decorator, sandbox, registry, executor, watcher）。重构 Agent 工具层，新增 Tier 2 三工具 + 重构 Tier 1 三工具。现有 FunctionExecutor 降级为兼容层。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, watchdog (新依赖), ast 模块

## Global Constraints

- Python 3.11+，与现有 requirements.txt 兼容
- 所有新模块放在 `backend/app/services/function_runtime/`
- 数据库变更通过 SQLAlchemy 模型字段添加实现（SQLite 开发 / MySQL 生产）
- 沙箱安全：禁止 os/sys/subprocess 等，只允许 json/re/datetime/math/decimal/collections/typing/functools/itertools/statistics/copy/dataclasses
- 单函数超时 30s，调用链总超时 120s，最大递归深度 10
- 测试使用 pytest，文件放在 `backend/tests/`
- 新增依赖：`watchdog>=4.0`

---

## File Structure

### 新建文件

| 文件 | 职责 |
|------|------|
| `backend/app/services/function_runtime/__init__.py` | 包入口，导出核心类 |
| `backend/app/services/function_runtime/models.py` | FunctionMeta, ExecContext, ExecResult, ParamSchema 数据结构 |
| `backend/app/services/function_runtime/decorator.py` | @Function 装饰器定义 |
| `backend/app/services/function_runtime/sandbox.py` | UnifiedSandbox（AST 校验 + 受限执行 + 超时） |
| `backend/app/services/function_runtime/registry.py` | FunctionRegistry（内存缓存 + DB 持久化） |
| `backend/app/services/function_runtime/executor.py` | FunctionRuntimeExecutor（调度 + call_function 注入 + 循环检测） |
| `backend/app/services/function_runtime/watcher.py` | FunctionWatcher（watchdog 监听 + AST 扫描 + 自动注册） |
| `backend/tests/test_function_runtime_sandbox.py` | 沙箱测试 |
| `backend/tests/test_function_runtime_registry.py` | 注册中心测试 |
| `backend/tests/test_function_runtime_executor.py` | 执行器测试（含互调、循环检测） |
| `backend/tests/test_function_runtime_watcher.py` | 文件监听测试 |
| `backend/tests/test_agent_tools_tier2.py` | Tier 2 工具集成测试 |
| `workspace/sample/calc_demo/main.py` | 示例函数文件（供测试和文档） |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/requirements.txt` | 添加 `watchdog>=4.0` |
| `backend/app/models/function.py` | 添加 source_path, func_name, checksum, registered_by 字段 |
| `backend/app/services/function_executor.py` | 降级为兼容层，python 类型委托给新运行时 |
| `backend/app/services/action_executors/call_function.py` | 补全实现，调用 FunctionRuntimeExecutor |
| `backend/app/services/agent_tools.py` | 新增 6 个工具 spec（Tier 1 × 3 + Tier 2 × 3） |
| `backend/app/services/agent/tool_router.py` | 新增 6 个 handler |
| `backend/app/main.py` | 启动时初始化 FunctionWatcher |

---

### Task 1: 数据结构与装饰器（models.py + decorator.py）

**Files:**
- Create: `backend/app/services/function_runtime/__init__.py`
- Create: `backend/app/services/function_runtime/models.py`
- Create: `backend/app/services/function_runtime/decorator.py`
- Test: `backend/tests/test_function_runtime_models.py`

**Interfaces:**
- Produces:
  - `ParamSchema(name: str, type: str, required: bool, description: str)`
  - `FunctionMeta(callable_name: str, description: str, type: Literal["logic","action"], params: list[ParamSchema], return_type: str, source_path: str, func_name: str, ontology_id: int, checksum: str)`
  - `ExecContext(call_stack: list[str], max_depth: int=10, timeout_sec: int=30, total_timeout_sec: int=120, ontology_id: int|None=None)`
  - `ExecResult(success: bool, result: Any, error: str|None, execution_ms: int, call_trace: list[str])`
  - `Function(name, description, type, params=None, return_type="object")` decorator

- [ ] **Step 1: Write tests for models and decorator**

```python
# backend/tests/test_function_runtime_models.py
from app.services.function_runtime.models import (
    ExecContext, ExecResult, FunctionMeta, ParamSchema,
)
from app.services.function_runtime.decorator import Function


class TestParamSchema:
    def test_create(self):
        p = ParamSchema(name="month", type="string", required=True, description="月份")
        assert p.name == "month"
        assert p.required is True


class TestFunctionMeta:
    def test_create(self):
        meta = FunctionMeta(
            callable_name="calc_loss",
            description="计算折损",
            type="logic",
            params=[ParamSchema(name="x", type="number", required=True, description="")],
            return_type="object",
            source_path="/workspace/1/calc/main.py",
            func_name="calc_loss",
            ontology_id=1,
            checksum="abc123",
        )
        assert meta.callable_name == "calc_loss"
        assert meta.type == "logic"


class TestExecContext:
    def test_defaults(self):
        ctx = ExecContext(call_stack=[])
        assert ctx.max_depth == 10
        assert ctx.timeout_sec == 30
        assert ctx.total_timeout_sec == 120

    def test_has_circular(self):
        ctx = ExecContext(call_stack=["a", "b"])
        assert "a" in ctx.call_stack


class TestExecResult:
    def test_success(self):
        r = ExecResult(success=True, result={"x": 1}, error=None, execution_ms=50, call_trace=["fn1"])
        assert r.success is True
        assert r.execution_ms == 50


class TestFunctionDecorator:
    def test_attaches_metadata(self):
        @Function(name="my_func", description="desc", type="logic")
        def my_func(params):
            return params

        assert hasattr(my_func, "_function_meta")
        assert my_func._function_meta["name"] == "my_func"
        assert my_func._function_meta["type"] == "logic"

    def test_with_params(self):
        @Function(
            name="calc",
            description="计算",
            type="action",
            params=[{"name": "x", "type": "number", "required": True, "description": ""}],
            return_type="number",
        )
        def calc(params):
            return params["x"]

        assert calc._function_meta["return_type"] == "number"
        assert len(calc._function_meta["params"]) == 1

    def test_function_still_callable(self):
        @Function(name="add", description="add", type="logic")
        def add(params):
            return params["a"] + params["b"]

        assert add({"a": 1, "b": 2}) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_runtime_models.py -v`
Expected: ModuleNotFoundError — module `app.services.function_runtime` does not exist yet

- [ ] **Step 3: Implement models.py**

```python
# backend/app/services/function_runtime/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ParamSchema:
    name: str
    type: str
    required: bool
    description: str


@dataclass
class FunctionMeta:
    callable_name: str
    description: str
    type: Literal["logic", "action"]
    params: list[ParamSchema]
    return_type: str
    source_path: str
    func_name: str
    ontology_id: int
    checksum: str


@dataclass
class ExecContext:
    call_stack: list[str] = field(default_factory=list)
    max_depth: int = 10
    timeout_sec: int = 30
    total_timeout_sec: int = 120
    ontology_id: int | None = None


@dataclass
class ExecResult:
    success: bool
    result: Any
    error: str | None
    execution_ms: int
    call_trace: list[str]
```

- [ ] **Step 4: Implement decorator.py**

```python
# backend/app/services/function_runtime/decorator.py
from __future__ import annotations

from typing import Literal


def Function(
    name: str,
    description: str,
    type: Literal["logic", "action"],
    params: list[dict] | None = None,
    return_type: str = "object",
):
    def wrapper(func):
        func._function_meta = {
            "name": name,
            "description": description,
            "type": type,
            "params": params,
            "return_type": return_type,
        }
        return func
    return wrapper
```

- [ ] **Step 5: Create __init__.py**

```python
# backend/app/services/function_runtime/__init__.py
from .models import ExecContext, ExecResult, FunctionMeta, ParamSchema
from .decorator import Function

__all__ = ["ExecContext", "ExecResult", "FunctionMeta", "ParamSchema", "Function"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_function_runtime_models.py -v`
Expected: All 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/function_runtime/__init__.py \
        backend/app/services/function_runtime/models.py \
        backend/app/services/function_runtime/decorator.py \
        backend/tests/test_function_runtime_models.py
git commit -m "新增 function_runtime 模块：数据结构与装饰器"
```

---

### Task 2: 统一沙箱（sandbox.py）

**Files:**
- Create: `backend/app/services/function_runtime/sandbox.py`
- Test: `backend/tests/test_function_runtime_sandbox.py`

**Interfaces:**
- Produces:
  - `ValidationResult(valid: bool, errors: list[str])`
  - `UnifiedSandbox.validate(code: str) -> ValidationResult`
  - `UnifiedSandbox.execute(code: str, func_name: str, namespace: dict, timeout: int = 30) -> Any`

- [ ] **Step 1: Write tests for sandbox**

```python
# backend/tests/test_function_runtime_sandbox.py
import pytest

from app.services.function_runtime.sandbox import UnifiedSandbox, ValidationResult


@pytest.fixture
def sandbox():
    return UnifiedSandbox()


class TestValidation:
    def test_clean_code_passes(self, sandbox):
        code = '''
def calc(params):
    return params["a"] + params["b"]
'''
        result = sandbox.validate(code)
        assert result.valid is True
        assert result.errors == []

    def test_import_os_rejected(self, sandbox):
        code = "import os\ndef f(params): return os.getcwd()"
        result = sandbox.validate(code)
        assert result.valid is False
        assert any("os" in e for e in result.errors)

    def test_import_from_subprocess_rejected(self, sandbox):
        code = "from subprocess import run\ndef f(params): return run(['ls'])"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_dunder_import_rejected(self, sandbox):
        code = "def f(params): return __import__('os')"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_open_call_rejected(self, sandbox):
        code = "def f(params): return open('/etc/passwd').read()"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_eval_call_rejected(self, sandbox):
        code = "def f(params): return eval('1+1')"
        result = sandbox.validate(code)
        assert result.valid is False

    def test_allowed_import_json(self, sandbox):
        code = "import json\ndef f(params): return json.dumps(params)"
        result = sandbox.validate(code)
        assert result.valid is True

    def test_allowed_import_datetime(self, sandbox):
        code = "from datetime import datetime\ndef f(params): return str(datetime.now())"
        result = sandbox.validate(code)
        assert result.valid is True

    def test_syntax_error(self, sandbox):
        code = "def f(params)\n  return 1"
        result = sandbox.validate(code)
        assert result.valid is False


class TestExecution:
    def test_simple_function(self, sandbox):
        code = '''
def add(params):
    return params["a"] + params["b"]
'''
        result = sandbox.execute(code, "add", {"params": {"a": 3, "b": 4}})
        assert result == 7

    def test_function_with_allowed_import(self, sandbox):
        code = '''
import json
def to_json(params):
    return json.dumps(params)
'''
        result = sandbox.execute(code, "to_json", {"params": {"x": 1}})
        assert result == '{"x": 1}'

    def test_namespace_injection(self, sandbox):
        code = '''
def my_func(params):
    return call_function("other", {"x": 1})
'''
        mock_call = lambda name, p: {"called": name, "params": p}
        ns = {"params": {}, "call_function": mock_call}
        result = sandbox.execute(code, "my_func", ns)
        assert result == {"called": "other", "params": {"x": 1}}

    def test_timeout(self, sandbox):
        code = '''
def slow(params):
    i = 0
    while True:
        i += 1
    return i
'''
        with pytest.raises(TimeoutError):
            sandbox.execute(code, "slow", {"params": {}}, timeout=1)

    def test_forbidden_builtin_at_runtime(self, sandbox):
        code = '''
def bad(params):
    return open("/etc/passwd")
'''
        with pytest.raises(Exception):
            sandbox.execute(code, "bad", {"params": {}})

    def test_function_not_found(self, sandbox):
        code = "def other(params): return 1"
        with pytest.raises(ValueError, match="not found"):
            sandbox.execute(code, "nonexistent", {"params": {}})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_runtime_sandbox.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement sandbox.py**

```python
# backend/app/services/function_runtime/sandbox.py
from __future__ import annotations

import ast
import signal
from dataclasses import dataclass, field
from typing import Any


FORBIDDEN_IMPORTS = frozenset([
    "os", "sys", "subprocess", "shutil", "socket", "ctypes",
    "importlib", "pickle", "shelve", "multiprocessing", "threading",
    "signal", "pty", "fcntl", "resource", "tempfile", "glob",
    "pathlib", "io",
])

ALLOWED_IMPORTS = frozenset([
    "json", "re", "datetime", "math", "decimal", "collections",
    "typing", "functools", "itertools", "statistics", "copy", "dataclasses",
])

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
    def validate(self, code: str) -> ValidationResult:
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

            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    errors.append(f"禁止调用: {node.func.id} (line {node.lineno})")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def execute(self, code: str, func_name: str, namespace: dict, timeout: int = 30) -> Any:
        validation = self.validate(code)
        if not validation.valid:
            raise ValueError(f"代码校验失败: {'; '.join(validation.errors)}")

        allowed_modules = {mod: __import__(mod) for mod in ALLOWED_IMPORTS if _try_import(mod)}

        sandbox_globals: dict[str, Any] = {"__builtins__": SAFE_BUILTINS.copy()}
        sandbox_globals.update(allowed_modules)
        sandbox_globals.update(namespace)

        old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            exec(code, sandbox_globals)
            if func_name not in sandbox_globals:
                raise ValueError(f"函数 '{func_name}' not found in code")
            result = sandbox_globals[func_name](namespace.get("params", {}))
            return result
        except _SandboxTimeout:
            raise TimeoutError(f"函数执行超时 (>{timeout}s)")
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


def _try_import(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except ImportError:
        return False
```

- [ ] **Step 4: Update __init__.py exports**

Add to `backend/app/services/function_runtime/__init__.py`:

```python
from .sandbox import UnifiedSandbox, ValidationResult
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_function_runtime_sandbox.py -v`
Expected: All 15 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/function_runtime/sandbox.py \
        backend/app/services/function_runtime/__init__.py \
        backend/tests/test_function_runtime_sandbox.py
git commit -m "新增统一沙箱：AST 校验 + 受限执行 + SIGALRM 超时"
```

---

### Task 3: 函数注册中心（registry.py）+ 数据库字段扩展

**Files:**
- Create: `backend/app/services/function_runtime/registry.py`
- Modify: `backend/app/models/function.py` — 添加 4 个字段
- Test: `backend/tests/test_function_runtime_registry.py`

**Interfaces:**
- Consumes: `FunctionMeta`, `ParamSchema` from Task 1
- Produces:
  - `FunctionRegistry(db: Session)`
  - `FunctionRegistry.register(meta: FunctionMeta) -> None`
  - `FunctionRegistry.unregister(callable_name: str) -> None`
  - `FunctionRegistry.get(callable_name: str) -> FunctionMeta | None`
  - `FunctionRegistry.list_by_type(type: str, ontology_id: int | None = None) -> list[FunctionMeta]`
  - `FunctionRegistry.list_capabilities(ontology_id: int | None = None) -> list[dict]`
  - `FunctionRegistry.sync_from_db() -> None`

- [ ] **Step 1: Write tests for registry**

```python
# backend/tests/test_function_runtime_registry.py
from unittest.mock import MagicMock, patch

import pytest

from app.services.function_runtime.models import FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry


def _make_meta(name="test_fn", type_="logic", ontology_id=1):
    return FunctionMeta(
        callable_name=name,
        description=f"desc for {name}",
        type=type_,
        params=[ParamSchema(name="x", type="number", required=True, description="")],
        return_type="object",
        source_path=f"/workspace/{ontology_id}/{name}/main.py",
        func_name=name,
        ontology_id=ontology_id,
        checksum="abc123",
    )


class TestRegistryInMemory:
    def test_register_and_get(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        meta = _make_meta("calc")
        registry.register(meta)
        assert registry.get("calc") == meta

    def test_unregister(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("calc"))
        registry.unregister("calc")
        assert registry.get("calc") is None

    def test_get_nonexistent_returns_none(self):
        db = MagicMock()
        registry = FunctionRegistry(db)
        assert registry.get("nonexistent") is None

    def test_list_by_type(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic"))
        registry.register(_make_meta("fn2", "action"))
        registry.register(_make_meta("fn3", "logic"))

        logics = registry.list_by_type("logic")
        assert len(logics) == 2
        actions = registry.list_by_type("action")
        assert len(actions) == 1

    def test_list_by_type_with_ontology_filter(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic", ontology_id=1))
        registry.register(_make_meta("fn2", "logic", ontology_id=2))

        result = registry.list_by_type("logic", ontology_id=1)
        assert len(result) == 1
        assert result[0].callable_name == "fn1"

    def test_list_capabilities(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        registry.register(_make_meta("fn1", "logic"))
        registry.register(_make_meta("fn2", "action"))

        caps = registry.list_capabilities()
        assert len(caps) == 2
        assert caps[0]["name"] == "fn1"
        assert caps[0]["type"] == "logic"
        assert "params" in caps[0]

    def test_register_updates_existing(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        meta1 = _make_meta("calc")
        registry.register(meta1)
        meta2 = _make_meta("calc")
        meta2.description = "updated"
        registry.register(meta2)
        assert registry.get("calc").description == "updated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_runtime_registry.py -v`
Expected: ModuleNotFoundError for `registry`

- [ ] **Step 3: Add fields to OntologyFunction model**

Modify `backend/app/models/function.py` — add after `last_executed` field:

```python
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    func_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registered_by: Mapped[str] = mapped_column(String(20), default="ui")
```

- [ ] **Step 4: Implement registry.py**

```python
# backend/app/services/function_runtime/registry.py
from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.models.function import OntologyFunction
from app.services.function_runtime.models import FunctionMeta, ParamSchema

logger = logging.getLogger(__name__)


class FunctionRegistry:
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, FunctionMeta] = {}

    def register(self, meta: FunctionMeta) -> None:
        self._cache[meta.callable_name] = meta
        self._persist(meta)

    def unregister(self, callable_name: str) -> None:
        self._cache.pop(callable_name, None)
        row = self.db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == callable_name,
            OntologyFunction.registered_by == "watcher",
        ).first()
        if row:
            self.db.delete(row)
            self.db.commit()

    def get(self, callable_name: str) -> FunctionMeta | None:
        return self._cache.get(callable_name)

    def list_by_type(
        self, type: Literal["logic", "action"], ontology_id: int | None = None
    ) -> list[FunctionMeta]:
        results = [m for m in self._cache.values() if m.type == type]
        if ontology_id is not None:
            results = [m for m in results if m.ontology_id == ontology_id]
        return results

    def list_capabilities(self, ontology_id: int | None = None) -> list[dict]:
        items = list(self._cache.values())
        if ontology_id is not None:
            items = [m for m in items if m.ontology_id == ontology_id]
        return [
            {
                "name": m.callable_name,
                "description": m.description,
                "type": m.type,
                "params": [
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in m.params
                ],
                "return_type": m.return_type,
            }
            for m in items
        ]

    def sync_from_db(self) -> None:
        rows = self.db.query(OntologyFunction).filter(
            OntologyFunction.status == "active",
            OntologyFunction.logic_type == "python",
            OntologyFunction.source_path.isnot(None),
        ).all()
        for row in rows:
            params = [
                ParamSchema(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                )
                for p in (row.input_schema or [])
                if isinstance(p, dict)
            ]
            meta = FunctionMeta(
                callable_name=row.callable_name,
                description=row.description or "",
                type="action" if "action" in (row.tags or []) else "logic",
                params=params,
                return_type=row.return_type or "object",
                source_path=row.source_path or "",
                func_name=row.func_name or row.callable_name,
                ontology_id=int(row.entity_id.split("-")[0]) if row.entity_id else 0,
                checksum=row.checksum or "",
            )
            self._cache[meta.callable_name] = meta
        logger.info(f"Registry synced {len(rows)} functions from DB")

    def _persist(self, meta: FunctionMeta) -> None:
        row = self.db.query(OntologyFunction).filter(
            OntologyFunction.callable_name == meta.callable_name,
        ).first()
        if row:
            row.description = meta.description
            row.input_schema = [
                {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in meta.params
            ]
            row.return_type = meta.return_type
            row.source_path = meta.source_path
            row.func_name = meta.func_name
            row.checksum = meta.checksum
            row.registered_by = "watcher"
            row.status = "active"
            row.logic_type = "python"
        else:
            row = OntologyFunction(
                name=meta.callable_name,
                callable_name=meta.callable_name,
                description=meta.description,
                input_schema=[
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in meta.params
                ],
                return_type=meta.return_type,
                logic_type="python",
                logic_body="",
                source_path=meta.source_path,
                func_name=meta.func_name,
                checksum=meta.checksum,
                registered_by="watcher",
                status="active",
            )
            self.db.add(row)
        self.db.commit()
```

- [ ] **Step 5: Update __init__.py exports**

Add to `backend/app/services/function_runtime/__init__.py`:

```python
from .registry import FunctionRegistry
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_function_runtime_registry.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/function_runtime/registry.py \
        backend/app/services/function_runtime/__init__.py \
        backend/app/models/function.py \
        backend/tests/test_function_runtime_registry.py
git commit -m "新增函数注册中心 + OntologyFunction 模型字段扩展"
```

---

### Task 4: 统一执行器（executor.py）

**Files:**
- Create: `backend/app/services/function_runtime/executor.py`
- Test: `backend/tests/test_function_runtime_executor.py`

**Interfaces:**
- Consumes: `FunctionMeta`, `ExecContext`, `ExecResult` from Task 1; `UnifiedSandbox` from Task 2; `FunctionRegistry` from Task 3
- Produces:
  - `FunctionRuntimeExecutor(registry: FunctionRegistry, sandbox: UnifiedSandbox, db: Session)`
  - `FunctionRuntimeExecutor.execute(callable_name: str, params: dict, context: ExecContext | None = None) -> ExecResult`

- [ ] **Step 1: Write tests for executor**

```python
# backend/tests/test_function_runtime_executor.py
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from app.services.function_runtime.executor import FunctionRuntimeExecutor
from app.services.function_runtime.models import ExecContext, FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox


def _write_function_file(tmp_dir, code):
    path = os.path.join(tmp_dir, "main.py")
    with open(path, "w") as f:
        f.write(code)
    return path


@pytest.fixture
def setup():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    registry = FunctionRegistry(db)
    sandbox = UnifiedSandbox()
    executor = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=db)
    return registry, executor


class TestBasicExecution:
    def test_execute_simple_function(self, setup, tmp_path):
        registry, executor = setup
        code = '''
def add(params):
    return params["a"] + params["b"]
'''
        path = _write_function_file(tmp_path, code)
        meta = FunctionMeta(
            callable_name="add", description="加法", type="logic",
            params=[],return_type="number",
            source_path=path, func_name="add", ontology_id=1, checksum="x",
        )
        registry.register(meta)
        result = executor.execute("add", {"a": 3, "b": 5})
        assert result.success is True
        assert result.result == 8

    def test_function_not_found(self, setup):
        _, executor = setup
        result = executor.execute("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error.lower() or "未找到" in result.error

    def test_execution_error_caught(self, setup, tmp_path):
        registry, executor = setup
        code = '''
def bad(params):
    return 1 / 0
'''
        path = _write_function_file(tmp_path, code)
        meta = FunctionMeta(
            callable_name="bad", description="", type="logic",
            params=[], return_type="number",
            source_path=path, func_name="bad", ontology_id=1, checksum="x",
        )
        registry.register(meta)
        result = executor.execute("bad", {})
        assert result.success is False
        assert "division" in result.error.lower()


class TestCallFunction:
    def test_inter_function_call(self, setup, tmp_path):
        registry, executor = setup
        code_a = '''
def double(params):
    return params["x"] * 2
'''
        code_b = '''
def quad(params):
    d = call_function("double", {"x": params["x"]})
    return d * 2
'''
        path_a = _write_function_file(tmp_path / "a", code_a)
        os.makedirs(tmp_path / "a", exist_ok=True)
        path_a = _write_function_file(tmp_path / "a", code_a)
        path_b = _write_function_file(tmp_path / "b", code_b)
        os.makedirs(tmp_path / "b", exist_ok=True)
        path_b = _write_function_file(tmp_path / "b", code_b)

        registry.register(FunctionMeta(
            callable_name="double", description="", type="logic",
            params=[], return_type="number",
            source_path=path_a, func_name="double", ontology_id=1, checksum="x",
        ))
        registry.register(FunctionMeta(
            callable_name="quad", description="", type="logic",
            params=[], return_type="number",
            source_path=path_b, func_name="quad", ontology_id=1, checksum="x",
        ))

        result = executor.execute("quad", {"x": 3})
        assert result.success is True
        assert result.result == 12

    def test_circular_call_detected(self, setup, tmp_path):
        registry, executor = setup
        code_a = '''
def fn_a(params):
    return call_function("fn_b", {})
'''
        code_b = '''
def fn_b(params):
    return call_function("fn_a", {})
'''
        os.makedirs(tmp_path / "a", exist_ok=True)
        os.makedirs(tmp_path / "b", exist_ok=True)
        path_a = _write_function_file(tmp_path / "a", code_a)
        path_b = _write_function_file(tmp_path / "b", code_b)

        registry.register(FunctionMeta(
            callable_name="fn_a", description="", type="logic",
            params=[], return_type="object",
            source_path=path_a, func_name="fn_a", ontology_id=1, checksum="x",
        ))
        registry.register(FunctionMeta(
            callable_name="fn_b", description="", type="logic",
            params=[], return_type="object",
            source_path=path_b, func_name="fn_b", ontology_id=1, checksum="x",
        ))

        result = executor.execute("fn_a", {})
        assert result.success is False
        assert "circular" in result.error.lower() or "循环" in result.error

    def test_max_depth_exceeded(self, setup, tmp_path):
        registry, executor = setup
        code = '''
def recurse(params):
    n = params.get("n", 0)
    if n > 20:
        return n
    return call_function("recurse", {"n": n + 1})
'''
        path = _write_function_file(tmp_path, code)
        registry.register(FunctionMeta(
            callable_name="recurse", description="", type="logic",
            params=[], return_type="number",
            source_path=path, func_name="recurse", ontology_id=1, checksum="x",
        ))
        result = executor.execute("recurse", {"n": 0})
        assert result.success is False
        assert "depth" in result.error.lower() or "深度" in result.error


class TestCallTrace:
    def test_trace_recorded(self, setup, tmp_path):
        registry, executor = setup
        code = '''
def simple(params):
    return 42
'''
        path = _write_function_file(tmp_path, code)
        registry.register(FunctionMeta(
            callable_name="simple", description="", type="logic",
            params=[], return_type="number",
            source_path=path, func_name="simple", ontology_id=1, checksum="x",
        ))
        result = executor.execute("simple", {})
        assert "simple" in result.call_trace
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_runtime_executor.py -v`
Expected: ModuleNotFoundError for `executor`

- [ ] **Step 3: Implement executor.py**

```python
# backend/app/services/function_runtime/executor.py
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.services.function_runtime.models import ExecContext, ExecResult, FunctionMeta
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox

logger = logging.getLogger(__name__)


class CircularCallError(Exception):
    pass


class MaxDepthError(Exception):
    pass


class FunctionRuntimeExecutor:
    def __init__(self, registry: FunctionRegistry, sandbox: UnifiedSandbox, db: Session):
        self.registry = registry
        self.sandbox = sandbox
        self.db = db

    def execute(
        self, callable_name: str, params: dict, context: ExecContext | None = None
    ) -> ExecResult:
        start = time.time()
        if context is None:
            context = ExecContext(call_stack=[])

        meta = self.registry.get(callable_name)
        if meta is None:
            return ExecResult(
                success=False, result=None,
                error=f"函数 '{callable_name}' 未找到",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        if callable_name in context.call_stack:
            return ExecResult(
                success=False, result=None,
                error=f"检测到循环调用 (circular): {' → '.join(context.call_stack)} → {callable_name}",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        if len(context.call_stack) >= context.max_depth:
            return ExecResult(
                success=False, result=None,
                error=f"超过最大递归深度 (depth): {context.max_depth}",
                execution_ms=int((time.time() - start) * 1000),
                call_trace=list(context.call_stack),
            )

        context.call_stack.append(callable_name)

        try:
            code = self._read_source(meta.source_path)
            call_fn = self._build_call_function(context)
            namespace = {
                "params": params,
                "call_function": call_fn,
            }
            result = self.sandbox.execute(
                code, meta.func_name, namespace, timeout=context.timeout_sec
            )
            elapsed = int((time.time() - start) * 1000)
            return ExecResult(
                success=True, result=result, error=None,
                execution_ms=elapsed, call_trace=list(context.call_stack),
            )
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return ExecResult(
                success=False, result=None, error=str(e),
                execution_ms=elapsed, call_trace=list(context.call_stack),
            )
        finally:
            context.call_stack.pop()

    def _build_call_function(self, context: ExecContext):
        def call_function(name: str, params: dict) -> Any:
            result = self.execute(name, params, context)
            if not result.success:
                raise RuntimeError(f"call_function('{name}') failed: {result.error}")
            return result.result
        return call_function

    def _read_source(self, source_path: str) -> str:
        with open(source_path, "r", encoding="utf-8") as f:
            return f.read()
```

- [ ] **Step 4: Update __init__.py exports**

Add to `backend/app/services/function_runtime/__init__.py`:

```python
from .executor import FunctionRuntimeExecutor, CircularCallError, MaxDepthError
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_function_runtime_executor.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/function_runtime/executor.py \
        backend/app/services/function_runtime/__init__.py \
        backend/tests/test_function_runtime_executor.py
git commit -m "新增统一执行器：call_function 注入 + 循环检测 + 深度限制"
```

---

### Task 5: 文件监听（watcher.py）

**Files:**
- Create: `backend/app/services/function_runtime/watcher.py`
- Modify: `backend/requirements.txt` — 添加 `watchdog>=4.0`
- Test: `backend/tests/test_function_runtime_watcher.py`

**Interfaces:**
- Consumes: `FunctionMeta`, `ParamSchema` from Task 1; `FunctionRegistry` from Task 3
- Produces:
  - `FunctionWatcher(registry: FunctionRegistry, workspace_root: str)`
  - `FunctionWatcher.start() -> None`
  - `FunctionWatcher.stop() -> None`
  - `FunctionWatcher.scan_file(path: str) -> list[FunctionMeta]`
  - `FunctionWatcher.scan_all(ontology_id: int | None = None) -> None`

- [ ] **Step 1: Write tests for watcher**

```python
# backend/tests/test_function_runtime_watcher.py
import os
import tempfile
import time
from unittest.mock import MagicMock

import pytest

from app.services.function_runtime.models import FunctionMeta
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.watcher import FunctionWatcher


SAMPLE_CODE = '''
from ontology_runtime import Function

@Function(
    name="calc_demo",
    description="演示计算函数",
    type="logic",
    params=[
        {"name": "x", "type": "number", "required": True, "description": "输入值"},
    ],
    return_type="number",
)
def calc_demo(params):
    return params["x"] * 2
'''

MULTI_FUNCTION_CODE = '''
from ontology_runtime import Function

@Function(name="fn_a", description="函数A", type="logic")
def fn_a(params):
    return 1

@Function(name="fn_b", description="函数B", type="action", params=[{"name":"y","type":"string","required":False,"description":""}], return_type="string")
def fn_b(params):
    return "done"
'''

BAD_CODE = '''
import os
from ontology_runtime import Function

@Function(name="bad_fn", description="坏函数", type="logic")
def bad_fn(params):
    return os.getcwd()
'''


class TestScanFile:
    def test_scan_single_function(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        workspace = str(tmp_path)
        watcher = FunctionWatcher(registry=registry, workspace_root=workspace)

        os.makedirs(tmp_path / "1" / "calc_demo")
        file_path = tmp_path / "1" / "calc_demo" / "main.py"
        file_path.write_text(SAMPLE_CODE)

        metas = watcher.scan_file(str(file_path))
        assert len(metas) == 1
        assert metas[0].callable_name == "calc_demo"
        assert metas[0].type == "logic"
        assert len(metas[0].params) == 1
        assert metas[0].params[0].name == "x"

    def test_scan_multi_function_file(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "1" / "multi")
        file_path = tmp_path / "1" / "multi" / "main.py"
        file_path.write_text(MULTI_FUNCTION_CODE)

        metas = watcher.scan_file(str(file_path))
        assert len(metas) == 2
        names = {m.callable_name for m in metas}
        assert names == {"fn_a", "fn_b"}

    def test_scan_file_with_no_decorator(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        file_path = tmp_path / "plain.py"
        file_path.write_text("def foo(): return 1")
        metas = watcher.scan_file(str(file_path))
        assert metas == []

    def test_scan_extracts_ontology_id_from_path(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "42" / "myfn")
        file_path = tmp_path / "42" / "myfn" / "main.py"
        file_path.write_text(SAMPLE_CODE)

        metas = watcher.scan_file(str(file_path))
        assert metas[0].ontology_id == 42


class TestScanAll:
    def test_scan_all_registers_functions(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "1" / "calc_demo")
        (tmp_path / "1" / "calc_demo" / "main.py").write_text(SAMPLE_CODE)

        watcher.scan_all()
        assert registry.get("calc_demo") is not None


class TestFileChangeDetection:
    def test_on_file_changed_registers_new(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "1" / "calc_demo")
        file_path = str(tmp_path / "1" / "calc_demo" / "main.py")
        with open(file_path, "w") as f:
            f.write(SAMPLE_CODE)

        watcher._on_file_changed(file_path)
        assert registry.get("calc_demo") is not None

    def test_on_file_deleted_unregisters(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "1" / "calc_demo")
        file_path = str(tmp_path / "1" / "calc_demo" / "main.py")
        with open(file_path, "w") as f:
            f.write(SAMPLE_CODE)
        watcher._on_file_changed(file_path)
        assert registry.get("calc_demo") is not None

        os.remove(file_path)
        watcher._on_file_deleted(file_path)
        assert registry.get("calc_demo") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_function_runtime_watcher.py -v`
Expected: ModuleNotFoundError for `watcher`

- [ ] **Step 3: Add watchdog to requirements.txt**

Append to `backend/requirements.txt`:
```
watchdog>=4.0
```

- [ ] **Step 4: Implement watcher.py**

```python
# backend/app/services/function_runtime/watcher.py
from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
from pathlib import Path

from app.services.function_runtime.models import FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry

logger = logging.getLogger(__name__)


class FunctionWatcher:
    def __init__(self, registry: FunctionRegistry, workspace_root: str):
        self.registry = registry
        self.workspace_root = workspace_root
        self._observer = None
        self._file_functions: dict[str, list[str]] = {}

    def start(self) -> None:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class _Handler(FileSystemEventHandler):
                def __init__(self, watcher: FunctionWatcher):
                    self.watcher = watcher

                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_changed(event.src_path)

                def on_created(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_changed(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory and event.src_path.endswith(".py"):
                        self.watcher._on_file_deleted(event.src_path)

            self._observer = Observer()
            self._observer.schedule(_Handler(self), self.workspace_root, recursive=True)
            self._observer.daemon = True
            self._observer.start()
            logger.info(f"FunctionWatcher started on {self.workspace_root}")
        except ImportError:
            logger.warning("watchdog not installed, using polling fallback disabled")

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("FunctionWatcher stopped")

    def scan_file(self, path: str) -> list[FunctionMeta]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Cannot read {path}: {e}")
            return []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            logger.warning(f"Syntax error in {path}, skipping")
            return []

        checksum = hashlib.md5(code.encode()).hexdigest()
        ontology_id = self._extract_ontology_id(path)
        metas: list[FunctionMeta] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            meta = self._extract_function_meta(node, path, ontology_id, checksum)
            if meta:
                metas.append(meta)

        return metas

    def scan_all(self, ontology_id: int | None = None) -> None:
        root = Path(self.workspace_root)
        if not root.exists():
            return
        for py_file in root.rglob("*.py"):
            metas = self.scan_file(str(py_file))
            for meta in metas:
                if ontology_id is not None and meta.ontology_id != ontology_id:
                    continue
                self.registry.register(meta)
                self._track_file(str(py_file), meta.callable_name)
        logger.info(f"scan_all complete, workspace={self.workspace_root}")

    def _on_file_changed(self, path: str) -> None:
        old_names = set(self._file_functions.get(path, []))
        metas = self.scan_file(path)
        new_names = {m.callable_name for m in metas}

        for meta in metas:
            self.registry.register(meta)

        for removed in old_names - new_names:
            self.registry.unregister(removed)

        self._file_functions[path] = list(new_names)

    def _on_file_deleted(self, path: str) -> None:
        names = self._file_functions.pop(path, [])
        for name in names:
            self.registry.unregister(name)

    def _track_file(self, path: str, callable_name: str) -> None:
        if path not in self._file_functions:
            self._file_functions[path] = []
        if callable_name not in self._file_functions[path]:
            self._file_functions[path].append(callable_name)

    def _extract_ontology_id(self, path: str) -> int:
        rel = os.path.relpath(path, self.workspace_root)
        parts = Path(rel).parts
        if parts and parts[0].isdigit():
            return int(parts[0])
        return 0

    def _extract_function_meta(
        self, node: ast.FunctionDef, path: str, ontology_id: int, checksum: str
    ) -> FunctionMeta | None:
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if isinstance(func, ast.Name) and func.id == "Function":
                pass
            elif isinstance(func, ast.Attribute) and func.attr == "Function":
                pass
            else:
                continue

            kwargs = {}
            for kw in dec.keywords:
                kwargs[kw.arg] = self._eval_literal(kw.value)

            name = kwargs.get("name")
            if not name:
                continue

            params_raw = kwargs.get("params") or []
            params = [
                ParamSchema(
                    name=p.get("name", ""),
                    type=p.get("type", "string"),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                )
                for p in params_raw
                if isinstance(p, dict)
            ]

            return FunctionMeta(
                callable_name=name,
                description=kwargs.get("description", ""),
                type=kwargs.get("type", "logic"),
                params=params,
                return_type=kwargs.get("return_type", "object"),
                source_path=path,
                func_name=node.name,
                ontology_id=ontology_id,
                checksum=checksum,
            )
        return None

    @staticmethod
    def _eval_literal(node: ast.expr):
        try:
            return ast.literal_eval(node)
        except (ValueError, TypeError):
            return None
```

- [ ] **Step 5: Update __init__.py exports**

Add to `backend/app/services/function_runtime/__init__.py`:

```python
from .watcher import FunctionWatcher
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pip install watchdog>=4.0 && python -m pytest tests/test_function_runtime_watcher.py -v`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/function_runtime/watcher.py \
        backend/app/services/function_runtime/__init__.py \
        backend/requirements.txt \
        backend/tests/test_function_runtime_watcher.py
git commit -m "新增文件监听：watchdog + AST 扫描 @Function 装饰器自动注册"
```

---

### Task 6: Agent 工具层改造（agent_tools.py + tool_router.py）

**Files:**
- Modify: `backend/app/services/agent_tools.py` — 新增 6 个 AgentToolSpec
- Modify: `backend/app/services/agent/tool_router.py` — 新增 6 个 handler + 注入 executor
- Test: `backend/tests/test_agent_tools_tier2.py`

**Interfaces:**
- Consumes: `FunctionRuntimeExecutor` from Task 4; `FunctionRegistry` from Task 3; `EntityDataService` (existing)
- Produces:
  - 6 new agent tools: `ontology_query_instances`, `ontology_get_attr_mapping`, `ontology_complex_sql`, `ontology_list_capabilities`, `ontology_run_logic`, `ontology_run_action`
  - `ToolRouter.__init__(db, runtime_executor=None)` — optional executor injection

- [ ] **Step 1: Write tests for Tier 2 tools**

```python
# backend/tests/test_agent_tools_tier2.py
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.services.function_runtime.executor import FunctionRuntimeExecutor
from app.services.function_runtime.models import ExecResult, FunctionMeta, ParamSchema
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.agent.tool_router import ToolRouter


@pytest.fixture
def setup_with_runtime(tmp_path):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    registry = FunctionRegistry(db)
    sandbox = UnifiedSandbox()
    executor = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=db)

    code = '''
def calc_demo(params):
    return params["x"] * 2
'''
    os.makedirs(tmp_path / "1" / "calc_demo")
    path = tmp_path / "1" / "calc_demo" / "main.py"
    path.write_text(code)

    registry.register(FunctionMeta(
        callable_name="calc_demo", description="演示", type="logic",
        params=[ParamSchema(name="x", type="number", required=True, description="")],
        return_type="number",
        source_path=str(path), func_name="calc_demo", ontology_id=1, checksum="x",
    ))

    router = ToolRouter(db, runtime_executor=executor)
    return router, registry


class TestListCapabilities:
    def test_returns_registered_functions(self, setup_with_runtime):
        router, _ = setup_with_runtime
        result, summary, count = router.execute("ontology_list_capabilities", {"type": "all"})
        assert count >= 1
        names = [c["name"] for c in result]
        assert "calc_demo" in names

    def test_filter_by_type(self, setup_with_runtime):
        router, _ = setup_with_runtime
        result, _, _ = router.execute("ontology_list_capabilities", {"type": "action"})
        names = [c["name"] for c in result]
        assert "calc_demo" not in names


class TestRunLogic:
    def test_execute_logic_function(self, setup_with_runtime):
        router, _ = setup_with_runtime
        result, summary, _ = router.execute("ontology_run_logic", {
            "callable_name": "calc_demo",
            "params": {"x": 5},
        })
        assert result["success"] is True
        assert result["result"] == 10

    def test_run_logic_not_found(self, setup_with_runtime):
        router, _ = setup_with_runtime
        result, _, _ = router.execute("ontology_run_logic", {
            "callable_name": "nonexistent",
            "params": {},
        })
        assert result["success"] is False

    def test_run_logic_rejects_action_type(self, setup_with_runtime):
        router, registry = setup_with_runtime
        registry.register(FunctionMeta(
            callable_name="my_action", description="", type="action",
            params=[], return_type="object",
            source_path="/fake", func_name="my_action", ontology_id=1, checksum="x",
        ))
        result, _, _ = router.execute("ontology_run_logic", {
            "callable_name": "my_action",
            "params": {},
        })
        assert result["success"] is False
        assert "logic" in str(result.get("error", "")).lower() or "类型" in str(result.get("error", ""))


class TestRunAction:
    def test_run_action_success(self, setup_with_runtime, tmp_path):
        router, registry = setup_with_runtime
        code = '''
def export_data(params):
    return {"path": "/tmp/out.csv"}
'''
        os.makedirs(tmp_path / "1" / "export", exist_ok=True)
        path = tmp_path / "1" / "export" / "main.py"
        path.write_text(code)
        registry.register(FunctionMeta(
            callable_name="export_data", description="导出", type="action",
            params=[], return_type="object",
            source_path=str(path), func_name="export_data", ontology_id=1, checksum="x",
        ))
        result, _, _ = router.execute("ontology_run_action", {
            "callable_name": "export_data",
            "params": {},
        })
        assert result["success"] is True


class TestToolSpecRegistration:
    def test_new_tools_in_spec_list(self):
        from app.services.agent_tools import AGENT_TOOL_SPECS
        names = [s.name for s in AGENT_TOOL_SPECS]
        assert "ontology_list_capabilities" in names
        assert "ontology_run_logic" in names
        assert "ontology_run_action" in names
        assert "ontology_query_instances" in names
        assert "ontology_get_attr_mapping" in names
        assert "ontology_complex_sql" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agent_tools_tier2.py -v`
Expected: Failures — new tools not yet defined

- [ ] **Step 3: Add 6 new AgentToolSpec entries to agent_tools.py**

Append before the closing `)` of `AGENT_TOOL_SPECS` tuple in `backend/app/services/agent_tools.py`:

```python
    # ── Tier 1: 数据查询（重构） ──
    AgentToolSpec(
        name="ontology_query_instances",
        description="查询本体实体的实例数据，支持条件过滤和分页。优先使用此工具。",
        parameters={
            "entity_name": {"type": "string", "description": "实体名称"},
            "filters": {"type": "object", "description": "过滤条件 {属性名: 值}"},
            "page": {"type": "integer", "description": "页码，默认 1"},
            "page_size": {"type": "integer", "description": "每页条数，默认 50，最大 200"},
        },
        required=("entity_name",),
    ),
    AgentToolSpec(
        name="ontology_get_attr_mapping",
        description="获取实体属性到物理数据库字段的映射关系，用于编写 SQL 前了解字段名。",
        parameters={
            "entity_names": {"type": "array", "items": {"type": "string"}, "description": "实体名称列表"},
        },
        required=("entity_names",),
    ),
    AgentToolSpec(
        name="ontology_complex_sql",
        description="执行复杂只读 SQL 查询（CTE/窗口函数/多表 JOIN）。需先通过 get_attr_mapping 获取字段名。仅允许 SELECT。",
        parameters={
            "sql": {"type": "string", "description": "SQL 语句（使用物理字段名）"},
            "params": {"type": "array", "items": {"type": "string"}, "description": "参数化查询的参数值列表"},
        },
        required=("sql",),
    ),
    # ── Tier 2: 逻辑/动作调用 ──
    AgentToolSpec(
        name="ontology_list_capabilities",
        description="列出当前本体可用的所有逻辑函数和动作函数，返回名称、描述、参数 schema。",
        parameters={
            "type": {"type": "string", "enum": ["logic", "action", "all"], "description": "过滤类型，默认 all"},
        },
    ),
    AgentToolSpec(
        name="ontology_run_logic",
        description="执行指定的逻辑函数，返回计算结果。函数名通过 list_capabilities 获取。",
        parameters={
            "callable_name": {"type": "string", "description": "函数名称"},
            "params": {"type": "object", "description": "函数所需参数"},
        },
        required=("callable_name",),
    ),
    AgentToolSpec(
        name="ontology_run_action",
        description="执行指定的动作函数（如生成报告、导出数据），可能有副作用。",
        parameters={
            "callable_name": {"type": "string", "description": "动作名称"},
            "params": {"type": "object", "description": "动作所需参数"},
        },
        required=("callable_name",),
        sensitive=True,
    ),
```

- [ ] **Step 4: Modify ToolRouter to accept runtime_executor and add handlers**

In `backend/app/services/agent/tool_router.py`:

1. Change `__init__`:
```python
def __init__(self, db: Session, runtime_executor=None):
    self.db = db
    self.runtime_executor = runtime_executor
```

2. Add new handlers to the `handlers` dict in `execute()`:
```python
"ontology_list_capabilities": self._tool_list_capabilities,
"ontology_run_logic": self._tool_run_logic,
"ontology_run_action": self._tool_run_action,
"ontology_query_instances": self._tool_query_instances,
"ontology_get_attr_mapping": self._tool_get_attr_mapping,
"ontology_complex_sql": self._tool_complex_sql,
```

3. Add handler methods:
```python
    def _tool_list_capabilities(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        type_filter = args.get("type", "all")
        caps = self.runtime_executor.registry.list_capabilities()
        if type_filter != "all":
            caps = [c for c in caps if c["type"] == type_filter]
        return caps, f"找到 {len(caps)} 个可用函数", len(caps)

    def _tool_run_logic(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        callable_name = args.get("callable_name", "")
        params = args.get("params", {})
        meta = self.runtime_executor.registry.get(callable_name)
        if meta and meta.type != "logic":
            return {"success": False, "error": f"'{callable_name}' 类型为 {meta.type}，不是 logic"}, "类型不匹配", 0
        result = self.runtime_executor.execute(callable_name, params)
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_ms": result.execution_ms,
            "call_trace": result.call_trace,
        }, f"逻辑函数{'成功' if result.success else '失败'}: {callable_name}", 1

    def _tool_run_action(self, args: dict) -> tuple[Any, str, int]:
        if not self.runtime_executor:
            return {"error": "Function runtime not initialized"}, "运行时未就绪", 0
        callable_name = args.get("callable_name", "")
        params = args.get("params", {})
        meta = self.runtime_executor.registry.get(callable_name)
        if meta and meta.type != "action":
            return {"success": False, "error": f"'{callable_name}' 类型为 {meta.type}，不是 action"}, "类型不匹配", 0
        result = self.runtime_executor.execute(callable_name, params)
        return {
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_ms": result.execution_ms,
            "call_trace": result.call_trace,
        }, f"动作函数{'成功' if result.success else '失败'}: {callable_name}", 1

    def _tool_query_instances(self, args: dict) -> tuple[Any, str, int]:
        entity_name = str(args.get("entity_name", "")).strip()
        filters = args.get("filters") or {}
        page = int(args.get("page", 1))
        page_size = min(int(args.get("page_size", 50)), 200)
        if not entity_name:
            return {"error": "需要提供 entity_name"}, "参数不完整", 0

        entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == entity_name).first()
        if not entity:
            return {"error": f"本体中不存在实体 '{entity_name}'"}, "实体不存在", 0

        valid_attrs = {a.name for a in entity.attributes}
        svc = EntityDataService(self.db)
        offset = (page - 1) * page_size
        result = svc.query_entity_data(
            entity.id, filters=filters, fields=[], limit=page_size,
            purpose="agent.query_instances", valid_attrs=valid_attrs,
        )
        if "error" in result:
            return result, f"查询失败: {result['error']}", 0
        result["entity"] = entity_name
        result["page"] = page
        return result, f"查询 {entity.name_cn} 第{page}页，返回 {result.get('rowCount', 0)} 条", result.get("rowCount", 0)

    def _tool_get_attr_mapping(self, args: dict) -> tuple[Any, str, int]:
        entity_names = args.get("entity_names", [])
        if not entity_names:
            return {"error": "需要提供 entity_names"}, "参数不完整", 0

        mapping = {}
        for name in entity_names:
            entity = self.db.query(OntologyEntity).filter(OntologyEntity.name == name).first()
            if not entity:
                mapping[name] = {"error": f"实体 '{name}' 不存在"}
                continue
            svc = EntityDataService(self.db)
            resolved = svc.resolve_entity_asset(entity.id)
            if not resolved:
                mapping[name] = {"error": "未绑定数据源"}
                continue
            asset, binding = resolved
            table_name = svc.get_table_name(asset)
            attrs = {}
            for a in entity.attributes:
                attrs[a.name] = a.name
            mapping[name] = {"table": table_name, "attributes": attrs}
        return mapping, f"返回 {len(entity_names)} 个实体的映射", len(entity_names)

    def _tool_complex_sql(self, args: dict) -> tuple[Any, str, int]:
        sql = str(args.get("sql", "")).strip()
        if not sql:
            return {"error": "需要提供 sql"}, "参数不完整", 0
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return {"error": "只允许 SELECT/WITH 语句"}, "非法 SQL", 0

        svc = EntityDataService(self.db)
        assets = svc.list_assets()
        if not assets:
            return {"error": "没有可用数据源"}, "无数据源", 0
        first_asset_name = assets[0].get("name", "")
        result = svc.execute_sql_on_asset(first_asset_name, sql, purpose="agent.complex_sql")
        if "error" in result:
            return result, f"SQL 执行失败: {result['error']}", 0
        return result, f"SQL 查询返回 {result.get('rowCount', 0)} 行", result.get("rowCount", 0)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent_tools_tier2.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_tools.py \
        backend/app/services/agent/tool_router.py \
        backend/tests/test_agent_tools_tier2.py
git commit -m "Agent 工具层改造：新增 Tier 1 三工具 + Tier 2 三工具"
```

---

### Task 7: 系统集成（兼容层 + call_function 执行器 + 启动初始化）

**Files:**
- Modify: `backend/app/services/function_executor.py` — 降级为兼容层
- Modify: `backend/app/services/action_executors/call_function.py` — 补全实现
- Modify: `backend/app/main.py` — 启动时初始化 FunctionWatcher
- Create: `workspace/sample/calc_demo/main.py` — 示例函数文件

**Interfaces:**
- Consumes: `FunctionRuntimeExecutor` from Task 4; `FunctionRegistry` from Task 3; `FunctionWatcher` from Task 5
- Produces: 系统启动时自动初始化 function runtime，ToolRouter 获得 runtime_executor 注入

- [ ] **Step 1: Modify FunctionExecutor as compatibility layer**

Replace `_execute_python` method in `backend/app/services/function_executor.py`:

```python
    def _execute_python(self, func: OntologyFunction, params: dict) -> Any:
        if func.source_path and func.callable_name:
            from app.services.function_runtime import FunctionRuntimeExecutor
            from app.services.function_runtime.registry import FunctionRegistry
            from app.services.function_runtime.sandbox import UnifiedSandbox
            registry = FunctionRegistry(self.db)
            sandbox = UnifiedSandbox()
            runtime = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=self.db)
            result = runtime.execute(func.callable_name, params)
            if result.success:
                return result.result
            raise RuntimeError(result.error)

        if not func.logic_body or not func.logic_body.strip():
            raise ValueError("Python body is empty")
        local_ns: dict = {"params": params, "result": None}
        safe_builtins = {
            "abs": abs, "max": max, "min": min, "round": round, "len": len,
            "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "range": range, "enumerate": enumerate,
            "sum": sum, "sorted": sorted, "zip": zip, "map": map, "filter": filter,
        }
        exec(func.logic_body, {"__builtins__": safe_builtins}, local_ns)
        return local_ns.get("result")
```

- [ ] **Step 2: Implement call_function executor**

Replace `backend/app/services/action_executors/call_function.py`:

```python
from .base import BaseActionExecutor, ExecutionResult


class CallFunctionExecutor(BaseActionExecutor):
    async def execute(self, type_config: dict, params: dict, dry_run: bool = False) -> ExecutionResult:
        function_name = type_config.get("function_name") or type_config.get("function_id", "")
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
```

- [ ] **Step 3: Add startup initialization to main.py**

In `backend/app/main.py`, add to the `lifespan` or startup logic (after existing model imports):

```python
# Function Runtime initialization
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.function_runtime.executor import FunctionRuntimeExecutor
from app.services.function_runtime.watcher import FunctionWatcher

_function_watcher: FunctionWatcher | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _function_watcher
    # ... existing startup code ...

    # Init function runtime
    db = SessionLocal()
    try:
        workspace_root = str(Path(__file__).resolve().parent.parent.parent / "workspace")
        registry = FunctionRegistry(db)
        registry.sync_from_db()
        sandbox = UnifiedSandbox()
        runtime_executor = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=db)
        _function_watcher = FunctionWatcher(registry=registry, workspace_root=workspace_root)
        _function_watcher.scan_all()
        _function_watcher.start()
        app.state.runtime_executor = runtime_executor
        app.state.function_registry = registry
    except Exception as e:
        logger.warning(f"Function runtime init failed: {e}")
    finally:
        pass  # db kept alive for registry

    yield

    # Shutdown
    if _function_watcher:
        _function_watcher.stop()
```

- [ ] **Step 4: Create sample function file**

```python
# workspace/sample/calc_demo/main.py
from ontology_runtime import Function, call_function


@Function(
    name="calc_demo",
    description="演示函数：输入数字翻倍返回",
    type="logic",
    params=[
        {"name": "x", "type": "number", "required": True, "description": "输入数字"},
    ],
    return_type="number",
)
def calc_demo(params):
    return params["x"] * 2
```

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q`
Expected: All existing tests + new tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/function_executor.py \
        backend/app/services/action_executors/call_function.py \
        backend/app/main.py \
        workspace/sample/calc_demo/main.py
git commit -m "系统集成：FunctionExecutor 兼容层 + call_function 执行器补全 + 启动初始化"
```

---

### Task 8: 端到端验证与清理

**Files:**
- Verify all components work together
- Clean up any issues

**Interfaces:**
- Consumes: All previous tasks

- [ ] **Step 1: Create end-to-end integration test**

```python
# backend/tests/test_function_runtime_e2e.py
"""端到端测试：模拟从文件写入到 Agent 工具调用的完整链路"""
import os
from unittest.mock import MagicMock

import pytest

from app.services.function_runtime.executor import FunctionRuntimeExecutor
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.function_runtime.watcher import FunctionWatcher
from app.services.agent.tool_router import ToolRouter


LOGIC_CODE = '''
from ontology_runtime import Function, call_function

@Function(
    name="factor_calc",
    description="计算因子",
    type="logic",
    params=[{"name": "value", "type": "number", "required": True, "description": "基础值"}],
    return_type="number",
)
def factor_calc(params):
    return params["value"] * 1.5
'''

ACTION_CODE = '''
from ontology_runtime import Function, call_function

@Function(
    name="gen_report",
    description="生成报告",
    type="action",
    params=[{"name": "value", "type": "number", "required": True, "description": ""}],
    return_type="object",
)
def gen_report(params):
    factor = call_function("factor_calc", {"value": params["value"]})
    return {"report": f"Factor is {factor}", "raw": factor}
'''


class TestEndToEnd:
    def test_full_lifecycle(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        # 1. Setup runtime components
        registry = FunctionRegistry(db)
        sandbox = UnifiedSandbox()
        executor = FunctionRuntimeExecutor(registry=registry, sandbox=sandbox, db=db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        # 2. Write function files (simulating user saving in code-server)
        os.makedirs(tmp_path / "1" / "factor_calc")
        os.makedirs(tmp_path / "1" / "gen_report")
        (tmp_path / "1" / "factor_calc" / "main.py").write_text(LOGIC_CODE)
        (tmp_path / "1" / "gen_report" / "main.py").write_text(ACTION_CODE)

        # 3. Watcher scans (simulating file save trigger)
        watcher.scan_all()

        # 4. Verify registration
        assert registry.get("factor_calc") is not None
        assert registry.get("gen_report") is not None
        caps = registry.list_capabilities()
        assert len(caps) == 2

        # 5. Execute via ToolRouter (simulating Agent calling tools)
        router = ToolRouter(db, runtime_executor=executor)

        # list_capabilities
        result, _, count = router.execute("ontology_list_capabilities", {"type": "all"})
        assert count == 2

        # run_logic
        result, _, _ = router.execute("ontology_run_logic", {
            "callable_name": "factor_calc", "params": {"value": 10}
        })
        assert result["success"] is True
        assert result["result"] == 15.0

        # run_action (calls factor_calc internally via call_function)
        result, _, _ = router.execute("ontology_run_action", {
            "callable_name": "gen_report", "params": {"value": 10}
        })
        assert result["success"] is True
        assert result["result"]["raw"] == 15.0
        assert "Factor is 15.0" in result["result"]["report"]

    def test_file_update_triggers_re_registration(self, tmp_path):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        registry = FunctionRegistry(db)
        watcher = FunctionWatcher(registry=registry, workspace_root=str(tmp_path))

        os.makedirs(tmp_path / "1" / "myfn")
        file_path = str(tmp_path / "1" / "myfn" / "main.py")

        # Write v1
        with open(file_path, "w") as f:
            f.write(LOGIC_CODE)
        watcher._on_file_changed(file_path)
        assert registry.get("factor_calc") is not None
        assert registry.get("factor_calc").description == "计算因子"

        # Write v2 with updated description
        updated = LOGIC_CODE.replace("计算因子", "计算折损因子v2")
        with open(file_path, "w") as f:
            f.write(updated)
        watcher._on_file_changed(file_path)
        assert registry.get("factor_calc").description == "计算折损因子v2"
```

- [ ] **Step 2: Run end-to-end test**

Run: `cd backend && python -m pytest tests/test_function_runtime_e2e.py -v`
Expected: All 2 tests PASS

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -30`
Expected: No regressions in existing tests

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_function_runtime_e2e.py
git commit -m "端到端集成测试：完整链路验证（文件保存 → 注册 → Agent 调用 → 互调）"
```

---

## Execution Summary

| Task | 交付物 | 依赖 |
|------|--------|------|
| 1 | models.py + decorator.py | 无 |
| 2 | sandbox.py | 无 |
| 3 | registry.py + DB 字段 | Task 1 |
| 4 | executor.py | Task 1, 2, 3 |
| 5 | watcher.py + watchdog | Task 1, 3 |
| 6 | agent_tools + tool_router | Task 3, 4 |
| 7 | 兼容层 + 启动初始化 | Task 3, 4, 5 |
| 8 | 端到端测试 | All |

Tasks 1 和 2 可以并行。Tasks 3 依赖 1。Task 4 依赖 1+2+3。Task 5 依赖 1+3。Tasks 6 和 7 依赖 3+4。Task 8 在所有任务完成后执行。
