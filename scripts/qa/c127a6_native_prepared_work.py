"""Prepared idle-work refusals on actual native owners and real tasks/threads.
No agent request/TurnRunner computation/service admission is started. Work records
are explicitly injected fixture faults; existing Windows Linux boundaries are
doubled by s124b1_startup_fixture. This is not kernel or active-work acceptance.
"""
import argparse,asyncio,hashlib,json,os,sys,tempfile,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/qa'),str(ROOT/'packages/claw-hermes')]
import c124l1_native_consumer_checks as b
c=b.c
OBS=[]
MISSING=object()
class PreparedWork(b.IndependentConsumer):
    @contextmanager
    def task_in(self,obj,field,*,completed=False,cancelled=False):
        old=getattr(obj,field,MISSING);gate=asyncio.Event()
        async def make():return asyncio.create_task(gate.wait())
        task=b.LOOP.run_until_complete(make())
        if completed:gate.set();b.LOOP.run_until_complete(task)
        if cancelled:
            task.cancel()
            try:b.LOOP.run_until_complete(task)
            except asyncio.CancelledError:pass
        mapping={'owned-fixture':task} if isinstance(old,dict) else {task}
        setattr(obj,field,mapping)
        try:yield task,mapping
        finally:
            if not task.done():gate.set();b.LOOP.run_until_complete(task)
            if old is MISSING:delattr(obj,field)
            else:setattr(obj,field,old)
    def idle_refused(self,consumer):
        with self.watched(),self.assertRaises(c.PreparedConsumerRejected):consumer.check()
    def known_detach_refused(self,consumer):
        caught=None
        with self.watched():
            try:b.LOOP.run_until_complete(consumer.detach())
            except Exception as exc:caught=type(exc).__name__
        stages=(consumer._stage,consumer._bundle._stage,consumer._binding._stage)
        OBS.append({'case':self._testMethodName,'stages':stages,'refusalType':caught})
        self.assertIsNotNone(caught);self.assertEqual(stages,('ATTACHED','ATTACHED','PREPARED'))
        self.open()
    def test_work_idle_positive_control_remains_readonly(self):
        consumer=self.prep()
        with self.watched():consumer.check()
        self.assertFalse(consumer.status()['activeTaskObserversQualified'])
        b.LOOP.run_until_complete(consumer.detach());self.o.close()
    def test_work_live_runner_task_not_idle(self):
        consumer=self.prep()
        with self.task_in(consumer._runner,'_background_tasks') as (task,records):
            self.idle_refused(consumer);self.assertFalse(task.done());self.assertFalse(task.cancelled())
            self.assertIs(consumer._runner._background_tasks,records)
        consumer.check()
    def test_work_runner_task_refused_before_api_detach(self):
        consumer=self.prep()
        with self.task_in(consumer._runner,'_background_tasks') as (task,records):
            self.known_detach_refused(consumer);self.assertFalse(task.cancelled());self.assertIn(task,records)
        b.LOOP.run_until_complete(consumer.detach());self.o.close()
    def test_work_authority_mutation_refused_before_api_detach(self):
        consumer=self.prep()
        with self.task_in(consumer._binding._authority,'_mutation_tasks') as (task,records):
            self.known_detach_refused(consumer);self.assertFalse(task.done());self.assertIn(task,records)
        b.LOOP.run_until_complete(consumer.detach())
    def test_work_mailbox_operation_is_not_silently_untracked(self):
        consumer=self.prep()
        with self.task_in(consumer._binding._authority,'_bot_mailbox_operations') as (task,records):
            self.known_detach_refused(consumer);self.assertFalse(task.done());self.assertIn(task,records)
    def test_work_done_runner_record_is_not_pruned(self):
        consumer=self.prep()
        with self.task_in(consumer._runner,'_background_tasks',completed=True) as (task,records):
            self.idle_refused(consumer);self.assertTrue(task.done());self.assertIn(task,records)
    def test_work_cancelled_runner_record_is_not_pruned(self):
        consumer=self.prep()
        with self.task_in(consumer._runner,'_background_tasks',cancelled=True) as (task,records):
            self.idle_refused(consumer);self.assertTrue(task.cancelled());self.assertIn(task,records)
    def test_work_executor_even_without_submitted_job_is_not_prepared(self):
        consumer=self.prep();runner=consumer._runner;old=runner._executor
        with ThreadPoolExecutor(max_workers=1) as executor:
            runner._executor=executor
            try:self.known_detach_refused(consumer)
            finally:runner._executor=old
    def test_work_heartbeat_task_refused_without_cancel(self):
        consumer=self.prep();runner=consumer._runner;old=runner._loop_heartbeat_task
        with self.task_in(runner,'_background_tasks') as (task,records):
            runner._background_tasks=set();runner._loop_heartbeat_task=task
            try:self.idle_refused(consumer);self.assertFalse(task.cancelled())
            finally:runner._loop_heartbeat_task=old
    def test_work_physical_thread_outlives_cancelled_waiter(self):
        from gateway.run import GatewayRunner
        consumer=self.prep();authority=consumer._binding._authority
        old=getattr(authority,'_turn_workers',MISSING);release=threading.Event();entered=threading.Event();done=threading.Event()
        def worker_body():
            entered.set()
            try:release.wait(10)
            finally:done.set()
        thread=threading.Thread(target=worker_body);thread.start();self.assertTrue(entered.wait(3))
        async def cancelled():await asyncio.Event().wait()
        async def make():
            task=asyncio.create_task(cancelled());task.cancel()
            try:await task
            except asyncio.CancelledError:pass
            return task
        carrier=b.LOOP.run_until_complete(make())
        worker=GatewayRunner._RunAgentWorker(executor_task=carrier,worker_done=done)
        # Explicit test-only registry fault, not native producer/admission acceptance.
        records={id(worker):(worker,[None])};authority._turn_workers=records
        try:
            self.known_detach_refused(consumer)
            self.assertTrue(carrier.cancelled());self.assertTrue(thread.is_alive());self.assertFalse(done.is_set())
            self.assertIs(authority._turn_workers,records);self.assertIn(id(worker),records)
        finally:
            release.set();thread.join(5);self.assertFalse(thread.is_alive())
            if old is MISSING:delattr(authority,'_turn_workers')
            else:authority._turn_workers=old
    def test_work_postdetach_mailbox_task_blocks_store_close(self):
        consumer=self.prep();b.LOOP.run_until_complete(consumer.detach())
        with self.task_in(consumer._binding._authority,'_bot_mailbox_operations') as (task,records):
            with self.assertRaises(c.PreparedConsumerRejected):self.o.close()
            self.open();self.assertFalse(task.done())
    def test_review_bot_receipt_task_blocks_selection_and_close(self):
        consumer=self.prep()
        with self.task_in(consumer._binding._authority,'_bot_receipt_tasks') as (task,records):
            self.known_detach_refused(consumer);self.assertFalse(task.cancelled())
    def test_review_completion_delivery_inflight_blocks_detach(self):
        consumer=self.prep();value=consumer._runner._completion_deliveries_inflight
        value.add(('owned','fixture',1))
        try:self.known_detach_refused(consumer)
        finally:value.clear()
    def test_review_completion_batch_payload_blocks_detach(self):
        consumer=self.prep();value=consumer._runner._completion_notification_batches
        value[('owned',)]=[('fixture',{},b.LOOP.create_future())]
        try:self.known_detach_refused(consumer)
        finally:value.clear()
    def test_review_detached_descriptor_drift_blocks_original_owner_close(self):
        consumer=self.prep();b.LOOP.run_until_complete(consumer.detach())
        descriptor=consumer._binding._descriptor;old=descriptor['state'];descriptor['state']='caller_prepared'
        try:
            with self.assertRaises(c.PreparedConsumerRejected):self.o.close()
            self.open();self.assertEqual(descriptor['state'],'caller_prepared')
        finally:descriptor['state']=old
    def test_review_detached_registry_drift_blocks_original_owner_close(self):
        consumer=self.prep();b.LOOP.run_until_complete(consumer.detach())
        registry=consumer._binding._registry;old=registry.multiplexed;registry.multiplexed=True
        try:
            with self.assertRaises(c.PreparedConsumerRejected):self.o.close()
            self.open();self.assertIs(registry.multiplexed,True)
        finally:registry.multiplexed=old
    def test_work_arriving_during_api_cleanup_retains_unknown(self):
        consumer=self.prep();old=consumer._adapter._memory_sessions;entered=threading.Event();release=threading.Event()
        class PausedMemory:
            def close_all(self):
                entered.set()
                if not release.wait(10):raise RuntimeError('fixture cleanup timeout')
                old.close_all()
        consumer._adapter._memory_sessions=PausedMemory()
        async def trial():
            closing=asyncio.create_task(consumer.detach())
            for _ in range(1000):
                if entered.is_set():break
                await asyncio.sleep(.005)
            self.assertTrue(entered.is_set());gate=asyncio.Event();task=asyncio.create_task(gate.wait())
            consumer._runner._background_tasks.add(task);release.set()
            try:
                with self.assertRaises(Exception):await closing
                self.assertEqual(consumer._stage,'CLOSE_UNKNOWN');self.assertFalse(task.cancelled())
                self.refuse_close()
            finally:gate.set();await task;consumer._runner._background_tasks.remove(task)
        try:b.LOOP.run_until_complete(trial())
        finally:release.set();consumer._adapter._memory_sessions=old

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--compat',action='store_true');p.add_argument('--review-only',action='store_true');a=p.parse_args()
    native=a.native.resolve(strict=True);out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    b.NATIVE=native;b.LOOP=asyncio.new_event_loop();asyncio.set_event_loop(b.LOOP)
    with tempfile.TemporaryDirectory(prefix='alaz-c127-prepared-') as tmp:
        b.BASE=Path(tmp).resolve();home=b.BASE/'import-home';home.mkdir()
        os.environ.update(HERMES_HOME=str(home),HOME=str(b.BASE),USERPROFILE=str(b.BASE));sys.path.insert(0,str(native));sys.addaudithook(b.audit)
        from gateway.config import GatewayConfig,PlatformConfig
        import hermes_state_registry
        b.Config,b.Platform,b.Registry=GatewayConfig,PlatformConfig,hermes_state_registry
        own=sorted(n for n in PreparedWork.__dict__ if n.startswith('test_') and (not a.review_only or n.startswith('test_review_')))
        suite=unittest.TestSuite(PreparedWork(name) for name in own)
        if a.compat:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(b.IndependentConsumer))
        with (out/'tests.txt').open('x',encoding='utf-8',newline='\n') as log:r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        b.LOOP.run_until_complete(b.LOOP.shutdown_default_executor());b.LOOP.close()
        imports={}
        for m in tuple(sys.modules.values()):
            file=getattr(m,'__file__',None)
            if file:
                q=Path(file).resolve()
                if q.is_relative_to(native) and q.suffix=='.py':imports[q.relative_to(native).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
        files=['packages/claw-hermes/gateway_prepared_consumer.py','packages/claw-hermes/gateway_store_startup.py','scripts/qa/s124b1_startup_fixture.py','scripts/qa/c124l1_native_consumer_checks.py','scripts/qa/c127a6_native_prepared_work.py','config/prepared-consumer-s124b1-sources.json']
        failed={t.id().split(' (',1)[0] for t,_ in r.errors+r.failures}
        report={'result':'PASS_PREPARED_WORK_GUARDS_WITH_WINDOWS_BOUNDARY_DOUBLES' if r.wasSuccessful() else 'FAIL','total':r.testsRun,'passed':r.testsRun-len(failed)-len(r.skipped),'errors':len(r.errors),'failures':len(r.failures),'skipped':len(r.skipped),'errorIds':[t.id() for t,_ in r.errors],'failureIds':[t.id() for t,_ in r.failures],
                'sourceHashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files},'nativeImports':imports,'checks':b.CHECKS,'caseEnd':b.ENDS,'detachObservations':OBS,'deniedEvents':b.DENIED,'nativeProductMethodsReplaced':False,'realTasksThreadsAndNativeWorkerRecord':True,'taskRegistryFaultInjectionExplicit':True,'completeAgentOrTurnRunnerExecuted':False,'windowsActorLeaseMountColdBoundariesDoubled':True,'linuxConfinementRerun':False,'serviceAdmissionActivated':False,'providerCalls':0,'ownMethods':len(own),'compatMethods':23 if a.compat else 0}
    report['temporaryRootRemoved']=not b.BASE.exists()
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sourceHashes','nativeImports','checks','caseEnd','deniedEvents')}),flush=True)
    if not r.wasSuccessful():print((out/'tests.txt').read_text(encoding='utf-8')[-9500:],flush=True)
    return 0 if r.wasSuccessful() and report['temporaryRootRemoved'] else 1
if __name__=='__main__':raise SystemExit(main())
