"""Approval receipts, recovery and evaluation failure use the production path."""
import json
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import pytest

from test_agent_governance import env, headers, pending, setup  # noqa: F401

from app.api.v1 import agents, evals
from app.models.agent_runtime import AgentPendingAction, AgentRun
from app.models.trace import AgentTrace
from app.services.agent_recovery import recover_interrupted_runs


def attach_run(env, pid):
    p = env["db"].get(AgentPendingAction, pid)
    run = AgentRun(agent_id=p.agent_id, user_id=p.user_id, config_hash=p.config_hash,
        question="创建检修单", answer="等待确认", status="pending_confirmation",
        pending_actions=[{"pending_id": pid, "status": "pending"}])
    env["db"].add(run)
    env["db"].flush()
    p.run_id = run.id
    env["db"].add(AgentTrace(id=run.id, agent_id=p.agent_id, input_text=run.question, status="pending"))
    env["db"].commit()
    return run


def test_actual_http_receipt_repeat_confirmation_and_trace_match(env, tmp_path):
    receipt = tmp_path / "receipt.json"
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            before = json.loads(receipt.read_text()) if receipt.exists() else []
            receipt.write_text(json.dumps(before + [body]))
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ticket_id":"WO-d1","success":true}')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        pid = pending(env)
        p = env["db"].get(AgentPendingAction, pid)
        p.action_snapshot = {"id": "ticket", "name": "创建检修单", "action_type": "api_call",
            "type_config": {"url": f"http://127.0.0.1:{server.server_port}/tickets", "method": "POST",
                            "body": {"device_id": "$device_id"}}}
        run = attach_run(env, pid)
        url = f"/api/v1/agents/{p.agent_id}/actions/{pid}/confirm"
        first = env["client"].post(url, json={"approve": True}, headers=headers())
        again = env["client"].post(url, json={"approve": True}, headers=headers())
        assert first.status_code == 200 and first.json()["status"] == again.json()["status"] == "approved", first.text
        assert json.loads(receipt.read_text()) == [{"device_id": "d1"}]
        env["db"].refresh(run)
        assert run.status == "completed"
        assert run.pending_actions[0]["result"]["output"]["body"]["ticket_id"] == "WO-d1"
        assert env["db"].get(AgentTrace, run.id).status == "ok"
    finally:
        server.shutdown()
        server.server_close()


def test_restart_keeps_interrupted_action_unknown_and_never_replays(env):
    pid = pending(env)
    p = env["db"].get(AgentPendingAction, pid)
    p.status = "executing"
    run = attach_run(env, pid)
    recover_interrupted_runs(env["db"])
    response = env["client"].post(f"/api/v1/agents/{p.agent_id}/actions/{pid}/confirm",
                                 json={"approve": True}, headers=headers())
    assert response.json()["status"] == "unknown"
    env["db"].refresh(run)
    assert run.status == "unknown" and env["db"].get(AgentTrace, run.id).status == "error"
    assert "重启" in run.error


def test_trace_queries_preserve_run_owner_scope(env):
    from app.api.v1 import traces
    env["app"].include_router(traces.router, prefix="/api/v1")
    pid = pending(env)
    run = attach_run(env, pid)
    client = env["client"]
    assert client.get(f"/api/v1/traces/{run.id}", headers=headers("reader")).status_code == 404
    assert client.get("/api/v1/traces", headers=headers("reader")).json()["items"] == []
    assert client.get(f"/api/v1/traces/{run.id}", headers=headers()).status_code == 200
    assert client.get("/api/v1/traces", headers=headers()).json()["items"][0]["id"] == run.id


