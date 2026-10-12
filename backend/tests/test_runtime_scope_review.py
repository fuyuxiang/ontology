"""Real isolated source receipts for scope, previews, approvals and graph continuation."""
import asyncio
import sqlite3
from types import SimpleNamespace

import pytest

from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from app.models.action import EntityAction
from app.models.agent import Agent
from app.models.agent_runtime import AgentRun, AgentPendingAction
from app.models.entity import OntologyEntity, EntityAttribute
from app.models.function import OntologyFunction
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity, OntologyVersionAttribute
from app.models.version_components import OntologyVersionFunction, OntologyVersionAction
from app.services.agent.managed_runtime import ManagedToolRouter
from app.services.agent.graph_engine import GraphEngine
from app.services.agent_management import config_hash, config_snapshot
from app.services.version_component_snapshot import capture_binding
from app.services.data_plane.object_binding_service import ObjectBindingService


@pytest.fixture
def runtime(data_env, monkeypatch):
    db, source = data_env
    bind(db)
    db.add(OntologyEntity(id="other", name="Other", name_cn="Other", ontology_id="a", tier=1))
    db.flush()
    db.add_all([EntityAttribute(id="other-id", entity_id="other", name="id", type="string"),
                EntityAttribute(id="other-temperature", entity_id="other", name="temperature", type="number")])
    db.flush()
    ObjectBindingService(db).create(object_type_id="other", asset_id="asset", id_column="device_id",
        field_mappings=[{"attribute_id": "other-id", "source_column": "device_id"},
                        {"attribute_id": "other-temperature", "source_column": "temp"}])
    version = OntologyVersion(id="v", ontology_id="a", version_number=1, name="v", status="published", is_active=True)
    db.add(version)
    db.flush()
    for eid, name in [("device", "Device"), ("other", "Other")]:
        ve = OntologyVersionEntity(id="v-"+eid, version_id="v", source_entity_id=eid, name=name, name_cn=name,
            tier=1, binding_snapshot=capture_binding(db, eid))
        db.add(ve)
        db.flush()
        db.add_all([OntologyVersionAttribute(version_entity_id=ve.id, source_attribute_id=a.id,
            name=a.name, type=a.type) for a in db.query(EntityAttribute).filter_by(entity_id=eid)])
    bodies = {"read_other": 'result = query_objects("Other", {}, 1)',
              "read": 'result = query_objects("Device", {}, 1)',
              "write": 'result = update_object("Device", "d1", {"temperature": 12})',
              "nested_write": 'result = call_function("write", {})',
              "nested_other": 'result = call_function("outside", {})',
              "outside": 'result = query_objects("Other", {}, 1)'}
    for fid, body in bodies.items():
        db.add(OntologyVersionFunction(id="v-"+fid, version_id="v", source_function_id=fid,
            version_entity_id="v-other" if fid == "outside" else "v-device", name=fid, callable_name=fid,
            logic_type="python", logic_body=body, input_schema=[], ontology_id="a"))
    admin = User(id="runtime-admin", username="runtime-admin", name="Admin", password_hash="x", role="admin", is_active=True)
    viewer = User(id="runtime-viewer", username="runtime-viewer", name="Viewer", password_hash="x", role="viewer", is_active=True)
    agent = Agent(id="runtime-agent", name="Runtime", entity_ids=["device"], ontology_version_id="v")
    db.add_all([admin, viewer, agent])
    db.flush()
    digest = config_hash(config_snapshot(agent))
    run = AgentRun(id="runtime-run", agent_id=agent.id, config_hash=digest, question="q", user_id=admin.id,
        pending_actions=[], steps=[], tool_runs=[])
    db.add(run)
    db.add(OntologyVersionAction(id="v-action", version_id="v", source_action_id="action",
        version_entity_id="v-device", name="Write", action_type="modify_attribute", category="domain",
        parameters_json=[], type_config={"target_entity_id": "device", "target_attribute": "temperature",
            "value_expression": "expr: 13", "record_id": "d1", "ontology_id": "a"}))
    db.commit()
    monkeypatch.setattr("app.services.agent.graph_engine.get_llm_client", lambda **_: object())
    context = {"ontology_id": "a", "ontology_version_id": "v", "entity_ids": ["device"], "skills": [],
        "action_mode": "confirm", "config_hash": digest, "user": admin, "agent_id": agent.id, "run_id": run.id}
    return SimpleNamespace(db=db, source=source, context=context, admin=admin, viewer=viewer, agent=agent, run=run)


