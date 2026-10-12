"""Regression evidence using real repositories, transactions and a local source DB.

Only the external MySQL driver is replaced with SQLite; no execution result is mocked.
"""
import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.connectors import ConnectorRegistry
from app.database import Base
from app.models.asset import Asset
from app.models.connection import Connection
from app.models.entity import EntityAttribute, OntologyEntity
from app.models.lineage_edge import LineageEdge
from app.models.quality_rule import QualityRule
from app.models.scenario import ScenarioDict
from app.models.system_config import SystemConfig
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.event_bus import get_event_bus
from app.services.data_plane.execute_service import ExecuteBlocked, ExecuteRequest, ExecuteService, ExecutePersistenceError
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.data_plane.quality_rule_service import QualityRuleService


@pytest.fixture
def data_env(tmp_path, monkeypatch):
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as raw:
        raw.execute("CREATE TABLE devices (device_id TEXT PRIMARY KEY, temp REAL, spare REAL, private TEXT)")
        raw.executemany("INSERT INTO devices VALUES (?,?,?,?)", [("d1", 90, 30, "secret"), ("d2", 20, 40, "secret2")])
    class SQLiteDriver:
        def connect(self, **kwargs):
            return sqlite3.connect(source, check_same_thread=False)
        def quote_identifier(self):
            return '"'
        def execute_sql_with_params(self, raw, sql, params):
            cur = raw.execute(sql, params)
            return {"columns": [d[0] for d in cur.description] if cur.description else [],
                    "rows": [list(r) for r in cur.fetchall()] if cur.description else [], "rowsAffected": cur.rowcount}
        def get_table_schema(self, raw, table_name, database):
            return [{"name": r[1], "type": r[2], "nullable": not r[3], "is_pk": bool(r[5])}
                    for r in raw.execute(f'PRAGMA table_info("{table_name}")')]
    monkeypatch.setitem(ConnectorRegistry._by_type, "mysql", SQLiteDriver)
    engine = create_engine(f"sqlite:///{tmp_path / 'metadata.sqlite'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.add_all([ScenarioDict(id="a", code="a", name="A"), ScenarioDict(id="b", code="b", name="B")])
    db.flush()
    db.add_all([OntologyEntity(id="device", name="Device", name_cn="设备", tier=1, ontology_id="a"),
                OntologyEntity(id="foreign", name="Device", name_cn="设备", tier=1, ontology_id="b")])
    db.flush()
    db.add_all([EntityAttribute(id="id", entity_id="device", name="id", type="string", required=True),
                EntityAttribute(id="temperature", entity_id="device", name="temperature", type="number", required=True),
                EntityAttribute(id="foreign-id", entity_id="foreign", name="id", type="string")])
    db.add(Connection(id=f"conn-{tmp_path.name}", name="isolated", type="mysql", category="database",
                      database=str(source), enabled=True, writable=True, rate_limit_qps=10000))
    db.flush()
    db.add(Asset(id="asset", name="devices", kind="table", status="active", connection_id=f"conn-{tmp_path.name}",
        locator={"table": "devices"}, primary_key=["device_id"], cache_ttl_seconds=60,
        schema_snapshot=[{"name": n, "type": t} for n, t in [("device_id", "TEXT"), ("temp", "REAL"), ("spare", "REAL"), ("private", "TEXT")]]))
    db.commit()
    yield db, source
    db.close()
    engine.dispose()


def bind(db):
    return ObjectBindingService(db).create(object_type_id="device", asset_id="asset", id_column="device_id",
        field_mappings=[{"attribute_id": "id", "source_column": "device_id"},
                        {"attribute_id": "temperature", "source_column": "temp"}])


def test_binding_transaction_mapping_quality_lineage_and_isolation(data_env):
    db, _ = data_env
    bus, seen = get_event_bus(), []
    bus.subscribe("binding.created", seen.append)
    b = bind(db)
    assert seen == []
    assert db.query(LineageEdge).filter_by(target_id="device", weight=1).count() == 1
    assert {(r.kind, r.column_name) for r in db.query(QualityRule).all()} == {
        ("row_count_min", None), ("pk_uniqueness", "device_id"), ("null_ratio_max", "device_id"), ("null_ratio_max", "temp")}
    db.rollback()
    assert seen == [] and db.query(QualityRule).count() == 0 and db.query(LineageEdge).count() == 0
    b = bind(db)
    db.commit()
    assert len(seen) == 1
    assert EntityDataService(db).query_entity_data("device", offset=1) == {
        "columns": ["id", "temperature"], "rows": [["d2", 20.0]], "rowCount": 1}
    assert "error" in EntityDataService(db).query_entity_data("device", fields=["private"])
    with pytest.raises(ValueError, match="不属于"):
        ObjectBindingService(db).update(b.id, field_mappings=[{"attribute_id": "foreign-id", "source_column": "temp"}])
    ObjectBindingService(db).update(b.id, field_mappings=[{"attribute_id": "id", "source_column": "device_id"}])
    db.commit()
    assert db.get(EntityAttribute, "temperature").source_field is None
    assert db.get(EntityAttribute, "foreign-id").source_field is None
    assert all(s.status == "healthy" for s in QualityRuleService(db).evaluate_asset("asset"))
    ObjectBindingService(db).delete(b.id)
    db.commit()
    assert db.query(QualityRule).count() == 0
    assert db.query(LineageEdge).one().weight == 0


def test_source_write_commits_invalidates_cache_and_disabled_connection_blocks(data_env, monkeypatch):
    db, source = data_env
    bind(db)
    db.commit()
    service = EntityDataService(db)
    assert service.query_entity_data("device", filters={"id": "d1"})["rows"] == [["d1", 90.0]]
    monkeypatch.setattr(ExecuteService, "ALLOWED_WRITE_PURPOSES", {"action.write"})
    result = ExecuteService(db).execute(ExecuteRequest(asset_id="asset", sql="UPDATE <asset> SET temp=:v WHERE device_id=:id",
        params={"v": 15, "id": "d1"}, purpose="action.write"))
    assert result.rows_affected == 1
    with sqlite3.connect(source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0] == 15
    assert service.query_entity_data("device", filters={"id": "d1"})["rows"] == [["d1", 15.0]]
    conn = db.get(Connection, db.get(Asset, "asset").connection_id)
    conn.enabled = False
    db.commit()
    with pytest.raises(ExecuteBlocked, match="connection_disabled"):
        ExecuteService(db).execute(ExecuteRequest(asset_id="asset", sql="SELECT * FROM <asset>", purpose="probe.test"))


def test_schema_drift_invalidates_binding_then_explicit_mapping_review_recovers(data_env):
    db, source = data_env
    b = bind(db)
    db.commit()
    with sqlite3.connect(source) as raw:
        raw.execute("ALTER TABLE devices RENAME COLUMN temp TO temperature_new")
    AssetService(db).sync_schema("asset")
    db.refresh(b)
    assert b.status == "needs_review" and db.get(EntityAttribute, "temperature").source_field is None
    assert "error" in EntityDataService(db).query_entity_data("device")
    ObjectBindingService(db).update(b.id, status="active", review_reason=None,
        field_mappings=[{"attribute_id": "id", "source_column": "device_id"},
                        {"attribute_id": "temperature", "source_column": "temperature_new"}])
    db.commit()
    assert EntityDataService(db).query_entity_data("device", filters={"id": "d1"})["rows"] == [["d1", 90.0]]


def test_saved_storage_policy_is_effective_and_text_is_readable(data_env, tmp_path):
    db, _ = data_env
    db.add_all([SystemConfig(group="storage", key="local_path", value=str(tmp_path / "uploads")),
                SystemConfig(group="storage", key="allowed_types", value=".txt"),
                SystemConfig(group="storage", key="max_upload_mb", value="1")])
    db.commit()
    service = AssetService(db)
    with pytest.raises(ValueError, match="文件类型"):
        service.register_document_file(file_bytes=b"x", filename="bad.exe")
    with pytest.raises(ValueError, match="限制"):
        service.register_document_file(file_bytes=b"x" * (1024 * 1024 + 1), filename="huge.txt")
    asset = service.register_document_file(file_bytes="设备手册".encode(), filename="../../manual.txt")
    from pathlib import Path
    assert Path(asset.locator["file_path"]).parent == tmp_path / "uploads"
    assert asset.parsed_summary == "设备手册"


def test_invalid_documents_and_missing_tables_do_not_register_success(data_env, tmp_path):
    db, _ = data_env
    db.add_all([SystemConfig(group="storage", key="local_path", value=str(tmp_path / "uploads")),
                SystemConfig(group="storage", key="allowed_types", value=".pdf")])
    db.commit()
    service = AssetService(db)
    with pytest.raises(ValueError, match="文档解析失败"):
        service.register_document_file(file_bytes=b"corrupt", filename="bad.pdf")
    assert not (tmp_path / "uploads").exists()
    assert db.query(Asset).filter_by(name="bad.pdf").count() == 0
    with pytest.raises(ValueError, match="源表不存在"):
        service.register(name="bad table", kind="table", locator={"table": "absent"},
            connection_id=db.get(Asset, "asset").connection_id)
    assert db.query(Asset).filter_by(name="bad table").count() == 0


def test_binding_sample_uses_actual_mapping_filter_and_active_state(data_env):
    from app.api.v1.data_plane.object_bindings import test_resolve as resolve
    from fastapi import HTTPException
    db, _ = data_env
    b = bind(db)
    ObjectBindingService(db).update(b.id, filter_expr="temp > 80")
    db.commit()
    sample = resolve(b.id, db=db)
    assert sample["columns"] == ["id", "temperature"]
    assert sample["rows"] == [["d1", 90.0]]
    ObjectBindingService(db).update(b.id, status="needs_review")
    db.commit()
    with pytest.raises(HTTPException) as error:
        resolve(b.id, db=db)
    assert error.value.status_code == 400


def test_mapping_confirmation_commits_and_rule_edits_invalidate_old_health(data_env):
    from app.api.v1.data_plane.mapping import apply, ApplyRequest
    from app.models.user import User
    db, _ = data_env
    result = apply(ApplyRequest(object_type_id="device", asset_id="asset", id_column="device_id",
        field_mappings=[{"attribute_id": "id", "source_column": "device_id"}]), db=db,
        user=User(id="editor", username="e", password_hash="x", name="E", role="editor"))
    with sessionmaker(bind=db.get_bind())() as fresh:
        from app.models.object_binding import ObjectBinding
        assert fresh.get(ObjectBinding, result["binding_id"]).id_column == "device_id"
    svc = QualityRuleService(db)
    rule = next(r for r in svc.list_rules("asset") if r.kind == "row_count_min")
    assert svc.evaluate(rule.id).status == "healthy"
    svc.update_rule(rule.id, params={"min": 100})
    assert svc.latest_status(rule.id).status == "unknown"
    assert svc.evaluate(rule.id).status == "failure"


def test_committed_source_write_with_record_failure_is_explicit(data_env, monkeypatch):
    db, source = data_env
    service = ExecuteService(db)
    def fail(log):
        raise ExecutePersistenceError("metadata unavailable")
    monkeypatch.setattr(service, "_save_log", fail)
    with pytest.raises(ExecutePersistenceError) as caught:
        service.execute_on_connection(connection_id=db.get(Asset, "asset").connection_id,
            sql="UPDATE devices SET temp=:v WHERE device_id=:id", params={"v": 14, "id": "d1"},
            purpose="action.review", write=True)
    assert caught.value.outcome == "committed_unrecorded" and caught.value.observed_result["rows_affected"] == 1
    with sqlite3.connect(source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0] == 14


def test_credentials_are_readable_after_restart_and_bad_keys_fail(monkeypatch):
    from app.config import settings
    from app.services.data_plane import credential_vault as vault
    from cryptography.fernet import Fernet
    monkeypatch.setattr(vault, "_vault_singleton", None)
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "")
    ref = vault.get_vault().store({"password": "isolated-only"})
    vault._vault_singleton = None
    assert vault.get_vault().fetch(ref) == {"password": "isolated-only"}
    with pytest.raises(ValueError, match="解密失败"):
        vault.FernetVault(Fernet.generate_key().decode()).fetch(ref)