def test_eval_uses_scoped_agent_path_and_business_failure_cannot_pass_keywords(env):
    env["app"].include_router(evals.router, prefix="/api/v1")
    client, aid = env["client"], env["agent"]["id"]
    assert client.post("/api/v1/evals/suites", json={"agent_id": aid, "name": "x"}, headers=headers("reader")).status_code == 403
    suite = client.post("/api/v1/evals/suites", json={"agent_id": aid, "name": "设备风险"}, headers=headers()).json()
    client.post(f"/api/v1/evals/suites/{suite['id']}/cases", json={"input_prompt": "计算风险", "expected_keywords": ["风险"]}, headers=headers())
    seen = {}
    class FailedTool:
        def __init__(self, db, **kwargs):
            seen.update(kwargs["runtime_context"])
        def ask(self, *args, **kwargs):
            yield {"type": "tool_start", "tool": "run_function", "arguments": {"function_id": "risk"}}
            yield {"type": "tool_result", "tool": "run_function", "result": {"success": False, "error": "源连接失败"}}
            yield {"type": "answer", "content": "风险已处理"}
            yield {"type": "done"}
    with patch("app.services.agent.orchestrator.AgentService", FailedTool):
        response = client.post(f"/api/v1/evals/suites/{suite['id']}/run", headers=headers())
    assert response.status_code == 200, response.text
    assert seen["ontology_version_id"] == "ops-v1" and seen["entity_ids"] == ["device"]
    assert response.json()["metrics"]["pass_rate"] == 0
    assert response.json()["results"][0]["passed"] is False
    assert "源连接失败" in response.json()["results"][0]["actual_output"]
    assert env["db"].query(AgentRun).one().status == "failed"
    assert env["db"].query(AgentTrace).one().status == "error"


def test_graph_configuration_roundtrips_and_foreign_conversation_is_rejected(env):
    client, aid = env["client"], env["agent"]["id"]
    nodes = [{"id": "risk-node", "type": "function", "data": {"function_id": "risk"}}]
    response = client.put(f"/api/v1/agents/{aid}", json={"nodes_json": nodes, "edges_json": []}, headers=headers())
    assert response.json()["nodes_json"] == nodes
    assert client.get(f"/api/v1/agents/{aid}", headers=headers()).json()["nodes_json"] == nodes
    result = client.post(f"/api/v1/agents/{aid}/chat", json={"question": "x", "conversation_id": "foreign", "stream": False}, headers=headers())
    assert result.status_code == 404


def test_unknown_function_outcome_remains_unknown_in_run_and_trace(env):
    class UnknownFunction:
        def __init__(self, db, **kwargs):
            pass
        def ask(self, *args, **kwargs):
            yield {"type": "tool_result", "tool": "run_function", "result": {
                "success": False, "outcome": "committed_unrecorded", "error": "源写入已提交，但回读失败"}}
            yield {"type": "answer", "content": "请核查设备状态"}
            yield {"type": "done"}
    aid = env["agent"]["id"]
    with patch.object(agents, "AgentService", UnknownFunction):
        result = env["client"].post(f"/api/v1/agents/{aid}/chat", json={"question": "修复", "stream": False}, headers=headers())
    assert result.json()["status"] == "unknown"
    assert env["db"].get(AgentTrace, result.json()["id"]).status == "error"
    assert "回读失败" in result.json()["error"]


