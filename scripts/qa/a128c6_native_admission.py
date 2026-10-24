"""Native local admission transitions; no HTTP, agent or provider execution.
Original native SessionDB/authority/API/binding methods remain real. Lower-level
ledger calls use the actual authority write guard; they are NOT a full API turn.
"""
import asyncio,hashlib,json,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import b123a6_native_prepared_api as base
OTHER=None
NOTES=[]

class AdmissionCases(base.PreparedAPICases):
    def call(self,fn,*a,**kw):
        async def invoke():return fn(*a,**kw)
        return base.LOOP.run_until_complete(invoke())
    def activate(self):
        b,a=self.make();self.call(b.activate_admission);return b,a
    def ledger(self):self.state.create_session('a128-owned','api_server')
    def admit(self,name='request-1'):
        return base.Runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='api',
            session_id='a128-owned',request_id=name,payload={'text':'owned ledger fixture'},
            _authorize_write=self.authority._admission_gate())
    def close_normal(self,b,a):
        if self.binding._stage=='ACTIVE':self.call(b.begin_drain)
        self.call(b.finish_drain);base.LOOP.run_until_complete(a.disconnect());self.runner.close_all_session_db_handles()
        self.assertEqual((b._stage,self.binding._stage),('DETACHED','DETACHED'))
        for c in (self.state._conn,self.replay._conn,self.response._conn):self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(base.Own.owns(self.home))
    def test_active_flags_alone_do_not_grant_admission(self):
        b,a=self.make();self.runner._draining=False;self.authority.retiring=False
        try:
            with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()
        finally:self.runner._draining=True;self.authority.retiring=True
        self.assertEqual(self.binding._stage,'PREPARED')
    def test_active_explicit_transition_preserves_three_handles_epoch_and_rows(self):
        b,a=self.make();before=tuple(s._conn for s in (self.state,self.replay,self.response))
        with self.observed():
            state=self.call(b.activate_admission)
            self.assertEqual(state['state'],'ACTIVE');self.assertTrue(state['localAdmissionOpen'])
            self.authority._require_admission_open();self.assertEqual(self.select(b,a),(self.state,self.replay,self.response))
        self.assertEqual(before,tuple(s._conn for s in (self.state,self.replay,self.response)))
        self.assertEqual(tuple(self.state._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),(self.epoch,'b123a6-owned'))
        self.close_normal(b,a)
    def test_active_no_reentry_or_finish_before_drain(self):
        b,a=self.activate()
        with self.observed():
            for fn in (b.activate_admission,b.finish_drain):
                with self.assertRaises(base.RejectStore):self.call(fn)
        self.assertEqual(self.binding._stage,'ACTIVE');self.close_normal(b,a)
    def test_active_cannot_disconnect_or_detach_while_admission_open(self):
        b,a=self.activate()
        with self.observed():
            with self.assertRaises(base.RejectStore):base.LOOP.run_until_complete(a.disconnect())
            with self.assertRaises(base.RejectRunner):self.runner.close_all_session_db_handles()
        self.assertEqual((b._stage,self.binding._stage),('ATTACHED','ACTIVE'));self.close_normal(b,a)
    def test_active_queued_native_admission_is_retained_after_drain(self):
        self.ledger();b,a=self.activate();row=self.call(self.admit)
        self.assertEqual(row['status'],'queued')
        with self.observed():self.call(b.begin_drain);self.call(b.begin_drain)
        with self.assertRaises(base.Runtime.RuntimeStoreError):self.call(self.admit,'request-2')
        with self.assertRaises(base.Runtime.RuntimeStoreError):self.call(base.Runtime.claim_session_input,self.state,epoch=self.epoch,session_id='a128-owned',_guard=self.authority._admission_gate())
        with self.assertRaises(base.RejectRunner):self.call(b.finish_drain)
        self.assertEqual(self.state._conn.execute('SELECT status FROM session_admissions').fetchone()[0],'queued')
        base.Runtime.cancel_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'])
        self.close_normal(b,a)
    def test_active_existing_native_claim_can_settle_during_drain(self):
        self.ledger();b,a=self.activate();row=self.call(self.admit)
        claim=self.call(base.Runtime.claim_session_input,self.state,epoch=self.epoch,session_id='a128-owned',_guard=self.authority._admission_gate())
        self.assertEqual(claim['status'],'started');self.call(b.begin_drain)
        with self.assertRaises(base.RejectRunner):self.call(b.finish_drain)
        terminal=base.Runtime.settle_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'],generation=claim['generation'],outcome='completed',result={'final_response':'fixture'})
        self.assertEqual(terminal['status'],'terminal');self.close_normal(b,a)
    def test_active_drain_does_not_rollback_any_open_transaction(self):
        for index in range(3):
            if index==0:b,a=self.activate();self.state._conn.execute('BEGIN IMMEDIATE');self.call(b.begin_drain)
            c=(self.state._conn,self.replay._conn,self.response._conn)[index]
            if index:c.execute('BEGIN IMMEDIATE')
            try:
                with self.assertRaises((base.RejectStore,base.RejectRunner)):self.call(b.finish_drain)
                self.assertTrue(c.in_transaction);self.assertEqual(self.binding._stage,'DRAINING')
            finally:c.rollback()
        self.close_normal(b,a)
    def test_active_admission_waiting_inside_native_write_refused_after_drain(self):
        self.ledger();b,a=self.activate();entered=threading.Event();release=threading.Event();gate=self.authority._admission_gate()
        def delayed_guard(conn):
            entered.set()
            if not release.wait(10):raise RuntimeError('fixture wait timeout')
            gate(conn)
        async def exercise():
            task=asyncio.create_task(asyncio.to_thread(base.Runtime.admit_session_input,self.state,epoch=self.epoch,principal_id='api',session_id='a128-owned',request_id='delayed',payload={'text':'fixture'},_authorize_write=delayed_guard))
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());b.begin_drain();release.set()
                with self.assertRaises(base.Runtime.RuntimeStoreError):await task
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        base.LOOP.run_until_complete(exercise())
        self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],0)
        NOTES.append({'case':self._testMethodName,'nativeTransactionGateAfterDrain':'REFUSED','newRows':0})
        self.close_normal(b,a)
    def test_active_cancelled_waiter_is_not_finished_native_write(self):
        self.ledger();b,a=self.activate();entered=threading.Event();release=threading.Event();finished=threading.Event();outcome=[];gate=self.authority._admission_gate()
        def delayed(conn):
            entered.set()
            if not release.wait(10):raise RuntimeError('fixture wait timeout')
            gate(conn)
        def write():
            try:base.Runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='api',session_id='a128-owned',request_id='cancelled-waiter',payload={'text':'fixture'},_authorize_write=delayed)
            except base.Runtime.RuntimeStoreError:outcome.append('refused')
            finally:finished.set()
        async def exercise():
            task=asyncio.create_task(asyncio.to_thread(write))
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                b.begin_drain();self.assertFalse(finished.is_set())
                with self.assertRaises((base.RejectStore,base.RejectRunner)):b.finish_drain()
                self.assertEqual(b._stage,'ATTACHED');release.set()
                for _ in range(2000):
                    if finished.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(finished.is_set())
            finally:release.set()
        try:base.LOOP.run_until_complete(exercise())
        finally:release.set();self.assertTrue(finished.wait(5))
        self.assertEqual(outcome,['refused']);self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],0)
        self.close_normal(b,a)
    def test_active_runtime_and_listener_entrypoints_remain_refused(self):
        b,a=self.activate()
        for fn in (a.connect,self.runner.start):
            with self.assertRaises((base.RejectRunner,base.RejectStore)):base.LOOP.run_until_complete(fn())
        self.assertIsNone(a._site);self.assertFalse(self.runner._running);self.close_normal(b,a)
    def test_active_other_loop_or_thread_cannot_transition(self):
        b,a=self.activate();errors=[]
        async def other():
            with self.assertRaises(base.RejectStore):b.begin_drain()
        OTHER.run_until_complete(other())
        def foreign():
            try:b.begin_drain()
            except base.RejectRunner:errors.append('actor-refused')
        thread=threading.Thread(target=foreign);thread.start();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(errors,['actor-refused']);self.assertEqual(self.binding._stage,'ACTIVE');self.close_normal(b,a)
    def test_active_one_way_drain_cannot_reactivate(self):
        b,a=self.activate();self.call(b.begin_drain)
        with self.assertRaises(base.RejectStore):self.call(b.activate_admission)
        self.call(b.finish_drain)
        with self.assertRaises(base.RejectStore):self.call(b.activate_admission)
        with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()
        self.close_normal(b,a)
    def test_active_live_task_blocks_finish_without_cancellation_or_pruning(self):
        b,a=self.activate();gate=asyncio.Event()
        async def create():return asyncio.create_task(gate.wait())
        task=base.LOOP.run_until_complete(create());self.runner._background_tasks.add(task);self.call(b.begin_drain)
        try:
            with self.assertRaises(base.RejectStore):self.call(b.finish_drain)
            self.assertFalse(task.done());self.assertFalse(task.cancelled());self.assertIn(task,self.runner._background_tasks)
        finally:gate.set();base.LOOP.run_until_complete(task);self.runner._background_tasks.remove(task)
        self.close_normal(b,a)
    def test_active_pending_response_blocks_activation_then_finish(self):
        b,a=self.make();pc=self.response._conn
        pc.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('idem:a128',?,1,'null')",('f'*64,));pc.commit()
        with self.assertRaises(base.RejectStore):self.call(b.activate_admission)
        self.assertEqual(self.binding._stage,'PREPARED')
        self.response.put('idem:a128',{'response':{'id':'fixture','status':'completed'}});self.call(b.activate_admission)
        pc.execute("UPDATE response_keys SET settled_at=NULL WHERE request_key='idem:a128'");pc.commit();self.call(b.begin_drain)
        with self.assertRaises(base.RejectStore):self.call(b.finish_drain)
        self.response.put('idem:a128',{'response':{'id':'fixture','status':'completed'}});self.close_normal(b,a)
    def test_active_pending_replay_blocks_activation_without_changing_status(self):
        b,a=self.make();self.replay.reserve('test','idem','f'*64,'run-1',{'run_id':'run-1','status':'running'})
        with self.assertRaises(base.RejectStore):self.call(b.activate_admission)
        self.assertEqual(self.binding._stage,'PREPARED');self.assertIn('running',self.replay._conn.execute('SELECT status_json FROM run_idempotency').fetchone()[0])
    def test_active_header_and_owner_drift_refuse_finish(self):
        b,a=self.activate();self.call(b.begin_drain);old=self.response._conn.execute('PRAGMA application_id').fetchone()[0]
        self.response._conn.execute('PRAGMA application_id=17')
        try:
            with self.assertRaises(base.RejectStore):self.call(b.finish_drain)
            self.assertEqual(self.binding._stage,'DRAINING')
        finally:self.response._conn.execute('PRAGMA application_id='+str(old))
        self.close_normal(b,a)
    def test_active_gate_detects_store_replacement_without_sql_recursion(self):
        b,a=self.activate();old=a._response_store;a._response_store=object()
        try:
            with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()
        finally:a._response_store=old
        self.close_normal(b,a)

    def test_regression_late_replay_blocks_api_detach_before_effect(self):
        b,a=self.activate();self.call(b.begin_drain);self.call(b.finish_drain)
        self.replay.reserve('test','late','c'*64,'late-run',{'run_id':'late-run','status':'running'})
        with self.assertRaises(base.RejectStore):base.LOOP.run_until_complete(a.disconnect())
        self.assertEqual(b._stage,'ATTACHED');self.assertEqual(self.binding._stage,'DRAINED')
    def test_regression_late_response_blocks_runner_after_api_detach(self):
        b,a=self.activate();self.call(b.begin_drain);self.call(b.finish_drain);base.LOOP.run_until_complete(a.disconnect())
        self.response._conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('idem:late',?,1,'null')",('f'*64,));self.response._conn.commit()
        with self.assertRaises(base.RejectStore):self.runner.close_all_session_db_handles()
        self.assertFalse(self.runner.session_store._borrowed_session_state._closed)
    def test_regression_changed_config_refuses_write_gate(self):
        b,a=self.activate();self.config.multiplex_profiles=True
        try:
            with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()
        finally:self.config.multiplex_profiles=False
        self.close_normal(b,a)
    def test_regression_foreign_scope_refuses_write_gate(self):
        b,a=self.activate();token=base.Constants.set_hermes_home_override(self.home/'foreign')
        try:
            with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()
        finally:base.Constants.reset_hermes_home_override(token)
        self.assertFalse((self.home/'foreign').exists());self.close_normal(b,a)
    def test_regression_closed_response_refuses_write_gate(self):
        b,a=self.activate();self.response.close()
        with self.assertRaises(base.Runtime.RuntimeStoreError):self.authority._require_admission_open()

    def test_drained_cleanup_await_new_replay_retains_unknown(self):
        b,a=self.activate();self.call(b.begin_drain);self.call(b.finish_drain)
        original=a._memory_sessions;entered=threading.Event();release=threading.Event();done=threading.Event()
        class PausedMemory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(10):raise RuntimeError('fixture cleanup timeout')
                    original.close_all()
                finally:done.set()
        a._memory_sessions=PausedMemory()
        async def trial():
            task=asyncio.create_task(a.disconnect())
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());self.assertEqual(b._stage,'DRAINING')
                self.replay.reserve('test','during-await','f'*64,'during-await',{'run_id':'during-await','status':'running'})
                release.set()
                with self.assertRaises(base.RejectStore):await task
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:base.LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));a._memory_sessions=original
        self.assertEqual(b._stage,'CLOSE_UNKNOWN');self.assertEqual(self.binding._stage,'DRAINED')
        with self.assertRaises(base.RejectStore):base.LOOP.run_until_complete(a.disconnect())
        with self.assertRaises(base.RejectStore):self.runner.close_all_session_db_handles()
        self.assertIn('running',self.replay._conn.execute('SELECT status_json FROM run_idempotency').fetchone()[0])
        for conn in (self.state._conn,self.replay._conn,self.response._conn):self.assertEqual(conn.execute('SELECT 1').fetchone()[0],1)
        NOTES.append({'case':self._testMethodName,'bundleState':'CLOSE_UNKNOWN','allCallerConnectionsOpen':True,'retryRefused':True})
    def test_drained_cleanup_cancelled_await_cannot_be_retried(self):
        b,a=self.activate();self.call(b.begin_drain);self.call(b.finish_drain)
        original=a._memory_sessions;entered=threading.Event();release=threading.Event();done=threading.Event()
        class PausedMemory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(10):raise RuntimeError('fixture cleanup timeout')
                    original.close_all()
                finally:done.set()
        a._memory_sessions=PausedMemory()
        async def trial():
            task=asyncio.create_task(a.disconnect())
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertFalse(done.is_set());self.assertEqual(b._stage,'CLOSE_UNKNOWN')
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:base.LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));a._memory_sessions=original
        with self.assertRaises(base.RejectStore):base.LOOP.run_until_complete(a.disconnect())
        with self.assertRaises(base.RejectStore):self.runner.close_all_session_db_handles()
        self.assertTrue(base.Own.owns(self.home))

