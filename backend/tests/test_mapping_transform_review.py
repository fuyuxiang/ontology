"""Mapping conversion operates on real source values, frozen bindings and gates."""
import sqlite3
from types import SimpleNamespace

import pytest

from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from app.models.entity import EntityAttribute
from app.models.quality_rule import QualityRule
from app.models.asset import Asset
from app.models.system_config import SystemConfig
from app.services.data_plane.asset_service import AssetService
from app.services.data_plane.entity_data_service import EntityDataService
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.data_plane.quality_rule_service import QualityRuleService
from app.services.data_plane.mapping_transform import apply_transform, validate_transform


def test_mapping_transform_real_query_filter_pagination_frozen_function_and_readonly(data_env):
    from app.services.version_component_snapshot import capture_binding
    from app.services.version_entity_data import VersionEntityDataService
    from app.services.function_executor import FunctionExecutor
    from app.models.function import OntologyFunction
    from app.services.object_mutation_service import ObjectMutationService
    db, source = data_env
    binding = bind(db)
    service = ObjectBindingService(db)
    mapped = [{'attribute_id':'id','source_column':'device_id'},
              {'attribute_id':'temperature','source_column':'temp','transform':'round(value / 100, 2) if value is not None else 0'}]
    service.update(binding.id,field_mappings=mapped)
    db.commit()
    query = EntityDataService(db)
    assert query.query_entity_data('device')['rows'] == [['d1',0.9],['d2',0.2]]
    assert query.query_entity_data('device',fields=['id'],filters={'temperature':0.2},limit=1)['rows'] == [['d2']]
    assert query.query_entity_data('device',fields=['temperature'],limit=1,offset=1)['rows'] == [[0.2]]
    snapshot = capture_binding(db,'device')
    version = SimpleNamespace(binding_snapshot=snapshot,source_entity_id='device',attributes=[
        SimpleNamespace(source_attribute_id=a.id,name=a.name,type=a.type,required=a.required) for a in db.query(EntityAttribute).filter_by(entity_id='device')])
    frozen = VersionEntityDataService(db,version)
    service.update(binding.id,field_mappings=[mapped[0],{**mapped[1],'transform':'value * 2'}])
    db.commit()
    assert query.query_entity_data('device')['rows'][0] == ['d1',180.0]
    assert frozen.query_entity_data('device')['rows'][0] == ['d1',0.9]
    function = OntologyFunction(name='read transformed',logic_type='python',logic_body="result = query_object('Device', {'id':'d1'})['temperature']",input_schema=[],ontology_id='a')
    result = FunctionExecutor(db).execute(function,{})
    assert result.success and result.value == 180.0,result
    with pytest.raises(ValueError,match='只读'):
        ObjectMutationService(db).update('device','d1',{'temperature':8})
    with sqlite3.connect(source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0] == 90
    service.update(binding.id,field_mappings=[mapped[0],{**mapped[1],'transform':'value / 0'}])
    db.commit()
    assert 'transform 转换失败' in query.query_entity_data('device')['error']
    with pytest.raises(ValueError,match='主键'):
        service.update(binding.id,field_mappings=[{**mapped[0],'transform':'str(value)'},mapped[1]])
    binding.field_mappings = [{**mapped[0],'transform':'str(value)'},mapped[1]]
    db.commit()
    assert '主键字段禁止' in query.query_entity_data('device')['error']
    for expression in ('__import__("os").getcwd()', 'query_object("Device", {})', 'value.__class__', 'params["x"]', 'x for x in value'):
        with pytest.raises(ValueError):
            validate_transform(expression)


def test_transform_null_semantics_and_binding_quality_use_converted_value(data_env):
    db, source = data_env
    binding = bind(db)
    assert apply_transform(None,'0 if value is None else value') == 0
    mappings = [{'attribute_id':'id','source_column':'device_id'},
                {'attribute_id':'temperature','source_column':'temp','transform':'None if value > 80 else value'}]
    ObjectBindingService(db).update(binding.id,field_mappings=mappings)
    db.commit()
    rule = db.query(QualityRule).filter_by(asset_id='asset',kind='null_ratio_max',column_name='temp').one()
    health = QualityRuleService(db).evaluate(rule.id)
    assert health.status == 'unknown' and '必填属性' in health.message
    db.get(EntityAttribute,'temperature').required = False
    db.commit()
    health = QualityRuleService(db).evaluate(rule.id)
    assert health.status == 'warning' and health.value_numeric == 0.5
    ObjectBindingService(db).update(binding.id,field_mappings=[mappings[0],{**mappings[1],'transform':'"bad numeric"'}])
    db.commit()
    assert '类型应为 number' in EntityDataService(db).query_entity_data('device')['error']


def test_unmanaged_local_file_directory_and_symlink_are_denied_including_existing_assets(data_env,tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1.data_plane import assets
    from app.database import get_db
    db, _ = data_env
    uploads = tmp_path/'allowed-uploads'
    uploads.mkdir()
    outside = tmp_path/'private'
    outside.mkdir()
    secret = outside/'private.txt'
    secret.write_text('isolated fake credential, must never be returned')
    db.add(SystemConfig(key='storage.local_path',value=str(uploads),group='storage'))
    db.commit()
    service = AssetService(db)
    with pytest.raises(ValueError,match='受管'):
        service.register(name='malicious',kind='document',locator={'source_type':'file','file_path':str(secret)})
    link = uploads/'link.txt'
    link.symlink_to(secret)
    with pytest.raises(ValueError,match='受管'):
        service.register(name='symlink',kind='document',locator={'source_type':'file','file_path':str(link)})
    with pytest.raises(ValueError,match='受管'):
        service.register_document_directory(name='private-directory',directory_path=str(outside))
    legacy = Asset(id='bad-file',name='legacy untrusted',kind='document',status='active',
                   locator={'source_type':'file','file_path':str(secret)},document_source_type='file')
    legacy_dir = Asset(id='bad-dir',name='legacy dir',kind='document',status='active',
                   locator={'source_type':'directory','directory_path':str(outside)},document_source_type='directory')
    db.add_all([legacy,legacy_dir]); db.commit()
    app = FastAPI(); app.include_router(assets.router)
    def sessions():
        yield db
    app.dependency_overrides[get_db] = sessions
    with TestClient(app) as client:
        for aid in ['bad-file','bad-dir']:
            response = client.post(f'/assets/{aid}/preview',json={})
            assert response.status_code == 400,response.text
            assert '受管' in response.text and 'isolated fake credential' not in response.text
    uploaded = service.register_document_file(file_bytes=b'actual safe upload',filename='manual.txt')
    assert service.read_document_content(uploaded) == 'actual safe upload'