def temperature(runtime):
    with sqlite3.connect(runtime.source) as raw:
        return raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0]


@pytest.mark.parametrize("name", ["read_other", "nested_other"])
@pytest.mark.parametrize("source_code", [False, True])
def test_functions_and_nested_dependencies_cannot_expand_selected_objects(runtime, name, source_code):
    if source_code:
        fn = runtime.db.get(OntologyVersionFunction, "v-"+name)
        fn.source_code = "def entry(params):\n    " + fn.logic_body
        fn.func_name = "entry"
        runtime.db.commit()
    result = ManagedToolRouter(runtime.db, runtime.context).execute("run_function", {"function_id": name, "params": {}})[0]
    assert result["success"] is False and "授权范围" in result["error"]
    assert temperature(runtime) == 90


@pytest.mark.parametrize("name", ["write", "nested_write"])
def test_simulation_stops_before_first_write_and_cannot_claim_completion(runtime, name):
    result = ManagedToolRouter(runtime.db, {**runtime.context, "action_mode": "simulation"}).execute(
        "run_function", {"function_id": name, "params": {}})[0]
    assert result["simulated"] and result["value"] is None and result["requested_write"]["updates"] == {"temperature": 12}
    assert temperature(runtime) == 90
    assert runtime.db.query(AgentPendingAction).count() == 0


def test_rule_permission_and_action_allowlist_apply_to_functions(runtime):
    router = ManagedToolRouter(runtime.db, {**runtime.context, "user": runtime.viewer})
    assert router.execute("run_function", {"function_id": "read", "params": {}})[0].get("error")
    for mode in ["simulation", "confirm"]:
        router = ManagedToolRouter(runtime.db, {**runtime.context, "action_mode": mode, "allowed_tools": ["run_function"]})
        assert router.execute("run_function", {"function_id": "read", "params": {}})[0]["success"]
        denied = router.execute("run_function", {"function_id": "write", "params": {}})[0]
        assert denied["success"] is False and "run_action" in denied["error"]
    assert temperature(runtime) == 90


def request_context():
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runtime_executor=None)))


def confirm(runtime, pending):
    from app.api.v1.agents import confirm_action, ActionDecisionRequest
    return confirm_action(runtime.agent.id, pending.id, ActionDecisionRequest(approve=True), request_context(), runtime.db, runtime.admin)


@pytest.mark.parametrize("name", ["write", "nested_write"])
def test_function_confirmation_uses_frozen_definition_and_only_executes_once(runtime, name):
    router = ManagedToolRouter(runtime.db, runtime.context)
    result = router.execute("run_function", {"function_id": name, "params": {}})[0]
    pending = runtime.db.get(AgentPendingAction, result["pending_action"]["pending_id"])
    assert len(pending.action_id) <= 36 and pending.action_snapshot["_runtime_scope"]["entity_ids"] == ["device"]
    assert temperature(runtime) == 90
    assert confirm(runtime, pending)["status"] == "approved"
    assert temperature(runtime) == 12
    with sqlite3.connect(runtime.source) as raw:
        raw.execute("UPDATE devices SET temp=15 WHERE device_id='d1'")
    assert confirm(runtime, pending)["status"] == "approved"
    assert temperature(runtime) == 15


