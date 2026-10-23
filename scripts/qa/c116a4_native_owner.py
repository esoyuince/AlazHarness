"""Independent actual native adapter/Task acceptance of C116 observer.

Task registration/native run-map publication are explicit producer fixtures.
Real task liveness, OS process-start and native executor-thread lifetime are NOT
mocked. No HTTP producer hooks, real model turn, storage mount proof or Linux
isolation acceptance is claimed. The selected observer cannot grant any of these.
"""
from pathlib import Path
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,time,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import b112x9_adapter_probe as fixture
import gateway_work_observer as observer
import gateway_work_health as policy
from gateway_work_health_reader import NativeWorkReader
from gateway_live_store_gate import schema_digest
runtime=None
OBSERVATIONS=[]

class NativeOwnerCases(unittest.IsolatedAsyncioTestCase):
    loop_factory=staticmethod(fixture.NativeBorrowTests.loop_factory)
    build=fixture.NativeBorrowTests.build
    alive=fixture.NativeBorrowTests.alive
    def setUp(self):
        fixture.NativeBorrowTests.setUp(self)
    async def asyncSetUp(self):
        self.a=self.build()
        epoch=runtime.begin_runtime_epoch(self.state,instance_id='c116a4-owned')
        self.state.create_session('session','api')
        store=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        self.identity=policy.RuntimeIdentity(store,epoch,'c116a4-owned',os.getpid(),self.a._run_owner_started)
        # These are independent expected schemas from the already accepted native
        # preparation proof, not values learned from this candidate's schema.
        self.reader=NativeWorkReader(self.state,self.replay,self.response,self.identity,schema_hashes=(
            'f4889e8d91c8b57ee828ac7a1ead9ac880db48f9c21500e3800d4b48b759e8c7',
            'c4adac6a33044a05806868e2518e5f778c62e99d26a73c003fc6112ed3d589a3',
            'c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4'))
        self.observer=observer.NativeTaskObserver(self.a,self.reader)
        self.release=asyncio.Event()
    async def asyncTearDown(self):
        await fixture.NativeBorrowTests.asyncTearDown(self)
    def prepare(self,started=True):
        admitted=runtime.admit_session_input(self.state,epoch=self.identity.epoch,principal_id='owned',session_id='session',request_id='input',payload={'text':'offline ownership fixture'})
        if started:admitted=runtime.claim_session_input(self.state,epoch=self.identity.epoch,session_id='session')
        request=observer.TaskRequest(admitted['admission_id'],'session',self.identity.epoch,admitted['generation'],
            'RUNNING' if started else 'QUEUED',observer.RunRequestBinding('run-owned','scope-owned','key-owned','a'*64),
            observer.ResponseRequestBinding('idem:owned','b'*64))
        self.replay.reserve(request.run.scope,request.run.key,request.run.fingerprint,request.run.run_id,
            {'status':'running' if started else 'queued'},owner_pid=self.identity.owner_pid,owner_started=self.identity.owner_started)
        self.response.bind_request_key(request.response.key,request.response.fingerprint)
        self.response.bind_request_admission(request.response.key,request.admission_id)
        return request
    def register(self,request,coroutine=None):
        task=asyncio.create_task(coroutine if coroutine is not None else self.release.wait());self.tasks.append(task)
        a=self.a;rid=request.run.run_id
        a._active_run_tasks[rid]=task;a._background_tasks.add(task);a._run_admission_aliases[rid]=request.admission_id
        a._run_owners[rid]=request.run.scope;a._run_statuses[rid]={'run_id':rid,'session_id':request.session_id,'status':'queued' if request.phase=='QUEUED' else 'running'}
        self.observer.publish(task,request)
        return task
    def capture(self):
        original=[s._conn.total_changes for s in (self.state,self.replay,self.response)]
        trace=[]
        for s in (self.state,self.replay,self.response):s._conn.set_trace_callback(trace.append)
        before=fixture.AUDIT['connects'];fixture.AUDIT['watch']=True
        try:result=self.observer.capture()
        finally:
            fixture.AUDIT['watch']=False
            for s in (self.state,self.replay,self.response):s._conn.set_trace_callback(None)
        self.assertEqual(before,fixture.AUDIT['connects'])
        self.assertEqual(original,[s._conn.total_changes for s in (self.state,self.replay,self.response)])
        self.assertTrue(all(s.lstrip().startswith(('SELECT','PRAGMA')) for s in trace))
        public=result.public()
        for key in ('storageIntegrityVerifiedHere','nativeProducerHooksVerifiedHere','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):
            self.assertIs(public[key],False)
        OBSERVATIONS.append({'case':self._testMethodName,'boundTasks':len(result.live_work),'noSQLiteConnectOrWrite':True,'noServicePermission':True})
        return result
    async def test_native_idle_is_metadata_not_service_ready(self):
        r=self.capture();self.assertEqual(r.live_work,());self.assertEqual(r.public()['observedTasks'],0)
    async def test_live_task_and_os_start_identity_are_real(self):
        request=self.prepare();task=self.register(request);await asyncio.sleep(0)
        from gateway.status import get_process_start_time
        self.assertEqual(self.identity.owner_started,get_process_start_time(os.getpid()))
        r=self.capture();self.assertTrue(r.live_work[0].task_alive);self.assertFalse(task.done());self.assertFalse(task.cancelled())
    async def test_cancel_request_not_done_is_refused_without_cancelling_again(self):
        task=self.register(self.prepare());await asyncio.sleep(0);task.cancel()
        self.assertFalse(task.done());self.assertEqual(task.cancelling(),1)
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.assertEqual(task.cancelling(),1);self.alive()
    async def test_completed_task_left_in_native_registry_is_refused(self):
        task=self.register(self.prepare());self.release.set();await task
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.assertIs(self.a._active_run_tasks['run-owned'],task)
    async def test_failed_task_exception_not_consumed(self):
        async def fail():raise RuntimeError('owned_test_failure')
        task=self.register(self.prepare(),fail());await asyncio.sleep(0)
        self.assertTrue(task.done());before=task._log_traceback
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.assertEqual(task._log_traceback,before)
        await asyncio.gather(task,return_exceptions=True)
    async def test_native_worker_survives_cancelled_wrapper_and_refuses_idle(self):
        started=threading.Event();release=threading.Event()
        def worker():started.set();release.wait(5);return 'owned done'
        async def wrapper():return await fixture.api_runs._submit_api_worker(asyncio.get_running_loop(),worker)
        task=self.register(self.prepare(),wrapper())
        try:
            for _ in range(500):
                if started.is_set():break
                await asyncio.sleep(0.002)
            self.assertTrue(started.is_set());self.assertEqual(fixture.api_runs.api_worker_live_count(),1)
            task.cancel();await asyncio.gather(task,return_exceptions=True)
            self.assertTrue(task.cancelled());self.assertEqual(fixture.api_runs.api_worker_live_count(),1)
            with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
            self.alive();OBSERVATIONS.append({'case':self._testMethodName,'cancelledTaskDone':True,'actualNativeWorkerStillLive':True,'positiveProofRefused':True})
        finally:
            release.set()
            for _ in range(500):
                if fixture.api_runs.api_worker_live_count()==0:break
                await asyncio.sleep(0.002)
            self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
    async def test_future_is_not_accepted_as_task(self):
        request=self.prepare();future=asyncio.get_running_loop().create_future()
        try:
            with self.assertRaises(observer.TaskObservationRejected):self.observer.publish(future,request)
        finally:future.cancel()
    async def test_cross_thread_observation_refused(self):
        self.register(self.prepare())
        with self.assertRaises(observer.TaskObservationRejected):await asyncio.to_thread(self.observer.capture)
    async def test_changed_run_fingerprint_not_learned_from_candidate(self):
        self.register(self.prepare());self.capture()
        self.replay._conn.execute("UPDATE main.run_idempotency SET fingerprint=?",('c'*64,));self.replay._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.replay._conn.execute("UPDATE main.run_idempotency SET fingerprint=?",('a'*64,));self.replay._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
    async def test_changed_run_scope_not_accepted_when_run_id_matches(self):
        self.register(self.prepare());self.replay._conn.execute("UPDATE main.run_idempotency SET scope='other'");self.replay._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
    async def test_changed_run_key_not_accepted_when_run_id_matches(self):
        self.register(self.prepare());self.replay._conn.execute("UPDATE main.run_idempotency SET idempotency_key='other'");self.replay._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
    async def test_response_fingerprint_mismatch_refused(self):
        self.register(self.prepare());self.response._conn.execute('UPDATE main.response_keys SET fingerprint=?',('c'*64,));self.response._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
    async def test_unregistered_background_task_refused(self):
        self.register(self.prepare());extra=asyncio.create_task(self.release.wait());self.tasks.append(extra);self.a._background_tasks.add(extra)
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.assertFalse(extra.done())
    async def test_unregistered_native_run_task_refused(self):
        self.register(self.prepare());extra=asyncio.create_task(self.release.wait());self.tasks.append(extra);self.a._active_run_tasks['other']=extra;self.a._background_tasks.add(extra)
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
    async def test_replaced_task_same_run_id_refused(self):
        original=self.register(self.prepare());extra=asyncio.create_task(self.release.wait());self.tasks.append(extra)
        self.a._active_run_tasks['run-owned']=extra;self.a._background_tasks={extra}
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.assertFalse(original.done())
    async def test_pending_ingress_not_mislabelled_idle(self):
        self.a._pending_agent_requests=1
        with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        self.a._pending_agent_requests=0
    async def test_live_transaction_retained_and_fresh_capture_recovers(self):
        self.register(self.prepare());self.response._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(observer.TaskObservationUnavailable):self.observer.capture()
            self.assertTrue(self.response._conn.in_transaction)
        finally:self.response._conn.rollback()
        self.capture()
    async def test_native_mutex_not_stolen(self):
        self.register(self.prepare());self.replay._lock.acquire()
        try:
            with self.assertRaises(observer.TaskObservationUnavailable):self.observer.capture()
            self.assertTrue(self.replay._lock.locked())
        finally:self.replay._lock.release()
        self.capture()
    async def test_live_task_owns_phase_transition_not_external_caller(self):
        request=self.prepare(started=False);go=asyncio.Event();stage=asyncio.Event()
        async def producer():
            await go.wait();row=runtime.claim_session_input(self.state,epoch=self.identity.epoch,session_id='session')
            self.observer.advance('run-owned',phase='RUNNING',generation=row['generation'])
            self.a._run_statuses['run-owned']['status']='running';self.replay.update_status('run-owned',{'status':'running'})
            stage.set();await self.release.wait()
        task=self.register(request,producer());self.capture()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.advance('run-owned',phase='RUNNING',generation=1)
        go.set();await asyncio.wait_for(stage.wait(),2)
        r=self.capture();self.assertEqual(r.live_work[0].phase,'RUNNING');self.assertFalse(task.done())
    async def test_revision_change_inside_reader_is_not_positive_proof(self):
        self.register(self.prepare());triggered=[]
        def fault(sql):
            if not triggered and sql.startswith('SELECT'):
                triggered.append(True);self.a._run_owners['run-owned']='changed-during-read'
        self.state._conn.set_trace_callback(fault)
        try:
            with self.assertRaises(observer.TaskObservationRejected):self.observer.capture()
        finally:self.state._conn.set_trace_callback(None)
        self.assertTrue(triggered)
    async def test_drain_never_reopens_intake(self):
        self.register(self.prepare());self.observer.request_drain();r=self.capture();self.assertTrue(r.draining)
        self.observer.request_drain();self.assertEqual(r.revision,self.capture().revision)
    async def test_native_listener_still_refused(self):
        with self.assertRaisesRegex(fixture.BorrowedStoreRejected,'listener_not_qualified'):await self.a.connect()
        self.assertIsNone(self.a._site);self.assertIsNone(self.a._runner)

    async def completed(self,mode='success',remove_native=True):
        request=self.prepare();go=asyncio.Event()
        async def producer():
            await go.wait();self.observer.advance('run-owned',phase='SETTLING',generation=request.generation)
            runtime.settle_session_input(self.state,epoch=request.epoch,admission_id=request.admission_id,generation=request.generation,outcome='completed')
            self.replay.update_status('run-owned',{'status':'completed'})
            self.a._run_statuses['run-owned']['status']='completed'
            if mode!='partial':self.response._settle_terminal_admissions();self.response._conn.commit()
            if mode=='failed':raise RuntimeError('late_fixture_failure')
        task=self.register(request,producer());task.add_done_callback(self.a._background_tasks.discard)
        go.set();await asyncio.gather(task,return_exceptions=True);await asyncio.sleep(0)
        if remove_native:fixture.api_runs._retire_live_run(self.a,'run-owned')
        return task
    def retire(self):
        stores=(self.state,self.replay,self.response);before=[s._conn.total_changes for s in stores]
        r=self.observer.retire_completed('run-owned')
        self.assertEqual(before,[s._conn.total_changes for s in stores]);self.alive()
        self.assertFalse(r['nativeTaskRemovedHere']);self.assertFalse(r['databaseWritesPerformed']);self.assertFalse(r['storeReleaseAuthorized'])
        return r
    async def test_successful_native_retirement_returns_to_empty_observation(self):
        task=await self.completed();self.assertTrue(task.done());self.assertFalse(task.cancelled())
        r=self.retire();self.assertEqual(r['state'],'TASK_OBSERVATION_RETIRED');self.assertEqual(self.capture().live_work,())
        OBSERVATIONS.append({'case':self._testMethodName,'realTaskFinishedSuccessfully':True,'nativeRetireFunctionUsed':True,'allThreeCommitted':True,'observerOnlyEntryRemoved':True,'storesRemainOpen':True})
    async def test_retirement_refuses_partial_response_settlement(self):
        await self.completed(mode='partial')
        with self.assertRaises(observer.TaskObservationRejected):self.observer.retire_completed('run-owned')
        self.assertIn('run-owned',self.observer._entries);self.alive()
    async def test_retirement_refuses_failed_task_even_when_rows_terminal(self):
        await self.completed(mode='failed')
        with self.assertRaises(observer.TaskObservationRejected):self.observer.retire_completed('run-owned')
        self.assertIn('run-owned',self.observer._entries);self.alive()
    async def test_retirement_does_not_remove_native_registry_itself(self):
        task=await self.completed(remove_native=False)
        with self.assertRaises(observer.TaskObservationRejected):self.observer.retire_completed('run-owned')
        self.assertIs(self.a._active_run_tasks['run-owned'],task);self.alive()
    async def test_retirement_unavailable_transaction_is_retryable_without_rollback(self):
        await self.completed();self.response._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(observer.TaskObservationUnavailable):self.observer.retire_completed('run-owned')
            self.assertTrue(self.response._conn.in_transaction);self.assertIn('run-owned',self.observer._entries)
        finally:self.response._conn.rollback()
        self.retire();self.assertEqual(self.capture().live_work,())
    async def test_retirement_rechecks_fingerprint_after_task_success(self):
        await self.completed();self.replay._conn.execute('UPDATE main.run_idempotency SET fingerprint=?',('d'*64,));self.replay._conn.commit()
        with self.assertRaises(observer.TaskObservationRejected):self.observer.retire_completed('run-owned')
        self.assertIn('run-owned',self.observer._entries);self.alive()

def main():
    global runtime
    parser=argparse.ArgumentParser();parser.add_argument('--native',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    boot=tempfile.TemporaryDirectory(prefix='alaz-c116a4-import-');os.environ.update(HERMES_HOME=boot.name,HOME=boot.name,USERPROFILE=boot.name,LOCALAPPDATA=boot.name,APPDATA=boot.name)
    sys.path.insert(0,str(native))
    def audit(event,args):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
            if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(args[1],tuple) and args[1][0] in ('127.0.0.1','::1'):
                fixture.AUDIT['frameworkSocketEvents']+=1;return
            fixture.AUDIT['network']+=1;raise PermissionError('c116a4_offline')
        if fixture.AUDIT['watch'] and event=='sqlite3.connect':fixture.AUDIT['connects']+=1;raise AssertionError('unexpected_SQLite_open')
    sys.addaudithook(audit)
    import urllib3.util.connection
    from gateway.platforms.api_server import APIServerAdapter
    from gateway.config import PlatformConfig
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
    from gateway import runtime_ownership as ownership
    from gateway.platforms import api_server_runs
    import hermes_state_runtime as runtime
    for name,value in locals().copy().items():
        if name in ('APIServerAdapter','PlatformConfig','SessionDB','RunIdempotencyStore','ResponseStore','BorrowedAPIStores','BorrowedStoreRejected','ownership'):setattr(fixture,name,value)
    fixture.api_runs=api_server_runs
    import_network=fixture.AUDIT['network']
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativeOwnerCases)
    with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    imports={}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    boot.cleanup()
    sources={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('packages/claw-hermes/gateway_work_observer.py','packages/claw-hermes/gateway_work_health.py','packages/claw-hermes/gateway_work_health_reader.py','scripts/qa/c116a4_native_owner.py','scripts/qa/b112x9_adapter_probe.py')}
    report={'result':'PASS_NATIVE_ADAPTER_TASK_OBSERVATION_ONLY' if r.wasSuccessful() and fixture.AUDIT['network']==import_network else 'FAIL','total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.errors+r.failures})-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'sources':sources,'nativeImports':imports,'observations':OBSERVATIONS,'newNetworkAttemptsInCases':fixture.AUDIT['network']-import_network,'deniedImportProbes':import_network,'nativeAdapterStoresAndTasksReal':True,'osProcessStartReal':True,'actualNativeExecutorThreadTested':True,'producerRegistrationIsExplicitFixture':True,'nativeIngressHooksIntegrated':False,'serviceReadinessProven':False,'fullIsolationTested':False,'nativeListenerStarted':False,'providerCalls':0,'rootWslAction':False,'profileOwnershipReleased':not ownership.process_ownership.homes,'bootstrapRemoved':not Path(boot.name).exists()}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sources','nativeImports','observations')}),flush=True)
    if report['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-18000:],flush=True)
    return 0 if report['result'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
