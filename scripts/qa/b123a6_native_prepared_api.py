"""Actual prepared runner + borrowed API join, no service or model invocation."""
import argparse,asyncio,hashlib,json,os,sys,tempfile,traceback,unittest
from contextlib import contextmanager
from pathlib import Path
State=Runner=Config=Bind=RejectRunner=Own=Registry=Runtime=Init=None
Bundle=RejectStore=Adapter=PlatformConfig=Replay=Response=Constants=None
BASE=LOOP=None;WATCH=None
CHECKS=[];ENDS=[];DENIED=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('b123a6_offline_test')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['sqliteOpens']+=1;raise AssertionError('unexpected_sqlite_open')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name.lower()
            if any(name==s or name.startswith(s+'-') for s in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('unexpected_raw_database_open')

class PreparedAPICases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        os.environ['HERMES_HOME']=str(self.home);Own.reserve([self.home]);self.state=State(self.home/'state.db')
        self.epoch=Runtime.begin_runtime_epoch(self.state,instance_id='b123a6-owned')
        self.replay=Replay(str(self.home/'runs_idempotency.db'))
        self.response=Response(db_path=str(self.home/'response_store.db'),canonical_state=self.state)
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.binding=Bind(self.config,self.state,epoch=self.epoch,instance_id='b123a6-owned')
        self.runner=Runner(self.config,caller_state=self.binding);self.authority=LOOP.run_until_complete(Init(self.runner))
        self.adapters=[];self.bundle=None
    def tearDown(self):
        global WATCH
        WATCH=None
        for store in (self.state,self.replay,self.response):
            try:
                if store._conn.in_transaction:store._conn.rollback() # own deliberately injected test transaction only
            except Exception:pass
        for a in self.adapters:
            if a._borrowed_api_stores._stage=='ATTACHED':
                try:LOOP.run_until_complete(a.disconnect())
                except (RejectStore,RejectRunner):pass # failed identity is not healed by fixture cleanup
        try:self.runner.close_all_session_db_handles()
        except (RejectStore,RejectRunner):pass
        self.response.close();self.replay.close();self.state.close();Own.close()
        tasks=[t for t in asyncio.all_tasks(LOOP) if not t.done()]
        self.assertEqual(tasks,[])
        counts=Registry.stats();self.tmp.cleanup()
        ENDS.append({'case':self._testMethodName,'profileRemoved':not self.home.exists(),'ownershipReleased':not Own.homes,'registry':counts,'pendingTasks':0})
        self.assertFalse(self.home.exists());self.assertFalse(Own.homes);self.assertEqual(counts['total_refcounts'],0)
    @contextmanager
    def observed(self):
        global WATCH
        conns=(self.state._conn,self.replay._conn,self.response._conn)
        before=[c.total_changes for c in conns];reg=Registry.stats();queries=[]
        for c in conns:c.set_trace_callback(queries.append)
        record={'case':self._testMethodName,'sqliteOpens':0,'rawDatabaseOpens':0};WATCH=record
        try:yield
        finally:
            WATCH=None
            for c in conns:c.set_trace_callback(None)
            self.assertEqual(before,[c.total_changes for c in conns]);self.assertEqual(reg,Registry.stats())
            self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries),queries)
            record['rowChanges']=0;record['queryCount']=len(queries);CHECKS.append(record)
    def make(self):
        b=Bundle(self.home,self.state,self.replay,self.response,prepared_runner=self.runner)
        a=Adapter(PlatformConfig(extra={'key':'fixture-only','model_name':'offline'}),borrowed_stores=b)
        self.adapters.append(a);self.bundle=b;return b,a
    def select(self,b,a):return b.select(a,self.home)
    def test_exact_three_handles_and_prepared_runner_without_extra_open(self):
        with self.observed():
            b,a=self.make();self.assertEqual(self.select(b,a),(self.state,self.replay,self.response))
            self.assertIs(a.gateway_runner,self.runner);self.assertIs(self.runner._session_db._db,self.state)
        self.assertFalse(b.status()['listenerAuthorized']);self.assertFalse(self.binding.status()['runtimeAdmissionAuthorized'])
        self.assertTrue(self.authority.retiring);self.assertFalse(self.runner._running)
    def test_local_epoch_map_is_native_preparation_not_database_write(self):
        self.assertEqual(self.runner.session_store._local_authority_epoch,self.epoch)
        self.assertEqual(self.runner.session_store._local_authority_epochs,{self.home/'state.db':self.epoch})
        with self.observed():b,a=self.make();self.select(b,a)
        self.assertEqual(tuple(self.state._conn.execute('SELECT epoch,instance_id FROM main.runtime_epoch').fetchone()),(self.epoch,'b123a6-owned'))
    def test_api_then_runner_detach_keeps_all_caller_connections_and_profile(self):
        b,a=self.make()
        with self.observed():
            LOOP.run_until_complete(a.disconnect());self.assertEqual(b.status()['state'],'DETACHED')
            self.runner.close_all_session_db_handles();self.assertEqual(self.binding.status()['state'],'DETACHED')
        for c in (self.state._conn,self.replay._conn,self.response._conn):self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(Own.owns(self.home))
    def test_runner_cannot_detach_before_api(self):
        b,a=self.make()
        with self.observed(),self.assertRaises(RejectStore):self.runner.close_all_session_db_handles()
        self.assertEqual(b._stage,'ATTACHED');self.assertEqual(self.binding.status()['state'],'PREPARED')
        self.assertFalse(self.runner.session_store._borrowed_session_state._closed)
    def test_old_bundle_still_rejects_arbitrary_runner_attachment(self):
        b=Bundle(self.home,self.state,self.replay,self.response);a=Adapter(PlatformConfig(extra={'key':'fixture-only'}),borrowed_stores=b);self.adapters.append(a)
        a.gateway_runner=self.runner
        try:
            with self.observed(),self.assertRaisesRegex(RejectStore,'borrowed_runner_conflict'):b.select(a,self.home)
        finally:a.gateway_runner=None
    def test_listener_and_ordinary_runner_still_closed(self):
        b,a=self.make()
        with self.observed():
            with self.assertRaises(RejectStore):LOOP.run_until_complete(a.connect())
            with self.assertRaises(RejectRunner):LOOP.run_until_complete(self.runner.start())
            with self.assertRaises(Runtime.RuntimeStoreError):self.authority._require_admission_open()
        self.assertIsNone(a._site);self.assertIsNone(a._runner)
    def test_foreign_runner_object_is_rejected(self):
        with self.observed(),self.assertRaises(RejectStore):Bundle(self.home,self.state,self.replay,self.response,prepared_runner=object())
        self.assertIsNone(self.binding._api_bundle)
    def test_one_bundle_and_one_adapter_per_prepared_owner(self):
        b,a=self.make()
        with self.observed():
            with self.assertRaises(RejectStore):Bundle(self.home,self.state,self.replay,self.response,prepared_runner=self.runner)
            with self.assertRaises(RejectStore):Adapter(PlatformConfig(extra={'key':'fixture'}),borrowed_stores=b)
        self.assertIs(self.binding._api_bundle,b);self.assertIs(b._adapter,a)
    def test_transaction_in_each_store_refuses_selection_and_disconnect_without_rollback(self):
        b,a=self.make()
        for store in (self.state,self.replay,self.response):
            with self.subTest(store=type(store).__name__):
                store._conn.execute('BEGIN IMMEDIATE')
                try:
                    with self.observed():
                        with self.assertRaises(RejectStore):self.select(b,a)
                        with self.assertRaises(RejectStore):LOOP.run_until_complete(a.disconnect())
                    self.assertTrue(store._conn.in_transaction);self.assertEqual(b._stage,'ATTACHED')
                finally:store._conn.rollback()
        self.select(b,a)
    def test_transaction_after_api_detach_blocks_runner_detach(self):
        b,a=self.make();LOOP.run_until_complete(a.disconnect());self.response._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.observed(),self.assertRaises(RejectStore):self.runner.close_all_session_db_handles()
            self.assertTrue(self.response._conn.in_transaction)
        finally:self.response._conn.rollback()
    def test_replay_mutex_refuses_without_waiting_or_unlocking(self):
        b,a=self.make();self.replay._lock.acquire()
        try:
            with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            self.assertTrue(self.replay._lock.locked())
        finally:self.replay._lock.release()
    def test_other_application_generation_never_silently_restored(self):
        b,a=self.make()
        for store in (self.replay,self.response):
            old=store._conn.execute('PRAGMA application_id').fetchone()[0];store._conn.execute('PRAGMA application_id='+str(old+1))
            try:
                with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
                self.assertEqual(store._conn.execute('PRAGMA application_id').fetchone()[0],old+1)
            finally:store._conn.execute('PRAGMA application_id='+str(old))
    def test_extra_database_remains_attached_on_refusal(self):
        b,a=self.make();self.response._conn.execute("ATTACH ':memory:' AS foreign_db")
        try:
            with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            self.assertIn('foreign_db',[r[1] for r in self.response._conn.execute('PRAGMA database_list')])
        finally:self.response._conn.execute('DETACH foreign_db')
    def test_mapping_replacement_and_value_change_refused(self):
        b,a=self.make();f=self.runner.session_store;old=f._local_authority_epochs
        for value in ({**old},{self.home/'state.db':self.epoch+1}):
            f._local_authority_epochs=value
            try:
                with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            finally:f._local_authority_epochs=old
        old_scalar=f._local_authority_epoch;f._local_authority_epoch=True
        try:
            with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
        finally:f._local_authority_epoch=old_scalar
    def test_adapter_runner_or_store_drift_refused(self):
        b,a=self.make()
        for name,value in (('gateway_runner',object()),('_response_store',object()),('_run_idempotency_store',object())):
            original=getattr(a,name);setattr(a,name,value)
            try:
                with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            finally:setattr(a,name,original)
    def test_foreign_profile_does_not_open_or_create(self):
        b,a=self.make();foreign=self.home/'foreign';token=Constants.set_hermes_home_override(foreign)
        try:
            with self.observed(),self.assertRaises(RejectStore):b.select(a,foreign)
            self.assertFalse(foreign.exists())
        finally:Constants.reset_hermes_home_override(token)
    def test_failed_adapter_cleanup_is_unknown_and_not_retried(self):
        b,a=self.make();memory=a._memory_sessions;a._memory_sessions=object()
        try:
            with self.assertRaises(AttributeError):LOOP.run_until_complete(a.disconnect())
        finally:a._memory_sessions=memory
        self.assertEqual(b._stage,'CLOSE_UNKNOWN')
        with self.observed():
            with self.assertRaises(RejectStore):LOOP.run_until_complete(a.disconnect())
            with self.assertRaises(RejectStore):self.runner.close_all_session_db_handles()
        self.assertFalse(self.runner.session_store._borrowed_session_state._closed)
    def test_real_pending_adapter_task_prevents_detach_without_cancellation(self):
        b,a=self.make();event=asyncio.Event()
        async def start():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(start());a._background_tasks.add(task)
        try:
            with self.observed(),self.assertRaises(RejectStore):LOOP.run_until_complete(a.disconnect())
            self.assertFalse(task.cancelled());self.assertFalse(task.done());self.assertEqual(b._stage,'ATTACHED')
        finally:
            event.set();LOOP.run_until_complete(task);a._background_tasks.remove(task)
    def test_runner_identity_change_cannot_be_fixed_by_api_select(self):
        b,a=self.make();old=self.authority.epoch;self.authority.epoch+=1
        try:
            with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            self.assertEqual(self.authority.epoch,old+1)
        finally:self.authority.epoch=old
    def test_prepared_service_objects_and_running_flag_are_refused(self):
        b,a=self.make()
        for name,value in (('_running',True),('_app',object()),('_site',object()),('_runner',object())):
            with self.subTest(field=name):
                old=getattr(a,name);setattr(a,name,value)
                try:
                    with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
                finally:setattr(a,name,old)
    def test_prepared_pending_work_is_not_treated_as_quiescent_attachment(self):
        b,a=self.make();a._pending_agent_requests=1
        try:
            with self.observed(),self.assertRaises(RejectStore):self.select(b,a)
            self.assertEqual(a._pending_agent_requests,1)
        finally:a._pending_agent_requests=0
    def test_disconnect_is_idempotent_but_bundle_cannot_be_reused(self):
        b,a=self.make()
        with self.observed():LOOP.run_until_complete(a.disconnect());LOOP.run_until_complete(a.disconnect())
        with self.observed(),self.assertRaises(RejectStore):Adapter(PlatformConfig(),borrowed_stores=b)
        self.assertEqual(b._stage,'DETACHED')

