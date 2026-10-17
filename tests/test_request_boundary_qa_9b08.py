"""Independent actual provider-handler normalization tests using synthetic web/IPC ports.
No aiohttp installation, real network, Gateway, or model required.
"""
import asyncio
import base64
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import test_execution_budget as budget_fixture
import execution_boundary as eb
import provider_egress as pe
from recovery_inspector import _json


class Headers(dict):
    def getall(self,key,default=()):
        return [self[key]] if key in self else default


class Request:
    def __init__(self,body,token):
        self.raw=body if isinstance(body,str) else _json(body)
        self.content_type='application/json';self.content_length=len(self.raw.encode())
        self.headers=Headers(Authorization='Bearer '+token);self.query_string=''
    async def text(self):return self.raw


class BoundaryHarness:
    def __init__(self,case,record=False):
        self.f=budget_fixture.BudgetTests('test_no_network_authority_in_ticket')
        self.f.setUp();case.addCleanup(self.f.doCleanups)
        self.file=self.f.home/'input.txt';self.file.write_bytes(b'fixture')
        self.docs=[];self.response={'model':'test','choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':'ok'}}],
            'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}
        self.cfg={'policy':asdict(self.f.policy),'provider_bearer':'t'*48,
            'allowed_read_files':[str(self.file)],
            'provider_broker':{'socket_path':'/tmp/qa-boundary-9b08/egress.sock',
                'broker_id':'a'*32,'route_fingerprint':pe.route_fingerprint('http://127.0.0.1:19229/v1','test'),
                'signing_key':'b'*64}}
        self.boundary=eb.ExecutionBoundary(self.cfg)
        async def ready():return None
        self.boundary.require_ready=ready;self.boundary.ledger=lambda:self.f.ledger
        self.boundary.tools.register=lambda ctx:None;self.boundary.context=object()
        async def exchange(doc,ticket):
            self.docs.append(doc)
            return {'version':1,'brokerId':'a'*32,'nonce':ticket,'ok':True,'status':200,
                'contentType':'application/json','dataBase64':base64.b64encode(_json(self.response).encode()).decode()}
        self.boundary.broker._exchange=exchange
        self.routes={};router=SimpleNamespace(add_get=lambda p,f:self.routes.update({('GET',p):f}),
            add_post=lambda p,f:self.routes.update({('POST',p):f}))
        class App(dict):pass
        app=App();app.router=router
        self.web=ModuleType('aiohttp')
        self.web.web=SimpleNamespace(json_response=lambda body,status=200:SimpleNamespace(status=status,body=body),
            Response=lambda body,status,headers:SimpleNamespace(status=status,body=body,headers=headers))
        self.web.ClientSession=object;self.web.ClientTimeout=object
        self.module_patch=patch.dict(sys.modules,{'aiohttp':self.web});self.module_patch.start();case.addCleanup(self.module_patch.stop)
        self.boundary.bind(app,object())
    def send(self,body):
        return asyncio.run(self.routes[('POST',eb.PROVIDER_BASE+'/chat/completions')](Request(body,'t'*48)))


class RequestBoundaryIndependentQA(unittest.TestCase):
    def setUp(self):self.h=BoundaryHarness(self)
    def payload(self):return {'model':'test','messages':[{'role':'user','content':'α\r\nβ'}]}
    def test_default_output_ceiling_is_in_actual_authorized_payload(self):
        result=self.h.send(self.payload());self.assertEqual(result.status,200)
        doc=self.h.docs[0];self.assertEqual(doc['payload']['max_tokens'],20)
        self.assertEqual(doc['grant']['fingerprint'],pe.hashed(doc['payload']))
        self.assertNotEqual(doc['grant']['fingerprint'],pe.hashed(self.payload()))
    def test_explicit_ceiling_not_silently_replaced(self):
        body=self.payload()|{'max_tokens':7};self.assertEqual(self.h.send(body).status,200)
        self.assertEqual(self.h.docs[0]['payload']['max_tokens'],7)
    def test_duplicate_json_keys_refused_before_provider_claim(self):
        result=self.h.send('{"model":"test","model":"test","messages":[{"role":"user","content":"x"}]}')
        self.assertNotEqual(result.status,200);self.assertEqual(self.h.docs,[])
        self.assertEqual(self.h.f.ledger.snapshot()['providerCalls'],0)
    def test_hidden_multimodal_fetch_refused_without_claim(self):
        body={'model':'test','messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'http://invalid.invalid/private'}}]}]}
        result=self.h.send(body);self.assertNotEqual(result.status,200)
        self.assertEqual(self.h.docs,[]);self.assertEqual(self.h.f.ledger.snapshot()['providerCalls'],0)
    def test_provider_payload_preserves_exact_tool_text(self):
        text='{"content":"İşık\\r\\nβ😀","modelSeen":true}'
        body={'model':'test','messages':[{'role':'tool','tool_call_id':'opaque-id','content':text}]}
        result=self.h.send(body);self.assertEqual(result.status,200)
        self.assertEqual(self.h.docs[0]['payload']['messages'][0]['content'].encode(),text.encode())
    def test_auth_rejection_has_no_preparation_or_claim(self):
        req=Request(self.payload(),'not-authorized')
        result=asyncio.run(self.h.routes[('POST',eb.PROVIDER_BASE+'/chat/completions')](req))
        self.assertEqual(result.status,401);self.assertEqual(self.h.docs,[])
        self.assertEqual(self.h.f.ledger.snapshot()['providerCalls'],0)
