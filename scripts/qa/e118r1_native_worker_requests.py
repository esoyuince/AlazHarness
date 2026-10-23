"""Independent actual request-to-executor tests; dummy compute only, no manual maps.

No worker record is inserted or advanced by these tests. Real native entry, Task,
worker submission/thread/finally and carrier callbacks generate all observations.
Deliberate callback/lock/source faults are labelled; no live HTTP/model is started.
"""
from pathlib import Path
import argparse,asyncio,concurrent.futures,hashlib,json,os,sys,tempfile,threading,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import p117n1_native_hook_audit as previous
fixture=previous.fixture
from gateway_native_worker_owner import NativeWorkerObserver,WorkerOwnerRejected,WorkerOwnerUnavailable
from gateway_work_observer import NativeTaskObserver
from gateway_native_run_provenance import NativeRunProvenance
from gateway_work_health_reader import NativeWorkReader
from gateway_work_health import RuntimeIdentity
runtime=None
RECORDS=[]
class Compute:
    session_id='';provider='fixture';model='fixture'
    def __init__(self,case):self.case=case
    def run_conversation(self,**kwargs):
        c=self.case;c.calls+=1
        c.loop.call_soon_threadsafe(c.entered_future.set_result,(threading.get_ident(),threading.get_native_id()))
        if not c.release.wait(15):raise RuntimeError('owned_compute_release_timeout')
        if c.fail_compute:raise RuntimeError('owned_expected_failure')
        return {'final_response':'owned offline worker output'}
