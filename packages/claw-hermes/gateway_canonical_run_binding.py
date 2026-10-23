"""Named native API request -> canonical claim correlation, not service readiness.

Uses the existing RunLifecycleChannel and SessionAuthority registries/committed
rows. No scheduler, native hook replacement, work admission or borrowed-runner
exception is introduced. Supported only on the normal non-borrowed authority
path. An adopted agent reference is NOT proof of a physical worker's completion.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sqlite3
import threading
import time

import gateway_live_store_gate as live
import gateway_work_health as health
from gateway_work_health_reader import digest

class CanonicalBindingRejected(RuntimeError):
    pass

class CanonicalBindingUnavailable(RuntimeError):
    pass

def require(ok, reason):
    if not ok:
        raise CanonicalBindingRejected(reason)

# Critical source seams must match the qualified native feature before attach.
NATIVE_FEATURE = '943210584828ccfcfd6adc8eb966ecaa8ca18429'
NATIVE_SOURCE_HASHES = {'gateway/session_authority.py': '035d5a5dee4090bbd85b275a9b33981d8d1378730b9400319a8cf7bf5a0bdff8', 'gateway/session_api_turn.py': 'feb785e12a153024b929efdf850ac69572342def6ddf3790d96473f4b140a63f', 'gateway/platforms/api_server_run_observation.py': 'a3761430afb716f28cf6d2cfa13805d88b20b21829abdb121920442a786f9c01', 'gateway/platforms/api_server_runs.py': '058d4e883cce5283e796335f52f16381a6891a940c1c3a8bd5257de70b9e00eb', 'gateway/session_runtime_workers.py': '3feea3bc6e0e452f0ad049343242d9b2499595d752e2a74cf77bd2fdeb9e877b'}

def _qualified_source():
    import hashlib, importlib
    for name, expected in NATIVE_SOURCE_HASHES.items():
        module = importlib.import_module(name[:-3].replace('/', '.'))
        path = Path(module.__file__).resolve()
        require(path.suffix == '.py' and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                'canonical_native_source_unqualified')

def json_object(raw):
    require(type(raw) is str and len(raw) <= 65536 and len(raw.encode('utf-8')) <= 65536,
            'canonical_json_bound')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'canonical_json_duplicate')
            result[key] = value
        return result
    def constant(_):
        raise CanonicalBindingRejected('canonical_json_nonfinite')
    def finite_number(value):
        import math
        number = float(value)
        require(math.isfinite(number), 'canonical_json_nonfinite')
        return number
    value = json.loads(raw, object_pairs_hook=unique, parse_constant=constant, parse_float=finite_number)
    require(type(value) is dict, 'canonical_json_object')
    return value

@dataclass(frozen=True, slots=True)
class CanonicalClaimSnapshot:
    admission_id: str = field(repr=False)
    run_id: str = field(repr=False)
    session_id: str = field(repr=False)
    epoch: int
    generation: int | None
    phase: str
    adopted_agent_observed: bool
    authority_task_live: bool
    carrier_done: bool
    carrier_cancelled: bool
    replay_terminal: bool
    draining: bool
    captured_ns: int

    def public(self):
        return {'state': 'CANONICAL_REQUEST_CORRELATED', 'phase': self.phase,
                'generation': self.generation, 'authorityTaskLive': self.authority_task_live,
                'adoptedAgentObserved': self.adopted_agent_observed,
                'carrierDone': self.carrier_done, 'carrierCancelled': self.carrier_cancelled,
                'apiReplayTerminal': self.replay_terminal,
                'draining': self.draining, 'requestBindingMatched': True,
                'canonicalClaimMatched': self.phase == 'CLAIMED', 'snapshotOnly': True,
                'admissionPayloadDigestVerified': False,
                'physicalWorkerHealthVerified': False, 'allAgentWorkObserved': False,
                'storageProfileMountVerified': False, 'serviceReadinessVerified': False,
                'runtimeAdmissionAuthorized': False, 'retryAuthorized': False,
                'storeReleaseAuthorized': False}

@dataclass(slots=True)
class _Entry:
    binding: object
    live: object
    stream: object
    stream_lock: object
    carrier: object = None
    carrier_done: bool = False
    carrier_cancelled: bool = False
    phase: str = 'ACCEPTED'
    claimed_task: object = None
    claimed_generation: int | None = None

class NativeCanonicalBinding:
    """Read source identity and native claim without adopting or executing it.

    One named canonical request at a time; no empty-inventory health verdict.
    Native admission/claim/adoption/settlement remain the authority's responsibility.
    Source notifications are automatic. Explicit release removes only this
    diagnostic entry after terminal commit and native carrier retirement.
    """
    def __init__(self, adapter, authority, expected, *, schema_hashes):
        from gateway.platforms.api_server import APIServerAdapter
        from gateway.session_authority import SessionAuthority
        from gateway.platforms.api_server_run_observation import RunLifecycleChannel
        from hermes_state import SessionDB
        from gateway.platforms.api_server_run_idempotency import RunIdempotencyStore
        require(type(adapter) is APIServerAdapter and type(authority) is SessionAuthority,
                'canonical_native_objects_required')
        require(adapter._borrowed_api_stores is None, 'canonical_borrowed_path_not_qualified')
        require(type(expected) is health.RuntimeIdentity and expected.owner_pid == os.getpid(),
                'canonical_expected_identity')
        require(type(schema_hashes) is tuple and len(schema_hashes) == 2
                and all(digest(v) for v in schema_hashes), 'canonical_schema_pins')
        require(type(authority.db) is SessionDB and
                type(adapter._run_idempotency_store) is RunIdempotencyStore, 'canonical_native_stores')
        _qualified_source()
        self._adapter, self._authority, self._runner = adapter, authority, authority.runner
        self._expected, self._schemas = expected, schema_hashes
        self._state, self._replay = authority.db, adapter._run_idempotency_store
        self._connections = (self._state._conn, self._replay._conn)
        self._locks = (self._state._lock, self._replay._lock)
        self._home = Path(self._state.db_path).parent
        require(self._home.is_absolute() and self._locks[0] is not self._locks[1], 'canonical_paths_or_locks')
        self._paths = (self._home/'state.db', self._home/'runs_idempotency.db')
        self._response = adapter._response_store
        self._sessions = authority.sessions
        self._task_map, self._background = adapter._active_run_tasks, adapter._background_tasks
        self._actor, self._loop = (os.getpid(), threading.get_ident()), asyncio.get_running_loop()
        self._entries, self._last_sequence = {}, 0
        self._fault, self._reading = None, False
        self._check(source=False)
        require(not any(v.task is not None and not v.task.done() for v in self._sessions.values())
                and not authority.executing and not authority.adopted, 'canonical_attach_requires_quiescence')
        self.channel = RunLifecycleChannel(adapter, self._receive)

    def _check(self, *, source=True):
        from gateway.session_authorities import active_authority
        from gateway.status import get_process_start_time
        require((os.getpid(), threading.get_ident()) == self._actor
                and asyncio.get_running_loop() is self._loop, 'canonical_other_actor')
        a, authority, e = self._adapter, self._authority, self._expected
        require(self._fault is None, 'canonical_requires_reconciliation')
        require(a._borrowed_api_stores is None and a.gateway_runner is self._runner
                and authority.runner is self._runner and active_authority(self._runner) is authority,
                'canonical_authority_replaced')
        require(authority.db is self._state and authority.sessions is self._sessions
                and a._run_idempotency_store is self._replay and a._response_store is self._response,
                'canonical_store_or_registry_changed')
        require(a._active_run_tasks is self._task_map and a._background_tasks is self._background,
                'canonical_carrier_registry_replaced')
        require(authority.epoch == e.epoch and authority.instance_id == e.instance_id
                and authority.profile_id == str(self._home) and not authority.retired,
                'canonical_authority_generation_changed')
        require(e.owner_pid == a._run_owner_pid == os.getpid()
                and e.owner_started == a._run_owner_started == get_process_start_time(os.getpid()),
                'canonical_process_identity_changed')
        require(a._site is None and a._runner is None and a._app is None,
                'canonical_listener_not_qualified')
        require(self._state._conn is self._connections[0] and self._replay._conn is self._connections[1]
                and self._state._lock is self._locks[0] and self._replay._lock is self._locks[1],
                'canonical_connection_changed')
        require((Path(self._state.db_path), Path(self._replay._db_path)) == self._paths
                and self._state.read_only is False and self._replay.durable is True,
                'canonical_store_path_changed')
        if source:
            require(a._run_observation_channel is self.channel
                    and self.channel.status()['state'] == 'OBSERVING'
                    and self._last_sequence == self.channel._sequence, 'canonical_source_gap')

    def _receive(self, event):
        from gateway.platforms.api_server_run_observation import RunProducerEvent
        require(type(event) is RunProducerEvent and event.source is self.channel
                and event.sequence == self._last_sequence + 1, 'canonical_event_source_gap')
        binding, run_id = event.binding, event.binding.run_id
        if event.phase == 'ACCEPTED':
            require(run_id not in self._entries and len(self._entries) < health.MAX_ROWS,
                    'canonical_record_limit_or_duplicate')
            node = self._sessions.get(binding.canonical_session_id)
            self._entries[run_id] = _Entry(binding, node, node.event_stream if node else None,
                                          node.event_stream.lock if node else None)
        else:
            entry = self._entries.get(run_id)
            require(entry is not None and entry.binding is binding, 'canonical_event_binding_changed')
            if event.phase == 'CREATED':
                require(entry.carrier is None and type(event.task) is asyncio.Task, 'canonical_event_task')
                entry.carrier = event.task
            else:
                require(entry.carrier is event.task, 'canonical_event_task_changed')
            entry.phase = event.phase
            if event.phase == 'DONE':
                entry.carrier_done, entry.carrier_cancelled = event.task_done, event.task_cancelled
                entry.carrier = None
                if binding.execution_role != 'canonical_authority_observer' or binding.key is None:
                    del self._entries[run_id]
        self._last_sequence = event.sequence

    def _runtime(self, sc):
        e = self._expected
        epoch = [tuple(r) for r in sc.execute(
            'SELECT epoch,instance_id FROM main.runtime_epoch WHERE singleton=1').fetchmany(2)]
        store = sc.execute("SELECT value FROM main.state_meta WHERE key='store_instance_id'").fetchone()
        require(epoch == [(e.epoch,e.instance_id)] and store is not None
                and store[0] == e.store_instance_id, 'canonical_runtime_changed')

    def _rows(self, entry):
        sc, rc = self._connections
        b = entry.binding
        rows = sc.execute('SELECT a.admission_id,a.target_session_id,a.request_id,a.principal_id,'
            'a.status,a.owner_epoch,a.generation,s.runtime_generation,'
            'CASE WHEN length(CAST(a.payload_json AS BLOB))<=65536 THEN a.payload_json ELSE NULL END '
            'FROM main.session_admissions a JOIN main.sessions s ON s.id=a.target_session_id '
            'WHERE a.admission_id=? LIMIT 2', (b.admission_id,)).fetchmany(2)
        require(len(rows) == 1, 'canonical_admission_missing')
        aid,sid,rid,principal,status,epoch,generation,current_generation,raw = tuple(rows[0])
        require((aid,sid,rid,principal,epoch) == (b.admission_id,b.canonical_session_id,b.run_id,'api',self._expected.epoch),
                'canonical_admission_identity')
        payload = json_object(raw)
        api = payload.get('api_turn_v1')
        require(type(api) is dict and api.get('run_owner_scope') == b.scope, 'canonical_admission_scope')
        runs = rc.execute('SELECT run_id,scope,idempotency_key,fingerprint,owner_pid,owner_started,'
            'CASE WHEN length(CAST(status_json AS BLOB))<=65536 THEN status_json ELSE NULL END '
            'FROM main.run_idempotency WHERE run_id=? LIMIT 2', (b.run_id,)).fetchmany(2)
        require(len(runs) == 1, 'canonical_replay_missing')
        row = tuple(runs[0])
        require(row[:6] == (b.run_id,b.scope,b.key,b.fingerprint,self._expected.owner_pid,self._expected.owner_started),
                'canonical_request_binding_changed')
        run_status = json_object(row[6])
        require(run_status.get('run_id') == b.run_id and run_status.get('session_id') == b.session_id,
                'canonical_replay_status_identity')
        require(run_status.get('status') in health.ACTIVE_RUNS | health.TERMINAL_RUNS,
                'canonical_replay_status_invalid')
        return status,generation,current_generation,run_status['status']

    def capture(self, run_id):
        require(health.text(run_id) and run_id in self._entries, 'canonical_request_not_observed')
        require(not self._reading, 'canonical_reentrant')
        self._reading = True
        acquired = []
        try:
            self._check()
            entry = self._entries[run_id];b = entry.binding
            require(b.execution_role == 'canonical_authority_observer' and health.text(b.key)
                    and digest(b.fingerprint) and b.admission_epoch == self._expected.epoch,
                    'canonical_request_not_qualified')
            node = entry.live
            require(node is not None and self._sessions.get(b.canonical_session_id) is node
                    and node.event_stream is entry.stream and node.event_stream.lock is entry.stream_lock,
                    'canonical_session_replaced')
            for lock in (entry.stream_lock,*self._locks):
                if not lock.acquire(blocking=False):
                    raise CanonicalBindingUnavailable('canonical_observation_contended')
                acquired.append(lock)
            if any(c.in_transaction for c in self._connections):
                raise CanonicalBindingUnavailable('canonical_transaction_active')
            start = time.monotonic_ns()
            seen = [live._connection(c,p,h,'delete') for c,p,h in zip(self._connections,self._paths,self._schemas)]
            self._runtime(self._connections[0])
            status,generation,current_generation,run_status = self._rows(entry)
            task = node.task
            task_live = type(task) is asyncio.Task and task.get_loop() is self._loop and not task.done() and not task.cancelling()
            adopted = self._authority.adopted.get(b.canonical_session_id)
            stamp = dict(entry.stream.execution)
            if b.admission_id in node.settling:
                raise CanonicalBindingUnavailable('canonical_settlement_in_progress')
            if status == 'queued':
                require(generation is None, 'canonical_queued_generation')
                phase,has_agent,owns_task = 'QUEUED',False,False
            elif status == 'started':
                require(health.integer(generation,1) and generation == current_generation,
                        'canonical_claim_generation_changed')
                require(stamp == {'authority_epoch':self._expected.epoch,'execution_generation':generation,'admission_id':b.admission_id},
                        'canonical_execution_stamp_mismatch')
                executing = self._authority.executing.get(b.canonical_session_id)
                if executing is None and task_live:
                    raise CanonicalBindingUnavailable('canonical_execution_returned_pending_settlement')
                require(executing == generation, 'canonical_execution_generation_mismatch')
                require(task_live and task is not entry.carrier, 'canonical_owner_task_unconfirmed')
                coro = task.get_coro();frame = getattr(coro, 'cr_frame', None)
                from gateway.session_authority import SessionAuthority
                require(getattr(coro, 'cr_code', None) is SessionAuthority._drain.__code__
                        and frame is not None and frame.f_locals.get('self') is self._authority,
                        'canonical_not_native_drain_task')
                task_ref = frame.f_locals.get('ref')
                require(getattr(task_ref, 'profile_id', None) == self._authority.profile_id
                        and getattr(task_ref, 'session_id', None) == b.canonical_session_id,
                        'canonical_task_route_mismatch')
                require(entry.claimed_task is None or (entry.claimed_task is task and entry.claimed_generation == generation),
                        'canonical_claim_owner_changed')
                require(adopted is None or (type(adopted) is tuple and len(adopted)==2
                        and adopted[0]==generation and adopted[1] is not None), 'canonical_adopted_generation_changed')
                phase,has_agent,owns_task = 'CLAIMED',adopted is not None,True
            elif status == 'terminal':
                require(generation is None or health.integer(generation,1), 'canonical_terminal_generation')
                if stamp.get('admission_id') == b.admission_id:
                    raise CanonicalBindingUnavailable('canonical_terminal_publication_pending')
                phase,has_agent,owns_task = 'SETTLED',False,False
            else:
                raise CanonicalBindingRejected('canonical_outcome_requires_reconciliation')
            for c,old in zip(self._connections,seen):
                if c.in_transaction or c.total_changes != old['changes'] or live._one(c,'PRAGMA main.data_version') != old['dataVersion']:
                    raise CanonicalBindingUnavailable('canonical_rows_changed')
            self._check()
            now = time.monotonic_ns()
            if not start <= now <= start + 5_000_000_000:
                raise CanonicalBindingUnavailable('canonical_observation_expired')
            if phase == 'CLAIMED':
                require(node.task is task and not task.done() and not task.cancelling(), 'canonical_owner_changed_during_read')
                entry.claimed_task, entry.claimed_generation = task,generation
            done = entry.carrier_done or (entry.carrier is not None and entry.carrier.done())
            cancelled = entry.carrier_cancelled or (entry.carrier is not None and entry.carrier.cancelled())
            return CanonicalClaimSnapshot(b.admission_id,b.run_id,b.canonical_session_id,self._expected.epoch,
                generation,phase,has_agent,owns_task,bool(done),bool(cancelled),run_status in health.TERMINAL_RUNS,
                bool(self._runner._draining or self._authority.retiring),now)
        except CanonicalBindingUnavailable:
            raise
        except (sqlite3.OperationalError,sqlite3.InterfaceError):
            raise CanonicalBindingUnavailable('canonical_native_read_unavailable') from None
        except (CanonicalBindingRejected,sqlite3.Error,live.LiveStoreRejected,ValueError,TypeError,AttributeError,KeyError,UnicodeError,RecursionError):
            self._fault = 'canonical_identity_or_claim_unconfirmed'
            raise CanonicalBindingRejected(self._fault) from None
        finally:
            for lock in reversed(acquired):
                lock.release()
            self._reading = False

    def release_settled(self, run_id):
        """Discard diagnostic references only; never remove native tasks or rows."""
        observed = self.capture(run_id)
        entry = self._entries[run_id]
        require(observed.phase == 'SETTLED' and observed.replay_terminal and entry.carrier_done and entry.carrier is None
                and run_id not in self._task_map, 'canonical_not_fully_retired')
        del self._entries[run_id]
        return {'state':'CANONICAL_OBSERVATION_RELEASED','nativeStateModified':False,
                'runtimeAdmissionAuthorized':False,'storeReleaseAuthorized':False}
