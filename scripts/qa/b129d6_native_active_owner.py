"""Real original owner + native local admission; explicit Windows OS-boundary doubles.
No native/owner/live SQL replacement in normal cases. Fault injections are named.
No full native task/agent/HTTP admission, queue recovery or Linux confinement claim.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(ROOT/'scripts/qa')]
import s124b1_startup_fixture as fixture
import gateway_prepared_consumer as consumer
startup=fixture.startup
LOOP=OTHER=BASE=NATIVE=Config=Platform=RT=Registry=None
WATCH=None;CHECKS=[];ENDS=[];RACES=[];DENIED=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append(event);raise PermissionError('b129d6_owned_offline')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('new_sqlite_in_observation')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('raw_database_in_observation')

class ActiveOwnerCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        self.f=fixture.NativeFixture(NATIVE,self.home,LOOP);self.o=self.f.startup
        self.config=Config(multiplex_profiles=False,write_sessions_json=False)
        self.api=Platform(extra={'key':'b129d6-fixture-only','model_name':'offline'})
        self.releases=[];self.threads=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        for event in self.releases:event.set()
        for thread in self.threads:thread.join(12)
        self.assertFalse(any(t.is_alive() for t in self.threads))
        self.assertFalse([t for t in asyncio.all_tasks(LOOP) if not t.done()])
        c=self.o._prepared_consumer
        state={'owner':self.o._stage,'consumer':getattr(c,'_stage',None),'phase':getattr(c,'_admission_phase',None)}
        self.f.cleanup_fixture();self.tmp.cleanup()
        ENDS.append({'case':self._testMethodName,'beforeFixtureCleanup':state,'profileRemoved':not self.home.exists(),'nativeOwnershipReleased':not self.f.owner.homes,'registry':Registry.stats()})
        self.assertFalse(self.home.exists());self.assertFalse(self.f.owner.homes);self.assertEqual(Registry.stats()['total_refcounts'],0)
    def call(self,fn,*args):
        async def invoke():return fn(*args)
        return LOOP.run_until_complete(invoke())
    def prepare(self,**kw):return LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True,**kw))
    def open(self):
        for conn in self.f.connections:self.assertEqual(conn.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(self.f.owner.owns(self.home))
    def blocked_close(self):
        with self.assertRaises((consumer.PreparedConsumerRejected,startup.StoreStartupRejected)):self.o.close()
        self.assertEqual(self.o._stage,'VERIFIED');self.open()
    @contextmanager
    def watched(self):
        global WATCH
        before=[c.total_changes for c in self.f.connections];record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0};WATCH=record
        try:yield
        finally:
            WATCH=None;self.assertEqual(before,[c.total_changes for c in self.f.connections]);record['rowChanges']=0;CHECKS.append(record)
    def session(self):self.f.stores[0].create_session('b129-owned','api_server')
    def admit(self,c,request='one',extra=None):
        return RT.admit_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,principal_id='api',session_id='b129-owned',request_id=request,payload={'text':request},_authorize_write=c._binding._authority._admission_gate(extra))
    def stop_clean(self,c):
        self.call(c.begin_drain);self.call(c.finish_drain);LOOP.run_until_complete(c.detach());self.o.close()
    def test_empty_full_same_owner_lifecycle_and_external_profile_release(self):
        with self.watched():
            c=self.prepare();self.call(c.activate_admission);status=self.call(c.check);self.blocked_close()
            self.assertTrue(status['localAdmissionOpen']);self.assertFalse(status['runtimeAdmissionAuthorized'])
            self.assertIs(self.o._prepared_consumer,c);self.assertEqual(c._stores,self.f.stores)
            self.call(c.begin_drain);self.call(c.finish_drain);LOOP.run_until_complete(c.detach())
        self.open();self.assertEqual(tuple(self.f.connections[0].execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),(1,'s124b1-owned'))
        self.o.close();self.assertEqual(self.o._stage,'CLOSED');self.assertTrue(self.f.owner.owns(self.home))
        for conn in self.f.connections:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.f.owner.close();self.assertFalse(self.f.owner.homes)
    def test_default_source_mode_does_not_silently_accept_new_native(self):
        with self.assertRaises(consumer.PreparedConsumerRejected):LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api))
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.blocked_close()
    def test_invalid_selection_refuses_before_slot_reservation(self):
        for value in (1,0,None,'true'):
            with self.assertRaises(startup.StoreStartupRejected):LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=value))
            self.assertIsNone(self.o._prepared_consumer)
        self.o.close()
    def test_new_generation_starts_prepared_with_admission_closed(self):
        c=self.prepare();self.assertEqual(c._admission_phase,'PREPARED')
        with self.assertRaises(RT.RuntimeStoreError):c._binding._authority._require_admission_open()
        with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.begin_drain)
        LOOP.run_until_complete(c.detach());self.o.close()
    def test_direct_native_activation_cannot_impersonate_consumer_transition(self):
        c=self.prepare();self.call(c._bundle.activate_admission)
        with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.check)
        self.blocked_close();self.assertEqual(c._admission_phase,'PREPARED');self.assertEqual(c._binding._stage,'ACTIVE')
    def test_pending_admission_identity_observed_but_clean_check_stays_closed(self):
        c=self.prepare();self.call(c.activate_admission);self.session();row=self.admit(c)
        with self.watched():
            status=self.call(c.check);self.assertFalse(status['workHealthEvaluated']);self.blocked_close()
            with self.assertRaises(startup.live.LiveStoreRejected):c._storage()
            self.call(c.begin_drain);self.call(c.check)
            with self.assertRaises(startup.live.LiveStoreRejected):self.call(c.finish_drain)
        self.assertEqual(RT.get_session_admission(self.f.stores[0],admission_id=row['admission_id'])['status'],'queued')
        self.assertEqual(c._admission_phase,'DRAINING')
    def test_claim_settle_and_close_retains_same_accepted_epoch(self):
        c=self.prepare();self.call(c.activate_admission);self.session();row=self.admit(c)
        claimed=RT.claim_session_input(self.f.stores[0],epoch=self.o.expectation.epoch,session_id='b129-owned',_guard=c._binding._authority._admission_gate())
        self.call(c.check);self.call(c.begin_drain)
        with self.assertRaises(startup.live.LiveStoreRejected):self.call(c.finish_drain)
        RT.settle_session_input(self.f.stores[0],epoch=1,admission_id=row['admission_id'],generation=claimed['generation'],outcome='completed')
        self.call(c.finish_drain);LOOP.run_until_complete(c.detach());self.open();self.o.close()
    def test_pending_response_is_identity_only_not_close_permission(self):
        c=self.prepare();self.call(c.activate_admission);conn=self.f.connections[2]
        conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('pending',?,1,'null')",('a'*64,));conn.commit()
        with self.watched():
            self.call(c.check);self.call(c.begin_drain);self.call(c.check)
            with self.assertRaises(startup.response_live.ResponseLiveRejected):self.call(c.finish_drain)
            self.blocked_close()
        self.assertIsNone(conn.execute("SELECT settled_at FROM response_keys WHERE request_key='pending'").fetchone()[0])
    def test_pending_replay_is_not_adopted_as_completed(self):
        c=self.prepare();self.call(c.activate_admission)
        self.f.stores[1].reserve('test','pending','b'*64,'pending-run',{'run_id':'pending-run','status':'running'})
        with self.watched():
            self.call(c.check);self.call(c.begin_drain)
            with self.assertRaises(startup.live.LiveStoreRejected):self.call(c.finish_drain)
        self.assertIn('running',self.f.connections[1].execute('SELECT status_json FROM run_idempotency').fetchone()[0]);self.blocked_close()
    def test_identity_only_does_not_skip_schema_header_or_epoch(self):
        c=self.prepare();self.call(c.activate_admission);conn=self.f.connections[0]
        conn.execute('UPDATE runtime_epoch SET epoch=epoch+1');conn.commit()
        with self.assertRaises(startup.live.LiveStoreRejected):self.call(c.check)
        self.assertEqual(conn.execute('SELECT epoch FROM runtime_epoch').fetchone()[0],2);self.blocked_close()
    def test_identity_mode_cannot_be_used_for_constructor(self):
        with self.assertRaises(startup.response_live.ResponseLiveRejected):startup.response_live.verify_response_connection(self.o._held,self.o._mount,self.f.stores[0],self.f.stores[2],self.o._response_live_expectation(),constructor=True,require_idle=False)
    def test_active_disconnect_and_direct_owner_close_block_before_effects(self):
        c=self.prepare();self.call(c.activate_admission)
        with self.watched():
            with self.assertRaises(consumer.PreparedConsumerRejected):LOOP.run_until_complete(c.detach())
            self.blocked_close()
        self.assertEqual((c._stage,c._bundle._stage,c._binding._stage),('ATTACHED','ATTACHED','ACTIVE'))
    def test_open_transactions_do_not_prevent_withdrawal_and_are_not_rolled_back(self):
        c=self.prepare();self.call(c.activate_admission)
        for conn in self.f.connections:conn.execute('BEGIN IMMEDIATE')
        try:
            self.call(c.begin_drain);self.assertEqual(c._admission_phase,'DRAINING')
            self.assertTrue(all(conn.in_transaction for conn in self.f.connections))
            with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.finish_drain)
            self.blocked_close()
        finally:
            for conn in self.f.connections:conn.rollback()
        self.call(c.finish_drain);LOOP.run_until_complete(c.detach());self.o.close()
    def test_drain_seals_while_real_sql_writer_waits_for_mutex(self):
        c=self.prepare();self.call(c.activate_admission);self.session();entered=threading.Event();out=[]
        def writer():
            entered.set()
            try:out.append(self.admit(c))
            except RT.RuntimeStoreError as exc:out.append(exc.reason)
        state=self.f.stores[0];state._lock.acquire()
        try:
            t=threading.Thread(target=writer);self.threads.append(t);t.start();self.assertTrue(entered.wait(5))
            self.call(c.begin_drain);self.assertEqual(c._admission_phase,'DRAINING');self.assertTrue(t.is_alive())
        finally:state._lock.release()
        t.join(10);self.assertFalse(t.is_alive());self.assertEqual(out,['runtime_draining']);self.call(c.finish_drain)
        RACES.append({'case':self._testMethodName,'blockedWriterRefused':True,'nativeMutexNotWaitedByDrain':True})
    def test_cancelled_carrier_does_not_close_original_owner_over_inflight_commit(self):
        from gateway.session_runtime_workers import tracked_write
        c=self.prepare();self.call(c.activate_admission);self.session();entered=threading.Event();release=threading.Event();self.releases.append(release)
        authority=c._binding._authority
        def authorize(conn):
            entered.set()
            if not release.wait(15):raise TimeoutError('fixture release')
        async def run():
            carrier=asyncio.create_task(tracked_write(authority,lambda:self.admit(c,'late',authorize),ordered=True))
            try:
                for _ in range(2000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());carrier.cancel()
                with self.assertRaises(asyncio.CancelledError):await carrier
                jobs=list(authority._mutation_tasks);self.assertTrue(jobs)
                c.begin_drain();self.assertEqual(c._admission_phase,'DRAINING')
                with self.assertRaises(consumer.PreparedConsumerRejected):c.finish_drain()
                with self.assertRaises((consumer.PreparedConsumerRejected,startup.StoreStartupRejected)):self.o.close()
                release.set();results=await asyncio.gather(*jobs,return_exceptions=True);await asyncio.sleep(0)
                self.assertFalse(any(isinstance(r,BaseException) for r in results),results)
            finally:
                release.set()
                jobs=list(getattr(authority,'_mutation_tasks',()))
                if jobs:await asyncio.wait_for(asyncio.gather(*jobs,return_exceptions=True),12)
                await asyncio.gather(carrier,return_exceptions=True)
        LOOP.run_until_complete(run());self.open();self.assertEqual(self.f.connections[0].execute("SELECT status FROM session_admissions WHERE request_id='late'").fetchone()[0],'queued')
        with self.assertRaises(startup.live.LiveStoreRejected):self.call(c.finish_drain)
        RACES.append({'case':self._testMethodName,'nativeTrackedWrite':True,'cancelledCarrier':True,'lateQueuedCommitRetained':True,'originalOwnerCloseRefused':True})
    def test_drain_under_live_registered_task_never_cancels_it(self):
        c=self.prepare();self.call(c.activate_admission);gate=asyncio.Event()
        async def create():return asyncio.create_task(gate.wait())
        task=LOOP.run_until_complete(create());c._runner._background_tasks.add(task)
        try:
            self.call(c.begin_drain)
            with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.finish_drain)
            self.assertFalse(task.cancelled());self.assertFalse(task.done())
        finally:gate.set();LOOP.run_until_complete(task);c._runner._background_tasks.remove(task)
        self.call(c.finish_drain)
    def test_late_unsettled_row_after_drained_blocks_detach(self):
        c=self.prepare();self.call(c.activate_admission);self.call(c.begin_drain);self.call(c.finish_drain)
        conn=self.f.connections[2];conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('late',?,1,'null')",('c'*64,));conn.commit()
        with self.assertRaises(startup.response_live.ResponseLiveRejected):LOOP.run_until_complete(c.detach())
        self.assertEqual(c._stage,'ATTACHED');self.assertEqual(c._bundle._stage,'ATTACHED');self.blocked_close()
    def test_late_sql_epoch_after_detached_blocks_original_close(self):
        c=self.prepare();self.call(c.activate_admission);self.call(c.begin_drain);self.call(c.finish_drain);LOOP.run_until_complete(c.detach())
        self.f.connections[0].execute('UPDATE runtime_epoch SET epoch=epoch+1');self.f.connections[0].commit();self.blocked_close()
    def test_wrong_loop_cannot_activate_or_drain(self):
        c=self.prepare()
        async def other(fn):return fn()
        with self.assertRaises(consumer.PreparedConsumerRejected):OTHER.run_until_complete(other(c.activate_admission))
        self.assertEqual(c._admission_phase,'PREPARED');self.call(c.activate_admission)
        with self.assertRaises(consumer.PreparedConsumerRejected):OTHER.run_until_complete(other(c.begin_drain))
        self.assertEqual(c._admission_phase,'ACTIVE')
    def test_source_envelope_remains_fixed_and_unknown_import_blocks_transition(self):
        from types import SimpleNamespace
        c=self.prepare();root,_=c._source_proof;name='b129_fixture_unknown_source';sys.modules[name]=SimpleNamespace(__file__=str(root/'unlisted_fixture.py'))
        try:
            with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.activate_admission)
            self.assertEqual(c._admission_phase,'PREPARED')
        finally:del sys.modules[name]
    def test_direct_native_drained_state_cannot_authorize_owner_release(self):
        c=self.prepare();self.call(c.activate_admission);self.call(c._bundle.begin_drain);self.call(c._bundle.finish_drain)
        with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.check)
        self.blocked_close();self.assertEqual(c._admission_phase,'ACTIVE')
    def test_native_transition_uncertainty_keeps_owner_without_retry(self):
        c=self.prepare();real=c._bundle.activate_admission
        def failure():real();raise RuntimeError('explicit post-effect native fault')
        with patch.object(c._bundle,'activate_admission',side_effect=failure):
            with self.assertRaises(RuntimeError):self.call(c.activate_admission)
        self.assertEqual(c._stage,'ADMISSION_UNKNOWN');self.assertEqual(c._admission_phase,'UNKNOWN');self.blocked_close()
        with self.assertRaises(consumer.PreparedConsumerRejected):self.call(c.activate_admission)
    def test_service_and_provider_permission_remain_separate(self):
        c=self.prepare();self.call(c.activate_admission)
        with self.assertRaises(Exception):LOOP.run_until_complete(c._runner.start())
        with self.assertRaises(Exception):LOOP.run_until_complete(c._adapter.connect())
        s=c.status();self.assertFalse(s['serviceStarted']);self.assertFalse(s['runtimeAdmissionAuthorized']);self.assertFalse(s['activeTaskObserversQualified']);self.blocked_close()


def main():
    global LOOP,OTHER,BASE,NATIVE,Config,Platform,RT,Registry
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--case',action='append');args=parser.parse_args()
    NATIVE=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();OTHER=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-b129d6-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'import-home';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),APPDATA=str(BASE),LOCALAPPDATA=str(BASE))
        sys.path.insert(0,str(NATIVE));sys.addaudithook(audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_runtime,hermes_state_registry
        Config,Platform,RT,Registry=GatewayConfig,PlatformConfig,hermes_state_runtime,hermes_state_registry
        suite=unittest.TestSuite(ActiveOwnerCases(n) for n in args.case) if args.case else unittest.defaultTestLoader.loadTestsFromTestCase(ActiveOwnerCases)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close();OTHER.close()
        imports={}
        for mod in tuple(sys.modules.values()):
            f=getattr(mod,'__file__',None)
            if f:
                p=Path(f).resolve()
                if p.is_relative_to(NATIVE) and p.suffix=='.py':imports[p.relative_to(NATIVE).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
        names=['packages/claw-hermes/'+n for n in ('gateway_store_startup.py','gateway_prepared_consumer.py','gateway_live_store_gate.py','gateway_response_live.py','gateway_consumer_admission.py')]+['config/admission-consumer-b129d6-sources.json','scripts/qa/s124b1_startup_fixture.py','scripts/qa/b129d6_native_active_owner.py']
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        report={'result':'PASS_REAL_OWNER_LOCAL_ADMISSION_WINDOWS_BOUNDARIES_DOUBLED' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'nativeImports':imports,'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'checks':CHECKS,'caseEnd':ENDS,'races':RACES,'deniedEvents':DENIED,'originalOwnerAndNativeConstructorsAndSqlReal':True,'linuxActorLeaseMetadataMountColdDoubled':True,'explicitPostEffectTransitionFaultDoubled':True,'wholeApiTurnOrAgentExecuted':False,'queuedWorkRetiredAutomatically':False,'linuxConfinementTested':False,'providerCalls':0,'rootWslAction':False,'nativeFeature':'1b7b31e14451baf1d56c3edbfa2cea69a8f7940c'}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','sourceHashes','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-16000:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
