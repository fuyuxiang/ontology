"""End-to-end regressions for confirmed mapping/publish/relation defects.

Metadata and source databases are isolated; reads exercise real repositories,
version snapshots and SQLite connector paths instead of mocked result rows.
"""
import sqlite3
from urllib.parse import urlsplit, parse_qs

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_builder_delivery import environment, draft  # noqa: F401
from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from test_enrichment_review import enrichment_fixture
from app.api.v1 import builder, doc_builder, ontology_api, ontology_publish
from app.core.deps import require_user
from app.database import get_db
from app.models.asset import Asset
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.object_binding import ObjectBinding
from app.models.quality_rule import QualityRule, HealthStatus
from app.models.user import User
from app.models.version import OntologyVersion
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.execute_service import ExecuteService
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.data_plane.quality_rule_service import QualityRuleService


def effective_draft(item, ontology_id, session_id):
    return {"ontology_id": ontology_id, "document_session_id": session_id, "objects": [{
        "name": item["entity_name"], "primaryKey": item["primary_key"],
        "backing_asset_ids": item["backing_asset_ids"], "enrichment_bindings": item["enrichment_bindings"],
        "properties": [{"name": f["attribute_name"], "type": f["type"], "required": f["required"],
                        "source_asset_id": f["source_asset_id"], "source_column": f["source_column"],
                        "transform": f["transform"]} for f in item["field_mappings"]]}]}


def test_document_keep_returns_actual_attributes_and_survives_finalize(environment):
    client, sessions = environment
    with sessions() as db:
        asset = db.get(Asset, "asset")
        asset.schema_snapshot = [*asset.schema_snapshot, {"name": "spare", "type": "number"}]
        db.commit()
    initial = client.post("/builder/finalize", json=draft("oa"))
    initial.raise_for_status()
    entity_id = initial.json()["entity_ids"]["Device"]
    with sessions() as db:
        binding = db.query(ObjectBinding).filter_by(object_type_id=entity_id).one()
        binding_id = binding.id
        binding.filter_expr = "device_id <> 'hidden'"
        db.commit()
    session_id = client.post("/doc-builder/upload", files={"files": ("device.md", b"Device: id, risk", "text/markdown")}).json()["session_id"]
    mapping = {"entities": [{"name": "Device", "table": "devices", "asset_id": "asset", "primaryKey": "id",
                "properties": [{"name": "id", "field": "device_id", "type": "string", "required": True},
                               {"name": "candidate", "field": "spare", "type": "number"}]}], "relations": []}
    applied = client.post("/doc-builder/mapping/apply", json={"session_id": session_id, "ontology_id": "oa",
        "mapping_result": mapping, "items": [{"entity_name": "Device", "entity_id": entity_id,
                                                "asset_id": "asset", "conflict_action": "keep"}]})
    assert applied.status_code == 200, applied.text
    assert applied.json()["skipped"] == 1
    item = applied.json()["items"][0]
    assert {f["attribute_name"]: f["source_column"] for f in item["field_mappings"]} == {"id": "device_id", "risk": "risk_score"}
    stale = draft("oa", "spare")
    stale["document_session_id"] = session_id
    assert client.post("/builder/finalize", json=stale).status_code == 409
    completed = client.post("/builder/finalize", json=effective_draft(item, "oa", session_id))
    assert completed.status_code == 200, completed.text
    with sessions() as db:
        binding = db.query(ObjectBinding).filter_by(object_type_id=entity_id).one()
        assert binding.id == binding_id and binding.filter_expr == "device_id <> 'hidden'"
        attrs = {a.id: a.name for a in db.query(EntityAttribute).filter_by(entity_id=entity_id)}
        assert {attrs[f["attribute_id"]]: f["source_column"] for f in binding.field_mappings} == {"id": "device_id", "risk": "risk_score"}
    assert client.post("/ontology-publish/quick-publish", json={"ontology_id": "oa"}).status_code == 200
    # A second editor cannot make an older keep decision silently authoritative.
    client.post("/builder/finalize", json=draft("oa", "spare")).raise_for_status()
    assert client.post("/builder/finalize", json=effective_draft(item, "oa", session_id)).status_code == 409


