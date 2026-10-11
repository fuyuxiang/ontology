"""Exercise isolation, immutable versions and actual runtime test evidence."""
import copy

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # register existing FK/relationship targets
from app.api.v1.skills import router
from app.core.deps import require_user
from app.database import Base, get_db
from app.models.action import EntityAction
from app.models.agent import Agent
from app.models.agent_runtime import AgentVersion
from app.models.asset import Asset
from app.models.entity import OntologyEntity
from app.models.function import OntologyFunction
from app.models.scenario import ScenarioDict
from app.models.skill import Skill
from app.models.skill_version import SkillTestRun
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity
from app.models.version_components import OntologyVersionAction, OntologyVersionFunction
from app.services.skill_service import SkillService


@pytest.fixture()
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    owner = User(id="owner", username="owner", password_hash="x", name="Owner", role="editor")
    reader = User(id="reader", username="reader", password_hash="x", name="Reader", role="viewer")
    admin = User(id="admin", username="admin", password_hash="x", name="Admin", role="admin")
    ontology = ScenarioDict(id="ops", code="ops", name="设备运维")
    other = ScenarioDict(id="sales", code="sales", name="客户经营")
    db.add_all([owner, reader, admin, ontology, other])
    db.flush()
    entity = OntologyEntity(id="device", name="Device", name_cn="设备", tier=1, ontology_id=ontology.id)
    foreign = OntologyEntity(id="customer", name="Customer", name_cn="客户", tier=1, ontology_id=other.id)
    db.add_all([entity, foreign])
    db.flush()
    function = OntologyFunction(id="risk", name="设备风险评估", callable_name="device_risk", entity_id=entity.id,
                                ontology_id=ontology.id, logic_type="expression", logic_body="1")
    version = OntologyVersion(id="ops-v1", ontology_id=ontology.id, version_number=1, name="v1", status="published")
    foreign_version = OntologyVersion(id="sales-v1", ontology_id=other.id, version_number=1, name="v1", status="published")
    db.add_all([function, version, foreign_version])
    db.flush()
    entity_snap = OntologyVersionEntity(id="device-snap", version_id=version.id, source_entity_id=entity.id,
                                       name=entity.name, name_cn=entity.name_cn, tier=1)
    db.add(entity_snap)
    db.flush()
    db.add(OntologyVersionFunction(id="risk-snap", version_id=version.id, source_function_id=function.id,
        version_entity_id=entity_snap.id, name=function.name, callable_name=function.callable_name,
        logic_type="expression", logic_body="1"))
    db.add(Asset(id="manual", name="运维手册", kind="document", locator={"source_type": "file"},
                 domain="ops", parsed_summary="排查手册", status="active"))
    db.add(Asset(id="foreign-manual", name="客户手册", kind="document", locator={"source_type": "file"},
                 domain="sales", status="active"))
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db

    def auth(x_test_user: str | None = Header(default=None)):
        if not x_test_user:
            raise HTTPException(401, "请先登录")
        user = db.get(User, x_test_user)
        if not user:
            raise HTTPException(401, "无效用户")
        return user
    app.dependency_overrides[require_user] = auth
    client = TestClient(app)
    payload = {"name": "设备故障诊断", "description": "诊断与处置", "prompt_template": "根据告警提供诊断建议",
        "ontology_id": "ops", "ontology_version_id": "ops-v1", "entity_ids": ["device"],
        "tools": [{"type": "function", "id": "risk"}], "asset_refs": ["manual"],
        "visibility": "workspace", "test_cases": [{"id": "normal", "name": "告警分析",
          "input": "分析设备告警", "expected_keywords": ["风险"], "expected_tools": ["risk"]}]}
    yield {"db": db, "client": client, "app": app, "owner": owner, "reader": reader,
           "payload": payload, "service": SkillService(db)}
    db.close()
    engine.dispose()


def headers(user="owner"):
    return {"X-Test-User": user}


def create(setup, payload=None):
    response = setup["client"].post("/api/v1/skills", json=payload or setup["payload"], headers=headers())
    assert response.status_code == 201, response.text
    return response.json()


def successful_runtime(snapshot, case, user):
    assert snapshot["dependencies"]["functions"][0]["logic_body"] == "1"
    return {"answer": "风险较高，建议检查设备", "tool_runs": [{"tool": "ontology_run_logic",
            "arguments": {"callable_name": "device_risk"}, "result": {"success": True}}]}