@pytest.mark.parametrize("tail", ["result = 1/0", "result = 5", 'result = call_function("broken", {})'])
def test_partial_script_write_has_uncertain_receipt_and_same_key_never_replays(runtime, tail):
    from app.api.v1.actions import execute_action
    from app.schemas.action import ActionExecuteRequest
    runtime.db.add(OntologyFunction(id="broken", name="broken", callable_name="broken", entity_id="device", ontology_id="a",
        logic_type="expression", logic_body="1/0", input_schema=[], status="active"))
    runtime.db.add(EntityAction(id="partial", name="Partial", ontology_id="a", entity_id="device", action_type="custom_script",
        status="active", parameters_json=[], type_config={"script": 'update_object("Device", "d1", {"temperature": 19})\n'+tail}))
    runtime.db.commit()
    payload = ActionExecuteRequest(params={}, idempotency_key="partial-once")
    receipt = asyncio.run(execute_action("partial", payload, runtime.db, runtime.admin))
    assert receipt.success is False and receipt.state == "unknown"
    assert receipt.output["outcome"] == "partial_committed" and len(receipt.output["committed_writes"]) == 1
    assert temperature(runtime) == 19
    with sqlite3.connect(runtime.source) as raw:
        raw.execute("UPDATE devices SET temp=23 WHERE device_id='d1'")
    repeated = asyncio.run(execute_action("partial", payload, runtime.db, runtime.admin))
    assert repeated.execution_id == receipt.execution_id and repeated.state == "unknown"
    assert temperature(runtime) == 23


@pytest.mark.parametrize("scene", [False, True])
@pytest.mark.parametrize("planner", [False, True])
def test_internal_agent_and_direct_action_pause_and_resume_graph_suffix_once(runtime, monkeypatch, scene, planner):
    if planner:
        class PlannedAgent:
            def __init__(self, db, **kwargs):
                self.router = ManagedToolRouter(db, kwargs["runtime_context"])
            def ask(self, *_):
                result = self.router.execute("run_action", {"action_id": "action", "params": {}})[0]
                yield {"type": "action_pending", **result["pending_action"]}
                yield {"type": "answer", "content": "Awaiting confirmation"}
                yield {"type": "done"}
        monkeypatch.setattr("app.services.agent.orchestrator.AgentService", PlannedAgent)
    nodes = [{"id": "planner", "type": "agentNode" if planner else "action", "data": {"action_id": "action"}},
             {"id": "after", "type": "function", "data": {"function_id": "read"}}]
    graph = GraphEngine(runtime.db, nodes, [{"source": "planner", "target": "after"}], runtime_context=runtime.context, emit_node_io=True)
    events = list(graph.run_for_scene({"question": "q"}) if scene else graph.run("q"))
    pending = runtime.db.query(AgentPendingAction).one()
    assert "after" not in graph.node_io and temperature(runtime) == 90
    assert pending.action_snapshot["_graph_checkpoint"]["mode"] == ("scene" if scene else "chat")
    assert sum(e["type"] == "action_pending" for e in events) == 1
    assert confirm(runtime, pending)["status"] == "approved"
    assert temperature(runtime) == 13
    runtime.db.refresh(runtime.run)
    assert runtime.run.status == "completed" and not runtime.run.error
    after = [e for e in runtime.run.steps if e.get("node_id") == "after" and e["type"] == "node_finished"]
    if scene:
        assert len(after) == 1
    else:
        assert sum(e["type"] == "tool_result" and e.get("tool") == "[function]" for e in runtime.run.steps) == 1
    before = list(runtime.run.steps)
    confirm(runtime, pending)
    runtime.db.refresh(runtime.run)
    assert runtime.run.steps == before


