"""Save/publication gates and manual recovery preserve actual executable contracts."""
import asyncio
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.database import Base
from app.models import ScenarioDict, OntologyEntity
from app.models.entity import EntityAttribute
from app.models.action import EntityAction
from app.models.action_execution import ActionExecution
from app.models.audit import AuditLog
from app.models.function import OntologyFunction
from app.models.user import User
from app.models.version import OntologyVersion, OntologyVersionEntity
from app.api.v1.actions import _validate_action_scope, reconcile_action_execution, ActionReconciliation, execute_action
from app.api.v1.functions import _validate_scope
from app.schemas.action import ActionExecuteRequest
from app.services.version_component_snapshot import snapshot_components_for_version


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([ScenarioDict(id='a',code='a',name='A'), ScenarioDict(id='b',code='b',name='B')]);db.flush()
        db.add_all([OntologyEntity(id='ea',name='Device',name_cn='设备',tier=1,ontology_id='a'),
                    OntologyEntity(id='eb',name='Device',name_cn='设备',tier=1,ontology_id='b')]);db.flush()
        db.add_all([EntityAttribute(id='aa',entity_id='ea',name='status',type='string'),
                    EntityAttribute(id='ab',entity_id='eb',name='status',type='string')]);db.commit()
        yield db
    engine.dispose()


def test_parameter_references_reject_unknown_foreign_and_entity_attribute_mismatch(db):
    for schema in [[{'name':'x','attribute_id':'missing'}], [{'name':'x','attribute_id':'ab'}],
                   [{'name':'x','entity_id':'eb'}], [{'name':'x','entity_id':'eb','attribute_id':'aa'}]]:
        with pytest.raises(HTTPException) as exc:
            _validate_scope(db, {'ontology_id':'a','input_schema':schema})
        assert exc.value.status_code == 422
    assert _validate_scope(db, {'ontology_id':'a','input_schema':[{'name':'x','entity_id':'ea','attribute_id':'aa'}]})['ontology_id']=='a'
    for reference in ['missing','ab']:
        with pytest.raises(HTTPException) as exc:
            _validate_action_scope(db, {'category':'system','ontology_id':'a','status':'draft',
                                       'parameters_json':[{'name':'x','entity_attribute_id':reference}]})
        assert exc.value.status_code == 422
    assert _validate_action_scope(db, {'category':'system','ontology_id':'a','status':'draft',
           'parameters_json':[{'name':'x','entity_attribute_id':'aa'}]})['ontology_id']=='a'


@pytest.mark.parametrize('kind', ['api_call','sql_exec','modify_attribute','notification','call_function','custom_script'])
def test_all_active_action_types_require_real_config_and_draft_can_be_saved(db, kind):
    values = {'category':'domain','entity_id':'ea','ontology_id':'a','action_type':kind,'type_config':{}}
    with pytest.raises(HTTPException) as exc:_validate_action_scope(db, dict(values))
    assert exc.value.status_code == 422 and '必填' in exc.value.detail
    assert _validate_action_scope(db, {**values,'status':'draft'})['ontology_id']=='a'
    legacy = EntityAction(**{**values,'name':'Incomplete legacy','status':'active'})
    db.add(legacy);db.commit()
    version=OntologyVersion(id='v',name='v1',version_number=1,ontology_id='a',status='draft');db.add(version);db.flush()
    db.add(OntologyVersionEntity(version_id='v',source_entity_id='ea',name='Device',name_cn='设备',tier=1));db.commit()
    with pytest.raises(ValueError, match='必填'):snapshot_components_for_version(db,version)
    db.rollback()


def test_active_action_target_and_script_validation_is_shared_with_publication(db):
    with pytest.raises(HTTPException, match='当前本体'):
        _validate_action_scope(db,{'category':'domain','entity_id':'ea','ontology_id':'a','action_type':'modify_attribute',
            'type_config':{'target_entity_id':'eb','target_attribute':'status','value_expression':'x'}})
    with pytest.raises(HTTPException, match='脚本'):
        _validate_action_scope(db,{'category':'system','ontology_id':'a','action_type':'custom_script',
            'type_config':{'script':'result = params.__class__'}})
    db.add(OntologyFunction(name='calc',callable_name='calc',entity_id='ea',ontology_id='a',logic_body='2'));db.commit()
    assert _validate_action_scope(db,{'category':'system','ontology_id':'a','action_type':'call_function',
        'type_config':{'function_id':db.query(OntologyFunction).one().id}})['ontology_id']=='a'
    with pytest.raises(HTTPException) as invalid_expression:
        _validate_action_scope(db,{'category':'domain','entity_id':'ea','ontology_id':'a','action_type':'modify_attribute',
            'type_config':{'target_entity_id':'ea','target_attribute':'status','value_expression':'expr: params['}})
    assert invalid_expression.value.status_code==422


