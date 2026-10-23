"""Real asyncio Task contracts; native adapter/storage boundaries explicitly doubled."""
import asyncio,os,sys,threading,time,unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_work_observer as o
p=o.policy

class BindingInputs(unittest.TestCase):
    def test_run_fingerprint_is_exact_lower_hex(self):
        for value in ('a'*63,'F'*64,True,'x'*64):
            with self.subTest(value=value),self.assertRaises(o.TaskObservationRejected):o.RunRequestBinding('run','scope','key',value)
    def test_response_input_bounded(self):
        for key in ('', 'x'*513,'bad'+chr(1)):
            with self.assertRaises(o.TaskObservationRejected):o.ResponseRequestBinding(key,'a'*64)
    def test_generation_and_phase_exact(self):
        run=o.RunRequestBinding('run','scope','key','a'*64)
        for phase,generation in (('QUEUED',0),('RUNNING',None),('SETTLING',True),('OTHER',1)):
            with self.subTest(phase=phase,generation=generation),self.assertRaises(o.TaskObservationRejected):o.TaskRequest('a','s',1,generation,phase,run)
        self.assertIsNone(o.TaskRequest('a','s',1,None,'QUEUED',run).generation)
    def test_frozen_bindings_cannot_be_changed_by_ingress_dict(self):
        run=o.RunRequestBinding('run','scope','key','a'*64)
        with self.assertRaises(AttributeError):run.key='other'
        with self.assertRaises(o.TaskObservationRejected):o.TaskRequest('a','s',1,1,'RUNNING',{'run_id':'run'})

