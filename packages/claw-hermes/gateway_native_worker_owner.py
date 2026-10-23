"""Read actual native worker/request bindings without treating a carrier as an owner.

The native counted function alone records execution start/exit. This companion
reads that source-owned book, including a worker surviving carrier cancellation.
It neither feeds invented admissions to NativeTaskObserver nor relaxes its gates.
No I/O except the existing process-start identity check; no worker/Task mutation.
"""
from __future__ import annotations
from dataclasses import dataclass
import os
import time

from gateway_native_run_provenance import NativeRunProvenance

class WorkerOwnerRejected(RuntimeError):
    pass

class WorkerOwnerUnavailable(RuntimeError):
    pass

def require(ok, reason):
    if not ok:
        raise WorkerOwnerRejected(reason)

@dataclass(frozen=True, slots=True)
class WorkerBoundSnapshot:
    workers: tuple
    revision: int
    native_worker_count: int
    captured_ns: int

    def public(self):
        running = sum(w.state == 'RUNNING' for w in self.workers)
        submitted = sum(w.state == 'SUBMITTED' for w in self.workers)
        return {'state': 'NATIVE_WORKER_LIFETIMES_BOUND',
                'submittedNotYetEntered': submitted, 'enteredNotYetExited': running,
                'exitedAwaitingCarrier': len(self.workers) - submitted - running,
                'workersOutlivingCarrier': sum(w.carrier_done and w.finished_ns is None for w in self.workers),
                'unattributedNativeWorkers': self.native_worker_count - submitted - running,
                'workerLifetimeBound': True, 'snapshotOnly': True,
                'canonicalExecutorVerified': False, 'allAgentWorkObserved': False,
                'storageIntegrityVerified': False, 'serviceReadinessVerified': False,
                'runtimeAdmissionAuthorized': False, 'retryAuthorized': False,
                'storeReleaseAuthorized': False}

class NativeWorkerObserver:
    def __init__(self, provenance):
        from gateway.platforms.api_server_worker_observation import WorkerBook
        require(type(provenance) is NativeRunProvenance, 'worker_provenance_required')
        provenance._observer._usable()
        self._provenance = provenance
        self._observer = provenance._observer
        self._channel = provenance.channel
        self._book = self._channel._workers
        require(type(self._book) is WorkerBook, 'worker_native_book_required')
        self._identity = self._observer._identity
        self._fault = False
        self._reading = False
        self._check()

    def _check(self):
        from gateway.status import get_process_start_time
        self._observer._actor_check()
        p, ch, a = self._provenance, self._channel, self._observer._adapter
        require(not self._fault and self._observer._fault is None, 'worker_requires_reconciliation')
        require(p._observer is self._observer and p.channel is ch and a._run_observation_channel is ch
                and ch._workers is self._book and self._book._channel is ch,
                'worker_source_changed')
        require(ch.status()['state'] == 'OBSERVING' and p._last_sequence == ch._sequence,
                'worker_provenance_gap')
        require(self._identity == self._observer._reader.expected
                and self._identity.owner_pid == os.getpid() == a._run_owner_pid
                and self._identity.owner_started == a._run_owner_started == get_process_start_time(os.getpid()),
                'worker_process_identity_changed')
        stores = self._observer._bundle.select(a, self._observer._bundle.home)
        require(all(x is y for x, y in zip(stores, self._observer._reader._stores)), 'worker_store_owner_changed')

    def capture(self):
        from gateway.platforms.api_server_runs import api_worker_live_count
        from gateway.platforms.api_server_worker_observation import WorkerObservationRejected, WorkerObservationUnavailable
        require(not self._reading, 'worker_capture_reentrant')
        self._reading = True
        try:
            self._check()
            start = time.monotonic_ns()
            global_before = api_worker_live_count()
            revision, workers = self._book.capture()
            for w in workers:
                require(w.owner_pid == self._identity.owner_pid
                        and w.binding.execution_role == 'executor_thread_carrier', 'worker_binding_role_changed')
                if not w.carrier_released:
                    entry = self._provenance._active.get(w.binding.run_id)
                    require(entry is not None and entry[0] is w.binding, 'worker_ingress_binding_changed')
            global_after = api_worker_live_count()
            revision_after, after = self._book.capture()
            self._check()
            active = sum(w.finished_ns is None for w in workers)
            now = time.monotonic_ns()
            if (revision != revision_after or workers != after or global_before != global_after
                    or type(global_after) is not int or global_after < active
                    or not start <= now <= start + 5_000_000_000):
                raise WorkerOwnerUnavailable('worker_observation_changed')
            return WorkerBoundSnapshot(workers, revision, global_after, now)
        except (WorkerObservationUnavailable, WorkerOwnerUnavailable):
            raise WorkerOwnerUnavailable('worker_observation_unavailable') from None
        except (WorkerObservationRejected, WorkerOwnerRejected, ValueError, TypeError, KeyError, AttributeError, RuntimeError):
            self._fault = True
            raise WorkerOwnerRejected('worker_ownership_unconfirmed') from None
        finally:
            self._reading = False