def test_graph_human_approval_resumes_remaining_nodes_and_cannot_replay(env, monkeypatch):
    # This graph has no LLM nodes; the unused client construction is isolated only.
    monkeypatch.setattr("app.services.agent.graph_engine.get_llm_client", lambda **_: object())
    client, aid = env["client"], env["agent"]["id"]
    nodes = [{"id": "approve", "type": "human-approval", "data": {"action_id": "notify", "params": {"device_id": "d1"}}},
             {"id": "risk", "type": "function", "data": {"function_id": "risk", "params": {}}},
             {"id": "out", "type": "output", "data": {}}]
    updated = client.put(f"/api/v1/agents/{aid}", headers=headers(), json={"nodes_json": nodes,
        "edges_json": [{"source": "approve", "target": "risk"}, {"source": "risk", "target": "out"}],
        "tools_config": {"ontology_id": "ops", "ontology_version_id": "ops-v1", "action_mode": "confirm"}})
    assert updated.status_code == 200, updated.text
    first = client.post(f"/api/v1/agents/{aid}/chat", headers=headers(), json={"question": "执行审批图", "stream": False})
    assert first.status_code == 200 and first.json()["status"] == "pending_confirmation", first.text
    assert not any(t["tool"] == "[function]" for t in first.json()["tool_runs"])
    pid = first.json()["pending_actions"][0]["pending_id"]
    confirmed = client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", headers=headers(), json={"approve": True})
    assert confirmed.json()["status"] == "approved", confirmed.text
    run = env["db"].get(AgentRun, first.json()["id"])
    env["db"].refresh(run)
    assert run.status == "completed" and '"value": 1' in json.loads(run.answer)["output"]
    assert sum(t["tool"] == "[function]" for t in run.tool_runs) == 1
    count = len(run.tool_runs)
    again = client.post(f"/api/v1/agents/{aid}/actions/{pid}/confirm", headers=headers(), json={"approve": True})
    assert again.json()["status"] == "approved"
    env["db"].refresh(run)
    assert len(run.tool_runs) == count and env["db"].get(AgentTrace, run.id).status == "ok"


@pytest.mark.parametrize("timeout_seconds", [0.1, 5])
def test_lost_http_receipt_manual_reconciliation_and_explicit_graph_resume_never_replays(env, tmp_path, monkeypatch, timeout_seconds):
    """The business source commits, then disconnects before returning its receipt."""
    from app.models.action import EntityAction
    from app.models.version_components import OntologyVersionAction
    receipt = tmp_path / "committed-tickets.json"
    class LostReceipt(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            previous = json.loads(receipt.read_text()) if receipt.exists() else []
            receipt.write_text(json.dumps(previous + [body]))
            import time
            time.sleep(0.3)
            self.close_connection = True
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), LostReceipt)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        db, client, aid = env["db"], env["client"], env["agent"]["id"]
        frozen = db.query(OntologyVersionAction).filter_by(source_action_id="notify").one()
        frozen.action_type = "api_call"
        frozen.type_config = {"url": f"http://127.0.0.1:{server.server_port}/tickets", "method": "POST",
                              "body": {"device_id": "$device_id"}, "timeout_seconds": timeout_seconds}
        db.add(EntityAction(id="notify", name="创建工单", action_type="api_call", impact_count=0))
        db.commit()
        monkeypatch.setattr("app.services.agent.graph_engine.get_llm_client", lambda **_: object())
        assert client.put(f"/api/v1/agents/{aid}", headers=headers(), json={
            "nodes_json": [{"id": "approve", "type": "human-approval", "data": {"action_id": "notify", "params": {"device_id": "d1"}}},
                           {"id": "risk", "type": "function", "data": {"function_id": "risk", "params": {}}},
                           {"id": "out", "type": "output", "data": {}}],
            "edges_json": [{"source": "approve", "target": "risk"}, {"source": "risk", "target": "out"}],
            "tools_config": {"ontology_id": "ops", "ontology_version_id": "ops-v1", "action_mode": "confirm"}}).status_code == 200
        first = client.post(f"/api/v1/agents/{aid}/chat", headers=headers(), json={"question": "创建工单", "stream": False}).json()
        pid = first["pending_actions"][0]["pending_id"]
        url = f"/api/v1/agents/{aid}/actions/{pid}"
        unknown = client.post(url + "/confirm", headers=headers(), json={"approve": True})
        assert unknown.json()["status"] == "unknown", unknown.text
        run = db.get(AgentRun, first["id"])
        db.refresh(run)
        assert run.status == "unknown" and db.get(AgentTrace, run.id).status == "error"
        assert client.post(url + "/reconcile", headers=headers("reader"), json={"resolution": "succeeded", "evidence": "源数据已查到工单 WO-d1"}).status_code in {403, 404}
        assert client.post(url + "/reconcile", headers=headers(), json={"resolution": "succeeded", "evidence": "   " * 10}).status_code == 422
        reconciled = client.post(url + "/reconcile", headers=headers(), json={"resolution": "succeeded", "evidence": "已查询隔离源工单，device_id=d1 的工单已持久化", "receipt_id": "WO-d1"})
        assert reconciled.status_code == 200, reconciled.text
        assert reconciled.json()["result"]["continuation_status"] == "awaiting_resume"
        db.refresh(run)
        assert run.status == "pending_confirmation" and run.error is None
        assert client.post(url + "/reconcile", headers=headers(), json={"resolution": "succeeded", "evidence": "再次核查源工单已存在"}).status_code == 409
        resumed = client.post(url + "/resume", headers=headers())
        assert resumed.status_code == 200, resumed.text
        db.refresh(run)
        assert run.status == "completed" and run.error is None
        assert sum(t["tool"] == "[function]" for t in run.tool_runs) == 1
        assert db.get(AgentTrace, run.id).status == "ok"
        assert client.post(url + "/resume", headers=headers()).status_code == 409
        assert client.post(url + "/confirm", headers=headers(), json={"approve": True}).json()["status"] == "approved"
        assert json.loads(receipt.read_text()) == [{"device_id": "d1"}]
        db.expire_all()
        assert db.get(EntityAction, "notify").impact_count == 1
    finally:
        server.shutdown()
        server.server_close()


