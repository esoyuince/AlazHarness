"""Native ingress provenance companion to the existing Task observer.

This consumer never promotes a watcher or thread carrier to a canonical executor.
It does not modify the observer's owner registry or grant health/admission. Only
source-generated immutable request identities and native lifecycle order are bound.
"""
from collections import deque
from dataclasses import dataclass
import asyncio

class NativeIngressRejected(RuntimeError):
    pass

@dataclass(frozen=True, slots=True)
class ProducerBinding:
    native_binding: object
    task: asyncio.Task

    def public(self):
        return {'state': 'NATIVE_RUN_PROVENANCE',
                'executionRole': self.native_binding.execution_role,
                'keyedRequest': self.native_binding.key is not None,
                'nativeProducerNotificationsObserved': True,
                'canonicalExecutorVerified': False, 'serviceReadinessVerified': False,
                'runtimeAdmissionAuthorized': False, 'storeReleaseAuthorized': False}

class NativeRunProvenance:
    def __init__(self, observer):
        from gateway_work_observer import NativeTaskObserver
        from gateway.platforms.api_server_run_observation import RunLifecycleChannel
        if type(observer) is not NativeTaskObserver:
            raise NativeIngressRejected('ingress_observer_required')
        observer._usable()
        if observer._entries:
            raise NativeIngressRejected('ingress_attach_requires_quiescence')
        self._observer = observer
        self._active = {}
        self._completed = deque(maxlen=32)
        self._last_sequence = 0
        self.channel = RunLifecycleChannel(observer._adapter, self._receive)

    def _receive(self, event):
        from gateway.platforms.api_server_run_observation import RunProducerEvent
        if (type(event) is not RunProducerEvent or event.source is not self.channel
                or event.sequence != self._last_sequence + 1):
            raise NativeIngressRejected('ingress_sequence_or_source_gap')
        binding, run_id = event.binding, event.binding.run_id
        if event.phase == 'ACCEPTED':
            if run_id in self._active or len(self._active) >= 256:
                raise NativeIngressRejected('ingress_inventory_limit_or_duplicate')
            self._active[run_id] = [binding, None, 'ACCEPTED']
        else:
            value = self._active.get(run_id)
            if value is None or value[0] is not binding:
                raise NativeIngressRejected('ingress_binding_changed')
            allowed = {'ACCEPTED': ('CREATED',), 'CREATED': ('STARTED',),
                       'STARTED': ('EXECUTION_RETURNED', 'RETIRED'),
                       'EXECUTION_RETURNED': ('RETIRED',), 'RETIRED': ('DONE',)}
            if event.phase not in allowed.get(value[2], ()):
                raise NativeIngressRejected('ingress_phase_gap')
            if event.phase == 'CREATED':
                if type(event.task) is not asyncio.Task:
                    raise NativeIngressRejected('ingress_task_required')
                value[1] = event.task
            elif value[1] is not event.task:
                raise NativeIngressRejected('ingress_task_changed')
            value[2] = event.phase
            if event.phase == 'DONE':
                self._completed.append((binding.execution_role, event.native_status,
                                        event.task_cancelled, event.worker_count))
                del self._active[run_id]
        self._last_sequence = event.sequence

    def binding_for(self, run_id, task):
        self._observer._actor_check()
        if (self.channel.status()['state'] != 'OBSERVING'
                or self._observer._adapter._run_observation_channel is not self.channel):
            raise NativeIngressRejected('ingress_observation_gap')
        entry = self._active.get(run_id)
        if entry is None or entry[1] is not task or task.done():
            raise NativeIngressRejected('ingress_task_not_active')
        return ProducerBinding(entry[0], task)

    def status(self):
        return {'channel': self.channel.status(), 'activeProvenanceRecords': len(self._active),
                'completedDiagnosticCount': len(self._completed),
                'nativeProducerNotificationsObserved': self._last_sequence > 0,
                'canonicalExecutorVerified': False, 'serviceReadinessVerified': False,
                'runtimeAdmissionAuthorized': False, 'storeReleaseAuthorized': False}
