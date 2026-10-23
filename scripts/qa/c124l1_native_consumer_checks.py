"""Independent lifecycle acceptance: real owner/native objects and SQL checks.
Linux actor, lease metadata, mount/layout and cold-helper gates are explicit
Windows fixture doubles. No active service, source-pin promotion or Linux claim.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,traceback,unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')]
import s124b1_startup_fixture as fixture
import gateway_prepared_consumer as c
s=fixture.startup
LOOP=BASE=NATIVE=Config=Platform=Registry=None
WATCH=None;CHECKS=[];ENDS=[];DENIED=[]
REJECTIONS=(c.PreparedConsumerRejected,s.StoreStartupRejected,s.live.LiveStoreRejected,s.response_live.ResponseLiveRejected)

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append({'event':event,'callers':[f.name for f in traceback.extract_stack(limit=7)]})
        raise PermissionError('c124l1_fresh_offline_native')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['sqliteOpens']+=1;raise AssertionError('fourth_sqlite_connection')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('raw_database_open')

class IndependentConsumer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        self.f=fixture.NativeFixture(NATIVE,self.home,LOOP);self.o=self.f.startup
        self.addCleanup(self.cleanup_fixture_only)
        self.config=Config(multiplex_profiles=False,write_sessions_json=False);self.api=Platform(extra={'key':'owned-independent-test','model_name':'offline'})
    def tearDown(self):
        global WATCH
        WATCH=None
        self.assertEqual([t for t in asyncio.all_tasks(LOOP) if not t.done()],[])
    def cleanup_fixture_only(self):
        # Runs even when a test or teardown assertion fails; not a product detach.
        stage=self.o._stage;borrower=getattr(self.o._prepared_consumer,'_stage',None)
        self.f.cleanup_fixture();self.tmp.cleanup()
        end={'case':self._testMethodName,'productStageBeforeIsolatedFixtureCleanup':stage,'consumerStageBeforeIsolatedFixtureCleanup':borrower,
             'profileRemoved':not self.home.exists(),'nativeOwnerReleased':not self.f.owner.homes,'registry':Registry.stats(),'pendingAsyncTasks':0}
        ENDS.append(end);self.assertTrue(end['profileRemoved']);self.assertTrue(end['nativeOwnerReleased']);self.assertEqual(end['registry']['total_refcounts'],0)
    def prep(self):return LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api))
    def open(self):
        for conn in self.f.connections:self.assertEqual(conn.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(self.f.owner.owns(self.home))
    def refuse_close(self):
        with self.assertRaises(REJECTIONS):self.o.close()
        self.open();self.assertEqual(self.o._stage,'VERIFIED')
    @contextmanager
    def watched(self):
        global WATCH
        before=[conn.total_changes for conn in self.f.connections];queries=[];counts=Registry.stats()
        for conn in self.f.connections:conn.set_trace_callback(queries.append)
        record={'case':self._testMethodName,'sqliteOpens':0,'rawDatabaseOpens':0};WATCH=record
        try:yield
        finally:
            WATCH=None
            for conn in self.f.connections:conn.set_trace_callback(None)
            self.assertEqual([conn.total_changes for conn in self.f.connections],before);self.assertEqual(Registry.stats(),counts)
            self.assertTrue(all(query.startswith(('SELECT ','PRAGMA ')) for query in queries),queries[-5:])
            record.update(sqlRowChanges=0,queryCount=len(queries));CHECKS.append(record)
    def test_borrower_reuses_exact_handles_once_and_owner_close_refuses(self):
        with self.watched():consumer=self.prep();consumer.check();self.refuse_close()
        self.assertTrue(all(a is b for a,b in zip(consumer._stores,self.f.stores)))
        self.assertEqual(self.o.expectation.epoch,1)
        self.assertEqual(tuple(self.f.connections[0].execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),(1,'s124b1-owned'))
        self.assertFalse(consumer.status()['runtimeAdmissionAuthorized'])
    def test_ordered_detach_leaves_handles_until_owner_and_lease_until_caller(self):
        consumer=self.prep()
        with self.watched():LOOP.run_until_complete(consumer.detach());LOOP.run_until_complete(consumer.detach())
        self.assertEqual((consumer._bundle._stage,consumer._binding._stage,consumer._stage),('DETACHED','DETACHED','DETACHED'));self.open()
        self.o.close();self.o.close()
        for conn in self.f.connections:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.assertTrue(self.f.owner.owns(self.home));self.assertTrue(self.o.status()['callerLeaseMayBeReleased'])
    def test_direct_native_detach_does_not_forge_owner_acknowledgment(self):
        consumer=self.prep();LOOP.run_until_complete(consumer._adapter.disconnect());consumer._runner.close_all_session_db_handles()
        self.refuse_close();self.assertEqual(consumer._stage,'ATTACHED')
    def test_slot_reentry_refused_before_second_constructor(self):
        real=c.qualify_sources;seen=[]
        def observed():
            self.refuse_close();seen.append(self.o._prepared_consumer._stage);return real()
        with patch.object(c,'qualify_sources',side_effect=observed):consumer=self.prep()
        with self.assertRaises(s.StoreStartupRejected):self.prep()
        self.assertEqual(seen,['QUALIFYING']);self.assertIs(self.o._prepared_consumer,consumer)
    def test_non_native_config_failed_attempt_retains_slot(self):
        with self.assertRaises(c.PreparedConsumerRejected):LOOP.run_until_complete(self.o.prepare_runtime({},self.api))
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.refuse_close()
        with self.assertRaises(s.StoreStartupRejected):self.prep()
    def test_bad_manifest_retains_stores_and_never_retries(self):
        with patch.object(c,'MANIFEST_SHA256','0'*64),self.assertRaises(c.PreparedConsumerRejected):self.prep()
        consumer=self.o._prepared_consumer;self.assertIsNone(consumer._runner);self.refuse_close()
        with self.assertRaises(c.PreparedConsumerRejected):LOOP.run_until_complete(consumer.prepare(self.config,self.api))
    def test_each_database_transaction_preserved_and_known_refusal_recoverable(self):
        consumer=self.prep()
        for conn in self.f.connections:
            conn.execute('BEGIN IMMEDIATE')
            try:
                with self.assertRaises(c.PreparedConsumerRejected):LOOP.run_until_complete(consumer.detach())
                self.assertTrue(conn.in_transaction);self.refuse_close();self.assertEqual(consumer._stage,'ATTACHED')
            finally:conn.rollback()
        LOOP.run_until_complete(consumer.detach());self.o.close()
    def test_actual_adapter_task_is_neither_cancelled_nor_hidden(self):
        consumer=self.prep();event=asyncio.Event()
        async def begin():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(begin());consumer._adapter._background_tasks.add(task)
        try:
            with self.assertRaises(Exception):LOOP.run_until_complete(consumer.detach())
            self.assertFalse(task.done());self.assertFalse(task.cancelled());self.refuse_close()
        finally:event.set();LOOP.run_until_complete(task);consumer._adapter._background_tasks.remove(task)
        LOOP.run_until_complete(consumer.detach())
    def test_cancelled_real_api_cleanup_await_is_unknown_not_retryable(self):
        consumer=self.prep();old=consumer._adapter._memory_sessions;entered=threading.Event();release=threading.Event();finished=threading.Event()
        class DelayedMemory:
            def close_all(self):
                entered.set()
                try:
                    if not release.wait(10):raise RuntimeError('owned fixture wait expired')
                    old.close_all()
                finally:finished.set()
        consumer._adapter._memory_sessions=DelayedMemory()
        async def trial():
            task=asyncio.create_task(consumer.detach())
            for _ in range(1000):
                if entered.is_set():break
                await asyncio.sleep(.005)
            self.assertTrue(entered.is_set());self.refuse_close();task.cancel()
            with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(consumer._stage,'CLOSE_UNKNOWN');self.assertEqual(consumer._bundle._stage,'CLOSE_UNKNOWN')
        try:LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(finished.wait(5));consumer._adapter._memory_sessions=old
        self.refuse_close()
        with self.assertRaises(c.PreparedConsumerRejected):LOOP.run_until_complete(consumer.detach())
    def test_cancelled_preparation_after_real_authority_holds_unfinished_consumer(self):
        real=c.native_types;entered=asyncio.Event();gate=asyncio.Event()
        def modified():
            values=list(real());initialize=values[4]
            async def paused(runner):
                result=await initialize(runner);entered.set();await gate.wait();return result
            values[4]=paused;return tuple(values)
        async def trial():
            with patch.object(c,'native_types',side_effect=modified):
                task=asyncio.create_task(self.o.prepare_runtime(self.config,self.api));await asyncio.wait_for(entered.wait(),10)
                self.refuse_close();task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
            self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.refuse_close()
        LOOP.run_until_complete(trial())
    def test_postdetach_committed_epoch_drift_blocks_owner_close(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());conn=self.f.connections[0]
        conn.execute('UPDATE runtime_epoch SET epoch=epoch+1');conn.commit()
        try:self.refuse_close()
        finally:
            try:conn.execute('UPDATE runtime_epoch SET epoch=epoch-1');conn.commit()
            except sqlite3.ProgrammingError:pass
    def test_postdetach_live_runner_task_blocks_without_cancellation(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());event=asyncio.Event()
        async def begin():return asyncio.create_task(event.wait())
        task=LOOP.run_until_complete(begin());consumer._runner._background_tasks.add(task)
        try:self.refuse_close();self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:event.set();LOOP.run_until_complete(task);consumer._runner._background_tasks.remove(task)
    def test_postdetach_live_authority_mutation_task_blocks(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());authority=consumer._binding._authority;event=asyncio.Event()
        async def begin():return asyncio.create_task(event.wait())
        original=getattr(authority,'_mutation_tasks',None);task=LOOP.run_until_complete(begin());authority._mutation_tasks={task}
        try:self.refuse_close();self.assertFalse(task.cancelled())
        finally:event.set();LOOP.run_until_complete(task);authority._mutation_tasks=original
    def test_postdetach_pending_response_identity_blocks_store_close(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());conn=self.f.connections[2]
        conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('idem:pending',?,1,'null')",('a'*64,));conn.commit()
        try:self.refuse_close()
        finally:
            try:conn.execute("DELETE FROM response_keys WHERE request_key='idem:pending'");conn.commit()
            except sqlite3.ProgrammingError:pass
    def test_postdetach_response_header_changed_refuses(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());conn=self.f.connections[2]
        old=conn.execute('PRAGMA application_id').fetchone()[0];conn.execute('PRAGMA application_id=7')
        try:self.refuse_close()
        finally:
            try:conn.execute('PRAGMA application_id='+str(old))
            except sqlite3.ProgrammingError:pass
    def test_postdetach_replay_connection_transaction_blocks(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());conn=self.f.connections[1];conn.execute('BEGIN IMMEDIATE')
        try:self.refuse_close();self.assertTrue(conn.in_transaction)
        finally:conn.rollback()
        self.o.close()
    def test_consumer_reference_replacement_not_treated_as_clean(self):
        consumer=self.prep();self.o._prepared_consumer=object()
        try:self.refuse_close()
        finally:self.o._prepared_consumer=consumer
    def test_equal_replacement_expectations_do_not_transfer_identity(self):
        consumer=self.prep();original=self.o._response_expected;self.o._response_expected=replace(original)
        try:
            with self.assertRaises(c.PreparedConsumerRejected):consumer.check()
            self.refuse_close()
        finally:self.o._response_expected=original
    def test_missing_third_configuration_refused_without_consumer(self):
        original=self.o._response_expected;self.o._response_expected=None
        try:
            with self.assertRaises(s.StoreStartupRejected):self.prep()
            self.assertIsNone(self.o._prepared_consumer)
        finally:self.o._response_expected=original
        self.o.close()
    def test_wrong_owner_stage_refuses_without_constructor(self):
        self.o._stage='FAILED'
        try:
            with self.assertRaises(s.StoreStartupRejected):self.prep()
            self.assertIsNone(self.o._prepared_consumer)
        finally:self.o._stage='VERIFIED'
    def test_foreign_thread_owner_close_never_releases_connections(self):
        consumer=self.prep();errors=[]
        def close():
            try:self.o.close()
            except REJECTIONS as exc:errors.append(type(exc).__name__)
        # Fixture actor is normally doubled; supply real current thread in this explicit actor control.
        actor=self.f.actor
        with patch.object(s.live.profiles,'_actor',side_effect=lambda:(actor[0],actor[1],actor[2],threading.get_ident())):
            thread=threading.Thread(target=close);thread.start();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1);self.open()
    def test_after_detach_closed_api_flags_are_rechecked(self):
        consumer=self.prep();LOOP.run_until_complete(consumer.detach());consumer._adapter._app=object()
        try:self.refuse_close()
        finally:consumer._adapter._app=None
        self.o.close()
    def test_native_service_and_admission_still_refused(self):
        consumer=self.prep()
        for action in (lambda:LOOP.run_until_complete(consumer._adapter.connect()),lambda:LOOP.run_until_complete(consumer._runner.start()),lambda:consumer._binding._authority._require_admission_open()):
            with self.assertRaises(Exception):action()
        self.assertFalse(consumer.status()['serviceStarted']);self.refuse_close()

def main():
    global LOOP,BASE,NATIVE,Config,Platform,Registry
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',action='append');args=p.parse_args()
    NATIVE=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-c124l1-native-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import-home';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE));sys.path.insert(0,str(NATIVE));sys.addaudithook(audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_registry
        Config,Platform,Registry=GatewayConfig,PlatformConfig,hermes_state_registry
        suite=unittest.TestSuite(IndependentConsumer(name) for name in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(IndependentConsumer)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close()
        imports={}
        for module in tuple(sys.modules.values()):
            name=getattr(module,'__file__',None)
            if name:
                path=Path(name).resolve()
                if path.is_relative_to(NATIVE) and path.suffix=='.py':imports[path.relative_to(NATIVE).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        names=('packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_prepared_consumer.py','config/prepared-consumer-s124b1-sources.json','scripts/qa/s124b1_startup_fixture.py','scripts/qa/c124l1_native_consumer_checks.py')
        failed={t.id().split(' (',1)[0] for t,_ in r.failures+r.errors}
        report={'result':'PASS_INDEPENDENT_NATIVE_OWNER_CONSUMER_WITH_WINDOWS_DOUBLES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'failureIds':[t.id() for t,_ in r.failures],'errorIds':[t.id() for t,_ in r.errors],
            'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'nativeImports':imports,'checks':CHECKS,'caseEnd':ENDS,'deniedEvents':DENIED,
            'realNativeStoreStartupRunnerApiStores':True,'nativeSqlLiveGatesReal':True,'linuxActorLeaseLayoutColdMountMetadataDoubled':True,'explicitFaultsIncludePausedInitializerAndMemoryCleanup':True,
            'fullLinuxAcceptance':False,'serviceAdmissionOrListenerActivated':False,'activeTaskObserverRequalified':False,'rootWslAction':False,'providerCalls':0}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sourceHashes','nativeImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-14000:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
