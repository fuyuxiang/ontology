import pytest
from unittest.mock import MagicMock, patch
from app.services.function_executor import FunctionExecutor, FunctionResult


def _make_function(logic_type="expression", logic_body="", input_schema=None):
    fn = MagicMock()
    fn.id = "fn-001"
    fn.name = "test_func"
    fn.logic_type = logic_type
    fn.logic_body = logic_body
    fn.input_schema = input_schema or []
    fn.entity_id = None
    fn.execution_count = 0
    fn.last_executed = None
    return fn


class TestExpressionExecution:
    def test_simple_arithmetic(self):
        fn = _make_function("expression", "params['a'] + params['b']")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"a": 3, "b": 4})
        assert result.success is True
        assert result.value == 7

    def test_expression_error(self):
        fn = _make_function("expression", "1 / 0")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False
        assert result.error is not None

    def test_empty_body(self):
        fn = _make_function("expression", "")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False

    def test_builtin_functions(self):
        fn = _make_function("expression", "round(abs(params['x']) * 1.5, 2)")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"x": -3.333})
        assert result.success is True
        assert result.value == 5.0


class TestPythonExecution:
    def test_python_sandbox(self):
        fn = _make_function("python", "result = params['x'] * 2")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"x": 5})
        assert result.success is True
        assert result.value == 10

    def test_python_with_loop(self):
        fn = _make_function("python", "result = sum(range(params['n']))")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {"n": 5})
        assert result.success is True
        assert result.value == 10

    def test_python_empty_body(self):
        fn = _make_function("python", "")
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False


class TestSqlExecution:
    def test_sql_returns_value(self):
        fn = _make_function("sql", "SELECT COUNT(*) FROM users")
        fn.entity_id = "entity-001"
        db = MagicMock()
        executor = FunctionExecutor(db)
        with patch.object(executor, '_execute_sql', return_value={"rows": [[42]], "columns": ["count"]}):
            result = executor.execute(fn, {})
            assert result.success is True
            assert result.value == 42

    def test_sql_no_entity(self):
        fn = _make_function("sql", "SELECT 1")
        fn.entity_id = None
        db = MagicMock()
        executor = FunctionExecutor(db)
        result = executor.execute(fn, {})
        assert result.success is False


class TestRequiredParams:
    def test_missing_required_param_fails(self):
        fn = _make_function("expression", "params['a'] + params['b']",
                            input_schema=[{"name": "a", "required": True}, {"name": "b", "required": True}])
        executor = FunctionExecutor(MagicMock())
        result = executor.execute(fn, {"a": 1})
        assert result.success is False
        assert "缺少必填参数" in result.error
        assert "b" in result.error

    def test_all_required_present_runs(self):
        fn = _make_function("expression", "params['a'] + params['b']",
                            input_schema=[{"name": "a", "required": True}, {"name": "b", "required": True}])
        executor = FunctionExecutor(MagicMock())
        result = executor.execute(fn, {"a": 1, "b": 2})
        assert result.success is True
        assert result.value == 3

    def test_optional_param_not_blocking(self):
        fn = _make_function("expression", "params['a']",
                            input_schema=[{"name": "a", "required": True}, {"name": "b", "required": False}])
        executor = FunctionExecutor(MagicMock())
        result = executor.execute(fn, {"a": 9})
        assert result.success is True
        assert result.value == 9


class TestCallableNameLookup:
    def test_execute_by_callable_name_found(self):
        fn = _make_function("expression", "params['x'] + 1")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = fn
        executor = FunctionExecutor(db)
        result = executor.execute_by_callable_name("calc_score", {"x": 5})
        assert result.success is True
        assert result.value == 6

    def test_execute_by_callable_name_not_found(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        executor = FunctionExecutor(db)
        result = executor.execute_by_callable_name("nonexistent", {})
        assert result.success is False
        assert "not found" in result.error
