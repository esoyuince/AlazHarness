"""Bounded work-health policy, NOT a collector, scheduler or admission capability.

Only a trusted adapter-owned collector may supply these local snapshots. It must
bind native handles/lease/generation and a complete current live-task inventory
under one observation barrier. No database row can establish its own live owner.
This module performs no I/O. Existing cold and quiescent HTTP gates are unchanged.
IDLE/BUSY are diagnostic decisions, never permission to dispatch/retry/release.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json
import uuid

MAX_ROWS = 256
MAX_TEXT = 512
MAX_RUN_JSON = 65536
TERMINAL_RUNS = frozenset(('completed', 'failed', 'cancelled', 'interrupted'))
ACTIVE_RUNS = frozenset(('queued', 'running'))

class Health(str, Enum):
    IDLE = 'IDLE'
    BUSY = 'BUSY'
    DRAINING = 'DRAINING'
    RECONCILE = 'RECONCILE_REQUIRED'
    UNOBSERVABLE = 'UNOBSERVABLE'

class InvalidEvidence(ValueError):
    pass

def need(value, code):
    if not value:
        raise InvalidEvidence(code)

def text(value):
    return type(value) is str and 0 < len(value) <= MAX_TEXT and not any(ord(c) < 32 for c in value)

def integer(value, minimum=0):
    return type(value) is int and minimum <= value < 2**63

@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    store_instance_id: str
    epoch: int
    instance_id: str
    owner_pid: int
    owner_started: int

    def __post_init__(self):
        try:
            valid = type(self.store_instance_id) is str and str(uuid.UUID(self.store_instance_id)) == self.store_instance_id
        except (ValueError, TypeError, AttributeError):
            valid = False
        need(valid and integer(self.epoch, 1) and text(self.instance_id)
             and integer(self.owner_pid, 1) and integer(self.owner_started, 1), 'runtime_identity')

@dataclass(frozen=True, slots=True)
class Admission:
    admission_id: str
    session_id: str
    status: str
    owner_epoch: int | None
    generation: int | None
    session_generation: int

@dataclass(frozen=True, slots=True)
class Run:
    run_id: str
    status_json: str
    owner_pid: int
    owner_started: int

@dataclass(frozen=True, slots=True)
class ResponseIdentity:
    request_key: str
    admission_id: str | None
    settled: bool

@dataclass(frozen=True, slots=True)
class LiveWork:
    """Evidence supplied by the live owner, NOT reconstructed from pending rows.

    QUEUED/RUNNING/SETTLING describe the owning task's observed phase. A terminal
    admission may still be BUSY while the same live task settles replay/response
    state; that does not grant permission to perform settlement.
    """
    admission_id: str
    session_id: str
    epoch: int
    generation: int | None
    phase: str
    task_alive: bool
    run_id: str | None = None
    response_key: str | None = None

@dataclass(frozen=True, slots=True)
class WorkSnapshot:
    identity: RuntimeIdentity
    admissions: tuple[Admission, ...]
    runs: tuple[Run, ...]
    responses: tuple[ResponseIdentity, ...]
    live_work: tuple[LiveWork, ...]
    unresolved_workers: int
    captured_ns: int
    revision_before: int
    revision_after: int
    complete: bool
    storage_verified: bool
    transaction_active: bool
    draining: bool
    shutdown_unknown: bool

@dataclass(frozen=True, slots=True)
class Decision:
    state: Health
    reason: str
    owned_work_count: int = 0

    def public(self):
        # Deliberately no IDs, private paths, payloads, arbitrary exception text.
        return {'state': self.state.value, 'reason': self.reason,
                'ownedWorkCount': self.owned_work_count,
                'healthy': True if self.state in (Health.IDLE, Health.BUSY, Health.DRAINING) else None,
                'runtimeAdmissionAuthorized': False, 'retryAuthorized': False,
                'storeReleaseAuthorized': False, 'snapshotOnly': True,
                'liveCollectorVerifiedHere': False}

def _run_status(raw):
    need(type(raw) is str and len(raw) <= MAX_RUN_JSON, 'run_json_invalid')
    need(len(raw.encode('utf-8')) <= MAX_RUN_JSON, 'run_json_invalid')
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'run_json_ambiguous')
            result[key] = value
        return result
    def constant(_):
        raise InvalidEvidence('run_json_invalid')
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, RecursionError):
        raise InvalidEvidence('run_json_invalid') from None
    need(type(value) is dict and type(value.get('status')) is str
         and value['status'] in ACTIVE_RUNS | TERMINAL_RUNS, 'run_status_unsupported')
    return value['status']

def _mapping(rows, kind, field):
    need(type(rows) is tuple and len(rows) <= MAX_ROWS, 'inventory_shape_or_limit')
    result = {}
    for row in rows:
        need(type(row) is kind, 'record_type')
        key = getattr(row, field)
        need(text(key), 'record_identity')
        need(key not in result, 'duplicate_record')
        result[key] = row
    return result

def assess(snapshot, expected, *, now_ns, max_age_ns):
    """Pure classifier. A stale/contended snapshot is not a positive health proof.

    Ownerless or unknown work requires reconciliation, never repair/replay here.
    This MVP supports at most one executing/settling owner globally, bounded
    queues, and no delegated workers. Future expansion needs explicit acceptance.
    """
    need(type(expected) is RuntimeIdentity, 'expected_identity_type')
    need(integer(now_ns) and integer(max_age_ns, 1) and max_age_ns <= 60_000_000_000, 'observation_clock')
    if type(snapshot) is not WorkSnapshot:
        return Decision(Health.UNOBSERVABLE, 'snapshot_type')
    s = snapshot
    try:
        need(type(s.identity) is RuntimeIdentity, 'snapshot_identity_type')
        need(all(type(getattr(s, n)) is bool for n in ('complete', 'storage_verified',
             'transaction_active', 'draining', 'shutdown_unknown')), 'observation_flags')
        need(integer(s.captured_ns) and integer(s.revision_before) and integer(s.revision_after)
             and integer(s.unresolved_workers), 'observation_numbers')
        if s.identity != expected:
            return Decision(Health.RECONCILE, 'runtime_identity_changed')
        if s.shutdown_unknown:
            return Decision(Health.RECONCILE, 'shutdown_outcome_unknown')
        if not s.storage_verified:
            return Decision(Health.UNOBSERVABLE, 'storage_not_verified')
        if not s.complete or s.revision_before != s.revision_after:
            return Decision(Health.UNOBSERVABLE, 'snapshot_incomplete_or_changed')
        if not 0 <= now_ns - s.captured_ns <= max_age_ns:
            return Decision(Health.UNOBSERVABLE, 'snapshot_stale_or_future')
        if s.transaction_active:
            return Decision(Health.UNOBSERVABLE, 'transaction_not_observable')
        admissions = _mapping(s.admissions, Admission, 'admission_id')
        runs = _mapping(s.runs, Run, 'run_id')
        responses = _mapping(s.responses, ResponseIdentity, 'request_key')
        owners = _mapping(s.live_work, LiveWork, 'admission_id')
        if s.unresolved_workers:
            return Decision(Health.RECONCILE, 'delegated_worker_not_qualified')
        statuses = {}
        for a in admissions.values():
            need(text(a.session_id) and type(a.status) is str and (a.owner_epoch is None or integer(a.owner_epoch, 1))
                 and (a.generation is None or integer(a.generation)) and integer(a.session_generation), 'admission_fields')
            if a.status not in ('queued', 'started', 'terminal'):
                return Decision(Health.RECONCILE, 'admission_unknown_or_unsupported')
            if a.status != 'terminal' and a.owner_epoch != expected.epoch:
                return Decision(Health.RECONCILE, 'stale_work_epoch')
        for run in runs.values():
            need(integer(run.owner_pid) and integer(run.owner_started), 'run_owner_fields')
            statuses[run.run_id] = _run_status(run.status_json)
        for response in responses.values():
            need(type(response.settled) is bool and (response.admission_id is None or text(response.admission_id)), 'response_fields')
        owner_runs = set()
        owner_responses = set()
        active_sessions = set()
        active_count = 0
        for owner in owners.values():
            need(text(owner.session_id) and integer(owner.epoch, 1) and (owner.generation is None or integer(owner.generation))
                 and type(owner.task_alive) is bool and type(owner.phase) is str, 'owner_fields')
            need(owner.run_id is None or text(owner.run_id), 'owner_run_id')
            need(owner.response_key is None or text(owner.response_key), 'owner_response_key')
            if not owner.task_alive:
                return Decision(Health.RECONCILE, 'owner_task_gone')
            if owner.phase not in ('QUEUED', 'RUNNING', 'SETTLING'):
                return Decision(Health.UNOBSERVABLE, 'owner_transition_unqualified')
            a = admissions.get(owner.admission_id)
            if a is None:
                return Decision(Health.RECONCILE, 'owner_without_admission')
            if (owner.epoch != expected.epoch or a.owner_epoch != owner.epoch
                    or a.session_id != owner.session_id or a.generation != owner.generation):
                return Decision(Health.RECONCILE, 'owner_admission_identity_mismatch')
            wanted = {'QUEUED': 'queued', 'RUNNING': 'started', 'SETTLING': 'terminal'}[owner.phase]
            if a.status != wanted:
                return Decision(Health.RECONCILE, 'owner_phase_mismatch')
            if owner.phase != 'QUEUED':
                if a.generation != a.session_generation or a.generation == 0:
                    return Decision(Health.RECONCILE, 'stale_work_generation')
                if a.session_id in active_sessions:
                    return Decision(Health.RECONCILE, 'multiple_session_owners')
                active_sessions.add(a.session_id)
                active_count += 1
            elif a.generation is not None:
                return Decision(Health.RECONCILE, 'queued_generation_invalid')
            if owner.run_id is not None:
                if owner.run_id in owner_runs or owner.run_id not in runs:
                    return Decision(Health.RECONCILE, 'run_owner_missing_or_ambiguous')
                owner_runs.add(owner.run_id)
                run = runs[owner.run_id]
                if (run.owner_pid, run.owner_started) != (expected.owner_pid, expected.owner_started):
                    return Decision(Health.RECONCILE, 'run_owner_process_mismatch')
                allowed = {'QUEUED': {'queued'}, 'RUNNING': {'running'},
                           'SETTLING': {'running'} | TERMINAL_RUNS}[owner.phase]
                if statuses[owner.run_id] not in allowed:
                    return Decision(Health.RECONCILE, 'run_phase_mismatch')
            if owner.response_key is not None:
                if owner.response_key in owner_responses or owner.response_key not in responses:
                    return Decision(Health.RECONCILE, 'response_owner_missing_or_ambiguous')
                owner_responses.add(owner.response_key)
                response = responses[owner.response_key]
                if response.admission_id != owner.admission_id:
                    return Decision(Health.RECONCILE, 'response_admission_mismatch')
                if response.settled and owner.phase != 'SETTLING':
                    return Decision(Health.RECONCILE, 'response_settled_before_admission')
        if active_count > 1:
            return Decision(Health.RECONCILE, 'single_active_owner_limit')
        if any(a.status != 'terminal' and a.admission_id not in owners for a in admissions.values()):
            return Decision(Health.RECONCILE, 'unowned_admission')
        if any(statuses[r.run_id] not in TERMINAL_RUNS and r.run_id not in owner_runs for r in runs.values()):
            return Decision(Health.RECONCILE, 'unowned_active_run')
        if any(not r.settled and r.request_key not in owner_responses for r in responses.values()):
            return Decision(Health.RECONCILE, 'unowned_unsettled_response')
        return Decision(Health.DRAINING if s.draining else Health.BUSY if owners else Health.IDLE,
                        'drain_requested' if s.draining else 'live_work_owned' if owners else 'no_active_work', len(owners))
    except (InvalidEvidence, UnicodeError, AttributeError, TypeError, ValueError, RecursionError):
        return Decision(Health.UNOBSERVABLE, 'invalid_or_ambiguous_evidence')

class WorkHealthSession:
    """Diagnostic continuity only; no state takeover or release on this object.

    Normal contention/staleness can be re-observed. Proven reconciliation needs
    latch until a NEW independently qualified session; drain cannot be unrequested.
    Runtime integration must also enforce actor and task-snapshot synchronization.
    """
    def __init__(self, expected):
        need(type(expected) is RuntimeIdentity, 'expected_identity_type')
        self._expected = expected
        self._revoked = None
        self._draining = False

    def observe(self, snapshot, *, now_ns, max_age_ns):
        if self._revoked is not None:
            return self._revoked
        result = assess(snapshot, self._expected, now_ns=now_ns, max_age_ns=max_age_ns)
        if result.state is Health.RECONCILE:
            self._revoked = result
        if type(snapshot) is WorkSnapshot and snapshot.draining is True:
            self._draining = True
        if self._draining and result.state in (Health.IDLE, Health.BUSY):
            return Decision(Health.DRAINING, 'drain_latched', result.owned_work_count)
        return result