def main():
    global State,Runner,Config,Bind,RejectRunner,Own,Registry,Runtime,Init,Bundle,RejectStore,Adapter,PlatformConfig,Replay,Response,Constants,BASE,LOOP
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',action='append');args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-b123a6-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import-home';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE))
        sys.path.insert(0,str(native));sys.addaudithook(audit)
        from hermes_state import SessionDB
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig,PlatformConfig as PC
        from gateway.run_borrowed_state import CallerOwnedRunnerState,BorrowedRunnerRejected
        from gateway.runtime_ownership import process_ownership
        from gateway.run_runtime import initialize_gateway_runtime
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        import hermes_state_registry,hermes_state_runtime,hermes_constants
        State,Runner,Config,Bind,RejectRunner,Own,Registry,Runtime,Init=SessionDB,GatewayRunner,GatewayConfig,CallerOwnedRunnerState,BorrowedRunnerRejected,process_ownership,hermes_state_registry,hermes_state_runtime,initialize_gateway_runtime
        Bundle,RejectStore,Adapter,PlatformConfig,Replay,Response,Constants=BorrowedAPIStores,BorrowedStoreRejected,APIServerAdapter,PC,RunIdempotencyStore,ResponseStore,hermes_constants
        suite=unittest.TestSuite(PreparedAPICases(name) for name in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(PreparedAPICases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                q=Path(name).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        failed={t.id().split(' (',1)[0] for t,_ in r.failures+r.errors}
        result={'result':'PASS_NATIVE_PREPARED_THREE_STORE_JOIN' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
                'nativeImports':imports,'checks':CHECKS,'caseEnd':ENDS,'deniedEvents':DENIED,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'actualNativeRunnerAndAdapter':True,'nativeMethodsReplaced':False,'cleanupObjectFaultInjectedExplicitly':True,'sameThreeCallerConnections':True,'epochAdvancedByAttachment':False,'serviceAdmissionOrListenerActivated':False,'providerCalls':0,'linuxIsolationTested':False,'rootWslAction':False}
    result['temporaryRootRemoved']=not BASE.exists()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-12000:],flush=True)
    return 0 if r.wasSuccessful() and result['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
