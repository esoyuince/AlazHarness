"""Optional third-store ordering with explicit boundaries and real SQLite handles."""
from dataclasses import replace
import sqlite3,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'tests')]
import gateway_store_startup as s
import gateway_http_readiness as h
import test_gateway_store_startup as existing

class ThreeStoreLifecycle(unittest.TestCase):
    mark=existing.Lifecycle.mark
    make_store=existing.Lifecycle.make_store
    def setUp(self):
        existing.Lifecycle.setUp(self)
        self.want=s.response_preopen.PreparedResponseExpectation(s.response_preopen.NATIVE_FEATURE,
            s.response_preopen.SCHEMA_SHA256,(7,13))
        self.layout.side_effect=lambda *a,**k:self.mark('layout',{'state.db':(7,11),'runs_idempotency.db':(7,12),'response_store.db':(7,13)})
        self.rpre=self.stack.enter_context(patch.object(s.response_preopen,'verify_response_preopen',side_effect=lambda *a:self.mark('response-pre',{'state':'COLD_RESPONSE_PREFLIGHT_VERIFIED'})))
        self.Response=Mock(side_effect=lambda **k:self.make_store('response'))
        self.rtype=self.stack.enter_context(patch.object(s.response_live,'qualified_response_type',return_value=self.Response))
        self.rlive=self.stack.enter_context(patch.object(s.response_live,'verify_response_connection',side_effect=lambda *a,**k:self.mark('response-live',{'state':'NATIVE_RESPONSE_CONNECTION_VERIFIED'})))
    def obj(self):return s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='three-new',response_expected=self.want)
    def test_exact_order_before_epoch_and_reverse_dependency_close(self):
        o=self.obj();result=o.start()
        self.assertEqual(self.events,['layout','preflight','response-pre','open-state','open-replay','live-0','open-response','response-live','epoch','live-1','response-live'])
        self.assertEqual(result['completedChecks'],['preflight','response_preflight','before_epoch','response_before_epoch','after_epoch','response_after_epoch'])
        self.assertIs(result['responseConfigured'],True);self.assertIs(o.response_store,self.created[2]);self.assertIs(o.response_expectation,self.want)
        self.assertTrue(self.layout.call_args.kwargs['include_response'])
        self.Response.assert_called_once_with(db_path=str(self.held._home/'response_store.db'),canonical_state=self.created[0],max_size=100,max_identities=1000)
        self.assertTrue(all(c.kwargs['constructor'] is True for c in self.rlive.call_args_list))
        o.close();self.assertEqual(self.events[-3:],['close-response','close-replay','close-state']);self.finish.assert_not_called()
        self.assertTrue(o.status()['callerLeaseMayBeReleased'])
    def test_missing_response_file_identity_rejects_before_preflights(self):
        self.layout.side_effect=None;self.layout.return_value={'state.db':(7,11),'runs_idempotency.db':(7,12),'response_store.db':(7,99)}
        o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'response_layout_identity'):o.start()
        self.pre.assert_not_called();self.rpre.assert_not_called();self.native.assert_not_called();o.close()
    def test_response_preflight_failure_never_opens_any_store(self):
        self.rpre.side_effect=s.response_preopen.ResponsePreopenRejected('response_preopen_unsettled_identity');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.native.assert_not_called();self.rtype.assert_not_called();self.epoch.assert_not_called()
        self.assertFalse(o.status()['epochMayHaveAdvanced']);o.close();self.finish.assert_not_called()
    def test_wrong_response_preflight_result_refused(self):
        self.rpre.side_effect=None;self.rpre.return_value={'state':'MAYBE'};o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'response_preflight_result'):o.start()
        self.State.assert_not_called()
    def test_pending_canonical_work_prevents_response_constructor(self):
        self.live.side_effect=s.live.LiveStoreRejected('live_store_unresolved_admissions');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.rtype.assert_not_called();self.Response.assert_not_called();self.epoch.assert_not_called();o.close()
        self.assertEqual(self.events[-2:],['close-replay','close-state'])
    def test_unknown_response_constructor_preserves_all_ownership(self):
        self.Response.side_effect=RuntimeError('partial constructor');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertTrue(o.status()['unknownConstructorEffects']);self.epoch.assert_not_called()
        with self.assertRaisesRegex(s.StoreStartupRejected,'constructor_effects_unknown'):o.close()
        for store in self.created:store.close.assert_not_called()
        self.finish.assert_not_called()
    def test_wrong_source_refused_before_response_open(self):
        self.rtype.side_effect=s.response_live.ResponseLiveRejected('response_live_source_mismatch');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.Response.assert_not_called();self.epoch.assert_not_called();self.assertFalse(o.status()['unknownConstructorEffects']);o.close()
    def test_response_live_failure_stops_epoch(self):
        self.rlive.side_effect=s.response_live.ResponseLiveRejected('response_live_constructor_changed_rows');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.epoch.assert_not_called();self.assertFalse(o.status()['epochMayHaveAdvanced']);o.close()
        self.assertEqual(self.events[-3:],['close-response','close-replay','close-state'])
    def test_response_failure_after_epoch_is_not_ready(self):
        self.rlive.side_effect=[{'state':'NATIVE_RESPONSE_CONNECTION_VERIFIED'},s.response_live.ResponseLiveRejected('drift')];o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertTrue(o.status()['epochMayHaveAdvanced']);self.assertEqual(o.status()['epochObserved'],1)
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_verified'):o.response_store
        o.close()
    def test_response_transaction_blocks_every_close_without_rollback(self):
        o=self.obj();o.start();r=self.created[2];r._conn.execute('BEGIN IMMEDIATE')
        with self.assertRaisesRegex(s.StoreStartupRejected,'transaction_active'):o.close()
        self.assertTrue(r._conn.in_transaction)
        for store in self.created:store.close.assert_not_called()
        self.assertEqual(o.status()['state'],'VERIFIED');r._conn.rollback();o.close()
    def test_state_transaction_blocks_response_close_too(self):
        o=self.obj();o.start();self.created[0]._conn.execute('BEGIN IMMEDIATE')
        with self.assertRaisesRegex(s.StoreStartupRejected,'transaction_active'):o.close()
        self.created[2].close.assert_not_called();self.created[0]._conn.rollback();o.close()
    def test_replaced_handle_refused_before_first_close(self):
        o=self.obj();o.start();r=self.created[2];original=r._conn;replacement=sqlite3.connect(':memory:');r._conn=replacement
        try:
            with self.assertRaisesRegex(s.StoreStartupRejected,'connection_replaced'):o.close()
            for store in self.created:store.close.assert_not_called()
        finally:r._conn=original;replacement.close()
        o.close()
    def test_response_close_swallowing_error_is_not_success(self):
        o=self.obj();o.start();self.created[2].close.side_effect=None
        with self.assertRaisesRegex(s.StoreStartupRejected,'connection_not_closed'):o.close()
        self.assertEqual(o.status()['state'],'CLOSE_UNKNOWN');self.created[0].close.assert_not_called();self.created[1].close.assert_not_called()
        with self.assertRaises(s.StoreStartupRejected):o.close()
    def test_response_close_exception_cannot_be_repeated(self):
        o=self.obj();o.start();self.created[2].close.side_effect=RuntimeError('unknown')
        with self.assertRaises(s.StoreStartupRejected):o.close()
        with self.assertRaises(s.StoreStartupRejected):o.close()
        self.assertEqual(self.created[2].close.call_count,1);self.finish.assert_not_called()
    def test_unconfigured_default_does_not_get_third_path(self):
        o=s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='default-new');o.start()
        self.rpre.assert_not_called();self.rtype.assert_not_called();self.rlive.assert_not_called()
        self.assertNotIn('include_response',self.layout.call_args.kwargs)
        for action in (lambda:o.response_store,lambda:o.response_expectation):
            with self.assertRaisesRegex(s.StoreStartupRejected,'response_not_configured'):action()
        self.assertFalse(o.status()['responseConfigured']);o.close()
    def test_two_store_http_diagnostics_cannot_claim_third_store(self):
        o=self.obj()
        with self.assertRaisesRegex(h.ReadinessRejected,'three_store_not_qualified'):h.StorageReadinessHttp(o,token='a'*64)
        self.pre.assert_not_called();self.native.assert_not_called()
    def test_new_expectation_cannot_alias_state_or_replay(self):
        for identity in ((7,11),(7,12),(8,13)):
            with self.subTest(identity=identity),self.assertRaises(s.response_preopen.ResponsePreopenRejected):
                s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='three',response_expected=replace(self.want,response_identity=identity))
    def test_failed_object_not_replayed(self):
        self.rpre.side_effect=ValueError('refuse');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_fresh'):o.start()
        self.assertEqual(self.rpre.call_count,1)

if __name__=='__main__':unittest.main()