def test_document_source_switch_is_a_conflict_and_overwrite_replaces_primary(environment):
    client, sessions = environment
    entity_id = client.post("/builder/finalize", json=draft("oa")).json()["entity_ids"]["Device"]
    with sessions() as db:
        db.add(Asset(id="other", name="other devices", kind="table", status="active", locator={"table": "other_devices"},
                     schema_snapshot=[{"name": "serial", "type": "string"}, {"name": "risk", "type": "number"}], primary_key=["serial"]))
        db.commit()
    mapping = {"entities": [{"name": "Device", "asset_id": "other", "table": "other_devices", "primaryKey": "id",
        "properties": [{"name": "id", "field": "serial", "required": True}, {"name": "risk", "field": "risk", "type": "number"}]}]}
    preview = client.post("/doc-builder/mapping/preview", json={"session_id": "switch", "ontology_id": "oa", "mapping_result": mapping})
    assert preview.json()["items"][0]["conflict"]["existing_asset_name"] == "devices"
    response = client.post("/doc-builder/mapping/apply", json={"session_id": "switch", "ontology_id": "oa", "mapping_result": mapping,
        "items": [{"entity_name": "Device", "entity_id": entity_id, "asset_id": "other", "conflict_action": "overwrite"}]})
    assert response.status_code == 200, response.text
    assert response.json()["updated"] == 1
    with sessions() as db:
        primary = db.query(ObjectBinding).filter_by(object_type_id=entity_id, role="primary").one()
        assert primary.asset_id == "other" and primary.status == "active" and primary.id_column == "serial"


def source_client(db):
    app = FastAPI()
    for api in (builder, doc_builder, ontology_publish, ontology_api):
        app.include_router(api.router)
    def database():
        try:
            yield db
        finally:
            # Production opens a fresh session for each request. Expire the
            # fixture identity map to emulate that boundary without closing it.
            db.expire_all()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[require_user] = lambda: User(id="owner", username="owner", password_hash="x", name="Owner", role="admin", is_active=True)
    return TestClient(app)


def test_finalize_moves_property_and_swaps_asset_roles_atomically(data_env, tmp_path, monkeypatch):
    db, _, _, enrichment_asset = enrichment_fixture(data_env, tmp_path, monkeypatch)
    enrich = ObjectBindingService(db).create(object_type_id="device", asset_id=enrichment_asset.id, role="enrichment",
        primary_source_column="device_id", enrichment_source_column="serial", field_mappings=[{"attribute_id": "owner", "source_column": "owner"}])
    db.commit()
    primary_id = db.query(ObjectBinding).filter_by(object_type_id="device", role="primary").one().id
    client = source_client(db)
    request = {"ontology_id": "a", "objects": [{"name": "Device", "primaryKey": "id", "backing_asset_ids": ["asset", enrichment_asset.id],
        "enrichment_bindings": [{"asset_id": enrichment_asset.id, "primary_source_column": "device_id", "enrichment_source_column": "serial"}],
        "properties": [{"name": "id", "required": True, "source_asset_id": "asset", "source_column": "device_id"},
                       {"name": "temperature", "type": "number", "source_asset_id": "asset", "source_column": "temp"},
                       {"name": "owner", "source_asset_id": "asset", "source_column": "private"}]}]}
    result = client.post("/builder/finalize", json=request)
    assert result.status_code == 200, result.text
    assert db.query(ObjectBinding).filter_by(object_type_id="device", role="primary").one().id == primary_id
    assert db.query(ObjectBinding).filter_by(object_type_id="device", role="enrichment").one().id == enrich.id
    assert EntityDataService(db).query_entity_data("device", fields=["owner"])["rows"] == [["secret"], ["secret2"]]
    obj = request["objects"][0]
    obj["backing_asset_ids"] = [enrichment_asset.id, "asset"]
    obj["enrichment_bindings"] = [{"asset_id": "asset", "primary_source_column": "serial", "enrichment_source_column": "device_id"}]
    obj["properties"] = [{"name": "id", "required": True, "source_asset_id": enrichment_asset.id, "source_column": "record_id"},
                         {"name": "temperature", "type": "number", "source_asset_id": "asset", "source_column": "spare"},
                         {"name": "owner", "source_asset_id": enrichment_asset.id, "source_column": "owner"}]
    swapped = client.post("/builder/finalize", json=request)
    assert swapped.status_code == 200, swapped.text
    assert db.query(ObjectBinding).filter_by(object_type_id="device").count() == 2
    assert db.query(ObjectBinding).filter_by(object_type_id="device", role="primary").one().asset_id == enrichment_asset.id
    assert EntityDataService(db).query_entity_data("device", fields=["id", "temperature", "owner"])["rows"] == [["o1", 30.0, "Team A"]]
    # Invalid joins after releasing old assignments must roll the entire set back.
    obj["enrichment_bindings"][0]["enrichment_source_column"] = "missing"
    assert client.post("/builder/finalize", json=request).status_code == 422
    assert EntityDataService(db).query_entity_data("device", fields=["id", "temperature", "owner"])["rows"] == [["o1", 30.0, "Team A"]]


