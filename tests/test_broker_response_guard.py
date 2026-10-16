"""Response confidentiality/transport tests with synthetic aiohttp ports, not live network."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from provider_broker import ProviderBrokerServer
from provider_egress import BrokerConfig
from execution_budget import ExecutionDenied
SECRET='p'*48

class ReplyTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self,raw,status=200,ctype='application/json',extra_headers=None):
        self.calls=[];self.options=[];self.connectors=[]
        owner=self
        class Response:
            headers={'Content-Type':ctype}|(extra_headers or {})
            def __init__(self):self.status=status;self.content=self
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            async def iter_chunked(self,n):
                for i in range(0,len(raw),137):yield raw[i:i+137]
        class Session:
            def __init__(self,**kw):owner.options.append(kw)
            async def __aenter__(self):return self
            async def __aexit__(self,*a):pass
            def post(self,url,**kw):owner.calls.append((url,kw));return Response()
        def connector(**kw):owner.connectors.append(kw);return 'connector'
        fake=SimpleNamespace(ClientSession=Session,ClientTimeout=lambda **kw:kw,TCPConnector=connector)
        db=str((Path.cwd()/'state.db').resolve())
        cfg=BrokerConfig('http://127.0.0.1:19777/v1','fixture',SECRET,'b'*64,db,'a'*64,'c'*64,'d'*64)
        broker=ProviderBrokerServer(cfg,Path('/tmp/not-started'))
        with patch.dict(sys.modules,{'aiohttp':fake}):return await broker._upstream({'model':'fixture','messages':[{'role':'user','content':'hello'}]})
    async def test_normal_json_unchanged(self):
        raw=b'{"model":"fixture","choices":[]}'
        self.assertEqual(await self.invoke(raw),(raw,200,'application/json'))
    async def test_raw_credential_not_returned(self):
        with self.assertRaisesRegex(ExecutionDenied,'broker_sensitive_response'):await self.invoke(json.dumps({'value':SECRET}).encode())
    async def test_escaped_json_credential_not_returned(self):
        raw=b'{"value":"'+b'\\u0070'*48+b'"}'
        self.assertNotIn(SECRET.encode(),raw)
        with self.assertRaisesRegex(ExecutionDenied,'broker_sensitive_response'):await self.invoke(raw)
    async def test_escaped_json_key_not_returned(self):
        raw=b'{"'+b'\\u0070'*48+b'":"value"}'
        with self.assertRaisesRegex(ExecutionDenied,'broker_sensitive_response'):await self.invoke(raw)
    async def test_escaped_sse_credential_not_returned(self):
        raw=b'data: {"content":"'+b'\\u0070'*48+b'"}\n\ndata: [DONE]\n\n'
        with self.assertRaisesRegex(ExecutionDenied,'broker_sensitive_response'):await self.invoke(raw,ctype='text/event-stream')
    async def test_sse_split_content_not_returned(self):
        raw=('data: '+json.dumps({'choices':[{'delta':{'content':'p'*24}}]})+'\n\n')*2+'data: [DONE]\n\n'
        with self.assertRaisesRegex(ExecutionDenied,'broker_sensitive_response'):await self.invoke(raw.encode(),ctype='text/event-stream')
    async def test_normal_sse_unchanged(self):
        raw=b'data: {"choices":[{"delta":{"content":"safe"}}]}\n\ndata: [DONE]\n\n'
        self.assertEqual(await self.invoke(raw,ctype='text/event-stream'),(raw,200,'text/event-stream'))
    async def test_error_body_and_headers_not_forwarded(self):
        answer=await self.invoke(SECRET.encode(),status=503,extra_headers={'Set-Cookie':SECRET,'Location':SECRET})
        self.assertEqual(answer,(b'{}',503,'application/json'))
    async def test_redirect_refused_no_second_call(self):
        with self.assertRaisesRegex(ExecutionDenied,'provider_redirect_refused'):await self.invoke(b'',status=307,extra_headers={'Location':'http://other/'})
        self.assertEqual(len(self.calls),1);self.assertIs(self.calls[0][1]['allow_redirects'],False)
    async def test_fixed_credential_and_target_only(self):
        await self.invoke(b'{}');url,args=self.calls[0]
        self.assertEqual(url,'http://127.0.0.1:19777/v1/chat/completions')
        self.assertEqual(args['headers'],{'Authorization':'Bearer '+SECRET,'Content-Type':'application/json'})
        self.assertIs(self.options[0]['trust_env'],False);self.assertIs(self.options[0]['auto_decompress'],False)
    async def test_encoded_upstream_refused(self):
        with self.assertRaises(ExecutionDenied):await self.invoke(b'{}',extra_headers={'Content-Encoding':'gzip'})
    async def test_unrecognized_type_refused(self):
        with self.assertRaises(ExecutionDenied):await self.invoke(b'{}',ctype='text/html')
    async def test_invalid_json_refused(self):
        with self.assertRaises(ExecutionDenied):await self.invoke(b'{broken')
    async def test_json_duplicate_keys_refused(self):
        with self.assertRaises(ExecutionDenied):await self.invoke(b'{"x":"a","x":"b"}')
    async def test_incomplete_sse_refused(self):
        with self.assertRaises(ExecutionDenied):await self.invoke(b'data: {"x":"a"}\n\n',ctype='text/event-stream')

if __name__=='__main__':unittest.main()
