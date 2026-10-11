"""Model credentials and referenced application releases remain protected."""
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.api.v1.models import router
from app.core.deps import require_user
from app.database import Base, get_db
from app.models.agent import Agent, ModelRegistry
from app.models.agent_runtime import AgentVersion
from app.models.user import User


@pytest.fixture()
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    users = [User(id=role, username=role, password_hash="x", name=role, role=role, is_active=True)
             for role in ("admin", "editor", "viewer")]
    inactive = User(id="disabled", username="disabled", password_hash="x", name="disabled", role="admin", is_active=False)
    model = ModelRegistry(id="model", name="Active model", provider="openai", model_name="example",
        api_key="secret-main-key", api_base="https://user:secret-password@example.invalid/v1?token=secret-url-key",
        config_json={"temperature": 0, "api_key": "secret-nested-key", "headers": {"Authorization": "secret-header-key"}})
    disabled = ModelRegistry(id="inactive", name="Inactive model", provider="openai", model_name="example", status="inactive")
    db.add_all([*users, inactive, model, disabled])
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    def auth(x_test_user: str | None = Header(default=None)):
        if not x_test_user:
            raise HTTPException(401, "请先登录")
        return db.get(User, x_test_user)
    app.dependency_overrides[require_user] = auth
    yield db, TestClient(app)
    db.close()
    engine.dispose()


def headers(role="editor"):
    return {"X-Test-User": role}


def test_model_catalog_requires_login_and_active_identity_and_hides_inactive(setup):
    _, client = setup
    assert client.get("/api/v1/models").status_code == 401
    assert client.get("/api/v1/models", headers=headers("disabled")).status_code == 403
    response = client.get("/api/v1/models", headers=headers("viewer"))
    assert response.status_code == 200
    assert [m["id"] for m in response.json()] == ["model"]
    assert client.get("/api/v1/models/inactive", headers=headers("viewer")).status_code == 404
    for role in ("admin", "editor"):
        response = client.get("/api/v1/models", headers=headers(role))
        assert {m["id"] for m in response.json()} == {"model", "inactive"}
        assert client.get("/api/v1/models/inactive", headers=headers(role)).status_code == 200
    assert client.put("/api/v1/models/inactive", json={"status": "active"}, headers=headers()).status_code == 200
    assert client.get("/api/v1/models/inactive", headers=headers("viewer")).status_code == 200


def test_model_catalog_does_not_expose_credentials_in_base_or_nested_options(setup):
    _, client = setup
    response = client.get("/api/v1/models/model", headers=headers("viewer"))
    assert response.status_code == 200
    assert "secret-" not in response.text
    assert response.json()["api_key"] == "***"
    assert response.json()["config_json"]["headers"]["Authorization"] == "***"


def test_viewers_cannot_write_delete_or_trigger_paid_model_test(setup):
    _, client = setup
    assert client.post("/api/v1/models", json={"name": "new", "provider": "openai", "model_name": "new"}, headers=headers("viewer")).status_code == 403
    assert client.put("/api/v1/models/model", json={"name": "unauthorized"}, headers=headers("viewer")).status_code == 403
    assert client.delete("/api/v1/models/model", headers=headers("viewer")).status_code == 403
    assert client.post("/api/v1/models/model/test", headers=headers("viewer")).status_code == 403


def test_draft_agent_prevents_model_deletion(setup):
    db, client = setup
    db.add(Agent(id="agent", name="Draft", model_id="model", status="draft"))
    db.commit()
    response = client.delete("/api/v1/models/model", headers=headers())
    assert response.status_code == 409
    assert db.get(ModelRegistry, "model") is not None


def test_historical_release_prevents_model_deletion_after_draft_switch(setup):
    db, client = setup
    db.add(Agent(id="agent", name="Application", model_id="inactive", status="published"))
    db.flush()
    db.add_all([
        AgentVersion(agent_id="agent", version=1, config_hash="old", published_by="editor",
                     config_snapshot={"model_id": "model"}),
        AgentVersion(agent_id="agent", version=2, config_hash="new", published_by="editor",
                     config_snapshot={"model_id": "inactive"}),
    ])
    db.commit()
    response = client.delete("/api/v1/models/model", headers=headers("admin"))
    assert response.status_code == 409
    assert db.get(ModelRegistry, "model") is not None


def test_unreferenced_model_can_be_deleted_and_masked_key_is_preserved_on_update(setup):
    db, client = setup
    response = client.put("/api/v1/models/model", json={"name": "Renamed", "api_key": "***"}, headers=headers())
    assert response.status_code == 200
    assert db.get(ModelRegistry, "model").api_key == "secret-main-key"
    assert client.delete("/api/v1/models/model", headers=headers()).status_code == 200
    assert db.get(ModelRegistry, "model") is None


def test_editing_redacted_model_preserves_nested_and_endpoint_credentials(setup):
    db, client = setup
    read = client.get("/api/v1/models/model", headers=headers()).json()
    read["config_json"]["temperature"] = 0.5
    response = client.put("/api/v1/models/model", json={
        "api_base": read["api_base"], "api_key": read["api_key"], "config_json": read["config_json"]}, headers=headers())
    assert response.status_code == 200
    model = db.get(ModelRegistry, "model")
    assert model.api_base == "https://user:secret-password@example.invalid/v1?token=secret-url-key"
    assert model.api_key == "secret-main-key"
    assert model.config_json["api_key"] == "secret-nested-key"
    assert model.config_json["headers"]["Authorization"] == "secret-header-key"
    assert model.config_json["temperature"] == 0.5


def test_recursive_url_and_header_redaction_keeps_raw_storage(setup):
    db, client = setup
    raw_url = "https://u:secret-url-password@example.invalid/v1?apiKey=secret-url-key&api-version=2025-01-01"
    raw_config = {"providers": [{"base_url": raw_url, "headers": {"X-API-Key": "secret-header-key"}}],
                  "note": f"Endpoint: {raw_url}"}
    response = client.put("/api/v1/models/model", json={"api_base": raw_url, "config_json": raw_config}, headers=headers())
    assert response.status_code == 200
    assert "secret-" not in response.text
    assert "api-version=2025-01-01" in response.text
    model = db.get(ModelRegistry, "model")
    assert model.api_base == raw_url
    assert model.config_json["providers"] == raw_config["providers"]


def test_connection_test_uses_model_client_helper_and_redacts_error(setup, monkeypatch):
    db, client = setup
    seen = {}
    def failed_client(**kwargs):
        seen.update(kwargs)
        raise RuntimeError(f"request to {kwargs['api_base']} failed: {kwargs['api_key']}")
    monkeypatch.setattr("app.services.llm_resolver.get_llm_client", failed_client)
    response = client.post("/api/v1/models/model/test", headers=headers())
    assert response.status_code == 200 and not response.json()["ok"]
    assert "secret-" not in response.text
    assert seen["db"] is db and seen["scene"] == "agent"
    assert seen["api_base"] == db.get(ModelRegistry, "model").api_base