def test_auth_private_workspace_and_edit_permission(setup):
    client = setup["client"]
    assert client.get("/api/v1/skills").status_code == 401
    payload = copy.deepcopy(setup["payload"])
    payload["visibility"] = "private"
    skill = create(setup, payload)
    path = f"/api/v1/skills/{skill['id']}"
    assert client.get(path, headers=headers("reader")).status_code == 404
    assert client.get("/api/v1/skills", headers=headers("reader")).json() == []
    assert client.get(path, headers=headers("admin")).status_code == 200
    response = client.put(path, json={"visibility": "workspace"}, headers=headers())
    assert response.status_code == 200
    assert client.get(path, headers=headers("reader")).json()["can_edit"] is False
    for suffix in ("/publish", "/archive", "/test"):
        assert client.post(path + suffix, json={}, headers=headers("reader")).status_code == 403
    assert client.put(path, json={"name": "非法改名"}, headers=headers("reader")).status_code == 403


def test_empty_draft_and_cross_ontology_dependencies(setup):
    draft = create(setup, {"name": "新技能"})
    assert draft["status"] == "draft" and draft["current_version"] == 0
    assert draft["entity_ids"] == [] and draft["tools"] == [] and draft["ref_count"] == 0
    for changes in ({"ontology_version_id": "sales-v1"}, {"entity_ids": ["customer"]},
                    {"asset_refs": ["foreign-manual"]}):
        payload = {**setup["payload"], **changes}
        response = setup["client"].post("/api/v1/skills", json=payload, headers=headers())
        assert response.status_code == 422, response.text
    assert setup["db"].query(Skill).count() == 1
    catalog = setup["client"].get("/api/v1/skills/catalog?ontology_id=ops&ontology_version_id=ops-v1", headers=headers()).json()
    assert [e["id"] for e in catalog["entities"]] == ["device"]
    assert [a["id"] for a in catalog["assets"]] == ["manual"]


def test_no_runner_does_not_claim_runtime_pass_or_publish(setup):
    skill = create(setup)
    path = f"/api/v1/skills/{skill['id']}"
    run = setup["client"].post(path + "/test", json={}, headers=headers()).json()
    assert run["validation_level"] == "static" and run["status"] == "not_run" and not run["passed"]
    assert setup["client"].post(path + "/publish", json={}, headers=headers()).status_code == 409


def test_runtime_error_failed_tool_and_expectation_mismatch(setup):
    skill = create(setup)
    service = setup["service"]
    model = service.get(skill["id"], setup["owner"])
    for runner in (
        lambda *_: {"answer": "AI 服务调用失败", "error": "LLM timeout"},
        lambda *_: {"answer": "风险", "tool_runs": [{"tool": "device_risk", "success": False}]},
        lambda *_: {"answer": "无异常", "tool_runs": []},
    ):
        result = service.run_tests(model, setup["owner"], runner=runner)
        assert result["validation_level"] == "runtime" and not result["passed"]
        assert result["case_results"][0]["errors"]
    with pytest.raises(HTTPException) as error:
        service.publish(model, setup["owner"])
    assert error.value.status_code == 409


def test_publication_snapshot_and_instruction_or_asset_change_invalidates_evidence(setup):
    skill = create(setup)
    client, app = setup["client"], setup["app"]
    path = f"/api/v1/skills/{skill['id']}"
    app.state.skill_test_runner = successful_runtime
    assert client.post(path + "/test", json={}, headers=headers()).json()["passed"]
    published = client.post(path + "/publish", json={"description": "初版"}, headers=headers()).json()
    assert published["current_version"] == 1 and published["status"] == "active" and not published["has_changes"]
    snapshot = client.get(path + "/versions/1", headers=headers()).json()["snapshot_json"]
    assert snapshot["prompt_template"] == "根据告警提供诊断建议"
    changed = client.put(path, json={"prompt_template": "增加证据核查"}, headers=headers()).json()
    assert changed["has_changes"] and changed["current_version"] == 1
    assert client.post(path + "/publish", json={}, headers=headers()).status_code == 409
    assert client.get(path + "/versions/1", headers=headers()).json()["snapshot_json"] == snapshot
    assert client.post(path + "/test", json={}, headers=headers()).json()["passed"]
    asset = setup["db"].get(Asset, "manual")
    asset.parsed_summary = "新增排查证据"
    setup["db"].commit()
    assert client.post(path + "/publish", json={}, headers=headers()).status_code == 409
    assert client.post(path + "/test", json={}, headers=headers()).json()["passed"]
    assert client.post(path + "/publish", json={}, headers=headers()).json()["current_version"] == 2


