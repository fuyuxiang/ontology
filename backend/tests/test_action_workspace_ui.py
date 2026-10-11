"""UI-created actions preserve display names and safe callable workspaces."""
import ast
from types import SimpleNamespace

from app.api.v1 import actions
from app.schemas.action import ActionCreate


def test_ui_custom_script_keeps_display_and_callable_names():
    value = ActionCreate(name="创建检修工单", category="system", action_type="custom_script", type_config={"callable_name": "create_work_order"})
    assert value.name == "创建检修工单"
    assert value.type_config["callable_name"] == "create_work_order"


def test_workspace_uses_callable_identifier_and_retains_legacy_fallback(tmp_path, monkeypatch):
    action = SimpleNamespace(name="创建检修工单", description='包含"引号"\n与换行', type_config={"callable_name": "create_work_order"})
    monkeypatch.setattr(actions, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(actions, "ActionRepository", lambda _db: SimpleNamespace(get_by_id=lambda _id: action))
    result = actions.open_action_workspace("action1", db=None, user=None)
    assert result.folder == str(tmp_path / "create_work_order")
    tree = ast.parse((tmp_path / "create_work_order" / "main.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    assert function.name == "create_work_order"
    description = next(item.value for item in function.decorator_list[0].keywords if item.arg == "description")
    assert description.value == action.description

    action.name = "legacy_action"
    action.type_config = None
    legacy = actions.open_action_workspace("action1", db=None, user=None)
    assert legacy.folder == str(tmp_path / "legacy_action")
    assert (tmp_path / "legacy_action" / "main.py").exists()


def test_legacy_non_identifier_display_name_still_generates_valid_python():
    ast.parse(actions._generate_action_template("2026 检修行动", '"输入"\n中文'))
    ast.parse(actions._generate_action_template("class", '"输入"\n中文'))
