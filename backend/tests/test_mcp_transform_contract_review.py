"""MCP physical SQL and transformed object queries keep explicit value contracts."""
import asyncio

from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from test_enrichment_review import enrichment_fixture
from app.api.v1.ontology_publish import QuickPublishRequest, quick_publish
from app.models.asset import Asset
from app.models.connection import Connection
from app.models.user import User
from app.services.data_plane.object_binding_service import ObjectBindingService
from app.services.mcp_tools.data_query import ComplexSqlTool, ObjectFindTool, QueryInstancesTool
from app.services.mcp_tools.metadata import GetAttrMappingTool


def publish(db):
    user=User(id='mcp-admin',username='mcp-admin',name='MCP Admin',password_hash='x',role='admin')
    db.add(user);db.commit()
    return quick_publish(QuickPublishRequest(ontology_id='a'),db=db,user=user)['version_id']


def invoke(tool,db,**arguments):
    return asyncio.run(tool.execute({'ontology_name':'a','user_id':'mcp-admin',**arguments},db=db))


def test_complex_sql_aggregates_physical_values_and_object_find_uses_frozen_transform(data_env,tmp_path,monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,'LOCAL_DATA_ROOT',str(tmp_path))
    db,_=data_env
    db.get(Connection,db.get(Asset,'asset').connection_id).type='sqlite'
    binding=bind(db)
    mappings=[{'attribute_id':'id','source_column':'device_id'},
              {'attribute_id':'temperature','source_column':'temp','transform':'round(value / 100, 2)'}]
    ObjectBindingService(db).update(binding.id,field_mappings=mappings);db.commit()
    version_id=publish(db)
    physical=invoke(ComplexSqlTool(),db,sql='SELECT SUM(temp) AS total FROM Device')
    assert physical['items']==[{'total':110.0}]
    assert physical['value_semantics']=='physical_source' and physical['transform_applied'] is False
    raw=invoke(QueryInstancesTool(),db,object_name='Device',return_attrs=['temp'],where_sql='temp >= ?',where_params=[80],order_by='temp DESC')
    assert raw['items']==[{'temp':90.0}] and not raw['transform_applied']
    converted=invoke(ObjectFindTool(),db,object_name='Device',fields=['id','temperature'],filters={'temperature':0.2})
    assert converted['rows']==[['d2',0.2]]
    metadata=invoke(GetAttrMappingTool(),db,object_names=['Device'])[0]
    assert metadata['attribute_transforms']=={'temperature':'round(value / 100, 2)'}
    assert metadata['sql_value_semantics']=='physical_source'
    ObjectBindingService(db).update(binding.id,field_mappings=[mappings[0],{**mappings[1],'transform':'value * 2'}]);db.commit()
    old=invoke(ObjectFindTool(),db,object_name='Device',version_id=version_id,fields=['temperature'])
    assert old['rows']==[[0.9],[0.2]]
    assert invoke(GetAttrMappingTool(),db,object_names=['Device'])[0]['attribute_transforms']==metadata['attribute_transforms']


def test_mcp_object_find_allows_authorized_frozen_enrichment_attributes(data_env,tmp_path,monkeypatch):
    db,_,_,asset=enrichment_fixture(data_env,tmp_path,monkeypatch)
    ObjectBindingService(db).create(object_type_id='device',asset_id=asset.id,role='enrichment',
        primary_source_column='device_id',enrichment_source_column='serial',field_mappings=[
            {'attribute_id':'owner','source_column':'owner','transform':'"Assigned: " + value if value is not None else None'}])
    db.commit()
    version_id=publish(db)
    result=invoke(ObjectFindTool(),db,object_name='Device',version_id=version_id,
        fields=['id','owner'],filters={'owner':'Assigned: Team A'})
    assert result['columns']==['id','owner'] and result['rows']==[['d1','Assigned: Team A']]
    metadata=invoke(GetAttrMappingTool(),db,object_names=['Device'],version_id=version_id)[0]
    assert metadata['attribute_transforms']['owner']=='"Assigned: " + value if value is not None else None'


def test_query_or_is_always_scoped_by_binding_filter(data_env,tmp_path,monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'LOCAL_DATA_ROOT', str(tmp_path))
    db, _ = data_env
    db.get(Connection, db.get(Asset, 'asset').connection_id).type = 'sqlite'
    binding = bind(db)
    ObjectBindingService(db).update(binding.id, filter_expr='temp < 30')
    db.commit()
    publish(db)
    result = invoke(QueryInstancesTool(), db, object_name='Device', return_attrs=['device_id'],
                    where_sql='temp >= ? OR device_id = ?', where_params=[0, 'd1'])
    assert result['items'] == [{'device_id': 'd2'}]
    malformed = invoke(QueryInstancesTool(), db, object_name='Device', return_attrs=['device_id'],
                       where_sql='1=1) OR (1=1')
    assert 'error' in malformed
