"""Regression for the current Function/Action version contract.

BusinessRule was removed by the repository migration; these tests retain the
useful snapshot/remapping assertions against real ORM sessions rather than mocks.
"""
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models import OntologyEntity, ScenarioDict
from app.models.entity import EntityAttribute
from app.models.action import EntityAction
from app.models.function import OntologyFunction
from app.models.version import OntologyVersion, OntologyVersionEntity, OntologyVersionAttribute
from app.models.version_components import OntologyVersionAction, OntologyVersionFunction
from app.services.version_component_snapshot import snapshot_components_for_version, _remap_attr_ids
from app.services.function_executor import FunctionExecutor

@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def state(db):
    scenario = ScenarioDict(code='snapshot', name='Snapshot')
    db.add(scenario); db.flush()
    entity = OntologyEntity(name='Device', name_cn='设备', tier=1, ontology_id=scenario.id)
    db.add(entity); db.flush()
    db.add(EntityAttribute(id='attr-source', entity_id=entity.id, name='value', type='number'))
    version = OntologyVersion(name='v1', version_number=1, ontology_id=scenario.id, status='published')
    db.add(version); db.flush()
    ve = OntologyVersionEntity(version_id=version.id, source_entity_id=entity.id, name=entity.name, name_cn=entity.name_cn, tier=1)
    db.add(ve); db.flush()
    va = OntologyVersionAttribute(version_entity_id=ve.id, source_attribute_id='attr-source', name='value', type='number')
    db.add(va); db.commit()
    return scenario, entity, version, ve, va


def test_models_relationships_and_defaults(db):
    _, _, version, _, _ = state(db)
    assert set(version.__mapper__.relationships.keys()) >= {'functions', 'actions', 'entities', 'relations'}
    fn = OntologyVersionFunction(version_id=version.id, source_function_id='fn', version_entity_id=version.entities[0].id, name='calc')
    db.add(fn); db.commit()
    assert (fn.logic_type, fn.logic_body, fn.callable_name) == ('expression', '', '')


def test_snapshot_function_action_remaps_attributes_without_mutating_draft(db):
    _, entity, version, ve, va = state(db)
    params = [{'name':'x','attribute_id':'attr-source','type':'number','required':True}]
    fn = OntologyFunction(entity_id=entity.id, name='calc', callable_name='calc', input_schema=params, logic_body="params['x'] * 2")
    action = EntityAction(entity_id=entity.id, name='call', action_type='call_function', parameters_json=params, type_config={'function_name':'calc'})
    db.add_all([fn, action]); db.commit()
    assert snapshot_components_for_version(db, version) == {'functions_count':1,'actions_count':1}
    db.commit()
    snap = db.query(OntologyVersionFunction).one()
    act = db.query(OntologyVersionAction).one()
    assert snap.source_function_id == fn.id and snap.version_entity_id == ve.id
    assert snap.input_schema[0]['version_attribute_id'] == va.id
    assert act.parameters_json[0]['version_attribute_id'] == va.id
    assert fn.input_schema == params and action.parameters_json == params
    assert FunctionExecutor(db).execute_snapshot(snap, {'x':3}).value == 6


def test_attribute_mapping_unknown_and_none():
    assert _remap_attr_ids(None, {}) is None
    original = [{'attribute_id':'missing'}, {'name':'plain'}]
    assert _remap_attr_ids(original, {}) == [{'version_attribute_id':None},{'name':'plain'}]
    assert original[0]['attribute_id'] == 'missing'


def test_ontology_level_functions_and_system_actions_are_scoped(db):
    own, _, version, _, _ = state(db)
    other = ScenarioDict(code='other', name='Other'); db.add(other); db.flush()
    db.add_all([OntologyFunction(name='own', ontology_id=own.id,logic_body='1'), OntologyFunction(name='foreign', ontology_id=other.id,logic_body='2'),
                EntityAction(name='own', ontology_id=own.id, category='system', action_type='notification',
                             type_config={'channel':'system','recipient':'owner','message_template':'Published'}),
                EntityAction(name='foreign', ontology_id=other.id, category='system', action_type='notification')])
    db.commit()
    assert snapshot_components_for_version(db, version) == {'functions_count':1,'actions_count':1}
    assert db.query(OntologyVersionFunction).one().name == 'own'
    assert db.query(OntologyVersionAction).one().name == 'own'


def test_workspace_snapshot_keeps_code_and_nested_version_after_file_edits(db, tmp_path):
    own, entity, version, _, _ = state(db)
    path = tmp_path/'main.py'; path.write_text("def calc(params):\n    return call_function('helper', params) + 1\n")
    workspace = OntologyFunction(name='calc', callable_name='calc', entity_id=entity.id, ontology_id=own.id, logic_type='python', source_path=str(path), func_name='calc')
    helper = OntologyFunction(name='helper', callable_name='helper', entity_id=entity.id, ontology_id=own.id, logic_type='expression', logic_body="params['x'] * 2")
    db.add_all([workspace, helper]); db.commit()
    snapshot_components_for_version(db, version); db.commit()
    frozen = db.query(OntologyVersionFunction).filter_by(callable_name='calc').one()
    path.write_text('def calc(params):\n    return 999\n')
    helper.logic_body = '999'; db.commit()
    result = FunctionExecutor(db).execute_snapshot(frozen, {'x':3})
    assert result.success and result.value == 7
    assert frozen.source_code != path.read_text()


def test_resnapshot_is_idempotent_and_approval_does_not_import_new_draft_components(db):
    own, entity, version, _, _ = state(db)
    snapshot_components_for_version(db, version); db.commit()
    db.add(OntologyFunction(name='late', entity_id=entity.id, ontology_id=own.id,logic_body='1')); db.commit()
    assert snapshot_components_for_version(db, version)['functions_count'] == 0
    assert version.components_frozen
    assert snapshot_components_for_version(db, version, replace=True)['functions_count'] == 1


def test_unreadable_workspace_blocks_publication(db):
    _, entity, version, _, _ = state(db)
    db.add(OntologyFunction(name='missing', entity_id=entity.id, logic_type='python', source_path='/missing/source.py')); db.commit()
    with pytest.raises(ValueError, match='无法发布'):
        snapshot_components_for_version(db, version)


def test_valid_syntax_but_missing_registered_entry_blocks_publication(db, tmp_path):
    _, entity, version, _, _ = state(db)
    path=tmp_path/'renamed.py';path.write_text('def different_name(params):\n    return 1\n')
    db.add(OntologyFunction(name='stale',callable_name='old_name',func_name='old_name',entity_id=entity.id,logic_type='python',source_path=str(path)))
    db.commit()
    with pytest.raises(ValueError,match='缺少已登记的入口'):
        snapshot_components_for_version(db, version)
