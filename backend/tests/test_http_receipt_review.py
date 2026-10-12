"""Actual HTTP receipts distinguish a business rejection from lost confirmation."""
import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.services.action_executors import get_executor


@pytest.fixture
def receipt_server():
    responses = {
        '/gateway': (502, None),
        '/unavailable': (503, None),
        '/timeout': (504, None),
        '/rejected': (503, {'success':False,'message':'No work was accepted'}),
        '/uncertain': (200, {'success':False,'output':{'outcome':'unknown'}}),
    }
    accepted = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            accepted.append((self.path, self.rfile.read(int(self.headers.get('Content-Length',0)))))
            status, body = responses[self.path]
            payload = b'' if body is None else json.dumps(body).encode()
            self.send_response(status);self.send_header('Content-Length',str(len(payload)));self.end_headers()
            self.wfile.write(payload)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}', accepted
    finally:server.shutdown();thread.join();server.server_close()


@pytest.mark.parametrize('executor_type',['api_call','notification'])
@pytest.mark.parametrize('path,outcome',[('/gateway','unknown'),('/unavailable','unknown'),('/timeout','unknown'),('/rejected','failed'),('/uncertain','unknown')])
def test_receipt_outcome_after_actual_post(executor_type,path,outcome,receipt_server):
    url,accepted=receipt_server
    engine=create_engine('sqlite:///:memory:');Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            executor=get_executor(executor_type,db=db)
            config=({'url':url+path,'method':'POST','body':{'ticket':'t1'}} if executor_type=='api_call' else
                    {'channel':'webhook','webhook_url':url+path,'recipient':'fixture','message_template':'A submitted work order'})
            result=asyncio.run(executor.execute(config,{}))
            assert not result.success
            assert result.output.get('outcome','failed')==outcome
            assert len(accepted)==1 and accepted[0][0]==path
            if outcome=='unknown':assert '禁止自动重试' in result.message
    finally:engine.dispose()