def test_reconciliation_retains_independent_failure_and_cannot_resume_interrupted_suffix(env):
    pid = pending(env)
    p = env["db"].get(AgentPendingAction, pid)
    run = attach_run(env, pid)
    p.status = "resuming"
    p.action_snapshot = {**p.action_snapshot, "_graph_checkpoint": {"node_id": "approve"}}
    run.status = "pending_confirmation"
    run.tool_runs = [{"success": False, "result": {"error": "后续函数真实业务失败"}}]
    env["db"].commit()
    recover_interrupted_runs(env["db"])
    url = f"/api/v1/agents/{p.agent_id}/actions/{pid}"
    response = env["client"].post(url + "/reconcile", headers=headers(), json={"resolution": "succeeded", "evidence": "已经核查原始业务动作提交成功，后续需另外核查"})
    assert response.status_code == 200, response.text
    assert response.json()["result"]["continuation_status"] == "unknown"
    env["db"].refresh(run)
    assert run.status == "unknown" and "后续函数真实业务失败" in run.error
    assert env["client"].post(url + "/resume", headers=headers()).status_code == 409


def test_monitor_lifecycle_stops_and_can_restart(monkeypatch):
    import asyncio
    from app.services.monitor import collector
    async def forever():
        await asyncio.Event().wait()
    monkeypatch.setattr(collector, "collect_service_metrics", forever)
    monkeypatch.setattr(collector, "check_alerts", forever)
    monkeypatch.setattr(collector, "cleanup_old_data", forever)
    async def check():
        await collector.stop_collector()
        monkeypatch.setattr(collector.settings, "MONITOR_ENABLED", False)
        await collector.start_collector()
        assert collector._collector_tasks == []
        monkeypatch.setattr(collector.settings, "MONITOR_ENABLED", True)
        await collector.start_collector()
        original = list(collector._collector_tasks)
        await collector.start_collector()
        assert collector._collector_tasks == original and len(original) == 3
        await collector.stop_collector()
        assert all(task.done() for task in original) and collector.ws_manager._heartbeat_task is None
        await collector.start_collector()
        assert len(collector._collector_tasks) == 3
        await collector.stop_collector()
    asyncio.run(check())


