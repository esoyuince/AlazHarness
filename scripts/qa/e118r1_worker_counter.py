"""Real native executor cancellation contract. No replaced executor or worker function.

Tests select one actual default ThreadPoolExecutor worker for deterministic queue
ordering. No API listener/model/provider, WSL/root or user profile data is used.
"""
from pathlib import Path
import argparse,asyncio,concurrent.futures,hashlib,json,os,sys,tempfile,threading,unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import b112x9_adapter_probe as fixture
api=None
RESULTS=[]
class WorkerCounter(unittest.IsolatedAsyncioTestCase):
    loop_factory=staticmethod(fixture.NativeBorrowTests.loop_factory)
    async def asyncSetUp(self):
        self.assertEqual(api.api_worker_live_count(),0)
        self.loop=asyncio.get_running_loop();self.loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=1))
        self.pending=[];self.releases=[];self.called=[]
    async def barrier(self):
        for _ in range(2):
            f=self.loop.create_future();self.loop.call_soon(f.set_result,None);await f
    def submit(self,fn):
        f=api._submit_api_worker(self.loop,fn);self.pending.append(f);return f
    async def hold(self,native=False):
        arrived=self.loop.create_future();release=threading.Event();self.releases.append(release)
        def body():
            self.called.append('holder');self.loop.call_soon_threadsafe(arrived.set_result,None)
            if not release.wait(8):raise RuntimeError('fixture_holder_not_released')
            return 17
        f=self.submit(body) if native else self.loop.run_in_executor(None,body)
        if not native:self.pending.append(f)
        await asyncio.wait_for(arrived,3);return f,release
    async def drain_pool(self):
        for event in self.releases:event.set()
        await asyncio.gather(*self.pending,return_exceptions=True)
        await self.loop.shutdown_default_executor(timeout=5);await self.barrier()
        self.assertEqual(api.api_worker_live_count(),0)
    async def asyncTearDown(self):
        await self.drain_pool()
        RESULTS.append({'case':self._testMethodName,'workerCountAfterDrain':api.api_worker_live_count(),'realDefaultExecutor':True})
    async def test_normal_return_releases_once(self):
        self.assertEqual(await self.submit(lambda:31),31);self.assertEqual(api.api_worker_live_count(),0)
    async def test_exception_releases_without_changing_exception(self):
        error=ValueError('owned-fixture')
        def fail():raise error
        with self.assertRaises(ValueError) as got:await self.submit(fail)
        self.assertIs(got.exception,error);self.assertEqual(api.api_worker_live_count(),0)
    async def test_queued_future_cancel_never_enters_callable_and_releases(self):
        holder,release=await self.hold();calls=[];f=self.submit(lambda:calls.append(1))
        self.assertEqual(api.api_worker_live_count(),1);self.assertTrue(f.cancel());await self.barrier()
        self.assertEqual(api.api_worker_live_count(),0);release.set();await holder;await self.drain_pool();self.assertEqual(calls,[])
    async def test_running_cancel_keeps_count_until_actual_body_exit(self):
        f,release=await self.hold(native=True);self.assertEqual(api.api_worker_live_count(),1)
        self.assertTrue(f.cancel());await self.barrier();self.assertTrue(f.cancelled());self.assertEqual(api.api_worker_live_count(),1)
        release.set();await self.drain_pool()
    async def test_carrier_task_cancel_queued_does_not_leak(self):
        holder,release=await self.hold();submitted=asyncio.Event();calls=[]
        async def carrier():
            f=self.submit(lambda:calls.append(1));submitted.set();return await f
        task=asyncio.create_task(carrier());await submitted.wait();task.cancel();await asyncio.gather(task,return_exceptions=True);await self.barrier()
        self.assertTrue(task.cancelled());self.assertEqual(api.api_worker_live_count(),0);release.set();await holder;self.assertEqual(calls,[])
    async def test_running_carrier_cancel_is_not_worker_cancellation(self):
        entered=self.loop.create_future();release=threading.Event();self.releases.append(release)
        def body():
            self.loop.call_soon_threadsafe(entered.set_result,None)
            if not release.wait(8):raise RuntimeError('fixture_release')
            return 4
        async def carrier():return await self.submit(body)
        task=asyncio.create_task(carrier());await asyncio.wait_for(entered,3);task.cancel();await asyncio.gather(task,return_exceptions=True);await self.barrier()
        self.assertTrue(task.cancelled());self.assertEqual(api.api_worker_live_count(),1);release.set()
    async def test_many_queued_cancels_preserve_remaining_work(self):
        holder,release=await self.hold();calls=[]
        futures=[self.submit(lambda i=i:calls.append(i)) for i in range(32)]
        self.assertEqual(api.api_worker_live_count(),32)
        for i in range(0,32,2):futures[i].cancel()
        await self.barrier();self.assertEqual(api.api_worker_live_count(),16);release.set();await holder
        await self.drain_pool();self.assertEqual(sorted(calls),list(range(1,32,2)))
    async def test_cancel_all_queued_does_not_underflow_on_late_worker_entry(self):
        holder,release=await self.hold();calls=[];futures=[self.submit(lambda:calls.append(1)) for _ in range(40)]
        for f in futures:f.cancel()
        await self.barrier();self.assertEqual(api.api_worker_live_count(),0);release.set();await holder
        await self.drain_pool();self.assertEqual(calls,[])
    async def test_completed_future_cancel_does_not_release_again(self):
        f=self.submit(lambda:9);self.assertEqual(await f,9);self.assertFalse(f.cancel());await self.barrier();self.assertEqual(api.api_worker_live_count(),0)
    async def test_submission_failure_does_not_leak_reservation(self):
        await self.loop.shutdown_default_executor(timeout=3)
        with self.assertRaises(RuntimeError):self.submit(lambda:None)
        self.assertEqual(api.api_worker_live_count(),0)
    async def test_baseexception_body_still_releases_once(self):
        class OwnedAbort(BaseException):pass
        def fail():raise OwnedAbort('expected')
        with self.assertRaises(OwnedAbort):await self.submit(fail)
        self.assertEqual(api.api_worker_live_count(),0)
    async def test_reuse_same_native_submission_path_after_cancellation(self):
        holder,release=await self.hold();f=self.submit(lambda:0);f.cancel();await self.barrier();release.set();await holder
        for value in range(12):self.assertEqual(await self.submit(lambda v=value:v),value)
        self.assertEqual(api.api_worker_live_count(),0)
