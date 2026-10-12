"""Standalone isolated acceptance: actual startup, API creation, writes, versions, SDK and MCP.

Run: PYTHONPATH=backend python3 backend/tests/run_runtime_versions_acceptance.py
Only source business rows are seeded directly. Ontology/assets/mappings/functions/
versions/actions are built through real production APIs. No external drivers are replaced.
"""
from pathlib import Path
import os
import tempfile
import sqlite3
import json
import sys
import time
import importlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import socketserver

ROOT = Path(tempfile.mkdtemp(prefix='ontology-runtime-acceptance-'))
os.environ.update(DATABASE_URL=f'sqlite:///{ROOT / "metadata.sqlite"}', SECRET_KEY='runtime-acceptance-isolated-key',
    ADMIN_INITIAL_PASSWORD='ReviewPass2026', WORKSPACE_ROOT=str(ROOT/'workspace'), LOCAL_DATA_ROOT=str(ROOT), MONITOR_ENABLED='false')
SOURCE = ROOT/'source.sqlite'
with sqlite3.connect(SOURCE) as raw:
    raw.execute('CREATE TABLE devices (device_id TEXT PRIMARY KEY, temp REAL NOT NULL, spare REAL NOT NULL, status TEXT NOT NULL)')
    raw.execute('INSERT INTO devices VALUES ("d1",90,30,"alarm")')
    raw.execute('CREATE TABLE tickets (ticket_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, state TEXT NOT NULL)')
    raw.execute('INSERT INTO tickets VALUES ("t1","d1","open")')
    raw.execute('CREATE TABLE devices_b (device_id TEXT PRIMARY KEY, temp REAL NOT NULL)')
    raw.execute('INSERT INTO devices_b VALUES ("b1",11)')

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.function import OntologyFunction
from app.models.action_execution import ActionExecution
from app.services.function_runtime.registry import FunctionRegistry
from app.services.function_runtime.executor import FunctionRuntimeExecutor
from app.services.function_runtime.sandbox import UnifiedSandbox

EVIDENCE=[]
RECEIPTS=[]
SMTP_RECEIPTS=[]
class ReceiptServer(BaseHTTPRequestHandler):
    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        RECEIPTS.append(data)
        if self.path == '/slow':
            time.sleep(.3)
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('X-Receipt-ID', str(len(RECEIPTS))); self.end_headers()
        try:
            self.wfile.write(json.dumps({'success':self.path != '/reject', 'receipt':len(RECEIPTS)}).encode())
        except BrokenPipeError:
            pass
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1',0), ReceiptServer)
threading.Thread(target=server.serve_forever, daemon=True).start()
WEBHOOK=f'http://127.0.0.1:{server.server_port}/receipts'
class SMTPReceiptServer(socketserver.StreamRequestHandler):
    """A real plaintext SMTP receipt fixture; no production mail is sent."""
    def handle(self):
        self.wfile.write(b'220 localhost SMTP review\r\n')
        sender='';recipients=[]
        while line:=self.rfile.readline():
            command=line.decode().strip();upper=command.upper()
            if upper.startswith(('EHLO','HELO')): response=b'250 localhost\r\n'
            elif upper.startswith('MAIL FROM:'):
                sender=command.split(':',1)[1].strip(' <>');recipients=[];response=b'250 OK\r\n'
            elif upper.startswith('RCPT TO:'):
                recipients.append(command.split(':',1)[1].strip(' <>'));response=b'250 OK\r\n'
            elif upper=='DATA':
                self.wfile.write(b'354 End with dot\r\n');body=[]
                while (data:=self.rfile.readline()) and data!=b'.\r\n':body.append(data)
                SMTP_RECEIPTS.append({'sender':sender,'recipients':recipients,'message':b''.join(body).decode()})
                response=b'250 queued\r\n'
            elif upper=='QUIT':
                self.wfile.write(b'221 bye\r\n');return
            else:response=b'250 OK\r\n'
            self.wfile.write(response)
