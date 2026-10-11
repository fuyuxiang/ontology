"""Isolated browser integration server using production routes and a local LLM.

Run from backend: python3 tests/run_agent_skills_browser_fixture.py
Every invocation creates a fresh temporary database and uploads directory. Only
the external OpenAI protocol is controlled; auth, skill tests, Agent execution,
versioning, permissions and action executors are production implementations.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
import threading
import time
from cryptography.fernet import Fernet
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
reuse_state = os.environ.get("ONTOLOGY_FIXTURE_STATE") or (sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == "--reuse" else None)
STATE = Path(reuse_state).resolve() if reuse_state else Path(tempfile.mkdtemp(prefix="ontology-agent-skills-browser-")).resolve()
if reuse_state and (not STATE.name.startswith("ontology-agent-skills-browser-") or not (STATE / "fixture.db").is_file()):
    raise RuntimeError("Only an existing isolated fixture directory may be reused")
LLM_PORT = int(os.environ.get("ONTOLOGY_FIXTURE_LLM_PORT", "5056"))
API_PORT = int(os.environ.get("ONTOLOGY_FIXTURE_API_PORT", "5055"))
PASSWORD = "Fixture123!"
secrets_path = STATE / "test-secrets.json"
test_secrets = json.loads(secrets_path.read_text()) if secrets_path.exists() else {"SECRET_KEY": secrets.token_hex(32), "CREDENTIAL_ENCRYPTION_KEY": Fernet.generate_key().decode()}
if not secrets_path.exists():
    secrets_path.write_text(json.dumps(test_secrets))
    secrets_path.chmod(0o600)
os.environ.update(
    DATABASE_URL=f"sqlite:///{STATE / 'fixture.db'}",
    **test_secrets,
    ADMIN_INITIAL_PASSWORD=PASSWORD,
    LLM_BASE_URL=f"http://127.0.0.1:{LLM_PORT}/v1",
    LLM_API_KEY="fixture-local-only",
    LLM_MODEL="fixture-controlled-chat",
    CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173",
)

ACTION_CALLS: list[dict] = json.loads((STATE / "action-calls.json").read_text()) if (STATE / "action-calls.json").exists() else []
REQUESTS: list[dict] = []


class ControlledOpenAI(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/fixture/state":
            self.json_response({"action_calls": ACTION_CALLS, "requests": len(REQUESTS)})
        else:
            self.json_response({"error": "not found"}, 404)

    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/fixture/actions":
            ACTION_CALLS.append(body)
            (STATE / "action-calls.json").write_text(json.dumps(ACTION_CALLS, ensure_ascii=False))
            return self.json_response({"created": True, "ticket": f"FIX-{len(ACTION_CALLS)}", "params": body})
        if self.path != "/v1/chat/completions":
            return self.json_response({"error": "not found"}, 404)
        REQUESTS.append(body)
        messages = body.get("messages", [])
        last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=0)
        question = str(messages[last_user].get("content", ""))
        if "故意失败" in question or "FAIL_RUNTIME" in question:
            return self.json_response({"error": {"message": "fixture controlled model failure", "type": "server_error"}}, 500)
        calls = [t for m in messages[last_user + 1:] for t in m.get("tool_calls", [])]
        called = {t["function"]["name"] for t in calls}
        defs = {t["function"]["name"]: t["function"] for t in body.get("tools", [])}
        selected, args = None, {}
        if body.get("tool_choice") != "none":
            if "load_skill" in defs and "load_skill" not in called:
                selected = "load_skill"
                args = {"skill_id": defs[selected]["parameters"]["properties"]["skill_id"]["enum"][0]}
            elif "run_function" in defs and "run_function" not in called:
                selected = "run_function"
                args = {"function_id": defs[selected]["parameters"]["properties"]["function_id"]["enum"][0], "params": {"temperature": 92}}
            elif "run_action" in defs and "run_action" not in called and any(w in question for w in ("工单", "动作", "确认", "处置")):
                selected = "run_action"
                args = {"action_id": defs[selected]["parameters"]["properties"]["action_id"]["enum"][0], "params": {"device_id": "DEV-001", "reason": "温度过高"}}
        system = messages[0].get("content", "")
        marker = "DRAFT_MARKER" if "DRAFT_MARKER" in system else "RELEASE_MARKER" if "RELEASE_MARKER" in system else "FIXTURE"
        answer = f"设备风险较高，温度92°C，建议检查冷却系统并安排检修。{marker}"
        if not body.get("stream"):
            return self.json_response({"id": "fixture", "object": "chat.completion", "created": int(time.time()), "model": body.get("model"), "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}]})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def chunk(delta, reason=None):
            value = {"id": "fixture-chat", "object": "chat.completion.chunk", "created": int(time.time()), "model": body.get("model"), "choices": [{"index": 0, "delta": delta, "finish_reason": reason}]}
            self.wfile.write(("data: " + json.dumps(value, ensure_ascii=False) + "\n\n").encode())
            self.wfile.flush()

        if selected:
            chunk({"role": "assistant", "tool_calls": [{"index": 0, "id": f"fixture-{len(calls)}", "type": "function", "function": {"name": selected, "arguments": json.dumps(args, ensure_ascii=False)}}]})
            chunk({}, "tool_calls")
        else:
            payload = json.dumps({"answer": answer, "suggestions": ["生成检修工单"]}, ensure_ascii=False)
            for i in range(0, len(payload), 20):
                chunk({"role": "assistant", "content": payload[i:i + 20]})
            chunk({}, "stop")
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def build_app():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import app.models  # noqa: F401
    from app.database import Base, SessionLocal, engine
    from app.main import app as production_app, _seed_system_config
    from app.models.action import EntityAction
    from app.models.agent import Agent, ModelRegistry
    from app.models.asset import Asset
    from app.models.entity import EntityAttribute, OntologyEntity
    from app.models.function import OntologyFunction
    from app.models.scenario import ScenarioDict
    from app.models.system_config import SystemConfig
    from app.models.user import User
    from app.models.version import OntologyVersion, OntologyVersionAttribute, OntologyVersionEntity
    from app.models.version_components import OntologyVersionAction, OntologyVersionFunction
    from app.services.skill_service import SkillService
    from app.services.skill_test_runner import run_skill_case
    from app.core.security import hash_password

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if reuse_state:
            if not db.get(User, "fixture-editor"):
                raise RuntimeError("The requested database is not the isolated browser fixture")
            _seed_system_config(db)
            return production_routes_app(production_app, run_skill_case, FastAPI, CORSMiddleware)
        for role in ("admin", "editor", "viewer"):
            db.add(User(id=f"fixture-{role}", username=role, name=f"联调{role}", role=role, password_hash=hash_password(PASSWORD)))
        db.add(ScenarioDict(id="ops", code="ops", name="设备运维", description="隔离浏览器测试本体"))
        db.add(ScenarioDict(id="sales", code="sales", name="客户管理"))
        db.add(SystemConfig(group="storage", key="local_path", value=str(STATE / "uploads"), description="isolated fixture storage"))
        db.add(ModelRegistry(id="fixture-model", name="联调模型（本地协议服务）", provider="openai", model_name="fixture-controlled-chat", api_base=os.environ["LLM_BASE_URL"], api_key="fixture-local-only", capabilities=["chat"], config_json={"temperature": 0}))
        db.flush()
        db.add(OntologyEntity(id="device", ontology_id="ops", name="Device", name_cn="设备", tier=1, status="published", description="冷却设备"))
        db.add(OntologyEntity(id="customer", ontology_id="sales", name="Customer", name_cn="客户", tier=1, status="published"))
        db.flush()
        db.add(EntityAttribute(id="device-temp", entity_id="device", name="temperature", type="float", description="温度", example="92"))
        fn = dict(name="设备风险评估", callable_name="device_risk", logic_type="expression", logic_body="'高风险' if params.get('temperature', 0) > 80 else '低风险'", input_schema=[{"name": "temperature", "type": "float", "required": True}], return_type="string")
        action = dict(name="创建检修工单", category="domain", action_type="api_call", type_config={"url": f"http://127.0.0.1:{LLM_PORT}/fixture/actions", "method": "POST", "body": {"device_id": "$device_id", "reason": "$reason"}}, parameters_json=[{"name": "device_id", "type": "string", "required": True}, {"name": "reason", "type": "string", "required": True}], description="隔离回执服务生成测试工单")
        db.add(OntologyFunction(id="risk", ontology_id="ops", entity_id="device", **fn))
        db.add(EntityAction(id="ticket", ontology_id="ops", entity_id="device", **action))
        for oid, eid, ename, cname in (("ops", "device", "Device", "设备"), ("sales", "customer", "Customer", "客户")):
            db.add(OntologyVersion(id=f"{oid}-v1", ontology_id=oid, version_number=1, name="稳定版", status="published", published_at=datetime.utcnow(), is_active=True, created_by="fixture-editor"))
            db.flush()
            db.add(OntologyVersionEntity(id=f"{eid}-snap", version_id=f"{oid}-v1", source_entity_id=eid, name=ename, name_cn=cname, tier=1))
        db.flush()
        db.add(OntologyVersionAttribute(id="temp-snap", version_entity_id="device-snap", source_attribute_id="device-temp", name="temperature", type="float", description="温度", example="92"))
        db.add(OntologyVersionFunction(id="risk-snap", version_id="ops-v1", source_function_id="risk", version_entity_id="device-snap", **fn))
        db.add(OntologyVersionAction(id="ticket-snap", version_id="ops-v1", source_action_id="ticket", version_entity_id="device-snap", **action))
        db.add(Asset(id="manual", name="设备检修手册", kind="document", locator={"source_type": "file", "path": str(STATE / "manual.txt")}, domain="ops", parsed_summary="温度超过80°C存在高风险，先检查冷却系统，再生成检修工单。", status="active"))
        db.commit()
        _seed_system_config(db)
        owner = db.get(User, "fixture-editor")
        service = SkillService(db)
        skill = service.create({"name": "设备故障诊断", "description": "风险评估与检修工单", "prompt_template": "先加载本技能，再调用设备风险评估；如需要处置则创建检修工单。", "ontology_id": "ops", "ontology_version_id": "ops-v1", "entity_ids": ["device"], "tools": [{"type": "function", "id": "risk"}, {"type": "action", "id": "ticket"}], "asset_refs": ["manual"], "visibility": "workspace", "test_cases": [{"id": "risk-case", "name": "高温风险分析", "input": "分析设备告警", "expected_keywords": ["风险"], "expected_tools": ["risk"]}]}, owner)
        model = service.get(skill["id"], owner, edit=True)
        result = service.run_tests(model, owner, run_skill_case)
        if not result["passed"]:
            raise RuntimeError(f"fixture skill real runtime failed: {result}")
        service.publish(model, owner, "通过隔离真实运行后发布")
        db.add(Agent(id="fixture-agent", name="设备运维助手", description="隔离联调种子", model_id="fixture-model", system_prompt="RELEASE_MARKER", entity_ids=["device"], tools_config={"ontology_id": "ops", "ontology_version_id": "ops-v1", "skill_bindings": [{"skill_id": skill["id"], "version": 1}], "action_mode": "simulation", "max_tool_rounds": 12}))
        db.commit()
        manifest = {"api_url": f"http://127.0.0.1:{API_PORT}/api/v1", "frontend_url": "http://127.0.0.1:5173", "state_dir": str(STATE), "database": str(STATE / "fixture.db"), "password": PASSWORD, "users": ["admin", "editor", "viewer"], "skill_id": skill["id"], "agent_id": "fixture-agent", "llm_url": os.environ["LLM_BASE_URL"]}
        Path("/private/tmp/ontology-agent-skills-browser-fixture.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)

    (STATE / "uploads").mkdir(exist_ok=True)
    (STATE / "manual.txt").write_text("隔离测试设备手册：高温风险与工单流程。")
    return production_routes_app(production_app, run_skill_case, FastAPI, CORSMiddleware)


def production_routes_app(production_app, run_skill_case, fastapi_cls, cors_cls):
    from app.services.data_plane import asset_service
    asset_service._UPLOAD_DIR = STATE / "uploads"
    asset_service._UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    application = fastapi_cls(title="Isolated production-route browser fixture")
    application.router.routes.extend(production_app.router.routes)
    application.state.skill_test_runner = run_skill_case
    application.add_middleware(cors_cls, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    return application


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", LLM_PORT), ControlledOpenAI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import uvicorn
    uvicorn.run(build_app(), host="127.0.0.1", port=API_PORT, log_level="warning")
