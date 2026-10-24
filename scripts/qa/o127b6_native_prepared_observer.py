"""Real native prepared observer attachment with explicit Windows OS doubles.
NativeStoreStartup/live SQL/consumer/runner/authority/API/channel stay real.
Only existing S124 profile actor/layout/mount/cold-helper fixture boundaries are
substituted. No work admission, service, native method substitution or provider.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,threading,traceback,unittest
from contextlib import contextmanager
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')]
import s124b1_startup_fixture as fixture
import gateway_canonical_run_binding as b
import gateway_canonical_turn_observation as turns
import gateway_work_health as health
LOOP=OTHER_LOOP=BASE=NATIVE=Config=Platform=Registry=None
WATCH=None;CHECKS=[];ENDS=[];DENIED=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=6)]})
        raise PermissionError('o127_prepared_offline')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('observer_opened_sqlite')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('observer_opened_database_file')

class PreparedObserverCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.f=fixture.NativeFixture(NATIVE,self.home,LOOP);self.owner=self.f.startup
        self.addCleanup(self.f.cleanup_fixture)
        self.consumer=LOOP.run_until_complete(self.owner.prepare_runtime(Config(multiplex_profiles=False,write_sessions_json=False),Platform(extra={'key':'owned-observer-fixture','model_name':'offline'})))
        self.adapter=self.consumer._adapter;self.authority=self.consumer._binding._authority
        e=self.owner.expectation
        sid=self.f.connections[0].execute("SELECT value FROM state_meta WHERE key='store_instance_id'").fetchone()[0]
        self.expected=health.RuntimeIdentity(sid,e.epoch,e.instance_id,os.getpid(),self.adapter._run_owner_started)
        self.schemas=(e.state_schema_sha256,e.replay_schema_sha256)
    def tearDown(self):
        global WATCH
        WATCH=None
        self.assertEqual([t for t in asyncio.all_tasks(LOOP) if not t.done()],[])
        # Dedicated fixture cleanup is not a successful product detach claim.
        self.f.cleanup_fixture();self.tmp.cleanup()
        ENDS.append({'case':self._testMethodName,'temporaryProfileRemoved':not self.home.exists(),'nativeOwnershipReleased':not self.f.owner.homes,'registry':Registry.stats()})
        self.assertFalse(self.home.exists());self.assertFalse(self.f.owner.homes);self.assertEqual(Registry.stats()['total_refcounts'],0)
    def run_async(self,action):
        async def call():return action()
        return LOOP.run_until_complete(call())
    def attach(self,**kw):
        args={'native_feature':b.CURRENT_NATIVE_FEATURE,'prepared_consumer':self.consumer};args.update(kw)
        return self.run_async(lambda:b.NativeCanonicalBinding(self.adapter,self.authority,self.expected,schema_hashes=self.schemas,**args))
    @contextmanager
    def observed(self):
        global WATCH
        conns=self.f.connections;before=[c.total_changes for c in conns];queries=[];registry=Registry.stats()
        for c in conns:c.set_trace_callback(queries.append)
        record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0};WATCH=record
        try:yield record
        finally:
            WATCH=None
            for c in conns:c.set_trace_callback(None)
            self.assertEqual(before,[c.total_changes for c in conns]);self.assertEqual(Registry.stats(),registry)
            self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries),queries)
            record['sqlRowChanges']=0;CHECKS.append(record)
    def test_actual_current_prepared_attach_is_readonly_and_has_no_readiness_claim(self):
        with self.observed() as record:
            observer=self.attach();status=self.run_async(observer.attachment_status)
        self.assertIs(self.adapter._run_observation_channel,observer.channel)
        self.assertEqual((status['attachmentMode'],status['namedRequestsObserved']),('PREPARED_ONLY',0))
        for key in ('activeBorrowedWorkQualified','allAgentWorkObserved','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertIs(status[key],False,key)
        record['status']=status
        self.assertTrue(self.authority.retiring);self.assertTrue(self.consumer._runner._draining)
        self.assertFalse(self.consumer._runner._running);self.assertIsNone(self.consumer._runner._executor)
    def test_native_turn_observer_attaches_but_cannot_invent_active_worker(self):
        with self.observed():
            observer=self.attach()
            with self.assertRaisesRegex(turns.TurnWorkerRejected,'prepared_active_path_not_qualified'):
                self.run_async(lambda:turns.NativeTurnWorkerObserver(observer))
            with self.assertRaisesRegex(b.CanonicalBindingUnavailable,'prepared_work_not_qualified'):
                self.run_async(lambda:observer.capture('not-a-run'))
        self.assertFalse(observer._entries)
    def test_source_gate_does_not_import_unqualified_worker_modules(self):
        import gateway_prepared_consumer as consumer_source
        before=set(sys.modules)
        with self.observed():observer=self.attach();self.run_async(observer.attachment_status)
        consumer_source.verify_imports(self.consumer._source_proof)
        self.assertFalse({'gateway.session_api_turn','gateway.session_execution','gateway.run_turn_runner','gateway.session_runtime_workers'}&set(sys.modules))
        self.assertEqual({n for n in set(sys.modules)-before if n.startswith('gateway.')},set())

    def test_no_consumer_or_default_feature_still_rejected_before_channel(self):
        with self.observed():
            with self.assertRaisesRegex(b.CanonicalBindingRejected,'borrowed_path_not_qualified'):self.attach(prepared_consumer=None)
            with self.assertRaisesRegex(b.CanonicalBindingRejected,'prepared_requires_current_source'):self.attach(native_feature=b.NATIVE_FEATURE)
        self.assertIsNone(self.adapter._run_observation_channel)
    def test_unknown_source_and_fake_consumer_do_not_attach(self):
        with self.observed():
            with self.assertRaises(b.CanonicalBindingRejected):self.attach(native_feature='unverified')
            with self.assertRaisesRegex(b.CanonicalBindingRejected,'consumer_required'):self.attach(prepared_consumer=object())
        self.assertIsNone(self.adapter._run_observation_channel)
    def test_second_observer_preserves_original_native_channel(self):
        observer=self.attach()
        with self.observed(),self.assertRaisesRegex(ValueError,'not_quiescent'):self.attach()
        self.assertIs(self.adapter._run_observation_channel,observer.channel)
        self.assertEqual(self.run_async(observer.attachment_status)['attachmentMode'],'PREPARED_ONLY')
    def test_each_open_transaction_refused_without_rollback(self):
        observer=self.attach()
        for conn in self.f.connections:
            conn.execute('BEGIN IMMEDIATE')
            try:
                with self.observed(),self.assertRaises(b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
                self.assertTrue(conn.in_transaction)
            finally:conn.rollback()
        self.run_async(observer.attachment_status)
    def test_source_generation_change_is_not_adopted(self):
        observer=self.attach();old=observer._native_feature;observer._native_feature=b.NATIVE_FEATURE
        try:
            with self.observed(),self.assertRaisesRegex(b.CanonicalBindingRejected,'generation_changed'):self.run_async(observer.attachment_status)
        finally:observer._native_feature=old
    def test_authority_generation_drift_is_not_repaired(self):
        observer=self.attach();old=self.authority.epoch;self.authority.epoch+=1
        try:
            with self.observed(),self.assertRaises(b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
            self.assertEqual(self.authority.epoch,old+1)
        finally:self.authority.epoch=old
    def test_real_pending_task_refused_without_cancellation(self):
        observer=self.attach();event=asyncio.Event()
        async def create():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(create());self.adapter._background_tasks.add(task)
        try:
            with self.observed(),self.assertRaises(b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
            self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:event.set();LOOP.run_until_complete(task);self.adapter._background_tasks.remove(task)
    def test_unexpected_native_event_latches_gap_without_claiming_work(self):
        from gateway.platforms.api_server_run_observation import RunBinding
        observer=self.attach();binding=RunBinding('fixture','session','scope','key','a'*64,'canonical_authority_observer','admission',1,None,'canonical')
        with self.observed():self.run_async(lambda:observer.channel._emit('ACCEPTED',binding))
        self.assertEqual(observer.channel.status()['state'],'GAP');self.assertEqual(observer._entries,{})
        with self.assertRaises(b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
        self.assertTrue(self.authority.retiring)
    def test_observer_does_not_prevent_normal_detach_or_keep_store_open(self):
        observer=self.attach()
        with self.observed():
            LOOP.run_until_complete(self.consumer.detach())
            with self.assertRaises(b.CanonicalBindingRejected):self.run_async(observer.attachment_status)
        self.owner.close();self.assertTrue(self.owner.status()['callerLeaseMayBeReleased'])
        for c in self.f.connections:
            import sqlite3
            with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
        self.assertTrue(self.f.owner.owns(self.home))
    def test_other_loop_and_actor_cannot_take_over(self):
        observer=self.attach();other=OTHER_LOOP
        async def read():return observer.attachment_status()
        try:
            with self.assertRaisesRegex(b.CanonicalBindingRejected,'other_actor'):other.run_until_complete(read())
        finally:pass
        self.run_async(observer.attachment_status)
    def test_existing_native_service_and_admission_guards_remain_closed(self):
        from gateway.run_borrowed_state import BorrowedRunnerRejected
        from gateway.platforms.api_server_borrowed import BorrowedStoreRejected
        import hermes_state_runtime
        observer=self.attach()
        with self.observed():
            with self.assertRaises(BorrowedRunnerRejected):LOOP.run_until_complete(self.consumer._runner.start())
            with self.assertRaises(BorrowedStoreRejected):LOOP.run_until_complete(self.adapter.connect())
            with self.assertRaises(hermes_state_runtime.RuntimeStoreError):self.authority._require_admission_open()
        self.assertIsNone(self.adapter._app);self.assertIsNone(self.adapter._site)
        self.run_async(observer.attachment_status)

def main():
    global LOOP,OTHER_LOOP,BASE,NATIVE,Config,Platform,Registry
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case');a=p.parse_args()
    NATIVE=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();OTHER_LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-o127-prepared-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import-home';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),APPDATA=str(BASE),LOCALAPPDATA=str(BASE));sys.path.insert(0,str(NATIVE));sys.addaudithook(audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_registry
        Config,Platform,Registry=GatewayConfig,PlatformConfig,hermes_state_registry
        suite=unittest.TestSuite([PreparedObserverCases(a.case)]) if a.case else unittest.defaultTestLoader.loadTestsFromTestCase(PreparedObserverCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close();OTHER_LOOP.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                q=Path(name).resolve()
                if q.is_relative_to(NATIVE) and q.suffix=='.py':imports[q.relative_to(NATIVE).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        names=('packages/claw-hermes/gateway_canonical_run_binding.py','packages/claw-hermes/gateway_canonical_turn_observation.py','packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py','scripts/qa/s124b1_startup_fixture.py','scripts/qa/o127b6_native_prepared_observer.py')
        failed={t.id().split(' (',1)[0] for t,_ in r.failures+r.errors}
        report={'result':'PASS_NATIVE_PREPARED_OBSERVER_ATTACHMENT_WINDOWS_BOUNDARIES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
            'nativeImports':imports,'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'checks':CHECKS,'caseEnd':ENDS,'deniedEvents':DENIED,'nativeFeature':b.CURRENT_NATIVE_FEATURE,
            'realNativeRunnerAuthorityApiChannelStores':True,'nativeMethodsReplaced':False,'linuxProfileLayoutMountColdBoundariesDoubled':True,'nativeSqlChecksReal':True,'unexpectedTaskAndEventAreExplicitFaultFixtures':True,
            'activeBorrowedWorkQualified':False,'httpListenerStarted':False,'modelOrProviderCalls':0,'kernelConfinementRerun':False,'rootOrWslAction':False}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','sourceHashes','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-16000:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
