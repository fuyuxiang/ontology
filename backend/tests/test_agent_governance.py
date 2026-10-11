"""Release isolation, scoped execution and single-use authenticated approvals."""
import copy
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from test_skills_lifecycle import headers, setup  # noqa: F401

from app.api.v1 import agents as api
from app.models.agent_runtime import AgentPendingAction, AgentRun
from app.models.function import OntologyFunction
from app.models.version import OntologyVersionAttribute
from app.models.version_components import OntologyVersionAction
from app.services.action_executors.base import ExecutionResult
from app.services.agent.managed_runtime import ManagedToolRouter
from app.services.agent_management import config_hash, config_snapshot, runtime_context
from app.services.skill_service import SkillService


class SuccessfulAgent:
    contexts = []
    prompts = []

    def __init__(self, db, **kwargs):
        self.contexts.append(kwargs["runtime_context"])
        self.prompts.append(kwargs.get("system_prompt_prefix"))

    def ask(self, question, entity_id=None, history=None):
        yield {"type": "content", "content": "风险分析完成"}
        yield {"type": "done", "suggestions": []}


@pytest.fixture
def env(setup):
    setup["app"].include_router(api.router, prefix="/api/v1")
    setup["app"].include_router(api.open_router, prefix="/api/v1")
    db = setup["db"]
    db.add(OntologyVersionAttribute(version_entity_id="device-snap", source_attribute_id="temperature",
                                   name="temperature", type="number"))
    db.add(OntologyVersionAction(version_id="ops-v1", version_entity_id="device-snap",
        source_action_id="notify", name="设备操作", category="entity", action_type="custom_script",
        type_config={"script": "result = {'ok': True}"}, parameters_json=[
            {"name": "device_id", "type": "string", "required": True}]))
    db.commit()
    c = setup["client"]
    response = c.post("/api/v1/agents", headers=headers(), json={
        "name": "设备助手", "entity_ids": ["device"], "system_prompt": "原始发布指引",
        "tools_config": {"ontology_id": "ops", "ontology_version_id": "ops-v1", "action_mode": "simulation"}})
    assert response.status_code == 201, response.text
    setup["agent"] = response.json()
    yield setup


def chat(env, **body):
    return env["client"].post(f"/api/v1/agents/{env['agent']['id']}/chat",
                              headers=headers(), json={"question": "设备风险", "stream": False, **body})


def release(env):
    with patch.object(api, "AgentService", SuccessfulAgent):
        result = chat(env)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "completed", result.text
    r = env["client"].post(f"/api/v1/agents/{env['agent']['id']}/publish", headers=headers())
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_scope_and_configuration_validation(env):
    client, aid = env["client"], env["agent"]["id"]
    assert client.get("/api/v1/agents").status_code == 401
    assert client.post("/api/v1/agents", json={"name": "x"}, headers=headers("reader")).status_code == 403
    assert client.put(f"/api/v1/agents/{aid}", json={"name": "x"}, headers=headers("reader")).status_code == 403
    assert client.post("/api/v1/skills", json=env["payload"], headers=headers("reader")).status_code == 403
    for config in ({"skill_bindings": None}, {"skill_bindings": {}}, {"max_tool_rounds": True},
                   {"skill_bindings": [{"skill_id": [], "version": 1}]}):
        assert client.put(f"/api/v1/agents/{aid}", json={"tools_config": config}, headers=headers()).status_code == 422
    assert client.put(f"/api/v1/agents/{aid}", json={"name": " "}, headers=headers()).status_code == 422


