"""Native /v1/runs handler events: real scheduler, Task maps and retirement.

Agent computation and an external-owner test boundary are doubled. No HTTP
listener/authentication middleware/model is started. QA never publishes events.
"""
from pathlib import Path
import argparse,asyncio,hashlib,json,os,sqlite3,sys,tempfile,threading,unittest
from unittest.mock import patch,AsyncMock
from dataclasses import FrozenInstanceError
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'packages/claw-hermes'),str(Path(__file__).parent)]
import b112x9_adapter_probe as fixture
from gateway_native_run_provenance import NativeRunProvenance
from gateway_work_observer import NativeTaskObserver,TaskObservationRejected
from gateway_work_health_reader import NativeWorkReader
from gateway_work_health import RuntimeIdentity
OBSERVATIONS=[]
runtime=hooks=None
class Request(dict):
    method='POST';path='/v1/runs';path_qs='/v1/runs';query={};remote='127.0.0.1';transport=None
    def __init__(self,body,key='owned-key'):
        super().__init__();self.body=body;self.headers={'Authorization':'Bearer owned-fixture-not-a-secret'}
        if key is not None:self.headers['Idempotency-Key']=key
    async def json(self):return self.body
class DummyAgent:
    session_id='';provider='fixture';model='fixture'
    def __init__(self,case):self.case=case
    def run_conversation(self,**kwargs):
        self.case.calls+=1;self.case.entered.set()
        if not self.case.release.wait(5):raise RuntimeError('dummy_test_timeout')
        if self.case.fail_compute:raise RuntimeError('owned_dummy_failure')
        return {'final_response':'offline dummy result'}
