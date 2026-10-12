"""Explicit one-to-one source joins use real SQLite connectors and published mappings."""
import sqlite3
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from app.models.connection import Connection
from app.models.asset import Asset
from app.models.entity import EntityAttribute
from app.models.object_binding import ObjectBinding
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.connection_service import ConnectionService
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.data_plane.execute_service import ExecuteService


def enrichment_fixture(data_env, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'LOCAL_DATA_ROOT', str(tmp_path))
    db, source = data_env
    primary_connection = db.get(Connection,db.get(Asset,'asset').connection_id)
    primary_connection.type = 'sqlite'
    db.add(EntityAttribute(id='owner',entity_id='device',name='owner',type='string'))
    db.commit()
    bind(db)
    other_source = tmp_path/'enrichment.sqlite'
    with sqlite3.connect(other_source) as raw:
        raw.execute('CREATE TABLE owners (record_id TEXT PRIMARY KEY, serial TEXT, owner TEXT)')
        raw.execute("INSERT INTO owners VALUES ('o1','d1','Team A')")
    connection = ConnectionService(db).create(name='other-source',type='sqlite',category='database',
        database=str(other_source),writable=True,rate_limit_qps=10000)
    asset = AssetService(db).register(name='owners',kind='table',locator={'table':'owners'},connection_id=connection.id)
    return db, source, other_source, asset