def test_publish_requires_current_successful_test_and_public_uses_snapshot(env):
    client, aid = env["client"], env["agent"]["id"]
    assert client.post(f"/api/v1/agents/{aid}/publish", headers=headers()).status_code == 409
    published = release(env)
    assert published["current_version"] == 1 and not published["has_changes"]
    client.put(f"/api/v1/agents/{aid}", json={"name": "编辑中", "system_prompt": "尚未发布新指引"}, headers=headers())
    assert client.post(f"/api/v1/agents/{aid}/publish", headers=headers()).status_code == 409
    SuccessfulAgent.prompts.clear()
    with patch.object(api, "AgentService", SuccessfulAgent):
        r = client.post(f"/api/v1/open/agents/{aid}/chat", json={"question": "风险", "stream": False},
                        headers={"X-Agent-Key": published["api_key"]})
    assert r.status_code == 200 and r.json()["version"] == 1, r.text
    assert SuccessfulAgent.prompts == ["原始发布指引"]
    assert client.get(f"/api/v1/open/agents/{aid}/info", headers={"X-Agent-Key": published["api_key"]}).json()["name"] == "设备助手"
    assert client.post(f"/api/v1/open/agents/{aid}/chat", json={"question": "x"},
                       headers={"X-Agent-Key": "wrong"}).status_code == 401
    assert client.get(f"/api/v1/agents/{aid}/api-info", headers=headers()).json()["endpoint"].endswith(f"open/agents/{aid}/chat")


def test_failed_or_empty_response_cannot_unlock_publish(env):
    class Failed(SuccessfulAgent):
        def ask(self, *args, **kwargs):
            yield {"type": "error", "message": "真实模型连接失败"}
            yield {"type": "answer", "content": "调用失败"}
    with patch.object(api, "AgentService", Failed):
        r = chat(env)
    assert r.json()["status"] == "failed" and r.json()["error"]
    aid = env["agent"]["id"]
    assert env["client"].get(f"/api/v1/agents/{aid}", headers=headers()).json()["last_test"]["passed"] is False
    assert env["client"].post(f"/api/v1/agents/{aid}/publish", headers=headers()).status_code == 409
    class Empty(SuccessfulAgent):
        def ask(self, *args, **kwargs):
            yield {"type": "done"}
    with patch.object(api, "AgentService", Empty):
        assert chat(env).json()["status"] == "failed"


def test_scope_queries_and_function_body_are_fixed(env):
    db = env["db"]
    from app.models.agent import Agent
    a = db.get(Agent, env["agent"]["id"])
    context = runtime_context(db, config_snapshot(a), env["owner"])
    router = ManagedToolRouter(db, context)
    assert router.execute("query_datasource", {"sql": "SELECT * FROM private"})[0].get("error")
    assert router.execute("get_entity_detail", {"entity_name": "Customer"})[0].get("error")
    assert router.execute("query_entity_data", {"entity_name": "Device", "fields": ["password"]})[0].get("error")
    db.get(OntologyFunction, "risk").logic_body = "999"
    db.commit()
    result = router.execute("run_function", {"function_id": "risk", "params": {}})[0]
    assert result["success"] and result["value"] == 1
    with patch("app.services.data_plane.entity_data_service.EntityDataService.query_entity_data",
               return_value={"rowCount": 1, "rows": []}) as query:
        router.execute("query_entity_data", {"entity_name": "Device"})
    assert query.call_args.kwargs["fields"] == ["temperature"]
    snap = config_snapshot(a)
    snap["entity_ids"] = ["customer"]
    with pytest.raises(Exception) as error:
        runtime_context(db, snap, env["owner"])
    assert error.value.status_code == 409


def pending(env, expired=False):
    from app.models.agent import Agent
    a = env["db"].get(Agent, env["agent"]["id"])
    p = AgentPendingAction(agent_id=a.id, user_id=env["owner"].id, action_id="notify",
        action_snapshot={"id": "notify", "name": "设备操作", "action_type": "custom_script", "type_config": {}},
        params={"device_id": "d1"}, config_hash=config_hash(config_snapshot(a)),
        expires_at=datetime.utcnow() + timedelta(minutes=-1 if expired else 10))
    env["db"].add(p)
    env["db"].commit()
    return p.id