class ProducerCases(unittest.IsolatedAsyncioTestCase):
    loop_factory=staticmethod(fixture.NativeBorrowTests.loop_factory)
    build=fixture.NativeBorrowTests.build
    def setUp(self):fixture.NativeBorrowTests.setUp(self)
    async def asyncSetUp(self):
        self.a=self.build();self.calls=0;self.fail_compute=False
        self.entered=threading.Event();self.release=threading.Event();self.events=[]
        self.agent_patch=patch.object(self.a,'_create_agent',side_effect=lambda **kw:DummyAgent(self));self.agent_patch.start()
    async def asyncTearDown(self):
        self.release.set()
        if self.tasks:await asyncio.gather(*self.tasks,return_exceptions=True)
        await asyncio.get_running_loop().shutdown_default_executor(timeout=5)
        self.agent_patch.stop();await fixture.NativeBorrowTests.asyncTearDown(self)
    def attach(self,sink=None):return hooks.RunLifecycleChannel(self.a,self.events.append if sink is None else sink)
    async def submit(self,body=None,key='owned-key'):
        q=Request({'input':'offline input','model':'owned-fixture'} if body is None else body,key)
        result=await self.a._handle_runs(q)
        if result.status==202:
            value=json.loads(result.text);task=self.a._active_run_tasks.get(value['run_id'])
            if task is not None and task not in self.tasks:self.tasks.append(task)
            return result,value,task,q
        return result,None,None,q
    async def complete(self,t):
        self.release.set();await asyncio.wait_for(asyncio.shield(t),5);await asyncio.sleep(0)
    def record(self,name,**extra):OBSERVATIONS.append({'case':self._testMethodName,'assertion':name,**extra})
    async def test_actual_handler_publishes_whole_task_lifecycle(self):
        ch=self.attach();r,v,t,q=await self.submit();self.assertEqual(r.status,202)
        self.assertEqual([e.phase for e in self.events],['ACCEPTED','CREATED'])
        await self.complete(t)
        self.assertEqual([e.phase for e in self.events],['ACCEPTED','CREATED','STARTED','EXECUTION_RETURNED','RETIRED','DONE'])
        self.assertEqual([e.sequence for e in self.events],list(range(1,7)));self.assertTrue(all(e.task is t for e in self.events[1:]))
        self.assertNotIn(v['run_id'],self.a._active_run_tasks);self.assertNotIn(t,self.a._background_tasks)
        self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed');self.assertIsNone(ch._fault)
        expected=hashlib.sha256(json.dumps({'body':q.body,'gateway_session_key':''},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        row=self.replay._conn.execute('SELECT scope,idempotency_key,fingerprint FROM main.run_idempotency').fetchone()
        ident=self.events[0].binding;self.assertEqual((ident.scope,ident.key,ident.fingerprint),tuple(row));self.assertEqual(ident.fingerprint,expected)
        self.assertTrue(all(e.binding is ident for e in self.events))
        self.record('native_lifecycle_not_fixture',phases=[e.phase for e in self.events],kinds=[e.binding.execution_role for e in self.events],dummyCalls=self.calls,nativeTaskRemoved=True)
    async def test_default_disabled_path_still_completes(self):
        r,v,t,q=await self.submit();await self.complete(t)
        self.assertIsNone(self.a._run_observation_channel);self.assertEqual(self.calls,1);self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed')
    async def test_running_replay_does_not_republish_or_execute(self):
        self.attach();r,v,t,q=await self.submit();self.assertTrue(await asyncio.to_thread(self.entered.wait,3));before=len(self.events)
        r2,v2,t2,q2=await self.submit();self.assertEqual(v2['run_id'],v['run_id']);self.assertEqual(r2.status,202)
        self.assertEqual(len(self.events),before);self.assertEqual(self.calls,1);await self.complete(t)
        self.record('replay_same_native_task',calls=self.calls,newEventsDuringReplay=0)
    async def test_callback_failure_is_sticky_without_duplicating_request(self):
        calls=[]
        def fail(event):calls.append(event.phase);raise RuntimeError('private callback failure')
        ch=self.attach(fail);r,v,t,q=await self.submit();self.assertEqual(r.status,202);await self.complete(t)
        self.assertEqual(calls,['ACCEPTED']);self.assertEqual(ch._fault,'run_observation_sink_failed')
        self.assertEqual(self.calls,1);self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed')
        r2,v2,t2,q2=await self.submit();self.assertEqual(v2['run_id'],v['run_id']);self.assertEqual(self.calls,1)
    async def test_callback_cancellation_does_not_cancel_native_request(self):
        def cancel(event):raise asyncio.CancelledError('callback-only')
        channel=self.attach(cancel);r,v,t,q=await self.submit();await self.complete(t)
        self.assertEqual(r.status,202);self.assertIsNotNone(channel._fault)
        self.assertFalse(t.cancelled());self.assertEqual(self.calls,1)
        self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed')
    async def test_callback_cancellation_during_retirement_keeps_native_cleanup(self):
        def cancel(event):
            self.events.append(event)
            if event.phase=='RETIRED':raise asyncio.CancelledError('cleanup-observer-only')
        channel=self.attach(cancel);r,v,t,q=await self.submit();await self.complete(t)
        self.assertIsNotNone(channel._fault);self.assertNotIn(v['run_id'],self.a._active_run_tasks)
        self.assertNotIn(t,self.a._background_tasks);self.assertFalse(t.cancelled())
        self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed')
    async def test_identity_is_immutable_and_excludes_input_and_secret(self):
        self.attach();r,v,t,q=await self.submit({'input':'PRIVATE-PAYLOAD-SENTINEL','model':'owned-fixture'})
        with self.assertRaises(FrozenInstanceError):self.events[0].binding.key='changed'
        self.assertNotIn('PRIVATE-PAYLOAD-SENTINEL',repr(self.events));self.assertNotIn('owned-fixture-not-a-secret',repr(self.events));await self.complete(t)
    async def test_native_auth_rejects_without_creating_work_or_trace(self):
        channel=self.attach();request=Request({'input':'offline'})
        request.headers.pop('Authorization')
        result=await self.a._handle_runs(request)
        self.assertEqual(result.status,401);self.assertEqual(channel._sequence,0)
        self.assertEqual(self.a._active_run_tasks,{});self.assertEqual(self.calls,0)
        self.assertEqual(self.a._pending_agent_requests,0)
    async def test_invalid_key_never_starts_trace_or_task(self):
        ch=self.attach();r,v,t,q=await self.submit(key='bad key');self.assertEqual(r.status,400)
        self.assertEqual(ch._sequence,0);self.assertEqual(self.events,[]);self.assertEqual(self.calls,0)
    async def test_json_cannot_enable_native_observation(self):
        r,v,t,q=await self.submit({'input':'offline','run_observer':True,'_run_observation_channel':True})
        await self.complete(t);self.assertIsNone(self.a._run_observation_channel)
    async def test_unkeyed_identity_remains_unkeyed(self):
        self.attach();r,v,t,q=await self.submit(key=None);await self.complete(t)
        self.assertIsNone(self.events[0].binding.key);self.assertIsNone(self.events[0].binding.fingerprint)
    async def test_duplicate_attach_never_replaces_sink(self):
        ch=self.attach()
        with self.assertRaises(ValueError):self.attach()
        self.assertIs(self.a._run_observation_channel,ch)
    async def test_async_sink_does_not_get_scheduled_as_work(self):
        async def sink(event):raise AssertionError('must not execute callback coroutine')
        channel=self.attach(sink);r,v,t,q=await self.submit();await self.complete(t)
        self.assertEqual(channel.status()['state'],'GAP');self.assertEqual(self.calls,1)

    async def test_coroutine_result_fault_does_not_retry_request(self):
        async def ignored():return None
        ch=self.attach(lambda event:ignored());r,v,t,q=await self.submit();await self.complete(t)
        self.assertIsNotNone(ch._fault);self.assertEqual(self.calls,1)
    async def test_selected_provenance_never_promotes_live_carrier_to_executor(self):
        epoch=runtime.begin_runtime_epoch(self.state,instance_id='p117-owned')
        sid=self.state._conn.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()[0]
        identity=RuntimeIdentity(sid,epoch,'p117-owned',os.getpid(),self.a._run_owner_started)
        reader=NativeWorkReader(self.state,self.replay,self.response,identity,schema_hashes=(
            'f4889e8d91c8b57ee828ac7a1ead9ac880db48f9c21500e3800d4b48b759e8c7',
            'c4adac6a33044a05806868e2518e5f778c62e99d26a73c003fc6112ed3d589a3',
            'c4b66ce0c9b2571b17eae2080834e365b3aa526d40157c8c3cf4f353541ae1b4'))
        obs=NativeTaskObserver(self.a,reader);source=NativeRunProvenance(obs)
        r,v,t,q=await self.submit();self.assertTrue(await asyncio.to_thread(self.entered.wait,3))
        bound=source.binding_for(v['run_id'],t).public()
        self.assertEqual(bound['executionRole'],'executor_thread_carrier')
        for k in ('canonicalExecutorVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','storeReleaseAuthorized'):self.assertFalse(bound[k])
        with self.assertRaises(TaskObservationRejected):obs.capture()
        await self.complete(t);status=source.status();self.assertEqual(status['activeProvenanceRecords'],0)
        self.assertEqual(status['completedDiagnosticCount'],1);self.assertFalse(status['canonicalExecutorVerified'])
        self.record('selected_source_no_executor_health',nativeHooksAutomatic=True,activeRecordsAfterDone=0)

    async def test_cancelled_wrapper_done_does_not_mean_worker_stopped(self):
        self.attach();r,v,t,q=await self.submit();self.assertTrue(await asyncio.to_thread(self.entered.wait,3))
        t.cancel();await asyncio.gather(t,return_exceptions=True);await asyncio.sleep(0)
        self.assertEqual(fixture.api_runs.api_worker_live_count(),1);self.assertTrue(t.cancelled())
        self.assertEqual(self.events[-1].phase,'DONE');self.assertEqual(self.events[-1].binding.execution_role,'executor_thread_carrier')
        self.record('wrapper_not_executor',wrapperDone=True,nativeWorkerStillAlive=True,noExecutorFinishedEvent=True)
    async def test_failed_compute_native_status_not_health(self):
        self.fail_compute=True;self.attach();r,v,t,q=await self.submit();await self.complete(t)
        self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'failed');self.assertEqual(self.events[-1].phase,'DONE')
    async def test_external_owner_is_labelled_waiter(self):
        self.attach();self.state.create_session('owned-session','api_server')
        async def finish(*args,**kwargs):return {'status':'settled','reply':'dummy remote receipt'}
        with patch.object(self.a,'_admit_to_live_bot_chat',new=AsyncMock(return_value=(self.home,{'delivery_id':'delivery-owned'}))),patch('gateway.platforms.api_server_bot_chat.await_live_delivery',new=finish):
            r,v,t,q=await self.submit({'input':'offline','session_id':'owned-session'});self.assertEqual(r.status,202);await self.complete(t)
        self.assertEqual(self.calls,0);self.assertTrue(all(e.binding.execution_role=='external_owner_observer' for e in self.events[1:]))
        self.record('external_waiter_not_executor',kind='external_owner_observer',remoteOwnerBoundaryDoubled=True)
    async def test_eager_factory_gaps_trace_but_preserves_native_execution(self):
        channel=self.attach();loop=asyncio.get_running_loop();old=loop.get_task_factory();loop.set_task_factory(asyncio.eager_task_factory)
        try:r,v,t,q=await self.submit()
        finally:loop.set_task_factory(old)
        await self.complete(t)
        self.assertEqual(channel.status()['state'],'GAP');self.assertEqual(self.calls,1)
        self.assertEqual(self.a._run_statuses[v['run_id']]['status'],'completed');self.assertEqual(self.events,[])

    async def test_native_borrowed_listener_stays_closed(self):
        self.attach()
        with self.assertRaisesRegex(fixture.BorrowedStoreRejected,'listener_not_qualified'):await self.a.connect()
        self.assertIsNone(self.a._site);self.assertIsNone(self.a._runner)

def main():
    global runtime,hooks
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-p117-import-') as boot:
        os.environ.update(HERMES_HOME=boot,HOME=boot,USERPROFILE=boot,LOCALAPPDATA=boot,APPDATA=boot);sys.path.insert(0,str(native))
        def audit(event,args):
            if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
                if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(args[1],tuple) and args[1][0] in ('127.0.0.1','::1'):
                    fixture.AUDIT['frameworkSocketEvents']+=1;return
                fixture.AUDIT['network']+=1;raise PermissionError('p117_offline')
            if event in ('subprocess.Popen','os.system'):raise PermissionError('p117_no_child_program')
            if fixture.AUDIT['watch'] and event=='sqlite3.connect':raise AssertionError('borrowed_reopen')
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
        hooks=api_server_run_observation
        for n,v in locals().copy().items():
            if n in ('APIServerAdapter','PlatformConfig','SessionDB','RunIdempotencyStore','ResponseStore','BorrowedAPIStores','BorrowedStoreRejected','ownership'):setattr(fixture,n,v)
        fixture.api_runs=api_server_runs;denied=fixture.AUDIT['network']
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProducerCases))
        imports={}
        for m in tuple(sys.modules.values()):
            file=getattr(m,'__file__',None)
            if file:
                path=Path(file).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        report={'result':'PASS_INDEPENDENT_SELECTED_NATIVE_PRODUCER' if r.wasSuccessful() and fixture.AUDIT['network']==denied else 'FAIL','total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.errors+r.failures})-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],'nativeImports':imports,'observations':OBSERVATIONS,'sources':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('packages/claw-hermes/gateway_native_run_provenance.py','packages/claw-hermes/gateway_work_observer.py','scripts/qa/p117n1_native_hook_audit.py','scripts/qa/b112x9_adapter_probe.py')},'nativeHandlerSchedulerTaskMapsAndRetirementReal':True,'manualObservationPublicationInTests':False,'agentComputationIsDummy':True,'externalOwnerBoundaryDoubled':True,'nativeHandlerAuthDecoratorUsed':True,'httpServerMiddlewareOrListenerTested':False,'executorOwnershipHealthAccepted':False,'newNetworkAttempts':fixture.AUDIT['network']-denied,'deniedImportProbes':denied,'providerCalls':0,'rootWslAction':False,'profileOwnershipReleased':not ownership.process_ownership.homes}
    report['bootstrapRemoved']=not Path(boot).exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sources','nativeImports','observations')}),flush=True)
    if report['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-18000:])
    return 0 if report['result'].startswith('PASS') and report['profileOwnershipReleased'] and report['bootstrapRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
