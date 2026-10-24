"""Independent canonical API publication and real async-admission contracts.
Uses the old Q128 real native fixture; product methods are never replaced.
No listener, model execution, harness source-gate bypass, or native FIFO schedule.
Publication call spelling is bound to the frozen producer API before any run.
"""
import asyncio,hashlib,json,sys,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import q128c6_native_lifecycle_checks as fx
Base=fx.IndependentLifecycle
OBS=[];PUBLICATIONS=[]

class PublicationChecks(unittest.TestCase):
    setUp=Base.setUp
    def tearDown(self):
        # Complete only this fixture's unexpected original status writer before
        # deleting its home. Dedicated test still REFUSES such publication.
        from gateway.status import flush_runtime_status
        self.assertTrue(flush_runtime_status(5))
        Base.tearDown(self)
    call=Base.call
    activate=Base.activate
    drain=Base.drain
    finish=Base.finish
    watched=Base.watched
    assert_open=Base.assert_open
    pending=Base.pending
    complete=Base.complete
    def publish(self):return self.call(self.bundle.publish_api_adapter)
    def source(self,sid='q131-session'):
        from gateway.config import Platform
        from gateway.session import SessionSource
        return SessionSource(platform=Platform.API_SERVER,chat_id=sid,user_id='api',chat_type='dm')
    def api_key(self):
        from gateway.config import Platform
        return Platform.API_SERVER
    def api_admit(self,sid='q131-session',rid='q131-request',text='owned offline request'):
        from gateway.session_api_turn import admit_api_turn_async
        async def attempt():
            result=await admit_api_turn_async(self.api,session_id=sid,request_id=rid,user_message=text,conversation_history=[])
            await asyncio.sleep(0)
            return result
        result=fx.LOOP.run_until_complete(attempt())
        self.assertIs(result[0],self.authority)
        OBS.append({'case':self._testMethodName,'session':result[1].session_id,'status':result[2]['status'],'sameAuthority':True,'wholeTurnScheduled':False})
        return result
    def settle(self,row):
        claim=fx.RT.claim_session_input(self.state,epoch=self.epoch,session_id=row['target_session_id'],_guard=self.authority._admission_gate())
        self.assertEqual(claim['admission_id'],row['admission_id'])
        return fx.RT.settle_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'],generation=claim['generation'],outcome='completed')
    def retire(self):return self.call(self.bundle.retire_idle_api_sessions)
    def test_default_prepared_does_not_publish(self):
        self.assertEqual(self.runner.adapters,{})
        self.assertIsNone(self.runner._adapter_for_source(self.source()))
        self.assertIs(self.api.gateway_runner,self.runner);self.assertEqual(self.binding._stage,'PREPARED')
    def test_published_identity_uses_existing_canonical_resolver(self):
        with self.watched():self.publish()
        self.assertEqual(list(self.runner.adapters),[self.api_key()]);self.assertIs(self.runner.adapters[self.api_key()],self.api)
        self.assertIs(self.runner._adapter_for_source(self.source()),self.api)
        self.assertFalse(self.runner._running);self.assertFalse(self.api._running);self.assertIsNone(self.api._site);self.assert_open()
    def test_publication_never_recovers_or_wires_voice(self):
        seen=[];old=sys.getprofile()
        def profile(frame,event,arg):
            if event=='call' and frame.f_code.co_name in ('recover_api_turns','_recover_api_turns','_sync_voice_mode_state_to_adapter','_bind_voice_input_callback'):
                seen.append(frame.f_code.co_name)
        sys.setprofile(profile)
        try:
            with self.watched():self.publish()
        finally:sys.setprofile(old)
        self.assertEqual(seen,[]);self.assertFalse([t for t in asyncio.all_tasks(fx.LOOP) if not t.done()])
        PUBLICATIONS.append({'case':self._testMethodName,'recoveryOrVoiceCalls':seen,'pendingTasks':0})
    def test_foreign_existing_adapter_is_not_overwritten(self):
        foreign=object();self.runner.adapters[self.api_key()]=foreign
        try:
            with self.watched(),self.assertRaises((fx.Reject,fx.RunnerReject)):self.publish()
            self.assertIs(self.runner.adapters[self.api_key()],foreign)
        finally:self.runner.adapters.clear()
    def test_non_api_adapter_is_not_silently_dropped(self):
        from gateway.config import Platform
        foreign=object();self.runner.adapters[Platform.LOCAL]=foreign
        try:
            with self.watched(),self.assertRaises((fx.Reject,fx.RunnerReject)):self.publish()
            self.assertIs(self.runner.adapters[Platform.LOCAL],foreign)
        finally:self.runner.adapters.clear()
    def test_publication_refuses_transaction_in_each_store(self):
        for conn in self.connections:
            conn.execute('BEGIN IMMEDIATE')
            try:
                with self.watched(),self.assertRaises((fx.Reject,fx.RunnerReject)):self.publish()
                self.assertTrue(conn.in_transaction);self.assertFalse(self.runner.adapters)
            finally:conn.rollback()
    def test_publication_refuses_pending_real_task_without_cancel(self):
        event,task=self.pending();self.runner._background_tasks.add(task)
        try:
            with self.watched(),self.assertRaises((fx.Reject,fx.RunnerReject)):self.publish()
            self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:self.complete(event,task);self.runner._background_tasks.remove(task)
    def test_native_async_admission_does_not_publish_unowned_gateway_status(self):
        from gateway.status import flush_runtime_status
        self.publish();self.activate();calls=[];previous=sys.getprofile()
        def observe(frame,event,arg):
            if event=='call' and frame.f_code.co_name in ('publish_runtime_status','write_runtime_status'):
                calls.append(frame.f_code.co_name)
        sys.setprofile(observe)
        try:self.api_admit()
        finally:
            sys.setprofile(previous);self.assertTrue(flush_runtime_status(5))
        PUBLICATIONS.append({'case':self._testMethodName,'runtimeStatusCalls':calls,'statusFileCreated':(self.home/'gateway_state.json').exists()})
        self.assertEqual(calls,[])
        self.assertFalse((self.home/'gateway_state.json').exists())
    def test_real_api_admission_then_exact_retry_is_one_row(self):
        self.publish();self.activate();authority,ref,row=self.api_admit()
        self.assertEqual(row['status'],'queued')
        again=self.api_admit()[2];self.assertEqual(again['admission_id'],row['admission_id'])
        self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
        self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],1)
        self.assertFalse(getattr(self.authority,'executing',{}));self.assert_open()
    def test_same_request_changed_payload_refused(self):
        self.publish();self.activate();row=self.api_admit()[2]
        with self.assertRaises(fx.RT.RuntimeStoreError):self.api_admit(text='different payload')
        self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
        self.assertEqual(fx.RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'queued')
    def test_same_request_other_target_refused(self):
        self.publish();self.activate();row=self.api_admit()[2]
        with self.assertRaises(fx.RT.RuntimeStoreError):self.api_admit(sid='other-session')
        self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
        self.assertEqual(fx.RT.get_session_admission(self.state,admission_id=row['admission_id'])['target_session_id'],'q131-session')
    def test_published_map_replacement_blocks_new_admission_before_write(self):
        self.publish();self.activate();old=self.runner.adapters;self.runner.adapters=dict(old)
        before=self.state._conn.total_changes
        try:
            with self.assertRaises((fx.RT.RuntimeStoreError,fx.Reject)):self.api_admit()
            self.assertEqual(self.state._conn.total_changes,before)
        finally:self.runner.adapters=old
    def test_published_adapter_replacement_blocks_native_guard(self):
        self.publish();self.activate();self.runner.adapters[self.api_key()]=object()
        try:
            with self.watched(),self.assertRaises(fx.RT.RuntimeStoreError):self.authority._require_admission_open()
        finally:self.runner.adapters[self.api_key()]=self.api
    def test_published_owner_profile_drift_blocks_guard(self):
        self.publish();self.activate();old=self.api._owner_profile;self.api._owner_profile='foreign'
        try:
            with self.watched(),self.assertRaises(fx.RT.RuntimeStoreError):self.authority._require_admission_open()
        finally:self.api._owner_profile=old
    def test_published_foreign_home_refused_without_materialization(self):
        import hermes_constants
        self.publish();self.activate();foreign=self.home/'foreign';token=hermes_constants.set_hermes_home_override(foreign)
        try:
            with self.assertRaises((fx.RT.RuntimeStoreError,fx.Reject)):self.api_admit()
            self.assertFalse(foreign.exists());self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],0)
        finally:hermes_constants.reset_hermes_home_override(token)
    def test_draining_queued_request_retains_publication_and_all_handles(self):
        self.publish();self.activate();row=self.api_admit()[2];self.drain()
        with self.assertRaises((fx.Reject,fx.RunnerReject)):self.finish()
        with self.assertRaises((fx.Reject,fx.RunnerReject)):fx.LOOP.run_until_complete(self.api.disconnect())
        self.assertIs(self.runner.adapters[self.api_key()],self.api);self.assert_open()
        self.assertEqual(fx.RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'queued')
    def test_settled_native_leaf_retirement_preserves_history_then_detaches(self):
        self.publish();self.activate();row=self.api_admit()[2];self.settle(row)
        self.drain();before=[hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest() for c in self.connections]
        self.retire();self.finish();fx.LOOP.run_until_complete(self.api.disconnect());self.runner.close_all_session_db_handles()
        self.assertEqual(self.runner.adapters,{});self.assertIsNone(self.runner._adapter_for_source(self.source()))
        self.assertEqual([hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest() for c in self.connections],before)
        self.assertEqual(fx.RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'terminal');self.assert_open()
    def test_prepared_only_disconnect_removes_publication_keeps_stores(self):
        self.publish()
        with self.watched():fx.LOOP.run_until_complete(self.api.disconnect());self.runner.close_all_session_db_handles()
        self.assertEqual(self.runner.adapters,{});self.assert_open()
    def test_standard_service_listener_remain_closed_after_publication(self):
        self.publish();self.activate()
        with self.assertRaises(fx.Reject):fx.LOOP.run_until_complete(self.api.connect())
        with self.assertRaises(fx.RunnerReject):fx.LOOP.run_until_complete(self.runner.start())
        self.assertFalse(self.api._running);self.assertFalse(self.runner._running);self.assertIsNone(self.api._app)
    def test_adapter_map_drift_during_awaited_cleanup_never_deletes_foreign_entry(self):
        self.publish();entered=threading.Event();release=threading.Event();self.releases.append(release);old=self.api._memory_sessions;foreign=object()
        class Pause:
            def close_all(inner):
                entered.set()
                if not release.wait(8):raise TimeoutError('owned pause')
        self.api._memory_sessions=Pause()
        async def exercise():
            task=asyncio.create_task(self.api.disconnect())
            for _ in range(1000):
                if entered.is_set():break
                await asyncio.sleep(.002)
            self.assertTrue(entered.is_set());self.runner.adapters[self.api_key()]=foreign;release.set()
            with self.assertRaises((fx.Reject,fx.RunnerReject)):await task
        try:fx.LOOP.run_until_complete(exercise())
        finally:release.set();self.api._memory_sessions=old
        self.assertIs(self.runner.adapters[self.api_key()],foreign);self.assertEqual(self.bundle._stage,'CLOSE_UNKNOWN');self.assert_open()
        with self.assertRaises((fx.Reject,fx.RunnerReject)):fx.LOOP.run_until_complete(self.api.disconnect())
    def test_foreign_loop_publication_refused_before_registry_effect(self):
        async def invoke():return self.bundle.publish_api_adapter()
        # Publication must retain the loop established when actual authority was prepared,
        # or explicitly bind its first loop and reject subsequent foreign transitions.
        self.publish();self.activate()
        with self.assertRaises((fx.Reject,fx.RunnerReject)):fx.OTHER.run_until_complete(invoke())
        self.assertIs(self.runner.adapters[self.api_key()],self.api)

def main():
    fx.IndependentLifecycle=PublicationChecks
    code=fx.main();out=Path(sys.argv[sys.argv.index('--output')+1]);record=json.loads((out/'result.json').read_text(encoding='utf-8'))
    record.update(result='PASS_INDEPENDENT_NATIVE_API_PUBLICATION' if code==0 else 'FAIL',driverSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),fixtureSha256=hashlib.sha256(Path(fx.__file__).read_bytes()).hexdigest(),apiAdmissionObservations=OBS,publicationObservations=PUBLICATIONS,
        realNativeAsyncApiAdmission=True,nativeMethodsReplaced=False,completeTurnOrModelExecuted=False,publicationAndDetachFaultObjectsExplicit=True,harnessSourceEnvelopeQualified=False)
    (out/'publication-result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('nativeImports','checks','caseEnd','deniedEvents','apiAdmissionObservations','publicationObservations')}),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