def test_declared_action_defaults_and_iso_parameters_are_validated():
    import pytest
    from app.services.agent_actions import validate_parameters
    assert validate_parameters([{"name": "count", "type": "integer", "default_value": "2"},
                                {"name": "payload", "type": "json", "default_value": '{"ok":true}'},
                                {"name": "date", "type": "date", "required": True}],
                               {"date": "2026-10-11"}) == {"count": 2, "payload": {"ok": True}, "date": "2026-10-11"}
    with pytest.raises(ValueError, match="ISO"):
        validate_parameters([{"name": "date", "type": "date"}], {"date": "tomorrow"})


def test_internal_generated_skill_executes_declared_import_and_empty_is_failure(env):
    from app.models.skill_tool import SkillTool
    from app.services.skill_executor import execute_generated_skill
    from app.services.skill_sandbox import CodeValidationError, execute_in_sandbox
    from types import SimpleNamespace
    import pytest
    skill = SimpleNamespace(id="internal-generated")
    assert execute_generated_skill(skill, {}, env["db"])["success"] is False
    env["db"].add(SkillTool(skill_id=skill.id, name="calculate",
        code="import json\nimport math\ndef calculate(value):\n    return json.dumps({'root':math.sqrt(value)})"))
    env["db"].commit()
    result = execute_generated_skill(skill, {"value": 16}, env["db"])
    assert result["success"] and json.loads(result["data"]["calculate"]["output"]) == {"root": 4}
    with pytest.raises(CodeValidationError):
        execute_in_sandbox("import os\ndef calculate():\n    return os.listdir('.')", "calculate", {})


def test_concurrent_confirmation_uses_independent_sessions_and_one_receipt(env, tmp_path):
    import sqlite3
    import time
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import FastAPI, Depends, Header
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.database import get_db
    from app.core.deps import require_user
    from app.models.user import User
    seen, receipt_lock = [], threading.Lock()
    class Receipt(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with receipt_lock:
                seen.append(payload)
            time.sleep(.15)
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"success":true,"ticket":"concurrent-1"}')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Receipt)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    engine = None
    try:
        pid = pending(env)
        p = env["db"].get(AgentPendingAction, pid)
        p.action_snapshot = {"id": "ticket", "name": "创建工单", "action_type": "api_call",
            "type_config": {"url": f"http://127.0.0.1:{server.server_port}/receipt", "method": "POST",
                            "body": {"device_id": "$device_id"}}}
        run = attach_run(env, pid)
        target = tmp_path / "concurrent.sqlite"
        raw = env["db"].get_bind().raw_connection()
        with sqlite3.connect(target) as clone:
            raw.driver_connection.backup(clone)
        raw.close()
        engine = create_engine(f"sqlite:///{target}", connect_args={"check_same_thread": False})
        sessions = sessionmaker(bind=engine, expire_on_commit=False)
        app = FastAPI()
        app.include_router(agents.router, prefix="/api/v1")
        def get_isolated_db():
            with sessions() as db:
                yield db
        def user(x_test_user: str = Header(), db=Depends(get_db)):
            return db.get(User, x_test_user)
        app.dependency_overrides[get_db] = get_isolated_db
        app.dependency_overrides[require_user] = user
        barrier = threading.Barrier(2)
        url = f"/api/v1/agents/{p.agent_id}/actions/{pid}/confirm"
        def confirm():
            with TestClient(app) as client:
                barrier.wait(timeout=5)
                response = client.post(url, headers=headers(), json={"approve": True})
                assert response.status_code == 200, response.text
                return response.json()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(confirm) for _ in range(2)]
            replies = [future.result(timeout=15) for future in futures]
        assert len(seen) == 1 and seen[0] == {"device_id": "d1"}
        assert {reply["status"] for reply in replies} <= {"approved", "executing"}
        with sessions() as db:
            assert db.get(AgentPendingAction, pid).status == "approved"
            assert db.get(AgentRun, run.id).status == "completed"
    finally:
        server.shutdown()
        server.server_close()
        if engine:
            engine.dispose()