def test_resolution_uses_binding_identity_and_real_cell_completeness(data_env):
    from app.api.v1.resolution import get_resolution_stats, preview_source_data, list_resolvable_entities
    from fastapi import HTTPException
    db, source = data_env
    db.add(Asset(id="other-source", name="foreign devices", kind="table", status="active",
        connection_id=db.get(Asset, "asset").connection_id, locator={"table": "devices"},
        schema_snapshot=db.get(Asset, "asset").schema_snapshot))
    ObjectBindingService(db).create(object_type_id="foreign", asset_id="other-source", id_column="device_id",
        field_mappings=[{"attribute_id": "foreign-id", "source_column": "device_id"}])
    bind(db)
    db.commit()
    with sqlite3.connect(source) as raw:
        raw.execute("UPDATE devices SET temp=NULL WHERE device_id='d2'")
    stats = get_resolution_stats("device", identifier_field="id", asset_id=None, db=db)
    assert stats.asset_id == "asset" and stats.total_rows == 2 and stats.completeness == .75
    assert stats.distinct_identifier_rows == 2 and stats.null_identifier_rows == 0
    preview = preview_source_data("foreign", table_name=None, asset_id=None, page=1, page_size=5, db=db)
    assert preview.asset_id == "other-source" and preview.columns == ["device_id"]
    assert [r.ontology_id for r in list_resolvable_entities(ontology_id="b", db=db)] == ["b"]
    with pytest.raises(HTTPException) as invalid:
        get_resolution_stats("device", identifier_field="x`);DROP TABLE devices;--", asset_id=None, db=db)
    assert invalid.value.status_code == 400


