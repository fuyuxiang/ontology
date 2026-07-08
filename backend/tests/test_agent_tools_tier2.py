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
