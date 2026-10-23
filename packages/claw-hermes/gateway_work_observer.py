"""Actual native run-task ownership observations, not a scheduler or HTTP gate.

The trusted producer publishes immutable request bindings at its commit boundary;
this observer never learns the expected request from candidate database rows.
It checks real Task objects and native registries before/after the existing
metadata reader. Source producer hooks and Linux profile/mount verification are
separate gates. No caller boolean can establish task liveness or completeness.
Only in-process keyed run tasks are supported; worker threads/other ingress fail
closed. No task is created, cancelled, awaited, resumed or removed by capture.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, replace
import os
import threading
import time

import gateway_work_health as policy
from gateway_work_health_reader import NativeWorkReader, CommittedWorkRows, WorkReadRejected, WorkReadUnavailable, digest

class TaskObservationRejected(RuntimeError):
    pass

class TaskObservationUnavailable(RuntimeError):
    pass

def need(ok, reason):
    if not ok:
        raise TaskObservationRejected(reason)

@dataclass(frozen=True, slots=True)
class RunRequestBinding:
    run_id: str
    scope: str
    key: str
    fingerprint: str

    def __post_init__(self):
        need(all(policy.text(v) for v in (self.run_id, self.scope, self.key)) and digest(self.fingerprint),
             'task_run_binding_invalid')

@dataclass(frozen=True, slots=True)
class ResponseRequestBinding:
    key: str
    fingerprint: str

    def __post_init__(self):
        need(policy.text(self.key) and digest(self.fingerprint), 'task_response_binding_invalid')

@dataclass(frozen=True, slots=True)
class TaskRequest:
    admission_id: str
    session_id: str
    epoch: int
    generation: int | None
    phase: str
    run: RunRequestBinding
    response: ResponseRequestBinding | None = None

    def __post_init__(self):
        need(policy.text(self.admission_id) and policy.text(self.session_id)
             and policy.integer(self.epoch, 1) and type(self.phase) is str
             and self.phase in ('QUEUED', 'RUNNING', 'SETTLING'), 'task_request_invalid')
        need((self.phase == 'QUEUED' and self.generation is None) or
             (self.phase != 'QUEUED' and policy.integer(self.generation, 1)), 'task_generation_invalid')
        need(type(self.run) is RunRequestBinding and
             (self.response is None or type(self.response) is ResponseRequestBinding), 'task_request_binding_type')

@dataclass(frozen=True, slots=True)
class TaskBoundRows:
    rows: CommittedWorkRows
    live_work: tuple[policy.LiveWork, ...]
    revision: int
    captured_ns: int
    draining: bool

    def public(self):
        return {'state': 'TASK_METADATA_BOUND', 'observedTasks': len(self.live_work),
                'producerRevision': self.revision, 'draining': self.draining,
                'realTaskStateObserved': True, 'requestBindingsMatched': True,
                'storageIntegrityVerifiedHere': False, 'nativeProducerHooksVerifiedHere': False,
                'serviceReadinessVerified': False, 'runtimeAdmissionAuthorized': False,
                'retryAuthorized': False, 'storeReleaseAuthorized': False}

# Exact pinned adapter inventory. No fallback to getattr(...,0/empty): a missing
# or malformed counter/container is unavailable evidence, never proof of idle.
_EMPTY_DICTS = ('_session_tasks', '_pending_text_batch_tasks', '_active_run_agents',
                '_shutdown_interruptible_agents', '_pending_messages', '_pending_text_batches',
                '_active_sessions', '_post_delivery_callbacks', '_text_debounce')
_EMPTY_SETS = ('_detached_fatal_tasks', '_expected_cancelled_tasks', '_stopping_run_ids',
               '_shutdown_interrupted_run_ids')

class NativeTaskObserver:
    """One observer bound to an actual native adapter, process, thread and loop.

    Registration/phase changes are trusted in-process producer calls, not exposed
    to serialized input. All capture work is synchronous and contains no await;
    this prevents cooperative loop interleaving, not hostile same-process writes
    or a cross-file atomic snapshot. Unqualified native executor threads refuse.
    """
    def __init__(self, adapter, reader):
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.platforms.api_server_borrowed import BorrowedAPIStores
        need(type(adapter) is APIServerAdapter and type(reader) is NativeWorkReader,
             'task_native_adapter_reader_required')
        bundle = adapter._borrowed_api_stores
        need(type(bundle) is BorrowedAPIStores, 'task_borrowed_bundle_required')
        self._adapter, self._reader, self._bundle = adapter, reader, bundle
        self._identity = reader.expected
        self._actor = (os.getpid(), threading.get_ident())
        self._loop = asyncio.get_running_loop()
        self._task_map = adapter._active_run_tasks
        self._background = adapter._background_tasks
        self._aliases = adapter._run_admission_aliases
        self._scopes = adapter._run_owners
        self._status_map = adapter._run_statuses
        self._entries = {}
        self._revision = 0
        self._reading = False
        self._draining = False
        self._fault = None
        self._actor_check()
        self._native_check()
        need(not self._task_map and not self._background, 'task_attach_requires_quiescence')

    def _actor_check(self):
        need((os.getpid(), threading.get_ident()) == self._actor, 'task_other_actor')
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise TaskObservationRejected('task_wrong_event_loop') from None
        need(loop is self._loop, 'task_wrong_event_loop')

    def _native_check(self):
        from gateway.status import get_process_start_time
        from gateway.platforms.api_server_runs import api_worker_live_count
        a = self._adapter
        need(a._borrowed_api_stores is self._bundle and self._reader.expected == self._identity,
             'task_owner_changed')
        stores = self._bundle.select(a, self._bundle.home)
        need(all(x is y for x, y in zip(stores, self._reader._stores)), 'task_store_mismatch')
        need(self._identity.owner_pid == os.getpid() == a._run_owner_pid
             and policy.integer(a._run_owner_started, 1)
             and a._run_owner_started == self._identity.owner_started == get_process_start_time(os.getpid()),
             'task_process_identity_changed')
        need(a._active_run_tasks is self._task_map and type(self._task_map) is dict
             and a._background_tasks is self._background and type(self._background) is set
             and a._run_admission_aliases is self._aliases and type(self._aliases) is dict
             and a._run_owners is self._scopes and type(self._scopes) is dict
             and a._run_statuses is self._status_map and type(self._status_map) is dict,
             'task_registry_replaced')
        for name in ('_pending_agent_requests', '_inflight_agent_runs'):
            value = getattr(a, name)
            need(type(value) is int and value == 0, 'task_other_ingress_active_or_unknown')
        count = api_worker_live_count()
        need(type(count) is int and count == 0, 'task_native_worker_unqualified')
        for name in _EMPTY_DICTS:
            value = getattr(a, name)
            need(type(value) is dict and not value, 'task_other_ingress_active_or_unknown')
        for name in _EMPTY_SETS:
            value = getattr(a, name)
            need(type(value) is set and not value, 'task_other_ingress_active_or_unknown')
        need(a._site is None and a._runner is None and a._app is None
             and a._running is False and a._fatal_error_code is None,
             'task_native_listener_or_fatal_state')
        need(a._run_shutdown_requested_at is None, 'task_native_shutdown_in_progress')

    def _usable(self):
        self._actor_check()
        need(self._fault is None, 'task_observer_requires_reconciliation')
        need(not self._reading, 'task_observation_reentrant')

    def publish(self, task, request):
        """Register after the producer put this exact Task in its native run map.

        No database write or scheduling is performed. Expected bindings must come
        from the authenticated request/committed admission producer, not this reader.
        """
        self._usable()
        need(not self._draining, 'task_observer_draining')
        need(type(request) is TaskRequest and type(task) is asyncio.Task, 'task_publish_types')
        need(request.epoch == self._identity.epoch, 'task_publish_epoch')
        need(len(self._entries) < policy.MAX_ROWS and request.run.run_id not in self._entries,
             'task_publish_duplicate_or_limit')
        need(all(old.admission_id != request.admission_id and t is not task
                 for t, old in self._entries.values()), 'task_publish_duplicate_owner')
        need(task.get_loop() is self._loop and not task.done() and task.cancelling() == 0,
             'task_publish_not_live')
        need(self._task_map.get(request.run.run_id) is task and task in self._background,
             'task_not_in_native_registry')
        self._entries[request.run.run_id] = (task, request)
        self._revision += 1

    def advance(self, run_id, *, phase, generation):
        self._usable()
        need(run_id in self._entries, 'task_transition_missing')
        task, old = self._entries[run_id]
        need(asyncio.current_task() is task, 'task_transition_not_owner')
        allowed = {'QUEUED': 'RUNNING', 'RUNNING': 'SETTLING'}
        need(allowed.get(old.phase) == phase, 'task_transition_invalid')
        need(old.generation is None or old.generation == generation, 'task_generation_changed')
        request = replace(old, phase=phase, generation=generation)
        self._entries[run_id] = (task, request)
        self._revision += 1

    def request_drain(self):
        self._usable()
        if not self._draining:
            self._draining = True
            self._revision += 1

    def _inventory(self, *, retiring=None):
        self._native_check()
        need(len(self._task_map) <= policy.MAX_ROWS and set(self._task_map) == set(self._entries) - ({retiring} if retiring is not None else set()),
             'task_registry_incomplete')
        tasks = set()
        owners = []
        stamp = []
        for run_id, (task, request) in self._entries.items():
            if run_id == retiring:
                continue
            need(type(task) is asyncio.Task and self._task_map[run_id] is task
                 and task.get_loop() is self._loop, 'task_registry_identity_changed')
            need(not task.done() and not task.cancelled() and task.cancelling() == 0,
                 'task_owner_gone_or_cancelling')
            need(self._aliases.get(run_id) == request.admission_id and
                 self._scopes.get(run_id) == request.run.scope, 'task_native_identity_changed')
            status = self._status_map.get(run_id)
            need(type(status) is dict and status.get('run_id') == run_id
                 and status.get('session_id') == request.session_id, 'task_native_status_identity')
            allowed = {'QUEUED': {'queued'}, 'RUNNING': {'running'},
                       'SETTLING': {'running'} | policy.TERMINAL_RUNS}[request.phase]
            need(type(status.get('status')) is str and status['status'] in allowed,
                 'task_native_status_phase')
            tasks.add(task)
            owners.append(policy.LiveWork(request.admission_id, request.session_id, request.epoch,
                request.generation, request.phase, True, run_id,
                request.response.key if request.response else None))
            stamp.append((run_id, task, request, id(status), status['status'], task.cancelling()))
        need(self._background == tasks, 'task_background_inventory_incomplete')
        return tuple(owners), (self._revision, tuple(stamp), frozenset(tasks), self._draining)

    def capture(self):
        """Read actual tasks and metadata without accepting caller health flags."""
        self._usable()
        self._reading = True
        try:
            before_ns = time.monotonic_ns()
            owners, before = self._inventory()
            rows = self._reader.capture(live_work=owners)
            need(type(rows) is CommittedWorkRows and rows.identity == self._identity,
                 'task_rows_identity')
            expected_runs = {r.run.run_id: (r.run.run_id, r.run.scope, r.run.key, r.run.fingerprint)
                             for _, r in self._entries.values()}
            actual_runs = {r[0]: r for r in rows.run_bindings}
            need(len(actual_runs) == len(rows.run_bindings)
                 and all(actual_runs.get(k) == v for k, v in expected_runs.items()), 'task_run_binding_mismatch')
            expected_responses = {r.response.key: r.response.fingerprint
                                  for _, r in self._entries.values() if r.response is not None}
            actual_responses = dict(rows.response_fingerprints)
            need(len(actual_responses) == len(rows.response_fingerprints)
                 and all(actual_responses.get(k) == v for k, v in expected_responses.items()),
                 'task_response_fingerprint_mismatch')
            after_owners, after = self._inventory()
            now = time.monotonic_ns()
            if before != after or owners != after_owners or not before_ns <= rows.captured_ns <= now:
                raise TaskObservationUnavailable('task_changed_during_observation')
            if now - before_ns > 5_000_000_000:
                raise TaskObservationUnavailable('task_observation_expired')
            return TaskBoundRows(rows, owners, self._revision, now, self._draining)
        except (WorkReadUnavailable, TaskObservationUnavailable):
            raise TaskObservationUnavailable('task_observation_unavailable') from None
        except (WorkReadRejected, TaskObservationRejected, ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            self._fault = 'task_ownership_or_binding_unconfirmed'
            raise TaskObservationRejected(self._fault) from None
        finally:
            self._reading = False

    def retire_completed(self, run_id):
        """Forget only this observation after actual success and committed settlement.

        The native producer must already have removed its Task/background entry.
        This method never cancels a task or removes native registries/DB records.
        Cancellation, task exception or partial settlement cannot be acknowledged
        as clean completion. No authority to close stores/profile is returned.
        """
        self._usable()
        need(policy.text(run_id) and run_id in self._entries, 'task_retire_missing')
        self._reading = True
        try:
            task, request = self._entries[run_id]
            need(request.phase == 'SETTLING' and task.done() and not task.cancelled()
                 and task.cancelling() == 0, 'task_retire_not_complete')
            need(task.exception() is None, 'task_retire_failed')
            need(run_id not in self._task_map and task not in self._background,
                 'task_native_retirement_pending')
            before_ns = time.monotonic_ns()
            remaining, before = self._inventory(retiring=run_id)
            selector = policy.LiveWork(request.admission_id, request.session_id,
                request.epoch, request.generation, 'SETTLING', False, run_id,
                request.response.key if request.response else None)
            rows = self._reader.capture(live_work=remaining + (selector,))
            need(type(rows) is CommittedWorkRows and rows.identity == self._identity,
                 'task_retire_runtime_changed')
            admissions = [a for a in rows.admissions if a.admission_id == request.admission_id]
            need(len(admissions) == 1, 'task_retire_admission_missing')
            a = admissions[0]
            need((a.session_id, a.status, a.owner_epoch, a.generation, a.session_generation) ==
                 (request.session_id, 'terminal', request.epoch, request.generation, request.generation),
                 'task_retire_admission_unsettled')
            runs = [r for r in rows.runs if r.run_id == run_id]
            need(len(runs) == 1 and policy._run_status(runs[0].status_json) in policy.TERMINAL_RUNS
                 and (runs[0].owner_pid, runs[0].owner_started) ==
                 (self._identity.owner_pid, self._identity.owner_started), 'task_retire_run_unsettled')
            need([r for r in rows.run_bindings if r[0] == run_id] ==
                 [(run_id, request.run.scope, request.run.key, request.run.fingerprint)],
                 'task_retire_run_binding_mismatch')
            if request.response is not None:
                responses = [r for r in rows.responses if r.request_key == request.response.key]
                need(len(responses) == 1 and responses[0].admission_id == request.admission_id
                     and responses[0].settled is True, 'task_retire_response_unsettled')
                need([r for r in rows.response_fingerprints if r[0] == request.response.key] ==
                     [(request.response.key, request.response.fingerprint)], 'task_retire_response_binding_mismatch')
            need(rows.unresolved_workers == 0, 'task_retire_worker_unqualified')
            status = self._status_map.get(run_id)
            need(type(status) is dict and status.get('run_id') == run_id
                 and status.get('session_id') == request.session_id
                 and status.get('status') in policy.TERMINAL_RUNS, 'task_retire_native_status')
            after_remaining, after = self._inventory(retiring=run_id)
            now = time.monotonic_ns()
            if before != after or remaining != after_remaining or not before_ns <= rows.captured_ns <= now:
                raise TaskObservationUnavailable('task_retire_changed_during_observation')
            if now - before_ns > 5_000_000_000:
                raise TaskObservationUnavailable('task_retire_observation_expired')
            need(self._entries.get(run_id) == (task, request) and run_id not in self._task_map
                 and task not in self._background, 'task_retire_owner_changed')
            del self._entries[run_id]
            self._revision += 1
            return {'state': 'TASK_OBSERVATION_RETIRED', 'producerRevision': self._revision,
                    'nativeTaskRemovedHere': False, 'databaseWritesPerformed': False,
                    'runtimeAdmissionAuthorized': False, 'storeReleaseAuthorized': False}
        except (WorkReadUnavailable, TaskObservationUnavailable):
            raise TaskObservationUnavailable('task_retirement_unavailable') from None
        except (WorkReadRejected, TaskObservationRejected, ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            self._fault = 'task_retirement_unconfirmed'
            raise TaskObservationRejected(self._fault) from None
        finally:
            self._reading = False