def test_sql_view_preview_and_probe_use_view_semantics(data_env):
    db, _ = data_env
    asset = AssetService(db).register(name="hot devices", kind="sql_view",
        connection_id=db.get(Asset, "asset").connection_id,
        locator={"base_asset_id": "asset", "sql": "SELECT device_id,temp FROM {{base}} WHERE temp>50"})
    assert AssetService(db).preview(asset.id)["rows"] == [["d1", 90.0]]
    from app.services.data_plane.probe_service import ProbeService
    assert ProbeService(db).run(asset.id, "row_count").value_numeric == 1


def test_freshness_queries_the_configured_source_column(data_env):
    from datetime import datetime, timedelta, timezone
    db, source = data_env
    with sqlite3.connect(source) as raw:
        raw.execute("ALTER TABLE devices ADD updated_at TEXT")
        raw.execute("UPDATE devices SET updated_at=?", (datetime.now(timezone.utc).isoformat(),))
    AssetService(db).sync_schema("asset")
    service = QualityRuleService(db)
    rule = service.create_rule(asset_id="asset", name="source freshness", kind="freshness", column_name="updated_at",
                               params={"max_age_seconds": 3600}, severity="failure")
    assert service.evaluate(rule.id).status == "healthy"
    with sqlite3.connect(source) as raw:
        raw.execute("UPDATE devices SET updated_at=?", ((datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),))
    assert service.evaluate(rule.id).status == "failure"


