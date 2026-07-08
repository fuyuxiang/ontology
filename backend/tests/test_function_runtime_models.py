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
