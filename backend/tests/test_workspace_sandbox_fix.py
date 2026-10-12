"""Actual workspace subprocesses use curated imports, including the legacy bridge."""
import asyncio
import json

import pytest

from app.services.mcp_tools import python_workspace as workspace


@pytest.fixture
def run_file(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, 'PYTHON_WORKSPACE_BASE', str(tmp_path))
    def invoke(source, **arguments):
        path = tmp_path / 'fixture' / 'main.py'
        path.parent.mkdir(exist_ok=True)
        path.write_text(source)
        return asyncio.run(workspace.RunPythonFileTool().execute({
            'ontology_name': 'fixture', 'file_path': 'main.py', 'user_id': 'fixture', **arguments}))
    return invoke


def test_workspace_program_and_main_guard_keep_legacy_helpers(run_file):
    result = run_file('import json\nimport math\nfrom __ontology_runtime__ import get_object\n'
                      'if __name__ == "__main__":\n    print(json.dumps({"name":get_object("Device"),"value":math.sqrt(16)}))\n')
    assert result['success'], result
    assert json.loads(result['stdout']) == {'name': 'Device', 'value': 4}


def test_workspace_cannot_obtain_host_modules_from_standard_data_imports(run_file):
    result = run_file('import dataclasses\nprint(dataclasses.sys)')
    assert not result['success']
    assert result['stdout'] == ''
    assert 'AttributeError' in result['stderr']
    rejected = run_file('from dataclasses import sys\nprint(0)')
    assert 'error' in rejected


def test_workspace_timeout_and_invalid_deadline_are_explicit(run_file):
    result = run_file('while True: pass', timeout_sec=1)
    assert not result['success'] and result['exit_code'] != 0
    assert '超时' in result['stderr']
    assert 'error' in run_file('print(1)', timeout_sec=-1)
