"""D2 HTTP boundary tests with real HostGate handlers and synthetic app."""
import asyncio
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import host_gate_plugin as hgp
from host_gate import HostGatePolicy
import test_evidence_view as fx
from recovery_inspector import _json
from execution_budget import ExecutionDenied


class Headers(dict):
    duplicate=False
    def getall(self,key,default=()):
        if key not in self:return default
        return [self[key],self[key]] if self.duplicate and key=='Authorization' else [self[key]]


class Request:
    def __init__(self,token,*,payload=None,method="POST",path=hgp.BASE+"/dream/review"):
        self.method=method
        self.path=path
        self.headers=Headers(Authorization="Bearer "+token)
        self.query_string=""
        self.content_type="application/json"
        self.charset="utf-8"
        self.match_info={"batch_id":"a"*64}
        self.raw=_json({"batchId":"a"*64,"candidateId":"dc_"+"b"*64,
                        "decision":"accept_for_testing",
                        "reasonCode":"evidence_sufficient_to_test",
                        "expectedRevision":"rv_"+"c"*64} if payload is None else payload)
        self.content_length=len(self.raw.encode())
    async def text(self):return self.raw


class ReviewHttpTests(unittest.TestCase):
    def setUp(self):
        self.f=fx.EvidenceViewTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.dream=SimpleNamespace(policy=SimpleNamespace(enabled=True),
            run=AsyncMock(return_value={"state":"completed","candidates":[],"activeMemoryChanged":False}),
            status=Mock(return_value={"state":"completed","candidates":[]}))
        self.review=SimpleNamespace(policy=SimpleNamespace(enabled=True),
            decide=Mock(return_value={"version":1,"reviewEventWritten":True,
                "grantsExecutionPermission":False,"activeMemoryChanged":False}),
            inspect=Mock(return_value={"version":1,"reviewedCount":0,
                "activeMemoryChanged":False}),
            diff=Mock(return_value={"version":1,"hasChanges":False,
                "independentEvaluationRequired":False,"activeMemoryChanged":False}))
        self.authority=SimpleNamespace(db=self.f.owner,epoch=self.f.context.epoch,
            retired=False,retiring=False)
        self.desc={"state":"ready","instance_id":self.f.context.instance_id}
        self.adapter=SimpleNamespace(_host="127.0.0.1",
            _room_grant_token=lambda request:None,
            _expected_api_key=lambda:self.f.context.api_token,
            gateway_runner=SimpleNamespace(
                session_authority=self.authority,
                session_runtime_descriptor=self.desc))
        self.execution=SimpleNamespace(bind=lambda app,adapter:None,
            require_ready=AsyncMock(),broker=object(),isolation=object())
        stub=ModuleType("aiohttp")
        stub.web=SimpleNamespace(middleware=lambda fn:fn,
            json_response=lambda data,status=200:SimpleNamespace(data=data,status=status))
        active=patch.dict(sys.modules,{"aiohttp":stub})
        active.start();self.addCleanup(active.stop)
        self.bind()

    def bind(self):
        self.routes={}
        class App(dict):
            frozen=False
        self.app=App()
        self.app.middlewares=[]
        self.app.router=SimpleNamespace(
            add_post=lambda path,handler:self.routes.update({("POST",path):handler}),
            add_get=lambda path,handler:self.routes.update({("GET",path):handler}))
        with patch.object(hgp,"validate_native_adapter",lambda adapter:None):
            hgp.bind_host_gate(self.app,self.adapter,
                HostGatePolicy(frozenset({"fixture-model"})),
                execution=self.execution,dream=self.dream,review=self.review)

    def req(self,**kwargs):return Request(self.f.context.api_token,**kwargs)

    def send(self,request,template=None):
        handler=self.routes[(request.method,template or request.path)]
        return asyncio.run(self.app.middlewares[0](request,handler))

    def test_review_post_calls_only_review(self):
        response=self.send(self.req())
        self.assertEqual(response.status,200)
        self.review.decide.assert_called_once_with(
            "a"*64,"dc_"+"b"*64,"accept_for_testing",
            "evidence_sufficient_to_test","rv_"+"c"*64)
        self.dream.run.assert_not_called()
        self.assertFalse(response.data["activeMemoryChanged"])

    def test_diff_gets_only_pinned_revision(self):
        payload={"batchId":"a"*64,"baseRevision":"rv_"+"d"*64}
        response=self.send(self.req(payload=payload,path=hgp.BASE+"/dream/review/diff"))
        self.assertEqual(response.status,200)
        self.review.diff.assert_called_once_with("a"*64,"rv_"+"d"*64)
        self.review.decide.assert_not_called()

    def test_status_get_requires_host_auth(self):
        request=Request("wrong",method="GET",path=hgp.BASE+"/dream/review/"+"a"*64)
        response=self.send(request,hgp.BASE+"/dream/review/{batch_id}")
        self.assertEqual(response.status,401)
        self.review.inspect.assert_not_called()

    def test_status_reads_by_batch_only(self):
        request=self.req(method="GET",path=hgp.BASE+"/dream/review/"+"a"*64)
        response=self.send(request,hgp.BASE+"/dream/review/{batch_id}")
        self.assertEqual(response.status,200)
        self.review.inspect.assert_called_once_with("a"*64)

    def test_duplicate_auth_refused(self):
        r=self.req()
        r.headers.duplicate=True
        response=self.send(r)
        self.assertEqual(response.status,401)
        self.review.decide.assert_not_called()

    def test_wrong_bearer_refused(self):
        response=self.send(Request("wrong"))
        self.assertEqual(response.status,401)
        self.review.decide.assert_not_called()

    def test_room_grant_not_review_privilege(self):
        self.adapter._room_grant_token=lambda _: "room-token"
        response=self.send(self.req())
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_profile_selector_header_refused(self):
        r=self.req()
        r.headers["X-Hermes-Profile"]="other"
        response=self.send(r)
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_query_parameter_refused(self):
        r=self.req();r.query_string="allow=all"
        response=self.send(r)
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_owner_retired_refused(self):
        self.authority.retired=True
        response=self.send(self.req())
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_unknown_payload_field_refused(self):
        r=self.req()
        payload=json.loads(r.raw)
        payload["promoteToMemory"]=True
        r.raw=_json(payload);r.content_length=len(r.raw.encode())
        response=self.send(r)
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_malformed_json_refused(self):
        r=self.req()
        r.raw='{"batchId":"x","batchId":"y"}'
        r.content_length=len(r.raw.encode())
        response=self.send(r)
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_compressed_body_refused(self):
        r=self.req()
        r.headers["Content-Encoding"]="gzip"
        response=self.send(r)
        self.assertGreaterEqual(response.status,400)
        self.review.decide.assert_not_called()

    def test_stale_revision_returns_not_success(self):
        self.review.decide.side_effect=ExecutionDenied("dream_review_revision_conflict")
        response=self.send(self.req())
        self.assertEqual(response.status,409)
        self.assertEqual(response.data["error"]["code"],"dream_review_revision_conflict")
        self.assertFalse(response.data["retryAllowed"])

    def test_disabled_review_registers_no_routes(self):
        self.review.policy.enabled=False
        self.bind()
        self.assertNotIn(("POST",hgp.BASE+"/dream/review"),self.routes)
        self.assertNotIn(("POST",hgp.BASE+"/dream/review/diff"),self.routes)
        self.assertNotIn(("GET",hgp.BASE+"/dream/review/{batch_id}"),self.routes)
        self.assertIn(("POST",hgp.BASE+"/dream"),self.routes)

    def test_capabilities_expose_no_automatic_promotion(self):
        result=self.send(self.req(method="GET",path=hgp.BASE+"/capabilities"))
        self.assertEqual(result.data["dreamReviewVersion"],1)
        self.assertEqual(result.data["dreamReviewMode"],"manual_for_testing_only")
        self.assertNotIn("dreamAutoPromote",result.data)

    def test_review_enabled_with_dream_disabled_route_has_no_dream_grant(self):
        self.review.policy.enabled=False
        self.dream.policy.enabled=False
        self.bind()
        self.assertNotIn(("POST",hgp.BASE+"/dream/review"),self.routes)
        self.assertNotIn(("POST",hgp.BASE+"/dream"),self.routes)

    def test_post_not_whitelisted_for_other_paths(self):
        r=self.req(path=hgp.BASE+"/dream/untrusted")
        handler=lambda request:None
        result=asyncio.run(self.app.middlewares[0](r,handler))
        self.assertEqual(result.status,409)
        self.review.decide.assert_not_called()


if __name__=="__main__":
    unittest.main(verbosity=2)
