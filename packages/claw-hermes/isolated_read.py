"""Native read_file -> registered terminal backend -> one no-network tool process.

This module is a trusted local Linux integration. No SSH, dynamic installation,
agent-selected mounts, provider credentials or host-execution fallback. Native
file formatting/redaction/tracking stay owned by Hermes, not a new file reader.
"""
from __future__ import annotations
from contextvars import ContextVar
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import uuid
from execution_budget import ExecutionDenied, ExecutionLedger
from isolated_tool import IsolatedToolRunner, ToolSandboxPolicy
from recovery_inspector import _json, _load, _KEYS

BACKEND = 'alaz_isolated_read'
_ACTIVE = ContextVar('alaz_isolated_native_read', default=None)
RUN = re.compile(r'run_[a-f0-9]{32}\Z')


def require(value, reason):
    if not value:
        raise ExecutionDenied(reason)


def linux_available():
    return os.name == 'posix' and Path('/proc/self/ns/net').exists()


def directory(path):
    require(type(path) is str and bool(path) and not any(c in path for c in ',\r\n\0'), 'invalid_isolation_directory')
    p = Path(path)
    require(p.is_absolute() and p != Path('/'), 'absolute_isolation_directory_required')
    require(not any(x.is_symlink() for x in (p, *p.parents)), 'linked_isolation_directory')
    require(p.is_dir(), 'isolation_directory_missing')
    return p.resolve()


