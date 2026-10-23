"""Real native worker lifetime + decorated ingress with bounded dummy computation.
No manual source event, Task map, worker-ticket or counter publication by tests.
Original H117 20 native tests are inherited unchanged as compatibility coverage.
"""
import argparse,asyncio,contextlib,hashlib,json,os,sys,tempfile,threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import h117b_native_producer as base
from gateway_native_run_provenance import NativeRunProvenance
from gateway_native_worker_owner import NativeWorkerObserver,WorkerOwnerRejected,WorkerOwnerUnavailable
fixture=base.fixture
RESULTS=base.RESULTS
WORKER_PROOFS=[]

class WorkerCases(base.NativeProducerTests):
    def bind_worker(self):
        self.provenance=NativeRunProvenance(self.observer)
        self.work=NativeWorkerObserver(self.provenance)
        return self.work
    def capture_worker(self):
        before=tuple(c.total_changes for c in (self.state._conn,self.replay._conn,self.response._conn))
        fixture.AUDIT['watch']=True
        try:result=self.work.capture()
        finally:fixture.AUDIT['watch']=False
        self.assertEqual(before,tuple(c.total_changes for c in (self.state._conn,self.replay._conn,self.response._conn)))
        WORKER_PROOFS.append({'case':self._testMethodName,'public':result.public(),
            'states':[w.state for w in result.workers],
            'carrierDone':[w.carrier_done for w in result.workers],
            'carrierCancelled':[w.carrier_cancelled for w in result.workers],
            'nativeWorkerCount':result.native_worker_count,'policyWrites':0})
        return result
    async def until(self,predicate):
        end=self.loop.time()+5
        while not predicate():
            if self.loop.time()>end:raise AssertionError('owned_condition_not_reached')
            await asyncio.sleep(0)
    async def run_blocked(self):
        self.bind_worker();self.worker_release.clear();response=await self.post()
        self.assertEqual(response.status,202)
        await asyncio.wait_for(self.worker_started.wait(),5)
        return response
    async def test_worker_real_thread_bound_to_exact_immutable_ingress(self):
        response=await self.run_blocked();r=self.capture_worker();self.assertEqual(len(r.workers),1)
        row=r.workers[0];rid=json.loads(response.body)['run_id']
        self.assertEqual(row.binding.run_id,rid);self.assertIs(row.binding,self.provenance._active[rid][0])
        self.assertEqual(row.state,'RUNNING');self.assertNotEqual(row.thread_id,threading.get_ident())
        self.assertGreater(row.native_thread_id,0);self.assertLessEqual(row.submitted_ns,row.started_ns)
        self.assertIsNone(row.finished_ns);self.assertFalse(row.carrier_done)
        with self.assertRaises(FrozenInstanceError):row.state='RETURNED'
        self.assertFalse(r.public()['canonicalExecutorVerified'])
        await self.finish();await self.until(lambda:not self.provenance.channel._workers._records)
        self.assertEqual(self.capture_worker().workers,())
    async def test_worker_survives_cancelled_carrier_without_task_retention(self):
        await self.run_blocked();task=self.tasks[0];task.cancel()
        await asyncio.gather(task,return_exceptions=True);await asyncio.sleep(0)
        r=self.capture_worker();self.assertEqual(r.native_worker_count,1)
        self.assertEqual(r.public()['workersOutlivingCarrier'],1)
        self.assertEqual(r.workers[0].state,'RUNNING');self.assertTrue(r.workers[0].carrier_cancelled)
        self.assertTrue(r.workers[0].carrier_released)
        self.assertTrue(all(v.task is None for v in self.provenance.channel._workers._records.values()))
        self.worker_release.set();await self.until(lambda:not self.provenance.channel._workers._records)
        self.assertEqual(self.capture_worker().native_worker_count,0)
    async def test_worker_queued_cancellation_does_not_leak_count_or_call_function(self):
        self.bind_worker();self.loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        r=await self.post();gate=threading.Event();entered=asyncio.Event()
        def blocker():
            self.loop.call_soon_threadsafe(entered.set)
            if not gate.wait(8):raise AssertionError('blocker_not_released')
        blocking=self.loop.run_in_executor(None,blocker)
        try:
            await asyncio.wait_for(entered.wait(),5)
            await self.until(lambda:fixture.api_runs.api_worker_live_count()==1)
            snap=self.capture_worker();self.assertEqual(snap.workers[0].state,'SUBMITTED')
            self.assertIsNone(snap.workers[0].thread_id)
            self.tasks[0].cancel();await asyncio.gather(*self.tasks,return_exceptions=True);await asyncio.sleep(0)
            self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
            self.assertEqual(self.capture_worker().workers,());self.assertEqual(self.dummy_calls,0)
        finally:gate.set();await asyncio.wait_for(blocking,5)
        await asyncio.sleep(0);self.assertEqual(self.dummy_calls,0);self.assertEqual(fixture.api_runs.api_worker_live_count(),0)
    async def test_worker_two_requests_do_not_share_identity_or_thread(self):
        self.bind_worker();self.a._max_concurrent_runs=4;self.worker_release.clear()
        a=await self.post({'input':'first'},key='first');b=await self.post({'input':'second'},key='second')
        self.assertEqual((a.status,b.status),(202,202));await self.until(lambda:self.dummy_calls==2)
        r=self.capture_worker();self.assertEqual(len(r.workers),2);self.assertEqual(r.native_worker_count,2)
        self.assertEqual({x.binding.key for x in r.workers},{'first','second'})
        self.assertEqual(len({x.submission for x in r.workers}),2);self.assertEqual(len({x.thread_id for x in r.workers}),2)
        await self.finish();self.assertEqual(self.capture_worker().workers,())
    async def test_worker_replay_never_adds_submission(self):
        await self.run_blocked();r=self.capture_worker();again=await self.post()
        self.assertTrue(json.loads(again.body)['replayed']);after=self.capture_worker()
        self.assertEqual([(x.binding,x.submission) for x in r.workers],[(x.binding,x.submission) for x in after.workers])
        self.assertEqual(self.dummy_calls,1);await self.finish()
    async def test_worker_source_binding_not_relearned_after_database_change(self):
        await self.run_blocked();r=self.capture_worker();original=r.workers[0].binding.fingerprint
        self.replay._conn.execute('UPDATE main.run_idempotency SET fingerprint=?',('f'*64,));self.replay._conn.commit()
        self.assertEqual(self.capture_worker().workers[0].binding.fingerprint,original)
        self.assertFalse(self.capture_worker().public()['storageIntegrityVerified']);await self.finish()
    async def test_worker_capture_contention_is_transient_not_false_idle(self):
        await self.run_blocked();book=self.provenance.channel._workers;book._lock.acquire()
        try:
            with self.assertRaises(WorkerOwnerUnavailable):self.work.capture()
        finally:book._lock.release()
        self.assertEqual(self.capture_worker().workers[0].state,'RUNNING');await self.finish()
    async def test_worker_foreign_thread_capture_is_rejected(self):
        await self.run_blocked()
        with self.assertRaises(WorkerOwnerRejected):await asyncio.to_thread(self.work.capture)
        self.assertEqual(fixture.api_runs.api_worker_live_count(),1);await self.finish()
    async def test_worker_provenance_gap_cannot_claim_no_workers(self):
        self.bind_worker()
        def fail(event):raise RuntimeError('private_observer_failure')
        self.provenance.channel._sink=fail
        await self.post();await self.finish()
        with self.assertRaises(WorkerOwnerRejected):self.work.capture()
        self.assertEqual(self.dummy_calls,1)
    async def test_worker_replaced_book_is_not_adopted(self):
        await self.run_blocked();book=self.provenance.channel._workers
        self.provenance.channel._workers=object()
        try:
            with self.assertRaises(WorkerOwnerRejected):self.work.capture()
        finally:self.provenance.channel._workers=book
        await self.finish()
    async def test_worker_json_cannot_inject_lifetime(self):
        self.bind_worker();self.worker_release.clear()
        await self.post({'input':'owned','_workers':{'state':'RETURNED'},'thread_id':1,'worker_ticket':999})
        await asyncio.wait_for(self.worker_started.wait(),5);r=self.capture_worker()
        self.assertEqual(r.workers[0].state,'RUNNING');self.assertNotEqual(r.workers[0].native_thread_id,1)
        await self.finish()
    async def test_worker_no_payload_or_identity_in_public_snapshot(self):
        await self.run_blocked();r=self.capture_worker();text=json.dumps(r.public())
        for value in (r.workers[0].binding.run_id,r.workers[0].binding.key,r.workers[0].binding.fingerprint):self.assertNotIn(value,text)
        for key in ('allAgentWorkObserved','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertFalse(r.public()[key])
        await self.finish()
    async def test_worker_submit_failure_does_not_leave_counter_or_record(self):
        self.bind_worker();response=await self.post()
        with patch.object(self.loop,'run_in_executor',side_effect=RuntimeError('owned_submit_failure')):
            await self.finish()
        rid=json.loads(response.body)['run_id']
        self.assertEqual(self.a._run_statuses[rid]['status'],'failed')
        self.assertEqual(fixture.api_runs.api_worker_live_count(),0);self.assertEqual(self.capture_worker().workers,())
        self.assertEqual(self.dummy_calls,0)
    async def test_worker_old_strict_task_observer_not_relaxed(self):
        await self.run_blocked()
        with self.assertRaises(base.TaskObservationRejected):self.observer.capture()
        self.assertEqual(fixture.api_runs.api_worker_live_count(),1);await self.finish()

def main():
    global api,native_hooks,runtime
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    n=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    boot=tempfile.TemporaryDirectory(prefix='alaz-e118w2-import-')
    os.environ.update(HERMES_HOME=boot.name,HOME=boot.name,USERPROFILE=boot.name,APPDATA=boot.name,LOCALAPPDATA=boot.name)
    sys.path.insert(0,str(n))
    def audit(event,fields):
        if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
            if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(fields[1],tuple) and fields[1][0] in ('127.0.0.1','::1'):
                fixture.AUDIT['frameworkSocketEvents']+=1;return
            fixture.AUDIT['network']+=1;raise PermissionError('h117b_offline')
        if event=='subprocess.Popen':raise PermissionError('h117b_no_subprocess')
        if fixture.AUDIT['watch'] and event=='sqlite3.connect':fixture.AUDIT['connects']+=1;raise AssertionError('unexpected_sqlite_open')
    sys.addaudithook(audit)
    import urllib3.util.connection
    import gateway.platforms.api_server as api
    from gateway.config import PlatformConfig
    from hermes_state import SessionDB
    from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
    from gateway.platforms.api_server_response_store import ResponseStore
    from gateway.platforms.api_server_borrowed import BorrowedAPIStores,BorrowedStoreRejected
    from gateway import runtime_ownership as ownership
    from gateway.platforms import api_server_runs,api_server_run_observation as native_hooks
    import hermes_state_runtime as runtime
    fixture.APIServerAdapter=api.APIServerAdapter;fixture.api_runs=api_server_runs
    for name in ('PlatformConfig','SessionDB','RunIdempotencyStore','ResponseStore','BorrowedAPIStores','BorrowedStoreRejected','ownership'):setattr(fixture,name,locals()[name])
    base.api,base.native_hooks,base.runtime=api,native_hooks,runtime
    before_network=fixture.AUDIT['network']
    local=('packages/claw-hermes/gateway_native_run_provenance.py','scripts/qa/h117b_native_producer.py','packages/claw-hermes/gateway_work_observer.py','scripts/qa/b112x9_adapter_probe.py','packages/claw-hermes/gateway_native_worker_owner.py','scripts/qa/e118w2_native_workers.py')
    sources={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in local}
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(WorkerCases)
    with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    imports={}
    for m in tuple(sys.modules.values()):
        f=getattr(m,'__file__',None)
        if f:
            path=Path(f).resolve()
            if path.is_relative_to(n) and path.suffix=='.py':imports[path.relative_to(n).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    stable=all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h for name,h in sources.items())
    boot.cleanup();report={'result':'PASS_NATIVE_WORKER_LIFETIME_BINDINGS' if r.wasSuccessful() and stable and fixture.AUDIT['network']==before_network else 'FAIL',
        'total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.errors+r.failures})-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),
        'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures], 'sources':sources,'nativeImports':imports,'sourcesUnchanged':stable,'cases':RESULTS,'workerProofs':WORKER_PROOFS,
        'realExecutorThreadsObserved':True,'workerStateManuallyPublished':False,'inheritedProducerCompatibilityMethods':20,
        'nativeEntryAndTaskLifecycleReal':True,'nativeTaskMapsWrittenByFixture':False,'agentExecutionDoubled':True,'authorityAndBotDeliveryBoundariesDoubled':True,
        'authenticationMiddlewareTested':False,'nativeAuthDecoratorTested':True,'httpListenerStarted':False,'canonicalExecutorHealthProven':False,'fullIsolationTested':False,'rootWslAction':False,
        'providerCalls':0,'newNetworkAttempts':fixture.AUDIT['network']-before_network,'deniedImportProbes':before_network,
        'profileReleased':not ownership.process_ownership.homes,'bootstrapRemoved':not Path(boot.name).exists()}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','cases','sources','workerProofs')}),flush=True)
    if report['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-20000:],flush=True)
    return 0 if report['result'].startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main())