def main():
    global api
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    native=args.native.resolve(strict=True);out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='alaz-e118-counter-') as home:
        os.environ.update(HERMES_HOME=home,HOME=home,USERPROFILE=home,APPDATA=home,LOCALAPPDATA=home);sys.path.insert(0,str(native))
        def audit(event,arguments):
            if event in ('socket.connect','socket.bind','socket.getaddrinfo'):
                if fixture.AUDIT['frameworkLoopSetup'] and event in ('socket.connect','socket.bind') and isinstance(arguments[1],tuple) and arguments[1][0] in ('127.0.0.1','::1'):
                    fixture.AUDIT['frameworkSocketEvents']+=1;return
                fixture.AUDIT['network']+=1;raise PermissionError('counter_offline')
            if event in ('subprocess.Popen','os.system'):raise PermissionError('counter_no_child_process')
        sys.addaudithook(audit)
        from gateway.platforms import api_server_runs as api
        denied=fixture.AUDIT['network']
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as stream:
            r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WorkerCounter))
        imports={}
        for module in tuple(sys.modules.values()):
            name=getattr(module,'__file__',None)
            if name:
                path=Path(name).resolve()
                if path.is_relative_to(native) and path.suffix=='.py':imports[path.relative_to(native).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        result={'result':'PASS_NATIVE_WORKER_CANCELLATION' if r.wasSuccessful() and api.api_worker_live_count()==0 and fixture.AUDIT['network']==denied else 'FAIL',
            'total':r.testsRun,'passed':r.testsRun-len({t.id() for t,_ in r.failures+r.errors})-len(r.skipped),
            'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),
            'failureIds':[t.id() for t,_ in r.failures],'errorIds':[t.id() for t,_ in r.errors],
            'nativeImports':imports,'qaSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'observations':RESULTS,'nativeWorkerFunctionReplaced':False,'counterManuallyReset':False,
            'realExecutorUsed':True,'listenerStarted':False,'providerCalls':0,'rootWslAction':False,
            'newNetworkAttempts':fixture.AUDIT['network']-denied,'deniedImportProbes':denied}
    result['temporaryBootstrapRemoved']=not Path(home).exists()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('nativeImports','observations')}))
    if result['result']=='FAIL':print((out/'tests.txt').read_text(encoding='utf-8')[-14000:])
    return 0 if result['result'].startswith('PASS') and result['temporaryBootstrapRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
