"""Independent real original owner + canonical API lifecycle.
OS identity/lease/mount/cold boundaries use the existing explicit Windows fixture.
Actual API admission is exercised; leaf settlement is declared, no payload/model.
Only test classes are composed; product functions remain real (trace faults named).
"""
import asyncio,hashlib,json,sqlite3,sys,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/qa'))
import b129d6_native_active_owner as f
Base=f.ActiveOwnerCases
OBS=[]
class OwnerPublication(unittest.TestCase):
    setUp=Base.setUp
    tearDown=Base.tearDown
    call=Base.call
    watched=Base.watched
    open=Base.open
    blocked_close=Base.blocked_close
    def prepare(self):
        return f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True,canonical_api=True))
    def published(self):
        c=self.prepare();self.call(c.publish_api_adapter);return c
    def active(self):
        c=self.published();self.call(c.activate_admission);return c
    def admit(self,c,*,request='owned-request',session='owned-api',text='offline API input'):
        from gateway.session_api_turn import admit_api_turn_async
        async def invoke():
            try:return await admit_api_turn_async(c._adapter,session_id=session,request_id=request,user_message=text,conversation_history=[])
            finally:
                await asyncio.sleep(0)
                jobs=list(getattr(c._binding._authority,'_mutation_tasks',()))
                if jobs:await asyncio.gather(*jobs,return_exceptions=True)
                await asyncio.sleep(0)
        return f.LOOP.run_until_complete(invoke())
    def settle_leaf(self,c):
        authority,ref,row=self.admit(c)
        claimed=f.RT.claim_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,session_id=ref.session_id,_guard=authority._admission_gate())
        done=f.RT.settle_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,admission_id=row['admission_id'],generation=claimed['generation'],outcome='completed')
        self.assertEqual(done['status'],'terminal');return authority,ref,row
    def dumps(self):return [hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest() for c in self.f.connections]
    def finish(self,c):self.call(c.begin_drain);self.call(c.finish_drain)
    def test_strict_explicit_options_reject_before_reservation(self):
        for local,canonical in ((False,True),(True,1),(True,0),(True,None),(True,'true')):
            with self.subTest(local=local,canonical=canonical),self.assertRaises(f.startup.StoreStartupRejected):
                f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=local,canonical_api=canonical))
            self.assertIsNone(self.o._prepared_consumer)
        self.o.close()
    def test_old_selection_never_auto_qualifies_latest_native(self):
        with self.assertRaises(f.consumer.PreparedConsumerRejected):f.LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True))
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.blocked_close()
    def test_prepare_selects_same_three_connections_without_publication(self):
        with self.watched():c=self.prepare();self.call(c.check)
        self.assertIs(c._owner,self.o);self.assertIs(self.o._prepared_consumer,c)
        self.assertTrue(all(x is y for x,y in zip(c._connections,self.f.connections)))
        self.assertEqual(c._selected_feature,'5ff88189832c3ff71bf8fd2f6b2ff05bb8bb4979')
        self.assertEqual((c._publication_phase,c._bundle._publication_state),('NEW','NEW'));self.assertEqual(c._runner.adapters,{})
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.activate_admission)
        f.LOOP.run_until_complete(c.detach());self.open();self.o.close()
    def test_publish_is_native_exact_owner_and_no_sql_mutation(self):
        c=self.prepare();before=self.dumps()
        with self.watched():r=self.call(c.publish_api_adapter);self.call(c.check)
        from gateway.config import Platform
        self.assertIs(c._runner.adapters[Platform.API_SERVER],c._adapter)
        self.assertEqual(r['canonicalApiPublicationState'],'PUBLISHED');self.assertFalse(r['localAdmissionOpen'])
        self.assertEqual(before,self.dumps());self.assertFalse((self.home/'gateway_state.json').exists());self.blocked_close()
    def test_prepared_published_detach_without_activation_preserves_owner(self):
        c=self.published()
        with self.watched():f.LOOP.run_until_complete(c.detach())
        self.assertEqual((c._stage,c._publication_phase,c._binding._stage),('DETACHED','WITHDRAWN','DETACHED'))
        self.assertEqual(c._runner.adapters,{});self.open();self.o.close()
    def test_full_empty_lifecycle_and_final_close_recheck(self):
        c=self.active()
        with self.watched():self.finish(c);f.LOOP.run_until_complete(c.detach());c.assert_store_closeable(self.o)
        self.open();self.assertEqual(tuple(self.f.connections[0].execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),(1,'s124b1-owned'))
        self.o.close();self.assertTrue(self.f.owner.owns(self.home))
        for conn in self.f.connections:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.f.owner.close()
    def test_direct_native_publication_cannot_impersonate_consumer(self):
        c=self.prepare();self.call(c._bundle.publish_api_adapter)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.check)
        self.assertEqual((c._publication_phase,c._bundle._publication_state),('NEW','PUBLISHED'));self.blocked_close()
    def test_duplicate_publish_and_active_publish_refuse(self):
        c=self.published()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.publish_api_adapter)
        self.call(c.activate_admission)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.publish_api_adapter)
        self.assertEqual(c._admission_phase,'ACTIVE');self.blocked_close()
    def test_other_event_loop_cannot_publish(self):
        c=self.prepare()
        async def foreign():return c.publish_api_adapter()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):f.OTHER.run_until_complete(foreign())
        self.assertEqual(c._publication_phase,'NEW');self.assertEqual(c._runner.adapters,{})
    def test_current_registry_identity_not_only_same_dictionary_contents(self):
        c=self.published();old=c._runner.adapters;c._runner.adapters=dict(old)
        try:
            with self.assertRaises(Exception):self.call(c.check)
            self.blocked_close()
        finally:c._runner.adapters=old
        self.call(c.check)
    def test_retired_registry_replacement_blocks_original_store_close(self):
        c=self.active();self.finish(c);f.LOOP.run_until_complete(c.detach());old=c._runner.adapters;c._runner.adapters={}
        try:self.blocked_close()
        finally:c._runner.adapters=old
        self.o.close()
    def test_actual_api_admission_stays_queued_and_blocks_clean_finish(self):
        c=self.active();a,ref,row=self.admit(c)
        self.assertIs(a,c._binding._authority);self.assertEqual(row['status'],'queued');self.assertIs(c._runner._adapter_for_source(a.sessions[ref.session_id].source),c._adapter)
        with self.watched():self.call(c.check);self.call(c.begin_drain);self.call(c.check)
        with self.assertRaises(Exception):self.call(c.finish_drain)
        with self.assertRaises(Exception):self.call(c.retire_idle_api_sessions)
        self.assertEqual(f.RT.get_session_admission(self.f.stores[0],admission_id=row['admission_id'])['status'],'queued');self.blocked_close()
        OBS.append({'case':self._testMethodName,'realApiAdmission':True,'actualOwnerSame':True,'queuedPayloadExecuted':False,'queuedRowRetained':True})
    def test_exact_retry_same_id_and_changed_body_conflict(self):
        c=self.active();first=self.admit(c);again=self.admit(c)
        self.assertEqual(first[2]['admission_id'],again[2]['admission_id'])
        with self.assertRaises(f.RT.RuntimeStoreError):self.admit(c,text='other')
        self.assertEqual(self.f.connections[0].execute('SELECT COUNT(*) FROM session_admissions').fetchone()[0],1)
        self.assertFalse((self.home/'gateway_state.json').exists())
    def test_leaf_settlement_native_retirement_preserves_durable_history(self):
        c=self.active();a,ref,row=self.settle_leaf(c);self.call(c.begin_drain);before=self.dumps()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.finish_drain)
        with self.watched():r=self.call(c.retire_idle_api_sessions);self.call(c.finish_drain);f.LOOP.run_until_complete(c.detach())
        self.assertEqual(r['retiredCount'],1);self.assertFalse(r['durableDataChanged']);self.assertEqual(before,self.dumps())
        self.assertIsNotNone(self.f.stores[0].get_session(ref.session_id));self.assertEqual(f.RT.get_session_admission(self.f.stores[0],admission_id=row['admission_id'])['status'],'terminal')
        self.open();self.o.close();OBS.append({'case':self._testMethodName,'actualApiAdmitted':True,'leafSettlementExplicitNotPayloadExecution':True,'nativeRetirementOnlyMemory':True,'originalOwnerClosesAfterDetach':True})
    def test_retirement_requires_seal_and_does_not_cancel_queued_work(self):
        c=self.active();self.admit(c)
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.retire_idle_api_sessions)
        self.assertEqual(c._admission_phase,'ACTIVE');self.assertEqual(len(c._binding._authority.sessions),1)
    def test_unknown_native_import_blocks_before_publication(self):
        from types import SimpleNamespace
        c=self.prepare();name='i133_unlisted';sys.modules[name]=SimpleNamespace(__file__=str(f.NATIVE/'unlisted_i133.py'))
        try:
            with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.publish_api_adapter)
            self.assertEqual(c._publication_phase,'NEW');self.assertEqual(c._runner.adapters,{})
        finally:del sys.modules[name]
    def test_trace_fault_after_native_publication_retains_unknown(self):
        import gateway_consumer_api as api
        c=self.prepare();old=sys.gettrace();hits=[]
        def trace(frame,event,arg):
            if event=='line' and frame.f_code is api.publish.__code__ and c._bundle._publication_state=='PUBLISHED' and c._publication_phase=='NEW' and not hits:
                hits.append(True);raise RuntimeError('owned post-native-publication fault')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(RuntimeError):self.call(c.publish_api_adapter)
        finally:sys.settrace(old)
        self.assertEqual(hits,[True]);self.assertEqual((c._stage,c._publication_phase),('PUBLICATION_UNKNOWN','UNKNOWN'));self.blocked_close()
    def test_trace_fault_after_native_retirement_retains_unknown(self):
        import gateway_consumer_api as api
        c=self.active();self.settle_leaf(c);self.call(c.begin_drain);before=self.dumps();self.assertEqual(len(c._binding._authority.sessions),1)
        old=sys.gettrace();hits=[]
        def trace(frame,event,arg):
            if event=='line' and frame.f_code is api.retire_idle_sessions.__code__ and 'receipt' in frame.f_locals and not hits:
                hits.append(True);raise RuntimeError('owned post-native-retirement receipt loss')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(RuntimeError):self.call(c.retire_idle_api_sessions)
        finally:sys.settrace(old)
        self.assertEqual(hits,[True]);self.assertEqual(before,self.dumps());self.assertEqual(c._binding._authority.sessions,{})
        self.assertEqual((c._stage,c._admission_phase),('ADMISSION_UNKNOWN','UNKNOWN'))
        self.blocked_close()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.finish_drain)
    def test_open_transactions_allow_seal_but_never_release(self):
        c=self.active()
        for conn in self.f.connections:conn.execute('BEGIN IMMEDIATE')
        try:
            self.call(c.begin_drain)
            self.assertTrue(all(conn.in_transaction for conn in self.f.connections));self.assertEqual(c._admission_phase,'DRAINING')
            with self.assertRaises(f.consumer.PreparedConsumerRejected):self.call(c.finish_drain)
            self.blocked_close()
        finally:
            for conn in self.f.connections:conn.rollback()
    def test_cancelled_cleanup_keeps_published_entry_and_owner(self):
        c=self.active();self.finish(c);entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release);real=c._adapter._memory_sessions
        class Memory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(10):raise TimeoutError('test release')
                    real.close_all()
                finally:done.set()
        c._adapter._memory_sessions=Memory()
        async def trial():
            task=asyncio.create_task(c.detach())
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertFalse(done.is_set());self.assertEqual(c._bundle._publication_state,'PUBLISHED')
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:f.LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));c._adapter._memory_sessions=real
        self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.blocked_close()
        with self.assertRaises(f.consumer.PreparedConsumerRejected):f.LOOP.run_until_complete(c.detach())
    def test_late_replay_during_await_never_withdraws_registration(self):
        c=self.active();self.finish(c);entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release);real=c._adapter._memory_sessions
        class Memory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(10):raise TimeoutError('test release')
                    real.close_all()
                finally:done.set()
        c._adapter._memory_sessions=Memory()
        async def trial():
            task=asyncio.create_task(c.detach())
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());self.f.stores[1].reserve('test','late','f'*64,'late',{'status':'running'});release.set()
                with self.assertRaises(Exception):await task
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:f.LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));c._adapter._memory_sessions=real
        self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.assertEqual(c._bundle._publication_state,'PUBLISHED');self.blocked_close()
    def test_late_response_after_detach_blocks_owner_close(self):
        c=self.active();self.finish(c);f.LOOP.run_until_complete(c.detach());db=self.f.connections[2]
        db.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('late',?,1,'null')",('a'*64,));db.commit()
        self.blocked_close();self.assertEqual(c._stage,'DETACHED')
    def test_service_model_and_full_worker_permissions_are_still_false(self):
        c=self.active();s=c.status()
        for name in ('serviceStarted','runtimeAdmissionAuthorized','activeTaskObserversQualified','fullD3BAccepted','workHealthEvaluated'):self.assertFalse(s[name],name)
        with self.assertRaises(Exception):f.LOOP.run_until_complete(c._runner.start())
        with self.assertRaises(Exception):f.LOOP.run_until_complete(c._adapter.connect())
        self.blocked_close()

def main():
    f.ActiveOwnerCases=OwnerPublication
    code=f.main()
    out=Path(sys.argv[sys.argv.index('--output')+1]);r=json.loads((out/'result.json').read_text(encoding='utf-8'))
    names=['packages/claw-hermes/'+n for n in ('gateway_store_startup.py','gateway_prepared_consumer.py','gateway_consumer_admission.py','gateway_consumer_api.py')]+['config/canonical-api-consumer-i133p1-sources.json','scripts/qa/i133c6_native_owner_publication.py']
    r.update(result='PASS_INDEPENDENT_CANONICAL_API_OWNER_WITH_OS_DOUBLES' if code==0 else 'FAIL',nativeFeature='5ff88189832c3ff71bf8fd2f6b2ff05bb8bb4979',driverSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),currentSourceHashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},observations=OBS,actualProgrammaticApiAdmission=True,nativeProductMethodsReplaced=False,traceFaultsAndMemoryCleanupFixtureExplicit=True,wholeApiTurnOrAgentExecuted=False)
    (out/'independent-result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k not in ('nativeImports','sourceHashes','currentSourceHashes','checks','caseEnd','deniedEvents')}),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