def test_execute_deadline_cancels_real_source_query_and_records_failure(data_env):
    from app.models.execution_log import ExecutionLog
    db, _ = data_env
    import time
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        ExecuteService(db).execute(ExecuteRequest(asset_id="asset", purpose="probe.timeout", timeout_ms=10,
            sql="WITH RECURSIVE seq(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM seq WHERE n<100000000) SELECT SUM(n) FROM seq"))
    assert time.monotonic() - start < 2
    assert db.query(ExecutionLog).one().blocked is True


def test_competing_primary_bindings_have_database_level_unique_guard(data_env):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from sqlalchemy.exc import IntegrityError
    from app.models.object_binding import ObjectBinding
    db, _ = data_env
    db.add(Asset(id="second", name="other", kind="table", status="active", locator={"table": "other"}))
    db.commit()
    factory = sessionmaker(bind=db.get_bind())
    barrier = threading.Barrier(2)
    def insert(asset):
        with factory() as session:
            session.add(ObjectBinding(object_type_id="device", asset_id=asset, role="primary", status="active"))
            barrier.wait(timeout=5)
            try:
                session.commit()
                return "saved"
            except IntegrityError:
                session.rollback()
                return "conflict"
    with ThreadPoolExecutor(2) as workers:
        futures = [workers.submit(insert, asset) for asset in ("asset", "second")]
        assert sorted(f.result() for f in futures) == ["conflict", "saved"]
    assert db.query(ObjectBinding).filter_by(status="active", role="primary").count() == 1