def test_skill_inspection_redacts_action_credentials_without_changing_runtime_snapshot(setup):
    db, service, owner = setup["db"], setup["service"], setup["owner"]
    config = {"url": "https://u:secret-password@example.invalid/hook?token=secret-url-key",
              "headers": {"Authorization": "Bearer secret-action-key", "X-API-Key": "secret-header-key"}}
    db.add(EntityAction(id="notify", entity_id="device", ontology_id="ops", name="通知",
                        action_type="http", type_config=config))
    db.add(OntologyVersionAction(id="notify-snap", version_id="ops-v1", source_action_id="notify",
        version_entity_id="device-snap", name="通知", action_type="http", type_config=config))
    db.commit()
    payload = copy.deepcopy(setup["payload"])
    payload["tools"].append({"type": "action", "id": "notify"})
    skill = create(setup, payload)
    path = f"/api/v1/skills/{skill['id']}"
    model = service.get(skill["id"], owner)
    original_fingerprint = service.validate(model, owner)["fingerprint"]
    inspection = setup["client"].post(path + "/validate", headers=headers("reader"))
    assert inspection.status_code == 200 and "secret-" not in inspection.text
    assert inspection.json()["fingerprint"] == original_fingerprint

    def runner(snapshot, case, user):
        assert snapshot["dependencies"]["actions"][0]["type_config"] == config
        return successful_runtime(snapshot, case, user)
    setup["app"].state.skill_test_runner = runner
    assert setup["client"].post(path + "/test", headers=headers()).json()["passed"]
    assert setup["client"].post(path + "/publish", json={}, headers=headers()).status_code == 200
    version = setup["client"].get(path + "/versions/1", headers=headers("reader"))
    assert version.status_code == 200 and "secret-" not in version.text
    raw = service.get_published_snapshot(skill["id"], 1, owner)
    assert raw["dependencies"]["actions"][0]["type_config"] == config
    assert raw["fingerprint"] == original_fingerprint


def test_subset_tests_cannot_publish_without_all_current_cases(setup):
    payload = copy.deepcopy(setup["payload"])
    payload["test_cases"].append({"id": "missing", "name": "缺失标识", "input": "设备告警如何处理",
                                 "expected_keywords": ["风险"], "expected_tools": []})
    skill = create(setup, payload)
    path = f"/api/v1/skills/{skill['id']}"
    setup["app"].state.skill_test_runner = successful_runtime
    assert setup["client"].post(path + "/test", json={"test_case_ids": ["normal"]}, headers=headers()).json()["passed"]
    assert setup["client"].post(path + "/publish", json={}, headers=headers()).status_code == 409
    assert setup["client"].post(path + "/test", json={"test_case_ids": ["missing"]}, headers=headers()).json()["passed"]
    assert setup["client"].post(path + "/publish", json={}, headers=headers()).status_code == 200


def test_archive_fixed_snapshot_and_delete_reference_protection(setup):
    skill = create(setup)
    service, owner = setup["service"], setup["owner"]
    model = service.get(skill["id"], owner)
    service.run_tests(model, owner, successful_runtime)
    service.publish(model, owner)
    setup["db"].add(Agent(name="运维助手", tools_config={"skill_bindings": [{"skill_id": model.id, "version": 1}]}))
    setup["db"].commit()
    assert service.to_dict(model, owner)["ref_count"] == 1
    with pytest.raises(HTTPException) as error:
        service.delete(model)
    assert error.value.status_code == 409
    service.archive(model, owner)
    with pytest.raises(HTTPException):
        service.get_published_snapshot(model.id, 1, owner)
    assert service.get_published_snapshot(model.id, 1, owner, allow_archived=True)["version"] == 1
    assert service.archive(model, owner, restore=True)["status"] == "active"
    setup["db"].query(Agent).delete()
    setup["db"].commit()
    service.delete(model)
    assert setup["db"].query(SkillTestRun).count() == 0


def test_published_agent_still_protects_referenced_skill_after_draft_unmount(setup):
    skill = create(setup)
    service, owner = setup["service"], setup["owner"]
    model = service.get(skill["id"], owner)
    service.run_tests(model, owner, successful_runtime)
    service.publish(model, owner)
    agent = Agent(name="运维助手", tools_config={"skill_bindings": []})
    setup["db"].add(agent)
    setup["db"].flush()
    setup["db"].add(AgentVersion(agent_id=agent.id, version=1, config_hash="hash", published_by=owner.id,
        config_snapshot={"tools_config": {"skill_bindings": [{"skill_id": model.id, "version": 1}]}}))
    setup["db"].commit()
    references = service.references(model)
    assert len(references) == 1 and references[0]["source"] == "published"
    assert references[0]["agent_version"] == 1
    with pytest.raises(HTTPException) as error:
        service.delete(model)
    assert error.value.status_code == 409
