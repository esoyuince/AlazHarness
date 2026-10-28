"""Real, task-free service lifecycle on the unchanged R167 installation.

New QA coordinates original product owners; it never replaces product launch,
store, broker, CLI or cleanup methods. Every operation is single-attempt. On
ambiguous effects the original controller and its objects remain alive.
"""
from __future__ import annotations

import argparse
import ast
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
import types
import uuid

PYTHON = '/usr/bin/python3.12'
NODE = '/opt/alaz-r167a1-node-24.22.1/bin/node'
INSTALL = Path('/opt/alaz-r167a1')
QA = Path(__file__).resolve().parents[2]
ENTRY = 'scripts/qa/r168a1_linux_accept.py'
SEED = 'scripts/qa/r168a1_service_seed.py'
CHILD = 'scripts/qa/r168a1_seed_child.py'
BROKER = 'scripts/qa/r168a1_ping_broker.py'
PROBE = 'scripts/qa/r168a1_bootstrap_probe.py'
CONTRACT = 'bootstrap-contract.json'
FILES = {ENTRY, SEED, CHILD, BROKER, PROBE, CONTRACT}
RECEIPT_SHA = '0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f'
FORMATTER_SHA = '07cd24ce58a410cc9cee93c55ae5ac95986df016c5907dc7a49b55389bd41ed2'
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'}
USER_NS = 'user:[4026531837]'
PRINCIPAL = {'version': 1, 'enabled': True, 'gatewayUid': 23001, 'brokerUid': 23002,
             'socketGroupGid': 23003, 'hostUserNamespace': USER_NS}
MODEL = 'r168a1-ping-only'
MAX_RESULT = 524288


class AcceptanceRejected(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise AcceptanceRejected(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw, maximum=MAX_RESULT):
    require(type(raw) is bytes and 0 < len(raw) <= maximum and raw.endswith(b'\n')
            and raw.count(b'\n') == 1, 'qa_json_frame')
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'qa_json_duplicate')
            result[key] = value
        return result
    value = json.loads(raw.decode('ascii'), object_pairs_hook=unique)
    require(canonical(value) == raw, 'qa_json_canonical')
    return value


def stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def trusted_read(raw, maximum=262144):
    path = Path(raw)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'qa_source_alias')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'qa_source_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_uid == before.st_gid == 0 and not before.st_mode & 0o022
                and 0 < before.st_size <= maximum, 'qa_source_metadata')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(maximum + 1)
        require(len(data) == before.st_size
                and stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                'qa_source_changed')
        return data
    finally:
        os.close(fd)


def verify_inputs(expected):
    require(re.fullmatch(r'/opt/alaz-r168a1-qa-[0-9]{2}', str(QA)) is not None
            and Path(__file__) == QA / ENTRY, 'qa_fixed_source_root')
    raw = trusted_read(QA / 'manifest.json', 8192)
    require(digest(raw) == expected, 'qa_manifest_pin')
    manifest = parse(raw, 8192)
    require(set(manifest) == {'protocol', 'files'}
            and manifest['protocol'] == 'alaz-r168a1-input-v1'
            and set(manifest['files']) == FILES, 'qa_manifest_fields')
    found = set()
    for root, dirs, names in os.walk(QA, followlinks=False):
        for name in dirs:
            path = Path(root) / name
            info = path.lstat()
            require(str(path.relative_to(QA)) in {'scripts', 'scripts/qa'}
                    and stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                    and stat.S_IMODE(info.st_mode) == 0o755, 'qa_input_directory')
        found.update(str((Path(root) / n).relative_to(QA)) for n in names)
    require(found == FILES | {'manifest.json'}, 'qa_input_inventory')
    sources = {}
    for name, row in manifest['files'].items():
        require(type(row) is dict and set(row) == {'sha256', 'size'}
                and type(row['size']) is int and 0 < row['size'] <= 262144
                and type(row['sha256']) is str
                and re.fullmatch('[a-f0-9]{64}', row['sha256']), 'qa_input_entry')
        data = trusted_read(QA / name)
        require(len(data) == row['size'] and digest(data) == row['sha256'], 'qa_input_pin')
        sources[name] = data
    return manifest, sources


def load_source(name, path, raw):
    require(name not in sys.modules, 'qa_module_already_loaded')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def start_ticks(pid, *, live=True):
    raw = Path('/proc', str(pid), 'stat').read_text()
    head, separator, tail = raw.rpartition(') ')
    fields = tail.split()
    require(separator and head.startswith(str(pid) + ' (') and len(fields) >= 20
            and (not live or fields[0] not in ('Z', 'X', 'x')), 'qa_original_process_not_live')
    if not live:
        require(int(fields[1]) == os.getpid(), 'qa_spawned_child_parent')
    return int(fields[19])


def actor():
    import pwd
    import grp
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64'
            and sys.executable == PYTHON and sys.version_info[:3] == (3, 12, 3)
            and sys.flags.isolated == 1 and sys.flags.no_site == 1
            and sys.dont_write_bytecode and not sys.flags.optimize, 'qa_interpreter')
    require(os.getresuid() == os.getresgid() == (0, 0, 0)
            and not os.getgroups(), 'qa_root_actor')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip() == 'AlazHarness-D3B-P71C'
            and not Path('/mnt/c/Windows').exists(), 'qa_dedicated_lab')
    require(os.readlink('/proc/self/ns/user') == USER_NS
            and Path('/proc/self/uid_map').read_text().split() == ['0', '0', '4294967295']
            and Path('/proc/self/gid_map').read_text().split() == ['0', '0', '4294967295'],
            'qa_initial_user_namespace')
    require(threading.active_count() == 1
            and threading.current_thread() is threading.main_thread(), 'qa_main_thread')
    require(pwd.getpwuid(23001).pw_name == 'alazgateway'
            and pwd.getpwuid(23001).pw_gid == 23003
            and pwd.getpwuid(23002).pw_name == 'alazbroker'
            and pwd.getpwuid(23002).pw_gid == 23003
            and grp.getgrgid(23003).gr_name == 'alazipc', 'qa_principals')


def exclusive(path, raw, mode=0o600, uid=0, gid=0):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fchown(stream.fileno(), uid, gid)
        os.fsync(stream.fileno())


def collect(attempt, seconds, maximum=65536):
    """Bounded original-pipe observation; no termination or second input."""
    process = attempt['process']
    buffers = attempt.setdefault('buffers', {'stdout': bytearray(), 'stderr': bytearray()})
    end = time.monotonic() + seconds
    with selectors.DefaultSelector() as selector:
        for name in buffers:
            os.set_blocking(getattr(process, name).fileno(), False)
            selector.register(getattr(process, name), selectors.EVENT_READ, name)
        while selector.get_map():
            left = end - time.monotonic()
            require(left > 0, 'qa_child_output_timeout_unknown')
            for key, _ in selector.select(min(left, .1)):
                raw = os.read(key.fileobj.fileno(), min(16384, maximum + 1 - len(buffers[key.data])))
                if not raw:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                else:
                    buffers[key.data].extend(raw)
                    require(len(buffers[key.data]) <= maximum, 'qa_child_output_overflow_unknown')
    attempt['pipesComplete'] = True
    code = process.wait(timeout=max(.01, end - time.monotonic()))
    attempt['exitCode'] = code
    return bytes(buffers['stdout']), bytes(buffers['stderr'])


def process_report(attempt):
    if attempt is None:
        return None
    process = attempt.get('process')
    value = {'phase': attempt.get('phase'), 'pid': process.pid if process else None,
             'exitCode': process.poll() if process else None,
             'startTicks': attempt.get('startTicks'),
             'pipesComplete': attempt.get('pipesComplete', False)}
    capture = attempt.get('capture')
    buffers = attempt.get('buffers', {})
    if capture is not None:
        buffers = {n: bytes(getattr(capture, n + '_bytes')) for n in ('stdout', 'stderr')}
        value.update(pipesComplete=capture.complete, inputWritten=capture.input_written,
                     overflowed=capture.overflowed)
    for name, raw in buffers.items():
        value[name] = {'bytes': len(raw), 'sha256': digest(raw),
                       'base64': base64.b64encode(raw).decode('ascii')}
    return value