def test_simulation_cannot_write_and_confirm_is_single_use(env):
    from app.models.agent import Agent
    a = env["db"].get(Agent, env["agent"]["id"])
    context = runtime_context(env["db"], config_snapshot(a), env["owner"])
    context["agent_id"] = a.id
    router = ManagedToolRouter(env["db"], context)
    with patch("app.services.agent_actions.run_executor_sync",
               return_value=ExecutionResult(True, "preview")) as execute:
        preview = router.execute("run_action", {"action_id": "notify", "params": {"device_id": "d1"}})[0]
    assert preview["simulated"] is True
    assert execute.call_args.kwargs["dry_run"] is True
    assert env["db"].query(AgentPendingAction).count() == 0
    pid = pending(env)
    url = f"/api/v1/agents/{a.id}/actions/{pid}/confirm"
    assert env["client"].post(url, json={"approve": True}, headers=headers("reader")).status_code == 403
    with patch("app.services.agent_actions.run_executor_sync", return_value=ExecutionResult(True, "执行成功")) as executor:
        first = env["client"].post(url, json={"approve": True}, headers=headers())
        repeat = env["client"].post(url, json={"approve": True}, headers=headers())
    assert first.json()["status"] == repeat.json()["status"] == "approved"
    assert executor.call_count == 1 and executor.call_args.kwargs["dry_run"] is False


def test_reject_expiry_failure_and_changed_config_are_explicit(env):
    aid, client = env["agent"]["id"], env["client"]
    with patch("app.services.agent_actions.run_executor_sync", return_value=ExecutionResult(False, "下游拒绝")) as ex:
        pid = pending(env)
        assert client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", json={"approve": False}, headers=headers()).json()["status"] == "rejected"
        pid = pending(env, expired=True)
        assert client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", json={"approve": True}, headers=headers()).json()["status"] == "expired"
        assert ex.call_count == 0
        pid = pending(env)
        result = client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", json={"approve": True}, headers=headers()).json()
        assert result["status"] == "failed" and result["result"]["success"] is False
        pid = pending(env)
        client.put(f"/api/v1/agents/{aid}", json={"name": "已修改"}, headers=headers())
        assert client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", json={"approve": True}, headers=headers()).status_code == 409


def test_rollback_restores_draft_and_preserves_current_public_release(env):
    c, aid = env["client"], env["agent"]["id"]
    release(env)
    c.put(f"/api/v1/agents/{aid}", json={"name": "第二版"}, headers=headers())
    published = release(env)
    assert published["current_version"] == 2
    r = c.post(f"/api/v1/agents/{aid}/rollback", json={"version": 1}, headers=headers()).json()
    assert r["name"] == "设备助手" and r["current_version"] == 2 and r["has_changes"]
    online = c.get(f"/api/v1/open/agents/{aid}/info", headers={"X-Agent-Key": published["api_key"]}).json()
    assert online["name"] == "第二版" and online["version"] == 2
    assert c.get(f"/api/v1/agents/{aid}/runs", headers=headers("reader")).json() == []


def test_pinned_asset_text_does_not_read_mutable_summary(env):
    from app.models.asset import Asset
    service = SkillService(env["db"])
    created = service.create(env["payload"], env["owner"])
    skill = service.get(created["id"], env["owner"])
    snapshot = service.snapshot(skill, env["owner"])
    env["db"].get(Asset, "manual").parsed_summary = "后来编辑的未发布内容"
    env["db"].commit()
    context = {"ontology_version_id": "ops-v1", "entity_ids": ["device"], "skills": [snapshot]}
    router = ManagedToolRouter(env["db"], context)
    loaded = router.execute("load_skill", {"skill_id": skill.id})[0]
    assert loaded["references"][0]["summary"] == "排查手册"


