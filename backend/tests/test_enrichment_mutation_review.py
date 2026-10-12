"""Mapped enrichment writes select the explicit source; no partial cross-source DML."""
import sqlite3
from types import SimpleNamespace
import pytest
from test_data_plane_integrity_review import data_env  # noqa: F401
from test_enrichment_review import enrichment_fixture
from app.models.entity import EntityAttribute
from app.models.connection import Connection
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.object_mutation_service import ObjectMutationService
from app.services.version_component_snapshot import capture_binding


def test_real_enrichment_update_uses_explicit_join_fixed_snapshot_and_independent_source(data_env,tmp_path,monkeypatch):
    db, primary, other, asset=enrichment_fixture(data_env,tmp_path,monkeypatch)
    binding=ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',field_mappings=[{'attribute_id':'owner','source_column':'owner'}])
    db.commit()
    # Read-only primary is sufficient when the actual mutated asset is writable.
    db.get(Connection,db.get(__import__('app.models.asset',fromlist=['Asset']).Asset,'asset').connection_id).writable=False;db.commit()
    result=ObjectMutationService(db).update('device','d1',{'owner':'Team B'})
    assert result['outcome']=='committed' and result['instance']['owner']=='Team B'
    with sqlite3.connect(other) as raw:assert raw.execute("SELECT owner FROM owners WHERE serial='d1'").fetchone()[0]=='Team B'
    with sqlite3.connect(primary) as raw:assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0]==90
    snapshot=capture_binding(db,'device')
    version=SimpleNamespace(source_entity_id='device',binding_snapshot=snapshot,attributes=[SimpleNamespace(
        source_attribute_id=a.id,name=a.name,type=a.type,required=a.required,constraints_json=a.constraints_json)
        for a in db.query(EntityAttribute).filter_by(entity_id='device').all()])
    ObjectBindingService(db).update(binding.id,field_mappings=[{'attribute_id':'owner','source_column':'record_id'}]);db.commit()
    assert ObjectMutationService(db,version).update('device','d1',{'owner':'Historical team'})['instance']['owner']=='Historical team'
    with sqlite3.connect(other) as raw:assert raw.execute("SELECT record_id,owner FROM owners WHERE serial='d1'").fetchone()==('o1','Historical team')


def test_missing_enrichment_instance_duplicate_and_cross_source_write_have_no_side_effect(data_env,tmp_path,monkeypatch):
    db, primary, other, asset=enrichment_fixture(data_env,tmp_path,monkeypatch)
    ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',field_mappings=[{'attribute_id':'owner','source_column':'owner'}]);db.commit()
    service=ObjectMutationService(db)
    with pytest.raises(ValueError,match='不存在'):service.update('device','d2',{'owner':'Missing'})
    with pytest.raises(ValueError,match='跨数据源'):service.update('device','d1',{'owner':'Partial','temperature':999})
    with sqlite3.connect(other) as raw:raw.execute("INSERT INTO owners VALUES ('o2','d1','Duplicate')")
    with pytest.raises((ValueError,RuntimeError),match='重复匹配'):service.update('device','d1',{'owner':'Wrong'})
    with sqlite3.connect(primary) as raw:assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0]==90
    with sqlite3.connect(other) as raw:assert raw.execute("SELECT owner FROM owners WHERE record_id='o1'").fetchone()[0]=='Team A'
