"""Actual isolated MySQL metadata migration and source commit/version acceptance.

Starts a new mysqld with --no-defaults and a disposable data directory. Never
connects to or stops an existing MySQL service. Credentials remain in memory.
"""
from pathlib import Path
import json
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import time

ROOT=Path(tempfile.mkdtemp(prefix='ontology-mysql-review-'))
REPO=Path(__file__).resolve().parents[2]
EVIDENCE=[]


def main():
    binary=shutil.which('mysqld')
    if not binary:raise RuntimeError('mysqld is required for this actual vendor integration')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    data=ROOT/'data';data.mkdir()
    init=subprocess.run([binary,'--no-defaults','--initialize-insecure',f'--datadir={data}'],capture_output=True,text=True,timeout=60)
    assert init.returncode==0,init.stderr
    log=(ROOT/'server.log').open('w')
    server=subprocess.Popen([binary,'--no-defaults',f'--datadir={data}',f'--socket={ROOT}/mysql.sock',f'--pid-file={ROOT}/mysql.pid',
        '--bind-address=127.0.0.1',f'--port={port}','--mysqlx=OFF','--skip-log-bin','--innodb-buffer-pool-size=64M'],stdout=log,stderr=log)
    password=secrets.token_hex(24)
    try:
        import pymysql
        admin=None
        for _ in range(150):
            if server.poll() is not None:raise RuntimeError((ROOT/'server.log').read_text())
            try:
                admin=pymysql.connect(host='127.0.0.1',port=port,user='root',connect_timeout=1);break
            except pymysql.MySQLError:time.sleep(.1)
        assert admin is not None,'Isolated server not ready'
        cursor=admin.cursor();cursor.execute('SELECT VERSION()');vendor_version=cursor.fetchone()[0]
        for database in ['review_metadata','review_upgrade','review_source']:
            cursor.execute(f'CREATE DATABASE {database} CHARACTER SET utf8mb4')
        cursor.execute("CREATE USER 'ontology_review'@'127.0.0.1' IDENTIFIED BY %s",(password,))
        for database in ['review_metadata','review_upgrade','review_source']:
            cursor.execute(f"GRANT ALL PRIVILEGES ON {database}.* TO 'ontology_review'@'127.0.0.1'")
        cursor.execute('CREATE TABLE review_source.devices (device_id VARCHAR(30) PRIMARY KEY, temp DOUBLE NOT NULL, status VARCHAR(30) NOT NULL)')
        cursor.execute("INSERT INTO review_source.devices VALUES ('d1',90,'alarm')");admin.commit()
        admin.close()
        os.environ.update(DATABASE_URL=f'mysql+pymysql://ontology_review:{password}@127.0.0.1:{port}/review_metadata',
            SECRET_KEY='isolated-mysql-review-key',ADMIN_INITIAL_PASSWORD='FixtureMysql2026',WORKSPACE_ROOT=str(ROOT/'workspace'),
            LOCAL_DATA_ROOT=str(ROOT/'local-data'),MONITOR_ENABLED='false',DATA_PLANE_REFRESH_ENABLED='false')
        from sqlalchemy import create_engine,text,inspect
        from app.database import Base
        import app.models
        from app.models import ScenarioDict,OntologyEntity
        from app.models.function import OntologyFunction
        from app.models.version import OntologyVersion,OntologyVersionEntity
        from app.models.version_components import OntologyVersionFunction
        from app.db_compat import ensure_legacy_schema_compat
        from app.migrations import run_startup_migrations
        from sqlalchemy.orm import Session
        upgrade=create_engine(f'mysql+pymysql://ontology_review:{password}@127.0.0.1:{port}/review_upgrade')
        Base.metadata.create_all(upgrade)
        with Session(upgrade) as db:
            db.add(ScenarioDict(id='legacy-onto',code='legacy',name='Legacy'));db.flush()
            db.add(OntologyEntity(id='legacy-entity',name='Device',name_cn='设备',tier=1,ontology_id='legacy-onto'));db.flush()
            db.add(OntologyVersion(id='legacy-version',name='Legacy v1',version_number=1,ontology_id='legacy-onto',status='published'));db.flush()
            db.add(OntologyVersionEntity(id='legacy-ve',version_id='legacy-version',source_entity_id='legacy-entity',name='Device',name_cn='设备',tier=1));db.flush()
            db.add(OntologyVersionFunction(id='legacy-fn',version_id='legacy-version',source_function_id='legacy-source',version_entity_id='legacy-ve',
                name='Legacy logic',callable_name='legacy_logic',logic_type='expression',logic_body='7'))
            db.add(OntologyFunction(id='existing-function',name='Existing function',callable_name='existing',entity_id='legacy-entity',logic_body='3'));db.commit()
        # Reconstruct the previous additive snapshot schema, keeping rows and
        # its original NOT NULL version_entity_id constraint.
        old_columns={'ontology_version_functions':['source_code','func_name','checksum','ontology_id','entity_ids'],
                     'ontology_versions':['components_frozen'],'ontology_version_entities':['binding_snapshot'],
                     'entity_relations':['source_field','target_field'],'ontology_version_relations':['source_field','target_field']}
        with upgrade.begin() as raw:
            for table,columns in old_columns.items():
                for column in columns:raw.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
            raw.execute(text('ALTER TABLE ontology_functions MODIFY is_derived_property BOOLEAN NULL DEFAULT NULL'))
            raw.execute(text('UPDATE ontology_functions SET is_derived_property=NULL'))
        for _ in range(2):
            ensure_legacy_schema_compat(upgrade);run_startup_migrations(upgrade)
        from app.services.version_component_snapshot import snapshot_components_for_version
        with Session(upgrade) as db:
            assert db.get(OntologyVersionFunction,'legacy-fn').logic_body=='7'
            assert db.get(OntologyFunction,'existing-function').is_derived_property is False
            assert not next(c for c in inspect(upgrade).get_columns('ontology_version_functions') if c['name']=='version_entity_id')['nullable']
            db.add(OntologyFunction(name='Ontology level',callable_name='ontology_level',ontology_id='legacy-onto',logic_body='9'));db.flush()
            version=OntologyVersion(name='Upgraded v2',version_number=2,ontology_id='legacy-onto',status='published');db.add(version);db.flush()
            db.add(OntologyVersionEntity(version_id=version.id,source_entity_id='legacy-entity',name='Device',name_cn='设备',tier=1));db.flush();db.expire(version,['entities'])
            counts=snapshot_components_for_version(db,version);db.commit()
            assert counts['functions_count']==2
            EVIDENCE.append({'check':'old MySQL schema migrated twice, rows/NOT NULL retained, ontology function published','functions_count':2})
        upgrade.dispose()
        from fastapi.testclient import TestClient
        from app.main import app
        def request(client,method,path,body=None,expected=200):
            response=client.request(method,'/api/v1'+path,json=body)
            assert response.status_code==expected,(path,response.status_code,response.text)
            result=response.json() if response.content else None
            # The connection and login carry credential material; evidence
            # records only their outcome and all subsequent business results.
            if path not in {'/auth/login','/connections'}:EVIDENCE.append({'method':method,'path':path,'status':response.status_code,'result':result})
            return result
        with TestClient(app) as client:
            auth=request(client,'POST','/auth/login',{'username':'admin','password':'FixtureMysql2026'});client.headers['Authorization']='Bearer '+auth['token']
            ontology=request(client,'POST','/scenarios',{'code':'mysql_review','name':'MySQL vendor integration'},201)
            connection=request(client,'POST','/connections',{'name':'Isolated vendor source','type':'mysql','host':'127.0.0.1','port':port,
                'database':'review_source','username':'ontology_review','password':password,'writable':True,'rate_limit_qps':10000},201)
            assert request(client,'POST',f'/connections/{connection["id"]}/test')['success']
            asset=request(client,'POST','/assets',{'name':'devices','kind':'table','connection_id':connection['id'],'locator':{'table':'devices'}},201)
            entity=request(client,'POST','/entities',{'name':'Device','name_cn':'设备','tier':1,'ontology_id':ontology['id'],'attributes':[
                {'name':'id','type':'string','required':True},{'name':'temperature','type':'number','required':True},{'name':'status','type':'string','required':True}]},201)
            mapping=[{'attribute_id':a['id'],'source_column':{'id':'device_id','temperature':'temp','status':'status'}[a['name']]} for a in entity['attributes']]
            request(client,'POST','/object-bindings',{'object_type_id':entity['id'],'asset_id':asset['id'],'id_column':'device_id','field_mappings':mapping},201)
            function=request(client,'POST','/functions',{'entity_id':entity['id'],'ontology_id':ontology['id'],'name':'risk','callable_name':'risk',
                'logic_type':'expression','logic_body':"params['temperature'] / 10",'input_schema':[{'name':'temperature','type':'number','required':True}]},201)
            sql=request(client,'POST','/functions',{'entity_id':entity['id'],'ontology_id':ontology['id'],'name':'read temp','callable_name':'read_temp',
                'logic_type':'sql','logic_body':'SELECT temp FROM devices WHERE device_id=:id','input_schema':[{'name':'id','type':'string','required':True}]},201)
            assert request(client,'POST',f'/functions/{sql["id"]}/test',{'params':{'id':'d1'}})['result']==90
            action=request(client,'POST','/actions',{'entity_id':entity['id'],'ontology_id':ontology['id'],'category':'domain','name':'repair','action_type':'modify_attribute',
                'type_config':{'target_entity_id':entity['id'],'target_attribute':'status','value_expression':'status'},
                'parameters_json':[{'name':'record_id','type':'string','required':True},{'name':'status','type':'string','required':True}]},201)
            first=request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':ontology['id'],'name':'MySQL v1'})
            query=request(client,'GET',f'/ontology-api/objects/{entity["id"]}?version_id={first["version_id"]}')
            assert query[0]['temperature']==90
            updated=request(client,'POST',f'/actions/{action["id"]}/execute',{'params':{'record_id':'d1','status':'repair'},'idempotency_key':'mysql-repair'})
            assert updated['success'] and updated['output']['instance']['status']=='repair'
            request(client,'PUT',f'/functions/{function["id"]}',{'logic_body':"params['temperature'] / 5"})
            second=request(client,'POST','/ontology-publish/quick-publish',{'ontology_id':ontology['id'],'name':'MySQL v2'})
            rollback=request(client,'POST',f'/ontology-publish/versions/{first["version_id"]}/rollback')
            request(client,'POST',f'/ontology-publish/versions/{rollback["id"]}/approve',{})
            protocol=request(client,'POST','/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{
                'name':'ontology_run_logic','arguments':{'ontology_name':'mysql_review','logic_name':'risk','params':{'temperature':90}}}})
            assert not protocol['result'].get('isError')
            assert json.loads(protocol['result']['content'][0]['text'])['result']==9
            with __import__('app.database',fromlist=['SessionLocal']).SessionLocal() as db:
                from app.services.function_executor import FunctionExecutor
                frozen=db.query(OntologyVersionFunction).filter_by(version_id=rollback['id'],callable_name='risk').one()
                result=FunctionExecutor(db).execute_snapshot(frozen,{'temperature':90});assert result.success and result.value==9
                EVIDENCE.append({'check':'actual MySQL rollback execution','v1':first['version_id'],'v2':second['version_id'],'rollback':rollback['id'],'risk':result.value})
        source=pymysql.connect(host='127.0.0.1',port=port,user='ontology_review',password=password,database='review_source')
        cursor=source.cursor();cursor.execute("SELECT temp,status FROM devices WHERE device_id='d1'");assert cursor.fetchone()==(90.0,'repair')
        cursor.execute("UPDATE devices SET temp=999 WHERE device_id='d1'");source.rollback()
        cursor.execute("SELECT temp FROM devices WHERE device_id='d1'");assert cursor.fetchone()[0]==90
        source.close();EVIDENCE.append({'check':'independent vendor source readback and transaction rollback','temperature':90,'status':'repair'})
        artifact=REPO/'docs/review/evidence/mysql-acceptance.json'
        artifact.write_text(json.dumps({'status':'passed','vendor':'MySQL','version':vendor_version,'isolated_root':str(ROOT),'port':port,'checks':EVIDENCE},ensure_ascii=False,indent=2))
        print(json.dumps({'status':'passed','vendor_version':vendor_version,'checks':len(EVIDENCE),'evidence':str(artifact)}))
    finally:
        server.terminate()
        try:server.wait(20)
        except subprocess.TimeoutExpired:server.kill();server.wait(5)
        log.close()


if __name__=='__main__':main()
