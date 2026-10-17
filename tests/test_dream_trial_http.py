"""D2B2 HostGate route tests. Synthetic app/native context, no live Gateway."""
from __future__ import annotations
import asyncio
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import AsyncMock,Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import host_gate_plugin as hgp
from host_gate import HostGatePolicy
from recovery_inspector import _json
from execution_budget import ExecutionDenied
import test_evidence_view as evidence_fixture
from test_dream_eval import fixture


class Headers(dict):
    duplicate=False
    def getall(self,key,default=()):
        if key not in self:return default
        if self.duplicate:return [self[key],self[key]]
        return [self[key]]


class Request:
    def __init__(self,token,*,method="POST",path=hgp.BASE+"/dream/trial",body=None):
        self.headers=Headers(Authorization="Bearer "+token)
        self.method=method;self.path=path;self.query_string=""
        self.content_type="application/json";self.charset="utf-8"
        self.raw=_json({"plan":fixture()[4]} if body is None else body)
        self.content_length=len(self.raw.encode())
        self.match_info={"plan_id":fixture()[4]["planId"]}
    async def text(self):return self.raw


class TrialHTTP(unittest.TestCase):
    def setUp(self):
        self.f=evidence_fixture.EvidenceViewTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.plan=fixture()[4]
        self.dream=SimpleNamespace(policy=SimpleNamespace(enabled=True),
                                   run=AsyncMock(),status=Mock())
        self.review=SimpleNamespace(policy=SimpleNamespace(enabled=True),
                                    decide=Mock(),inspect=Mock(),diff=Mock())
        self.trial=SimpleNamespace(policy=SimpleNamespace(enabled=True),
                 run=AsyncMock(return_value={"state":"completed","planId":self.plan["planId"],
                       "realModelExecutionVerified":False,"activeMemoryChanged":False}),
                 status=Mock(return_value={"state":"completed","planId":self.plan["planId"],
                       "realModelExecutionVerified":False,"activeMemoryChanged":False}))
        self.authority=SimpleNamespace(db=self.f.owner,epoch=self.f.context.epoch,retired=False,retiring=False)
        self.desc={"state":"ready","instance_id":self.f.context.instance_id}
        self.adapter=SimpleNamespace(_host="127.0.0.1",_room_grant_token=lambda req:None,
          _expected_api_key=lambda:self.f.context.api_token,gateway_runner=SimpleNamespace(
          session_authority=self.authority,session_runtime_descriptor=self.desc))
        self.execution=SimpleNamespace(bind=lambda app,adapter:None,require_ready=AsyncMock(),
                                      broker=object(),isolation=object())
        module=ModuleType("aiohttp")
        module.web=SimpleNamespace(middleware=lambda fn:fn,
                       json_response=lambda data,status=200:SimpleNamespace(data=data,status=status))
        mocked=patch.dict(sys.modules,{"aiohttp":module})
        mocked.start();self.addCleanup(mocked.stop)
        self.bind()

    def bind(self):
        self.routes={}
        class App(dict):
            frozen=False
        self.app=App();self.app.middlewares=[]
        self.app.router=SimpleNamespace(
             add_post=lambda route,fn:self.routes.update({("POST",route):fn}),
             add_get=lambda route,fn:self.routes.update({("GET",route):fn}))
        with patch.object(hgp,'validate_native_adapter',lambda adapter:None):
            hgp.bind_host_gate(self.app,self.adapter,
              HostGatePolicy(frozenset({"fixture-model"})),
              execution=self.execution,dream=self.dream,review=self.review,trial=self.trial)

    def send(self,req,*,template=None):
        handler=self.routes[(req.method,template or req.path)]
        return asyncio.run(self.app.middlewares[0](req,handler))

    def request(self,**kwargs):
        return Request(self.f.context.api_token,**kwargs)

    def test_authorized_trial_exact_plan(self):
        result=self.send(self.request())
        self.assertEqual(result.status,200)
        self.trial.run.assert_awaited_once_with(self.plan)
        self.assertFalse(result.data['realModelExecutionVerified'])

    def test_pending_or_unknown_not_200(self):
        self.trial.run.return_value={'state':'unknown','results':[]}
        self.assertEqual(self.send(self.request()).status,202)

    def test_status_requires_exact_same_host_bearer(self):
        r=Request('bad',method='GET',path=hgp.BASE+'/dream/trial/'+self.plan['planId'])
        result=self.send(r,template=hgp.BASE+'/dream/trial/{plan_id}')
        self.assertEqual(result.status,401)
        self.trial.status.assert_not_called()

    def test_status_passes_only_plan_id(self):
        r=self.request(method='GET',path=hgp.BASE+'/dream/trial/'+self.plan['planId'])
        result=self.send(r,template=hgp.BASE+'/dream/trial/{plan_id}')
        self.assertEqual(result.status,200)
        self.trial.status.assert_called_once_with(self.plan['planId'])

    def test_room_token_cannot_trigger_trial(self):
        self.adapter._room_grant_token=lambda _: 'room-secret'
        r=self.send(self.request())
        self.assertGreaterEqual(r.status,400)
        self.trial.run.assert_not_called()

    def test_profile_header_cannot_cross_scopes(self):
        r=self.request();r.headers['X-Hermes-Profile']='other'
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_query_cannot_override_safety(self):
        r=self.request();r.query_string='allow=true'
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_duplicate_authorization_refused(self):
        r=self.request();r.headers.duplicate=True
        self.assertEqual(self.send(r).status,401)
        self.trial.run.assert_not_called()

    def test_retired_native_owner_refused(self):
        self.authority.retired=True
        self.assertGreaterEqual(self.send(self.request()).status,400)
        self.trial.run.assert_not_called()

    def test_unsupported_body_fields_rejected(self):
        r=self.request(body={'plan':self.plan,'promoteMemory':True})
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_duplicate_json_keys_refused(self):
        r=self.request();r.raw='{"plan":{},"plan":{}}';r.content_length=len(r.raw)
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_bad_content_encoding_refused(self):
        r=self.request();r.headers['Content-Encoding']='gzip'
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_large_body_refused(self):
        r=self.request();r.content_length=131073
        self.assertGreaterEqual(self.send(r).status,400)
        self.trial.run.assert_not_called()

    def test_disabled_trial_not_registered(self):
        self.trial.policy.enabled=False;self.bind()
        self.assertNotIn(('POST',hgp.BASE+'/dream/trial'),self.routes)
        self.assertNotIn(('GET',hgp.BASE+'/dream/trial/{plan_id}'),self.routes)
        self.assertIn(('POST',hgp.BASE+'/dream'),self.routes)

    def test_capability_nonlearning_mode(self):
        r=self.request(method='GET',path=hgp.BASE+'/capabilities')
        v=self.send(r)
        self.assertEqual(v.data.get('dreamTrialVersion'),1)
        self.assertEqual(v.data.get('dreamTrialMode'),'manual_paired_broker_evidence_only')
        self.assertNotIn('skillPromotion',v.data)

    def test_unlisted_post_not_allowed(self):
        r=self.request(path=hgp.BASE+'/dream/trial/scheduler')
        v=asyncio.run(self.app.middlewares[0](r,lambda _:None))
        self.assertEqual(v.status,409)
        self.trial.run.assert_not_called()

    def test_missing_profile_get_error_is_not_authorized_inference(self):
        self.trial.status.side_effect=ExecutionDenied('dream_trial_not_found')
        r=self.request(method='GET',path=hgp.BASE+'/dream/trial/'+self.plan['planId'])
        out=self.send(r,template=hgp.BASE+'/dream/trial/{plan_id}')
        self.assertEqual(out.status,409)
        self.assertEqual(out.data['error']['code'],'dream_trial_not_found')


if __name__=='__main__':
    unittest.main(verbosity=2)