def test_shared_asset_quality_survives_owner_update_and_deactivation(data_env):
    db, _ = data_env
    first = bind(db)
    db.add(EntityAttribute(id="foreign-temp", entity_id="foreign", name="temperature", type="number", required=True))
    db.commit()
    service = ObjectBindingService(db)
    second = service.create(object_type_id="foreign", asset_id="asset", id_column="device_id", field_mappings=[
        {"attribute_id": "foreign-id", "source_column": "device_id"}, {"attribute_id": "foreign-temp", "source_column": "temp"}])
    db.commit()
    service.update(first.id, field_mappings=[{"attribute_id": "id", "source_column": "device_id"}])
    db.commit()
    assert db.query(QualityRule).filter_by(asset_id="asset", kind="null_ratio_max", column_name="temp").count() == 1
    service.update(second.id, status="needs_review")
    db.commit()
    assert db.query(QualityRule).filter_by(asset_id="asset", kind="null_ratio_max", column_name="temp").count() == 0
    assert db.query(QualityRule).filter_by(asset_id="asset", kind="pk_uniqueness", column_name="device_id").count() == 1


def test_manual_quality_rules_and_history_survive_shared_binding_reconciliation(data_env):
    db, _ = data_env
    quality = QualityRuleService(db)
    # Extra metadata on a row-count rule cannot make it a transformed-value
    # rule: evaluation only uses binding references for null_ratio_max.
    row_count = quality.create_rule(asset_id="asset", name="Manual row minimum", kind="row_count_min",
        params={"min": 2, "binding_attribute_id": "temperature"}, severity="warning", description="Manual contract", commit=False)
    required = quality.create_rule(asset_id="asset", name="Manual temperature threshold", kind="null_ratio_max",
        column_name="temp", params={"max": 0.25}, severity="failure", description="Manual contract", commit=False)
    required.enabled = False
    db.add(HealthStatus(id="manual-health", rule_id=row_count.id, asset_id="asset", status="healthy", value_numeric=2))
    db.add(EntityAttribute(id="foreign-temp", entity_id="foreign", name="temperature", type="number", required=True))
    db.commit()
    original_rules = {r.id: (r.name, dict(r.params), r.severity, r.enabled, r.description, r.created_at)
                      for r in (row_count, required)}
    first = bind(db)
    service = ObjectBindingService(db)
    second = service.create(object_type_id="foreign", asset_id="asset", id_column="device_id", field_mappings=[
        {"attribute_id": "foreign-id", "source_column": "device_id"}, {"attribute_id": "foreign-temp", "source_column": "temp"}])
    db.commit()
    service.update(first.id, field_mappings=[{"attribute_id": "id", "source_column": "device_id"}])
    db.commit()
    service.delete(first.id)
    db.commit()
    service.update(second.id, status="needs_review")
    db.commit()
    service.delete(second.id)
    db.commit()
    remaining = db.query(QualityRule).all()
    assert {r.id: (r.name, r.params, r.severity, r.enabled, r.description, r.created_at) for r in remaining} == original_rules
    assert db.query(HealthStatus).filter_by(id="manual-health", rule_id=row_count.id).count() == 1


