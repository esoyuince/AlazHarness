"""Actual native memory retirement, with no full-agent or whole HTTP claim.

Real API binding/SessionStore/SessionAuthority/caller connections and native leaf
admission, claim, settlement. Deliberate task/container/SQL fault inputs are
labelled and scoped to fresh profiles. No native product method substitutions.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,unittest
from contextlib import contextmanager
from pathlib import Path
BASE=LOOP=OTHER=None
State=Config=Platform=Binding=Runner=Initialize=Bundle=Adapter=Replay=Response=Own=Registry=RT=Reject=RunnerReject=BindApi=RestoreApi=None
WATCH=None;OBS=[];ENDS=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise PermissionError('c130t6_offline_native')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('retirement_opened_database')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('retirement_raw_database_open')

class RetirementCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve();os.environ['HERMES_HOME']=str(self.home)
        Own.reserve([self.home]);self.state=State(self.home/'state.db');self.epoch=RT.begin_runtime_epoch(self.state,instance_id='c130-owned')
        self.replay=Replay(str(self.home/'runs_idempotency.db'));self.response=Response(db_path=str(self.home/'response_store.db'),canonical_state=self.state)
        self.stores=(self.state,self.replay,self.response);self.connections=tuple(s._conn for s in self.stores)
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.binding=Binding(self.config,self.state,epoch=self.epoch,instance_id='c130-owned');self.runner=Runner(self.config,caller_state=self.binding)
        self.authority=LOOP.run_until_complete(Initialize(self.runner));self.store=self.runner.session_store
        self.bundle=Bundle(self.home,*self.stores,prepared_runner=self.runner);self.api=Adapter(Platform(extra={'key':'offline-c130-owned','model_name':'offline'}),borrowed_stores=self.bundle)
        self.threads=[];self.release_events=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        for e in self.release_events:e.set()
        for t in self.threads:t.join(8)
        self.assertFalse(any(t.is_alive() for t in self.threads))
        self.assertFalse([t for t in asyncio.all_tasks(LOOP) if not t.done()])
        stage=self.binding._stage
        for s in reversed(self.stores):
            try:
                if s._conn.in_transaction:s._conn.rollback()
                s.close()
            except sqlite3.ProgrammingError:pass
        Own.close();self.tmp.cleanup();counts=Registry.stats()
        ENDS.append({'case':self._testMethodName,'nativeBeforeFixtureCleanup':stage,'remainingLiveSessions':len(self.authority.sessions),'temporaryProfileRemoved':not self.home.exists(),'profileReleased':not Own.homes,'registry':counts})
        self.assertFalse(self.home.exists());self.assertFalse(Own.homes);self.assertEqual(counts['total_refcounts'],0)
    def call(self,fn,*args):
        async def invoke():return fn(*args)
        return LOOP.run_until_complete(invoke())
    def start(self,sid='s-one'):
        if self.binding._stage=='PREPARED':self.call(self.bundle.activate_admission)
        ref=BindApi(self.authority,sid);self.state.append_message(sid,'user','preserved original transcript')
        return ref,self.authority.sessions[sid]
    def drain(self):return self.call(self.bundle.begin_drain)
    def retire(self):return self.call(self.bundle.retire_idle_api_sessions)
    def finish(self):return self.call(self.bundle.finish_drain)
    def admit(self,sid='s-one',rid='request'):
        return RT.admit_session_input(self.state,epoch=self.epoch,principal_id='api',session_id=sid,request_id=rid,payload={'text':'offline leaf'},_authorize_write=self.authority._admission_gate())
    def complete_leaf(self,sid='s-one'):
        row=self.admit(sid);claimed=RT.claim_session_input(self.state,epoch=self.epoch,session_id=sid,_guard=self.authority._admission_gate())
        return RT.settle_session_input(self.state,epoch=self.epoch,admission_id=row['admission_id'],generation=claimed['generation'],outcome='completed')
    def digest(self):return [hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest() for c in self.connections]
    def intact(self,live,sid='s-one'):
        self.assertIs(self.authority.sessions[sid],live);self.assertIn(live.route,self.store._entries)
        for c in self.connections:self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(Own.owns(self.home))
    @contextmanager
    def watched(self):
        global WATCH
        before=self.digest();changes=[c.total_changes for c in self.connections];record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0};WATCH=record
        try:yield
        finally:
            WATCH=None;self.assertEqual(changes,[c.total_changes for c in self.connections]);self.assertEqual(self.digest(),before)
            record.update(sqlRowChanges=0,allThreeLogicalDatabaseDigestsUnchanged=True);OBS.append(record)
    def refuse(self,live):
        with self.watched(),self.assertRaises((Reject,RunnerReject)):self.retire()
        self.intact(live)
    def pending(self):
        gate=asyncio.Event()
        async def make():return asyncio.create_task(gate.wait())
        return gate,LOOP.run_until_complete(make())
    def endtask(self,gate,task):gate.set();LOOP.run_until_complete(task)
    def test_bound_idle_api_session_drops_only_memory_and_preserves_all_rows(self):
        _,live=self.start();before=self.digest();self.drain()
        with self.assertRaises(Reject):self.finish()
        with self.watched():r=self.retire()
        self.assertEqual((r['state'],r['retiredCount']),('IDLE_API_SESSIONS_RETIRED',1));self.assertFalse(r['drainFinished'])
        self.assertEqual(self.authority.sessions,{});self.assertNotIn(live.route,self.store._entries);self.assertEqual(self.digest(),before)
        with self.watched():self.finish();LOOP.run_until_complete(self.api.disconnect());self.runner.close_all_session_db_handles()
        self.assertEqual(self.binding._stage,'DETACHED');self.assertTrue(Own.owns(self.home));self.assertEqual(self.digest(),before)
    def test_native_claimed_settled_row_and_transcript_survive_retirement(self):
        _,live=self.start();settled=self.complete_leaf();self.assertEqual(settled['status'],'terminal');self.drain()
        with self.watched():self.retire();self.finish()
        self.assertEqual(RT.get_session_admission(self.state,admission_id=settled['admission_id'])['status'],'terminal')
        self.assertIsNotNone(self.state.get_session('s-one'));self.assertEqual(self.state._conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0],1)
    def test_active_and_prepared_refuse_retirement(self):
        with self.assertRaises(Reject):self.retire()
        _,live=self.start();self.refuse(live)
    def test_queued_input_retained_and_finish_blocked(self):
        _,live=self.start();row=self.admit();self.drain();self.refuse(live)
        self.assertEqual(RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'queued')
        with self.assertRaises((Reject,RunnerReject)):self.finish()
    def test_unknown_input_retained_without_recovery(self):
        _,live=self.start();row=self.admit();self.state._conn.execute("UPDATE session_admissions SET status='unknown' WHERE admission_id=?",(row['admission_id'],));self.state._conn.commit();self.drain();self.refuse(live)
        self.assertEqual(RT.get_session_admission(self.state,admission_id=row['admission_id'])['status'],'unknown')
    def test_real_dispatcher_running_is_not_cancelled_or_detached(self):
        _,live=self.start();gate,task=self.pending();live.task=task;self.drain()
        try:self.refuse(live);self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:self.endtask(gate,task)
    def test_normal_completed_dispatcher_can_retire_after_all_workers_gone(self):
        _,live=self.start()
        async def done():return None
        async def create():return asyncio.create_task(done())
        live.task=LOOP.run_until_complete(create());LOOP.run_until_complete(live.task);self.drain()
        with self.watched():self.retire();self.finish()
    def test_cancelled_dispatcher_is_not_mistaken_for_completed(self):
        _,live=self.start();gate,task=self.pending();live.task=task;task.cancel()
        LOOP.run_until_complete(asyncio.gather(task,return_exceptions=True));self.drain();self.refuse(live);self.assertTrue(task.cancelled())
    def test_failed_dispatcher_is_not_silently_retired(self):
        _,live=self.start()
        async def broken():raise RuntimeError('explicit_owned_task_failure')
        async def create():return asyncio.create_task(broken())
        live.task=LOOP.run_until_complete(create());LOOP.run_until_complete(asyncio.gather(live.task,return_exceptions=True));self.drain();self.refuse(live)
    def test_live_controls_subscribers_and_event_observers_all_refuse(self):
        _,live=self.start();self.drain()
        targets=((live,'subscribers',{'x':object()}),(live,'settling',{'x':object()}),(live.controls,'pending',{'x':object()}),(live.controls,'remote_responders',{'x':object()}),(live.event_stream,'execution',{'execution_generation':1}),(live.event_stream,'observers',{object()}),(live.event_stream.fanout,'_peers',[object()]))
        for obj,name,value in targets:
            old=getattr(obj,name);setattr(obj,name,value)
            try:
                with self.subTest(field=name):self.refuse(live)
            finally:setattr(obj,name,old)
    def test_all_sessions_validated_before_first_memory_effect(self):
        _,one=self.start('s-one');_,two=self.start('s-two');two.controls.pending={'fault':object()};self.drain()
        try:self.refuse(one);self.assertIs(self.authority.sessions['s-two'],two)
        finally:two.controls.pending.clear()
        with self.watched():r=self.retire()
        self.assertEqual(r['retiredCount'],2)
    def test_held_facade_mutex_refuses_without_waiting(self):
        _,live=self.start();self.drain();self.store._lock.acquire()
        try:self.refuse(live)
        finally:self.store._lock.release()
    def test_foreign_thread_holding_event_lock_is_not_disrupted(self):
        _,live=self.start();self.drain();ready=threading.Event();release=threading.Event();self.release_events.append(release)
        def held():
            with live.event_stream.lock:ready.set();release.wait(10)
        t=threading.Thread(target=held);self.threads.append(t);t.start();self.assertTrue(ready.wait(5))
        try:self.refuse(live);self.assertTrue(t.is_alive())
        finally:release.set();t.join(5)
    def test_open_transaction_in_each_store_preserved(self):
        _,live=self.start();self.drain()
        for conn in self.connections:
            conn.execute('BEGIN IMMEDIATE')
            try:self.refuse(live);self.assertTrue(conn.in_transaction)
            finally:conn.rollback()
    def test_unsettled_response_and_replay_records_preserved(self):
        _,live=self.start();self.drain();conn=self.response._conn
        conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('pending',?,1,'null')",('a'*64,));conn.commit()
        self.refuse(live);self.assertIsNone(conn.execute("SELECT settled_at FROM response_keys WHERE request_key='pending'").fetchone()[0])
    def test_finished_physical_worker_registry_still_requires_native_retirement(self):
        _,live=self.start();done=threading.Event();done.set();worker=Runner._RunAgentWorker(task_id='owned',worker_done=done)
        self.authority._turn_workers={id(worker):(worker,[None])};self.drain()
        try:self.refuse(live);self.assertIn(id(worker),self.authority._turn_workers)
        finally:self.authority._turn_workers.clear()
    def test_actual_native_waiter_reply_registry_is_not_discarded(self):
        from gateway.session_ingress import waiter_replies
        _,live=self.start();pending=waiter_replies(self.authority);pending['receipt']=object();self.drain()
        try:self.refuse(live);self.assertIn('receipt',pending)
        finally:pending.clear()
    def test_api_observers_refuse_retirement_even_without_transport(self):
        _,live=self.start();self.authority.api_observers={'receipt':[object()]};self.drain()
        try:self.refuse(live)
        finally:self.authority.api_observers.clear()
    def test_durable_binding_drift_keeps_every_memory_entry(self):
        _,live=self.start();self.drain();conn=self.state._conn;key='gateway.api.binding.v1.s-one';old=conn.execute('SELECT value FROM state_meta WHERE key=?',(key,)).fetchone()[0]
        bad=json.loads(old);bad['profile_id']='other';conn.execute('UPDATE state_meta SET value=? WHERE key=?',(json.dumps(bad),key));conn.commit()
        try:self.refuse(live)
        finally:conn.execute('UPDATE state_meta SET value=? WHERE key=?',(old,key));conn.commit()
    def test_route_cache_identity_drift_not_repaired(self):
        _,live=self.start();entry=self.store._entries[live.route];old=entry.session_id;entry.session_id='foreign';self.drain()
        try:self.refuse(live);self.assertEqual(entry.session_id,'foreign')
        finally:entry.session_id=old
    def test_dirty_transcript_and_unsaved_routing_refuse(self):
        _,live=self.start();self.drain();self.store._dirty_transcripts['s-one']=[{'role':'user','content':'pending'}]
        try:self.refuse(live)
        finally:self.store._dirty_transcripts.clear()
        self.store._routing_generation+=1
        try:self.refuse(live)
        finally:self.store._routing_generation-=1
    def test_foreign_event_loop_cannot_retire(self):
        _,live=self.start();self.drain()
        async def other():return self.bundle.retire_idle_api_sessions()
        with self.assertRaises(Reject):OTHER.run_until_complete(other())
        self.intact(live)
    def test_empty_repeat_and_postretirement_rebind_do_not_authorize_close(self):
        self.start();self.drain()
        with self.watched():self.retire();again=self.retire()
        self.assertEqual(again['retiredCount'],0);RestoreApi(self.authority,'s-one')
        with self.assertRaises(Reject):self.finish()
        with self.watched():self.retire();self.finish()
    def test_memory_crash_marker_refuses_without_erasing_route(self):
        _,live=self.start();entry=self.store._entries[live.route];old=entry.active_turn_token;entry.active_turn_token='owned-live-marker';self.drain()
        try:self.refuse(live);self.assertEqual(entry.active_turn_token,'owned-live-marker')
        finally:entry.active_turn_token=old
    def test_durable_crash_marker_refuses_without_rewriting_json(self):
        _,live=self.start();self.drain();conn=self.state._conn;old=conn.execute("SELECT entry_json FROM gateway_routing WHERE scope='' AND session_key=?",(live.route,)).fetchone()[0]
        changed=json.loads(old);changed['active_turn_token']='durable-owned-marker';conn.execute("UPDATE gateway_routing SET entry_json=? WHERE scope='' AND session_key=?",(json.dumps(changed),live.route));conn.commit()
        try:self.refuse(live);self.assertIn('durable-owned-marker',conn.execute("SELECT entry_json FROM gateway_routing WHERE scope='' AND session_key=?",(live.route,)).fetchone()[0])
        finally:conn.execute("UPDATE gateway_routing SET entry_json=? WHERE scope='' AND session_key=?",(old,live.route));conn.commit()
    def test_changed_live_source_does_not_get_retired_as_original_profile(self):
        _,live=self.start();old=live.source.profile;live.source.profile='foreign-profile';self.drain()
        try:self.refuse(live);self.assertEqual(live.source.profile,'foreign-profile')
        finally:live.source.profile=old
    def test_trace_interruption_after_first_memory_effect_retains_unknown(self):
        from gateway.run_borrowed_retirement import _retire_idle_api_sessions
        self.start('s-one');self.start('s-two');self.drain();before=self.digest();armed=True;original=sys.gettrace()
        def interrupt(frame,event,arg):
            nonlocal armed
            if (armed and event=='line' and frame.f_code is _retire_idle_api_sessions.__code__
                    and self.binding._stage=='RETIRING_SESSIONS' and len(self.authority.sessions)==1):
                armed=False
                raise RuntimeError('explicit trace fault after actual memory retirement effect')
            return interrupt
        try:
            sys.settrace(interrupt)
            with self.assertRaisesRegex(RuntimeError,'explicit trace fault'):self.retire()
        finally:sys.settrace(original)
        self.assertFalse(armed);self.assertEqual(self.binding._stage,'ADMISSION_UNKNOWN')
        self.assertEqual(len(self.authority.sessions),1);self.assertEqual(self.digest(),before)
        for operation in (self.retire,self.finish):
            with self.assertRaises((Reject,RunnerReject)):operation()
        with self.assertRaises((Reject,RunnerReject)):LOOP.run_until_complete(self.api.disconnect())
        with self.assertRaises((Reject,RunnerReject)):self.runner.close_all_session_db_handles()
        self.assertEqual(self.bundle._stage,'ATTACHED');self.assertTrue(Own.owns(self.home))
        for conn in self.connections:self.assertEqual(conn.execute('SELECT 1').fetchone()[0],1)
    def test_default_service_and_listener_are_not_activated(self):
        self.start();self.drain();self.retire();self.finish()
        with self.assertRaises(Reject):LOOP.run_until_complete(self.api.connect())
        with self.assertRaises(RunnerReject):LOOP.run_until_complete(self.runner.start())
        self.assertFalse(self.runner._running);self.assertFalse(self.api._running)

def main():
    global BASE,LOOP,OTHER,State,Config,Platform,Binding,Runner,Initialize,Bundle,Adapter,Replay,Response,Own,Registry,RT,Reject,RunnerReject,BindApi,RestoreApi
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',action='append');a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();OTHER=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-c130t6-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'imports';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),APPDATA=str(BASE),LOCALAPPDATA=str(BASE));sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.config import GatewayConfig,PlatformConfig
        from gateway.run_borrowed_state import CallerOwnedRunnerState,BorrowedRunnerRejected
        from gateway.run import GatewayRunner
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.runtime_ownership import process_ownership
        from gateway.session_api import bind_api_session,restore_api_session
        import hermes_state_registry,hermes_state_runtime
        State,Config,Platform,Binding,Runner,Initialize=SessionDB,GatewayConfig,PlatformConfig,CallerOwnedRunnerState,GatewayRunner,initialize_gateway_runtime
        Bundle,Adapter,Replay,Response,Own,Registry,RT,Reject,RunnerReject=BorrowedAPIStores,APIServerAdapter,RunIdempotencyStore,ResponseStore,process_ownership,hermes_state_registry,hermes_state_runtime,BorrowedStoreRejected,BorrowedRunnerRejected
        BindApi,RestoreApi=bind_api_session,restore_api_session
        suite=unittest.TestSuite(RetirementCases(name) for name in a.case) if a.case else unittest.defaultTestLoader.loadTestsFromTestCase(RetirementCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close();OTHER.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            file=getattr(mod,'__file__',None)
            if file:
                path=Path(file).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        result={'result':'PASS_NATIVE_MEMORY_RETIREMENT_ONLY' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'observations':OBS,'caseEnd':ENDS,'actualNativeApiBindingAndStores':True,'nativeProductMethodsReplaced':False,'directNativeLeafSettlementNotAgentExecution':True,'faultFixturesUseExplicitMemoryOrSqlInputs':True,'explicitPartialEffectTraceFault':True,'completeApiRequestOrWorkerExecuted':False,'sameHarnessOwnerQualified':False,'newLinuxIsolationAccepted':False,'providerCalls':0,'rootWslAction':False}
    result['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeImports','observations','caseEnd')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-16000:],flush=True)
    return 0 if r.wasSuccessful() and result['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