class RealTaskContracts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.identity=p.RuntimeIdentity('12345678-1234-4234-8234-123456789012',1,'fixture-process',os.getpid(),77)
        self.tasks=[]
        self.obj=o.NativeTaskObserver.__new__(o.NativeTaskObserver)
        self.obj._identity=self.identity;self.obj._actor=(os.getpid(),threading.get_ident());self.obj._loop=asyncio.get_running_loop()
        self.obj._entries={};self.obj._revision=0;self.obj._reading=False;self.obj._draining=False;self.obj._fault=None
        for name in ('_task_map','_aliases','_scopes','_status_map'):setattr(self.obj,name,{})
        self.obj._background=set()
        self.obj._reader=SimpleNamespace(capture=self.rows)
        self.boundary=patch.object(self.obj,'_native_check',return_value=None);self.boundary.start();self.addCleanup(self.boundary.stop)
    async def asyncTearDown(self):
        for task in self.tasks:
            if not task.done():task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
    def task(self,coro=None):
        task=asyncio.create_task(coro if coro is not None else asyncio.Event().wait());self.tasks.append(task);return task
    def request(self,run_id='run',aid='a',response=True,phase='RUNNING',generation=1):
        return o.TaskRequest(aid,'s',1,generation,phase,o.RunRequestBinding(run_id,'scope','key','a'*64),o.ResponseRequestBinding('response','b'*64) if response else None)
    def publish(self,task=None,request=None):
        task=task or self.task();request=request or self.request();run=request.run.run_id
        self.obj._task_map[run]=task;self.obj._background.add(task);self.obj._aliases[run]=request.admission_id;self.obj._scopes[run]=request.run.scope
        self.obj._status_map[run]={'run_id':run,'session_id':request.session_id,'status':'queued' if request.phase=='QUEUED' else 'running'}
        self.obj.publish(task,request);return task,request
    def rows(self,*,live_work):
        requests=[self.obj._entries[w.run_id][1] for w in live_work]
        return o.CommittedWorkRows(self.identity,1,time.monotonic_ns(),(),(),(),0,
            tuple((r.run.run_id,r.run.scope,r.run.key,r.run.fingerprint) for r in requests),
            tuple((r.response.key,r.response.fingerprint) for r in requests if r.response))
    def rejected(self):
        with self.assertRaises(o.TaskObservationRejected):self.obj.capture()
    async def test_actual_live_task_bound_without_health_or_storage_flags(self):
        task,request=self.publish();seen=self.obj.capture();self.assertTrue(seen.live_work[0].task_alive)
        self.assertFalse(task.done());self.assertFalse(task.cancelled());self.assertEqual(seen.revision,1)
        body=seen.public()
        for key in ('storageIntegrityVerifiedHere','nativeProducerHooksVerifiedHere','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertIs(body[key],False)
        self.assertNotIn('complete',body);self.assertNotIn('healthy',body)
    async def test_no_claimed_liveness_argument_accepted(self):
        self.publish()
        with self.assertRaises(TypeError):self.obj.capture(task_alive=True)
    async def test_cancel_requested_before_next_loop_tick_refused(self):
        task,_=self.publish();task.cancel();self.assertGreater(task.cancelling(),0);self.rejected()
        self.assertTrue(self.obj._fault)
    async def test_done_task_refused_without_touching_native_metadata(self):
        async def finished():return 'done'
        task,_=self.publish(self.task(finished()));await task;self.rejected();self.assertIn('run',self.obj._task_map)
    async def test_failed_task_remains_reconciliation_not_idle(self):
        async def fail():raise ValueError('fixture only')
        task,_=self.publish(self.task(fail()))
        with self.assertRaises(ValueError):await task
        self.rejected()
    async def test_unregistered_native_task_and_hidden_background_refused(self):
        task,_=self.publish();extra=self.task();self.obj._background.add(extra);self.rejected()
        self.assertFalse(task.done());self.assertFalse(extra.done())
    async def test_native_map_can_not_drop_registered_task(self):
        self.publish();self.obj._task_map.clear();self.rejected()
    async def test_native_map_can_not_replace_task_object(self):
        self.publish();self.obj._task_map['run']=self.task();self.rejected()
    async def test_wrong_native_alias_or_scope_rejected(self):
        self.publish();self.obj._aliases['run']='wrong';self.rejected()
        self.obj._aliases['run']='a'
        with self.assertRaisesRegex(o.TaskObservationRejected,'requires_reconciliation'):self.obj.capture()
    async def test_native_status_wrong_session_rejected(self):
        self.publish();self.obj._status_map['run']['session_id']='other';self.rejected()
    async def test_native_status_wrong_phase_rejected(self):
        self.publish();self.obj._status_map['run']['status']='completed';self.rejected()
    async def test_run_scope_key_fingerprint_checked_independently(self):
        self.publish();original=self.rows
        def corrupt(**kw):return replace(original(**kw),run_bindings=(('run','scope','key','c'*64),))
        self.obj._reader.capture=corrupt;self.rejected()
    async def test_response_fingerprint_mismatch_rejected(self):
        self.publish();original=self.rows
        self.obj._reader.capture=lambda **kw:replace(original(**kw),response_fingerprints=(('response','c'*64),));self.rejected()
    async def test_duplicate_binding_rows_not_silently_collapsed(self):
        self.publish();original=self.rows
        self.obj._reader.capture=lambda **kw:replace(original(**kw),run_bindings=(('run','scope','key','a'*64),)*2);self.rejected()
    async def test_unavailable_native_read_can_be_reobserved(self):
        self.publish()
        def unavailable(**kw):raise o.WorkReadUnavailable('busy')
        self.obj._reader.capture=unavailable
        with self.assertRaises(o.TaskObservationUnavailable):self.obj.capture()
        self.assertIsNone(self.obj._fault);self.obj._reader.capture=self.rows;self.obj.capture()
    async def test_revision_change_is_not_consistent_capture(self):
        self.publish()
        def drift(**kw):
            result=self.rows(**kw);self.obj._revision+=1;return result
        self.obj._reader.capture=drift
        with self.assertRaises(o.TaskObservationUnavailable):self.obj.capture()
    async def test_native_reference_change_during_read_is_sticky(self):
        self.publish()
        def drift(**kw):
            result=self.rows(**kw);self.obj._aliases['run']='other';return result
        self.obj._reader.capture=drift;self.rejected()
    async def test_phase_change_requires_the_registered_current_task(self):
        self.publish()
        with self.assertRaisesRegex(o.TaskObservationRejected,'not_owner'):self.obj.advance('run',phase='SETTLING',generation=1)
    async def test_real_owner_advances_and_generation_stays_bound(self):
        gate=asyncio.Event();ready=asyncio.Event()
        async def owner():
            await gate.wait();self.obj.advance('run',phase='RUNNING',generation=4)
            self.obj._status_map['run']['status']='running';ready.set();await asyncio.Event().wait()
        task=self.task(owner());self.publish(task,self.request(phase='QUEUED',generation=None));gate.set();await ready.wait()
        seen=self.obj.capture();self.assertEqual((seen.live_work[0].phase,seen.live_work[0].generation),('RUNNING',4));self.assertEqual(seen.revision,2)
    async def test_drain_latches_and_rejects_new_publish(self):
        self.publish();self.obj.request_drain();rev=self.obj._revision;self.obj.request_drain();self.assertEqual(rev,self.obj._revision)
        self.assertTrue(self.obj.capture().draining)
        with self.assertRaisesRegex(o.TaskObservationRejected,'draining'):self.obj.publish(self.task(),self.request('second','b'))
    async def test_publish_requires_native_registry_not_just_task(self):
        with self.assertRaisesRegex(o.TaskObservationRejected,'native_registry'):self.obj.publish(self.task(),self.request())
    async def test_same_task_cannot_be_second_owner(self):
        task,_=self.publish();self.obj._task_map['second']=task
        with self.assertRaisesRegex(o.TaskObservationRejected,'duplicate_owner'):self.obj.publish(task,self.request('second','b'))
    async def test_other_thread_cannot_observe(self):
        self.publish();error=[]
        def other():
            try:self.obj.capture()
            except o.TaskObservationRejected as exc:error.append(str(exc))
        thread=threading.Thread(target=other);thread.start();thread.join(2);self.assertEqual(error,['task_other_actor'])
    async def test_no_response_request_does_not_fabricate_binding(self):
        self.publish(request=self.request(response=False));seen=self.obj.capture();self.assertIsNone(seen.live_work[0].response_key)

    async def completed(self,settled=True,remove_native=True):
        async def done():return 'ok'
        task,request=self.publish(self.task(done()),self.request(phase='SETTLING'))
        await task
        self.obj._status_map['run']['status']='completed'
        if remove_native:self.obj._task_map.clear();self.obj._background.clear()
        def rows(*,live_work):
            return o.CommittedWorkRows(self.identity,1,time.monotonic_ns(),
                (p.Admission('a','s','terminal',1,1,1),),
                (p.Run('run','{"status":"completed"}',self.identity.owner_pid,self.identity.owner_started),),
                (p.ResponseIdentity('response','a',settled),),0,
                (('run','scope','key','a'*64),),(('response','b'*64),))
        self.obj._reader.capture=rows
        return task,request
    async def test_normal_retirement_removes_observation_not_native_state(self):
        await self.completed();result=self.obj.retire_completed('run')
        self.assertEqual(result['state'],'TASK_OBSERVATION_RETIRED');self.assertEqual(self.obj._entries,{})
        for k in ('nativeTaskRemovedHere','databaseWritesPerformed','runtimeAdmissionAuthorized','storeReleaseAuthorized'):self.assertFalse(result[k])
        self.assertEqual(self.obj._status_map['run']['status'],'completed')
        self.obj._reader.capture=self.rows;self.assertEqual(self.obj.capture().live_work,())
    async def test_successful_task_does_not_erase_unsettled_response(self):
        await self.completed(settled=False)
        with self.assertRaises(o.TaskObservationRejected):self.obj.retire_completed('run')
        self.assertIn('run',self.obj._entries);self.assertTrue(self.obj._fault)
    async def test_observer_does_not_remove_native_task_for_producer(self):
        task,_=await self.completed(remove_native=False)
        with self.assertRaises(o.TaskObservationRejected):self.obj.retire_completed('run')
        self.assertIs(self.obj._task_map['run'],task);self.assertIn(task,self.obj._background)
    async def test_cancelled_owner_cannot_be_retired_as_success(self):
        task,_=self.publish(request=self.request(phase='SETTLING'));task.cancel();await asyncio.gather(task,return_exceptions=True)
        self.obj._task_map.clear();self.obj._background.clear()
        with self.assertRaises(o.TaskObservationRejected):self.obj.retire_completed('run')
        self.assertIn('run',self.obj._entries)
    async def test_retirement_unavailable_read_is_retryable_without_state_change(self):
        await self.completed();original=self.obj._reader.capture
        def busy(**kw):raise o.WorkReadUnavailable('busy')
        self.obj._reader.capture=busy
        with self.assertRaises(o.TaskObservationUnavailable):self.obj.retire_completed('run')
        self.assertIsNone(self.obj._fault);self.assertIn('run',self.obj._entries)
        self.obj._reader.capture=original;self.obj.retire_completed('run')
    async def test_completed_return_does_not_hide_request_fingerprint_change(self):
        await self.completed();original=self.obj._reader.capture
        self.obj._reader.capture=lambda **kw:replace(original(**kw),run_bindings=(('run','scope','key','f'*64),))
        with self.assertRaises(o.TaskObservationRejected):self.obj.retire_completed('run')
        self.assertIn('run',self.obj._entries)

if __name__=='__main__':unittest.main()
