"""Current native lifecycle with real NativeStoreStartup and SQL gates; Linux actor/preopen/mount metadata are explicit fixture doubles."""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,traceback,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')]
import s124b1_startup_fixture as fixture
import gateway_prepared_consumer as consumer
startup=fixture.startup
LOOP=OTHER_LOOP=BASE=NATIVE=Config=Platform=Registry=None
WATCH=None;DENIED=[];CHECKS=[];ENDS=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('s124b1_owned_offline')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('consumer_reopened_sqlite')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('consumer_raw_database_open')

class LifecycleCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        self.f=fixture.NativeFixture(NATIVE,self.home,LOOP);self.o=self.f.startup
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.api=Platform(extra={'key':'owned-fixture-only','model_name':'offline'})
    def tearDown(self):
        global WATCH
        WATCH=None
        # Never turn product UNKNOWN into success. Isolated fixture closes only own resources.
        tasks=[t for t in asyncio.all_tasks(LOOP) if not t.done()]
        self.assertEqual(tasks,[])
        stage=self.o._stage;consumer_stage=getattr(self.o._prepared_consumer,'_stage',None)
        self.f.cleanup_fixture();self.tmp.cleanup()
        ENDS.append({'case':self._testMethodName,'productStageBeforeFixtureCleanup':stage,'consumerStageBeforeFixtureCleanup':consumer_stage,
                     'temporaryHomeRemoved':not self.home.exists(),'profileReleased':not self.f.owner.homes,'registry':Registry.stats()})
        self.assertFalse(self.home.exists());self.assertFalse(self.f.owner.homes);self.assertEqual(Registry.stats()['total_refcounts'],0)
    @contextmanager
    def watched(self):
        global WATCH
        before=[c.total_changes for c in self.f.connections];queries=[]
        record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0}
        for c in self.f.connections:c.set_trace_callback(queries.append)
        WATCH=record
        try:yield
        finally:
            WATCH=None
            for c in self.f.connections:c.set_trace_callback(None)
            self.assertEqual([c.total_changes for c in self.f.connections],before)
            self.assertTrue(all(q.startswith(('SELECT ','PRAGMA ')) for q in queries),queries[-5:])
            record.update(rowChanges=0,queryCount=len(queries));CHECKS.append(record)
    def prepare(self):return LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api))
    def remains_open(self):
        for c in self.f.connections:self.assertEqual(c.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(self.f.owner.owns(self.home))
    def blocked_close(self):
        with self.assertRaises((consumer.PreparedConsumerRejected,startup.StoreStartupRejected)):self.o.close()
        self.remains_open();self.assertEqual(self.o._stage,'VERIFIED')
    def test_exact_handles_epoch_and_original_close_blocked(self):
        with self.watched():c=self.prepare();c.check();self.blocked_close()
        self.assertEqual(c.status()['sameAcceptedEpoch'],1)
        self.assertEqual(tuple(self.f.connections[0].execute('SELECT epoch,instance_id FROM main.runtime_epoch').fetchone()),(1,'s124b1-owned'))
        self.assertIs(c._binding.state,self.o.state_store);self.assertIs(c._adapter._response_store,self.o.response_store)
    def test_api_runner_store_then_external_profile_release(self):
        c=self.prepare()
        with self.watched():LOOP.run_until_complete(c.detach())
        self.assertEqual((c._bundle._stage,c._binding._stage,c._stage),('DETACHED','DETACHED','DETACHED'));self.remains_open()
        self.o.close();self.assertEqual(self.o._stage,'CLOSED')
        for conn in self.f.connections:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.assertTrue(self.f.owner.owns(self.home));self.f.owner.close();self.assertFalse(self.f.owner.homes)
    def test_second_prepare_never_replaces_consumer(self):
        c=self.prepare()
        with self.assertRaises(startup.StoreStartupRejected):self.prepare()
        self.assertIs(self.o._prepared_consumer,c);self.blocked_close()
    def test_direct_native_detaches_cannot_bypass_consumer_ack(self):
        c=self.prepare();LOOP.run_until_complete(c._adapter.disconnect());c._runner.close_all_session_db_handles()
        self.blocked_close();self.assertEqual(c._stage,'ATTACHED')
    def test_constructor_failure_holds_slot_and_is_not_replayed(self):
        original=consumer.native_types
        def bad_types():
            values=list(original())
            def failure(*a,**k):raise RuntimeError('explicit fixture constructor fault')
            values[3]=failure;return tuple(values)
        with patch.object(consumer,'native_types',side_effect=bad_types):
            with self.assertRaises(RuntimeError):self.prepare()
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.blocked_close()
        with self.assertRaises(startup.StoreStartupRejected):self.prepare()
    def test_source_manifest_refusal_does_not_close_owner(self):
        with patch.object(consumer,'MANIFEST_SHA256','0'*64):
            with self.assertRaises(consumer.PreparedConsumerRejected):self.prepare()
        self.blocked_close();self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN')
    def test_source_unknown_import_is_refused(self):
        proof=consumer.qualify_sources();root,hashes=proof
        self.assertGreaterEqual(len(hashes),501)
        from types import SimpleNamespace
        name='s124b1_fixture_unknown_native';sys.modules[name]=SimpleNamespace(__file__=str(root/'unqualified_fixture_module.py'))
        try:
            with self.assertRaises(consumer.PreparedConsumerRejected):consumer.verify_imports(proof)
        finally:del sys.modules[name]
    def test_source_gate_before_constructor_and_reserved_close(self):
        original=consumer.qualify_sources
        def observed():
            self.blocked_close();self.assertEqual(self.o._prepared_consumer._stage,'QUALIFYING');return original()
        with patch.object(consumer,'qualify_sources',side_effect=observed):c=self.prepare()
        self.assertEqual(c._stage,'ATTACHED')
    def test_each_store_transaction_blocks_without_rollback_then_recovers(self):
        c=self.prepare()
        for conn in self.f.connections:
            conn.execute('BEGIN IMMEDIATE')
            try:
                with self.assertRaises(consumer.PreparedConsumerRejected):LOOP.run_until_complete(c.detach())
                self.assertTrue(conn.in_transaction);self.blocked_close();self.assertEqual(c._stage,'ATTACHED')
            finally:conn.rollback()
        with self.watched():LOOP.run_until_complete(c.detach())
        self.o.close()
    def test_pending_real_adapter_task_not_cancelled(self):
        c=self.prepare();event=asyncio.Event()
        async def begin():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(begin());c._adapter._background_tasks.add(task)
        try:
            with self.assertRaises(Exception):LOOP.run_until_complete(c.detach())
            self.assertFalse(task.done());self.assertFalse(task.cancelled());self.assertEqual(c._stage,'ATTACHED');self.blocked_close()
        finally:event.set();LOOP.run_until_complete(task);c._adapter._background_tasks.remove(task)
        LOOP.run_until_complete(c.detach());self.o.close()
    def test_unknown_cleanup_is_not_retried(self):
        c=self.prepare();old=c._adapter._memory_sessions;c._adapter._memory_sessions=object()
        try:
            with self.assertRaises(AttributeError):LOOP.run_until_complete(c.detach())
        finally:c._adapter._memory_sessions=old
        self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.blocked_close()
        with self.assertRaises(consumer.PreparedConsumerRejected):LOOP.run_until_complete(c.detach())
    def test_owner_epoch_object_replaced_refused(self):
        from dataclasses import replace
        c=self.prepare();old=self.o._expected;self.o._expected=replace(old,epoch=old.epoch+1)
        try:
            with self.assertRaises(consumer.PreparedConsumerRejected):c.check()
            self.blocked_close()
        finally:self.o._expected=old
    def test_same_epoch_value_different_object_not_learned(self):
        from dataclasses import replace
        c=self.prepare();old=self.o._expected;self.o._expected=replace(old)
        try:
            with self.assertRaises(consumer.PreparedConsumerRejected):c.check()
        finally:self.o._expected=old
    def test_other_event_loop_cannot_detach(self):
        c=self.prepare();other=OTHER_LOOP
        try:
            with self.assertRaises(consumer.PreparedConsumerRejected):other.run_until_complete(c.detach())
        finally:pass
        self.assertEqual(c._stage,'ATTACHED')
    def test_native_authority_identity_drift_refused(self):
        c=self.prepare();authority=c._runner.session_authority;old=authority.epoch;authority.epoch+=1
        try:
            with self.assertRaises(Exception):c.check()
            self.blocked_close()
        finally:authority.epoch=old
    def test_attached_consumer_retains_native_service_guards(self):
        c=self.prepare()
        with self.assertRaises(Exception):LOOP.run_until_complete(c._adapter.connect())
        with self.assertRaises(Exception):LOOP.run_until_complete(c._runner.start())
        with self.assertRaises(Exception):c._runner.session_authority._require_admission_open()
        self.assertFalse(c.status()['runtimeAdmissionAuthorized']);self.blocked_close()
    def test_close_refused_after_postdetach_adapter_revived(self):
        c=self.prepare();LOOP.run_until_complete(c.detach());c._adapter._running=True
        try:self.blocked_close()
        finally:c._adapter._running=False
        self.o.close()
    def test_actual_epoch_changed_after_detach_refuses_close(self):
        c=self.prepare();LOOP.run_until_complete(c.detach());conn=self.f.connections[0]
        conn.execute('UPDATE runtime_epoch SET epoch=epoch+1');conn.commit()
        try:self.blocked_close()
        finally:
            try:conn.execute('UPDATE runtime_epoch SET epoch=epoch-1');conn.commit()
            except sqlite3.ProgrammingError:pass # preserve original unsafe-close failure, no attempt to reopen
    def test_pending_runner_task_after_detach_refuses_close(self):
        c=self.prepare();LOOP.run_until_complete(c.detach());event=asyncio.Event()
        async def begin():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(begin());c._runner._background_tasks.add(task)
        try:self.blocked_close();self.assertFalse(task.cancelled())
        finally:event.set();LOOP.run_until_complete(task);c._runner._background_tasks.remove(task)
    def test_lease_loss_during_api_await_holds_runner_and_stores(self):
        c=self.prepare();entered=asyncio.Event();gate=asyncio.Event();real=c._adapter.disconnect
        async def delayed():
            await real();entered.set();await gate.wait()
        async def trial():
            with patch.object(c._adapter,'disconnect',side_effect=delayed):
                task=asyncio.create_task(c.detach());await entered.wait()
                self.blocked_close();self.o._expected=object();gate.set()
                try:
                    with self.assertRaises(consumer.PreparedConsumerRejected):await task
                finally:self.o._expected=c._expected
        LOOP.run_until_complete(trial());self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.blocked_close()
        self.assertEqual(c._binding._stage,'PREPARED')

def main():
    global LOOP,OTHER_LOOP,BASE,NATIVE,Config,Platform,Registry
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',action='append');args=p.parse_args()
    NATIVE=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();OTHER_LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-s124b1-native-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import-home';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE))
        sys.path.insert(0,str(NATIVE));sys.addaudithook(audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_registry
        Config,Platform,Registry=GatewayConfig,PlatformConfig,hermes_state_registry
        suite=unittest.TestSuite(LifecycleCases(n) for n in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close();OTHER_LOOP.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            name=getattr(mod,'__file__',None)
            if name:
                q=Path(name).resolve()
                if q.is_relative_to(NATIVE) and q.suffix=='.py':imports[q.relative_to(NATIVE).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        failures={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        names=('packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py','config/prepared-consumer-s124b1-sources.json','scripts/qa/s124b1_startup_fixture.py','scripts/qa/s124b1_native_consumer.py')
        result={'result':'PASS_NATIVE_CONSUMER_WITH_WINDOWS_BOUNDARY_DOUBLES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failures)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
          'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'nativeImports':imports,'checks':CHECKS,'caseEnd':ENDS,'deniedEvents':DENIED,
          'actualNativeStoreStartupAndStores':True,'actualNativeRunnerAndAdapter':True,'linuxLeaseMountColdPreflightMetadataDoubled':True,'nativeSqlLiveChecksReal':True,
          'productBoundaryDoublesOnlyInExplicitFaultTests':True,'fullLinuxAcceptance':False,'activeTaskObserversRequalified':False,'serviceStarted':False,'providerCalls':0,'rootWslAction':False}
    result['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sourceHashes','nativeImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-16000:],flush=True)
    return 0 if r.wasSuccessful() and result['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