def test_manual_receipt_reconciliation_is_audited_and_never_redispatches(db, monkeypatch):
    user=User(id='owner',username='owner',name='Owner',password_hash='x',role='editor')
    stranger=User(id='stranger',username='stranger',name='Stranger',password_hash='x',role='editor')
    viewer=User(id='viewer',username='viewer',name='Viewer',password_hash='x',role='viewer')
    action=EntityAction(id='action',name='External receipt',ontology_id='a',category='system',action_type='api_call',impact_count=0)
    record=ActionExecution(id='execution',action_id='action',ontology_id='a',user_id='owner',idempotency_key='original',
        request_hash='digest',state='unknown',params={'ticket':'t1'},output={'outcome':'unknown'})
    db.add_all([user,stranger,viewer,action,record]);db.commit()
    data=ActionReconciliation(resolution='succeeded',evidence='Checked source ticket t1 and supplier receipt 77',receipt_id='77')
    def forbidden_dispatch(*args,**kwargs):raise AssertionError('reconciliation dispatched an action')
    monkeypatch.setattr('app.api.v1.actions.get_executor',forbidden_dispatch)
    with pytest.raises(HTTPException) as denied:reconcile_action_execution('action','execution',data,db,stranger)
    assert denied.value.status_code==404
    with pytest.raises(HTTPException) as denied:reconcile_action_execution('action','execution',data,db,viewer)
    assert denied.value.status_code==403
    result=reconcile_action_execution('action','execution',data,db,user)
    db.expire_all()
    assert result.success and result.state=='succeeded' and result.output['outcome']=='manually_reconciled'
    assert db.get(ActionExecution,'execution').idempotency_key=='original'
    assert db.get(EntityAction,'action').impact_count==1
    audit=db.query(AuditLog).one();assert audit.action=='manual_reconciliation' and audit.status=='success'
    assert json.loads(audit.details)['receipt_id']=='77'
    with pytest.raises(HTTPException) as conflict:reconcile_action_execution('action','execution',data,db,user)
    assert conflict.value.status_code==409
    assert db.get(EntityAction,'action').impact_count==1


def test_executing_and_terminal_records_cannot_be_manually_relabelled(db):
    user=User(id='admin',username='admin',name='Admin',password_hash='x',role='admin');db.add(user)
    for state in ['pending','executing','succeeded','failed']:
        db.add(ActionExecution(id=state,action_id='action',user_id='owner',idempotency_key=state,request_hash='x',state=state))
    db.commit()
    for state in ['pending','executing','succeeded','failed']:
        with pytest.raises(HTTPException) as conflict:
            reconcile_action_execution('action',state,ActionReconciliation(resolution='failed',evidence='Checked receipt and confirmed no write'),db,user)
        assert conflict.value.status_code==409


def test_invalid_or_missing_workspace_remains_editable_without_overwriting_existing_binding(db,tmp_path,monkeypatch):
    from app.api.v1 import functions, actions
    monkeypatch.setattr(functions,'WORKSPACE_DIR',tmp_path)
    monkeypatch.setattr(actions,'WORKSPACE_DIR',tmp_path)
    legacy=tmp_path/'legacy';legacy.mkdir();source=legacy/'main.py';source.write_text('def calc(params):\n    invalid (\n')
    fn=OntologyFunction(id='workspace-function',name='Calculation',callable_name='calc',ontology_id='a',source_path=str(source),func_name='calc',logic_type='python')
    action_dir=tmp_path/'action_workspace-action';action_dir.mkdir();action_source=action_dir/'main.py';action_source.write_text('def execute(params):\n    invalid (\n')
    act=EntityAction(id='workspace-action',name='Repair',category='domain',entity_id='ea',ontology_id='a',status='draft',action_type='custom_script',
        type_config={'source_path':str(action_source),'func_name':'execute','callable_name':'execute'})
    db.add_all([fn,act]);db.commit()
    for obj,open_workspace,path in [(fn,functions.open_workspace,source),(act,actions.open_action_workspace,action_source)]:
        original=path.read_text()
        response=open_workspace(obj.id,db,None)
        assert response.folder==str(path.parent) and response.registration_error
        assert path.read_text()==original
        path.unlink()
        response=open_workspace(obj.id,db,None)
        assert response.registration_error and not path.exists()


def test_action_workspace_does_not_switch_entry_to_first_helper(db,tmp_path,monkeypatch):
    from app.api.v1 import actions
    monkeypatch.setattr(actions,'WORKSPACE_DIR',tmp_path)
    folder=tmp_path/'action_workspace';folder.mkdir()
    source=folder/'main.py';source.write_text('def helper(params):\n    return {"wrong":True}\ndef run(params):\n    return {"correct":True}\n')
    act=EntityAction(id='workspace',name='Repair',category='domain',entity_id='ea',ontology_id='a',status='draft',action_type='custom_script',
        type_config={'source_path':str(source),'func_name':'run','callable_name':'run'})
    db.add(act);db.commit()
    response=actions.open_action_workspace('workspace',db,None)
    assert not response.registration_error and act.type_config['func_name']=='run'


@pytest.mark.parametrize('logic_type,body', [('expression',''),('expression','x = 1'),('python','result = params.__class__'),('sql','UPDATE devices SET temp=1')])
def test_unexecutable_active_functions_do_not_publish(db,logic_type,body):
    version=OntologyVersion(id='bad-v',name='Bad',version_number=1,ontology_id='a',status='draft');db.add(version);db.flush()
    db.add(OntologyVersionEntity(version_id='bad-v',source_entity_id='ea',name='Device',name_cn='设备',tier=1))
    db.add(OntologyFunction(name='Unexecutable',entity_id='ea',ontology_id='a',logic_type=logic_type,logic_body=body));db.commit()
    with pytest.raises(ValueError):snapshot_components_for_version(db,version)


def test_version_history_preserves_ontology_owner_and_filters_without_hiding_rows(db):
    from app.api.v1.ontology_publish import list_versions, get_version
    db.add_all([OntologyVersion(id='a-v1',name='A1',version_number=1,ontology_id='a'),
                OntologyVersion(id='b-v1',name='B1',version_number=1,ontology_id='b')]);db.commit()
    all_versions=list_versions(db=db)
    assert {row['ontology_id'] for row in all_versions}=={'a','b'}
    assert [row['id'] for row in list_versions(ontology_id='a',db=db)]==['a-v1']
    assert get_version('a-v1',db=db)['ontology_id']=='a'
