"""Real native prepared join. One explicit empty memory-cleanup fault object.
No native store/runner methods replaced; service/admission remain unqualified.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,traceback,unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
State=Replay=Response=Bundle=Adapter=Config=PlatformConfig=Runner=Binding=None
Rejected=RunnerRejected=Ownership=Registry=Runtime=Constants=Initialize=StartApi=None
BASE=LOOP=WATCH=None
OBS=[];CLEAN=[];DENIED=[]
def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('a123c6_offline_native_acceptance')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('extra SQLite open')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if name in ('state.db','runs_idempotency.db','response_store.db') or any(name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('raw database open')
class NativeThreeJoin(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        os.environ['HERMES_HOME']=str(self.home);Ownership.reserve([self.home])
        self.state=State(self.home/'state.db');self.epoch=Runtime.begin_runtime_epoch(self.state,instance_id='a123c6-native')
        self.replay=Replay(str(self.home/'runs_idempotency.db'));self.response=Response(db_path=str(self.home/'response_store.db'),canonical_state=self.state)
        self.stores=(self.state,self.replay,self.response)
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.owner=Binding(self.config,self.state,epoch=self.epoch,instance_id='a123c6-native')
        self.runner=Runner(self.config,caller_state=self.owner);self.authority=LOOP.run_until_complete(Initialize(self.runner))
        self.api_config=PlatformConfig(enabled=True,extra={'host':'127.0.0.1','port':8642,'key':'owned-not-secret','model_name':'fixture'})
        self.bundle=self.adapter=None;self.tasks=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        for task in self.tasks:
            if not task.done():task.cancel()
        if self.tasks:LOOP.run_until_complete(asyncio.gather(*self.tasks,return_exceptions=True))
        for store in self.stores:
            try:
                if store._conn is not None and store._conn.in_transaction:store._conn.rollback()
            except sqlite3.Error:pass
        if self.adapter is not None:
            try:LOOP.run_until_complete(self.adapter.disconnect())
            except (Rejected,RunnerRejected,RuntimeError):pass # deliberate failed/closed test fixture retained
        try:self.runner.close_all_session_db_handles()
        except (Rejected,RunnerRejected):pass
        for store in reversed(self.stores):store.close()
        Ownership.close();counts=Registry.stats();pending=[t for t in asyncio.all_tasks(LOOP) if not t.done()]
        self.tmp.cleanup();CLEAN.append({'case':self._testMethodName,'temporaryProfileRemoved':not self.home.exists(),'profileReleased':not Ownership.homes,'registry':counts,'pendingTasks':len(pending)})
        self.assertFalse(self.home.exists());self.assertFalse(Ownership.homes);self.assertEqual(len(pending),0)
        self.assertEqual(counts,{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    @contextmanager
    def observed(self,*,closed=False):
        global WATCH
        conns=[] if closed else [s._conn for s in self.stores]
        before=[c.total_changes for c in conns];registry=Registry.stats();queries=[]
        for c in conns:c.set_trace_callback(queries.append)
        record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0};WATCH=record
        try:yield
        finally:
            WATCH=None
            for c in conns:c.set_trace_callback(None)
            self.assertEqual([c.total_changes for c in conns],before);self.assertEqual(Registry.stats(),registry)
            self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries),queries)
            record.update(sqlRowChanges=0,queryCount=len(queries));OBS.append(record)
    def build(self):
        self.bundle=Bundle(self.home,*self.stores,prepared_runner=self.runner)
        self.adapter=Adapter(self.api_config,borrowed_stores=self.bundle);return self.adapter
    def alive(self):
        for store in self.stores:self.assertEqual(store._conn.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(Ownership.owns(self.home))
    def select(self):return self.bundle.select(self.adapter,self.home)
    def test_real_join_has_same_three_handles_no_epoch_or_row_change(self):
        before=tuple(self.state._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone())
        with self.observed():a=self.build();selected=self.select()
        for expected,actual in zip(self.stores,selected):self.assertIs(expected,actual)
        self.assertIs(a.gateway_runner,self.runner);self.assertIs(self.runner._session_db._db,self.state)
        self.assertIs(self.authority.db,self.state);self.assertIs(self.response._canonical_state._state,self.state)
        self.assertEqual(tuple(self.state._conn.execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),before)
    def test_actual_sync_async_and_response_selectors_keep_caller_objects(self):
        a=self.build()
        with self.observed():
            self.assertIs(a._ensure_session_db(),self.state);self.assertIs(LOOP.run_until_complete(a._ensure_session_db_async()),self.state)
            self.assertIs(a._current_response_store(),self.response);self.assertIs(a._open_and_cache_session_db(self.home),self.state)
        self.assertFalse(a._session_dbs);self.assertFalse(a._response_stores)
    def test_local_epoch_binding_matches_caller_path_and_epoch(self):
        self.build();s=self.runner.session_store
        with self.observed():self.select()
        self.assertEqual(s._local_authority_epoch,self.epoch);self.assertEqual(s._local_authority_epochs,{self.home/'state.db':self.epoch})
    def test_local_epoch_copy_wrong_value_extra_home_and_bool_refused(self):
        self.build();s=self.runner.session_store;old=s._local_authority_epochs
        for new in (dict(old),{self.home/'state.db':self.epoch+1},{self.home/'state.db':True},{**old,self.home/'other.db':self.epoch}):
            s._local_authority_epochs=new
            try:
                with self.subTest(value=new),self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.select()
            finally:s._local_authority_epochs=old
        old=s._local_authority_epoch;s._local_authority_epoch=True
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.select()
        finally:s._local_authority_epoch=old
    def test_default_bundle_still_rejects_direct_runner_assignment(self):
        self.bundle=Bundle(self.home,*self.stores);self.adapter=Adapter(self.api_config,borrowed_stores=self.bundle);self.adapter.gateway_runner=self.runner
        try:
            with self.observed(),self.assertRaisesRegex(Rejected,'runner_conflict'):self.select()
        finally:self.adapter.gateway_runner=None
    def test_non_native_prepared_runner_not_accepted(self):
        with self.observed(),self.assertRaises(Rejected):Bundle(self.home,*self.stores,prepared_runner=object())
        self.assertIsNone(self.owner._api_bundle)
    def test_only_one_bundle_can_claim_prepared_runner(self):
        self.build()
        with self.observed(),self.assertRaises(Rejected):Bundle(self.home,*self.stores,prepared_runner=self.runner)
        self.assertIs(self.owner._api_bundle,self.bundle)
    def test_only_one_adapter_can_claim_bundle(self):
        self.build()
        with self.observed(),self.assertRaises(Rejected):Adapter(self.api_config,borrowed_stores=self.bundle)
        self.assertIs(self.bundle._adapter,self.adapter)
    def test_runner_cannot_detach_before_api(self):
        self.build()
        with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
        self.assertEqual(self.owner.status()['state'],'PREPARED');self.assertEqual(self.bundle.status()['state'],'ATTACHED');self.alive()
    def test_ordered_detach_keeps_all_caller_stores_and_profile(self):
        self.build()
        with self.observed():
            LOOP.run_until_complete(self.adapter.disconnect());LOOP.run_until_complete(self.adapter.disconnect())
            self.assertEqual(self.bundle.status()['state'],'DETACHED');self.alive()
            self.runner.close_all_session_db_handles();self.runner.close_all_session_db_handles()
        self.assertEqual(self.owner.status()['state'],'DETACHED');self.alive()
    def test_each_open_transaction_blocks_selection_and_detach_no_rollback(self):
        self.build()
        for store in self.stores:
            store._conn.execute('BEGIN IMMEDIATE')
            try:
                with self.subTest(store=type(store).__name__),self.observed():
                    with self.assertRaises((Rejected,RunnerRejected)):self.select()
                    with self.assertRaises((Rejected,RunnerRejected)):LOOP.run_until_complete(self.adapter.disconnect())
                    with self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
                self.assertTrue(store._conn.in_transaction);self.assertEqual(self.bundle.status()['state'],'ATTACHED')
            finally:store._conn.rollback()
    def test_replay_lock_contention_is_nonblocking_and_not_unlocked(self):
        self.build();self.replay._lock.acquire()
        try:
            with self.observed(),self.assertRaises(Rejected):self.select()
            self.assertTrue(self.replay._lock.locked())
        finally:self.replay._lock.release()
        with self.observed():self.select()
    def test_pending_adapter_task_is_retained_not_cancelled(self):
        self.build()
        async def scenario():
            done=asyncio.Event();task=asyncio.create_task(done.wait());self.tasks.append(task);self.adapter._background_tasks.add(task)
            try:
                with self.observed(),self.assertRaises(Rejected):await self.adapter.disconnect()
                self.assertFalse(task.done());self.assertFalse(task.cancelled())
            finally:done.set();await task;self.adapter._background_tasks.remove(task)
        LOOP.run_until_complete(scenario());self.alive()
    def test_replaced_adapter_store_not_relearned(self):
        self.build();old=self.adapter._response_store;self.adapter._response_store=object()
        try:
            with self.observed(),self.assertRaises(Rejected):self.select()
        finally:self.adapter._response_store=old
    def test_replaced_connection_is_not_adopted(self):
        self.build();old=self.replay._conn;fake=sqlite3.connect(':memory:');self.replay._conn=fake
        try:
            with self.observed(),self.assertRaises(Rejected):self.select()
        finally:self.replay._conn=old;fake.close()
    def test_closed_response_cannot_reopen_or_detach_runner(self):
        self.build();self.response.close()
        with self.observed(closed=True):
            with self.assertRaises((Rejected,RunnerRejected)):self.select()
            with self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
    def test_foreign_scope_refused_without_new_profile(self):
        self.build();foreign=self.home/'foreign';token=Constants.set_hermes_home_override(foreign)
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.adapter._ensure_session_db()
            self.assertFalse(foreign.exists())
        finally:Constants.reset_hermes_home_override(token)
    def test_each_replay_response_generation_change_refused(self):
        self.build()
        for store in (self.replay,self.response):
            old=store._conn.execute('PRAGMA application_id').fetchone()[0];store._conn.execute('PRAGMA application_id='+str(old+1))
            try:
                with self.subTest(store=type(store).__name__),self.observed(),self.assertRaises(Rejected):self.select()
            finally:store._conn.execute('PRAGMA application_id='+str(old))
    def test_changed_authority_or_descriptor_refused(self):
        self.build();a=self.authority;old=a.epoch;a.epoch+=1
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.select()
        finally:a.epoch=old
        old=self.runner.session_runtime_descriptor;self.runner.session_runtime_descriptor=dict(old)
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.select()
        finally:self.runner.session_runtime_descriptor=old
    def test_listener_service_and_authority_admission_remain_closed(self):
        self.build();before=len(DENIED)
        with self.observed():
            for op in (self.adapter.connect,self.runner.start,self.runner.stop,lambda:StartApi(self.runner)):
                with self.assertRaises((Rejected,RunnerRejected)):LOOP.run_until_complete(op())
            with self.assertRaises(Runtime.RuntimeStoreError):self.authority._require_admission_open()
        self.assertEqual(len(DENIED),before);self.assertIsNone(self.adapter._site);self.assertIsNone(self.adapter._app)
        self.assertTrue(self.authority.retiring);self.assertTrue(self.runner._draining);self.assertFalse(self.runner._running)
    def test_cleanup_fault_retains_unknown_ownership_no_retry(self):
        self.build();old=self.adapter._memory_sessions
        def fault():raise RuntimeError('owned cleanup fault fixture')
        self.adapter._memory_sessions=SimpleNamespace(close_all=fault)
        try:
            with self.observed(),self.assertRaises(RuntimeError):LOOP.run_until_complete(self.adapter.disconnect())
        finally:self.adapter._memory_sessions=old
        self.assertEqual(self.bundle.status()['state'],'CLOSE_UNKNOWN')
        with self.observed():
            with self.assertRaises((Rejected,RunnerRejected)):LOOP.run_until_complete(self.adapter.disconnect())
            with self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
        self.alive()
    def test_construction_failure_retains_claim_not_reusable(self):
        self.bundle=Bundle(self.home,*self.stores,prepared_runner=self.runner);old=self.authority.epoch;self.authority.epoch+=1
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):Adapter(self.api_config,borrowed_stores=self.bundle)
        finally:self.authority.epoch=old
        self.assertEqual(self.bundle.status()['state'],'ATTACHED');self.assertFalse(self.bundle._prepared_adapter_ready)
        with self.observed(),self.assertRaises(Rejected):Adapter(self.api_config,borrowed_stores=self.bundle)
        with self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
    def test_prepared_bundle_requires_exact_state_not_other_home(self):
        other=self.home/'other';other.mkdir();Ownership.reserve([other]);old=os.environ['HERMES_HOME'];os.environ['HERMES_HOME']=str(other)
        state=State(other/'state.db');replay=Replay(str(other/'runs_idempotency.db'));response=Response(db_path=str(other/'response_store.db'),canonical_state=state)
        try:
            with self.observed(),self.assertRaises((Rejected,RunnerRejected)):Bundle(other,state,replay,response,prepared_runner=self.runner)
        finally:
            for s in (response,replay,state):s.close()
            os.environ['HERMES_HOME']=old;Ownership.release(other)
        self.assertIsNone(self.owner._api_bundle)
    def test_profile_reacquire_does_not_adopt_old_bundle(self):
        self.build();Ownership.close();Ownership.reserve([self.home])
        with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.select()
    def test_detached_adapter_never_reopens_or_selects(self):
        self.build();LOOP.run_until_complete(self.adapter.disconnect())
        with self.observed():
            with self.assertRaises(Rejected):self.adapter._ensure_session_db()
            with self.assertRaises(Rejected):self.adapter._current_response_store()
        self.alive()
    def test_unclaimed_prepared_bundle_retains_runner(self):
        self.bundle=Bundle(self.home,*self.stores,prepared_runner=self.runner)
        with self.observed(),self.assertRaises((Rejected,RunnerRejected)):self.runner.close_all_session_db_handles()
        self.assertEqual(self.bundle.status()['state'],'NEW');self.alive()
    def test_wrong_actor_cannot_select_or_release(self):
        self.build();result=[]
        def other():
            try:self.select()
            except Rejected:result.append('refused')
        with self.observed():thread=threading.Thread(target=other);thread.start();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(result,['refused']);self.alive()
def main():
    global State,Replay,Response,Bundle,Adapter,Config,PlatformConfig,Runner,Binding,Rejected,RunnerRejected,Ownership,Registry,Runtime,Constants,Initialize,StartApi,BASE,LOOP
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case');args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-a123c6-suite-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),APPDATA=str(BASE/'roaming'),LOCALAPPDATA=str(BASE/'local'))
        sys.path.insert(0,str(native));LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP);sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig,PlatformConfig as PC
        from gateway.run_borrowed_state import CallerOwnedRunnerState,BorrowedRunnerRejected
        from gateway.run_runtime import initialize_gateway_runtime,start_gateway_runtime_api
        from gateway.runtime_ownership import process_ownership
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        import hermes_state_registry,hermes_state_runtime,hermes_constants
        State,Replay,Response,Bundle,Adapter,Config,PlatformConfig,Runner,Binding=SessionDB,RunIdempotencyStore,ResponseStore,BorrowedAPIStores,APIServerAdapter,GatewayConfig,PC,GatewayRunner,CallerOwnedRunnerState
        Rejected,RunnerRejected,Ownership,Registry,Runtime,Constants=BorrowedStoreRejected,BorrowedRunnerRejected,process_ownership,hermes_state_registry,hermes_state_runtime,hermes_constants
        Initialize,StartApi=initialize_gateway_runtime,start_gateway_runtime_api
        suite=unittest.TestSuite([NativeThreeJoin(args.case)]) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(NativeThreeJoin)
        try:
            with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        finally:LOOP.run_until_complete(LOOP.shutdown_asyncgens());LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close()
        imports={}
        for module in tuple(sys.modules.values()):
            filename=getattr(module,'__file__',None)
            if filename:
                q=Path(filename).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        failures={t.id().split(' (',1)[0] for t,_ in result.failures+result.errors}
        report={'result':'PASS_NATIVE_PREPARED_THREE_STORE_JOIN' if result.wasSuccessful() else 'FAIL','total':result.testsRun,'passed':result.testsRun-len(failures)-len(result.skipped),'failedMethods':len(failures),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'failureIds':[t.id() for t,_ in result.failures],'errorIds':[t.id() for t,_ in result.errors],
            'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'observations':OBS,'cleanup':CLEAN,'deniedImportProbes':DENIED,
            'actualNativeRunnerAndAdapterAndThreeStores':True,'nativeProductMethodsReplaced':False,'oneCleanupObjectReplacedForExplicitFault':True,
            'profileMountOrLinuxIsolationTested':False,'activeWorkOrModelTested':False,'httpListenerStarted':False,'providerCalls':0,'rootWslAction':False}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','observations','cleanup','deniedImportProbes')}),flush=True)
    if not result.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-20000:],flush=True)
    return 0 if result.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
