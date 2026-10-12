"""Frozen transform definitions remain read-only and invalid legacy mappings cannot publish."""
import copy
import sqlite3
from types import SimpleNamespace

import pytest

from test_data_plane_integrity_review import data_env, bind  # noqa: F401
from app.models.entity import EntityAttribute
from app.models.object_binding import ObjectBinding
from app.services.object_mutation_service import ObjectMutationService
from app.services.version_component_snapshot import capture_binding
from app.api.v1.ontology_publish import _check_readiness_for_version_entity


def test_transformed_attributes_read_only_for_draft_and_frozen_writes(data_env):
    db,source=data_env
    binding=bind(db)
    mappings=copy.deepcopy(binding.field_mappings)
    mappings[1]['transform']='value * 2'
    binding.field_mappings=mappings;db.commit()
    attrs=db.query(EntityAttribute).filter_by(entity_id='device').all()
    version=SimpleNamespace(source_entity_id='device',binding_snapshot=capture_binding(db,'device'),
        attributes=[SimpleNamespace(source_attribute_id=attr.id,name=attr.name,type=attr.type,
            required=attr.required,constraints_json=attr.constraints_json) for attr in attrs])
    # Changing the current binding must not relax the historical write policy.
    binding.field_mappings=[{**mapping,'transform':None} for mapping in mappings];db.commit()
    with pytest.raises(ValueError,match='只读'):
        ObjectMutationService(db,version).update('device','d1',{'temperature':111})
    binding.field_mappings=mappings;db.commit()
    with pytest.raises(ValueError,match='只读'):
        ObjectMutationService(db).update('device','d1',{'temperature':111})
    with pytest.raises(ValueError,match='只读'):
        ObjectMutationService(db).create('device',{'id':'d3','temperature':111})
    with sqlite3.connect(source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()==(90,)
        assert raw.execute("SELECT count(*) FROM devices").fetchone()==(2,)


@pytest.mark.parametrize('column,expression',[('device_id','str(value)'),('temp','params["x"]'),('temp','value.__class__')])
def test_invalid_legacy_transform_is_a_publication_readiness_error(data_env,column,expression):
    db,_=data_env
    binding=bind(db);db.commit()
    snapshot=capture_binding(db,'device')
    snapshot['field_mappings'][0 if column=='device_id' else 1]['transform']=expression
    version=SimpleNamespace(binding_snapshot=snapshot,attributes=[
        SimpleNamespace(source_table='devices',source_field='device_id'),SimpleNamespace(source_table='devices',source_field='temp')])
    result=_check_readiness_for_version_entity(version)
    assert not result['ready'] and any('transform' in issue for issue in result['issues'])