def test_existing_ambiguous_primary_upgrade_requires_review_and_is_idempotent(tmp_path):
    from sqlalchemy import text
    from app.migrations.binding_integrity import migrate_binding_integrity
    engine = create_engine(f"sqlite:///{tmp_path/'old-metadata.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE object_bindings (id TEXT PRIMARY KEY, object_type_id TEXT, asset_id TEXT, role TEXT, status TEXT, review_reason TEXT)"))
        conn.execute(text("CREATE TABLE entity_attributes (id TEXT PRIMARY KEY, entity_id TEXT, source_table TEXT, source_field TEXT, data_status TEXT)"))
        conn.execute(text("INSERT INTO object_bindings VALUES ('a','device','a','primary','active',NULL),('b','device','b','primary','active',NULL)"))
        conn.execute(text("INSERT INTO entity_attributes VALUES ('id','device','devices','id','已确认')"))
    migrate_binding_integrity(engine)
    migrate_binding_integrity(engine)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT status,active_primary_key FROM object_bindings")).all() == [('needs_review',None),('needs_review',None)]
        assert conn.execute(text("SELECT source_table,source_field FROM entity_attributes")).one() == (None,None)
        conn.execute(text("UPDATE object_bindings SET status='active',active_primary_key='device' WHERE id='a'"))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            conn.execute(text("UPDATE object_bindings SET status='active',active_primary_key='device' WHERE id='b'"))
    engine.dispose()


def test_object_storage_upload_and_preview_use_real_s3_wire_protocol(data_env, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs
    from xml.sax.saxutils import escape
    import threading
    db, _ = data_env
    stored, calls = {}, []
    class Protocol(BaseHTTPRequestHandler):
        def do_HEAD(self):
            calls.append(('head', self.path))
            self.send_response(200)
            self.send_header('Content-Length','0')
            self.end_headers()
        def do_PUT(self):
            calls.append(('put', self.path))
            stored[self.path] = self.rfile.read(int(self.headers['Content-Length']))
            self.send_response(200)
            self.send_header('ETag', '"isolated-upload"')
            self.send_header('Content-Length', '0')
            self.end_headers()
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in stored:
                calls.append(('get', parsed.path))
                payload = stored[parsed.path]
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            prefix = parse_qs(parsed.query).get('prefix', [''])[0]
            calls.append(('list', prefix))
            content = ''.join(f'<Contents><Key>{escape(k.split("/",2)[2])}</Key><Size>{len(v)}</Size></Contents>'
                for k,v in stored.items() if k.split('/',2)[2].startswith(prefix))
            payload = f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>isolated</Name><IsTruncated>false</IsTruncated>{content}</ListBucketResult>'.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1',0), Protocol)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        db.add_all([SystemConfig(group='storage',key='backend',value='minio'),
            SystemConfig(group='storage',key='endpoint',value=f'http://127.0.0.1:{server.server_port}'),
            SystemConfig(group='storage',key='bucket',value='isolated'),
            SystemConfig(group='storage',key='access_key',value='isolated-access'),
            SystemConfig(group='storage',key='secret_key',value='isolated-secret')])
        db.commit()
        service = AssetService(db)
        asset = service.register_document_file(filename='manual.txt',file_bytes='设备92度'.encode())
        key = asset.locator['object_key']
        assert stored[f'/isolated/{key}'] == '设备92度'.encode()
        assert 'secret_key' not in asset.locator and asset.locator['credential_ref']
        preview = service.preview(asset.id)
        assert preview['objects'][0]['key'] == key and preview['summary'] == '设备92度'
        assert service.read_document_content(asset) == '设备92度'
        connection = __import__('app.services.data_plane.connection_service', fromlist=['ConnectionService']).ConnectionService(db).create(
            name='s3-document',type='s3',category='object_storage',
            params={'endpoint':f'http://127.0.0.1:{server.server_port}','bucket':'isolated'},
            credential={'access_key':'isolated-access','secret_key':'isolated-secret'})
        from_connection = service.register(name='connection-object',kind='document',connection_id=connection.id,
            locator={'source_type':'s3','key':key})
        assert from_connection.parsed_summary == '设备92度'
        assert service.read_document_content(from_connection) == '设备92度'
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.v1.data_plane.assets import router as asset_router
        from app.database import get_db
        app = FastAPI()
        app.include_router(asset_router)
        sessions = sessionmaker(bind=db.get_bind())
        def request_db():
            with sessions() as current:
                yield current
        app.dependency_overrides[get_db] = request_db
        api_result = TestClient(app).post(f'/assets/{from_connection.id}/preview').json()
        assert api_result['objects'][0]['key'] == key and api_result['summary'] == '设备92度'
        directory = service.register(name='object-list',kind='document',connection_id=connection.id,
            locator={'source_type':'s3','prefix':''})
        with pytest.raises(ValueError,match='目录不是文档正文'):
            service.read_document_content(directory)
        assert calls[:4] == [('put',f'/isolated/{key}'),('list',key),('get',f'/isolated/{key}'),('get',f'/isolated/{key}')]
        import asyncio
        from app.services.monitor import collector
        monkeypatch.setattr(collector,'SessionLocal',sessionmaker(bind=db.get_bind()))
        assert asyncio.run(collector._check_minio())[0] == 'healthy'
        assert calls[-1] == ('head','/isolated')
    finally:
        server.shutdown()
        server.server_close()