def test_function_test_returns_explicit_incomplete_write_preview(runtime):
    from app.api.v1.functions import test_function as invoke_test
    from app.schemas.function import FunctionTestRequest
    runtime.db.add(OntologyFunction(id="draft-write", name="Draft", callable_name="draft-write", entity_id="device", ontology_id="a",
        logic_type="python", logic_body='update_object("Device", "d1", {"temperature": 25})\nresult = {"completed": True}',
        input_schema=[]))
    runtime.db.commit()
    response = invoke_test("draft-write", FunctionTestRequest(params={}), runtime.db, runtime.admin)
    assert response.simulated and response.outcome == "simulated" and not response.execution_complete
    assert response.result is None and response.requested_write["updates"] == {"temperature": 25}
    assert temperature(runtime) == 90
    assert runtime.db.get(OntologyFunction, "draft-write").execution_count == 0


def test_released_action_uses_frozen_entity_scope_after_draft_moves(runtime):
    from app.api.v1.actions import execute_action
    from app.schemas.action import ActionExecuteRequest
    runtime.db.add(EntityAction(id="frozen-script", name="Moved draft", ontology_id="a", entity_id="other",
        action_type="custom_script", status="active", parameters_json=[], type_config={"script": "result = {}"}))
    runtime.db.add(OntologyVersionAction(id="v-frozen-script", version_id="v", source_action_id="frozen-script",
        version_entity_id="v-device", name="Released script", action_type="custom_script", category="domain",
        parameters_json=[], type_config={"script": 'result = {"updated": update_object("Device", "d1", {"temperature": 17})}'}))
    runtime.db.commit()
    response = asyncio.run(execute_action("frozen-script", ActionExecuteRequest(params={}, version_id="v"),
        runtime.db, runtime.admin))
    assert response.success and response.state == "succeeded" and response.output["outcome"] == "committed"
    assert temperature(runtime) == 17


