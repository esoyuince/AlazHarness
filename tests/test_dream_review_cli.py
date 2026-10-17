"""Dream D2 manual CLI tests; no network outside synthetic loopback."""
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
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('dream_review_once',ROOT/'scripts/dream_review_once.py')
cli=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def view(batch='a'*64):
    return {'version':1,'batchId':batch,'revision':'rv_'+'c'*64,
        'decisions':[],'evaluationStatus':'not_run','eventCount':0,
        'grantsExecutionPermission':False,'activeMemoryChanged':False,
        'conclusionVerified':False,'skillTransferVerified':False,
        'independentOutcomeVerified':False,'additionalModelCalls':0}


def diff(batch='a'*64):
    return {'version':1,'batchId':batch,'baseRevision':'rv_'+'d'*64,
        'currentRevision':'rv_'+'c'*64,'hasChanges':False,
        'newlyAcceptedForIndependentEvaluation':[],
        'promotableMemoryProposal':False,'activeMemoryChanged':False,
        'skillTransferVerified':False,'independentOutcomeVerified':False,
        'additionalModelCalls':0}


class ReviewClientTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.closed=0;self.http_status=200;self.response=view()
        self.connection={'base_url':'http://127.0.0.1:19372','token':'synthetic-private-token'}
        outer=self
        class Connection:
            def __init__(self,*args,**kwargs):pass
            def request(self,*args,**kwargs):outer.calls.append((args,kwargs))
            def getresponse(self):
                class Response:
                    def read(self,n):return json.dumps(outer.response).encode()
                Response.status=outer.http_status
                return Response()
            def close(self):outer.closed+=1
        p=patch.object(cli.http.client,'HTTPConnection',Connection)
        p.start();self.addCleanup(p.stop)

    def test_inspect_get_no_body_or_post(self):
        out=cli.invoke(self.connection,batch_id='a'*64)
        self.assertEqual(out['evaluationStatus'],'not_run')
        self.assertEqual(self.calls[0][0][0],'GET')
        self.assertEqual(self.closed,1)

    def test_decision_sends_one_body(self):
        cli.invoke(self.connection,batch_id='a'*64,operation='decide',
            candidate_id='dc_'+'b'*64,decision='accept_for_testing',
            reason_code='evidence_sufficient_to_test',expected_revision='rv_'+'c'*64)
        args,kw=self.calls[0]
        self.assertEqual(args[:2],('POST','/alaz/host/v1/dream/review'))
        self.assertEqual(json.loads(kw['body'])['decision'],'accept_for_testing')
        self.assertEqual(len(self.calls),1)

    def test_diff_no_model_charge(self):
        self.response=diff()
        result=cli.invoke(self.connection,batch_id='a'*64,
            operation='diff',base_revision='rv_'+'d'*64)
        self.assertFalse(result['hasChanges'])
        self.assertEqual(self.calls[0][0][:2],
                         ('POST','/alaz/host/v1/dream/review/diff'))

    def test_no_remote_host_or_proxy(self):
        for url in ['http://localhost:19372','https://example.com',
            'http://127.0.0.1:19372/x','http://u@127.0.0.1:19372',
            'http://127.0.0.1:19372?x=1']:
            with self.subTest(url=url),self.assertRaises(ValueError):
                cli.invoke(self.connection|{'base_url':url},batch_id='a'*64)
        self.assertEqual(self.calls,[])

    def test_no_header_in_credential(self):
        with self.assertRaises(ValueError):
            cli.invoke(self.connection|{'token':'secret\nHeader:fake'},batch_id='a'*64)
        self.assertEqual(self.calls,[])

    def test_invalid_batch_never_contacts(self):
        for bad in ('../private','',None,42,'b'*63):
            with self.subTest(value=bad),self.assertRaises(ValueError):
                cli.invoke(self.connection,batch_id=bad)
        self.assertEqual(self.calls,[])

    def test_invalid_decision_and_revision_never_contact(self):
        cases=[('bad','reject','conflict','rv_'+'c'*64),
               ('dc_'+'b'*64,'accept_for_testing','operator_deferred','rv_'+'c'*64),
               ('dc_'+'b'*64,'reject','conflict','bad')]
        for cid,action,reason,revision in cases:
            with self.subTest(case=action),self.assertRaises(ValueError):
                cli.invoke(self.connection,batch_id='a'*64,operation='decide',
                    candidate_id=cid,decision=action,reason_code=reason,
                    expected_revision=revision)
        self.assertEqual(self.calls,[])

    def test_operation_inconsistent_never_contacts(self):
        with self.assertRaises(ValueError):
            cli.invoke(self.connection,batch_id='a'*64,candidate_id='dc_'+'b'*64)
        self.assertEqual(self.calls,[])

    def test_http_error_never_auto_retries(self):
        self.http_status=409
        with self.assertRaises(ValueError):
            cli.invoke(self.connection,batch_id='a'*64)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.closed,1)

    def test_redirect_refused(self):
        self.http_status=302
        with self.assertRaises(ValueError):
            cli.invoke(self.connection,batch_id='a'*64)
        self.assertEqual(len(self.calls),1)

    def test_fake_privilege_rejected(self):
        for key in ('activeMemoryChanged','conclusionVerified','skillTransferVerified',
                    'independentOutcomeVerified','grantsExecutionPermission'):
            with self.subTest(key=key):
                self.response=view()|{key:True}
                with self.assertRaises(ValueError):
                    cli.invoke(self.connection,batch_id='a'*64)

    def test_fake_promotion_in_diff_refused(self):
        self.response=diff()|{'promotableMemoryProposal':True}
        with self.assertRaises(ValueError):
            cli.invoke(self.connection,batch_id='a'*64,operation='diff',
                       base_revision='rv_'+'d'*64)

    def test_disconnected_post_never_retried(self):
        class Disconnected:
            def __init__(this,*a,**kw):pass
            def request(this,*a,**kw):self.calls.append(a);raise ConnectionResetError('secret')
            def close(this):self.closed+=1
        with patch.object(cli.http.client,'HTTPConnection',Disconnected),self.assertRaises(ConnectionResetError):
            cli.invoke(self.connection,batch_id='a'*64,operation='decide',
                candidate_id='dc_'+'b'*64,decision='reject',reason_code='conflict',
                expected_revision='rv_'+'c'*64)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.closed,1)

    def test_real_subprocess_loopback_new_file_only(self):
        calls=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                calls.append(self.path)
                raw=json.dumps(view()).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                home=Path(tmp);conn=home/'connection.json';out=home/'result.json'
                conn.write_text(json.dumps({'base_url':'http://127.0.0.1:'+str(server.server_port),
                             'token':'synthetic-private-token'}))
                cmd=[sys.executable,'-B',str(ROOT/'scripts/dream_review_once.py'),
                     '--connection',str(conn),'--batch-id','a'*64,'--inspect',
                     '--output',str(out)]
                first=subprocess.run(cmd,capture_output=True,timeout=15)
                self.assertEqual(first.returncode,0,first.stderr)
                self.assertFalse(json.loads(out.read_text())['activeMemoryChanged'])
                before=out.read_bytes()
                second=subprocess.run(cmd,capture_output=True,timeout=15)
                self.assertEqual(second.returncode,2)
                self.assertEqual(out.read_bytes(),before)
                self.assertEqual(len(calls),1)
                self.assertNotIn(b'synthetic-private-token',second.stderr+second.stdout)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':
    unittest.main(verbosity=2)
