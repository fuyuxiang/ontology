"""Failure/recovery regressions for actual runtime integration points."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.models.user import User
from app.models.action import EntityAction
from app.models.action_execution import ActionExecution, recover_interrupted_actions
from app.models.audit import AuditLog
from app.schemas.action import ActionExecuteRequest
from app.api.v1.actions import execute_action
from app.services.action_executors.base import ExecutionResult
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.function_runtime.executor import _coerce_param
from app.services.mcp_tools.python_workspace import _resolve_path, _workspace_dir
from app.services.function_executor import FunctionExecutor
from app.models.function import OntologyFunction
from test_data_plane_integrity_review import data_env, bind

@pytest.fixture
def db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db: yield db
    engine.dispose()


def test_unknown_action_receipt_is_persistent_and_same_key_never_redispatches(db, monkeypatch):
    user=User(id='u',username='u',name='U',password_hash='x',role='admin')
    action=EntityAction(id='a',name='external',category='system',action_type='api_call',type_config={})
    db.add_all([user,action]);db.commit()
    calls=[]
    class Executor:
        async def execute(self,*args):
            calls.append(1)
            return ExecutionResult(False,'dispatch receipt lost',{'outcome':'unknown'})
    monkeypatch.setattr('app.api.v1.actions.get_executor',lambda *args,**kwargs:Executor())
    request=ActionExecuteRequest(params={'ticket':'t1'},idempotency_key='retry-once')
    first=asyncio.run(execute_action('a',request,db,user))
    db.expire_all()
    second=asyncio.run(execute_action('a',request,db,user))
    assert first.state==second.state=='unknown' and not first.success and first.execution_id==second.execution_id
    assert len(calls)==1 and db.query(ActionExecution).count()==1
    assert db.query(AuditLog).one().status=='unknown' and action.impact_count is None
    with pytest.raises(Exception) as conflict:
        asyncio.run(execute_action('a',ActionExecuteRequest(params={'ticket':'other'},idempotency_key='retry-once'),db,user))
    assert conflict.value.status_code==409


def test_restart_marks_interrupted_dispatch_unknown_without_replaying(db):
    db.add(ActionExecution(id='interrupted', action_id='deleted-action', user_id='u', idempotency_key='crash',request_hash='h',state='executing'))
    db.commit()
    assert recover_interrupted_actions(db)==1
    db.expire_all()
    record=db.get(ActionExecution,'interrupted')
    assert record.state=='unknown' and record.output['outcome']=='unknown'
    assert recover_interrupted_actions(db)==0 and db.query(ActionExecution).count()==1


def test_worker_thread_timeout_terminates_python_loop():
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(UnifiedSandbox().execute,'def spin(params):\n    while True: pass\n','spin',{'params':{}},1)
        with pytest.raises(TimeoutError): future.result(timeout=3)


def test_type_coercion_does_not_turn_invalid_boolean_or_fractional_id_into_valid_values():
    assert _coerce_param('not-a-bool','boolean')=='not-a-bool'
    assert _coerce_param('3.5','integer')=='3.5'
    assert _coerce_param('false','boolean') is False
    assert _coerce_param('3','integer')==3


def test_update_contract_rejects_explicit_null_without_breaking_partial_update():
    from app.schemas.action import ActionUpdate
    from app.schemas.function import FunctionUpdate
    from pydantic import ValidationError
    for model,field in [(ActionUpdate,'action_type'),(FunctionUpdate,'logic_type'),(ActionUpdate,'name'),(FunctionUpdate,'name')]:
        with pytest.raises(ValidationError):model.model_validate({field:None})
        assert model.model_validate({}).model_dump(exclude_unset=True)=={}


def test_mcp_inflight_counter_clears_on_request_failure_and_cancel(monkeypatch):
    from app.api.v1 import mcp
    from app.services.mcp_tools.activity import active_requests
    import asyncio
    async def scenario(cancel):
        started=asyncio.Event()
        async def handler(*args):
            started.set()
            assert active_requests()==1
            if cancel:
                await asyncio.Event().wait()
            raise RuntimeError('protocol interrupted')
        monkeypatch.setattr(mcp,'_handle_mcp_request',handler)
        task=asyncio.create_task(mcp.mcp_endpoint(None,None))
        await started.wait()
        if cancel:task.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):await task
        assert active_requests()==0
    asyncio.run(scenario(False));asyncio.run(scenario(True))


def test_mcp_recording_failure_preserves_observed_receipt_and_unknown_outcome(db, monkeypatch):
    from app.api.v1 import mcp
    import json
    class Tool:
        def input_schema(self):return {'properties':{}}
        async def execute(self,*args,**kwargs):return {'success':True,'execution_id':'real-tool-receipt'}
    monkeypatch.setitem(mcp.TOOL_REGISTRY,'ontology_run_action',Tool())
    def fail_log(*args):raise RuntimeError('log commit failed')
    monkeypatch.setattr(mcp,'log_mcp_call',fail_log)
    request=SimpleNamespace(state=SimpleNamespace(mcp_permissions={'rule:execute'}))
    result=asyncio.run(mcp._handle_tools_call({'name':'ontology_run_action','arguments':{}},db,request))
    payload=json.loads(result['content'][0]['text'])
    assert result['isError'] and not payload['success'] and payload['outcome']=='committed_unrecorded'
    assert payload['observed_result']['execution_id']=='real-tool-receipt'


def test_workspace_paths_reject_absolute_escape_traversal_and_symlink(tmp_path, monkeypatch):
    monkeypatch.setattr('app.services.mcp_tools.python_workspace.PYTHON_WORKSPACE_BASE',str(tmp_path/'workspace'))
    with pytest.raises(ValueError):_workspace_dir('../../outside')
    with pytest.raises(ValueError):_resolve_path('ontology','/tmp/outside.py')
    with pytest.raises(ValueError):_resolve_path('ontology','../outside.py')
    root=Path(_workspace_dir('ontology'));root.mkdir(exist_ok=True)
    (root/'escape').symlink_to(tmp_path)
    with pytest.raises(ValueError):_resolve_path('ontology','escape/outside.py')
    assert _resolve_path('ontology','main.py')==str(root/'main.py')


def test_expression_and_inline_python_share_ast_validation(db):
    for kind,code in [('expression','().__class__.__base__.__subclasses__()'),('python','result = params.__class__.__base__')]:
        result=FunctionExecutor(db).execute(OntologyFunction(name='bad',logic_type=kind,logic_body=code,input_schema=[]),{})
        assert not result.success and 'dunder' in result.error


def test_unavailable_sandbox_helpers_fail_instead_of_claiming_a_write():
    with pytest.raises(RuntimeError, match='未提供 update_object'):
        UnifiedSandbox().execute('from ontology_runtime import update_object\ndef execute(params):\n    return update_object("Device", "d1", {})', 'execute', {'params':{}})


def test_mcp_pagination_uses_native_dialect_and_not_keyword_in_literal():
    from app.services.mcp_tools.data_query import _paginate_sql
    assert _paginate_sql("SELECT 'LIMIT' FROM devices", 10, 3, 'sqlite').endswith('LIMIT 10 OFFSET 3')
    assert _paginate_sql('SELECT * FROM devices LIMIT 2', 10, 3, 'sqlite').endswith('LIMIT 2')
    assert _paginate_sql('SELECT * FROM devices', 10, 3, 'sqlserver').endswith('ORDER BY (SELECT NULL) OFFSET 3 ROWS FETCH NEXT 10 ROWS ONLY')
    assert _paginate_sql('SELECT * FROM devices ORDER BY id', 10, 3, 'oracle').endswith('OFFSET 3 ROWS FETCH NEXT 10 ROWS ONLY')


def test_real_instance_write_requires_record_and_mapping_and_readback(data_env):
    from app.services.object_mutation_service import ObjectMutationService
    db,source=data_env;bind(db);db.commit()
    service=ObjectMutationService(db)
    with pytest.raises(ValueError,match='record_id'):service.update('device',None,{'temperature':15})
    with pytest.raises(ValueError,match='未知对象属性'):service.update('device','d1',{'private':'exfiltrate'})
    result=service.update('device','d1',{'temperature':15})
    assert result['instance']=={'id':'d1','temperature':15.0} and result['outcome']=='committed'
    import sqlite3
    with sqlite3.connect(source) as raw: assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0]==15
    assert db.get(__import__('app.models.entity',fromlist=['EntityAttribute']).EntityAttribute,'temperature').type=='number'


def test_committed_instance_write_readback_failure_is_unknown(data_env, monkeypatch):
    from app.services.object_mutation_service import ObjectMutationService
    from app.services.data_plane.execute_service import ExecuteOutcomeUnknown
    db, source = data_env; bind(db); db.commit()
    service = ObjectMutationService(db)
    actual_query = service.data.query_entity_data
    calls = []
    def query(*args, **kwargs):
        calls.append(1)
        return actual_query(*args, **kwargs) if len(calls) == 1 else {'error': 'connection lost'}
    monkeypatch.setattr(service.data, 'query_entity_data', query)
    with pytest.raises(ExecuteOutcomeUnknown) as error:
        service.update('device', 'd1', {'temperature': 21})
    assert error.value.outcome == 'unknown'
    import sqlite3
    with sqlite3.connect(source) as raw:
        assert raw.execute("SELECT temp FROM devices WHERE device_id='d1'").fetchone()[0] == 21


def test_workspace_metadata_update_and_detach_survive_rescan(db, tmp_path, monkeypatch):
    from app.api.v1.functions import _update_workspace_contract
    from app.services.function_runtime.watcher import FunctionWatcher
    from app.services.function_runtime.registry import FunctionRegistry
    monkeypatch.setattr('app.api.v1.functions.WORKSPACE_DIR', tmp_path)
    source = tmp_path / 'main.py'
    source.write_text('from ontology_runtime import Function\n@Function(name="old", params=[])\ndef implementation(params):\n    return params["x"]\n')
    function = OntologyFunction(name='Display', callable_name='old', logic_type='python', source_path=str(source), func_name='implementation', input_schema=[])
    db.add(function); db.commit()
    registry = FunctionRegistry(db)
    watcher = FunctionWatcher(registry, str(tmp_path))
    changes = {'callable_name': 'new', 'input_schema': [{'name':'x', 'type':'number', 'default':5, 'enum':[5,6]}]}
    _update_workspace_contract(function, changes)
    for field, value in changes.items():setattr(function, field, value)
    db.commit(); watcher.scan_all(); db.expire_all()
    assert db.query(OntologyFunction).count() == 1
    refreshed = db.get(OntologyFunction, function.id)
    assert refreshed.callable_name == 'new' and refreshed.input_schema[0]['default'] == 5
    from app.services.function_runtime.executor import FunctionRuntimeExecutor
    runtime = FunctionRuntimeExecutor(registry, UnifiedSandbox(), db)
    assert runtime.execute('new', {}).result == 5
    assert not runtime.execute('new', {'x': 9}).success
    refreshed.status = 'inactive'; db.commit(); watcher.scan_all()
    assert registry.get('new') is None
    db.expire_all(); assert db.get(OntologyFunction, function.id).status == 'inactive'
    _update_workspace_contract(refreshed, {'logic_type':'expression'})
    refreshed.logic_type='expression'; refreshed.logic_body='3'; refreshed.status='active'; db.commit()
    watcher._on_file_changed(str(source)); db.expire_all()
    assert db.get(OntologyFunction, function.id).logic_type == 'expression'
    assert db.query(OntologyFunction).count() == 1 and 'def implementation' in source.read_text()


def test_legacy_snapshot_upgrade_preserves_rows_and_nonnull_entity_contract(db):
    from sqlalchemy import text, inspect
    from app.migrations.runtime_snapshots import migrate_runtime_snapshots
    from app.models import ScenarioDict, OntologyEntity
    from app.models.version import OntologyVersion, OntologyVersionEntity
    from app.models.version_components import OntologyVersionFunction
    from app.services.version_component_snapshot import snapshot_components_for_version
    engine=db.get_bind()
    with engine.begin() as connection:
        connection.execute(text('DROP TABLE ontology_version_functions'))
        connection.execute(text('''CREATE TABLE ontology_version_functions (
            id VARCHAR(36) PRIMARY KEY, version_id VARCHAR(36) NOT NULL,
            source_function_id VARCHAR(36) NOT NULL, version_entity_id VARCHAR(36) NOT NULL,
            name VARCHAR(200) NOT NULL, description TEXT, return_type VARCHAR(50), input_schema JSON,
            logic_type VARCHAR(30), logic_body TEXT, callable_name VARCHAR(100), tags JSON, created_at DATETIME)'''))
        connection.execute(text("INSERT INTO ontology_version_functions (id,version_id,source_function_id,version_entity_id,name,logic_type,logic_body) VALUES ('old','v0','f0','e0','legacy','expression','1')"))
    migrate_runtime_snapshots(engine);migrate_runtime_snapshots(engine)
    assert next(c for c in inspect(engine).get_columns('ontology_version_functions') if c['name']=='version_entity_id')['nullable'] is False
    db.expire_all();legacy=db.get(OntologyVersionFunction,'old')
    assert legacy.logic_body=='1' and legacy.source_code is None
    owner=ScenarioDict(code='legacy-runtime',name='升级本体');db.add(owner);db.flush()
    entity=OntologyEntity(name='Device',name_cn='设备',tier=1,ontology_id=owner.id)
    version=OntologyVersion(name='v1',ontology_id=owner.id,version_number=1,status='draft')
    db.add_all([entity,version]);db.flush()
    snapshot_entity=OntologyVersionEntity(version_id=version.id,source_entity_id=entity.id,name='Device',name_cn='设备',tier=1)
    function=OntologyFunction(name='Ontology function',callable_name='ontology_function',ontology_id=owner.id,logic_type='expression',logic_body='2',status='active')
    db.add_all([snapshot_entity,function]);db.commit()
    assert snapshot_components_for_version(db,version)['functions_count']==1
    db.commit();published=db.query(OntologyVersionFunction).filter_by(version_id=version.id).one()
    assert published.version_entity_id==snapshot_entity.id and published.ontology_id==owner.id


def test_legacy_function_nullable_boolean_is_backfilled_and_migration_is_idempotent(db):
    from sqlalchemy import text, inspect
    from app.migrations.schema_compat import _migrate_ontology_functions
    with db.get_bind().begin() as raw:
        raw.execute(text('DROP TABLE ontology_functions'))
        raw.execute(text('CREATE TABLE ontology_functions (id VARCHAR(36) PRIMARY KEY,name VARCHAR(200),is_derived_property BOOLEAN NULL)'))
        raw.execute(text("INSERT INTO ontology_functions VALUES ('nullable-flag','Legacy',NULL)"))
    for _ in range(2):
        with db.get_bind().connect() as raw:_migrate_ontology_functions(raw,inspect(db.get_bind()),{'ontology_functions'})
    with db.get_bind().connect() as raw:
        assert raw.execute(text("SELECT name,is_derived_property FROM ontology_functions WHERE id='nullable-flag'")).one()==('Legacy',0)


def test_sdk_names_do_not_overwrite_client_or_case_colliding_files(db):
    from app.models.version import OntologyVersion, OntologyVersionEntity
    from app.services.osdk_generator import generate_sdk
    version=OntologyVersion(name='sdk',version_number=1,status='published',is_active=True)
    db.add(version);db.flush()
    for i,name in enumerate(['Client','OntologyClient','Device','device','DeviceProps','__init__']):
        db.add(OntologyVersionEntity(version_id=version.id,source_entity_id=f'entity-{i}',name=name,name_cn=name,tier=1))
    db.commit()
    for language in ('python','typescript'):
        result=generate_sdk(db,language)
        filenames=[item['name'].casefold() for item in result['files']]
        assert len(filenames)==len(set(filenames))
        assert sum(name.startswith('client.') for name in filenames)==1
        if language=='python':
            for item in result['files']:compile(item['content'],item['name'],'exec')
