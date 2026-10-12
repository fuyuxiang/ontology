"""Actual isolated Unix start/stop/code-server and non-destructive CLI init."""
from pathlib import Path
import os
import json
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import httpx

REPO=Path(__file__).resolve().parents[2]
ROOT=Path(tempfile.mkdtemp(prefix='ontology-startup-acceptance-'))
EVIDENCE=[]
DOCUMENT={'text':'scheduled document revision one','requests':0}


class DocumentSource(BaseHTTPRequestHandler):
    def do_GET(self):
        DOCUMENT['requests']+=1
        body=DOCUMENT['text'].encode()
        self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass


def port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1',0));return connection.getsockname()[1]


def command(args, cwd=ROOT, timeout=150, expected=0):
    environment=dict(os.environ)
    extra_dependencies=os.environ.get('REVIEW_DEPENDENCY_PATH')
    if not extra_dependencies and Path('/private/tmp/ontology-review-deps').is_dir():extra_dependencies='/private/tmp/ontology-review-deps'
    if extra_dependencies:environment['PYTHONPATH']=extra_dependencies+os.pathsep+environment.get('PYTHONPATH','')
    result=subprocess.run(args,cwd=cwd,env=environment,capture_output=True,text=True,timeout=timeout)
    EVIDENCE.append({'command':args,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==expected,(args,result.returncode,result.stdout,result.stderr)
    return result


def main():
    for name in ('backend','frontend','scripts','code-server'):
        shutil.copytree(REPO/name,ROOT/name,ignore=shutil.ignore_patterns('node_modules','venv','.venv','dist','__pycache__','*.db','*.sqlite','.DS_Store'))
    for name in ('start.sh','stop.sh','ctl.ps1','ctl.bat','start.bat','stop.bat'):shutil.copy2(REPO/name,ROOT/name)
    dependencies=ROOT/'frontend/node_modules';dependencies.mkdir()
    for package in (REPO/'frontend/node_modules').iterdir():
        if package.name not in {'.vite','.vite-temp'}:(dependencies/package.name).symlink_to(package,target_is_directory=package.is_dir())
    backend,frontend,editor=port(),port(),port()
    settings={'DATABASE_URL':f'sqlite:///{ROOT}/metadata.sqlite','SECRET_KEY':'isolated-startup-key','ADMIN_INITIAL_PASSWORD':'FixtureStartup2026',
        'WORKSPACE_ROOT':str(ROOT/'workspace'),'LOCAL_DATA_ROOT':str(ROOT/'local-data'),'PORT':str(backend),
        'FRONTEND_PORT':str(frontend),'CODE_SERVER_PORT':str(editor),'MONITOR_ENABLED':'false',
        'SKIP_DEPENDENCY_INSTALL':'1','SKIP_EXTENSION_INSTALL':'1','CORS_ORIGINS':f'http://127.0.0.1:{frontend}'}
    (ROOT/'.env').write_text('\n'.join(f'{key}={value}' for key,value in settings.items())+'\n');(ROOT/'.env').chmod(0o600)
    # The CLI uses the same .env as production. It must seed a clean database
    # and keep user-created data when rerun.
    command(['python3','init_db.py'],cwd=ROOT/'backend')
    document_server=ThreadingHTTPServer(('127.0.0.1',0),DocumentSource)
    document_thread=threading.Thread(target=document_server.serve_forever,daemon=True);document_thread.start()
    try:
        command(['bash','start.sh'])
        with httpx.Client(base_url=f'http://127.0.0.1:{frontend}',timeout=10,follow_redirects=True) as ui:
            page=ui.get('/');assert page.status_code==200 and '/src/main.ts' in page.text
            health=ui.get('/api/health');assert health.status_code==200 and health.json()['status']=='ok'
            assert health.json()['components']['data_refresh'] is True
            EVIDENCE.append({'check':'production startup readiness including actual data refresher','health':health.json()})
            login=ui.post('/api/v1/auth/login',json={'username':'admin','password':settings['ADMIN_INITIAL_PASSWORD']})
            assert login.status_code==200,login.text
            ui.headers['Authorization']='Bearer '+login.json()['token']
            ontology=ui.post('/api/v1/scenarios',json={'code':'startup_saved','name':'Startup persisted fixture'})
            assert ontology.status_code==201,ontology.text
            EVIDENCE.append({'check':'real frontend proxy auth and create','status':ontology.status_code,'ontology':ontology.json()})
            document=ui.post('/api/v1/assets/document/api',json={'name':'Real scheduled source','api_url':f'http://127.0.0.1:{document_server.server_port}/document','poll_interval':10})
            assert document.status_code==201,document.text
            asset=document.json();assert asset['parsed_summary']==DOCUMENT['text']
            before=DOCUMENT['requests'];DOCUMENT['text']='scheduled document revision two'
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                current=ui.get('/api/v1/assets/'+asset['id']);assert current.status_code==200,current.text
                state=current.json();refresh=(state.get('profile') or {}).get('source_refresh') or {}
                if state['parsed_summary']==DOCUMENT['text'] and refresh.get('last_success') and DOCUMENT['requests']>before:break
                time.sleep(.25)
            else:raise AssertionError('Production scheduled refresher did not consume the changed real HTTP document')
            EVIDENCE.append({'check':'production scheduled refresher reads changed actual HTTP source and persists result',
                'asset_id':asset['id'],'parsed_summary':state['parsed_summary'],'source_refresh':refresh,'source_requests':DOCUMENT['requests']})
        with httpx.Client(base_url=f'http://127.0.0.1:{editor}',timeout=10,follow_redirects=False) as code:
            health=code.get('/healthz');assert health.status_code==200
            unauthed=code.get('/');assert unauthed.status_code in (302,303) and '/login' in unauthed.headers['location']
            password=(ROOT/'.code-server-password').read_text().strip()
            authenticated=code.post('/login',data={'password':password});assert authenticated.status_code in (302,303)
            workbench=code.get('/',params={'folder':str(ROOT/'workspace')});assert workbench.status_code==200 and 'workbench' in workbench.text.lower()
            EVIDENCE.append({'check':'real isolated code-server password/auth/workspace','unauthenticated_status':unauthed.status_code,
                             'authenticated_status':workbench.status_code,'health':health.json()})
        command(['bash','stop.sh'])
        for number in (backend,frontend,editor):
            with socket.socket() as probe:assert probe.connect_ex(('127.0.0.1',number))!=0
        command(['python3','init_db.py'],cwd=ROOT/'backend')
        with sqlite3.connect(ROOT/'metadata.sqlite') as raw:
            assert raw.execute("SELECT COUNT(*) FROM scenario_dict WHERE code='startup_saved'").fetchone()[0]==1
            assert raw.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0]==1
        command(['bash','start.sh'])
        response=httpx.post(f'http://127.0.0.1:{frontend}/api/v1/auth/login',json={'username':'admin','password':settings['ADMIN_INITIAL_PASSWORD']});assert response.status_code==200
        saved=httpx.get(f'http://127.0.0.1:{frontend}/api/v1/scenarios',headers={'Authorization':'Bearer '+response.json()['token']})
        assert any(item['code']=='startup_saved' for item in saved.json())
        command(['bash','stop.sh'])
        # A foreign process with a forged/stale legacy PID file must survive
        # stop; an occupied backend port must cause start to fail safely.
        foreign_port=port()
        foreign=subprocess.Popen(['python3','-m','http.server',str(foreign_port),'--bind','127.0.0.1'],cwd='/private/tmp',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    if httpx.get(f'http://127.0.0.1:{foreign_port}').status_code==200:break
                except httpx.ConnectError:time.sleep(.05)
            (ROOT/'.backend.pid').write_text(str(foreign.pid))
            command(['bash','stop.sh']);assert foreign.poll() is None
            original=(ROOT/'.env').read_text();(ROOT/'.env').write_text(original.replace(f'PORT={backend}',f'PORT={foreign_port}'))
            command(['bash','start.sh'],expected=1);assert foreign.poll() is None
            EVIDENCE.append({'check':'foreign listener preserved through stop and conflicting start','foreign_port':foreign_port,'preserved':True})
            (ROOT/'.env').write_text(original)
        finally:
            foreign.terminate();foreign.wait(5)
    finally:
        command(['bash','stop.sh'])
        document_server.shutdown();document_server.server_close();document_thread.join(5)
    artifact=Path(os.environ.get('REVIEW_EVIDENCE_PATH', str(ROOT/'startup-acceptance.json')))
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({'status':'passed','isolated_root':str(ROOT),'ports':{'backend':backend,'frontend':frontend,'editor':editor},'checks':EVIDENCE},ensure_ascii=False,indent=2))
    print(json.dumps({'status':'passed','checks':len(EVIDENCE),'evidence':str(artifact)}))


if __name__=='__main__':main()
