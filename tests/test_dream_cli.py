"""Manual Dream CLI tests: controlled HTTP port plus real loopback subprocess.
No Gateway/model/paid calls. Unknown transport is never automatically retried.
"""
import http.server
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dream_once',ROOT/'scripts/dream_once.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)

class DreamCLI(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.closed=0;self.http_status=200
        self.response={'version':1,'state':'completed','candidates':[],'activeMemoryChanged':False}
        self.connection={'base_url':'http://127.0.0.1:19351','token':'test-private-token'}
        outer=self
        class Connection:
            def __init__(self,*args,**kwargs):pass
            def request(self,*args,**kwargs):outer.calls.append((args,kwargs))
            def getresponse(self):
                class Response:
                    status=outer.http_status
                    def read(self,n):return json.dumps(outer.response).encode()
                return Response()
            def close(self):outer.closed+=1
        self.port=patch.object(cli.http.client,'HTTPConnection',Connection);self.port.start();self.addCleanup(self.port.stop)
    def test_post_exactly_once_and_closed(self):
        result=cli.invoke(self.connection,sources=[]);self.assertEqual(result['state'],'completed')
        self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0][0],('POST','/alaz/host/v1/dream'))
        self.assertEqual(json.loads(self.calls[0][1]['body']),{'sources':[]});self.assertEqual(self.closed,1)
    def test_status_get_not_post(self):
        cli.invoke(self.connection,batch_id='a'*64);self.assertEqual(self.calls[0][0][0],'GET')
    def test_unknown_202_is_not_completion(self):
        self.http_status=202;self.response['state']='unknown'
        self.assertEqual(cli.invoke(self.connection,sources=[])['state'],'unknown');self.assertEqual(len(self.calls),1)
    def test_redirect_is_refused_not_followed(self):
        self.http_status=302
        with self.assertRaises(ValueError):cli.invoke(self.connection,sources=[])
        self.assertEqual(len(self.calls),1);self.assertEqual(self.closed,1)
    def test_foreign_endpoints_not_contacted(self):
        for url in ['https://example.com','http://localhost:19351','http://127.0.0.1:19351/other','http://u@127.0.0.1:19351','http://127.0.0.1:19351?token=x']:
            with self.subTest(url=url),self.assertRaises(ValueError):cli.invoke(self.connection|{'base_url':url},sources=[])
        self.assertEqual(self.calls,[])
    def test_unknown_credential_shape_rejected(self):
        with self.assertRaises(ValueError):cli.invoke(self.connection|{'token':'test\r\nX:header'},sources=[])
        self.assertEqual(self.calls,[])
    def test_source_count_bound_before_contact(self):
        with self.assertRaises(ValueError):cli.invoke(self.connection,sources=[{}]*9)
        self.assertEqual(self.calls,[])
    def test_response_cannot_claim_active_memory_change(self):
        self.response['activeMemoryChanged']=True
        with self.assertRaises(ValueError):cli.invoke(self.connection,sources=[])
    def test_candidate_cannot_claim_active_memory(self):
        self.response['candidates']=[{'usableAsMemory':True}]
        with self.assertRaises(ValueError):cli.invoke(self.connection,sources=[])
    def test_invalid_batch_does_not_contact(self):
        with self.assertRaises(ValueError):cli.invoke(self.connection,batch_id='../private')
        self.assertEqual(self.calls,[])
    def test_disconnect_not_retried(self):
        class Disconnected:
            def __init__(this,*args,**kwargs):pass
            def request(this,*args,**kwargs):self.calls.append(args);raise ConnectionResetError('private transport detail')
            def close(this):self.closed+=1
        with patch.object(cli.http.client,'HTTPConnection',Disconnected),self.assertRaises(ConnectionResetError):
            cli.invoke(self.connection,sources=[])
        self.assertEqual(len(self.calls),1);self.assertEqual(self.closed,1)
    def test_real_cli_loopback_and_no_overwrite(self):
        self.port.stop()
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                calls.append(self.path);raw=json.dumps({'version':1,'state':'completed','candidates':[],'activeMemoryChanged':False}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);conn=root/'connection.json';out=root/'result.json'
                conn.write_text(json.dumps({'base_url':f'http://127.0.0.1:{server.server_port}','token':'local-synthetic-token'}))
                command=[sys.executable,'-B',str(ROOT/'scripts/dream_once.py'),'--connection',str(conn),'--batch-id','a'*64,'--output',str(out)]
                p=subprocess.run(command,capture_output=True,timeout=10)
                self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(out.read_text())['state'],'completed');before=out.read_bytes()
                p=subprocess.run(command,capture_output=True,timeout=10)
                self.assertEqual(p.returncode,2);self.assertEqual(out.read_bytes(),before);self.assertEqual(len(calls),1)
                self.assertNotIn(b'local-synthetic-token',p.stdout+p.stderr)
        finally:server.shutdown();server.server_close();thread.join(timeout=3)

if __name__=='__main__':unittest.main(verbosity=2)