@pytest.mark.parametrize("scene", [False, True])
def test_loop_confirmation_preserves_completed_items_and_runs_each_remaining_item_once(runtime, scene):
    fn = runtime.db.get(OntologyVersionFunction, "v-write")
    fn.logic_body = 'result = update_object("Device", params["record_id"], {"temperature": 12})'
    fn.input_schema = [{"name": "record_id", "type": "string", "required": True}]
    runtime.db.commit()
    nodes = [{"id": "loop", "type": "loop", "data": {"function_id": "write", "source_field": "items",
        "params": {"record_id": "{item.id}"}}}, {"id": "after", "type": "output", "data": {}}]
    graph = GraphEngine(runtime.db, nodes, [{"source": "loop", "target": "after"}], runtime_context=runtime.context)
    items = {"items": [{"id": "d1"}, {"id": "d2"}]}
    list(graph.run_for_scene(items) if scene else graph.run("q", initial_context=items))
    first = runtime.db.query(AgentPendingAction).one()
    confirm(runtime, first)
    assert temperature(runtime) == 12
    second = runtime.db.query(AgentPendingAction).filter_by(status="pending").one()
    assert second.id != first.id and second.params == {"record_id": "d2"}
    with sqlite3.connect(runtime.source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d2'").fetchone()[0] == 20
        raw.execute("UPDATE devices SET temp=15 WHERE device_id='d1'")
    confirm(runtime, second)
    runtime.db.refresh(runtime.run)
    assert runtime.run.status == "completed" and not runtime.run.error
    assert temperature(runtime) == 15
    with sqlite3.connect(runtime.source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d2'").fetchone()[0] == 12
    confirm(runtime, first)
    confirm(runtime, second)
    assert temperature(runtime) == 15


def test_mcp_execute_uses_authenticated_user_and_returns_real_write_receipt(runtime):
    from app.services.mcp_tools.orm_export_logic import RunLogicTool
    request = SimpleNamespace(state=SimpleNamespace(mcp_user_id=runtime.admin.id))
    result = asyncio.run(RunLogicTool().execute({"ontology_name": "a", "logic_name": "write", "params": {},
        "user_id": runtime.viewer.id}, db=runtime.db, request=request))
    assert result["success"] and result["outcome"] == "committed" and result["committed_writes"]
    assert temperature(runtime) == 12
    request.state.mcp_user_id = runtime.viewer.id
    denied = asyncio.run(RunLogicTool().execute({"ontology_name": "a", "logic_name": "write", "params": {},
        "user_id": runtime.admin.id}, db=runtime.db, request=request))
    assert denied.get("error") and temperature(runtime) == 12


def test_skill_function_context_keeps_version_scope_and_write_mode(runtime):
    from app.services.function_runtime.models import ExecContext
    from app.services.skill_executor import execute_skill_tool_call
    scoped = ExecContext(ontology_id="a", version_id="v", entity_ids=frozenset({"device"}), user=runtime.admin,
        action_mode="simulation")
    preview = execute_skill_tool_call("function", {"function_id": "write"}, {}, runtime.db, context=scoped)
    assert preview["simulated"] and not preview["execution_complete"] and temperature(runtime) == 90
    denied = execute_skill_tool_call("function", {"function_id": "read_other"}, {}, runtime.db, context=scoped)
    assert denied["success"] is False
    scoped.action_mode = "execute"
    receipt = execute_skill_tool_call("function", {"function_id": "nested_write"}, {}, runtime.db, context=scoped)
    assert receipt["success"] and receipt["outcome"] == "committed" and temperature(runtime) == 12


def test_registry_nested_function_cannot_expand_restricted_context(runtime, tmp_path):
    from app.services.function_runtime.registry import FunctionRegistry
    from app.services.function_runtime.models import ExecContext, FunctionMeta
    from app.services.function_runtime.executor import FunctionRuntimeExecutor
    from app.services.function_runtime.sandbox import UnifiedSandbox
    registry = FunctionRegistry(runtime.db)
    for name, entity, body in [("registry_root", "device", 'return call_function("registry_outside", {})'),
                               ("registry_outside", "other", "return 1")]:
        source = tmp_path / (name+".py")
        source.write_text("def entry(params):\n    "+body)
        runtime.db.add(OntologyFunction(id=name, name=name, callable_name=name, entity_id=entity, ontology_id="a",
            source_path=str(source), func_name="entry", logic_type="python", status="active"))
        registry.register(FunctionMeta(name, "", "logic", [], "number", str(source), "entry", "a", "x"))
    runtime.db.commit()
    executor = FunctionRuntimeExecutor(registry, UnifiedSandbox(), runtime.db)
    result = executor.execute("registry_root", {}, ExecContext(ontology_id="a", entity_ids=frozenset({"device"}),
        function_ids=frozenset({"registry_root"}), user=runtime.admin))
    assert result.success is False and "授权范围" in result.error
    assert executor.execute("registry_root", {}).result == 1


def test_call_function_action_preserves_partial_write_and_never_replays(runtime):
    from app.api.v1.actions import execute_action
    from app.schemas.action import ActionExecuteRequest
    runtime.db.add(OntologyFunction(id="partial-function", name="partial-function", callable_name="partial-function",
        entity_id="device", ontology_id="a", logic_type="python", input_schema=[], status="active",
        logic_body='update_object("Device", "d1", {"temperature": 19})\nresult = 1/0'))
    runtime.db.add(EntityAction(id="call-partial", name="Call partial", entity_id="device", ontology_id="a",
        action_type="call_function", status="active", parameters_json=[], type_config={"function_name": "partial-function"}))
    runtime.db.commit()
    payload = ActionExecuteRequest(params={}, idempotency_key="call-partial-once")
    result = asyncio.run(execute_action("call-partial", payload, runtime.db, runtime.admin))
    assert result.state == "unknown" and result.output["outcome"] == "partial_committed"
    assert temperature(runtime) == 19
    with sqlite3.connect(runtime.source) as raw:
        raw.execute("UPDATE devices SET temp=27 WHERE device_id='d1'")
    again = asyncio.run(execute_action("call-partial", payload, runtime.db, runtime.admin))
    assert again.execution_id == result.execution_id and temperature(runtime) == 27
