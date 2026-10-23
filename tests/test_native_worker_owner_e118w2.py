"""Worker companion contracts with explicit native/process boundary doubles.
Actual native counted threads are exercised separately in e118w2_native_workers.
"""
import os,sys,types,unittest
from dataclasses import dataclass,replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'packages/claw-hermes'))
import gateway_native_worker_owner as g
from gateway_native_run_provenance import NativeRunProvenance
class NativeRejected(RuntimeError):pass
class NativeUnavailable(RuntimeError):pass
class Book:
    def capture(self):return self.values
@dataclass(frozen=True)
class Row:
    binding:object
    state:str='RUNNING'
    owner_pid:int=os.getpid()
    finished_ns:int|None=None
    carrier_done:bool=False
    carrier_released:bool=False
class WorkerContracts(unittest.TestCase):
    def setUp(self):
        self.count=Mock(return_value=1)
        source=types.ModuleType('gateway.platforms.api_server_worker_observation')
        source.WorkerBook=Book;source.WorkerObservationRejected=NativeRejected;source.WorkerObservationUnavailable=NativeUnavailable
        runs=types.ModuleType('gateway.platforms.api_server_runs');runs.api_worker_live_count=self.count
        status=types.ModuleType('gateway.status');status.get_process_start_time=lambda pid:77
        self.modules=patch.dict(sys.modules,{source.__name__:source,runs.__name__:runs,status.__name__:status});self.modules.start();self.addCleanup(self.modules.stop)
        self.identity=NS(owner_pid=os.getpid(),owner_started=77)
        self.stores=(object(),object(),object());self.adapter=NS(_run_owner_pid=os.getpid(),_run_owner_started=77)
        self.observer=NS(_usable=lambda:None,_actor_check=lambda:None,_adapter=self.adapter,_identity=self.identity,_fault=None,
            _reader=NS(expected=self.identity,_stores=self.stores),_bundle=NS(home='fixture',select=lambda *args:self.stores))
        self.channel=NS(_sequence=3,status=lambda:{'state':'OBSERVING'})
        self.book=Book();self.book._channel=self.channel;self.channel._workers=self.book
        self.adapter._run_observation_channel=self.channel
        self.provenance=NativeRunProvenance.__new__(NativeRunProvenance)
        self.provenance._observer=self.observer;self.provenance.channel=self.channel;self.provenance._last_sequence=3
        self.binding=NS(run_id='private-run',key='private-key',execution_role='executor_thread_carrier')
        self.provenance._active={'private-run':[self.binding,object(),'STARTED']}
        self.row=Row(self.binding);self.book.values=(4,(self.row,));self.owner=g.NativeWorkerObserver(self.provenance)
    def test_running_output_has_no_authority_or_private_request(self):
        out=self.owner.capture().public();self.assertEqual(out['enteredNotYetExited'],1)
        for key in ('canonicalExecutorVerified','allAgentWorkObserved','storageIntegrityVerified','serviceReadinessVerified','runtimeAdmissionAuthorized','retryAuthorized','storeReleaseAuthorized'):self.assertFalse(out[key])
        self.assertNotIn('private',str(out))
    def test_empty_snapshot_is_not_service_idle_or_close_permission(self):
        self.book.values=(4,());self.count.return_value=0
        out=self.owner.capture().public();self.assertEqual(out['enteredNotYetExited'],0);self.assertFalse(out['storeReleaseAuthorized'])
    def test_source_replacement_latches_refusal(self):
        self.adapter._run_observation_channel=object()
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
        self.adapter._run_observation_channel=self.channel
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
    def test_sequence_gap_refused(self):
        self.channel._sequence=4
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
    def test_changed_worker_book_revision_is_transient_unavailable(self):
        self.book.capture=Mock(side_effect=[(4,(self.row,)),(5,(self.row,))])
        with self.assertRaises(g.WorkerOwnerUnavailable):self.owner.capture()
        self.book.capture=lambda:(5,(self.row,));self.assertEqual(self.owner.capture().revision,5)
    def test_native_count_race_does_not_return_positive(self):
        self.count.side_effect=[1,0]
        with self.assertRaises(g.WorkerOwnerUnavailable):self.owner.capture()
    def test_count_less_than_bound_work_is_not_empty(self):
        self.count.return_value=0
        with self.assertRaises(g.WorkerOwnerUnavailable):self.owner.capture()
    def test_other_native_work_is_explicit_not_claimed_as_this_request(self):
        self.count.return_value=2;out=self.owner.capture().public()
        self.assertEqual(out['unattributedNativeWorkers'],1);self.assertFalse(out['allAgentWorkObserved'])
    def test_retired_carrier_does_not_remove_running_worker_proof(self):
        self.book.values=(5,(replace(self.row,carrier_done=True,carrier_released=True),));self.provenance._active.clear()
        self.assertEqual(self.owner.capture().public()['workersOutlivingCarrier'],1)
    def test_equal_but_different_request_binding_not_adopted(self):
        self.book.values=(5,(replace(self.row,binding=NS(**vars(self.binding))),))
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
    def test_contention_does_not_latch_or_mutate_store(self):
        self.book.capture=Mock(side_effect=NativeUnavailable('busy'))
        with self.assertRaises(g.WorkerOwnerUnavailable):self.owner.capture()
        self.book.capture=lambda:(4,(self.row,));self.assertEqual(len(self.owner.capture().workers),1)
    def test_process_restart_and_store_owner_change_refused(self):
        self.adapter._run_owner_started=78
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
    def test_false_role_is_not_promoted_to_local_worker(self):
        self.binding.execution_role='canonical_authority_observer'
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
    def test_no_generic_provenance_or_reentrant_read(self):
        with self.assertRaises(g.WorkerOwnerRejected):g.NativeWorkerObserver(object())
        self.owner._reading=True
        with self.assertRaises(g.WorkerOwnerRejected):self.owner.capture()
if __name__=='__main__':unittest.main()