def test_document_keep_handles_legacy_primary_key_and_complete_enrichment(data_env, tmp_path, monkeypatch):
    db, _, _, asset = enrichment_fixture(data_env, tmp_path, monkeypatch)
    ObjectBindingService(db).create(object_type_id="device", asset_id=asset.id, role="enrichment",
        primary_source_column="device_id", enrichment_source_column="serial",
        field_mappings=[{"attribute_id": "owner", "source_column": "owner"}])
    db.commit()
    assert not (db.get(OntologyEntity, "device").config_json or {}).get("primary_key")
    client = source_client(db)
    mapping = {"entities": [{"name": "Device", "asset_id": "asset", "table": "devices", "primaryKey": "id",
        "properties": [{"name": "id", "field": "device_id", "required": True},
                       {"name": "owner", "field": "private"}]}]}
    applied = client.post("/doc-builder/mapping/apply", json={"session_id": "legacy-keep", "ontology_id": "a", "mapping_result": mapping,
        "items": [{"entity_id": "device", "entity_name": "Device", "asset_id": "asset", "conflict_action": "keep"}]})
    assert applied.status_code == 200, applied.text
    item = applied.json()["items"][0]
    assert item["primary_key"] == "id" and item["backing_asset_ids"] == ["asset", asset.id]
    assert {f["attribute_name"]: f["source_asset_id"] for f in item["field_mappings"]}["owner"] == asset.id
    request = effective_draft(item, "a", "legacy-keep")
    for _ in range(2):
        response = client.post("/builder/finalize", json=request)
        assert response.status_code == 200, response.text
    assert client.post("/ontology-publish/quick-publish", json={"ontology_id": "a"}).status_code == 200
    query = client.get("/ontology-api/objects/device/d1", params={"ontology_id": "a"})
    assert query.status_code == 200 and query.json()["owner"] == "Team A"


@pytest.mark.parametrize("identity_fault", ["missing", "unmapped", "ambiguous"])
def test_publish_rejects_unusable_instance_identity_and_rolls_back(environment, identity_fault):
    client, sessions = environment
    entity_id = client.post("/builder/finalize", json=draft("oa")).json()["entity_ids"]["Device"]
    with sessions() as db:
        binding = db.query(ObjectBinding).filter_by(object_type_id=entity_id).one()
        if identity_fault == "missing":
            binding.id_column = None
        elif identity_fault == "unmapped":
            binding.field_mappings = [m for m in binding.field_mappings if m["source_column"] != "device_id"]
        else:
            binding.field_mappings = [{**m, "source_column": "device_id"} for m in binding.field_mappings]
        db.commit()
    result = client.post("/ontology-publish/quick-publish", json={"ontology_id": "oa"})
    assert result.status_code == 400, result.text
    assert "唯一实例 ID" in result.text
    with sessions() as db:
        assert db.query(OntologyVersion).count() == 0


