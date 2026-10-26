"""One original native owner/consumer lifecycle with an explicit scripted model.

Only model factory, computation and model close are doubled. API admission,
authority scheduling, physical worker, result settlement, replay, retirement,
store close and the caller lease use the installed pinned native implementation.
This qualification entry has no general model/provider or HTTP service grant.
Unknown effects retain this module's original attempt and all owned references.
"""
from __future__ import annotations

import asyncio
import contextlib
import errno
import hashlib
import os
from pathlib import Path
import socket
import sqlite3
import sys
import threading
import time
from types import FunctionType, SimpleNamespace

import gateway_finite_protocol as protocol

ROOT = Path(__file__).resolve().parents[2]
MAX_EXECUTION_SECONDS = 50
_attempt = None


class FiniteRuntimeRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise FiniteRuntimeRejected(reason)


class _Attempt:
    """A strong reference survives errors; there is no automatic teardown path."""
    def __init__(self, work):
        self.work = protocol.validate_work(work)
        self.deadline = time.monotonic() + MAX_EXECUTION_SECONDS
        self.stage = 'RESERVED'
        self.held = self.owner = self.consumer = self.loop = None
        self.stores = self.connections = ()
        self.tasks = []
        self.agents = []
        self.computations = []
        self.cases = []
        self.profile_counts = {name: 0 for name in protocol.PROFILE_FUNCTIONS}
        self.sqlite_opens = []
        self.denied = []
        self.blocked_ipv6_sockets = []
        self.main_thread = threading.get_ident()

    async def wait(self, awaitable, seconds):
        # wait_for/asyncio.run would cancel native work on timeout. Keep the
        # original task/loop/consumer instead; the supervisor owns observation.
        now = time.monotonic()
        remaining = min(seconds, self.deadline - now)
        require(remaining > 0, 'finite_execution_deadline')
        stop_by = now + remaining
        task = asyncio.ensure_future(awaitable)
        self.tasks.append(task)
        done, pending = await asyncio.wait((task,), timeout=remaining)
        require(not pending and task in done, 'finite_execution_unknown')
        require(time.monotonic() <= stop_by, 'finite_execution_deadline')
        return task.result()

    def audit(self, event, args):
        if event == 'socket.bind' and self.ipv6_probe(args, sys._getframe(1)):
            # A qualified DENIAL only. The pinned import probe catches this
            # PermissionError, closes its socket and reports HAS_IPV6=False.
            self.blocked_ipv6_sockets.append(args[0])
            raise PermissionError(errno.EACCES, 'finite_ipv6_capability_probe_disabled')
        if event == 'subprocess.Popen':
            command = args[1]
            helpers = tuple(str(ROOT / 'scripts' / name) for name in
                            ('run_store_preopen.py', 'run_response_preopen.py'))
            allowed = (isinstance(command, (tuple, list)) and len(command) == 4
                       and list(command[:3]) == [sys.executable, '-I', '-B']
                       and command[3] in helpers and str(args[2]) == str(ROOT)
                       and args[3] == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'})
            if allowed and self.stage == 'OWNER_START':
                return
        elif event == 'sqlite3.connect':
            self.sqlite_opens.append((self.stage, str(args[0])))
            return
        elif event not in ('socket.connect', 'socket.bind', 'socket.getaddrinfo',
                           'socket.gethostbyname', 'socket.gethostbyaddr',
                           'socket.getnameinfo', 'socket.sendto', 'socket.sendmsg',
                           'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'):
            return
        if len(self.denied) < 16:
            self.denied.append(event)
        raise PermissionError('finite_offline_boundary')

    def ipv6_probe(self, args, caller):
        module = sys.modules.get('urllib3.util.connection')
        source = str(ROOT / 'dependencies/urllib3/util/connection.py')
        if (self.stage != 'CONSUMER_PREPARE' or self.blocked_ipv6_sockets
                or module is None or getattr(module, '__file__', None) != source
                or len(args) != 2):
            return False
        sock, address = args
        original = getattr(module, '_has_ipv6', None)
        return (type(original) is FunctionType and caller.f_code is original.__code__
                and caller.f_code.co_filename == source and caller.f_globals is vars(module)
                and caller.f_locals.get('host') == '::1' and caller.f_locals.get('sock') is sock
                and type(address) is tuple and len(address) == 2
                and type(address[0]) is str and address[0] == '::1'
                and type(address[1]) is int and address[1] == 0
                and type(sock) is socket.socket and sock.family == socket.AF_INET6
                and sock.type == socket.SOCK_STREAM and sock.proto == 0 and sock.fileno() >= 0)

    def check_probes_closed(self):
        if self.blocked_ipv6_sockets:
            module = sys.modules.get('urllib3.util.connection')
            require(len(self.blocked_ipv6_sockets) == 1
                    and self.blocked_ipv6_sockets[0].fileno() == -1
                    and module is not None and getattr(module, '__file__', None)
                    == str(ROOT / 'dependencies/urllib3/util/connection.py')
                    and module.HAS_IPV6 is False, 'finite_ipv6_probe_not_closed')

    def profile(self, frame, event, arg):
        name = frame.f_code.co_name
        if (event == 'call' and name in self.profile_counts
                and frame.f_code.co_filename.startswith(str(ROOT / 'native') + os.sep)):
            self.profile_counts[name] += 1


def _scripted_model(attempt):
    """The sole declared model fixture; never a second runner or store owner."""
    class ScriptedModel:
        def __init__(self, **kwargs):
            require(kwargs.get('session_db') is attempt.stores[0], 'finite_model_other_state')
            self.kwargs = kwargs
            self.session_id = kwargs['session_id']
            self.model = kwargs['model']
            self.tools = []
            self.session_prompt_tokens = 0
            self.session_completion_tokens = 0
            self.session_output_tokens = 0
            self.context_compressor = SimpleNamespace(
                compression_count=0, last_prompt_tokens=0, context_length=4096)
            self.request_overrides = {}
            self._codex_session = None
            self.interrupted = False
            self.closed = False
            attempt.agents.append(self)

        def close(self):
            self.closed = True

        def clear_interrupt(self):
            self.interrupted = False

        def interrupt(self, *args, **kwargs):
            self.interrupted = True

        def run_conversation(self, message, **kwargs):
            require(type(message) is str and len(message) <= 16384,
                    'finite_model_message')
            matches = [kind for kind, text in protocol.MESSAGES.items() if text in message]
            require(len(matches) == 1 and len(attempt.computations) < 3,
                    'finite_model_unexpected_work')
            kind = matches[0]
            require(kind == ('normal', 'new', 'error')[len(attempt.computations)]
                    and threading.get_ident() != attempt.main_thread
                    and self.kwargs['session_db'] is attempt.stores[0],
                    'finite_model_worker_identity')
            attempt.computations.append(kind)
            if kind == 'error':
                raise RuntimeError('controlled_native_finite_model_failure')
            numbers = protocol.MESSAGES[kind].removeprefix('SUM:').split(',')
            answer = str(sum(int(value) for value in numbers))
            return {'final_response': answer, 'completed': True, 'api_calls': 0,
                    'tools': [], 'agent_persisted': False,
                    'messages': [{'role': 'user', 'content': message},
                                 {'role': 'assistant', 'content': answer}]}
    return ScriptedModel


async def _settle_scheduled(attempt):
    authority = attempt.consumer._binding._authority
    tasks = [live.task for live in authority.sessions.values()
             if live.task is not None and not live.task.done()]
    tasks.extend(task for task in getattr(authority, '_mutation_tasks', ())
                 if not task.done())
    for task in dict.fromkeys(tasks):
        await attempt.wait(task, 10)
    # Let the original done callbacks finish; do not prune any native registry.
    await asyncio.sleep(0)


def _read_case(attempt, kind, api_result):
    """Read the native ledger/result, never insert or settle SQL manually."""
    from gateway.session_results import admission_result
    request_kind = 'normal' if kind == 'replay' else kind
    request = attempt.work['requestIds'][request_kind]
    rows = [dict(row) for row in attempt.connections[0].execute(
        'SELECT admission_id,status,outcome,owner_epoch,request_id,target_session_id '
        'FROM session_admissions WHERE principal_id=? AND request_id=?', ('api', request))]
    require(len(rows) == 1, 'finite_admission_readback')
    row = rows[0]
    require(row['status'] == 'terminal'
            and row['outcome'] == ('failed' if kind == 'error' else 'completed')
            and row['owner_epoch'] == attempt.owner.expectation.epoch
            and row['target_session_id'] == attempt.work['sessionId'],
            'finite_admission_not_terminal')
    saved = admission_result(attempt.stores[0], row['admission_id'])
    require(type(saved) is dict and 'result' in saved and 'usage' in saved
            and type(api_result) is tuple and len(api_result) == 2
            and api_result == (saved['result'], saved['usage']), 'finite_result_not_native_saved')
    value = saved['result']
    require(type(value) is dict, 'finite_native_result_shape')
    if kind == 'error':
        require(value.get('completed') is False
                and (value.get('failed') is True or bool(value.get('error'))),
                'finite_native_error_not_settled')
    else:
        require(value.get('completed') is True
                and value.get('final_response') == protocol.ANSWERS[request_kind],
                'finite_native_answer_changed')
    return {'kind': kind, 'requestId': request, 'admissionId': row['admission_id'],
            'outcome': row['outcome'],
            'apiResultSha256': hashlib.sha256(protocol.canonical(api_result)).hexdigest(),
            'storedResultSha256': hashlib.sha256(protocol.canonical(saved)).hexdigest(),
            'computationCount': len(attempt.computations)}


async def _work_and_close(attempt, opened, previous_epoch):
    from gateway.config import GatewayConfig, PlatformConfig
    import hermes_state_registry as registry

    attempt.stage = 'CONSUMER_PREPARE'
    await attempt.wait(attempt.owner.prepare_runtime(
        GatewayConfig(multiplex_profiles=False, write_sessions_json=False),
        PlatformConfig(extra={'key': 'owned-finite-qualification',
                              'model_name': 'owned-scripted-fixture'}),
        local_admission=True, canonical_api=True, finite_turn=True), 15)
    attempt.consumer = attempt.owner._prepared_consumer
    c = attempt.consumer
    require(len(c._connections) == len(attempt.connections) == 3
            and all(a is b for a, b in zip(c._connections, attempt.connections)),
            'finite_original_connections_changed')
    c.publish_api_adapter()
    c.activate_admission()
    require(c._admission_phase == 'ACTIVE' and c._publication_phase == 'PUBLISHED',
            'finite_native_admission_not_active')
    from gateway.session_api_turn import run_api_turn
    import run_agent
    attempt.check_probes_closed()
    original_factory = run_agent.AIAgent
    run_agent.AIAgent = _scripted_model(attempt)
    attempt.stage = 'NATIVE_WORK'
    for kind in protocol.KINDS:
        key = 'normal' if kind == 'replay' else kind
        result = await attempt.wait(run_api_turn(c._adapter,
            session_id=attempt.work['sessionId'], request_id=attempt.work['requestIds'][key],
            user_message=protocol.MESSAGES[key], conversation_history=[]), 25)
        await _settle_scheduled(attempt)
        case = _read_case(attempt, kind, result)
        expected_count = {'normal': 1, 'replay': 1, 'new': 2, 'error': 3}[kind]
        require(case['computationCount'] == expected_count, 'finite_duplicate_or_missing_computation')
        if kind == 'replay':
            require(all(case[name] == attempt.cases[0][name] for name in case if name != 'kind'),
                    'finite_replay_changed')
        attempt.cases.append(case)
    require(len({case['admissionId'] for case in attempt.cases}) == 3,
            'finite_new_request_not_independent')
    require(not attempt.denied
            and not any(stage == 'NATIVE_WORK' and path.endswith('state.db')
                        for stage, path in attempt.sqlite_opens), 'finite_unexpected_side_effect')
    attempt.stage = 'NATIVE_DRAIN'
    changes = [conn.total_changes for conn in attempt.connections]
    c.begin_drain()
    await attempt.wait(c.retire_idle_runtime(), 10)
    c.retire_idle_api_sessions()
    c.finish_drain()
    await attempt.wait(c.detach(), 10)
    require(c._stage == 'DETACHED' and c._admission_phase == 'DETACHED',
            'finite_consumer_not_detached')
    require(changes == [conn.total_changes for conn in attempt.connections],
            'finite_retirement_changed_rows')
    require(registry.stats()['total_refcounts'] == 0
            and attempt.agents and all(agent.closed for agent in attempt.agents),
            'finite_native_runtime_not_retired')
    # Restore only after native retirement proves that no model use remains.
    # On error the dedicated child retains the fixture and the original owner.
    run_agent.AIAgent = original_factory
    require(all(task.done() and not task.cancelled() for task in attempt.tasks),
            'finite_task_still_owned')
    current = asyncio.current_task()
    require(not any(task is not current and not task.done()
                    for task in asyncio.all_tasks()), 'finite_loop_tasks_remain')
    # After native retirement, join only the idle loop executor while the
    # original stores and caller lease are still held. A timeout retains both.
    await attempt.wait(attempt.loop.shutdown_default_executor(), 10)
    require(not any(task is not current and not task.done()
                    for task in asyncio.all_tasks()), 'finite_loop_tasks_remain')
    attempt.check_probes_closed()
    require(not attempt.denied, 'finite_unexpected_side_effect')
    epoch = attempt.owner.expectation.epoch
    attempt.stage = 'OWNER_CLOSE'
    attempt.owner.close()
    closed = 0
    for connection in attempt.connections:
        try:
            connection.execute('SELECT 1')
        except sqlite3.ProgrammingError:
            closed += 1
    require(closed == 3 and attempt.owner.status()['callerLeaseMayBeReleased'] is True,
            'finite_connections_not_physically_closed')
    attempt.held.check()
    attempt.check_probes_closed()
    require(not attempt.denied, 'finite_unexpected_side_effect')
    attempt.held.finish()
    require(attempt.held._finished and not attempt.held._owner.homes,
            'finite_caller_lease_not_released')
    result = {'protocol': protocol.RESULT_PROTOCOL, 'state': 'PROJECTED_FINITE_OWNER_CLOSED',
        'pid': os.getpid(), 'epoch': epoch, 'completedChecks': opened['completedChecks'],
        'workSha256': protocol.work_digest(attempt.work), 'caseReceipts': attempt.cases,
        'nativeProfileCallEvents': dict(attempt.profile_counts),
        'close': {'consumerState': c._stage, 'ownerState': attempt.owner.status()['state'],
                  'sameThreeConnections': True, 'registryRefcounts': registry.stats()['total_refcounts'],
                  'physicalConnectionsClosed': closed, 'modelInstancesClosed': True,
                  'rowsChangedByRetirement': 0, 'callerLeaseReleased': True},
        'model': {'kind': 'scripted-factory-fixture', 'factoryComputationCloseDoubled': True,
                  'realProviderCalls': 0, 'modelInvocations': len(attempt.computations)},
        'localAdmissionActivated': True, 'canonicalApiPublished': True,
        'serviceStarted': False, 'runtimeAdmissionAuthorized': False,
        'finiteWorkExecuted': True, 'fullD3BAccepted': False}
    return protocol.validate_result(result, work=attempt.work, pid=os.getpid(),
                                    previous_epoch=previous_epoch)


def execute(record, expected_mount, instance, work):
    """Called only by the fixed target after receive_finite validates projection."""
    global _attempt
    require(_attempt is None, 'finite_attempt_already_owned')
    require(threading.current_thread() is threading.main_thread()
            and threading.active_count() == 1 and sys.getprofile() is None
            and threading.getprofile() is None, 'finite_fresh_main_thread')
    _attempt = attempt = _Attempt(work)
    # No real credential is read or inherited. This fixed inert provider choice
    # lets the original native agent factory resolve its expected arguments.
    os.environ.update(HERMES_INFERENCE_PROVIDER='openai',
                      OPENAI_API_KEY='owned-offline-fixture-not-real',
                      OPENAI_BASE_URL='http://127.0.0.1:9/v1',
                      HERMES_AGENT_TIMEOUT='0', HERMES_AGENT_TIMEOUT_WARNING='0')
    sys.addaudithook(attempt.audit)
    sys.setprofile(attempt.profile)
    threading.setprofile(attempt.profile)
    try:
        with contextlib.redirect_stdout(sys.stderr):
            import gateway_retained_handoff as handoff
            import gateway_profile_lease as lease
            import gateway_store_startup as startup
            attempt.held = lease.reserve_profile(Path(handoff.TARGET), expected_mount)
            attempt.owner = startup.NativeStoreStartup(attempt.held, expected_mount, record.state,
                instance_id=instance, response_expected=record.response,
                prepared_layout=True, retained_profile=record.retained)
            attempt.stage = 'OWNER_START'
            opened = attempt.owner.start()
            attempt.stores = (attempt.owner.state_store, attempt.owner.replay_store,
                              attempt.owner.response_store)
            attempt.connections = tuple(store._conn for store in attempt.stores)
            attempt.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(attempt.loop)
            result = attempt.loop.run_until_complete(
                _work_and_close(attempt, opened, record.state.epoch))
            # Native detach/close is complete before ordinary idle loop teardown.
            # There is no task cancellation, executor shutdown or lease cleanup
            # in the error path.
            require(not any(not task.done() for task in asyncio.all_tasks(attempt.loop)),
                    'finite_loop_tasks_remain')
            attempt.loop.close()
            attempt.stage = 'COMPLETED'
            return result
    except BaseException:
        attempt.failed_stage = attempt.stage
        attempt.stage = 'UNKNOWN'
        raise
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