def test_enrichment_explicit_one_to_one_left_query_cross_connection_and_duplicates(data_env,tmp_path,monkeypatch):
    db, source, other_source, asset = enrichment_fixture(data_env,tmp_path,monkeypatch)
    service = ObjectBindingService(db)
    pending = service.create(object_type_id='device',asset_id=asset.id,role='enrichment',
        field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    assert pending.status == 'needs_review' and pending.primary_source_column is None
    assert '尚未审核' in EntityDataService(db).query_entity_data('device')['error']
    assert EntityDataService(db).query_entity_data('device',fields=['id'])['rows'] == [['d1'],['d2']]
    service.update(pending.id,primary_source_column='device_id',enrichment_source_column='serial')
    db.commit()
    assert pending.status == 'active' and pending.review_reason is None
    data = EntityDataService(db).query_entity_data('device')
    assert data['columns'] == ['id','temperature','owner']
    assert data['rows'] == [['d1',90.0,'Team A'],['d2',20.0,None]]
    with sqlite3.connect(other_source) as raw:
        raw.execute("INSERT INTO owners VALUES ('o2','d1','Duplicate')")
    ExecuteService.invalidate_cache_for_asset(asset.id)
    result = EntityDataService(db).query_entity_data('device')
    assert '重复匹配' in result['error'] and 'rows' not in result
    assert EntityDataService(db).query_entity_data('device',fields=['temperature'])['rows'] == [[90.0],[20.0]]
    with sqlite3.connect(other_source) as raw:
        raw.execute("DELETE FROM owners WHERE record_id='o2'")
    ExecuteService.invalidate_cache_for_asset(asset.id)
    assert EntityDataService(db).query_entity_data('device')['rows'][0][-1] == 'Team A'
    with pytest.raises(ValueError,match='primary_source_column'):
        service.update(pending.id,primary_source_column='missing')
    service.delete(db.query(ObjectBinding).filter_by(role='primary').one().id)
    db.commit()
    assert pending.status == 'needs_review'


def test_enrichment_filter_is_applied_before_pagination_and_version_is_immutable(data_env,tmp_path,monkeypatch):
    from app.services.version_component_snapshot import capture_binding
    from app.services.version_entity_data import VersionEntityDataService
    db, source, other_source, asset = enrichment_fixture(data_env,tmp_path,monkeypatch)
    service = ObjectBindingService(db)
    binding = service.create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',
        field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    with sqlite3.connect(source) as raw:
        raw.executemany('INSERT INTO devices VALUES (?,?,?,?)',[(f'z{i:03}',i,0,'x') for i in range(3,206)])
    with sqlite3.connect(other_source) as raw:
        raw.execute("INSERT INTO owners VALUES ('o205','z205','Team A')")
    ExecuteService.invalidate_cache_for_asset('asset')
    query = EntityDataService(db).query_entity_data('device',fields=['id','owner'],filters={'owner':'Team A'},limit=1,offset=1)
    assert query['rows'] == [['z205','Team A']]
    snapshot = capture_binding(db,'device')
    version = SimpleNamespace(binding_snapshot=snapshot,
        attributes=[SimpleNamespace(source_attribute_id=a.id,name=a.name,source_field=a.source_field)
            for a in db.query(EntityAttribute).filter_by(entity_id='device').all()])
    frozen = VersionEntityDataService(db,version)
    ObjectBindingService(db).update(binding.id,field_mappings=[{'attribute_id':'owner','source_column':'record_id'}])
    db.commit()
    assert EntityDataService(db).query_entity_data('device',fields=['owner'],limit=1)['rows'] == [['o1']]
    assert frozen.query_entity_data('device',fields=['owner'],limit=1)['rows'] == [['Team A']]
    ObjectBindingService(db).delete(binding.id)
    db.commit()
    assert frozen.query_entity_data('device',fields=['owner'],limit=1)['rows'] == [['Team A']]
    AssetService(db).deprecate(asset.id)
    assert '失效' in frozen.query_entity_data('device')['error']


def test_legacy_enrichment_upgrade_requires_explicit_rules(tmp_path):
    from app.migrations.binding_integrity import migrate_binding_integrity
    engine = create_engine(f"sqlite:///{tmp_path/'legacy-enrichment.sqlite'}")
    with engine.begin() as raw:
        raw.execute(text('CREATE TABLE object_bindings (id TEXT PRIMARY KEY, object_type_id TEXT, asset_id TEXT, role TEXT,status TEXT, review_reason TEXT,field_mappings TEXT)'))
        raw.execute(text('CREATE TABLE entity_attributes (id TEXT,entity_id TEXT,source_table TEXT,source_field TEXT,data_status TEXT)'))
        raw.execute(text("INSERT INTO object_bindings VALUES ('e','device','owners','enrichment','active',NULL,:mapping)"),
            {'mapping':'[{"attribute_id":"owner","source_column":"owner"}]'})
        raw.execute(text("INSERT INTO entity_attributes VALUES ('owner','device','owners','owner','已确认')"))
    migrate_binding_integrity(engine)
    migrate_binding_integrity(engine)
    with engine.begin() as raw:
        result = raw.execute(text('SELECT status,primary_source_column,enrichment_source_column FROM object_bindings')).one()
        assert result == ('needs_review',None,None)
        assert raw.execute(text('SELECT source_table,source_field FROM entity_attributes')).one() == (None,None)
    engine.dispose()


def test_enrichment_join_schema_drift_and_explicit_review_recovers(data_env,tmp_path,monkeypatch):
    db, source, other_source, asset = enrichment_fixture(data_env,tmp_path,monkeypatch)
    binding = ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',
        field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    with sqlite3.connect(other_source) as raw:
        raw.execute('ALTER TABLE owners RENAME COLUMN serial TO device_serial')
    AssetService(db).sync_schema(asset.id)
    assert binding.status == 'needs_review' and db.get(EntityAttribute,'owner').source_field is None
    assert '尚未审核' in EntityDataService(db).query_entity_data('device')['error']
    ObjectBindingService(db).update(binding.id,enrichment_source_column='device_serial',status='active',review_reason=None)
    db.commit()
    assert EntityDataService(db).query_entity_data('device')['rows'][0][-1] == 'Team A'
    with sqlite3.connect(source) as raw:
        raw.execute('ALTER TABLE devices RENAME COLUMN device_id TO device_serial')
    AssetService(db).sync_schema('asset')
    assert binding.status == 'needs_review'


def test_enrichment_requires_review_before_real_publish_and_release_queries_sources(data_env,tmp_path,monkeypatch):
    from fastapi import HTTPException
    from app.api.v1 import ontology_publish
    from app.models.user import User
    from app.models.version import OntologyVersionEntity
    from app.services.version_entity_data import VersionEntityDataService
    db, source, other_source, asset = enrichment_fixture(data_env,tmp_path,monkeypatch)
    binding = ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    user = User(id='admin',username='a',password_hash='x',name='a',role='admin',is_active=True)
    with pytest.raises(HTTPException) as failure:
        ontology_publish.quick_publish(ontology_publish.QuickPublishRequest(ontology_id='a'),db=db,user=user)
    assert failure.value.status_code == 400
    ObjectBindingService(db).update(binding.id,primary_source_column='device_id',enrichment_source_column='serial')
    db.commit()
    release = ontology_publish.quick_publish(ontology_publish.QuickPublishRequest(ontology_id='a'),db=db,user=user)
    version = db.query(OntologyVersionEntity).filter_by(version_id=release['version_id'],source_entity_id='device').one()
    assert version.binding_snapshot['enrichments'][0]['primary_source_column'] == 'device_id'
    assert VersionEntityDataService(db,version).query_entity_data('device')['rows'] == [['d1',90.0,'Team A'],['d2',20.0,None]]


def test_enrichment_joins_original_keys_then_redacts_public_projection(data_env,tmp_path,monkeypatch):
    db, source, other_source, asset = enrichment_fixture(data_env,tmp_path,monkeypatch)
    primary = db.get(Asset,'asset')
    primary.sensitivity_tags = {'device_id':'pii'}
    asset.sensitivity_tags = {'serial':'pii','owner':'sensitive'}
    ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',
        field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    result = EntityDataService(db).query_entity_data('device')
    assert result['rows'] == [['**',90.0,'***'],['**',20.0,None]]
