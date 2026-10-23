"""Independent genuine GatewayRunner construction/epoch ownership acceptance.
No GatewayRunner/SessionStore/SessionAuthority methods replaced. Config and temp
homes are fixtures. No model, ordinary service start, HTTP or Linux acceptance.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,threading,traceback,unittest
from contextlib import contextmanager
from pathlib import Path
State=Runner=Config=Binding=Rejected=Ownership=Registry=Runtime=Constants=None
Initialize=InitializeOrdinary=StartApi=None
BASE=LOOP=None
WATCH=None
CHECKS=[];CLEANUP=[];DENIED=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('r122q6_offline_native_tests')
    if WATCH is not None:
        if event=='sqlite3.connect':
            WATCH['newSQLiteConnections']+=1;raise AssertionError('additional_sqlite_open')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name.lower()
            if name=='state.db' or name.startswith('state.db-'):
                WATCH['rawStateOpens']+=1;raise AssertionError('raw_state_open')

class RunnerOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        os.environ['HERMES_HOME']=str(self.home);Ownership.reserve([self.home])
        self.state=State(self.home/'state.db');self.instance='r122q6-owned'
        self.epoch=Runtime.begin_runtime_epoch(self.state,instance_id=self.instance)
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.bindings=[];self.runners=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        if self.state._conn is not None and self.state._conn.in_transaction:self.state._conn.rollback()
        for runner in self.runners:
            try:runner.close_all_session_db_handles()
            except Rejected:pass # negative fixtures deliberately keep state unavailable; caller owns final close
        self.state.close();Ownership.close();counts=Registry.stats();self.tmp.cleanup()
        CLEANUP.append({'case':self._testMethodName,'temporaryProfileRemoved':not self.home.exists(),'profileReleased':not Ownership.homes,'registry':counts})
        self.assertFalse(self.home.exists());self.assertFalse(Ownership.homes)
        self.assertEqual(counts,{'live_generations':0,'retired_generations':0,'total_refcounts':0})
    @contextmanager
    def observe(self):
        global WATCH
        before=self.state._conn.total_changes;counts=Registry.stats();queries=[]
        record={'case':self._testMethodName,'newSQLiteConnections':0,'rawStateOpens':0}
        self.state._conn.set_trace_callback(queries.append);WATCH=record
        try:yield
        finally:
            WATCH=None;self.state._conn.set_trace_callback(None)
            self.assertEqual(before,self.state._conn.total_changes);self.assertEqual(counts,Registry.stats())
            self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries),queries)
            record['sqlRowChanges']=0;record['queries']=len(queries);CHECKS.append(record)
    def binding(self,**kwargs):
        b=Binding(self.config,self.state,epoch=kwargs.pop('epoch',self.epoch),instance_id=kwargs.pop('instance_id',self.instance),**kwargs)
        self.bindings.append(b);return b
    def make(self):
        b=self.binding();r=Runner(config=self.config,caller_state=b);self.runners.append(r);return b,r
    def prepare(self,r):return LOOP.run_until_complete(Initialize(r))
    def queue(self):
        self.state.create_session('queued-session','api_server')
        return Runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='owned',session_id='queued-session',request_id='fixture',payload={'text':'offline fixture'})
    def test_real_constructor_uses_same_state_without_opens_or_epoch_change(self):
        with self.observe():
            b,r=self.make();self.assertIs(type(r),Runner)
            self.assertIs(r.session_store._db,self.state);self.assertIs(r._session_db._db,self.state)
            self.assertIs(r._open_session_db_for_active_scope(),r._session_db)
            self.assertEqual(b.status()['state'],'CONSTRUCTED')
        self.assertEqual(self.state._conn.execute('SELECT epoch,instance_id FROM main.runtime_epoch').fetchone()[:],(self.epoch,self.instance))
        self.assertFalse(r._session_db_handles);self.assertFalse(r.session_store._db_handles)
    def test_real_authority_preparation_reuses_epoch_and_stays_closed(self):
        b,r=self.make()
        with self.observe():a=self.prepare(r)
        from gateway.session_authority import SessionAuthority
        self.assertIs(type(a),SessionAuthority);self.assertIs(a.db,self.state);self.assertIs(a.runner,r)
        self.assertEqual((a.epoch,a.instance_id),(self.epoch,self.instance))
        self.assertIs(r.session_authorities.launch,a);self.assertTrue(a.retiring);self.assertTrue(r._draining)
        self.assertEqual(r.session_runtime_descriptor['capabilities'],[]);self.assertEqual(r.session_runtime_descriptor['served_profiles'],[])
        self.assertFalse(b.status()['runtimeAdmissionAuthorized']);self.assertFalse(b.status()['allThreeStoresIntegrated'])
        with self.assertRaises(Exception):a._require_admission_open()
    def test_repeated_preparation_preserves_original_authority(self):
        b,r=self.make();a=self.prepare(r)
        with self.observe(),self.assertRaises(Rejected):self.prepare(r)
        self.assertIs(r.session_authority,a);self.assertEqual(b.status()['state'],'PREPARED')
    def test_wrong_epoch_or_instance_refused_before_any_runner(self):
        for args in ({'epoch':self.epoch+1},{'instance_id':'different'},{'epoch':True}):
            with self.subTest(args=args),self.observe(),self.assertRaises(Rejected):self.binding(**args)
    def test_changed_epoch_after_constructor_not_recovered(self):
        b,r=self.make();new=Runtime.begin_runtime_epoch(self.state,instance_id='fixture-successor')
        with self.observe(),self.assertRaises(Rejected):self.prepare(r)
        self.assertEqual(self.state._conn.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0],new)
        self.assertIsNone(getattr(r,'session_authority',None))
    def test_queued_work_before_binding_not_recovered(self):
        a=self.queue()
        with self.observe(),self.assertRaises(Rejected):self.binding()
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=a['admission_id'])['status'],'queued')
    def test_queued_work_after_constructor_blocks_prepare_and_detach(self):
        b,r=self.make();a=self.queue()
        with self.observe():
            for fn in (lambda:self.prepare(r),r.close_all_session_db_handles):
                with self.assertRaises(Rejected):fn()
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=a['admission_id'])['status'],'queued')
        self.assertTrue(Ownership.owns(self.home));self.assertEqual(b.status()['state'],'CONSTRUCTED')
    def test_terminal_history_accepted_without_rewrite(self):
        a=self.queue();claim=Runtime.claim_session_input(self.state,epoch=self.epoch,session_id='queued-session')
        Runtime.settle_session_input(self.state,epoch=self.epoch,admission_id=a['admission_id'],generation=claim['generation'],outcome='completed')
        with self.observe():b,r=self.make();self.prepare(r)
        self.assertEqual(Runtime.get_session_admission(self.state,admission_id=a['admission_id'])['status'],'terminal')
    def test_existing_worker_registry_row_not_ignored(self):
        self.state.create_session('worker-session','api_server')
        Runtime.register_worker_execution(self.state,epoch=self.epoch,execution_id='fixture-worker',session_id='worker-session',generation=0,kind='compute',adoption_secret='a'*32)
        with self.observe(),self.assertRaises(Rejected):self.binding()
    def test_default_start_stop_and_api_routes_reject_before_side_effects(self):
        b,r=self.make()
        for fn in (r.start,r._start_impl,r.stop,r._stop_impl,lambda:StartApi(r)):
            with self.subTest(fn=fn.__name__),self.observe(),self.assertRaises(Rejected):LOOP.run_until_complete(fn())
        with self.observe(),self.assertRaises(Rejected):r._stop_quiesce_and_close_session_dbs(0,None)
        self.assertIsNone(r._stop_task);self.assertIsNone(r._executor);self.assertFalse(r._running)
        self.assertEqual(b.status()['state'],'CONSTRUCTED')
    def test_ordinary_authority_initializer_cannot_bump_borrowed_epoch(self):
        b,r=self.make()
        with self.observe(),self.assertRaises(Rejected):LOOP.run_until_complete(InitializeOrdinary(r,profile_id=str(self.home),instance_id='not-accepted'))
        self.assertEqual(self.state._conn.execute('SELECT epoch FROM main.runtime_epoch').fetchone()[0],self.epoch)
    def test_binding_one_shot_and_exact_config_not_equal_copy(self):
        b,r=self.make()
        with self.observe(),self.assertRaises(Rejected):Runner(config=self.config,caller_state=b)
        new=self.binding();other=Config(multiplex_profiles=False,write_sessions_json=False)
        with self.observe(),self.assertRaises(Rejected):Runner(config=other,caller_state=new)
        self.assertIs(r._session_db._db,self.state)
    def test_fake_binding_and_repinned_state_refused(self):
        with self.observe(),self.assertRaises(Rejected):Runner(config=self.config,caller_state=object())
        b,r=self.make()
        for value in (None,self.state,r._session_db):
            with self.observe(),self.assertRaises(Rejected):r._session_db=value
        self.assertIs(r._session_db._db,self.state)
    def test_configuration_change_refused_without_transport_start(self):
        b,r=self.make();old=self.config.platforms;self.config.platforms={'fixture':object()}
        try:
            with self.observe(),self.assertRaises(Rejected):self.prepare(r)
        finally:self.config.platforms=old
        self.assertFalse(r.adapters);self.assertEqual(b.status()['state'],'CONSTRUCTED')
    def test_open_transaction_retained_on_prepare_and_detach(self):
        b,r=self.make();self.state._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.observe():
                for fn in (lambda:self.prepare(r),r.close_all_session_db_handles):
                    with self.assertRaises(Rejected):fn()
            self.assertTrue(self.state._conn.in_transaction)
        finally:self.state._conn.rollback()
        with self.observe():self.prepare(r)
    def test_locked_state_refuses_without_unlock(self):
        b,r=self.make();self.state._lock.acquire()
        try:
            with self.observe(),self.assertRaises(Rejected):self.prepare(r)
            self.assertTrue(self.state._lock.locked())
        finally:self.state._lock.release()
    def test_foreign_scope_does_not_create_a_profile(self):
        b,r=self.make();foreign=self.home/'foreign';token=Constants.set_hermes_home_override(foreign)
        try:
            with self.observe():
                for fn in (lambda:r._session_db,lambda:self.prepare(r)):
                    with self.assertRaises(Rejected):fn()
        finally:Constants.reset_hermes_home_override(token)
        self.assertFalse(foreign.exists());self.assertIs(r._session_db._db,self.state)
    def test_lifecycle_from_another_thread_is_rejected(self):
        b,r=self.make();results=[]
        def other_thread():
            try:b.initialize_authority(r)
            except Rejected:results.append('refused')
        with self.observe():
            t=threading.Thread(target=other_thread);t.start();t.join(5)
        self.assertFalse(t.is_alive());self.assertEqual(results,['refused']);self.assertIsNone(getattr(r,'session_authority',None))
    def test_native_background_task_blocks_detach_without_cancellation(self):
        b,r=self.make()
        async def scenario():
            event=asyncio.Event();task=asyncio.create_task(event.wait());r._background_tasks.add(task)
            try:
                with self.observe(),self.assertRaises(Rejected):r.close_all_session_db_handles()
                self.assertFalse(task.done());self.assertFalse(task.cancelled())
            finally:event.set();await task;r._background_tasks.remove(task)
        LOOP.run_until_complete(scenario())
        with self.observe():r.close_all_session_db_handles()
        self.assertEqual(b.status()['state'],'DETACHED')
    def test_authority_pending_result_blocks_detach_without_discard(self):
        b,r=self.make();a=self.prepare(r);sentinel=object();a.pending_results['owned']=sentinel
        try:
            with self.observe(),self.assertRaises(Rejected):r.close_all_session_db_handles()
            self.assertIs(a.pending_results['owned'],sentinel)
        finally:a.pending_results.clear()
        with self.observe():r.close_all_session_db_handles()
    def test_normal_detach_retains_caller_state_and_profile(self):
        b,r=self.make();a=self.prepare(r)
        with self.observe():r.close_all_session_db_handles();r.close_all_session_db_handles()
        self.assertTrue(a.retired);self.assertTrue(Ownership.owns(self.home));self.assertEqual(self.state._conn.execute('SELECT 1').fetchone()[0],1)
        with self.assertRaises(Rejected):r._session_db
        self.assertFalse(b.status()['storesClosedHere']);self.assertFalse(b.status()['profileReleasedHere'])
    def test_profile_reacquire_does_not_adopt_old_binding(self):
        b,r=self.make();Ownership.close();Ownership.reserve([self.home])
        with self.observe(),self.assertRaises(Rejected):self.prepare(r)
        self.assertTrue(Ownership.owns(self.home))
    def test_changed_async_wrapper_not_adopted(self):
        b,r=self.make();wrapper=r._session_db;old=wrapper._db;wrapper._db=object()
        try:
            with self.observe(),self.assertRaises(Rejected):self.prepare(r)
        finally:wrapper._db=old
        self.assertIs(r._session_db._db,self.state)
    def test_caller_closed_state_is_not_reopened(self):
        global WATCH
        b,r=self.make();self.state.close();record={'case':self._testMethodName,'newSQLiteConnections':0,'rawStateOpens':0,'sqlRowChanges':0,'queries':0};WATCH=record
        try:
            with self.assertRaises(Rejected):r._session_db
            with self.assertRaises(Rejected):self.prepare(r)
        finally:WATCH=None;CHECKS.append(record)
        self.assertFalse(r._session_db_handles)

def main():
    global State,Runner,Config,Binding,Rejected,Ownership,Registry,Runtime,Constants,Initialize,InitializeOrdinary,StartApi,BASE,LOOP
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case');args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-r122q6-suite-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import';home.mkdir()
        os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),LOCALAPPDATA=str(BASE/'local'),APPDATA=str(BASE/'roaming'))
        sys.path.insert(0,str(native));LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP);sys.addaudithook(audit)
        from gateway.run import GatewayRunner
        from gateway.config import GatewayConfig
        from gateway.run_borrowed_state import CallerOwnedRunnerState,BorrowedRunnerRejected
        from gateway.run_runtime import initialize_gateway_runtime,start_gateway_runtime_api
        from gateway.session_authority import initialize_session_authority
        from gateway.runtime_ownership import process_ownership
        from hermes_state import SessionDB
        import hermes_state_registry,hermes_state_runtime,hermes_constants
        State,Runner,Config,Binding,Rejected,Ownership,Registry,Runtime,Constants=SessionDB,GatewayRunner,GatewayConfig,CallerOwnedRunnerState,BorrowedRunnerRejected,process_ownership,hermes_state_registry,hermes_state_runtime,hermes_constants
        Initialize,InitializeOrdinary,StartApi=initialize_gateway_runtime,initialize_session_authority,start_gateway_runtime_api
        suite=unittest.TestSuite([RunnerOwnershipTests(args.case)]) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(RunnerOwnershipTests)
        try:
            with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        finally:
            LOOP.run_until_complete(LOOP.shutdown_asyncgens());LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            fn=getattr(mod,'__file__',None)
            if fn:
                q=Path(fn).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        report={'result':'PASS_REAL_BORROWED_RUNNER_INDEPENDENT' if result.wasSuccessful() else 'FAIL','total':result.testsRun,
                'passed':result.testsRun-len({t.id() for t,_ in result.errors+result.failures})-len(result.skipped),'errors':len(result.errors),'failures':len(result.failures),'skipped':len(result.skipped),
                'errorIds':[t.id() for t,_ in result.errors],'failureIds':[t.id() for t,_ in result.failures],'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'checks':CHECKS,'cleanup':CLEANUP,'deniedExternalProbes':DENIED,'nativeMethodsReplaced':False,'actualGatewayRunnerConstructed':True,'actualSessionAuthorityConstructed':True,
                'sharedThreeStoreApiIntegrated':False,'fullAgentExecutionTested':False,'httpListenerStarted':False,'fullLinuxIsolationTested':False,'providerCalls':0,'rootWslAction':False}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','checks','cleanup','deniedExternalProbes')}),flush=True)
    if not result.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-18000:],flush=True)
    return 0 if result.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
