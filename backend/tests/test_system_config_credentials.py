"""UI 编辑、设默认和连通性测试必须保留已保存的真实凭据。"""
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1 import system_config
from app.models.system_config import SystemConfig
from app.schemas.system_config import ConfigSaveRequest


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    SystemConfig.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.mark.parametrize("secret", ["short", "sk-real-api-key-123456789"])
def test_model_edit_and_set_default_preserve_masked_key(db, secret):
    model = {"id": "m1", "name": "Before", "api_key": secret, "is_default": False}
    row = SystemConfig(group="ai", key="ai.models", value=json.dumps([model]))
    db.add(row)
    db.commit()
    displayed = system_config.get_ai_models(db, None)["models"]
    assert displayed[0]["api_key"] != secret
    displayed[0].update(name="After", is_default=True)
    system_config.save_ai_models({"models": displayed}, db, SimpleNamespace(username="admin"))
    persisted = json.loads(row.value)[0]
    assert persisted["api_key"] == secret
    assert persisted["name"] == "After"
    assert persisted["is_default"] is True


def test_model_new_key_replaces_old_key(db):
    row = SystemConfig(group="ai", key="ai.models", value=json.dumps([{"id": "m1", "api_key": "old-secret"}]))
    db.add(row)
    db.commit()
    system_config.save_ai_models({"models": [{"id": "m1", "api_key": "new-secret"}]}, db, SimpleNamespace(username="admin"))
    assert json.loads(row.value)[0]["api_key"] == "new-secret"


@pytest.mark.parametrize("key", ["smtp_password", "notification.smtp_password"])
@pytest.mark.parametrize("secret", ["short", "real-smtp-secret-123456"])
def test_grouped_secret_is_masked_and_other_field_save_preserves_it(db, key, secret):
    password = SystemConfig(group="notification", key=key, value=secret)
    host = SystemConfig(group="notification", key="smtp_host", value="old.example")
    db.add_all([password, host])
    db.commit()
    displayed = system_config.get_all_config(db, None).groups["notification"]
    item = next(i for i in displayed if i["key"] == key)
    assert item["is_sensitive"] is True
    assert item["value"] != secret
    payload = ConfigSaveRequest(group="notification", items=[
        {"key": key, "value": item["value"]},
        {"key": "smtp_host", "value": "new.example"},
    ])
    system_config.save_config(payload, db, SimpleNamespace(username="admin"))
    assert password.value == secret
    assert host.value == "new.example"
    assert system_config._get_config_value(db, "notification.smtp_password") == secret


def test_saved_model_test_uses_real_key_without_exposing_it(db, monkeypatch):
    secret = "real-test-secret-123456"
    db.add(SystemConfig(group="ai", key="ai.models", value=json.dumps([{"id": "m1", "api_key": secret}])))
    db.commit()
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, headers):
            captured.update(headers)
            return SimpleNamespace(status_code=200)

    monkeypatch.setattr("httpx.Client", FakeClient)
    result = system_config.test_ai_model({
        "id": "m1", "api_key": system_config._mask_model_api_key(secret),
        "model_id": "test-model", "base_url": "http://example.test",
    }, db, None)
    assert result.success
    assert captured["Authorization"] == f"Bearer {secret}"
    assert secret not in result.message