def _snapshot_input(path):
    """Copy only the already allowlisted regular file; reject link/replacement evidence."""
    p = Path(path)
    require(p.is_absolute() and p.suffix.lower() == '.txt', 'unsupported_isolated_read')
    require(not any(x.is_symlink() for x in (p, *p.parents)), 'linked_isolated_input')
    before = p.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= 65536,
            'unsupported_isolated_input')
    fd = os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns), 'isolated_input_changed')
        data = stream.read(65537)
        after = os.fstat(stream.fileno())
    require(len(data) <= 65536 and len(data) == before.st_size and
            (opened.st_size, opened.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'isolated_input_changed')
    return data


def validate_admission(conn, ledger, session_id):
    """Validate the native admission and scope before a read; not just its existence."""
    ledger._epoch(conn)
    fields = ('admission_id','request_id','principal_id','target_session_id','payload_json',
              'payload_digest','intent','status','owner_epoch','generation')
    rows = conn.execute('SELECT '+','.join(fields)+' FROM session_admissions WHERE request_id=? LIMIT 2',
                        (session_id,)).fetchall()
    require(len(rows) == 1, 'isolation_admission_unverified')
    row = dict(zip(fields, rows[0]))
    require(row['principal_id'] == 'api' and row['target_session_id'] == session_id and
            row['status'] == 'started' and type(row['owner_epoch']) is int and
            row['owner_epoch'] == ledger.context.epoch and type(row['generation']) is int and
            row['generation'] > 0, 'isolation_admission_not_active')
    require(type(row['admission_id']) is str and re.fullmatch('[a-f0-9]{32}', row['admission_id']),
            'invalid_isolation_admission_id')
    payload = _load(row['payload_json'])
    require(type(payload) is dict and type(payload.get('api_turn_v1')) is dict and
            payload['api_turn_v1'].get('run_owner_scope') == ledger.context.scope, 'isolation_scope_mismatch')
    settings = payload['api_turn_v1'].get('settings', {})
    require(type(settings) is dict and settings.get('requested_model') == ledger.policy.model and
            not any(settings.get(k) is not None for k in ('route','requested_provider','model_options')),
            'isolated_admission_model_mismatch')
    expected = _KEYS.admission_fingerprint(canonical_target=session_id,
                                           payload={'input':payload,'intent':row['intent']})
    require(row['payload_digest'] == expected, 'isolation_admission_digest_mismatch')
    return row


def native_input_guard(path):
    from agent.file_safety import get_read_block_error
    require(not get_read_block_error(path), 'native_input_refused')


def native_redact_result(text, path):
    from agent.redact import redact_sensitive_text, _is_secret_file_arg
    value = _load(text)
    require(type(value) is dict, 'invalid_native_read_result')
    if type(value.get('content')) is str:
        value['content'] = redact_sensitive_text(value['content'], file_read=True,
                                                 secret_file=_is_secret_file_arg(path))
    return _json(value)


class _NativeInterruptSource:
    def __init__(self, session_id):
        try:
            from tools import interrupt, approval_context
            require(approval_context._approval_session_id.get() == session_id and
                    bool(approval_context._approval_tool_call_id.get()), 'native_tool_context_missing')
            self.native = interrupt
            self.thread_id = threading.get_ident()
            self.acting_for = interrupt.acting_for_tid.get()
            require(self.acting_for is None or type(self.acting_for) is int, 'invalid_native_interrupt_owner')
        except ExecutionDenied:
            raise
        except Exception:
            raise ExecutionDenied('native_cancellation_unavailable') from None

    @property
    def is_interrupted(self):
        # Freeze execution-owner identities before any runner/polling thread change.
        return (self.native.is_thread_interrupted(self.thread_id) or
                self.native.is_thread_interrupted(self.acting_for))


class _Cancellation:
    """The native agent's interrupted flag plus current owner/config revocation.

    The trusted parent keeps running to enforce this polling contract. A killed
    parent is NOT repaired by this object (D1 hard-crash limitation remains).
    """
    def __init__(self, invocation):
        self.invocation = invocation
        self.reason = None
    def is_set(self):
        if self.reason:
            return True
        call = self.invocation
        try:
            value = call.parent_agent.is_interrupted
            require(type(value) is bool, 'native_cancellation_unavailable')
            if value:
                self.reason = 'native_read_cancelled'
            else:
                call.owner.check_call(call)
        except Exception:
            self.reason = 'isolated_read_authority_lost'
        return self.reason is not None


@dataclass
class _Invocation:
    owner: object
    ledger: object
    ticket: dict
    session_id: str
    fingerprint: str
    input_data: bytes = field(repr=False)
    parent_agent: object = field(repr=False)
    used: bool = False
    failure: str | None = None
    receipt: dict | None = None
    admission_identity: tuple | None = None


class _Environment:
    cwd = '/workspace'
    env_type = BACKEND
    _hermes_backend_name = BACKEND
    def __init__(self, owner):
        self.owner = owner
    def cleanup(self):
        # Each call closes its own exact container. Never sweep names or profiles.
        return None
    def execute(self, command, cwd=None, timeout=None, stdin_data=None, **kwargs):
        call = _ACTIVE.get()
        require(call is not None and call.owner is self.owner, 'isolated_read_context_required')
        require(cwd in (None, '/workspace') and stdin_data is None and not kwargs, 'unsupported_isolated_command')
        require(type(command) is str and 0 < len(command.encode()) <= 131072 and '\0' not in command,
                'invalid_isolated_command')
        if timeout is not None:
            require(type(timeout) is int and timeout > 0, 'invalid_isolated_timeout')
        require(not call.used, 'isolated_command_already_attempted')
        call.used = True  # Before staging or any external effect; no fallback probe retry.
        stop = _Cancellation(call)
        require(not stop.is_set(), stop.reason or 'isolated_read_cancelled')
        capsule = self.owner.capsule_root / uuid.uuid4().hex
        capsule.mkdir(mode=0o755)
        (capsule/('input-'+call.ticket['ticket']+'.txt')).write_bytes(call.input_data)
        # Only a reviewed native read command reaches bash; it is never host-executed.
        (capsule/'command.txt').write_text(command, encoding='utf-8')
        program = "import os\nfrom pathlib import Path\nos.execv('/bin/bash',['/bin/bash','--noprofile','--norc','-c',Path('/workspace/command.txt').read_text()])\n"
        (capsule/'program.py').write_text(program, encoding='utf-8')
        receipt = self.owner.receipt_root / uuid.uuid4().hex
        try:
            runner = IsolatedToolRunner(root=self.owner.capsule_root, capsule=capsule,
                receipt_dir=receipt, policy=self.owner.policy, use_sudo=self.owner.use_sudo)
            result = runner.run(cancel_event=stop)
            call.receipt = {'version':1,'ticket':call.ticket['ticket'],'runId':call.session_id,
                'outcome':result.get('result'),'retryAllowed':False,
                'containerId':result.get('exit',{}).get('containerId'),
                'exited':result.get('exit',{}).get('exited') is True,
                'removed':result.get('exit',{}).get('removed') is True,
                'admissionId':call.admission_identity[0], 'executionGeneration':call.admission_identity[1],
                'inputDigest':hashlib.sha256(call.input_data).hexdigest(),
                'commandDigest':hashlib.sha256(command.encode()).hexdigest()}
            self.owner.observations.append(dict(call.receipt))
            if receipt.is_dir():
                with (receipt/'bridge-binding.json').open('x',encoding='utf-8') as handle:
                    handle.write(_json(call.receipt)+'\n')
            require(result.get('errors') == [] and result.get('capsuleUnchanged') is True,
                    'isolated_result_unverified')
            end = result.get('exit',{})
            require(end.get('exited') is True and end.get('removed') is True and end.get('neverStarted') is False,
                    'isolated_exit_unverified')
            require(result.get('result') in ('completed','tool_failed'), stop.reason or 'isolated_read_not_completed')
            require(type(end.get('exitCode')) is int and type(result.get('stdout')) is str,
                    'invalid_isolated_result')
            require((result['result'] == 'completed') == (end['exitCode'] == 0),
                    'isolated_outcome_exit_conflict')
            require(not result.get('outputTruncated'), 'isolated_read_output_limit')
            require(not stop.is_set(), stop.reason or 'isolated_read_cancelled')
            return {'output':result['stdout'], 'returncode':end['exitCode']}
        except Exception as exc:
            call.failure = str(exc) if isinstance(exc, ExecutionDenied) else 'isolated_backend_unavailable'
            raise ExecutionDenied(call.failure) from None


class NativeReadIsolation:
    def __init__(self, settings, ledger_factory):
        require(type(settings) is dict and set(settings) == {'capsule_root','receipt_root','policy','use_sudo'},
                'explicit_isolation_settings_required')
        require(type(settings['policy']) is dict and type(settings['use_sudo']) is bool,
                'invalid_isolation_policy')
        try:
            self.policy = ToolSandboxPolicy(**settings['policy'])
        except Exception:
            raise ExecutionDenied('invalid_isolation_policy') from None
        self.capsule_root = directory(settings['capsule_root'])
        self.receipt_root = directory(settings['receipt_root'])
        require(not self.receipt_root.is_relative_to(self.capsule_root) and
                not self.capsule_root.is_relative_to(self.receipt_root), 'overlapping_isolation_directories')
        self.use_sudo = settings['use_sudo']
        self.ledger_factory = ledger_factory
        self.provider = None
        self.scope = None
        self.observations = []
        self._tickets = set()
        self._lock = threading.Lock()

    def register(self, ctx):
        from agent.terminal_env_provider import TerminalEnvironmentProvider
        from agent import terminal_env_registry
        import inspect
        source = Path(inspect.getfile(TerminalEnvironmentProvider)).resolve().parents[1]
        lock = _load((Path(__file__).resolve().parents[2]/'config/isolated-read/source-lock.json').read_text())
        for item in lock['files']:
            p = source/item['path']
            require(not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256'],
                    'unsupported_isolation_native_source')
        owner = self
        class Provider(TerminalEnvironmentProvider):
            name = BACKEND
            is_container = True
            is_remote = True
            skip_container_guards = False
            def is_available(self):
                return linux_available() and Path('/usr/bin/docker').is_file()
            def create_environment(self, *, cwd, timeout, task_id='default', **kwargs):
                require(cwd == '/workspace', 'isolated_cwd_required')
                return _Environment(owner)
        self.provider = Provider()
        self.scope = ctx._manager.scope_key
        ctx.register_terminal_environment_provider(self.provider)
        self.verify()

    def verify(self):
        require(linux_available(), 'linux_isolation_required')
        from agent import terminal_env_registry
        require(self.provider is not None and terminal_env_registry.get_provider(BACKEND, scope=self.scope) is self.provider,
                'isolation_provider_missing')

    def check_call(self, call):
        require(linux_available(), 'linux_isolation_required')
        self.verify()
        fresh = self.ledger_factory()
        require(type(fresh) is ExecutionLedger and fresh.context == call.ledger.context and
                fresh.policy == call.ledger.policy, 'isolated_owner_changed')
        def check(c):
            require(fresh._state(c)['quarantined'] is False, 'execution_budget_quarantined')
            row = validate_admission(c, fresh, call.session_id)
            identity = (row['admission_id'], row['generation'], row['payload_digest'], row['owner_epoch'])
            if call.admission_identity is None:
                call.admission_identity = identity
            require(call.admission_identity == identity, 'isolated_admission_changed')
            row = c.execute('SELECT value FROM state_meta WHERE key=?', (fresh.prefix+call.ticket['ticket'],)).fetchone()
            require(row is not None, 'isolated_ticket_missing')
            saved = fresh._row(_load(row[0]), call.ticket['ticket'])
            require(saved == call.ticket and saved['kind'] == 'read_file' and saved['state'] == 'reserved' and
                    saved['fingerprint'] == call.fingerprint and saved['epoch'] == fresh.context.epoch and
                    saved['instance'] == fresh.context.instance_id, 'isolated_ticket_mismatch')
        fresh._write(check)

    def invoke(self, original, args, canonical, kwargs, ledger, ticket):
        require(type(ledger) is ExecutionLedger and type(ticket) is dict, 'isolated_ledger_required')
        args = _load(_json(args), 16384)
        require(type(args) is dict and type(args.get('path')) is str and
                Path(args['path']).resolve() == Path(canonical).resolve(), 'isolated_path_mismatch')
        native_input_guard(canonical)
        sid = kwargs.get('session_id')
        require(type(sid) is str and RUN.fullmatch(sid), 'isolated_session_required')
        parent = kwargs.get('parent_agent')
        if parent is None:
            parent = _NativeInterruptSource(sid)
        # Optional trusted caller context remains supported; normal pinned read_file
        # dispatcher has no parent_agent and uses the native thread identities above.
        require(type(getattr(parent,'is_interrupted',None)) is bool, 'native_cancellation_unavailable')
        fp = hashlib.sha256(_json({'name':'read_file','args':args,'session_id':sid}).encode()).hexdigest()
        call = _Invocation(self,ledger,dict(ticket),sid,fp,b'',parent)
        self.check_call(call)
        with self._lock:
            require(ticket['ticket'] not in self._tickets, 'isolated_ticket_already_attempted')
            self._tickets.add(ticket['ticket'])
        call.input_data = _snapshot_input(canonical)
        require(_ACTIVE.get() is None, 'nested_isolated_read')
        token = _ACTIVE.set(call)
        try:
            # Unique staged names avoid cross-input native dedup while preserving
            # the actual session/task identities supplied by Hermes.
            result = original(dict(args,path='/workspace/input-'+ticket['ticket']+'.txt'), **kwargs)
            if call.failure:
                raise ExecutionDenied(call.failure)
            require(type(result) is str, 'invalid_native_read_result')
            require(call.used and call.receipt is not None, 'native_read_without_isolated_execution')
            return native_redact_result(result, canonical)
        finally:
            _ACTIVE.reset(token)
