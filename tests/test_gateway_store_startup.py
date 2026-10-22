"""A109 lifecycle tests with explicit dependency doubles and real close probes."""
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import os,sqlite3,sys,threading,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import gateway_store_startup as s

class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.events=[];self.created=[];self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.actor=(os.getpid(),23001,23003,threading.get_ident())
        self.held=s.live.profiles.ProfileLease.__new__(s.live.profiles.ProfileLease)
        self.held._actor=self.actor;self.held._home=Path('/owned/profile')
        self.held._owner=SimpleNamespace(_mutex=threading.RLock(),_writers=[])
        self.expected=s.live.PreparedStoreExpectation(s.live.NATIVE_PIN,'a'*64,'b'*64,'12345678-1234-4234-8234-123456789012',123,(7,11),(7,12),0,None)
        self.mount=s.live.mounts.ExpectedMount(11,(7,0),'/profile','/owned/profile','ext4')
        self.actor_fn=self.stack.enter_context(patch.object(s.live.profiles,'_actor',return_value=self.actor))
        self.lease=self.stack.enter_context(patch.object(s.live.profiles.ProfileLease,'check',return_value={'state':'NATIVE_PROFILE_RESERVED'}))
        self.finish=self.stack.enter_context(patch.object(s.live.profiles.ProfileLease,'finish'))
        self.layout=self.stack.enter_context(patch.object(s.layout,'inspect_profile',side_effect=lambda *a,**k:self.mark('layout',{'state.db':(7,11),'runs_idempotency.db':(7,12)})))
        self.pre=self.stack.enter_context(patch.object(s.preopen,'verify_preopen',side_effect=lambda *a:self.mark('preflight',{'state':'COLD_STORES_PREFLIGHT_VERIFIED'})))
        self.live=self.stack.enter_context(patch.object(s.live,'verify_live_stores',side_effect=lambda *a:self.mark('live-'+str(a[-1].epoch),{'state':'NATIVE_STORE_CONNECTIONS_VERIFIED'})))
        self.State=Mock(side_effect=lambda path:self.make_store('state'))
        self.Replay=Mock(side_effect=lambda path:self.make_store('replay'))
        self.epoch=Mock(side_effect=lambda *a,**k:self.mark('epoch',1))
        self.runtime=SimpleNamespace(begin_runtime_epoch=self.epoch)
        self.native=self.stack.enter_context(patch.object(s,'_native',return_value=(self.State,self.Replay,self.runtime)))
        self.addCleanup(lambda:[x._conn.close() for x in self.created])
    def mark(self,name,result):self.events.append(name);return result
    def make_store(self,name):
        self.events.append('open-'+name);conn=sqlite3.connect(':memory:')
        value=SimpleNamespace(_conn=conn,_token_writer_thread=None)
        value.close=Mock(side_effect=lambda:self.mark('close-'+name,conn.close()))
        self.created.append(value);return value
    def obj(self):return s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id='a109-new')
    def test_exact_sequence_and_real_closed_handles_lease_retained(self):
        o=self.obj();r=o.start()
        self.assertEqual(self.events,['layout','preflight','open-state','open-replay','live-0','epoch','live-1'])
        self.assertEqual(r['completedChecks'],['preflight','before_epoch','after_epoch'])
        self.assertEqual(o.expectation.epoch,1);self.assertEqual(o.expectation.instance_id,'a109-new')
        self.assertIs(o.state_store,self.created[0]);self.assertIs(o.replay_store,self.created[1])
        self.assertFalse(r['runtimeAdmissionAuthorized']);self.assertFalse(r['automaticRecoveryPerformed'])
        o.close();self.assertEqual(self.events[-2:],['close-replay','close-state'])
        self.assertTrue(o.status()['callerLeaseMayBeReleased']);self.finish.assert_not_called()
        o.close();self.assertEqual(self.created[0].close.call_count,1)
    def test_layout_refusal_precedes_helper_and_native_import(self):
        self.layout.side_effect=ValueError('private details');o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'startup_sequence_rejected'):o.start()
        self.pre.assert_not_called();self.native.assert_not_called();o.close();self.finish.assert_not_called()
    def test_wrong_layout_file_identity_refuses(self):
        self.layout.side_effect=None;self.layout.return_value={'state.db':(7,999),'runs_idempotency.db':(7,12)}
        o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'layout_identity'):o.start()
        self.pre.assert_not_called();self.native.assert_not_called()
    def test_preflight_failure_never_opens_native_stores(self):
        self.pre.side_effect=s.preopen.PreopenRejected('preopen_constructor_metadata');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.native.assert_not_called();self.epoch.assert_not_called();self.assertFalse(o.status()['epochMayHaveAdvanced'])
        o.close();self.finish.assert_not_called()
    def test_wrong_preflight_result_refused(self):
        self.pre.side_effect=None;self.pre.return_value={'state':'NOT_VERIFIED'};o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'preflight_result'):o.start()
        self.native.assert_not_called()
    def test_constructor_failure_has_unknown_effects_no_blind_close(self):
        self.State.side_effect=RuntimeError('partial init');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertTrue(o.status()['unknownConstructorEffects'])
        with self.assertRaisesRegex(s.StoreStartupRejected,'constructor_effects_unknown'):o.close()
        self.Replay.assert_not_called();self.finish.assert_not_called()
    def test_replay_constructor_failure_preserves_returned_state_and_lease(self):
        self.Replay.side_effect=RuntimeError('partial replay');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        with self.assertRaisesRegex(s.StoreStartupRejected,'constructor_effects_unknown'):o.close()
        self.created[0].close.assert_not_called();self.finish.assert_not_called()
    def test_live_refusal_does_not_advance_epoch_and_owned_handles_can_close(self):
        self.live.side_effect=s.live.LiveStoreRejected('live_store_unresolved_admissions');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.epoch.assert_not_called();self.assertFalse(o.status()['epochMayHaveAdvanced']);o.close()
        self.assertEqual(self.events[-2:],['close-replay','close-state']);self.finish.assert_not_called()
    def test_failed_object_cannot_retry(self):
        self.pre.side_effect=s.preopen.PreopenRejected('fail');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_fresh'):o.start()
        self.assertEqual(self.pre.call_count,1)
    def test_verified_object_cannot_start_twice(self):
        o=self.obj();o.start()
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_fresh'):o.start()
        self.assertEqual(self.epoch.call_count,1)
    def test_unknown_epoch_error_is_not_retried_or_rolled_back(self):
        self.epoch.side_effect=RuntimeError('ack lost');o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertTrue(o.status()['epochMayHaveAdvanced']);self.assertFalse(o.status()['storageReady'])
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_fresh'):o.start()
        self.assertEqual(self.epoch.call_count,1);o.close();self.finish.assert_not_called()
    def test_epoch_wrong_or_boolean_result_refused(self):
        for value in (True,0,2):
            self.epoch.side_effect=None;self.epoch.return_value=value;o=self.obj()
            with self.assertRaisesRegex(s.StoreStartupRejected,'epoch_result'):o.start()
            self.assertTrue(o.status()['epochMayHaveAdvanced']);o.close()
    def test_post_epoch_failure_is_not_ready(self):
        self.live.side_effect=[{'state':'NATIVE_STORE_CONNECTIONS_VERIFIED'},s.live.LiveStoreRejected('drift')];o=self.obj()
        with self.assertRaises(s.StoreStartupRejected):o.start()
        self.assertEqual(o.status()['epochObserved'],1);self.assertTrue(o.status()['epochMayHaveAdvanced'])
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_verified'):o.state_store
        o.close()
    def test_keyboard_interrupt_after_epoch_intent_blocks_restart(self):
        self.epoch.side_effect=KeyboardInterrupt;o=self.obj()
        with self.assertRaises(KeyboardInterrupt):o.start()
        self.assertEqual(o.status()['state'],'FAILED');self.assertTrue(o.status()['epochMayHaveAdvanced'])
        with self.assertRaises(s.StoreStartupRejected):o.start()
        o.close()
    def test_live_writer_blocks_start(self):
        self.held._owner._writers=[SimpleNamespace(is_alive=lambda:True)];o=self.obj()
        with self.assertRaisesRegex(s.StoreStartupRejected,'writers_active'):o.start()
        self.layout.assert_not_called();self.held._owner._writers.clear();o.close()
    def test_live_writer_blocks_close_before_any_store_close(self):
        o=self.obj();o.start();self.held._owner._writers=[SimpleNamespace(is_alive=lambda:True)]
        with self.assertRaisesRegex(s.StoreStartupRejected,'writers_active'):o.close()
        self.assertEqual(o.status()['state'],'VERIFIED');self.created[0].close.assert_not_called()
        self.held._owner._writers.clear();o.close()
    def test_native_token_writer_blocks_close(self):
        o=self.obj();o.start();self.created[0]._token_writer_thread=SimpleNamespace(is_alive=lambda:True)
        with self.assertRaisesRegex(s.StoreStartupRejected,'writers_active'):o.close()
        self.created[0]._token_writer_thread=None;o.close()
    def test_active_state_transaction_is_not_rolled_back_by_close(self):
        o=self.obj();o.start();self.created[0]._conn.execute('BEGIN IMMEDIATE')
        with self.assertRaisesRegex(s.StoreStartupRejected,'transaction_active'):o.close()
        self.assertTrue(self.created[0]._conn.in_transaction);self.created[0].close.assert_not_called()
        self.assertEqual(o.status()['state'],'VERIFIED');self.finish.assert_not_called()
        self.created[0]._conn.rollback();o.close()
    def test_active_replay_transaction_is_not_rolled_back_by_close(self):
        o=self.obj();o.start();self.created[1]._conn.execute('BEGIN IMMEDIATE')
        with self.assertRaisesRegex(s.StoreStartupRejected,'transaction_active'):o.close()
        self.assertTrue(self.created[1]._conn.in_transaction);self.created[1].close.assert_not_called()
        self.created[1]._conn.rollback();o.close()
    def test_close_exception_retains_lease_and_cannot_repeat(self):
        o=self.obj();o.start();self.created[1].close.side_effect=RuntimeError('close unknown')
        with self.assertRaisesRegex(s.StoreStartupRejected,'close_unconfirmed'):o.close()
        self.assertEqual(o.status()['state'],'CLOSE_UNKNOWN')
        with self.assertRaisesRegex(s.StoreStartupRejected,'close_unknown_or_active'):o.close()
        self.assertEqual(self.created[1].close.call_count,1);self.created[0].close.assert_not_called();self.finish.assert_not_called()
    def test_native_close_that_leaves_handle_open_is_not_success(self):
        o=self.obj();o.start();self.created[1].close.side_effect=None
        with self.assertRaisesRegex(s.StoreStartupRejected,'connection_not_closed'):o.close()
        self.assertFalse(o.status()['callerLeaseMayBeReleased']);self.finish.assert_not_called()
    def test_caller_lease_failure_on_close_prevents_action(self):
        o=self.obj();o.start();self.lease.side_effect=s.live.profiles.ProfileLeaseRejected('lost')
        with self.assertRaises(s.live.profiles.ProfileLeaseRejected):o.close()
        self.created[0].close.assert_not_called();self.created[1].close.assert_not_called()
    def test_foreign_process_or_thread_cannot_start_access_or_close(self):
        o=self.obj();self.actor_fn.return_value=(999,23001,23003,1)
        for action in (o.start,o.close,o.status,lambda:o.state_store):
            with self.assertRaisesRegex(s.StoreStartupRejected,'other_actor'):action()
        self.pre.assert_not_called();self.finish.assert_not_called()
    def test_access_before_start_or_after_close_refused(self):
        o=self.obj()
        for action in (lambda:o.state_store,lambda:o.replay_store,lambda:o.expectation):
            with self.assertRaisesRegex(s.StoreStartupRejected,'not_verified'):action()
        o.close()
        with self.assertRaisesRegex(s.StoreStartupRejected,'not_fresh'):o.start()
    def test_no_native_import_during_object_configuration(self):
        o=self.obj();self.native.assert_not_called();self.pre.assert_not_called();self.assertEqual(o.status()['state'],'NEW')
    def test_invalid_typed_inputs_and_instance_never_start(self):
        for args in (({},self.mount,self.expected),(self.held,{},self.expected),(self.held,self.mount,{})):
            with self.assertRaises(s.StoreStartupRejected):s.NativeStoreStartup(*args,instance_id='x')
        for name in ('',True,'space not allowed','x'*129):
            with self.assertRaises(s.StoreStartupRejected):s.NativeStoreStartup(self.held,self.mount,self.expected,instance_id=name)
        self.native.assert_not_called()
    def test_same_instance_rejected_and_non_delete_not_adopted(self):
        exp=replace(self.expected,epoch=1,instance_id='a109-new')
        with self.assertRaisesRegex(s.StoreStartupRejected,'new_instance_required'):s.NativeStoreStartup(self.held,self.mount,exp,instance_id='a109-new')
        with self.assertRaisesRegex(s.StoreStartupRejected,'cold_expectation'):s.NativeStoreStartup(self.held,self.mount,replace(self.expected,journal_mode='wal'),instance_id='new')

if __name__=='__main__':unittest.main()