def main():
    global OTHER
    OTHER=asyncio.new_event_loop()  # test-owned loop setup before offline audit hook
    base.PreparedAPICases=AdmissionCases  # extend QA class only, never native code
    try:code=base.main()
    finally:OTHER.close()
    out=Path(sys.argv[sys.argv.index('--output')+1]);native=Path(sys.argv[sys.argv.index('--native')+1])
    p=out/'result.json';r=json.loads(p.read_text(encoding='utf-8'))
    names=('gateway/run_borrowed_admission.py','gateway/run_borrowed_state.py','gateway/session_authority.py','gateway/platforms/api_server_prepared.py','gateway/platforms/api_server_borrowed.py')
    r['candidateSources']={name:hashlib.sha256((native/name).read_bytes()).hexdigest() for name in names}
    r['sourceHashes']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('scripts/qa/a128c6_native_admission.py','scripts/qa/b123a6_native_prepared_api.py')}
    r['result']='PASS_NATIVE_LOCAL_ADMISSION_LIFECYCLE' if code==0 else 'FAIL'
    r['preparedCompatibilityMethods']=22;r['newAdmissionMethods']=24;r['notes']=NOTES
    r.pop('serviceAdmissionOrListenerActivated',None)
    r.update(localNativeAdmissionGateExercised=True,actualGuardedAdmissionAndClaimRows=True,fullAgentOrTurnRunnerExecuted=False,httpListenerActivated=False,harnessConsumerIntegrated=False,nativeMethodsReplaced=False,waitingWriteBarrierIsExplicitFixture=True)
    p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print('A128_RESULT',r['result'],r['total'],r['passed'],r['errors'],r['failures'],flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
