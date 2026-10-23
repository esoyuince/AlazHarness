"""Real native data and real Tasks through normal retirement; ingress hooks are QA.

No native route/model/HTTP invocation and no Linux profile/mount acceptance.
"""
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import b112x9_adapter_probe as fixture
import gateway_work_observer as obs
import gateway_work_health as policy
from gateway_work_health_reader import NativeWorkReader
runtime=None
RECORDS=[]

class NativeRetirement(unittest.IsolatedAsyncioTestCase):
    loop_factory=staticmethod(fixture.NativeBorrowTests.loop_factory)
    build=fixture.NativeBorrowTests.build
    alive=fixture.NativeBorrowTests.alive
    def setUp(self):fixture.NativeBorrowTests.setUp(self)
    async def asyncSetUp(self):
        self.a=self.build();self.epoch=runtime.begin_runtime_epoch(self.state,instance_id='c116a-owned')
        self.state.create_session('session','api')
        sid=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        self.identity=policy.RuntimeIdentity(sid,self.epoch,'c116a-owned',os.getpid(),self.a._run_owner_started)
        self.reader=NativeWorkReader(self.state,self.replay,self.response,self.identity,schema_hashes=(
            'f4889e8d91c8b57ee828ac7a1ead9ac880db48f9c21500e3800d4b48b759e8c7',
            'c4adac6a33044a05806868e2518e5f778c62e99d26a73c003fc6112ed3d589a3',
            'c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4'))
        self.observer=obs.NativeTaskObserver(self.a,self.reader)
        self.go=asyncio.Event();self.running=asyncio.Event();self.settle=asyncio.Event();self.settling=asyncio.Event();self.finish=asyncio.Event()
    async def asyncTearDown(self):await fixture.NativeBorrowTests.asyncTearDown(self)
    def watch(self,fn):
        before=tuple(s._conn.total_changes for s in (self.state,self.replay,self.response))
        queries=[]
        for s in (self.state,self.replay,self.response):s._conn.set_trace_callback(queries.append)
        fixture.AUDIT['watch']=True
        try:r=fn()
        finally:
            fixture.AUDIT['watch']=False
            for s in (self.state,self.replay,self.response):s._conn.set_trace_callback(None)
        self.assertEqual(before,tuple(s._conn.total_changes for s in (self.state,self.replay,self.response)))
        self.assertTrue(all(s.lstrip().startswith(('SELECT','PRAGMA')) for s in queries));self.alive()
        return r
    def launch(self,*,commit_response=True,fail_after=False):
        # Expected request identity is fixed BEFORE any replay/response candidate is written.
        body={'input':'offline trusted producer fixture','session_id':'session'}
        fp=hashlib.sha256(json.dumps({'body':body,'gateway_session_key':''},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        rp=hashlib.sha256(b'independent-response-fixture').hexdigest()
        a=runtime.admit_session_input(self.state,epoch=self.epoch,principal_id='owned',session_id='session',request_id='request',payload={'text':body['input']})
        request=obs.TaskRequest(a['admission_id'],'session',self.epoch,None,'QUEUED',
            obs.RunRequestBinding('run-retire','scope','key',fp),obs.ResponseRequestBinding('response-retire',rp))
        self.replay.reserve('scope','key',fp,'run-retire',{'status':'queued'},owner_pid=self.identity.owner_pid,owner_started=self.identity.owner_started)
        self.response.bind_request_key(request.response.key,rp);self.response.bind_request_admission(request.response.key,a['admission_id'])
        self.a._run_idempotency_ids.add(request.run.run_id)
        self.a._run_statuses[request.run.run_id]={'run_id':request.run.run_id,'session_id':'session','status':'queued'}
        async def producer():
            await self.go.wait()
            row=runtime.claim_session_input(self.state,epoch=self.epoch,session_id='session')
            self.observer.advance(request.run.run_id,phase='RUNNING',generation=row['generation'])
            self.a._set_run_status(request.run.run_id,'running',session_id='session');self.running.set()
            await self.settle.wait()
            self.observer.advance(request.run.run_id,phase='SETTLING',generation=row['generation'])
            runtime.settle_session_input(self.state,epoch=self.epoch,admission_id=request.admission_id,generation=row['generation'],outcome='completed')
            self.settling.set();await self.finish.wait()
            self.a._set_run_status(request.run.run_id,'completed',session_id='session')
            if commit_response:
                self.response._settle_terminal_admissions();self.response._conn.commit()
            if fail_after:raise RuntimeError('explicit task failure fixture')
            return 'owner finished'
        task=asyncio.create_task(producer());self.tasks.append(task)
        self.a._active_run_tasks[request.run.run_id]=task;self.a._background_tasks.add(task)
        self.a._run_admission_aliases[request.run.run_id]=request.admission_id;self.a._run_owners[request.run.run_id]=request.run.scope
        self.observer.publish(task,request)
        return task,request
    async def complete(self,*,commit_response=True,fail_after=False):
        task,request=self.launch(commit_response=commit_response,fail_after=fail_after)
        self.go.set();await asyncio.wait_for(self.running.wait(),2);self.settle.set();await asyncio.wait_for(self.settling.wait(),2)
        self.finish.set();await asyncio.gather(task,return_exceptions=True)
        fixture.api_runs._retire_live_run(self.a,request.run.run_id);self.a._background_tasks.discard(task)
        return task,request
    async def test_real_queue_running_settling_success_to_empty_inventory(self):
        task,request=self.launch();phases=[]
        phases.append(self.watch(self.observer.capture).live_work[0].phase)
        self.go.set();await asyncio.wait_for(self.running.wait(),2);phases.append(self.watch(self.observer.capture).live_work[0].phase)
        self.settle.set();await asyncio.wait_for(self.settling.wait(),2);phases.append(self.watch(self.observer.capture).live_work[0].phase)
        self.finish.set();self.assertEqual(await task,'owner finished')
        fixture.api_runs._retire_live_run(self.a,request.run.run_id);self.a._background_tasks.discard(task)
        result=self.watch(lambda:self.observer.retire_completed(request.run.run_id))
        seen=self.watch(self.observer.capture);self.assertEqual(seen.live_work,());self.assertEqual(seen.rows.admissions,())
        self.assertEqual(phases,['QUEUED','RUNNING','SETTLING']);self.assertFalse(result['storeReleaseAuthorized'])
        self.assertTrue(self.owner.owns(self.home));RECORDS.append({'case':self._testMethodName,'phases':phases,'retired':result,'emptyTaskInventory':True,'profileStillOwned':True})
    async def test_real_partial_settlement_keeps_observation(self):
        task,request=await self.complete(commit_response=False)
        with self.assertRaises(obs.TaskObservationRejected):self.watch(lambda:self.observer.retire_completed(request.run.run_id))
        self.assertIn(request.run.run_id,self.observer._entries)
        self.assertIsNone(self.response._conn.execute('SELECT settled_at FROM main.response_keys').fetchone()[0]);self.alive()
    async def test_real_response_transaction_blocks_retirement_without_rollback(self):
        _,request=await self.complete();self.response._conn.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(obs.TaskObservationUnavailable):self.observer.retire_completed(request.run.run_id)
            self.assertTrue(self.response._conn.in_transaction);self.assertIn(request.run.run_id,self.observer._entries)
        finally:self.response._conn.rollback()
        self.watch(lambda:self.observer.retire_completed(request.run.run_id));self.watch(self.observer.capture)
    async def test_real_failed_task_not_retired_despite_terminal_rows(self):
        task,request=await self.complete(fail_after=True);self.assertIsInstance(task.exception(),RuntimeError)
        with self.assertRaises(obs.TaskObservationRejected):self.observer.retire_completed(request.run.run_id)
        self.assertIn(request.run.run_id,self.observer._entries);self.alive()
    async def test_real_cancelled_task_cannot_be_forgiven_by_done_flag(self):
        task,request=self.launch();self.go.set();await asyncio.wait_for(self.running.wait(),2);task.cancel();await asyncio.gather(task,return_exceptions=True)
        fixture.api_runs._retire_live_run(self.a,request.run.run_id);self.a._background_tasks.discard(task)
        with self.assertRaises(obs.TaskObservationRejected):self.observer.retire_completed(request.run.run_id)
        self.assertIn(request.run.run_id,self.observer._entries);self.assertTrue(task.cancelled())
    async def test_real_completed_binding_mismatch_latches(self):
        _,request=await self.complete();self.replay._conn.execute('UPDATE main.run_idempotency SET fingerprint=?',('e'*64,));self.replay._conn.commit()
        with self.assertRaises(obs.TaskObservationRejected):self.observer.retire_completed(request.run.run_id)
        self.replay._conn.execute('UPDATE main.run_idempotency SET fingerprint=?',(request.run.fingerprint,));self.replay._conn.commit()
        with self.assertRaisesRegex(obs.TaskObservationRejected,'requires_reconciliation'):self.observer.retire_completed(request.run.run_id)
        self.assertIn(request.run.run_id,self.observer._entries)
    async def test_success_does_not_end_latched_drain(self):
        _,request=await self.complete();self.observer.request_drain();self.watch(lambda:self.observer.retire_completed(request.run.run_id))
        r=self.watch(self.observer.capture);self.assertTrue(r.draining);self.assertEqual(r.live_work,())
        self.assertFalse(r.public()['runtimeAdmissionAuthorized'])
    async def test_native_metadata_removal_is_not_observer_responsibility(self):
        task,request=self.launch();self.go.set();await self.running.wait();self.settle.set();await self.settling.wait();self.finish.set();await task
        with self.assertRaises(obs.TaskObservationRejected):self.observer.retire_completed(request.run.run_id)
        self.assertIs(self.a._active_run_tasks[request.run.run_id],task);self.assertIn(task,self.a._background_tasks)

def main():
    global runtime
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-c116a-import-') as boot:
        os.environ.update(HERMES_HOME=boot,HOME=boot,USERPROFILE=boot,LOCALAPPDATA=boot,APPDATA=boot);sys.path.insert(0,str(native))
        def audit(event,args):
            if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
                if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(args[1],tuple) and args[1][0] in ('127.0.0.1','::1'):
                    fixture.AUDIT['frameworkSocketEvents']+=1;return
                fixture.AUDIT['network']+=1;raise PermissionError('c116a_offline')
            if fixture.AUDIT['watch'] and event=='sqlite3.connect':raise AssertionError('observer_new_connection')
            if fixture.AUDIT['watch'] and event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and str(args[0]).endswith(('.db','.db-journal','.db-wal','.db-shm')):raise AssertionError('observer_raw_database_open')
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
        fixture.api_runs=api_server_runs;denied=fixture.AUDIT['network']
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeRetirement))
        imports={}
        for module in tuple(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if file:
                path=Path(file).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        report={'result':'PASS_NATIVE_TASK_RETIREMENT' if r.wasSuccessful() and fixture.AUDIT['network']==denied else 'FAIL','total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.errors+r.failures})-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'records':RECORDS,'nativeImports':imports,'sources':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('packages/claw-hermes/gateway_work_observer.py','packages/claw-hermes/gateway_work_health.py','packages/claw-hermes/gateway_work_health_reader.py','scripts/qa/c116a_native_retirement.py','scripts/qa/b112x9_adapter_probe.py')},'realNativeAdapterStoresAndTasks':True,'realProcessStartIdentity':True,'producerHooksAreTestSeam':True,'nativeIngressHooksIntegrated':False,'profileMountVerified':False,'httpStarted':False,'fullIsolationTested':False,'newNetworkAttempts':fixture.AUDIT['network']-denied,'deniedImportProbes':denied,'providerCalls':0,'rootWslAction':False,'profileOwnershipReleased':not ownership.process_ownership.homes}
    report['bootstrapRemoved']=not Path(boot).exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('nativeImports','sources','records')}),flush=True)
    if report['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-12000:])
    return 0 if report['result'].startswith('PASS') and report['bootstrapRemoved'] and report['profileOwnershipReleased'] else 1
if __name__=='__main__':raise SystemExit(main())