def execution_policy():
    return {'model': MODEL, 'max_provider_calls': 0, 'max_tool_calls': 0,
            'input_ceiling_tokens': 1, 'output_ceiling_tokens': 1,
            'total_token_limit': 0, 'total_cost_microusd': 0,
            'input_rate_microusd_per_million': 1, 'output_rate_microusd_per_million': 1}


def configuration(ready, canary, signing_key):
    bearer, api_key = uuid.uuid4().hex, uuid.uuid4().hex
    return {'model': {'provider': 'custom', 'default': MODEL,
                'base_url': 'http://127.0.0.1:45568/alaz/provider/v1', 'api_key': bearer},
            'gateway': {'multiplex_profiles': False, 'write_sessions_json': False,
                'loop_watchdog': False, 'systemd_watchdog_seconds': 0},
            'platform_toolsets': {'api_server': ['file']},
            'platforms': {'api_server': {'enabled': True, 'extra': {
                'host': '127.0.0.1', 'port': 45568, 'key': api_key, 'model_name': MODEL}}},
            'plugins': {'enabled': [], 'entries': {'alaz-host-gate': {
                'allow_tool_override': True, 'settings': {
                    'policy': {'allowed_models': [MODEL], 'max_issued': 1,
                        'max_dispatches': 1, 'validity_seconds': 30},
                    'execution': {'policy': execution_policy(), 'provider_bearer': bearer,
                        'allowed_read_files': [str(canary)], 'provider_broker': {
                            'socket_path': ready['socketPath'], 'broker_id': ready['brokerId'],
                            'route_fingerprint': ready['routeFingerprint'],
                            'signing_key': signing_key, 'principal_contract': dict(PRINCIPAL)}}}}}}}


