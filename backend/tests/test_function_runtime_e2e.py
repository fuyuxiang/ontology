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
        """完整链路：文件写入 → watcher 扫描 → registry 注册 → ToolRouter 调用 → 函数互调"""
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
        """文件更新后 watcher 重新注册，metadata 正确更新"""
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