smtp_server=socketserver.ThreadingTCPServer(('127.0.0.1',0),SMTPReceiptServer)
smtp_thread=threading.Thread(target=smtp_server.serve_forever,daemon=True);smtp_thread.start()
SMTP_PORT=smtp_server.server_address[1]


def request(client, method, path, body=None, expected=200):
    response = client.request(method, '/api/v1'+path, json=body)
    assert response.status_code == expected, (method,path,response.status_code,response.text)
    result = response.json() if response.content else None
    if path != '/auth/login':
        EVIDENCE.append({'method':method,'path':path,'status':response.status_code,'result':result})
    return result

def mcp(client, name, args):
    result = request(client,'POST','/mcp',{'jsonrpc':'2.0','id':len(EVIDENCE),'method':'tools/call','params':{'name':name,'arguments':args}})
    assert not result.get('error'), result
    assert not result['result'].get('isError'), result
    return json.loads(result['result']['content'][0]['text'])


def main():
    with TestClient(app) as client:
        auth=request(client,'POST','/auth/login',{'username':'admin','password':'ReviewPass2026'})
        token=auth['token']; client.headers['Authorization']='Bearer '+token
        ontology=request(client,'POST','/scenarios',{'code':'runtime_review','name':'Runtime review'},201)
        oid=ontology['id']
        connection=request(client,'POST','/connections',{'name':'Isolated actual SQLite','type':'sqlite','database':str(SOURCE),'writable':True,'rate_limit_qps':10000},201)
        assert request(client,'POST',f'/connections/{connection["id"]}/test')['success']
        asset=request(client,'POST','/assets',{'name':'devices','kind':'table','connection_id':connection['id'],'locator':{'table':'devices'},'cache_ttl_seconds':60},201)
        entity=request(client,'POST','/entities',{'name':'Device','name_cn':'设备','tier':1,'ontology_id':oid,'attributes':[
            {'name':'id','type':'string','required':True},{'name':'temperature','type':'number','required':True},{'name':'status','type':'string','required':True}]},201)
        eid=entity['id']; attrs={a['name']:a['id'] for a in entity['attributes']}
        mapping=[{'attribute_id':attrs[k],'source_column':v} for k,v in [('id','device_id'),('temperature','temp'),('status','status')]]
        binding=request(client,'POST','/object-bindings',{'object_type_id':eid,'asset_id':asset['id'],'role':'primary','id_column':'device_id','field_mappings':mapping},201)
        assert request(client,'POST',f'/assets/{asset["id"]}/preview',{})['rows'][0][0]=='d1'
        ticket_asset=request(client,'POST','/assets',{'name':'tickets','kind':'table','connection_id':connection['id'],'locator':{'table':'tickets'}},201)
        ticket=request(client,'POST','/entities',{'name':'Ticket','name_cn':'工单','tier':1,'ontology_id':oid,'attributes':[
            {'name':'id','type':'string','required':True},{'name':'device','type':'string','required':True},{'name':'state','type':'string','required':True}]},201)
        ticket_attrs={a['name']:a['id'] for a in ticket['attributes']}
        request(client,'POST','/object-bindings',{'object_type_id':ticket['id'],'asset_id':ticket_asset['id'],'role':'primary','id_column':'ticket_id',
            'field_mappings':[{'attribute_id':ticket_attrs[k],'source_column':v} for k,v in [('id','ticket_id'),('device','device_id'),('state','state')]]},201)
        request(client,'POST','/relations',{'from_entity_id':eid,'to_entity_id':ticket['id'],'name':'tickets','source_field':'id','target_field':'device'},201)
        helper=request(client,'POST','/functions',{'entity_id':eid,'ontology_id':oid,'name':'helper','callable_name':'helper','logic_type':'expression','logic_body':"params['x'] * 2",'input_schema':[{'name':'x','type':'number','required':True}]},201)
        inline=request(client,'POST','/functions',{'entity_id':eid,'ontology_id':oid,'name':'inline','callable_name':'inline','logic_type':'python','logic_body':"result = {'risk': params['x'] + 5}"},201)
        assert request(client,'POST',f'/functions/{inline["id"]}/test',{'params':{'x':2}})['result']=={'risk':7}
        sql=request(client,'POST','/functions',{'entity_id':eid,'ontology_id':oid,'name':'count','callable_name':'count','logic_type':'sql','logic_body':'SELECT COUNT(*) FROM devices'},201)
        assert request(client,'POST',f'/functions/{sql["id"]}/test',{'params':{}})['result']==1
        function=request(client,'POST','/functions',{'entity_id':eid,'ontology_id':oid,'name':'risk','callable_name':'risk','logic_type':'python','input_schema':[{'name':'x','type':'number','required':True}]},201)
        workspace=request(client,'POST',f'/functions/{function["id"]}/workspace')
        source=Path(workspace['folder'])/'main.py'
        code="from ontology_runtime import Function, call_function\n@Function(name='risk', type='logic', params=[{'name':'x','type':'number','required':True}])\ndef risk(params):\n    return call_function('helper', params) + 1\n"
        source.write_text(code)
        # Observe real polling watcher registration, with no direct registry success seed.
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with SessionLocal() as db:
                fn=db.get(OntologyFunction,function['id'])
                if fn.checksum and fn.input_schema[0]['name']=='x': break
            time.sleep(.15)
        else: raise AssertionError('watcher did not register edited source')
        assert request(client,'POST',f'/functions/{function["id"]}/test',{'params':{'x':3}})['result']==7
        action=request(client,'POST','/actions',{'name':'Repair status','category':'domain','entity_id':eid,'ontology_id':oid,'action_type':'modify_attribute',
            'type_config':{'target_entity_id':eid,'target_attribute':'status','value_expression':"expr: params['new_status']"},
            'parameters_json':[{'name':'record_id','type':'string','required':True},{'name':'new_status','type':'string','required':True}]},201)
        workspace_action=request(client,'POST','/actions',{'name':'Workspace repair calculation','category':'domain','entity_id':eid,'ontology_id':oid,
            'status':'draft','action_type':'custom_script','type_config':{'callable_name':'work_script'},'parameters_json':[{'name':'x','type':'number','required':True}]},201)
        action_workspace=request(client,'POST',f'/actions/{workspace_action["id"]}/workspace')
        action_source=Path(action_workspace['folder'])/'main.py'
        action_code="from ontology_runtime import Function, call_function\n@Function(name='work_script', type='action', params=[{'name':'x','type':'number','required':True}])\ndef work_script(params):\n    return {'risk':call_function('helper', params) + 2}\n"
        action_source.write_text(action_code)
        request(client,'PUT',f'/actions/{workspace_action["id"]}',{'status':'active'})
        assert request(client,'POST',f'/actions/{workspace_action["id"]}/execute',{'params':{'x':3},'idempotency_key':'workspace-draft'})['output']['risk']==8
        inflight_action=request(client,'POST','/actions',{'name':'Track in-flight request','category':'domain','entity_id':eid,'ontology_id':oid,'action_type':'api_call',
            'type_config':{'url':WEBHOOK.replace('/receipts','/slow'),'method':'POST','body':{'tracker':'waiting'},'timeout_seconds':1}},201)
        v1=request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':oid,'name':'v1'})
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['temperature']==90
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','user_id':'spoof','params':{'x':3}})['result']==7
        performed=request(client,'POST',f'/actions/{action["id"]}/execute',{'version_id':v1['version_id'],'idempotency_key':'repair-once','params':{'record_id':'d1','new_status':'repair'}})
        assert performed['success'] and performed['state']=='succeeded'
        replay=request(client,'POST',f'/actions/{action["id"]}/execute',{'version_id':v1['version_id'],'idempotency_key':'repair-once','params':{'record_id':'d1','new_status':'repair'}})
        assert replay['execution_id']==performed['execution_id']
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['status']=='repair'
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1/relations')[0]['instances'][0]['id']=='t1'
        # All Action types dispatch actual implementations; webhook is a real local receipt server.
        cases=[('call_function',{'function_name':'helper'},{'x':4},8),('custom_script',{'script':"result['ok'] = params['x'] + 1"},{'x':4},None),
               ('api_call',{'url':WEBHOOK,'method':'POST','body':{'number':'$x','enabled':'$enabled'}},{'x':4,'enabled':True},None),
               ('notification',{'channel':'system','recipient':'admin','message_template':'Repair complete $id'},{'id':'d1'},None),
               ('notification',{'channel':'webhook','recipient':'ops','message_template':'Repair $id','webhook_url':WEBHOOK},{'id':'d1'},None),
               ('sql_exec',{'connection_id':connection['id'],'sql':'UPDATE devices SET temp=temp+1 WHERE device_id=$id'},{'id':'d1'},None)]
        for i,(kind,config,params,expected) in enumerate(cases):
            a=request(client,'POST','/actions',{'name':kind+str(i),'category':'domain','entity_id':eid,'ontology_id':oid,'action_type':kind,'type_config':config},201)
            if kind=='sql_exec':
                def fire():
                    return client.post(f'/api/v1/actions/{a["id"]}/execute',json={'params':params,'idempotency_key':'concurrent-sql'}).json()
                with ThreadPoolExecutor(max_workers=2) as pool: concurrent=list(pool.map(lambda _:fire(),range(2)))
                final=request(client,'POST',f'/actions/{a["id"]}/execute',{'params':params,'idempotency_key':'concurrent-sql'})
                assert final['success'] and len({r['execution_id'] for r in concurrent})==1
            else:
                execution=request(client,'POST',f'/actions/{a["id"]}/execute',{'params':params,'idempotency_key':'type-'+str(i)})
                assert execution['success'],execution
                if expected is not None: assert execution['output']['result']==expected
        with sqlite3.connect(SOURCE) as raw:
            assert raw.execute('SELECT temp,status FROM devices WHERE device_id="d1"').fetchone()==(91.0,'repair')
        assert RECEIPTS[0]['number']==4 and RECEIPTS[0]['enabled'] is True
        assert request(client,'GET','/actions/notifications')[0]['receipt']['message']=='Repair complete d1'
        request(client,'PUT','/system-config',{'group':'notification','items':[
            {'key':'notification.smtp_host','value':'127.0.0.1'}, {'key':'notification.smtp_port','value':str(SMTP_PORT)},
            {'key':'notification.smtp_username','value':'review@example.invalid'}, {'key':'notification.smtp_encryption','value':'none'}]})
        email=request(client,'POST','/actions',{'name':'SMTP receipt','category':'domain','entity_id':eid,'ontology_id':oid,'action_type':'notification',
            'type_config':{'channel':'email','recipient':'recipient@example.invalid','message_template':'Repair persisted d1'}},201)
        smtp_result=request(client,'POST',f'/actions/{email["id"]}/execute',{'idempotency_key':'smtp-once'})
        assert smtp_result['success'],smtp_result
        assert len(SMTP_RECEIPTS)==1 and 'Repair persisted d1' in SMTP_RECEIPTS[0]['message']
        # The downstream has accepted the HTTP request, but its receipt times
        # out. Retrying the same action key must not dispatch a second write.
        timeout_action=request(client,'POST','/actions',{'name':'Unknown receipt','category':'domain','entity_id':eid,'ontology_id':oid,'action_type':'api_call',
            'type_config':{'url':WEBHOOK.replace('/receipts','/slow'),'method':'POST','body':{'id':'once'},'timeout_seconds':.05}},201)
        before=len(RECEIPTS)
        unknown=request(client,'POST',f'/actions/{timeout_action["id"]}/execute',{'idempotency_key':'timeout-once'})
        assert not unknown['success'] and unknown['state']=='unknown'
        same=request(client,'POST',f'/actions/{timeout_action["id"]}/execute',{'idempotency_key':'timeout-once'})
        assert same['execution_id']==unknown['execution_id'] and len(RECEIPTS)==before+1
        receipt=RECEIPTS[-1]
        assert receipt['id']=='once'
        reconciliation_path=f'/actions/{timeout_action["id"]}/executions/{unknown["execution_id"]}/reconcile'
        def reconcile():
            response=client.post('/api/v1'+reconciliation_path,json={
                'resolution':'succeeded','evidence':'Local receipt server accepted exactly one request with id once; receipt list inspected', 'receipt_id':'local-once'})
            return {'method':'POST','path':reconciliation_path,'status':response.status_code,'result':response.json()}
        with ThreadPoolExecutor(max_workers=2) as pool: reconciliations=list(pool.map(lambda _:reconcile(),range(2)))
        EVIDENCE.extend(reconciliations)
        assert sorted(r['status'] for r in reconciliations)==[200,409]
        reconciled=next(r['result'] for r in reconciliations if r['status']==200)
        assert reconciled['success'] and reconciled['output']['manual_reconciliation']['method']=='manual'
        after_reconciliation=request(client,'POST',f'/actions/{timeout_action["id"]}/execute',{'idempotency_key':'timeout-once'})
        assert after_reconciliation['state']=='succeeded' and len(RECEIPTS)==before+1
        rejected=request(client,'POST','/actions',{'name':'Webhook rejected business','category':'domain','entity_id':eid,'ontology_id':oid,'action_type':'notification',
            'type_config':{'channel':'webhook','recipient':'ops','message_template':'test','webhook_url':WEBHOOK.replace('/receipts','/reject')}},201)
        assert request(client,'POST',f'/actions/{rejected["id"]}/execute',{'idempotency_key':'rejected'})['state']=='failed'
        # A second ontology deliberately reuses names and has independent
        # bindings/functions/version state. A rollback in A must not change B.
        other=request(client,'POST','/scenarios',{'code':'runtime_other','name':'Runtime B'},201)
        other_asset=request(client,'POST','/assets',{'name':'devices_b','kind':'table','connection_id':connection['id'],'locator':{'table':'devices_b'}},201)
        other_entity=request(client,'POST','/entities',{'name':'Device','name_cn':'B设备','tier':1,'ontology_id':other['id'],
            'attributes':[{'name':'id','type':'string','required':True},{'name':'temperature','type':'number','required':True}]},201)
        other_binding=request(client,'POST','/object-bindings',{'object_type_id':other_entity['id'],'asset_id':other_asset['id'],'role':'primary','id_column':'device_id',
            'field_mappings':[{'attribute_id':a['id'],'source_column':'device_id' if a['name']=='id' else 'temp'} for a in other_entity['attributes']]},201)
        request(client,'POST','/functions',{'entity_id':other_entity['id'],'ontology_id':other['id'],'name':'helper','callable_name':'helper',
            'logic_type':'expression','logic_body':"params['x'] * 100"},201)
        other_version=request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':other['id'],'name':'B v1'})
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_other','logic_name':'helper','params':{'x':3}})['result']==300
        # Draft mapping/source changes must not alter v1 executable or data definitions.
        mapping[1]['source_column']='spare'
        request(client,'PUT',f'/object-bindings/{binding["id"]}',{'field_mappings':mapping})
        request(client,'PUT',f'/actions/{action["id"]}',{'type_config':{'target_entity_id':eid,'target_attribute':'status','value_expression':'scheduled'}})
        source.write_text(code.replace('+ 1','+ 10'))
        action_source.write_text(action_code.replace('+ 2','+ 20'))
        assert request(client,'POST',f'/actions/{workspace_action["id"]}/execute',{'version_id':v1['version_id'],
            'params':{'x':3},'idempotency_key':'workspace-v1'})['output']['risk']==8
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','params':{'x':3}})['result']==7
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['temperature']==91
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_other','logic_name':'helper','params':{'x':3}})['result']==300
        assert request(client,'GET',f'/ontology-api/objects/{other_entity["id"]}/b1')['temperature']==11
        assert request(client,'GET',f'/ontology-publish/versions?ontology_id={other["id"]}')[0]['id']==other_version['version_id']
        assert mcp(client,'ontology_object_find',{'ontology_name':'runtime_review','object_name':'Device','filters':{'id':'d1'}})['rows'][0][1]==91
        assert mcp(client,'ontology_get_attr_mapping',{'ontology_name':'runtime_review','object_names':['Device']})[0]['attr_to_col']['temperature']=='temp'
        v2=request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':oid,'name':'v2'})
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','params':{'x':3}})['result']==16
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['temperature']==30
        assert request(client,'POST',f'/actions/{workspace_action["id"]}/execute',{'version_id':v2['version_id'],
            'params':{'x':3},'idempotency_key':'workspace-v2'})['output']['risk']==26
        assert request(client,'POST',f'/actions/{action["id"]}/execute',{'version_id':v2['version_id'],'idempotency_key':'v2-status',
            'params':{'record_id':'d1','new_status':'ignored'}})['success']
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['status']=='scheduled'
        rollback=request(client,'POST',f'/ontology-publish/versions/{v1["version_id"]}/rollback')
        assert rollback['status']=='pending_approval'
        request(client,'POST',f'/ontology-publish/versions/{rollback["id"]}/approve')
        assert request(client,'POST',f'/actions/{workspace_action["id"]}/execute',{'version_id':rollback['id'],
            'params':{'x':3},'idempotency_key':'workspace-rollback'})['output']['risk']==8
        assert request(client,'POST',f'/actions/{action["id"]}/execute',{'version_id':rollback['id'],'idempotency_key':'rollback-status',
            'params':{'record_id':'d1','new_status':'repair'}})['success']
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','params':{'x':3}})['result']==7
        assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['temperature']==91
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_other','logic_name':'helper','params':{'x':3}})['result']==300
        assert request(client,'GET',f'/ontology-api/objects/{other_entity["id"]}/b1')['temperature']==11
        # Workspace helper bridge traverses a real HTTP MCP endpoint and nested
        # call while the actual lifespan is running in the TestClient above.
        import uvicorn
        import httpx
        protocol = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=0, log_level='error', lifespan='off'))
        protocol_thread = threading.Thread(target=protocol.run, daemon=True)
        protocol_thread.start()
        deadline=time.monotonic()+5
        while not protocol.started and time.monotonic()<deadline: time.sleep(.05)
        assert protocol.started
        protocol_port=protocol.servers[0].sockets[0].getsockname()[1]
        def protocol_call(name,args):
            response=httpx.post(f'http://127.0.0.1:{protocol_port}/api/v1/mcp',headers={'Authorization':'Bearer '+token},json={
                'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}},timeout=10)
            assert response.status_code==200,response.text
            result=response.json()['result']; payload=json.loads(result['content'][0]['text'])
            assert not result.get('isError'),payload
            EVIDENCE.append({'method':'HTTP MCP','tool':name,'result':payload})
            return payload
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(protocol_call,'ontology_run_action',{'ontology_name':'runtime_review','object_name':'Device','action_name':inflight_action['name'],
                'params':{},'idempotency_key':'track-in-flight'})
            deadline=time.monotonic()+3
            while not any(r.get('tracker')=='waiting' for r in RECEIPTS) and time.monotonic()<deadline:time.sleep(.01)
            assert request(client,'GET','/mcp/stats/overview')['active_requests']>=1
            assert pending.result(timeout=5)['success']
        assert request(client,'GET','/mcp/stats/overview')['active_requests']==0
        written=protocol_call('write_python_file',{'ontology_name':'runtime_review','filename':'bridge_acceptance.py',
            'python_code':"import json\nfrom __ontology_runtime__ import execute_logic\nprint(json.dumps(execute_logic('risk', {'x':3})))\n"})
        executed=protocol_call('run_python_file',{'ontology_name':'runtime_review','file_path':written['file_path']})
        assert json.loads(executed['stdout'])['result']==7
        # Import and call generated Python SDK using the real API transport.
        sdk=request(client,'POST','/osdk/generate',{'language':'python','entity_ids':[eid]})
        package=ROOT/'ontology_sdk'; package.mkdir()
        for item in sdk['files']: (package/item['name']).write_text(item['content'])
        sys.path.insert(0,str(ROOT)); generated=importlib.import_module('ontology_sdk')
        sdk_client=generated.OntologyClient('http://testserver/api/v1',token=token)
        sdk_client.http.close()
        class Transport:
            def get(self,path,params=None): return client.get('/api/v1/'+path,params=params)
            def close(self): pass
        sdk_client.http=Transport()
        assert generated.Device.get(sdk_client,'d1').temperature==91
        assert len(generated.Device.list(sdk_client,filter={'status':'repair'}))==1
        assert generated.Device.get(sdk_client,'d1').relations(sdk_client)[0]['instances'][0]['id']=='t1'
        ts=request(client,'POST','/osdk/generate',{'language':'typescript','entity_ids':[eid]})
        tsdir=ROOT/'typescript';tsdir.mkdir()
        for item in ts['files']:(tsdir/item['name']).write_text(item['content'])
        compiler=Path(__file__).resolve().parents[2]/'frontend/node_modules/.bin/tsc'
        if compiler.exists():
            compiled=subprocess.run([str(compiler),'--noEmit','--strict','--target','ES2020','--module','ESNext','--moduleResolution','bundler','--lib','ES2020,DOM',str(tsdir/'index.ts')],capture_output=True,text=True)
            assert compiled.returncode==0,compiled.stdout+compiled.stderr
            compiled_dir=ROOT/'typescript-commonjs'
            emitted=subprocess.run([str(compiler),'--strict','--target','ES2020','--module','commonjs','--ignoreDeprecations','6.0','--lib','ES2020,DOM',
                '--outDir',str(compiled_dir),str(tsdir/'index.ts')],capture_output=True,text=True)
            assert emitted.returncode==0,emitted.stdout+emitted.stderr
            node_code="""const {OntologyClient, Device} = require(process.env.ONTOLOGY_SDK_MODULE);
                (async () => {
                  const client = new OntologyClient(process.env.ONTOLOGY_API_URL, process.env.ONTOLOGY_RUNTIME_TOKEN);
                  const instance = await Device.get(client, 'd1');
                  const list = await Device.list(client, {filter:{status:'repair'}});
                  const relations = await instance.relations();
                  if(instance.props.temperature !== 91 || list.length !== 1 || relations[0].instances[0].id !== 't1') throw new Error('SDK returned wrong instances');
                  console.log(JSON.stringify({temperature:instance.props.temperature,list_count:list.length,ticket_id:relations[0].instances[0].id}));
                })().catch(error => { console.error(error); process.exit(1); });"""
            invoked=subprocess.run(['node','-e',node_code],capture_output=True,text=True,env={**os.environ,
                'ONTOLOGY_SDK_MODULE':str(compiled_dir/'index.js'),'ONTOLOGY_API_URL':f'http://127.0.0.1:{protocol_port}/api/v1','ONTOLOGY_RUNTIME_TOKEN':token},timeout=15)
            assert invoked.returncode==0,invoked.stdout+invoked.stderr
            EVIDENCE.append({'method':'TypeScript SDK real HTTP','result':json.loads(invoked.stdout)})
        else: raise AssertionError('TypeScript compiler unavailable')
        protocol.should_exit=True;protocol_thread.join(10);assert not protocol_thread.is_alive()
        # Authentication and protocol failure cannot appear as success.
        assert client.post('/api/v1/mcp',headers={'Authorization':''},json={'jsonrpc':'2.0','id':1,'method':'tools/list'}).status_code==401
        failed=request(client,'POST','/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'ontology_run_logic','arguments':{'ontology_name':'runtime_review','logic_name':'missing','params':{}}}})
        assert failed['result']['isError'] is True
        missing_mapping=request(client,'POST','/mcp',{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'ontology_get_attr_mapping',
            'arguments':{'ontology_name':'runtime_review','object_names':['missing']}}})
        assert missing_mapping['result']['isError'] is True
        assert request(client,'GET','/mcp/stats/overview')['error_rate']>0
        request(client,'DELETE',f'/functions/{function["id"]}',expected=204)
        assert not source.exists()
        assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','params':{'x':3}})['result']==7
        request(client,'DELETE',f'/actions/{workspace_action["id"]}',expected=204)
        assert not action_source.exists()
        assert request(client,'POST',f'/actions/{workspace_action["id"]}/execute',{'version_id':rollback['id'],
            'params':{'x':3},'idempotency_key':'workspace-deleted-historical'})['output']['risk']==8
        # MCP raw SQL and object values have intentionally different contracts.
        # Publish transformed B through the real API; never seed a successful
        # version or transform result directly in metadata.
        other_mapping=[{'attribute_id':attribute['id'],
            'source_column':'device_id' if attribute['name']=='id' else 'temp',
            **({'transform':'value / 10'} if attribute['name']=='temperature' else {})}
            for attribute in other_entity['attributes']]
        request(client,'PUT',f'/object-bindings/{other_binding["id"]}',{'field_mappings':other_mapping})
        assert mcp(client,'ontology_object_find',{'ontology_name':'runtime_other','object_name':'Device','fields':['temperature']})['rows']==[[11.0]]
        request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':other['id'],'name':'B transformed v2'})
        transformed=mcp(client,'ontology_object_find',{'ontology_name':'runtime_other','object_name':'Device',
            'fields':['id','temperature'],'filters':{'temperature':1.1}})
        assert transformed['rows']==[['b1',1.1]]
        physical=mcp(client,'ontology_complex_sql_execute',{'ontology_name':'runtime_other','sql':'SELECT SUM(temp) AS total FROM Device'})
        assert physical['items']==[{'total':11.0}] and physical['value_semantics']=='physical_source' and not physical['transform_applied']
        assert mcp(client,'ontology_get_attr_mapping',{'ontology_name':'runtime_other','object_names':['Device']})[0]['attribute_transforms']=={'temperature':'value / 10'}
        next(mapping for mapping in other_mapping if mapping['source_column']=='temp')['transform']='value * 2'
        request(client,'PUT',f'/object-bindings/{other_binding["id"]}',{'field_mappings':other_mapping})
        assert mcp(client,'ontology_object_find',{'ontology_name':'runtime_other','object_name':'Device','fields':['temperature']})['rows']==[[1.1]]
        ids={'ontology_id':oid,'entity_id':eid,'v1':v1['version_id'],'v2':v2['version_id'],'rollback':rollback['id'],'action_execution_id':performed['execution_id']}
    # Repeat actual production lifecycle; watcher + registry are recovered from persisted rows.
    for _ in range(2):
        with TestClient(app) as client:
            client.headers['Authorization']='Bearer '+token
            assert mcp(client,'ontology_run_logic',{'ontology_name':'runtime_review','logic_name':'risk','params':{'x':3}})['result']==7
            assert request(client,'GET',f'/ontology-api/objects/{eid}/d1')['status']=='repair'
    server.shutdown();server.server_close()
    smtp_server.shutdown();smtp_server.server_close();smtp_thread.join(2)
    destination=Path(os.environ.get('REVIEW_EVIDENCE_PATH', str(ROOT/'runtime-api-acceptance.json')))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'status':'passed','environment_root':str(ROOT),'ids':ids,'receipts':RECEIPTS,'smtp_receipts':SMTP_RECEIPTS,'checks':EVIDENCE},ensure_ascii=False,indent=2))
    print(json.dumps({'status':'passed','ids':ids,'checks':len(EVIDENCE),'evidence':str(destination)},ensure_ascii=False))

if __name__=='__main__': main()