def test_connection_document_reads_full_body_and_scheduled_refresh_recovers(data_env):
    from datetime import datetime, timedelta, timezone
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs
    import threading
    from app.services.data_plane.connection_service import ConnectionService
    from app.services.data_plane.refresh_service import DataPlaneRefresher
    db, _ = data_env
    responses = {'status':200, 'body':'设备文档开始' + ('正文'*30000) + '末尾字段'}
    calls = []
    class Protocol(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            assert parsed.path == '/device'
            assert parse_qs(parsed.query) == {'api_key':['isolated-secret']}
            calls.append(parsed.path)
            body = responses['body'].encode()
            self.send_response(responses['status'])
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self,*args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Protocol)
    worker = threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try:
        connection = ConnectionService(db).create(name='doc-api',type='rest',category='api',
            params={'base_url':f'http://127.0.0.1:{server.server_port}','auth_type':'api_key'},
            credential={'key':'api_key','value':'isolated-secret','in':'query'})
        service = AssetService(db)
        asset = service.register(name='device-doc',kind='document',connection_id=connection.id,
            locator={'source_type':'api','path':'/device','method':'GET','poll_interval':10})
        assert len(asset.parsed_summary) == 50000
        assert service.read_document_content(asset).endswith('末尾字段')
        assert 'isolated-secret' not in str(asset.locator) and 'isolated-secret' not in str(asset.profile)
        sessions = sessionmaker(bind=db.get_bind(),expire_on_commit=False)
        refresher = DataPlaneRefresher(sessions)
        now = datetime.now(timezone.utc)
        assert refresher.refresh_due(now=now)['completed'] == []
        responses['body'] = '修订后的设备文档'
        assert refresher.refresh_due(now=now+timedelta(seconds=11))['completed'] == [asset.id]
        db.expire_all()
        assert db.get(Asset,asset.id).parsed_summary == '修订后的设备文档'
        responses['status'] = 503
        assert refresher.refresh_due(now=now+timedelta(seconds=22))['failed'] == [asset.id]
        db.expire_all()
        failed = db.get(Asset,asset.id)
        assert failed.parsed_summary == '修订后的设备文档'
        assert failed.profile['source_refresh']['status'] == 'error'
        assert failed.profile['source_refresh']['error'] == '文档 API 抓取失败：HTTP 503'
        assert 'isolated-secret' not in str(failed.profile)
        assert refresher.refresh_due(now=now+timedelta(seconds=25))['completed'] == []
        responses.update(status=200,body='恢复后的文档')
        assert refresher.refresh_due(now=now+timedelta(seconds=33))['completed'] == [asset.id]
        db.expire_all()
        restored = db.get(Asset,asset.id)
        assert restored.parsed_summary == '恢复后的文档' and restored.profile['source_refresh']['status'] == 'ok'
        ConnectionService(db).update(connection.id,enabled=False)
        with pytest.raises(ValueError,match='禁用'):
            service.preview(asset.id)
        with pytest.raises(ValueError,match='poll_interval'):
            service.register(name='invalid-poll',kind='document',connection_id=connection.id,
                locator={'source_type':'api','path':'/device','poll_interval':1})
        assert len(calls) == 5
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_data_refresh_lifecycle_and_structured_schedule(data_env):
    import asyncio
    from datetime import datetime, timedelta, timezone
    from app.services.data_plane.refresh_service import DataPlaneRefresher
    db, _ = data_env
    asset = db.get(Asset,'asset')
    asset.refresh_policy = 'hourly'
    db.commit()
    sessions = sessionmaker(bind=db.get_bind(),expire_on_commit=False)
    refresher = DataPlaneRefresher(sessions,tick_seconds=0.01)
    now = datetime.now(timezone.utc)
    assert refresher.refresh_due(now=now)['completed'] == []
    assert refresher.refresh_due(now=now+timedelta(hours=1,seconds=1))['completed'] == ['asset']
    db.expire_all()
    assert db.get(Asset,'asset').profile['row_count'] == 2
    assert db.get(Asset,'asset').profile['source_refresh']['status'] == 'ok'
    await refresher.start()
    first = refresher._task
    await refresher.start()
    assert refresher._task is first
    await asyncio.sleep(0.03)
    await refresher.stop()
    assert first.done() and refresher._task is None
    await refresher.start()
    assert refresher._task is not first
    await refresher.stop()


