import os
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
            params=[], return_type="number",
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
        os.makedirs(tmp_path / "a", exist_ok=True)
        path_a = _write_function_file(tmp_path / "a", code_a)
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
