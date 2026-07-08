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
        assert metas[0].ontology_id == 0


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