def config_bytes(document):
    """Installed service-profile JSON is unframed UTF-8, without a newline."""
    return json.dumps(document, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


# Candidate-specific diagnostic qualification; no runtime pin overrides.
_SEED_DIAG_ARCHIVE_SHA = '43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a'
_SEED_DIAG_RECEIPT_SHA = '0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f'
_SEED_DIAG_HARNESS = '1600eba430562795b9114209d1168bfa0d6ea5fd'
_SEED_DIAG_NATIVE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
_SEED_DIAG_SEED_SHA = '129afb6e52e8034ba25a583868699f774592efe09296651a2b90145393ed272f'
_SEED_DIAG_PYTHON = '/usr/bin/python3.12'
_SEED_DIAG_PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
_SEED_DIAG_SQLITE_VERSION = (3, 45, 1)
_SEED_DIAG_OBSERVED_REPAIR_COMMAND = 'hermes update'
_SEED_DIAG_LABELS = ('state.db', 'runs_idempotency.db', 'response_store.db')
_SEED_DIAG_CHECKS = ('preflight', 'response_preflight', 'before_epoch', 'response_before_epoch',
          'after_epoch', 'response_after_epoch')
_SEED_DIAG_SOURCE_PINS = {
    'native/hermes_state_wal.py':
        '5fb152d748a373995093e253b10af3ab662f7331202ebd99d2897340d14b0e61',
    'native/hermes_state.py':
        'c24484b3026a377621dd1a0f1d23de8e0d9d9d0b6d9600d47cee9368646c9577',
    'native/gateway/platforms/api_server_run_idempotency.py':
        '4ad0c20dfe220cf0aac8b340702b54621f7ecdb075799816407406c5cd733c03',
    'native/gateway/platforms/api_server_response_store.py':
        '9d787af0433af6d99c0518ba7bcabfbea06b73bd3f8da48e47e63464e1e0f3ad',
}


def _seed_diag_require(value, reason):
    if not value:
        raise AcceptanceRejected(reason)


def _seed_diag_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _seed_diag_canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _seed_diag_one(rows, reason):
    _seed_diag_require(len(rows) == 1, reason)
    return rows[0]


def _seed_diag_assignment(tree, name):
    node = _seed_diag_one([n for n in tree.body if isinstance(n, ast.Assign)
               and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
               and n.targets[0].id == name], 'diagnostic_source_assignment')
    return node.value


def _seed_diag_dictionary_value(node, key):
    _seed_diag_require(isinstance(node, ast.Dict), 'diagnostic_source_dictionary')
    return _seed_diag_one([value for k, value in zip(node.keys, node.values)
               if isinstance(k, ast.Constant) and k.value == key],
               'diagnostic_source_dictionary_key')


def _seed_diag_function(tree, name):
    return _seed_diag_one([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name],
               'diagnostic_source_function')


def _seed_diag_expected_stderr(native_sources, *, sqlite_version, interpreter):
    """Render only the observed DELETE branch from four byte-pinned sources."""
    _seed_diag_require(type(native_sources) is dict and set(native_sources) == set(_SEED_DIAG_SOURCE_PINS),
            'diagnostic_source_inventory')
    trees = {}
    for name, expected in _SEED_DIAG_SOURCE_PINS.items():
        raw = native_sources[name]
        _seed_diag_require(type(raw) is bytes and 0 < len(raw) <= 262144 and _seed_diag_sha(raw) == expected,
                'diagnostic_source_pin')
        trees[name] = ast.parse(raw, filename=name, mode='exec')
    _seed_diag_require(type(sqlite_version) is tuple and len(sqlite_version) == 3
            and all(type(n) is int for n in sqlite_version) and sqlite_version == _SEED_DIAG_SQLITE_VERSION,
            'diagnostic_sqlite_version')
    _seed_diag_require(interpreter == _SEED_DIAG_PYTHON and type(interpreter) is str, 'diagnostic_interpreter')
    wal = trees['native/hermes_state_wal.py']
    entry = _seed_diag_dictionary_value(_seed_diag_assignment(wal, '_ONCE_LOGS'), 'wal_reset_bug')
    _seed_diag_require(isinstance(entry, ast.Tuple) and len(entry.elts) == 4
            and ast.dump(entry.elts[2]) ==
                ast.dump(ast.parse('logging.WARNING', mode='eval').body)
            and isinstance(entry.elts[3], ast.Constant) and type(entry.elts[3].value) is str,
            'diagnostic_source_warning_format')
    template = entry.elts[3].value
    action = ast.literal_eval(_seed_diag_dictionary_value(_seed_diag_assignment(wal, '_WAL_RESET_BUG_ACTIONS'), 'delete'))
    _seed_diag_require(action == 'using journal_mode=DELETE instead of enabling WAL',
            'diagnostic_source_action')
    log = _seed_diag_function(wal, '_log_wal_reset_bug_once')
    call = _seed_diag_one([n for n in ast.walk(log) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id == '_log_once'],
               'diagnostic_source_logger')
    expected_call = ast.parse(
        "_log_once('wal_reset_bug', db_label, sqlite3.sqlite_version, sys.executable, action, _wal_reset_repair_hint)",
        mode='eval').body
    _seed_diag_require(ast.dump(call) == ast.dump(expected_call), 'diagnostic_source_argument_order')
    hint_function = _seed_diag_function(wal, '_wal_reset_repair_hint')
    hint = _seed_diag_one([n.value for n in ast.walk(hint_function)
               if isinstance(n, ast.Return) and isinstance(n.value, ast.JoinedStr)
               and len(n.value.values) == 3
               and isinstance(n.value.values[0], ast.Constant)
               and n.value.values[0].value ==
                    'Hermes-managed installs can repair the embedded runtime with ' + chr(96)],
               'diagnostic_source_repair_hint')
    middle = hint.values[1]
    _seed_diag_require(isinstance(middle, ast.FormattedValue) and isinstance(middle.value, ast.Name)
            and middle.value.id == 'cmd' and middle.conversion == -1 and middle.format_spec is None
            and isinstance(hint.values[2], ast.Constant) and hint.values[2].value == chr(96),
            'diagnostic_source_repair_hint_shape')
    repair = hint.values[0].value + _SEED_DIAG_OBSERVED_REPAIR_COMMAND + hint.values[2].value
    for name, label in zip(tuple(_SEED_DIAG_SOURCE_PINS)[1:], _SEED_DIAG_LABELS):
        calls = [n for n in ast.walk(trees[name]) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'apply_wal_with_fallback'
                 and any(k.arg == 'db_label' and isinstance(k.value, ast.Constant)
                         and k.value.value == label for k in n.keywords)]
        _seed_diag_require(len(calls) == 1, 'diagnostic_constructor_label')
    version = '.'.join(map(str, sqlite_version))
    raw = ''.join(template % (label, version, interpreter, action, repair) + '\n'
                  for label in _SEED_DIAG_LABELS).encode('utf-8')
    _seed_diag_require(len(raw) == 1265 and raw.count(b'\n') == 3, 'diagnostic_expected_shape')
    return raw, {'warningTemplateSha256': _seed_diag_sha(template.encode('utf-8')),
                 'deleteActionSha256': _seed_diag_sha(action.encode('utf-8')),
                 'repairCommandBasis': 'exact previously observed value in pinned emitter wrapper',
                 'repairCommand': _SEED_DIAG_OBSERVED_REPAIR_COMMAND}


def _seed_diag_seed_handoff(seed):
    _seed_diag_require(type(seed) is dict and seed.get('kind') == 'R168A1_TASK_FREE_SERVICE_SEED'
            and seed.get('result') == 'PASS' and seed.get('state') == 'SERVICE_SEED_CREATED'
            and seed.get('phase') == 'COMPLETE', 'diagnostic_seed_terminal')
    _seed_diag_require(all(seed.get(k) is True for k in ('allThreeConnectionsPhysicallyClosed',
        'profileLeaseReleasedNormally', 'serviceCapturedWhileLeaseHeld', 'normalLoopShutdown',
        'zeroExecutionCapacity', 'sourceAndDependencyBytesReadBackBeforeAndAfter',
        'runtimeBinaryBytesReadBackBeforeAndAfter')), 'diagnostic_seed_proof')
    _seed_diag_require(all(seed.get(k) is False for k in ('apiAdmissionPublished', 'providerExchangePerformed',
        'serviceAccepted', 'kernelAccepted', 'fullD3BAccepted', 'automaticCleanup', 'automaticRetry')),
        'diagnostic_seed_scope')
    _seed_diag_require(all(type(seed.get(k)) is int and seed[k] == 0 for k in ('executedTasks', 'realModelCalls',
        'listenersCreated', 'outstandingAsyncTasks', 'outstandingThreads')), 'diagnostic_seed_work')
    _seed_diag_require(seed.get('ownerState') == 'CLOSED' and seed.get('consumerState') == 'DETACHED'
            and seed.get('completedChecks') == list(_SEED_DIAG_CHECKS)
            and seed.get('installationReceiptSha256') == _SEED_DIAG_RECEIPT_SHA
            and seed.get('harnessCommit') == _SEED_DIAG_HARNESS and seed.get('nativeFeature') == _SEED_DIAG_NATIVE
            and type(seed.get('sourceFileCount')) is int and seed['sourceFileCount'] == 878
            and type(seed.get('dependencyFileCount')) is int and seed['dependencyFileCount'] == 1162
            and type(seed.get('qualifiedNativeSourceCount')) is int
            and seed['qualifiedNativeSourceCount'] == 760, 'diagnostic_seed_source_and_checks')
    source = seed.get('sourceIdentity')
    _seed_diag_require(type(source) is dict and source.get('sha256') == _SEED_DIAG_SEED_SHA,
            'diagnostic_seed_producer_pin')
    binaries = seed.get('runtimeBinaries')
    _seed_diag_require(type(binaries) is dict, 'diagnostic_seed_runtime_pin')
    binary = binaries.get('python')
    _seed_diag_require(type(binary) is dict and binary.get('path') == _SEED_DIAG_PYTHON
            and binary.get('sha256') == _SEED_DIAG_PYTHON_SHA, 'diagnostic_seed_runtime_pin')
    wire = seed.get('handoff')
    _seed_diag_require(type(wire) is str and 0 < len(wire) <= 16384, 'diagnostic_handoff_bound')
    raw = wire.encode('ascii')
    _seed_diag_require(_seed_diag_sha(raw) == seed.get('handoffSha256'), 'diagnostic_handoff_hash')
    def unique(rows):
        result = {}
        for key, value in rows:
            _seed_diag_require(key not in result, 'diagnostic_handoff_duplicate')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    _seed_diag_require(type(value) is dict and set(value) == {'protocol', 'state', 'response', 'service'}
            and _seed_diag_canonical(value) == raw and value['protocol'] == 'alaz-service-startup-v1',
            'diagnostic_handoff_format')
    state, response, service = value['state'], value['response'], value['service']
    _seed_diag_require(all(type(row) is dict for row in (state, response, service))
            and state.get('journal_mode') == 'delete'
            and type(state.get('epoch')) is int and state['epoch'] == 1
            and type(service.get('epoch')) is int and service['epoch'] == 1
            and type(seed.get('previousEpoch')) is int and seed['previousEpoch'] == 1
            and state.get('instance_id') == service.get('instance_id') == seed.get('instanceId')
            and service.get('home') == seed.get('home'), 'diagnostic_handoff_delete')
    identities = seed.get('databaseIdentities')
    _seed_diag_require(type(identities) is list and len(identities) == 3
            and all(type(pair) is list and len(pair) == 2
                    and all(type(n) is int and n >= 0 for n in pair)
                    and pair[1] > 0 for pair in identities)
            and len({tuple(pair) for pair in identities}) == 3
            and _seed_diag_canonical(service.get('database_identities')) == _seed_diag_canonical(identities)
            and _seed_diag_canonical(state.get('state_identity')) == _seed_diag_canonical(identities[0])
            and _seed_diag_canonical(state.get('replay_identity')) == _seed_diag_canonical(identities[1])
            and _seed_diag_canonical(response.get('response_identity')) == _seed_diag_canonical(identities[2]),
            'diagnostic_handoff_identities')
    return value


def classify_seed_diagnostics(stderr, seed, native_sources, *, archive_sha256,
                         sqlite_version, interpreter, exit_code, pipes_complete):
    """Classify exact warnings after original PID, handoff and store binding gates.

    Supplied source bytes come from the complete verified archive. AST parsing
    never executes those programs or opens a live database. The linked SQLite
    version is observed from the already loaded seed module, not inferred from
    the text. This separate receipt cannot grant service acceptance or revise a
    prior UNKNOWN. The repair command is the exact previously observed value;
    its pinned emitter wrapper is derived without rerunning native detection.
    """
    _seed_diag_require(type(exit_code) is int and exit_code == 0 and pipes_complete is True,
            'diagnostic_original_terminal')
    _seed_diag_require(archive_sha256 == _SEED_DIAG_ARCHIVE_SHA, 'diagnostic_archive_pin')
    _seed_diag_require(type(stderr) is bytes and 0 < len(stderr) <= 4096, 'diagnostic_stderr_bound')
    handoff = _seed_diag_seed_handoff(seed)
    expected, source_proof = _seed_diag_expected_stderr(native_sources, sqlite_version=sqlite_version,
                                           interpreter=interpreter)
    _seed_diag_require(stderr == expected, 'diagnostic_unexpected_stderr')
    return {'kind': 'R168_EXACT_NATIVE_SQLITE_DIAGNOSTICS',
        'classification': 'EXACT_PINNED_NATIVE_DELETE_WARNINGS', 'qualified': True,
        'stderrBytes': len(stderr), 'stderrSha256': _seed_diag_sha(stderr),
        'warningCount': 3, 'databaseLabelsInOrder': list(_SEED_DIAG_LABELS),
        'sqliteVersionObservedByCaller': list(sqlite_version), 'pythonPath': interpreter,
        'nativeSourcePins': dict(_SEED_DIAG_SOURCE_PINS), 'archiveSha256': archive_sha256,
        'seedSourceSha256': _SEED_DIAG_SEED_SHA, 'seedHandoffSha256': seed['handoffSha256'],
        'declaredJournalMode': handoff['state']['journal_mode'],
        'deleteModeBasis': 'pinned seed six preopen/live checks plus three physical closes',
        'derivation': source_proof, 'nativeSourceExecutedByClassifier': False,
        'liveDatabaseOpenedByClassifier': False, 'installedHandoffCodecRunByClassifier': False,
        'fullSharedLibraryClosureAccepted': False, 'serviceAccepted': False,
        'kernelAccepted': False, 'priorUnknownReclassified': False,
        'automaticCleanup': False, 'automaticRetry': False}


class Controller:
    def __init__(self, attempt, mode):
        require(type(attempt) is str and re.fullmatch(r'(normal|lostreply)-[0-9]{2}', attempt),
                'qa_attempt_id')
        require(mode in ('normal', 'lostreply') and attempt.startswith(mode + '-'), 'qa_attempt_mode')
        self.attempt, self.mode = attempt, mode
        self.base = Path('/srv/alaz-r168a1-' + attempt)
        self.run = Path('/run/alaz-r168a1-' + attempt)
        self.image = self.base / 'images/state.ext4'
        self.mount = self.base / 'mount'
        self.profile = self.mount / 'profile'
        self.scratch = self.base / 'scratch'
        self.canary = self.base / 'canary.txt'
        self.cgroup = Path('/sys/fs/cgroup/alaz-r168a1-' + attempt)
        self.anchor = Path('/tmp/alaz-ipc-r168a1-' + attempt)
        self.phase, self.events, self.effects = 'PREFLIGHT', [], False
        self.volume = self.server = self.seed = self.broker = self.formatter = None
        self.seed_result = self.installed = self.modules = None
        self.seed_sqlite_version = None
        self.clients, self.bootstrap = [], []
        self.connection = None
        self.broker_control = None
        self.broker_spec = None

    def event(self, name):
        self.phase = name
        self.events.append(name)

    def fresh(self):
        for p in (self.base, self.run, self.cgroup, self.anchor):
            require(not os.path.lexists(p), 'qa_fresh_attempt_required')

    def bootstrap_probe(self, manifest):
        self.event('QUALIFY_ACTUAL_OS_BOOTSTRAP')
        contexts = (
            ('root', 0, 0, 'qa', dict(ENV), '/'),
            ('gateway', 23001, 23003, 'qa', dict(ENV), '/'),
            ('root', 0, 0, 'worker', {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, '/'),
            ('root', 0, 0, 'supervised', {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}, '/'),
            ('gateway', 23001, 23003, 'preopen',
                {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}, str(INSTALL)),
        )
        for name, uid, gid, context, environment, cwd in contexts:
            attempt = {'phase': 'BOOTSTRAP_' + name + '_' + context, 'process': None}
            self.bootstrap.append(attempt)
            p = subprocess.Popen([PYTHON, '-I', '-B', str(QA / PROBE), '--actor', name,
                    '--context', context, '--expected-source-sha256', manifest['files'][PROBE]['sha256'],
                    '--contract', str(QA / CONTRACT),
                    '--expected-contract-sha256', manifest['files'][CONTRACT]['sha256']],
                cwd=cwd, env=environment, user=uid, group=gid, extra_groups=[],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                close_fds=True, bufsize=0)
            attempt['process'] = p
            attempt['startTicks'] = start_ticks(p.pid, live=False)
            out, err = collect(attempt, 20)
            require(p.returncode == 0 and not err, 'qa_bootstrap_refused')
            result = parse(out, 65536)
            require(result.get('result') == 'PASS', 'qa_bootstrap_unaccepted')
            attempt.update(phase='COMPLETE', result=result)

    def provision(self):
        self.event('PROVISION_NEW_ATTEMPT')
        self.effects = True
        os.umask(0o022)
        for p, mode, uid, gid in ((self.base, 0o755, 0, 0),
                (self.image.parent, 0o700, 0, 0), (self.mount, 0o700, 0, 0),
                (self.scratch, 0o700, 23001, 23003), (self.run, 0o755, 0, 0),
                (self.run / 'broker', 0o710, 23002, 23003),
                (self.run / 'control', 0o700, 0, 0),
                (self.cgroup, 0o755, 0, 0), (self.anchor, 0o700, 0, 0)):
            p.mkdir(mode=mode)
            os.chown(p, uid, gid)
            require(stat.S_IMODE(p.stat().st_mode) == mode, 'qa_directory_mode')
        exclusive(self.canary, b'R168 owned protected read export; no secrets.\n', 0o644)
        fd = os.open(self.image, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'r+b') as stream:
            stream.truncate(64 * 1024 * 1024)
            stream.flush()
            os.fsync(stream.fileno())
        self.event('FORMAT_NEW_IMAGE')
        attempt = self.formatter = {'phase': 'SPAWNING', 'process': None}
        p = subprocess.Popen(['/usr/sbin/mke2fs', '-t', 'ext4', '-q', '-F', '-E',
            'lazy_itable_init=0,lazy_journal_init=0', str(self.image)], cwd='/', env=dict(ENV),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        attempt['process'] = p
        attempt['startTicks'] = start_ticks(p.pid, live=False)
        collect(attempt, 20, 8192)
        require(p.returncode == 0, 'qa_formatter_failed')
        attempt['phase'] = 'COMPLETE'
        s, parent = self.image.stat(), self.image.parent.stat()
        return self.modules.image.ImagePin(str(self.image), s.st_dev, s.st_ino, s.st_size,
                                          s.st_uid, s.st_gid, parent.st_dev, parent.st_ino)

    def start_broker(self):
        self.event('START_REAL_PING_BROKER')
        reader, writer = os.pipe2(os.O_CLOEXEC)
        self.broker_control = writer
        pipe = os.fstat(reader)
        spec = {'schema': 1, 'kind': 'R168A1_PING_BROKER', 'attemptId': self.attempt,
            'brokerDirectory': str(self.run / 'broker'), 'principalContract': dict(PRINCIPAL),
            'signingKey': uuid.uuid4().hex + uuid.uuid4().hex,
            'scope': digest(('scope:' + self.attempt).encode()),
            'binding': digest(('binding:' + self.attempt).encode()),
            'policyFingerprint': self.modules.budget.ExecutionPolicy(**execution_policy()).fingerprint,
            'owner': {'pid': os.getpid(), 'startTicks': start_ticks(os.getpid()), 'uid': 0},
            'control': {'dev': pipe.st_dev, 'ino': pipe.st_ino, 'nonce': uuid.uuid4().hex},
            'maxLifetimeSeconds': 300, 'expectedPings': 1}
        self.broker_spec = spec
        expected_readback = {'installationReceiptSha256': RECEIPT_SHA,
            'pythonSha256': self.installed.binaries['python']['sha256'],
            'moduleSha256': {name: digest(trusted_read(INSTALL / 'packages/claw-hermes' / (name + '.py')))
                for name in ('provider_broker', 'provider_egress', 'host_principal',
                             'execution_budget', 'recovery_inspector', 'request_view', 'source_capture')}}
        self.broker_readback = expected_readback
        raw = canonical(spec)
        exclusive(self.base / 'broker-spec.json', raw)
        specfd = os.open(self.base / 'broker-spec.json', os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        logs = []
        try:
            for name in ('stdout', 'stderr'):
                logs.append(os.open(self.base / ('broker-' + name + '.log'),
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600))
            self.broker = {'phase': 'SPAWNING', 'process': None}
            p = subprocess.Popen([PYTHON, '-I', '-S', '-B', str(QA / BROKER),
                '--spec-fd', str(specfd), '--control-fd', str(reader),
                '--expected-spec-sha256', digest(raw)], cwd='/', env=dict(ENV),
                user=23002, group=23003, extra_groups=[], pass_fds=(specfd, reader),
                stdin=subprocess.DEVNULL, stdout=logs[0], stderr=logs[1], close_fds=True)
            self.broker['process'] = p
            self.broker['startTicks'] = start_ticks(p.pid, live=False)
        finally:
            os.close(specfd)
            os.close(reader)
            for fd in logs:
                os.close(fd)
        end = time.monotonic() + 15
        path = self.base / 'broker-stdout.log'
        while True:
            require(p.poll() is None and time.monotonic() < end, 'qa_broker_readiness_unknown')
            raw = path.read_bytes()
            require(len(raw) <= 65536, 'qa_broker_readiness_bound')
            if raw.endswith(b'\n'):
                break
            time.sleep(.02)
        ready = parse(raw, 65536)
        require(ready.get('kind') == 'R168A1_PING_BROKER_READY'
                and ready.get('attemptId') == self.attempt and ready.get('pid') == p.pid
                and ready.get('owner') == spec['owner']
                and ready.get('principalContract') == PRINCIPAL
                and canonical({k: ready.get(k) for k in expected_readback}) == canonical(expected_readback)
                and type(ready.get('expectedPings')) is int and ready['expectedPings'] == 1
                and type(ready.get('maxLifetimeSeconds')) is int and ready['maxLifetimeSeconds'] == 300,
                'qa_broker_readiness_binding')
        self.verify_broker_receipt(ready, 'ready.json')
        broker = ready.get('broker')
        require(type(broker) is dict and set(broker) == {'brokerId', 'socketPath', 'routeFingerprint', 'pid', 'backend'}
                and type(broker['brokerId']) is str and re.fullmatch('[a-f0-9]{32}', broker['brokerId'])
                and broker['socketPath'] == str(self.run / 'broker/egress.sock')
                and broker['routeFingerprint'] == self.modules.egress.route_fingerprint('http://127.0.0.1:1/v1', MODEL)
                and broker['pid'] == p.pid and broker['backend'] == 'linux_unix_credential_broker',
                'qa_broker_identity')
        observed_socket = self.modules.principal.socket_identity(PRINCIPAL, broker['socketPath'])
        require(canonical(ready.get('socketIdentity')) == canonical(observed_socket),
                'qa_broker_socket_identity')
        self.broker.update(phase='READY', ready=ready, readySha256=digest(raw))
        return ready['broker']

    def verify_broker_receipt(self, value, name):
        path = self.run / 'broker' / name
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    and (info.st_uid, info.st_gid) == (23002, 23003)
                    and stat.S_IMODE(info.st_mode) == 0o600
                    and 0 < info.st_size <= 32768, 'qa_broker_receipt_metadata')
            raw = os.read(fd, 32769)
            require(len(raw) == info.st_size
                    and stamp(info) == stamp(os.fstat(fd)) == stamp(path.lstat()),
                    'qa_broker_receipt_changed')
        finally:
            os.close(fd)
        require(value.get('receipt') == {'file': name, 'sha256': digest(raw), 'bytes': len(raw)}
                and canonical({k: v for k, v in value.items() if k != 'receipt'}) == raw,
                'qa_broker_receipt_binding')

    def projection(self):
        ipc = {'version': 2, 'mode': 'projected_root_principal', 'root': str(self.anchor),
               'brokerSocket': str(self.run / 'broker/egress.sock'),
               'principalContract': dict(PRINCIPAL)}
        fs = {'version': 1, 'enabled': True,
            'readonly': ['/usr/bin', '/usr/lib/python3.12', '/usr/lib/x86_64-linux-gnu',
                '/usr/lib64', '/usr/lib/locale', str(INSTALL), '/etc/ld.so.cache',
                '/etc/mime.types', '/dev/urandom'],
            'writable': ['/dev/null', str(self.scratch)],
            'protected': [str(self.canary)], 'self_process_metadata': True}
        return ipc, fs

    def scope_only_worker(self):
        v = self.volume
        v._owned()
        require(v.worker.poll() is None
                and (v.scope / 'cgroup.procs').read_text().split() == [str(v.worker.pid)]
                and not any(p.is_dir() for p in v.scope.iterdir()), 'qa_other_volume_users')

    def seed_once(self, manifest, boundary):
        self.event('REAL_NATIVE_SERVICE_SEED')
        v = self.volume
        require(self.seed is None and v.stage == 'RUNNING', 'qa_seed_once')
        self.scope_only_worker()
        fd = os.open('/proc/' + str(v.worker.pid) + '/ns/mnt', os.O_RDONLY | os.O_CLOEXEC)
        nsino = os.fstat(fd).st_ino
        contract = {'protocol': boundary.PROTOCOL, 'attemptId': self.attempt,
            'controller': {'pid': os.getpid(), 'startTicks': start_ticks(os.getpid())},
            'worker': {'pid': v.worker.pid, 'startTicks': start_ticks(v.worker.pid)},
            'scope': {'path': str(v.scope), 'device': v.scope_id[0], 'inode': v.scope_id[1]},
            'namespace': {'fd': fd, 'inode': nsino}, 'image': asdict(v.pin),
            'token': v.token, 'fence': {'path': str(v.fence), 'sha256': digest(v.fence_bytes)},
            'mountpoint': str(self.mount), 'profile': str(self.profile), 'loopNumber': v.loop_number,
            'principal': dict(PRINCIPAL),
            'installation': {'path': str(INSTALL), 'receiptSha256': RECEIPT_SHA},
            'bootstrap': {'path': str(QA / SEED), 'sha256': manifest['files'][SEED]['sha256']},
            'childSha256': manifest['files'][CHILD]['sha256'],
            'configSha256': digest((self.base / 'seed-config.json').read_bytes()),
            'seedInstanceId': 'r168a1-' + self.attempt + '-seed'}
        payload = boundary.encode_contract(contract)
        self.seed = {'phase': 'SPAWNING', 'process': None,
                     'capture': self.modules.capture.PipeCapture(65536)}
        try:
            p = subprocess.Popen([PYTHON, '-I', '-S', '-B', str(QA / CHILD)], cwd='/', env=dict(ENV),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                pass_fds=(fd,), close_fds=True, bufsize=0)
            self.seed['process'] = p
            self.seed['startTicks'] = start_ticks(p.pid, live=False)
        finally:
            os.close(fd)
        self.seed['phase'] = 'RUNNING'
        capture = self.seed['capture']
        capture.send_once(p, payload, 60)
        require(p.returncode == 0 and capture.complete, 'qa_seed_exit_or_output')
        self.scope_only_worker()
        result = parse(bytes(capture.stdout_bytes), 65536)
        require(result.get('kind') == 'R168A1_TASK_FREE_SERVICE_SEED'
                and result.get('result') == 'PASS' and result.get('state') == 'SERVICE_SEED_CREATED'
                and result.get('pid') == p.pid and result.get('parentPid') == os.getpid()
                and result.get('startTicks') == self.seed['startTicks']
                and result.get('parentStartTicks') == contract['controller']['startTicks']
                and result.get('resUid') == [23001] * 3 and result.get('resGid') == [23003] * 3
                and result.get('supplementaryGroups') == []
                and result.get('mountNamespaceInode') == nsino
                and result.get('userNamespace') == USER_NS
                and result.get('installationReceiptSha256') == RECEIPT_SHA
                and result.get('ownerState') == 'CLOSED' and result.get('consumerState') == 'DETACHED'
                and all(result.get(k) is True for k in ('allThreeConnectionsPhysicallyClosed',
                    'normalLoopShutdown', 'profileLeaseReleasedNormally', 'zeroExecutionCapacity'))
                and all(type(result.get(k)) is int and result[k] == 0 for k in
                    ('outstandingAsyncTasks', 'outstandingThreads', 'executedTasks', 'realModelCalls', 'listenersCreated')),
                'qa_seed_binding')
        wire = result['handoff'].encode('ascii')
        require(digest(wire) == result['handoffSha256'], 'qa_seed_handoff_hash')
        record = self.modules.handoff.decode(wire, expected_home=str(self.profile))
        root = Path('/proc/' + str(v.worker.pid) + '/root')
        observed = []
        for name in ('', '/state.db', '/runs_idempotency.db', '/response_store.db'):
            info = (root / (str(self.profile).lstrip('/') + name)).lstat()
            require((stat.S_ISDIR(info.st_mode) if not name else stat.S_ISREG(info.st_mode))
                    and (info.st_uid, info.st_gid) == (23001, 23003), 'qa_seed_store_actor')
            observed.append((info.st_dev, info.st_ino))
        require(record.state.epoch == record.service.epoch == 1
                and record.state.instance_id == record.service.instance_id == contract['seedInstanceId']
                and tuple(record.service.home_identity) == observed[0]
                and list(record.service.database_identities) == observed[1:], 'qa_seed_store_binding')
        # Source-derived stderr qualification comes only after all original
        # child, installed handoff, profile and three-store close checks above.
        # Keep the producer's immutable PASS document separate from this receipt.
        self.seed['diagnostics'] = classify_seed_diagnostics(
            bytes(capture.stderr_bytes), result,
            {name: self.installed.prepared.source[name] for name in _SEED_DIAG_SOURCE_PINS},
            archive_sha256=self.installed.prepared.archive_sha256,
            sqlite_version=self.seed_sqlite_version, interpreter=PYTHON,
            exit_code=p.returncode, pipes_complete=capture.complete)
        self.seed_result, self.seed['phase'] = result, 'COMPLETE'
        return record

    def cli(self, command, request_id):
        self.event('CLI_' + command.upper().replace('-', '_'))
        c = self.connection
        env = {**ENV, 'ALAZ_SERVICE_SOCKET': c['socketPath'], 'ALAZ_SERVICE_ID': c['serviceId'],
            'ALAZ_SERVICE_OWNER_PID': str(c['owner']['pid']),
            'ALAZ_SERVICE_OWNER_START_TICKS': str(c['owner']['startTicks']),
            'ALAZ_SERVICE_OWNER_TOKEN': c['owner']['token']}
        attempt = {'phase': 'SPAWNING', 'process': None, 'command': command, 'requestId': request_id}
        self.clients.append(attempt)
        p = subprocess.Popen([NODE, str(INSTALL / 'scripts/alaz_local.mjs'), command,
            '--request-id', request_id, '--request-timeout-ms', '55000'], cwd='/', env=env,
            user=0, group=0, extra_groups=[], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, bufsize=0)
        attempt['process'] = p
        attempt['startTicks'] = start_ticks(p.pid, live=False)
        end = time.monotonic() + 55
        while True:
            require(time.monotonic() < end, 'qa_cli_dispatch_timeout_unknown')
            served = self.server.serve_one(timeout=.1)
            if served['state'] != 'IDLE' or p.poll() is not None:
                break
        attempt['served'] = served
        out, err = collect(attempt, 5)
        require(p.returncode == 0 and not err and served['state'] == 'REPLIED', 'qa_cli_unconfirmed')
        # The actual Node CLI uses indented JSON; its internal wire is validated
        # by the unchanged client. No invented canonical output requirement.
        result = json.loads(out.decode('utf-8'))
        require(type(result) is dict and result.get('command') == command
                and result.get('serviceId') == c['serviceId']
                and result.get('requestId') == request_id and result.get('retryAllowed') is False
                and result.get('kernelVerified') is False and result.get('error') is None
                and result.get('owner') == {k: c['owner'][k] for k in ('pid', 'startTicks')},
                'qa_cli_report_binding')
        attempt.update(phase='COMPLETE', result=result)
        return result

    def live_service_observation(self):
        self.event('OBSERVE_PROJECTED_SERVICE_KERNEL')
        child = self.volume._service_child
        p = child.process
        require(p.poll() is None, 'qa_ready_child_not_live')
        root = Path('/proc', str(p.pid), 'root')
        status = {}
        for line in Path('/proc', str(p.pid), 'status').read_text().splitlines():
            key, _, value = line.partition(':')
            if key in ('Uid', 'Gid', 'Groups', 'NoNewPrivs', 'CapEff', 'CapBnd'):
                status[key] = value.split()
        require(status['Uid'] == ['23001'] * 4 and status['Gid'] == ['23003'] * 4
                and status['Groups'] == [] and status['NoNewPrivs'] == ['1']
                and int(status['CapEff'][0], 16) == int(status['CapBnd'][0], 16) == 0,
                'qa_ready_gateway_principal')
        excluded = ['/etc/python3.12/sitecustomize.py', '/usr/local/lib/python3.12/dist-packages',
                    '/usr/lib/python3/dist-packages', '/mnt/c/Windows']
        # An inaccessible proc-root must never be mistaken for absent paths.
        # This known regular source proves positive access before exclusion.
        observed_receipt = (root / 'opt/alaz-r167a1/.alaz-service-installation.json').read_bytes()
        require(digest(observed_receipt) == RECEIPT_SHA, 'qa_projected_root_access_unproved')
        for name in excluded:
            try:
                (root / name.lstrip('/')).lstat()
            except FileNotFoundError:
                pass
            else:
                raise AcceptanceRejected('qa_projected_ambient_path_present')
        mounts = Path('/proc', str(p.pid), 'mountinfo').read_bytes()
        namespaces = {n: os.readlink('/proc/' + str(p.pid) + '/ns/' + n) for n in ('mnt', 'net', 'user')}
        require(namespaces['user'] == USER_NS
                and namespaces['mnt'] != os.readlink('/proc/self/ns/mnt')
                and namespaces['net'] != os.readlink('/proc/self/ns/net'), 'qa_projected_namespaces')
        members = sorted(map(int, (self.volume.scope / 'cgroup.procs').read_text().split()))
        require(members == sorted([self.volume.worker.pid, p.pid]), 'qa_service_cgroup_members')
        return {'pid': p.pid, 'startTicks': start_ticks(p.pid), 'principal': status,
                'namespaces': namespaces, 'excludedPathsAbsent': excluded,
                'mountinfoSha256': digest(mounts), 'mountinfoBytes': len(mounts),
                'cgroupMembers': members, 'runtimeImportTraceClaimed': False,
                'projectedBootstrapPathExclusionObserved': True}

    def lose_close_reply(self, manifest_sha, request_id):
        self.event('SEND_CLOSE_THEN_DROP_ONLY_REPLY')
        c = self.connection
        payload = canonical({'socketPath': c['socketPath'], 'request': {
            'protocol': 'alaz-supervisor-control-v1', 'command': 'close',
            'expectedOwner': c['owner'], 'requestId': request_id, 'serviceId': c['serviceId']}})
        attempt = {'phase': 'SPAWNING', 'process': None, 'command': 'close-reply-drop',
                   'requestId': request_id, 'capture': self.modules.capture.PipeCapture(4096)}
        self.clients.append(attempt)
        p = subprocess.Popen([PYTHON, '-I', '-S', '-B', str(QA / ENTRY),
            '--manifest-sha256', manifest_sha, '--attempt', self.attempt,
            '--mode', self.mode, '--drop-reply-client'], cwd='/', env=dict(ENV),
            user=0, group=0, extra_groups=[], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, bufsize=0)
        attempt['process'] = p
        attempt['startTicks'] = start_ticks(p.pid, live=False)
        # Complete sender EOF before accept: the exact close is queued once,
        # and the caller has already closed its read side before product reply.
        attempt['capture'].send_once(p, payload, 5)
        require(p.returncode == 0 and attempt['capture'].complete
                and not attempt['capture'].stderr_bytes, 'qa_fault_sender_unknown')
        result = parse(bytes(attempt['capture'].stdout_bytes), 4096)
        require(result == {'kind': 'R168_CLOSE_REPLY_DROPPED', 'requestId': request_id,
            'requestSha256': digest(payload), 'sentOnce': True, 'responseRead': False},
            'qa_fault_sender_binding')
        served = self.server.serve_one(timeout=1)
        require(served['state'] == 'REPLY_LOST' and served['requestDispatched'] is True
                and served['ownerRetained'] is True, 'qa_close_reply_not_lost')
        require(self.volume.stage == 'CLOSED' and self.server._terminal_view is not None,
                'qa_lost_reply_terminal_proof_absent')
        attempt.update(phase='COMPLETE', served=served, result=result)
        return {'requestId': request_id, 'served': served, 'sender': result,
                'closeRepeated': False, 'terminalProofRetainedBeforeObservation': True}

    def stop_broker(self):
        self.event('STOP_ORIGINAL_PING_BROKER')
        require(self.volume.stage == 'CLOSED' and self.broker['phase'] == 'READY', 'qa_broker_stop_order')
        ready = self.broker['ready']['broker']
        raw = canonical({'schema': 1, 'operation': 'shutdown', 'attemptId': self.attempt,
                         'brokerId': ready['brokerId'], 'nonce': self.broker_spec['control']['nonce']})
        self.broker['phase'] = 'STOPPING'
        require(os.write(self.broker_control, raw) == len(raw), 'qa_broker_stop_short_write')
        os.close(self.broker_control)
        self.broker_control = None
        p = self.broker['process']
        require(p.wait(timeout=10) == 0, 'qa_broker_exit_unconfirmed')
        out = trusted_read(self.base / 'broker-stdout.log', 65536)
        err = (self.base / 'broker-stderr.log').read_bytes()
        require(not err, 'qa_broker_stderr')
        frames = [parse(line + b'\n', 65536) for line in out.splitlines()]
        require(len(frames) == 2 and frames[0] == self.broker['ready'], 'qa_broker_terminal_frames')
        final = frames[1]
        self.broker.update(phase='COMPLETE', final=final,
            stdoutSha256=digest(out), stdoutBytes=len(out), stderrSha256=digest(err))
        require(not os.path.lexists(self.run / 'broker/egress.sock'), 'qa_broker_socket_retained')
        # Exact terminal schema is checked by the broker launcher; controller
        # independently binds the observed final and counters below.
        self.verify_broker_receipt(final, 'shutdown.json')
        require(final.get('kind') == 'R168A1_PING_BROKER_TERMINAL'
                and final.get('result') == 'PASS' and final.get('attemptId') == self.attempt
                and final.get('pid') == p.pid and final.get('owner') == self.broker_spec['owner']
                and final.get('broker') == ready
                and final.get('shutdownCommandAccepted') is True
                and final.get('closeConfirmed') is True and final.get('reason') is None
                and final.get('controllerMustRetainOwnership') is False
                and canonical(final.get('forbiddenEffects')) == canonical({'count': 0, 'events': []})
                and canonical(final.get('readbackBefore')) == canonical(self.broker_readback)
                and canonical(final.get('readbackAfter')) == canonical(self.broker_readback)
                and canonical(final.get('closed')) == canonical({'brokerId': ready['brokerId'], 'pid': p.pid,
                    'socketRemoved': True, 'activeRequests': 0, 'counters': {
                        'physicalAttempts': 0, 'refused': 0, 'pings': 1, 'responses': 0}})
                and all(final.get(k) is False for k in ('automaticRetry', 'upstreamStarted',
                    'providerSendInvokedByLauncher', 'productionAcceptance'))
                and type(final.get('realModelCalls')) is int and final['realModelCalls'] == 0
                and final.get('processExitMustBeObservedByController') is True,
                'qa_broker_terminal_binding')
        return final

    def snapshot(self):
        v = self.volume
        child = getattr(v, '_service_child', None) if v else None
        service = None
        if child is not None:
            service = process_report({'phase': child.phase, 'process': child.process,
                                      'startTicks': child.start_ticks})
            channel = child.channel
            if channel is not None:
                service.update(channel=channel.status(), stdoutEof=channel.stdout_eof,
                    stderrEof=channel.stderr_eof, stdinClosed=channel.stdin_closed,
                    finalFrame=channel.final_frame,
                    stderrTailBase64=base64.b64encode(bytes(channel.stderr_tail)).decode('ascii'),
                    stderrTailIsComplete=channel.stderr_bytes == len(channel.stderr_tail))
        return {'phase': self.phase, 'events': list(self.events), 'effectsAttempted': self.effects,
            'controller': {'pid': os.getpid(), 'startTicks': start_ticks(os.getpid())},
            'volumeStage': v.stage if v else None,
            'workerPid': v.worker.pid if v and v.worker else None,
            'scope': str(v.scope) if v else None, 'fence': str(v.fence) if v else None,
            'seed': {**process_report(self.seed), 'diagnostics': self.seed.get('diagnostics')}
                if self.seed else None, 'service': service,
            'formatter': process_report(self.formatter),
            'bootstrap': [process_report(x) for x in self.bootstrap],
            'clients': [{**process_report(x), 'command': x['command'],
                         'requestId': x['requestId'], 'served': x.get('served'),
                         'result': x.get('result')} for x in self.clients],
            'broker': {**process_report(self.broker), 'ready': self.broker.get('ready'),
                       'final': self.broker.get('final')} if self.broker else None}

    def failure_snapshot(self):
        try:
            return self.snapshot()
        except BaseException as exc:
            return {'phase': self.phase, 'effectsAttempted': self.effects,
                    'events': list(self.events), 'snapshotUnavailable': type(exc).__name__}


def drop_reply_client(controller):
    raw = sys.stdin.buffer.read(16385)
    value = parse(raw, 16384)
    require(set(value) == {'socketPath', 'request'}
            and value['socketPath'] == str(controller.run / 'control/service.sock'), 'qa_fault_client_target')
    request = value['request']
    require(set(request) == {'protocol', 'command', 'expectedOwner', 'requestId', 'serviceId'}
            and request['protocol'] == 'alaz-supervisor-control-v1'
            and request['command'] == 'close'
            and request['expectedOwner']['pid'] == os.getppid()
            and request['expectedOwner']['startTicks'] == start_ticks(os.getppid()), 'qa_fault_client_owner')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(value['socketPath'])
        pid, uid, gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require((pid, uid, gid) == (os.getppid(), 0, 0), 'qa_fault_server_peer')
        connection.sendall(canonical(request))
        connection.shutdown(socket.SHUT_WR)
    return {'kind': 'R168_CLOSE_REPLY_DROPPED', 'requestId': request['requestId'],
            'requestSha256': digest(raw), 'sentOnce': True, 'responseRead': False}


def execute(c, manifest_sha):
    actor()
    c.fresh()
    manifest, sources = verify_inputs(manifest_sha)
    seed = load_source('_r168_reviewed_seed', QA / SEED, sources[SEED])
    verified = seed.verify_installation()
    require(len(verified.prepared.source) == 878 and len(verified.prepared.dependencies) == 1162,
            'qa_installed_inventory')
    c.installed = verified
    c.seed_sqlite_version = seed.sqlite3.sqlite_version_info
    require(digest(trusted_read('/usr/sbin/mke2fs', 4 << 20)) == FORMATTER_SHA, 'qa_formatter_changed')
    c.bootstrap_probe(manifest)
    boundary = load_source('_r168_reviewed_seed_boundary', QA / CHILD, sources[CHILD])
    sys.path.insert(0, str(INSTALL / 'packages/claw-hermes'))
    import service_volume_supervisor as service_volume
    import state_volume_supervisor as volume
    import state_image_lease as image
    import gateway_service_handoff as handoff
    import gateway_projection as projection
    import service_control_server as control
    import supervised_pipe_capture as capture
    import host_principal as principal
    import execution_budget as budget
    import provider_egress as egress
    c.modules = types.SimpleNamespace(service_volume=service_volume, volume=volume, image=image,
        handoff=handoff, projection=projection, control=control, capture=capture,
        principal=principal, budget=budget, egress=egress)
    volume.actor()
    host_namespace = os.readlink('/proc/self/ns/mnt')
    host_mounts = Path('/proc/self/mountinfo').read_bytes()
    pin = c.provision()
    ready = c.start_broker()
    config = configuration(ready, c.canary, c.broker_spec['signingKey'])
    exclusive(c.base / 'seed-config.json', config_bytes(config), 0o600, 23001, 23003)
    ipc, filesystem = c.projection()
    projection.validate(ipc, filesystem)
    export = projection.inspect(ipc, filesystem)
    c.event('BEGIN_ORIGINAL_SERVICE_VOLUME')
    c.volume = service_volume.ServiceVolumeSupervisor.begin(pin, c.cgroup, c.mount)
    original = c.volume
    c.event('ATTACH_ORIGINAL_VOLUME')
    loop_path = original.attach()
    c.event('START_ORIGINAL_SERVICE_WORKER')
    mounted = original.start()
    record = c.seed_once(manifest, boundary)
    c.event('BIND_ORIGINAL_CONTROL_SERVER')
    service_id = uuid.uuid4().hex
    c.server = control.ServiceControlServer(original, ipc, filesystem, record,
        socket_path=str(c.run / 'control/service.sock'), scratch=str(c.scratch),
        instance_id='r168a1-' + c.attempt + '-service', service_id=service_id,
        operation_seconds=40, request_seconds=5, response_seconds=3).bind()
    c.connection = c.server.connection()
    start_id, close_id = uuid.uuid4().hex, uuid.uuid4().hex
    started = c.cli('start', start_id)
    require(started.get('state') == 'READY' and started.get('serviceStarted') is True,
            'qa_real_service_not_ready')
    child = original._service_child
    live = c.live_service_observation()
    status = c.cli('service-status', start_id)
    require(status.get('state') == 'READY' and status.get('serviceStarted') is False,
            'qa_ready_status_unconfirmed')
    fault = None
    if c.mode == 'lostreply':
        fault = c.lose_close_reply(manifest_sha, close_id)
        closed = None
    else:
        closed = c.cli('close', close_id)
        require(closed.get('state') == 'CLOSED', 'qa_close_not_complete')
    final = c.cli('service-status', close_id)
    require(final.get('state') == 'CLOSED' and final.get('serviceClosed') is True
            and final.get('completion', {}).get('physicalStoresClosed') == 3
            and all(value is True for key, value in final['completion'].items()
                    if key != 'physicalStoresClosed'), 'qa_final_closure_unconfirmed')
    require(c.volume is original and original._service_child is child
            and original.stage == 'CLOSED' and child.process.poll() == 0
            and child.channel.phase == 'COMPLETED' and child.channel.final_frame is not None
            and child.channel.stdout_eof and child.channel.stderr_eof
            and child.channel.stdin_closed and child.channel.pending is None
            and original.worker.poll() == 0
            and set(c.server._mutations) == {start_id, close_id}
            and c.server._mutations[start_id]['dispatched'] is True
            and c.server._mutations[close_id]['dispatched'] is True
            and c.server._task_mutations == {}, 'qa_original_lifecycle_ownership')
    closure = original.observe_service(timeout=0)
    listener = c.server.close_listener()
    broker_final = c.stop_broker()
    c.event('VERIFY_REAL_NORMAL_CLEANUP')
    require(os.readlink('/proc/self/ns/mnt') == host_namespace
            and Path('/proc/self/mountinfo').read_bytes() == host_mounts
            and not os.path.ismount(c.mount) and not any(c.mount.iterdir())
            and not os.path.lexists(original.fence) and not os.path.lexists(original.scope)
            and not volume.attachments(pin)
            and not (c.cgroup / 'cgroup.procs').read_text().strip()
            and not volume.populated((c.cgroup / 'cgroup.events').read_text()), 'qa_cleanup_kernel_postconditions')
    info, parent = c.image.stat(), c.image.parent.stat()
    require(asdict(pin) == asdict(image.ImagePin(str(c.image), info.st_dev, info.st_ino, info.st_size,
        info.st_uid, info.st_gid, parent.st_dev, parent.st_ino)), 'qa_image_identity_changed')
    after_receipt, after_binaries = verified.helper.installed_bytes(
        verified.installer, verified.prepared, RECEIPT_SHA)
    require(canonical(after_receipt) == canonical(verified.receipt)
            and canonical(after_binaries) == canonical(verified.binaries), 'qa_installed_runtime_changed')
    verify_inputs(manifest_sha)
    c.event('COMPLETE')
    return {'kind': 'R168A1_REAL_SERVICE_LIFECYCLE', 'result': 'PASS',
        'state': 'REAL_SERVICE_LIFECYCLE_CLOSED', 'mode': c.mode, 'attemptId': c.attempt,
        'manifestSha256': manifest_sha, 'installationReceiptSha256': RECEIPT_SHA,
        'sourceFiles': 878, 'dependencyFiles': 1162, 'installedSourcesAndRuntimesUnchanged': True,
        'bootstrap': [x['result'] for x in c.bootstrap], 'image': asdict(pin),
        'loopPath': loop_path, 'workerMounted': mounted, 'seed': c.seed_result,
        'seedDiagnostics': c.seed['diagnostics'],
        'start': started, 'readyStatus': status, 'liveKernel': live,
        'close': closed, 'lostReply': fault, 'finalStatus': final,
        'closure': closure, 'listenerClosed': listener, 'brokerFinal': broker_final,
        'observations': c.snapshot(), 'exportEntriesScanned': export['scanned'],
        'sameOriginalSupervisor': True, 'sameOriginalServiceChild': True,
        'allOwnedChildrenTerminal': True, 'hostMountNamespaceUnchanged': True,
        'hostMountTableUnchanged': True, 'serviceStarted': True,
        'taskFreeLifecycleAccepted': True, 'realBrokerPingAccepted': True,
        'executedTasks': 0, 'realModelCalls': 0, 'providerBudget': 0, 'toolBudget': 0,
        'taskExecutionAccepted': False, 'restartAccepted': False,
        'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
        'automaticRetry': False, 'automaticCleanup': False}


def retain_alive(c):
    require(c.effects, 'qa_retention_without_effects')
    for fd in (0, 1, 2):
        try:
            os.close(fd)
        except OSError:
            pass
    while True:
        signal.pause()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--attempt', required=True)
    p.add_argument('--mode', choices=('normal', 'lostreply'), required=True)
    p.add_argument('--drop-reply-client', action='store_true')
    args = p.parse_args(argv)
    c = Controller(args.attempt, args.mode)
    try:
        if args.drop_reply_client:
            actor()
            verify_inputs(args.manifest_sha256)
            value = drop_reply_client(c)
        else:
            value = execute(c, args.manifest_sha256)
        raw = canonical(value)
        require(len(raw) <= MAX_RESULT, 'qa_result_bound')
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        return 0
    except BaseException as exc:
        try:
            value = {'kind': 'R168A1_REAL_SERVICE_LIFECYCLE', 'result': 'NOT_ACCEPTED',
                'state': 'OUTCOME_UNKNOWN' if c.effects else 'REFUSED',
                'reason': str(exc)[:160] if type(exc) is AcceptanceRejected else type(exc).__name__,
                'reasonType': type(exc).__name__, 'attemptId': c.attempt, 'mode': c.mode,
                'observations': c.failure_snapshot(), 'partialStatePreserved': True,
                'normalCloseClaimed': False, 'automaticRetry': False, 'automaticCleanup': False,
                'executedTasks': 0, 'realModelCalls': 0, 'productionReady': False}
            if c.effects:
                value['custody'] = {'state': 'RETAINED_CONTROLLER', 'pid': os.getpid(),
                                    'startTicks': start_ticks(os.getpid())}
            raw = canonical(value)
            require(len(raw) <= MAX_RESULT, 'qa_failure_result_bound')
            sys.stderr.buffer.write(raw)
            sys.stderr.buffer.flush()
        finally:
            if c.effects:
                retain_alive(c)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
