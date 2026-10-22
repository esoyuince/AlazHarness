"""Third-store HTTP selection; HTTP/native boundaries explicitly doubled here."""
import asyncio
from dataclasses import replace
from pathlib import Path
import sys,unittest
from types import SimpleNamespace
from unittest.mock import PropertyMock,patch,AsyncMock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'packages/claw-hermes')]
import test_gateway_http_readiness as base
h=base.h

class ThreeStoreReadiness(unittest.IsolatedAsyncioTestCase):
    request=base.ReadinessTests.request
    def setUp(self):
        base.ReadinessTests.setUp(self)
        self.want=h.startup.response_preopen.PreparedResponseExpectation(
            h.startup.response_preopen.NATIVE_FEATURE,h.startup.response_preopen.SCHEMA_SHA256,(7,13))
        self.stores._response_expected=self.want
        self.response=SimpleNamespace(_conn=object())
        self.response_property=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'response_store',new_callable=PropertyMock,return_value=self.response))
        self.response_expectation=self.stack.enter_context(patch.object(h.startup.NativeStoreStartup,'response_expectation',new_callable=PropertyMock,return_value=self.want))
        self.rproof={'state':'NATIVE_RESPONSE_CONNECTION_VERIFIED','featureCommit':self.want.native_feature,
            'sameCanonicalConnectionBorrowed':True,'newDatabaseConnectionsOpened':False,
            'rawDatabaseDescriptorsOpened':False,'sqlWritesPerformed':False,'connectionsClosed':False,
            'runtimeAdmissionAuthorized':False}
        def response_probe(*args,**kwargs):self.events.append('response-probe');return dict(self.rproof)
        self.rprobe=self.stack.enter_context(patch.object(h.startup.response_live,'verify_response_connection',side_effect=response_probe))
    def obj(self,**kwargs):return h.StorageReadinessHttp(self.stores,token=self.token,response_ready=True,**kwargs)
    async def serving(self):o=self.obj();await o.start();return o
    async def test_explicit_three_checks_before_any_http_construction(self):
        o=await self.serving()
        self.assertEqual(self.events[:5],['storage-start','live-probe','response-probe','live-probe','http-app'])
        self.assertEqual(o._native,(self.state,self.replay,self.response));self.assertEqual(o._handles,tuple(x._conn for x in o._native))
        self.assertTrue(o.status()['responseIncluded']);self.assertEqual(o.status()['configuredStoreCount'],3)
        args=self.rprobe.call_args
        self.assertIs(args.args[2],self.state);self.assertIs(args.args[3],self.response)
        self.assertEqual(args.args[4].identity,self.want.response_identity);self.assertIs(args.kwargs['constructor'],False)
    async def test_ready_checks_pair_response_pair_and_has_no_authority(self):
        o=await self.serving();self.events.clear();reply=await o._handle(self.request())
        self.assertEqual(self.events,['live-probe','response-probe','live-probe'])
        self.assertEqual(reply.status,200);self.assertFalse(reply.body['agentRoutesEnabled']);self.assertFalse(reply.body['runtimeAdmissionAuthorized'])
        self.assertEqual(o.status()['successfulStorageObservations'],2)
    async def test_default_still_refuses_three_configured_stores(self):
        with self.assertRaisesRegex(h.ReadinessRejected,'three_store_not_qualified'):h.StorageReadinessHttp(self.stores,token=self.token)
        self.start.assert_not_called();self.web.assert_not_called()
    async def test_option_requires_bool_and_response_expectation(self):
        for value in (1,'true',None,{}):
            with self.assertRaisesRegex(h.ReadinessRejected,'response_option'):h.StorageReadinessHttp(self.stores,token=self.token,response_ready=value)
        for want in (None,{},object()):
            self.stores._response_expected=want
            with self.assertRaisesRegex(h.ReadinessRejected,'response_expectation_required'):self.obj()
        self.start.assert_not_called()
    async def test_configuration_drift_before_start_has_zero_storage_effect(self):
        o=self.obj();self.stores._response_expected=None
        with self.assertRaisesRegex(h.ReadinessRejected,'configuration_changed'):await o.start()
        self.start.assert_not_called();self.web.assert_not_called()
    async def test_default_cannot_acquire_third_file_after_construction(self):
        self.stores._response_expected=None;o=h.StorageReadinessHttp(self.stores,token=self.token)
        self.stores._response_expected=self.want
        with self.assertRaisesRegex(h.ReadinessRejected,'configuration_changed'):await o.start()
        self.start.assert_not_called()
    async def test_response_failure_before_bind_leaves_caller_owned_stores(self):
        self.rprobe.side_effect=RuntimeError('private response path');o=self.obj()
        with self.assertRaises(h.ReadinessRejected):await o.start()
        self.web.assert_not_called();self.close.assert_not_called();self.assertEqual(o.status()['state'],'FAILED')
        await o.close();self.close.assert_called_once()
    async def test_response_result_requires_exact_state_feature_and_authority(self):
        for key,value in (('state','OTHER'),('featureCommit','f'*40),('sameCanonicalConnectionBorrowed',False),
                          ('newDatabaseConnectionsOpened',True),('rawDatabaseDescriptorsOpened',True),
                          ('sqlWritesPerformed',True),('connectionsClosed',True),('runtimeAdmissionAuthorized',True)):
            with self.subTest(key=key):
                self.stores._stage='NEW';o=self.obj();old=dict(self.rproof);self.rproof[key]=value
                with self.assertRaises(h.ReadinessRejected):await o.start()
                self.rproof=old;self.assertIsNone(o._runner)
        self.web.assert_not_called()
    async def test_response_closed_or_corrupt_revokes_permanently(self):
        o=await self.serving();self.rprobe.side_effect=RuntimeError('secret fixture')
        r=await o._handle(self.request());self.assertEqual(r.status,503);self.assertNotIn('secret',str(r.body))
        n=self.rprobe.call_count;self.rprobe.side_effect=None;self.rprobe.return_value=self.rproof
        self.assertEqual((await o._handle(self.request())).status,503);self.assertEqual(self.rprobe.call_count,n)
        self.close.assert_not_called()
    async def test_pending_response_does_not_mean_healthy_busy(self):
        o=await self.serving();self.rprobe.side_effect=h.startup.response_live.ResponseLiveRejected('response_live_unsettled_identity')
        self.assertEqual((await o._handle(self.request())).status,503);self.assertTrue(o.status()['readinessRevoked'])
    async def test_response_transaction_is_not_rolled_back_by_probe(self):
        o=await self.serving();self.rprobe.side_effect=h.startup.response_live.ResponseLiveRejected('response_live_transaction_active')
        self.assertEqual((await o._handle(self.request())).status,503);self.close.assert_not_called()
    async def test_response_handle_replaced_before_probe_refused(self):
        o=await self.serving();n=self.rprobe.call_count;self.response._conn=object()
        self.assertEqual((await o._handle(self.request())).status,503);self.assertEqual(self.rprobe.call_count,n)
    async def test_response_object_replaced_even_with_same_handle_refused(self):
        o=await self.serving();self.response_property.return_value=SimpleNamespace(_conn=self.response._conn)
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_response_expectation_replaced_is_not_relearned(self):
        o=await self.serving();self.response_expectation.return_value=replace(self.want)
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_hidden_configuration_changed_revokes(self):
        o=await self.serving();self.stores._response_expected=replace(self.want)
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_final_pair_failure_is_not_ready_even_after_response_success(self):
        o=await self.serving();self.probe.side_effect=[{'state':'NATIVE_STORE_CONNECTIONS_VERIFIED','epochObserved':1,'runtimeAdmissionAuthorized':False},RuntimeError('drift')]
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_handle_changed_during_observation_cannot_be_accepted(self):
        o=await self.serving()
        def swap(*a,**k):self.response._conn=object();return dict(self.rproof)
        self.rprobe.side_effect=swap
        self.assertEqual((await o._handle(self.request())).status,503)
    async def test_liveness_and_bad_auth_do_not_probe_response(self):
        o=await self.serving();n=self.rprobe.call_count
        self.assertEqual((await o._handle(self.request(path='/health/live'))).status,200)
        self.assertEqual((await o._handle(self.request(headers=[]))).status,401)
        self.assertEqual((await o._handle(self.request(path='/v1/runs'))).status,404)
        self.assertEqual(self.rprobe.call_count,n)
    async def test_cancellation_still_retains_all_stores(self):
        o=await self.serving();self.runner.cleanup=AsyncMock(side_effect=asyncio.CancelledError)
        with self.assertRaises(asyncio.CancelledError):await o.close()
        self.close.assert_not_called();self.assertEqual(o.status()['state'],'CLOSE_UNKNOWN')
    async def test_http_cleanup_precedes_three_store_close(self):
        o=await self.serving();await o.close()
        self.assertEqual(self.events[-2:],['http-cleanup','storage-close']);self.assertTrue(o.status()['callerLeaseMayBeReleased'])
    async def test_close_refusal_never_rebinds_or_restarts(self):
        o=await self.serving();self.close.side_effect=RuntimeError('response txn')
        with self.assertRaises(h.ReadinessRejected):await o.close()
        self.assertEqual(o.status()['state'],'HTTP_CLOSED');self.assertFalse(o.status()['httpCleanupPending'])
        self.assertEqual(self.start.call_count,1);self.assertEqual(self.events.count('http-bind'),1)

if __name__=='__main__':unittest.main()