def test_invalid_legacy_refresh_schedule_is_visible_and_does_not_write_each_tick(data_env):
    from datetime import datetime, timedelta, timezone
    from app.services.data_plane.refresh_service import DataPlaneRefresher
    db, _ = data_env
    asset = Asset(name='legacy-invalid-poll',kind='document',document_source_type='api',
                  locator={'poll_interval':1},status='active')
    db.add(asset)
    db.commit()
    sessions = sessionmaker(bind=db.get_bind(),expire_on_commit=False)
    refresher = DataPlaneRefresher(sessions)
    now = datetime.now(timezone.utc)
    assert refresher.refresh_due(now=now)['failed'] == [asset.id]
    db.expire_all()
    assert 'poll_interval' in db.get(Asset,asset.id).profile['source_refresh']['error']
    assert refresher.refresh_due(now=now+timedelta(seconds=5))['failed'] == []
    assert refresher.refresh_due(now=now+timedelta(seconds=61))['failed'] == [asset.id]


def test_sql_view_registration_captures_schema_and_invalid_sources_do_not_persist(data_env):
    db, _ = data_env
    service = AssetService(db)
    asset = service.register(name='hot-devices',kind='sql_view',connection_id=db.get(Asset,'asset').connection_id,
        locator={'base_asset_id':'asset','sql':'SELECT device_id,temp FROM {{base}} WHERE temp > 80'})
    assert [column['name'] for column in asset.schema_snapshot] == ['device_id','temp']
    ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,
        field_mappings=[{'attribute_id':'id','source_column':'device_id'},{'attribute_id':'temperature','source_column':'temp'}])
    db.commit()
    assert db.get(EntityAttribute,'id').source_table == 'hot-devices'
    assert EntityDataService(db).query_entity_data('device')['rows'] == [['d1',90.0]]
    with pytest.raises(Exception):
        service.register(name='invalid-view',kind='sql_view',connection_id=db.get(Asset,'asset').connection_id,
            locator={'base_asset_id':'asset','sql':'SELECT missing FROM {{base}}'})
    assert db.query(Asset).filter_by(name='invalid-view').count() == 0
    with pytest.raises(ValueError,match='只读'):
        service.register(name='write-view',kind='sql_view',connection_id=db.get(Asset,'asset').connection_id,
            locator={'base_asset_id':'asset','sql':'DELETE FROM {{base}}'})
    assert db.query(Asset).filter_by(name='write-view').count() == 0
