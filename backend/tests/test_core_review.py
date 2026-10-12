"""Regression: production route access, durable permissions, groups and imports."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.database import Base, get_db
from app.main import app as production
from app.models import OntologyEntity, ScenarioDict, User
from app.services.file_import import parse_json_ontology, parse_owl_ontology
from app.migrations import run_startup_migrations


@pytest.fixture
def fixture():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    for role in ("admin", "editor", "viewer"):
        db.add(User(id=role, username=role, name=role, role=role, password_hash=hash_password("Fixture123!")))
    db.add_all([ScenarioDict(id="a", code="a", name="A"), ScenarioDict(id="b", code="b", name="B")])
    db.add_all([OntologyEntity(id="ea", ontology_id="a", name="Device", name_cn="设备A", tier=1),
                OntologyEntity(id="eb", ontology_id="b", name="Device", name_cn="设备B", tier=1)])
    db.commit()
    app = FastAPI()
    app.include_router(production.router)
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), db
    db.close()
    engine.dispose()


def auth(role):
    return {"Authorization": f"Bearer {create_access_token(role)}"}


def test_platform_config_is_public_safe_validated_and_durable(fixture):
    from app.models.system_config import SystemConfig
    client, db = fixture
    assert client.get("/api/v1/auth/platform-config").json() == {
        "system_name": "本体管理平台", "language": "zh-CN", "timezone": "Asia/Shanghai"}
    db.add(SystemConfig(group="auth", key="auth.client_secret", value="never-public"))
    db.commit()
    items = [{"key": "system_name", "value": "检修平台"}, {"key": "language", "value": "en"},
             {"key": "timezone", "value": "UTC"}]
    assert client.put("/api/v1/system-config", headers=auth("viewer"), json={"group": "basic", "items": items}).status_code == 403
    assert client.put("/api/v1/system-config", headers=auth("admin"), json={"group": "basic", "items": items}).status_code == 200
    db.expire_all()
    public = client.get("/api/v1/auth/platform-config").json()
    assert public == {"system_name": "检修平台", "language": "en", "timezone": "UTC"}
    assert "never-public" not in str(public)
    assert client.put("/api/v1/system-config", headers=auth("admin"), json={"group": "basic", "items": [{"key": "basic.system_name", "value": "检修平台"}]}).status_code == 200
    assert db.query(SystemConfig).filter_by(group="basic").count() == 3
    for key, value in (("timezone", "invalid"), ("language", "fr"), ("system_name", " ")):
        invalid = [{"key": "system_name", "value": "must-not-leak"}, {"key": key, "value": value}]
        assert client.put("/api/v1/system-config", headers=auth("admin"), json={"group": "basic", "items": invalid}).status_code == 422
        assert client.get("/api/v1/auth/platform-config").json() == public
    assert client.put("/api/v1/system-config", headers=auth("admin"), json={"group": "basic", "items": [{"key": "auth.new_secret", "value": "bad"}]}).status_code == 422


def test_refresh_is_not_access_and_disabled_logout_revoke(fixture):
    client, db = fixture
    assert client.get("/api/v1/entities").status_code == 401
    assert client.get("/api/v1/entities", headers={"Authorization": f"Bearer {create_refresh_token('admin')}"}).status_code == 401
    assert client.get("/api/v1/entities", headers=auth("admin")).status_code == 200
    refresh = create_refresh_token("admin")
    assert client.post("/api/v1/auth/logout", headers=auth("admin")).status_code == 200
    assert client.get("/api/v1/entities", headers=auth("admin")).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    db.get(User, "editor").is_active = False
    db.commit()
    assert client.get("/api/v1/entities", headers=auth("editor")).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": create_refresh_token("editor")}).status_code == 401


def test_viewer_cannot_mutate_and_permissions_survive_new_session(fixture):
    client, db = fixture
    payload = {"name": "collection", "entity_ids": ["ea"]}
    assert client.post("/api/v1/ontology/a/groups", json=payload, headers=auth("viewer")).status_code == 403
    assert client.put("/api/v1/auth/roles/viewer/permissions", json={"permissions": ["entity:read", "entity:write"]}, headers=auth("admin")).status_code == 200
    db.expire_all()
    assert client.get("/api/v1/auth/me", headers=auth("viewer")).json()["permissions"] == ["entity:read", "entity:write"]
    assert client.post("/api/v1/ontology/a/groups", json=payload, headers=auth("viewer")).status_code == 201


def test_scenario_status_comes_from_active_published_version(fixture):
    from app.models import OntologyVersion
    client, db = fixture
    db.add_all([OntologyVersion(id="v-a", ontology_id="a", name="A published", version_number=1, status="published", is_active=True),
                OntologyVersion(id="v-b", ontology_id="b", name="B pending", version_number=1, status="pending", is_active=False)])
    db.commit()
    rows = {r["id"]: r for r in client.get('/api/v1/scenarios', headers=auth('viewer')).json()}
    assert rows['a']['active_version_id'] == 'v-a' and rows['a']['version_number'] == 1
    assert rows['b']['active_version_id'] is None and rows['b']['version_number'] is None


def test_group_membership_isolated_edit_readback_and_delete_cleanup(fixture):
    client, db = fixture
    headers = auth("admin")
    assert client.post("/api/v1/ontology/a/groups", json={"name": "cross", "entity_ids": ["eb"]}, headers=headers).status_code == 422
    created = client.post("/api/v1/ontology/a/groups", json={"name": "检修组", "entity_ids": ["ea"]}, headers=headers)
    assert created.status_code == 201
    gid = created.json()["id"]
    assert client.put(f"/api/v1/ontology/b/groups/{gid}", json={"name": "bad"}, headers=headers).status_code == 404
    assert client.get("/api/v1/ontology/a/groups", headers=headers).json()[0]["entity_ids"] == ["ea"]
    assert client.get("/api/v1/ontology/b/groups", headers=headers).json() == []
    assert client.delete("/api/v1/entities/ea", headers=headers).status_code == 204
    assert client.get("/api/v1/ontology/a/groups", headers=headers).json()[0]["entity_ids"] == []
    assert db.get(OntologyEntity, "eb").name_cn == "设备B"


def test_json_and_rdf_same_names_do_not_mutate_other_ontology(fixture):
    _, db = fixture
    data = {"object_types": [{"name": "Sensor", "properties": [{"name": "id", "type": "string"}]}]}
    parse_json_ontology(data, "ns", db, ontology_id="a")
    parse_json_ontology(data, "ns", db, ontology_id="b")
    db.commit()
    a = db.query(OntologyEntity).filter_by(ontology_id="a", name="Sensor").one()
    b = db.query(OntologyEntity).filter_by(ontology_id="b", name="Sensor").one()
    assert a.id != b.id and a.attributes[0].id != b.attributes[0].id
    ttl = b'@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix ex: <http://example.test/> . ex:Asset a owl:Class .'
    parse_owl_ontology(ttl, "turtle", db, ontology_id="a")
    parse_owl_ontology(ttl, "turtle", db, ontology_id="b")
    db.commit()
    assert db.query(OntologyEntity).filter_by(name="Asset").count() == 2


def test_startup_migration_idempotent_and_retains_legacy_rules():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE business_rules (id TEXT PRIMARY KEY, body TEXT)"))
        conn.execute(text("INSERT INTO business_rules VALUES ('historical', 'keep')"))
    run_startup_migrations(engine)
    run_startup_migrations(engine)
    assert "token_version" in {c["name"] for c in inspect(engine).get_columns("users")}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT body FROM business_rules WHERE id='historical'")).scalar() == "keep"
    engine.dispose()


def test_initial_admin_requires_configured_strong_password_and_never_resets_existing(monkeypatch):
    from app.api.v1.auth import seed_admin
    from app.config import settings
    from app.core.security import verify_password
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        monkeypatch.setattr(settings, "ADMIN_INITIAL_PASSWORD", "")
        with pytest.raises(RuntimeError, match="首次初始化必须配置"):
            seed_admin(db)
        monkeypatch.setattr(settings, "ADMIN_INITIAL_PASSWORD", "admin")
        with pytest.raises(RuntimeError, match="不符合密码策略"):
            seed_admin(db)
        assert db.query(User).count() == 0
        monkeypatch.setattr(settings, "ADMIN_INITIAL_PASSWORD", "IsolatedAdmin2026!")
        seed_admin(db)
        first = db.query(User).one()
        assert first.username == "admin" and verify_password("IsolatedAdmin2026!", first.password_hash)
        original_hash = first.password_hash
        monkeypatch.setattr(settings, "ADMIN_INITIAL_PASSWORD", "")
        seed_admin(db)
        db.expire_all()
        assert db.query(User).one().password_hash == original_hash
    engine.dispose()


def test_attribute_editor_mapping_relation_rename_and_forced_delete_are_consistent(fixture):
    from app.models import EntityAttribute
    from app.models.asset import Asset
    from app.models.object_binding import ObjectBinding
    client, db = fixture
    headers = auth("admin")
    db.add(Asset(id="asset-a", name="设备数据", kind="table", locator={"table": "devices"},
                 schema_snapshot=[{"name": "device_id", "type": "string", "is_pk": True}], primary_key=["device_id"]))
    db.add(EntityAttribute(id="b-id", entity_id="eb", name="id", type="string"))
    db.commit()
    response = client.post("/api/v1/entities/ea/attributes", headers=headers,
                           json={"name": "id", "type": "string", "source_table": "devices", "source_field": "device_id"})
    assert response.status_code == 201, response.text
    aid = response.json()["id"]
    binding = db.query(ObjectBinding).filter_by(object_type_id="ea").one()
    assert binding.field_mappings[0]["attribute_id"] == aid
    assert client.post("/api/v1/entities/ea/attributes", headers=headers, json={"name": "id", "type": "string"}).status_code == 409
    # Sharing an unrelated object into a third scope cannot authorize A -> B.
    relation = dict(from_entity_id="ea", to_entity_id="eb", name="related", source_field="id", target_field="id", cardinality="1:1")
    assert client.post("/api/v1/relations", headers=headers, json=relation).status_code == 400
    target = client.post("/api/v1/entities", headers=headers,
                         json={"ontology_id": "a", "name": "Ticket", "name_cn": "工单", "tier": 1, "attributes": [{"name": "device", "type": "string"}]}).json()
    relation.update(to_entity_id=target["id"], target_field="device")
    created = client.post("/api/v1/relations", headers=headers, json=relation)
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    renamed = client.put(f"/api/v1/entities/ea/attributes/{aid}", headers=headers,
                         json={"name": "device_code", "type": "string", "source_table": "devices", "source_field": "device_id"})
    assert renamed.status_code == 200, renamed.text
    assert client.get("/api/v1/relations?ontology_id=a", headers=headers).json()[0]["source_field"] == "device_code"
    relation.update(source_field="device_code", name="维修对象")
    assert client.put(f"/api/v1/relations/{rid}", headers=headers, json=relation).status_code == 200
    assert client.delete(f"/api/v1/entities/ea/attributes/{aid}", headers=headers).status_code == 409
    assert client.delete(f"/api/v1/entities/ea/attributes/{aid}?force=true", headers=headers).status_code == 204
    assert db.query(ObjectBinding).filter_by(id=binding.id).one().field_mappings == []
    assert client.get("/api/v1/relations?ontology_id=a", headers=headers).json()[0]["source_field"] is None
    assert client.delete("/api/v1/entities/ea?force=true", headers=headers).status_code == 204
    assert db.query(ObjectBinding).filter_by(object_type_id="ea").count() == 0
    assert client.get("/api/v1/relations?ontology_id=a", headers=headers).json() == []
