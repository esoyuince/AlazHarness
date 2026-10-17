"""Independent actual Dream HTTP route handlers with synthetic app/native/service ports.
Explicit source via ALAZ_DREAM_QA_SOURCE. No server, inference, real tool or install.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import AsyncMock,Mock,patch
TARGET=Path(os.environ['ALAZ_DREAM_QA_SOURCE']).resolve()
sys.path[:0]=[str(TARGET/'packages/claw-hermes'),str(TARGET/'tests')]
import host_gate_plugin as hgp
from host_gate import HostGatePolicy
import test_evidence_view as fixture
from recovery_inspector import _json
assert Path(hgp.__file__).resolve().is_relative_to(TARGET)

class Headers(dict):
    duplicate=False
    def getall(self,key,default=()):
        if key not in self:return default
        return [self[key],self[key]] if self.duplicate and key=='Authorization' else [self[key]]

class Request:
    def __init__(self,token,payload=None,method='POST',path=hgp.BASE+'/dream'):
        self.headers=Headers(Authorization='Bearer '+token)
        self.path=path;self.method=method;self.query_string='';self.content_type='application/json';self.charset='utf-8'
        self.raw=_json({'sources':[]} if payload is None else payload)
        self.content_length=len(self.raw.encode());self.match_info={'batch_id':'a'*64}
    async def text(self):return self.raw

class DreamHTTPIndependentQA(unittest.TestCase):
    def setUp(self):
        self.f=fixture.EvidenceViewTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.dream=SimpleNamespace(policy=SimpleNamespace(enabled=True),
            run=AsyncMock(return_value={'state':'completed','candidates':[],'activeMemoryChanged':False}),
            status=Mock(return_value={'state':'completed','candidates':[]}))
        self.authority=SimpleNamespace(db=self.f.owner,epoch=self.f.context.epoch,retired=False,retiring=False)
        self.desc={'state':'ready','instance_id':self.f.context.instance_id}
        self.adapter=SimpleNamespace(_host='127.0.0.1',_room_grant_token=lambda request:None,
            _expected_api_key=lambda:self.f.context.api_token,
            gateway_runner=SimpleNamespace(session_authority=self.authority,session_runtime_descriptor=self.desc))
        self.execution=SimpleNamespace(bind=lambda app,adapter:None,require_ready=AsyncMock(),broker=object(),isolation=object())
        module=ModuleType('aiohttp');module.web=SimpleNamespace(middleware=lambda fn:fn,
            json_response=lambda data,status=200:SimpleNamespace(data=data,status=status))
        install=patch.dict(sys.modules,{'aiohttp':module});install.start();self.addCleanup(install.stop)
        self.bind()

    def bind(self):
        self.routes={}
        class App(dict):
            frozen=False
        self.app=App();self.app.middlewares=[]
        self.app.router=SimpleNamespace(add_post=lambda path,fn:self.routes.update({('POST',path):fn}),
            add_get=lambda path,fn:self.routes.update({('GET',path):fn}))
        with patch.object(hgp,'validate_native_adapter',lambda adapter:None):
            hgp.bind_host_gate(self.app,self.adapter,HostGatePolicy(frozenset({'fixture-model'})),
                               execution=self.execution,dream=self.dream)

    def request(self,**kwargs):return Request(self.f.context.api_token,**kwargs)
    def send(self,r=None,route=None):
        r=r or self.request()
        handler=self.routes[(r.method,route or r.path)]
        return asyncio.run(self.app.middlewares[0](r,handler))
    def refused(self,r):
        response=self.send(r);self.assertGreaterEqual(response.status,400)
        self.dream.run.assert_not_called();return response

    def test_authorized_explicit_post_reaches_service_once(self):
        response=self.send();self.assertEqual(response.status,200)
        self.dream.run.assert_awaited_once_with([])

    def test_wrong_bearer_cannot_start_dream(self):
        response=self.refused(Request('wrong'));self.assertEqual(response.status,401)

    def test_duplicate_auth_headers_are_rejected(self):
        r=self.request();r.headers.duplicate=True;self.refused(r)

    def test_room_grant_is_not_host_authority(self):
        self.adapter._room_grant_token=lambda request:'room-grant';self.refused(self.request())

    def test_profile_header_cannot_select_other_memory(self):
        r=self.request();r.headers['X-Hermes-Profile']='other';self.refused(r)

    def test_query_parameters_are_not_accepted_as_authority(self):
        r=self.request();r.query_string='profile=other';self.refused(r)

    def test_retired_owner_cannot_start_dream(self):
        self.authority.retired=True;self.refused(self.request())

    def test_compressed_body_is_rejected(self):
        r=self.request();r.headers['Content-Encoding']='gzip';self.refused(r)

    def test_oversized_body_is_rejected_before_read(self):
        r=self.request();r.content_length=131073;self.refused(r)

    def test_duplicate_json_fields_are_rejected(self):
        r=self.request();r.raw='{"sources":[],"sources":[]}';r.content_length=len(r.raw)
        self.refused(r)

    def test_extra_settings_in_payload_cannot_enable_memory_writes(self):
        r=self.request(payload={'sources':[],'enabled':True,'memory_write':True});self.refused(r)

    def test_unknown_outcome_is_202_not_completion(self):
        self.dream.run.return_value={'state':'unknown','candidates':[]}
        self.assertEqual(self.send().status,202)

    def test_rejected_candidate_is_422_not_completion(self):
        self.dream.run.return_value={'state':'rejected','candidates':[]}
        self.assertEqual(self.send().status,422)

    def test_status_endpoint_also_requires_host_bearer(self):
        r=Request('wrong',method='GET',path=hgp.BASE+'/dream/'+'a'*64)
        result=self.send(r,route=hgp.BASE+'/dream/{batch_id}')
        self.assertEqual(result.status,401);self.dream.status.assert_not_called()

    def test_disabled_service_registers_no_dream_routes(self):
        self.dream.policy.enabled=False;self.bind()
        self.assertNotIn(('POST',hgp.BASE+'/dream'),self.routes)
        self.assertNotIn(('GET',hgp.BASE+'/dream/{batch_id}'),self.routes)

    def test_capability_explicitly_reports_manual_candidate_mode(self):
        r=self.request(method='GET',path=hgp.BASE+'/capabilities');result=self.send(r)
        self.assertEqual(result.data['dreamVersion'],1)
        self.assertEqual(result.data['dreamMode'],'manual_candidates_only')

if __name__=='__main__':unittest.main(verbosity=2)
