"""Provenance consumer contracts; native publisher is explicitly doubled.

Asyncio Tasks are real. Actual producer-hook coverage lives in the separate
native QA, which calls the original decorated native entry point.
"""
import asyncio,sys,types,unittest
from dataclasses import dataclass,replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
from gateway_work_observer import NativeTaskObserver
from gateway_native_run_provenance import NativeRunProvenance,NativeIngressRejected

@dataclass(frozen=True)
class Binding:
    run_id:str='r'
    execution_role:str='executor_thread_carrier'
    key:str|None='fixture-private-key'
@dataclass(frozen=True)
class Event:
    source:object
    sequence:int
    phase:str
    binding:object
    task:object=None
    native_status:str='completed'
    task_cancelled:bool=False
    worker_count:int=0
class Channel:
    def __init__(self,adapter,sink):
        self.adapter,self.sink,self.seq,self.state=adapter,sink,0,'OBSERVING';adapter._run_observation_channel=self
    def status(self):return {'state':self.state}
    def emit(self,phase,binding,task=None):
        self.seq+=1;return self.sink(Event(self,self.seq,phase,binding,task))

class ProvenanceContracts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        module=types.ModuleType('gateway.platforms.api_server_run_observation')
        module.RunLifecycleChannel=Channel;module.RunProducerEvent=Event
        self.modules=patch.dict(sys.modules,{'gateway.platforms.api_server_run_observation':module});self.modules.start();self.addCleanup(self.modules.stop)
        self.observer=NativeTaskObserver.__new__(NativeTaskObserver)
        self.observer._entries={};self.observer._adapter=SimpleNamespace();self.observer._usable=lambda:None;self.observer._actor_check=lambda:None
        self.consumer=NativeRunProvenance(self.observer);self.binding=Binding();self.tasks=[]
    async def asyncTearDown(self):
        for task in self.tasks:
            if not task.done():task.cancel()
        if self.tasks:await asyncio.gather(*self.tasks,return_exceptions=True)
    def task(self):
        task=asyncio.create_task(asyncio.Event().wait());self.tasks.append(task);return task
    def started(self):
        task=self.task();c=self.consumer.channel;c.emit('ACCEPTED',self.binding);c.emit('CREATED',self.binding,task);c.emit('STARTED',self.binding,task);return task
    async def test_rejects_non_observer_and_existing_owner_inventory(self):
        with self.assertRaises(NativeIngressRejected):NativeRunProvenance(object())
        self.observer._entries['x']=object()
        with self.assertRaises(NativeIngressRejected):NativeRunProvenance(self.observer)
    async def test_exact_task_binding_never_grants_executor_health(self):
        task=self.started();r=self.consumer.binding_for('r',task);self.assertIs(r.task,task);self.assertIs(r.native_binding,self.binding)
        public=r.public();self.assertNotIn('fixture-private-key',str(public))
        for key in ('canonicalExecutorVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','storeReleaseAuthorized'):self.assertFalse(public[key])
        self.assertEqual(self.observer._entries,{})
    async def test_foreign_source_or_sequence_is_rejected(self):
        for event in (Event(object(),1,'ACCEPTED',self.binding),Event(self.consumer.channel,2,'ACCEPTED',self.binding)):
            with self.assertRaises(NativeIngressRejected):self.consumer._receive(event)
        self.assertEqual(self.consumer.status()['activeProvenanceRecords'],0)
    async def test_duplicate_acceptance_not_overwritten(self):
        c=self.consumer.channel;c.emit('ACCEPTED',self.binding)
        with self.assertRaises(NativeIngressRejected):c.emit('ACCEPTED',self.binding)
        self.assertEqual(self.consumer.status()['activeProvenanceRecords'],1)
    async def test_binding_object_cannot_be_replaced_by_equal_value(self):
        c=self.consumer.channel;c.emit('ACCEPTED',self.binding)
        with self.assertRaises(NativeIngressRejected):c.emit('CREATED',replace(self.binding),self.task())
    async def test_out_of_order_return_is_not_success(self):
        c=self.consumer.channel;c.emit('ACCEPTED',self.binding)
        with self.assertRaises(NativeIngressRejected):c.emit('EXECUTION_RETURNED',self.binding,self.task())
    async def test_replaced_task_is_rejected(self):
        task=self.started()
        with self.assertRaises(NativeIngressRejected):self.consumer.channel.emit('EXECUTION_RETURNED',self.binding,self.task())
        self.assertFalse(task.done())
    async def test_completed_provenance_discards_task_reference(self):
        task=self.started();c=self.consumer.channel
        for phase in ('EXECUTION_RETURNED','RETIRED','DONE'):c.emit(phase,self.binding,task)
        self.assertEqual(self.consumer.status()['activeProvenanceRecords'],0);self.assertEqual(self.consumer.status()['completedDiagnosticCount'],1)
        self.assertTrue(all(not isinstance(v,asyncio.Task) for v in self.consumer._completed[0]))
        with self.assertRaises(NativeIngressRejected):self.consumer.binding_for('r',task)
    async def test_active_inventory_bounded_not_silently_evicted(self):
        c=self.consumer.channel
        for i in range(256):c.emit('ACCEPTED',Binding(run_id=str(i)))
        with self.assertRaises(NativeIngressRejected):c.emit('ACCEPTED',Binding(run_id='overflow'))
        self.assertEqual(self.consumer.status()['activeProvenanceRecords'],256)
    async def test_gap_or_replaced_channel_prevents_binding_access(self):
        task=self.started();self.consumer.channel.state='GAP'
        with self.assertRaises(NativeIngressRejected):self.consumer.binding_for('r',task)
        self.consumer.channel.state='OBSERVING';self.observer._adapter._run_observation_channel=object()
        with self.assertRaises(NativeIngressRejected):self.consumer.binding_for('r',task)
    async def test_finished_task_is_not_active_binding(self):
        task=self.started();task.cancel();await asyncio.gather(task,return_exceptions=True)
        with self.assertRaises(NativeIngressRejected):self.consumer.binding_for('r',task)
    async def test_bounded_completed_diagnostics_retain_no_request_keys(self):
        c=self.consumer.channel;task=self.task()
        for i in range(40):
            binding=Binding(run_id=str(i));c.emit('ACCEPTED',binding)
            for phase in ('CREATED','STARTED','RETIRED','DONE'):c.emit(phase,binding,task)
        self.assertEqual(len(self.consumer._completed),32);self.assertNotIn('fixture-private-key',str(self.consumer._completed))
if __name__=='__main__':unittest.main()