def test_model_behavior_changes_require_retest_but_published_model_is_pinned(env):
    from app.models.agent import ModelRegistry
    db, c, aid = env["db"], env["client"], env["agent"]["id"]
    model = ModelRegistry(id="model-a", name="模型 A", provider="openai", model_name="original-model",
        api_base="https://original.example/v1", api_key="never-in-snapshot",
        config_json={"temperature": 0, "max_tokens": 100, "api_key": "also-secret"})
    db.add(model)
    db.commit()
    c.put(f"/api/v1/agents/{aid}", json={"model_id": model.id}, headers=headers())
    published = release(env)
    versions = c.get(f"/api/v1/agents/{aid}/versions", headers=headers()).json()
    pinned = versions[0]["config_snapshot"]["model_snapshot"]
    assert pinned["model_name"] == "original-model"
    assert "api_key" not in pinned["config_json"] and "never-in-snapshot" not in str(versions)
    model.model_name, model.api_base, model.config_json = "changed", "https://changed.example/v1", {"temperature": 1}
    db.commit()
    changed = c.get(f"/api/v1/agents/{aid}", headers=headers()).json()
    assert changed["has_changes"] and changed["last_test"] is None
    captured = {}
    class Captured(SuccessfulAgent):
        def __init__(self, db, **kwargs):
            captured.update(kwargs)
            super().__init__(db, **kwargs)
    with patch.object(api, "AgentService", Captured):
        response = c.post(f"/api/v1/open/agents/{aid}/chat", json={"question": "风险", "stream": False},
                          headers={"X-Agent-Key": published["api_key"]})
    assert response.json()["status"] == "completed"
    assert captured["model_name"] == "original-model"
    assert captured["model_config"]["api_base"] == "https://original.example/v1"
    assert captured["model_config"]["temperature"] == 0


def test_callable_action_uses_function_snapshot_not_live_registry(env):
    db = env["db"]
    action = OntologyVersionAction(version_id="ops-v1", version_entity_id="device-snap",
        source_action_id="call-risk", name="评估", category="entity", action_type="call_function",
        type_config={"function_name": "device_risk"}, parameters_json=[])
    db.add(action)
    db.commit()
    router = ManagedToolRouter(db, {"ontology_version_id": "ops-v1", "entity_ids": ["device"]})
    snapshot = router.actions["call-risk"]
    db.get(OntologyFunction, "risk").logic_body = "999"
    db.commit()
    from app.services.agent_actions import execute_action_snapshot
    result = execute_action_snapshot(db, snapshot, {}, dry_run=False)
    assert result.success and result.output["result"] == 1
    assert router.execute("run_action", {"action_id": "notify", "params": {"device_id": 123}})[0].get("error")


def test_runtime_skill_test_requires_actual_instruction_load(env):
    from app.services import skill_test_runner
    service = SkillService(env["db"])
    created = service.create(env["payload"], env["owner"])
    snapshot = service.snapshot(service.get(created["id"], env["owner"]), env["owner"])
    class SkippedInstruction:
        def __init__(self, *args, **kwargs):
            pass
        def ask(self, *args, **kwargs):
            yield {"type": "content", "content": "风险分析完成"}
            yield {"type": "done"}
    with patch.object(skill_test_runner, "SessionLocal", lambda: env["db"]), patch.object(
            skill_test_runner, "AgentService", SkippedInstruction):
        result = skill_test_runner.run_skill_case(snapshot, snapshot["test_cases"][0], env["owner"])
    assert "未实际加载" in result["error"]


def test_action_decision_finishes_waiting_run(env):
    from app.models.agent import Agent
    a = env["db"].get(Agent, env["agent"]["id"])
    pid = pending(env)
    p = env["db"].get(AgentPendingAction, pid)
    run = AgentRun(agent_id=a.id, user_id=env["owner"].id, config_hash=config_hash(config_snapshot(a)),
                   question="创建工单", answer="等待确认", status="pending_confirmation",
                   pending_actions=[{"pending_id": pid, "status": "pending"}])
    env["db"].add(run)
    env["db"].flush()
    p.run_id = run.id
    env["db"].commit()
    result = env["client"].post(f"/api/v1/agents/{a.id}/actions/{pid}/confirm",
                                json={"approve": False}, headers=headers())
    assert result.json()["status"] == "rejected"
    env["db"].refresh(run)
    assert run.status == "completed" and run.pending_actions[0]["status"] == "rejected"