def test_relations_pages_recover_all_instances_and_bound_multi_hop(data_env):
    db, source = data_env
    with sqlite3.connect(source) as raw:
        raw.executemany("INSERT INTO devices VALUES (?,?,?,?)", [(f"p{i:03}", i, 0, "secret") for i in range(1,206)])
    client = source_client(db)
    props = [{"name": "id", "required": True, "source_asset_id": "asset", "source_column": "device_id"},
             {"name": "group", "source_asset_id": "asset", "source_column": "private"}]
    saved = client.post("/builder/finalize", json={"ontology_id": "a", "objects": [
        {"name": name, "primaryKey": "id", "backing_asset_ids": ["asset"], "properties": props} for name in ("Device", "Peer")],
        "relations": [{"name": "same_group", "source": "Device", "target": "Peer", "sourceField": "group", "targetField": "group"}]})
    assert saved.status_code == 200, saved.text
    published = client.post("/ontology-publish/quick-publish", json={"ontology_id": "a"})
    assert published.status_code == 200, published.text
    url = f'/ontology-api/objects/{saved.json()["entity_ids"]["Device"]}/d1/relations?depth=1&limit=100'
    collected = []
    pages = 0
    while url:
        response = client.get(url)
        assert response.status_code == 200, response.text
        rows = response.json()
        assert isinstance(rows, list) and len(rows) == 1
        page = rows[0]
        collected += [r["id"] for r in page["instances"]]
        url = page["pagination"]["next"]
        if url:
            assert parse_qs(urlsplit(url).query)["version_id"] == [published.json()["version_id"]]
            assert page["traversal"]["truncated"] and "pagination" in page["traversal"]["reasons"]
        pages += 1
    assert len(collected) == len(set(collected)) == 206 and pages == 3
    limited = client.get(f'/ontology-api/objects/{saved.json()["entity_ids"]["Device"]}/d1/relations', params={"depth": 3, "limit": 100, "max_nodes": 2})
    assert limited.status_code == 200, limited.text
    traversal = limited.json()[0]["traversal"]
    assert traversal["visited_nodes"] <= 2 and traversal["truncated"] and "node_limit" in traversal["reasons"]
    assert traversal["continuations"]
    assert client.get(urlsplit(limited.json()[0]["pagination"]["next"]).path + "?" + urlsplit(limited.json()[0]["pagination"]["next"]).query).status_code == 200


def test_relations_use_real_identity_when_business_id_is_another_attribute(data_env):
    db, source = data_env
    with sqlite3.connect(source) as raw:
        raw.executemany("INSERT INTO devices VALUES (?,?,?,?)", [(f"p{i}", i, 0, "secret") for i in range(1,5)])
    client = source_client(db)
    # Both sides have a business property named id; it is deliberately neither
    # unique nor the configured primary key. Preserve it in instance payloads.
    props = [{"name": "serial", "required": True, "source_asset_id": "asset", "source_column": "device_id"},
             {"name": "id", "source_asset_id": "asset", "source_column": "private"}]
    saved = client.post("/builder/finalize", json={"ontology_id": "a", "objects": [
        {"name": name, "primaryKey": "serial", "backing_asset_ids": ["asset"], "properties": props} for name in ("Device", "Peer")],
        "relations": [{"name": "same_business_id", "source": "Device", "target": "Peer", "sourceField": "id", "targetField": "id"}]})
    assert saved.status_code == 200, saved.text
    published = client.post("/ontology-publish/quick-publish", json={"ontology_id": "a"})
    assert published.status_code == 200, published.text
    response = client.get("/ontology-api/objects/device/d1", params={"ontology_id": "a"})
    assert response.status_code == 200 and response.json() == {"serial": "d1", "id": "secret"}
    query = client.post("/ontology-api/query", json={"ontology_id": "a", "entity_name": "Device"})
    assert query.json()["entity"]["id_property"] == "serial"
    groups = client.get("/ontology-api/endpoints", params={"ontology_id": "a"}).json()["groups"]
    assert all(group["id_property"] == "serial" for group in groups)
    first = client.get("/ontology-api/objects/device/d1/relations", params={"ontology_id": "a", "limit": 2, "depth": 2, "max_nodes": 2})
    assert first.status_code == 200, first.text
    page = first.json()[0]
    assert page["source_record_id"] == "d1"
    assert {r["id"] for r in page["instances"]} == {"secret"}
    assert len(first.json()) == 2  # distinct canonical IDs really expand a hop
    next_page = client.get(page["pagination"]["next"])
    assert next_page.status_code == 200, next_page.text
    assert {r["serial"] for r in page["instances"]}.isdisjoint({r["serial"] for r in next_page.json()[0]["instances"]})
    for url in page["traversal"]["continuations"]:
        assert client.get(url).status_code == 200
