"""A canvas cannot bypass the managed ontology/skill/action authorization surface."""
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.database import Base
from app.models.action import EntityAction
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.models.scenario import ScenarioDict
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity
from app.models.version_components import OntologyVersionAction, OntologyVersionFunction
from app.services.agent.graph_engine import GraphEngine


@pytest.fixture()
def managed(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.add(ScenarioDict(id="ops", code="ops", name="运维"))
    db.flush()
    db.add(OntologyEntity(id="device", name="Device", name_cn="设备", tier=1, ontology_id="ops"))
    db.flush()
    db.add_all([
        OntologyFunction(id="risk", name="风险计算", ontology_id="ops", entity_id="device",
                         logic_type="expression", logic_body="999"),
        EntityAction(id="notify", name="发送通知", entity_id="device", ontology_id="ops",
                     action_type="http", type_config={"url": "https://draft.invalid"}),
        OntologyVersion(id="ops-v1", name="v1", ontology_id="ops", version_number=1, status="published"),
    ])
    db.flush()
    db.add(OntologyVersionEntity(id="device-v1", version_id="ops-v1", source_entity_id="device",
                                 name="Device", name_cn="设备", tier=1))
    db.flush()
    db.add_all([
        OntologyVersionFunction(id="risk-v1", version_id="ops-v1", source_function_id="risk",
            version_entity_id="device-v1", name="风险计算", logic_type="expression", logic_body="1"),
        OntologyVersionAction(id="notify-v1", version_id="ops-v1", source_action_id="notify",
            version_entity_id="device-v1", name="发送通知", action_type="http", category="domain",
            type_config={"url": "https://published.invalid"}, parameters_json=[]),
    ])
    db.commit()
    monkeypatch.setattr("app.services.agent.graph_engine.get_llm_client", lambda **_: object())
    ctx = {"ontology_id": "ops", "ontology_version_id": "ops-v1", "entity_ids": ["device"],
           "skills": [], "action_mode": "simulation", "config_hash": "test",
           "user": User(id="owner", username="owner", password_hash="x", name="Owner", role="editor", is_active=True)}
    yield db, ctx
    db.close()
    engine.dispose()


def graph(managed, nodes=None, edges=None, context=None):
    db, default = managed
    return GraphEngine(db, nodes or [], edges or [], runtime_context=context or default, emit_node_io=True)


def test_direct_effect_nodes_require_explicit_published_action(managed, monkeypatch):
    calls = []
    monkeypatch.setattr("app.services.action_executors.run_executor_sync", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr("app.services.agent.graph_handlers.execute_skill", lambda *_: pytest.fail("legacy skill executed"))
    monkeypatch.setattr("requests.request", lambda *a, **k: calls.append((a, k)))
    eng = graph(managed)
    for ntype in ("datasource", "notification", "httpCall", "write-back", "writebackOntology", "action", "actionSystem"):
        result, _ = eng._execute_node(ntype, {"url": "https://evil.invalid", "sql": "DELETE FROM x"}, {}, "q")
        assert result.get("error"), ntype
    assert calls == []


def test_mapped_action_uses_fixed_config_and_runtime_simulation(managed, monkeypatch):
    calls = []
    def execute(action_type, config, params, dry_run, db=None):
        calls.append((action_type, config, params, dry_run))
        return SimpleNamespace(success=True, message="预览", output={})
    monkeypatch.setattr("app.services.agent_actions.run_executor_sync", execute)
    eng = graph(managed)
    result, _ = eng._execute_node("httpCall", {"action_id": "notify", "url": "https://evil.invalid",
        "type_config": {"url": "https://evil.invalid"}, "dry_run": False, "params": {"device": "{device}"}},
        {"input": {"device": "P-102"}}, "q")
    assert result["simulated"]
    assert calls == [("http", {"url": "https://published.invalid", "_version_entity_id": "device-v1"}, {"device": "P-102"}, True)]
    assert eng._execute_node("action", {"action_id": "foreign-action"}, {}, "q")[0].get("error")


def test_function_nodes_use_fixed_logic_and_cannot_escape_allowlist(managed):
    eng = graph(managed)
    result, _ = eng._execute_node("function", {"function_id": "risk", "logic_body": "888"}, {}, "q")
    assert result["success"] and result["value"] == 1
    assert eng._execute_node("function", {"function_id": "foreign-function"}, {}, "q")[0].get("error")
    context = {**managed[1], "allowed_tools": ["query_entity_data"]}
    assert graph(managed, context=context)._execute_node("function", {"function_id": "risk"}, {}, "q")[0].get("error")


def test_skill_nodes_load_only_fixed_mounted_instructions_without_registry(managed, monkeypatch):
    monkeypatch.setattr("app.services.agent.graph_handlers.execute_skill", lambda *_: pytest.fail("legacy skill executed"))
    skill = {"skill_id": "diagnosis", "name": "设备诊断", "version": 2,
             "prompt_template": "固定诊断指引", "asset_refs": [], "tools": [], "dependencies": {"assets": []}}
    ctx = {**managed[1], "skills": [skill]}
    eng = graph(managed, context=ctx)
    result, _ = eng._execute_node("skill", {"skill_id": "diagnosis", "version": 2}, {}, "q")
    assert result["instructions"] == "固定诊断指引"
    assert eng._execute_node("skill", {"skill_id": "diagnosis", "version": 1}, {}, "q")[0].get("error")
    assert eng._execute_node("skill", {"skill_id": "foreign-skill"}, {}, "q")[0].get("error")


def test_agent_nodes_use_managed_loop_and_do_not_expand_scope(managed, monkeypatch):
    from app.services.agent.orchestrator import AgentService
    calls = []
    class ScopedAgent:
        def __init__(self, db, **kwargs):
            calls.append(kwargs)
        def ask(self, question):
            yield {"type": "content", "content": "根据发布事实提供建议"}
            yield {"type": "tool_summary", "toolRuns": []}
            yield {"type": "done", "suggestions": []}
    assert AgentService is not None
    monkeypatch.setattr("app.services.agent.orchestrator.AgentService", ScopedAgent)
    eng = graph(managed)
    result, _ = eng._execute_node("agentNode", {"objectTypes": ["Device"]}, {}, "q")
    assert result["answer"] == "根据发布事实提供建议"
    assert calls[0]["runtime_context"] == managed[1]
    with pytest.raises(ValueError, match="授权范围"):
        eng._execute_node("agentNode", {"objectTypes": ["Customer"]}, {}, "q")
    with pytest.raises(ValueError, match="未挂载"):
        eng._execute_node("agent", {"skill_id": "foreign-skill"}, {}, "q")
    assert len(calls) == 1


def test_managed_stream_rejects_legacy_shortcut_and_stops_on_permission_error(managed, monkeypatch):
    monkeypatch.setattr("app.services.agent.graph_engine.has_skill_stream", lambda *_: pytest.fail("legacy stream queried"))
    nodes = [{"id": "bad", "type": "skill", "data": {"skill_id": "foreign-skill"}},
             {"id": "after", "type": "notification", "data": {"action_id": "notify"}}]
    eng = graph(managed, nodes, [{"source": "bad", "target": "after"}])
    events = list(eng.run("q"))
    assert any(e["type"] == "error" for e in events)
    assert eng.node_io["bad"]["status"] == "failed"
    assert "after" not in eng.node_io
    scene = graph(managed, nodes, [{"source": "bad", "target": "after"}])
    assert any(e["type"] == "scene_failed" for e in scene.run_for_scene({"question": "q"}))
    assert "after" not in scene.node_io


def test_managed_unknown_nodes_fail_instead_of_reporting_fake_completion(managed):
    result, _ = graph(managed)._execute_node("unknown-plugin", {}, {}, "q")
    assert result.get("error") and not result.get("executed")


@pytest.mark.parametrize("nodes,edges", [([], []),
    ([{"id": "a", "type": "output"}, {"id": "b", "type": "output"}],
     [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]),
    ([{"id": "start", "type": "input"}, {"id": "a", "type": "output"}, {"id": "b", "type": "output"}],
     [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]),
])
def test_empty_or_fully_or_partly_cyclic_managed_graph_is_not_a_success(managed, nodes, edges):
    eng = graph(managed, nodes, edges)
    assert any(event["type"] == "error" for event in eng.run("q"))
    assert eng.node_io == {}
    scene = graph(managed, nodes, edges)
    assert any(event["type"] == "scene_failed" for event in scene.run_for_scene({}))


def test_chat_graph_conditions_skip_wrong_branch_and_edge_mapping_is_used(managed):
    nodes = [{"id": "check", "type": "condition", "data": {"expression": {"field": "question", "operator": "==", "value": "go"}}},
             {"id": "yes", "type": "function", "data": {"function_id": "risk"}},
             {"id": "no", "type": "function", "data": {"function_id": "foreign-function"}},
             {"id": "output", "type": "output", "data": {}}]
    edges = [{"source": "check", "target": "yes", "sourceHandle": "branch-true"},
             {"source": "check", "target": "no", "sourceHandle": "branch-false"},
             {"source": "yes", "target": "output"}, {"source": "no", "target": "output"}]
    engine = graph(managed, nodes, edges)
    events = list(engine.run("go"))
    assert not any(event["type"] == "error" for event in events)
    assert engine.node_io["yes"]["output"]["value"] == 1
    assert engine.node_io["no"]["status"] == "skipped" and engine.node_io["output"]["status"] == "success"


def test_sql_nested_modifications_are_not_classified_readonly():
    from app.services.data_plane.sql_introspect import introspect
    nested = introspect("WITH changed AS (DELETE FROM devices RETURNING *) SELECT * FROM changed", dialect="postgresql")
    assert nested.is_dml and not nested.is_select
    into = introspect("SELECT * INTO copied_devices FROM devices", dialect="postgresql")
    assert into.is_ddl and not into.is_select


def test_loop_executes_each_item_with_fixed_function_and_does_not_truncate(managed):
    db, _ = managed
    fn = db.get(OntologyVersionFunction, "risk-v1")
    fn.logic_body = "int(params['value'])*2"
    fn.input_schema = [{"name": "value", "type": "string", "required": True}]
    db.commit()
    engine = graph(managed)
    config = {"source_field": "input.items", "item_var": "item", "function_id": "risk",
              "params": {"value": "{item.value}"}}
    result, _ = engine._execute_node("loop", config, {"input": {"items": [{"value": 2}, {"value": 3}]}}, "q")
    assert result["success"] and [r["value"] for r in result["outputs"]] == [4, 6]
    assert engine._execute_node("loop", config, {"input": {"items": [1]*101}}, "q")[0].get("error")
    assert engine._execute_node("loop", {"source_field": "items"}, {"items": [1]}, "q")[0].get("error")
