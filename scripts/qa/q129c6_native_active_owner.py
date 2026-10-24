"""Independent same-owner admission integration with real native/harness SQL.
Existing s124 fixture doubles only Windows actor/lease metadata/layout/mount/cold
helpers. Explicit unknown/await faults are labelled. No full agent/HTTP/Linux claim.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,threading,sqlite3,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
BASE=LOOP=OTHER=NATIVE=HARNESS=Fixture=Startup=Consumer=Config=Platform=RT=Registry=None
WATCH=None;CHECKS=[];ENDS=[];RACES=[];DENIED=[]

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        DENIED.append(event);raise PermissionError('q129c6_owned_offline')
    if WATCH is not None:
        if event=='sqlite3.connect':WATCH['newConnections']+=1;raise AssertionError('new_sqlite_handle')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            name=Path(os.fsdecode(args[0])).name
            if any(name==n or name.startswith(n+'-') for n in ('state.db','runs_idempotency.db','response_store.db')):
                WATCH['rawDatabaseOpens']+=1;raise AssertionError('raw_database_descriptor')

class OwnerIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='profile-',dir=BASE);self.home=Path(self.tmp.name).resolve()
        self.f=Fixture.NativeFixture(NATIVE,self.home,LOOP);self.o=self.f.startup;self.c=None
        self.stores=self.f.stores;self.connections=self.f.connections
        self.config=Config(multiplex_profiles=False,write_sessions_json=False);self.api=Platform(extra={'key':'q129-owned','model_name':'offline'})
        self.threads=[];self.releases=[]
    def tearDown(self):
        global WATCH
        WATCH=None
        for event in self.releases:event.set()
        for t in self.threads:t.join(12)
        self.assertFalse(any(t.is_alive() for t in self.threads));self.assertFalse([t for t in asyncio.all_tasks(LOOP) if not t.done()])
        before={'owner':self.o._stage,'consumer':getattr(self.o._prepared_consumer,'_stage',None),'phase':getattr(self.o._prepared_consumer,'_admission_phase',None)}
        self.f.cleanup_fixture();self.tmp.cleanup();counts=Registry.stats()
        ENDS.append({'case':self._testMethodName,'beforeFixtureCleanup':before,'temporaryProfileRemoved':not self.home.exists(),'ownershipReleased':not self.f.owner.homes,'registry':counts})
        self.assertFalse(self.home.exists());self.assertFalse(self.f.owner.homes);self.assertEqual(counts['total_refcounts'],0)
    def call(self,fn,*args,**kwargs):
        async def run():return fn(*args,**kwargs)
        return LOOP.run_until_complete(run())
    def prepare(self):
        self.c=LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=True));return self.c
    def activate(self):
        c=self.prepare();self.call(c.activate_admission);return c
    def remains_open(self):
        for conn in self.connections:self.assertEqual(conn.execute('SELECT 1').fetchone()[0],1)
        self.assertTrue(self.f.owner.owns(self.home))
    def blocked_close(self):
        with self.assertRaises((Consumer.PreparedConsumerRejected,Startup.StoreStartupRejected)):self.o.close()
        self.remains_open();self.assertEqual(self.o._stage,'VERIFIED')
    def session(self):self.stores[0].create_session('q129-session','api_server')
    def admit(self,name='q129-request',extra=None):
        return RT.admit_session_input(self.stores[0],epoch=self.o.expectation.epoch,principal_id='api',session_id='q129-session',request_id=name,payload={'text':name},_authorize_write=self.c._runner.session_authority._admission_gate(extra))
    def claim(self):
        return RT.claim_session_input(self.stores[0],epoch=self.o.expectation.epoch,session_id='q129-session',_guard=self.c._runner.session_authority._admission_gate())
    def drain(self):return self.call(self.c.begin_drain)
    def finish(self):return self.call(self.c.finish_drain)
    def pending(self):
        event=asyncio.Event()
        async def create():return asyncio.create_task(event.wait())
        return event,LOOP.run_until_complete(create())
    @contextmanager
    def watched(self):
        global WATCH
        before=[c.total_changes for c in self.connections];q=[];record={'case':self._testMethodName,'newConnections':0,'rawDatabaseOpens':0}
        for c in self.connections:c.set_trace_callback(q.append)
        WATCH=record
        try:yield
        finally:
            WATCH=None
            for c in self.connections:c.set_trace_callback(None)
            self.assertEqual([c.total_changes for c in self.connections],before)
            self.assertTrue(all(s.startswith(('SELECT ','PRAGMA ')) for s in q),q[-6:])
            record.update(rowChanges=0,queryCount=len(q));CHECKS.append(record)
    def test_explicit_generation_same_owner_three_handles_epoch(self):
        with self.watched():
            c=self.prepare();r=self.call(c.activate_admission);self.call(c.check);self.blocked_close()
        self.assertIs(self.o._prepared_consumer,c);self.assertIs(c._owner,self.o)
        self.assertTrue(all(x is y for x,y in zip(c._stores,self.stores)))
        self.assertEqual(r['nativeFeature'],'1b7b31e14451baf1d56c3edbfa2cea69a8f7940c')
        self.assertEqual(r['nativeAdmissionState'],'ACTIVE');self.assertFalse(r['workHealthEvaluated']);self.assertFalse(r['runtimeAdmissionAuthorized'])
        self.assertEqual(tuple(self.connections[0].execute('SELECT epoch,instance_id FROM runtime_epoch').fetchone()),(1,'s124b1-owned'))
    def test_default_source_does_not_auto_select_new_feature(self):
        with self.assertRaisesRegex(Consumer.PreparedConsumerRejected,'source_unqualified'):LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api))
        self.assertEqual(self.o._prepared_consumer._stage,'FAILED_UNKNOWN');self.blocked_close()
    def test_nonboolean_selection_refused_before_consumer_reservation(self):
        for value in (1,0,'true',None):
            with self.assertRaises(Startup.StoreStartupRejected):LOOP.run_until_complete(self.o.prepare_runtime(self.config,self.api,local_admission=value))
            self.assertIsNone(self.o._prepared_consumer)
    def test_active_and_draining_never_allow_direct_close_or_detach(self):
        c=self.activate()
        for phase in ('ACTIVE','DRAINING'):
            if phase=='DRAINING':self.drain()
            with self.watched():
                self.blocked_close()
                with self.assertRaises(Consumer.PreparedConsumerRejected):LOOP.run_until_complete(c.detach())
            self.assertEqual((c._stage,c._bundle._stage,c._binding._stage),('ATTACHED','ATTACHED',phase))
    def test_full_empty_lifecycle_closes_only_original_owner_then_lease(self):
        c=self.activate()
        with self.watched():self.drain();self.finish();self.blocked_close();LOOP.run_until_complete(c.detach())
        self.remains_open();self.assertEqual((c._stage,c._binding._stage),('DETACHED','DETACHED'))
        self.o.close();self.assertEqual(self.o._stage,'CLOSED')
        for conn in self.connections:
            with self.assertRaises(sqlite3.ProgrammingError):conn.execute('SELECT 1')
        self.assertTrue(self.f.owner.owns(self.home));self.f.owner.close()
    def test_queued_work_passes_identity_but_not_finish(self):
        self.session();c=self.activate();row=self.admit()
        with self.watched():
            result=self.call(c.check);self.blocked_close();self.drain();self.call(c.check)
            with self.assertRaises(Startup.live.LiveStoreRejected):self.finish()
        self.assertFalse(result['workHealthEvaluated']);self.assertFalse(result['storeReleaseAuthorized'])
        self.assertEqual(RT.get_session_admission(self.stores[0],admission_id=row['admission_id'])['status'],'queued');self.assertEqual(c._admission_phase,'DRAINING')
    def test_claimed_leaf_settles_during_drain_and_owner_can_close(self):
        self.session();c=self.activate();row=self.admit();claim=self.claim();self.drain()
        with self.assertRaises(Startup.live.LiveStoreRejected):self.finish()
        RT.settle_session_input(self.stores[0],epoch=self.o.expectation.epoch,admission_id=row['admission_id'],generation=claim['generation'],outcome='completed')
        self.finish();LOOP.run_until_complete(c.detach());self.o.close();self.assertEqual(self.o._stage,'CLOSED')
    def test_unknown_record_is_not_health_or_recovery_permission(self):
        self.session();c=self.activate();row=self.admit();db=self.connections[0]
        db.execute("UPDATE session_admissions SET status='unknown'");db.commit()
        with self.watched():
            r=self.call(c.check);self.drain();self.call(c.check)
            with self.assertRaises(Startup.live.LiveStoreRejected):self.finish()
        self.assertFalse(r['fullD3BAccepted']);self.assertEqual(RT.get_session_admission(self.stores[0],admission_id=row['admission_id'])['status'],'unknown')
    def test_pending_response_identity_allowed_active_clean_gate_unchanged(self):
        c=self.activate();conn=self.connections[2];conn.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('pending',?,1,'null')",('d'*64,));conn.commit()
        with self.watched():
            self.call(c.check)
            with self.assertRaises(Startup.response_live.ResponseLiveRejected):Startup.response_live.verify_response_connection(self.f.held,self.f.mount,self.stores[0],self.stores[2],self.o._response_live_expectation())
            self.drain()
            with self.assertRaises(Startup.response_live.ResponseLiveRejected):self.finish()
        self.assertIsNone(conn.execute('SELECT settled_at FROM response_keys').fetchone()[0])
    def test_malformed_replay_is_not_declared_valid_work_by_identity(self):
        c=self.activate();self.stores[1].reserve('test','pending','e'*64,'pending',{'status':'running'})
        db=self.connections[1];db.execute("UPDATE run_idempotency SET status_json='not json'");db.commit()
        with self.watched():
            r=self.call(c.check);self.drain()
            with self.assertRaises(Startup.live.LiveStoreRejected):self.finish()
        self.assertFalse(r['workHealthEvaluated']);self.assertEqual(db.execute('SELECT status_json FROM run_idempotency').fetchone()[0],'not json')
    def test_actual_pending_task_allowed_identity_never_pruned_by_finish(self):
        c=self.activate();event,task=self.pending();c._runner._background_tasks.add(task)
        try:
            with self.watched():
                self.call(c.check);self.drain();self.call(c.check)
                with self.assertRaises(Consumer.PreparedConsumerRejected):self.finish()
            self.assertFalse(task.done());self.assertFalse(task.cancelled())
        finally:event.set();LOOP.run_until_complete(task);c._runner._background_tasks.remove(task)
        self.finish();LOOP.run_until_complete(c.detach());self.o.close()
    def test_seal_with_any_open_transaction_keeps_it_unmodified(self):
        c=self.activate()
        for db in self.connections:
            db.execute('BEGIN IMMEDIATE')
            try:
                self.drain();self.assertTrue(db.in_transaction)
                with self.assertRaises(Consumer.PreparedConsumerRejected):self.call(c.check)
                with self.assertRaises(Consumer.PreparedConsumerRejected):self.finish()
                self.assertEqual(c._admission_phase,'DRAINING');self.assertTrue(db.in_transaction)
            finally:db.rollback()
        self.finish()
    def test_seal_does_not_wait_for_blocked_native_writer(self):
        self.session();c=self.activate();entered=threading.Event();result=[];state=self.stores[0]
        def write():
            entered.set()
            try:result.append(self.admit())
            except RT.RuntimeStoreError as exc:result.append(exc.reason)
        state._lock.acquire()
        try:
            t=threading.Thread(target=write);self.threads.append(t);t.start();self.assertTrue(entered.wait(5));self.drain()
            self.assertTrue(t.is_alive());self.assertEqual(c._admission_phase,'DRAINING')
        finally:state._lock.release()
        t.join(10);self.assertFalse(t.is_alive());self.assertEqual(result,['runtime_draining']);self.finish()
        RACES.append({'case':self._testMethodName,'guardNotYetPassed':True,'drainReturnedWithMutexHeld':True,'newAdmissionCommitted':False})
    def test_cancelled_tracked_writer_preserved_through_original_owner(self):
        from gateway.session_runtime_workers import tracked_write
        self.session();c=self.activate();entered=threading.Event();release=threading.Event();self.releases.append(release)
        def extra(conn):
            entered.set()
            if not release.wait(15):raise TimeoutError('owned tracked writer release')
        async def trial():
            caller=asyncio.create_task(tracked_write(c._runner.session_authority,lambda:self.admit('tracked',extra),ordered=True))
            try:
                for _ in range(1000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());caller.cancel()
                with self.assertRaises(asyncio.CancelledError):await caller
                writers=list(c._runner.session_authority._mutation_tasks);self.assertTrue(writers)
                c.begin_drain();self.assertEqual(c._admission_phase,'DRAINING')
                with self.assertRaises(Consumer.PreparedConsumerRejected):c.finish_drain()
                with self.assertRaises(Consumer.PreparedConsumerRejected):self.o.close()
                self.assertTrue(any(not task.done() for task in writers));release.set()
                result=await asyncio.gather(*writers,return_exceptions=True);self.assertFalse(any(isinstance(v,BaseException) for v in result),result)
                await asyncio.sleep(0);self.assertFalse(c._runner.session_authority._mutation_tasks)
            finally:
                release.set()
                await asyncio.gather(caller,return_exceptions=True)
                pending=list(getattr(c._runner.session_authority,'_mutation_tasks',()))
                if pending:await asyncio.wait_for(asyncio.gather(*pending,return_exceptions=True),12)
        LOOP.run_until_complete(trial())
        self.assertEqual(self.connections[0].execute("SELECT status FROM session_admissions WHERE request_id='tracked'").fetchone()[0],'queued')
        with self.assertRaises(Startup.live.LiveStoreRejected):self.finish()
        self.blocked_close();RACES.append({'case':self._testMethodName,'nativeTrackedWriter':True,'callerCancelled':True,'acceptedQueuedRowRetained':True,'ownerCloseRefused':True})
    def test_late_response_after_drained_refuses_before_api_effect(self):
        c=self.activate();self.drain();self.finish();db=self.connections[2]
        db.execute("INSERT INTO response_keys(request_key,fingerprint,created_at,model_json) VALUES('late',?,1,'null')",('f'*64,));db.commit()
        with self.assertRaises(Startup.response_live.ResponseLiveRejected):LOOP.run_until_complete(c.detach())
        self.assertEqual((c._stage,c._bundle._stage,c._admission_phase),('ATTACHED','ATTACHED','DRAINED'));self.blocked_close()
    def test_late_replay_after_detach_blocks_original_store_close(self):
        c=self.activate();self.drain();self.finish();LOOP.run_until_complete(c.detach())
        self.stores[1].reserve('test','late','a'*64,'late',{'status':'running'})
        self.blocked_close();self.assertEqual(c._stage,'DETACHED')
    def test_active_identity_checks_actual_epoch_not_pending_counts(self):
        c=self.activate();db=self.connections[0];db.execute('UPDATE runtime_epoch SET epoch=epoch+1');db.commit()
        try:
            with self.assertRaises(Startup.live.LiveStoreRejected):self.call(c.check)
            self.blocked_close()
        finally:db.execute('UPDATE runtime_epoch SET epoch=epoch-1');db.commit()
    def test_active_identity_checks_schema_with_pending_work(self):
        self.session();c=self.activate();self.admit();db=self.connections[1];db.execute('CREATE TABLE unrelated_fixture(x)');db.commit()
        try:
            with self.assertRaises(Startup.live.LiveStoreRejected):self.call(c.check)
            self.blocked_close()
        finally:db.execute('DROP TABLE unrelated_fixture');db.commit()
    def test_other_loop_cannot_activate_or_drain(self):
        c=self.prepare()
        async def invoke(fn):return fn()
        with self.assertRaises(Consumer.PreparedConsumerRejected):OTHER.run_until_complete(invoke(c.activate_admission))
        self.call(c.activate_admission)
        with self.assertRaises(Consumer.PreparedConsumerRejected):OTHER.run_until_complete(invoke(c.begin_drain))
        self.assertEqual(c._admission_phase,'ACTIVE')
    def test_unknown_native_import_refuses_before_activation(self):
        from types import SimpleNamespace
        c=self.prepare();key='q129_unqualified_native';sys.modules[key]=SimpleNamespace(__file__=str(NATIVE/'not_in_manifest.py'))
        try:
            with self.assertRaises(Consumer.PreparedConsumerRejected):self.call(c.activate_admission)
            self.assertEqual((c._admission_phase,c._binding._stage),('PREPARED','PREPARED'))
        finally:del sys.modules[key]
    def test_native_completed_transition_then_error_retains_unknown(self):
        c=self.prepare();real=c._bundle.activate_admission
        def fault():real();raise RuntimeError('explicit after-native-activation fixture')
        with patch.object(c._bundle,'activate_admission',side_effect=fault):
            with self.assertRaises(RuntimeError):self.call(c.activate_admission)
        self.assertEqual((c._stage,c._admission_phase,c._binding._stage),('ADMISSION_UNKNOWN','UNKNOWN','ACTIVE'))
        self.blocked_close()
        with self.assertRaises(Consumer.PreparedConsumerRejected):self.call(c.activate_admission)
    def test_cancelled_cleanup_retains_unknown_and_all_connections(self):
        c=self.activate();self.drain();self.finish();real=c._adapter._memory_sessions
        entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release)
        class SlowMemory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(15):raise TimeoutError('owned memory cleanup release')
                    real.close_all()
                finally:done.set()
        c._adapter._memory_sessions=SlowMemory()
        async def trial():
            task=asyncio.create_task(c.detach())
            try:
                for _ in range(1000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                self.assertFalse(done.is_set())
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));c._adapter._memory_sessions=real
        self.assertEqual((c._stage,c._bundle._stage),('CLOSE_UNKNOWN','CLOSE_UNKNOWN'));self.blocked_close()
        with self.assertRaises(Consumer.PreparedConsumerRejected):LOOP.run_until_complete(c.detach())
    def test_new_replay_during_cleanup_await_is_not_successful_detach(self):
        c=self.activate();self.drain();self.finish();real=c._adapter._memory_sessions
        entered=threading.Event();release=threading.Event();done=threading.Event();self.releases.append(release)
        class SlowMemory:
            def close_all(inner):
                entered.set()
                try:
                    if not release.wait(15):raise TimeoutError('owned cleanup release')
                    real.close_all()
                finally:done.set()
        c._adapter._memory_sessions=SlowMemory()
        async def trial():
            task=asyncio.create_task(c.detach())
            try:
                for _ in range(1000):
                    if entered.is_set():break
                    await asyncio.sleep(.002)
                self.assertTrue(entered.is_set());self.stores[1].reserve('test','late','b'*64,'late',{'status':'running'});release.set()
                with self.assertRaises(Exception):await task
            finally:release.set();await asyncio.gather(task,return_exceptions=True)
        try:LOOP.run_until_complete(trial())
        finally:release.set();self.assertTrue(done.wait(5));c._adapter._memory_sessions=real
        self.assertEqual(c._stage,'CLOSE_UNKNOWN');self.blocked_close()
    def test_identity_policy_cannot_relax_constructor_or_accept_nonbool(self):
        for value in (0,1,None,'false'):
            with self.assertRaises(Startup.live.LiveStoreRejected):Startup.live.verify_live_stores(self.f.held,self.f.mount,*self.stores[:2],self.o.expectation,require_idle=value)
        with self.assertRaises(Startup.response_live.ResponseLiveRejected):Startup.response_live.verify_response_connection(self.f.held,self.f.mount,self.stores[0],self.stores[2],self.o._response_live_expectation(),constructor=True,require_idle=False)

def main():
    global BASE,LOOP,OTHER,NATIVE,HARNESS,Fixture,Startup,Consumer,Config,Platform,RT,Registry
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--harness',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--case',action='append');a=p.parse_args()
    NATIVE=a.native.resolve(strict=True);HARNESS=a.harness.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    LOOP=asyncio.new_event_loop();OTHER=asyncio.new_event_loop();asyncio.set_event_loop(LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-q129c6-tests-') as tmp:
        BASE=Path(tmp).resolve();home=BASE/'imports';home.mkdir();os.environ.update(HERMES_HOME=str(home),HOME=str(BASE),USERPROFILE=str(BASE),APPDATA=str(BASE),LOCALAPPDATA=str(BASE))
        sys.path[:0]=[str(HARNESS/'packages/claw-hermes'),str(HARNESS/'scripts/qa'),str(NATIVE)];sys.addaudithook(audit)
        import s124b1_startup_fixture,gateway_prepared_consumer,gateway_store_startup
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_runtime,hermes_state_registry
        Fixture,Consumer,Startup=s124b1_startup_fixture,gateway_prepared_consumer,gateway_store_startup
        Config,Platform,RT,Registry=GatewayConfig,PlatformConfig,hermes_state_runtime,hermes_state_registry
        suite=unittest.TestSuite(OwnerIntegration(name) for name in a.case) if a.case else unittest.defaultTestLoader.loadTestsFromTestCase(OwnerIntegration)
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        LOOP.run_until_complete(LOOP.shutdown_default_executor());LOOP.close();OTHER.close()
        native={};harness={}
        for mod in tuple(sys.modules.values()):
            path=getattr(mod,'__file__',None)
            if path:
                q=Path(path).resolve()
                if q.suffix=='.py':
                    if q.is_relative_to(NATIVE):native[q.relative_to(NATIVE).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
                    if q.is_relative_to(HARNESS):harness[q.relative_to(HARNESS).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        hashes={n:hashlib.sha256((HARNESS/n).read_bytes()).hexdigest() for n in ('config/admission-consumer-b129d6-sources.json','config/prepared-consumer-s124b1-sources.json')}
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        report={'result':'PASS_INDEPENDENT_ACTIVE_OWNER_WITH_OS_DOUBLES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
            'nativeImports':native,'harnessImports':harness,'configHashes':hashes,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':CHECKS,'caseEnd':ENDS,'races':RACES,'deniedEvents':DENIED,
            'actualNativeStartupOwnerAndConsumer':True,'nativeSqlAndAdmissionGuardsReal':True,'windowsLinuxActorLeaseMountColdBoundariesDoubled':True,'unknownTransitionAndMemoryCleanupFaultsExplicit':True,'fullNativeAgentOrHttpExecution':False,'fullLinuxIsolationAccepted':False,'providerCalls':0,'rootWslAction':False}
    report['temporaryRootRemoved']=not BASE.exists();(out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','harnessImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-14000:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