class WorkerRequestCases(unittest.IsolatedAsyncioTestCase):
    loop_factory=staticmethod(fixture.NativeBorrowTests.loop_factory)
    build=fixture.NativeBorrowTests.build
    submit=previous.ProducerCases.submit
    def setUp(self):fixture.NativeBorrowTests.setUp(self)
    async def asyncSetUp(self):
        self.a=self.build();self.calls=0;self.fail_compute=False;self.loop=asyncio.get_running_loop()
        self.release=threading.Event();self.entered_future=self.loop.create_future();self.extras=[]
        self.agent=patch.object(self.a,'_create_agent',side_effect=lambda **kw:Compute(self));self.agent.start()
        epoch=runtime.begin_runtime_epoch(self.state,instance_id='owned-e118-independent')
        store=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        identity=RuntimeIdentity(store,epoch,'owned-e118-independent',os.getpid(),self.a._run_owner_started)
        reader=NativeWorkReader(self.state,self.replay,self.response,identity,schema_hashes=(
            'f4889e8d91c8b57ee828ac7a1ead9ac880db48f9c21500e3800d4b48b759e8c7',
            'c4adac6a33044a05806868e2518e5f778c62e99d26a73c003fc6112ed3d589a3',
            'c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4'))
        self.observer=NativeTaskObserver(self.a,reader);self.provenance=NativeRunProvenance(self.observer)
        self.workers=NativeWorkerObserver(self.provenance)
    async def asyncTearDown(self):
        self.release.set()
        for event,f in self.extras:event.set()
        if self.tasks:await asyncio.gather(*self.tasks,return_exceptions=True)
        if self.extras:await asyncio.gather(*(f for _,f in self.extras),return_exceptions=True)
        await self.loop.shutdown_default_executor(timeout=15);await self.barrier()
        self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
        self.agent.stop();await fixture.NativeBorrowTests.asyncTearDown(self)
    async def barrier(self):
        f=self.loop.create_future();self.loop.call_soon(f.set_result,None);await f
    async def complete(self,t):
        self.release.set();await asyncio.wait_for(asyncio.shield(t),15);await self.barrier()
    def captured(self):
        before=tuple(s._conn.total_changes for s in (self.state,self.replay,self.response))
        fixture.AUDIT['watch']=True
        try:s=self.workers.capture()
        finally:fixture.AUDIT['watch']=False
        self.assertEqual(before,tuple(s._conn.total_changes for s in (self.state,self.replay,self.response)))
        public=s.public()
        for k in ('canonicalExecutorVerified','allAgentWorkObserved','storageIntegrityVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):
            self.assertFalse(public[k])
        RECORDS.append({'case':self._testMethodName,'public':public,'workerStates':[v.state for v in s.workers],
                        'nativeRequestAndWorkerPublicationAutomatic':True,'newConnectionsAndRowWritesDuringCapture':False})
        return s
    async def running(self):
        r,v,t,q=await self.submit();self.assertEqual(r.status,202)
        ids=await asyncio.wait_for(asyncio.shield(self.entered_future),15)
        return r,v,t,q,ids
    async def test_actual_worker_ids_and_immutable_ingress_match(self):
        r,v,t,q,ids=await self.running();s=self.captured();self.assertEqual(len(s.workers),1)
        worker=s.workers[0];binding=self.provenance.binding_for(v['run_id'],t).native_binding
        self.assertIs(worker.binding,binding);self.assertEqual((worker.thread_id,worker.native_thread_id),ids)
        self.assertEqual(worker.state,'RUNNING');self.assertEqual(worker.owner_pid,os.getpid())
        expected=hashlib.sha256(json.dumps({'body':q.body,'gateway_session_key':''},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(worker.binding.fingerprint,expected);self.assertEqual(worker.binding.key,'owned-key')
        self.assertGreaterEqual(worker.started_ns,worker.submitted_ns);self.assertIsNone(worker.finished_ns)
        await self.complete(t);self.assertEqual(self.captured().workers,())
    async def test_cancelled_carrier_record_survives_until_actual_worker_exit(self):
        _,v,t,_,_=await self.running();t.cancel();await asyncio.gather(t,return_exceptions=True);await self.barrier()
        self.assertEqual(self.provenance.status()['activeProvenanceRecords'],0)
        s=self.captured();self.assertEqual(len(s.workers),1);record=s.workers[0]
        self.assertEqual(record.state,'RUNNING');self.assertTrue(record.carrier_done);self.assertTrue(record.carrier_cancelled);self.assertTrue(record.carrier_released)
        self.assertIsNone(record.finished_ns);self.assertEqual(s.public()['workersOutlivingCarrier'],1)
        self.assertEqual(s.native_worker_count,1)
        self.release.set();await self.loop.shutdown_default_executor(timeout=15);await self.barrier()
        self.assertEqual(self.captured().workers,());self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
    async def test_queued_carrier_cancel_never_runs_and_leaves_no_owner(self):
        self.loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=1))
        signal=self.loop.create_future();hold=threading.Event()
        def blocker():
            self.loop.call_soon_threadsafe(signal.set_result,None)
            if not hold.wait(15):raise RuntimeError('owned_queue_release_timeout')
        f=self.loop.run_in_executor(None,blocker);self.extras.append((hold,f));await asyncio.wait_for(signal,3)
        r,v,t,q=await self.submit();await self.barrier()
        s=self.captured();self.assertEqual([v.state for v in s.workers],['SUBMITTED']);self.assertEqual(self.calls,0)
        t.cancel();await asyncio.gather(t,return_exceptions=True);await self.barrier();await self.barrier()
        self.assertEqual(fixture.api_runs.api_worker_live_count(),0);self.assertEqual(self.captured().workers,())
        hold.set();await f;self.assertEqual(self.calls,0)
    async def test_replay_does_not_create_a_second_worker_binding(self):
        _,v,t,_,_=await self.running();before=self.captured()
        r2,v2,t2,q2=await self.submit();self.assertEqual(v2['run_id'],v['run_id']);self.assertIs(t2,t)
        after=self.captured();self.assertEqual(before.revision,after.revision);self.assertEqual(before.workers,after.workers);self.assertEqual(self.calls,1)
        await self.complete(t)
    async def test_untracked_other_ingress_is_visible_not_counted_as_complete(self):
        _,v,t,_,_=await self.running();ready=self.loop.create_future();hold=threading.Event()
        def other():
            self.loop.call_soon_threadsafe(ready.set_result,None)
            if not hold.wait(15):raise RuntimeError('owned_other_release_timeout')
        f=fixture.api_runs._submit_api_worker(self.loop,other);self.extras.append((hold,f));await asyncio.wait_for(ready,3)
        s=self.captured();self.assertEqual(len(s.workers),1);self.assertEqual(s.native_worker_count,2)
        self.assertEqual(s.public()['unattributedNativeWorkers'],1);self.assertFalse(s.public()['allAgentWorkObserved'])
        hold.set();await f;await self.complete(t)
    async def test_worker_book_lock_contention_is_retryable_observation_only(self):
        _,_,t,_,_=await self.running();lock=self.provenance.channel._workers._lock;self.assertTrue(lock.acquire(blocking=False))
        try:
            with self.assertRaises(WorkerOwnerUnavailable):self.workers.capture()
        finally:lock.release()
        self.assertFalse(self.workers._fault);self.assertEqual(self.captured().public()['enteredNotYetExited'],1)
        await self.complete(t)
    async def test_process_identity_change_stays_rejected_after_restore(self):
        _,_,t,_,_=await self.running();old=self.a._run_owner_started;self.a._run_owner_started=old+1
        try:
            with self.assertRaises(WorkerOwnerRejected):self.workers.capture()
        finally:self.a._run_owner_started=old
        with self.assertRaises(WorkerOwnerRejected):self.workers.capture()
        await self.complete(t)
    async def test_observation_failure_does_not_cancel_business_work(self):
        book=self.provenance.channel._workers
        with patch.object(book,'transition',side_effect=RuntimeError('explicit observation fault')):
            r,v,t,q=await self.submit();await self.complete(t)
        self.assertEqual(r.status,202);self.assertEqual(self.calls,1);self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed')
        self.assertFalse(t.cancelled())
        with self.assertRaises(WorkerOwnerRejected):self.workers.capture()
    async def test_failed_compute_does_not_fabricate_worker_success(self):
        self.fail_compute=True;_,v,t,_,_=await self.running();self.assertEqual(self.captured().workers[0].state,'RUNNING')
        await self.complete(t);self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'failed')
        self.assertEqual(self.captured().workers,());self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
    async def test_capture_never_consumes_payload_or_claims_admission(self):
        _,_,t,_,_=await self.running();s=self.captured();payload=json.dumps(s.public())
        self.assertNotIn('owned-key',payload);self.assertNotIn('offline input',payload)
        self.assertFalse(s.public()['runtimeAdmissionAuthorized']);self.assertFalse(s.public()['storeReleaseAuthorized'])
        await self.complete(t)
def main():
    global runtime
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-e118-request-') as home:
        os.environ.update(HERMES_HOME=home,HOME=home,USERPROFILE=home,APPDATA=home,LOCALAPPDATA=home);sys.path.insert(0,str(native))
        def audit(event,args):
            if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
                if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(args[1],tuple) and args[1][0] in ('127.0.0.1','::1'):
                    fixture.AUDIT['frameworkSocketEvents']+=1;return
                fixture.AUDIT['network']+=1;raise PermissionError('independent_worker_offline')
            if event in ('subprocess.Popen','os.system'):raise PermissionError('no_child_program')
            if fixture.AUDIT['watch'] and event=='sqlite3.connect':raise AssertionError('capture_reopened_connection')
            if fixture.AUDIT['watch'] and event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and str(args[0]).endswith(('.db','.db-journal','.db-wal','.db-shm')):raise AssertionError('capture_raw_db_open')
        sys.addaudithook(audit)
        import urllib3.util.connection
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.config import PlatformConfig
        from hermes_state import SessionDB
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        from gateway.platforms.api_server_response_store import ResponseStore
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
        from gateway import runtime_ownership as ownership
        from gateway.platforms import api_server_runs,api_server_run_observation
        import hermes_state_runtime as runtime
        for name,value in locals().copy().items():
            if name in ('APIServerAdapter','PlatformConfig','SessionDB','RunIdempotencyStore','ResponseStore','BorrowedAPIStores','BorrowedStoreRejected','ownership'):setattr(fixture,name,value)
        fixture.api_runs=api_server_runs;previous.runtime=runtime;previous.hooks=api_server_run_observation;denied=fixture.AUDIT['network']
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkerRequestCases))
        imports={}
        for module in tuple(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if file:
                path=Path(file).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        names=('packages/claw-hermes/gateway_native_worker_owner.py','packages/claw-hermes/gateway_native_run_provenance.py','packages/claw-hermes/gateway_work_observer.py','scripts/qa/e118r1_native_worker_requests.py','scripts/qa/p117n1_native_hook_audit.py','scripts/qa/b112x9_adapter_probe.py')
        report={'result':'PASS_INDEPENDENT_NATIVE_WORKER_REQUESTS' if r.wasSuccessful() and fixture.AUDIT['network']==denied else 'FAIL',
                'total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.errors+r.failures})-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),
                'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
                'nativeImports':imports,'sources':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},'observations':RECORDS,
                'realNativeHandlerTaskWorkerAndCounter':True,'manualWorkerPublication':False,'dummyModelComputation':True,
                'canonicalSessionAuthorityVerified':False,'serviceHealthAccepted':False,'httpListenerStarted':False,'kernelIsolationTested':False,
                'providerCalls':0,'rootWslAction':False,'newNetworkAttempts':fixture.AUDIT['network']-denied,'profileOwnershipReleased':not ownership.process_ownership.homes}
    report['bootstrapRemoved']=not Path(home).exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','sources','observations')}))
    if report['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-16000:])
    return 0 if report['result'].startswith('PASS') and report['profileOwnershipReleased'] and report['bootstrapRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
