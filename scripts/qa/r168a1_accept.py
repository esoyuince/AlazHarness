"""Freeze and apply one R168 QA attempt from the original Windows worktree.

Only explicit scratch attempt files and the separately reviewed Linux QA
transport are used. The product installation is not a bundle member. A durable
exclusive execution marker prevents replay, including after unknown outcomes.
The same held, verified ZIP supplies stdin; both output buffers and observation
time are bounded. Unknown children are never signalled or automatically retried.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
BASE_COMMIT = '9440a2251d26db88b5f08a0e0292e73f4fbb6e57'
BRANCH = 'alaz/p2-service-lifecycle-r168a1'
BASELINE_SHA = '1af1f7710647f06b25d7efd8b7bb26a18d2ad9ab12476391d16c97ad12cf368f'
PARENT_SEAL_SHA = '65693d5e1453da650422d63b30b29e5b3ed291aad753b527ed24985e08456cd8'
LAB = 'AlazHarness-D3B-P71C'
TRANSPORT = 'scripts/qa/r168a1_linux_transport.py'
SOURCES = frozenset((
    'scripts/qa/r168a1_linux_accept.py', 'scripts/qa/r168a1_service_seed.py',
    'scripts/qa/r168a1_seed_child.py', 'scripts/qa/r168a1_ping_broker.py',
    'scripts/qa/r168a1_bootstrap_probe.py', 'bootstrap-contract.json',
))
MAX_SOURCE, MAX_BUNDLE = 262144, 524288
MAX_OUTPUT, MAX_RECEIPT = 2 * 1024 * 1024, 2 * 1024 * 1024
COMMUNICATION_SECONDS = 360
_PENDING = []


class RunnerRejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise RunnerRejected(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'runner_digest')
    return value


def parse(raw, maximum=MAX_OUTPUT, *, framed=True):
    require(type(raw) is bytes and 0 < len(raw) <= maximum, 'runner_json_bound')
    def unique(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'runner_json_duplicate')
            value[key] = item
        return value
    def constant(value):
        raise RunnerRejected('runner_json_constant')
    def integer(value):
        require(len(value.lstrip('-')) <= 20, 'runner_json_integer_bound')
        return int(value)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                           parse_constant=constant, parse_int=integer)
        if framed:
            require(canonical(value) == raw, 'runner_json_noncanonical')
        return value
    except RunnerRejected:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        raise RunnerRejected('runner_json_invalid') from None


def path_without_alias(path, *, exists=True):
    path = Path(os.path.abspath(path))
    require(path.resolve(strict=exists) == path
            and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                        for p in (path, *path.parents)), 'runner_path_alias')
    return path


def common_stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_nlink,
            getattr(info, 'st_birthtime_ns', getattr(info, 'st_birthtime', None)))


def stamp(info):
    return (*common_stamp(info), info.st_ctime_ns)


def cross_stamp(info):
    # Windows path ctime and held-FD ctime can use distinct time definitions.
    return common_stamp(info) if sys.platform == 'win32' else stamp(info)


def open_verified(path, maximum, *, empty=False, expected=None):
    path = path_without_alias(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and int(not empty) <= before.st_size <= maximum, 'runner_file_metadata')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    stream = None
    try:
        opened = os.fstat(fd)
        require(cross_stamp(opened) == cross_stamp(before), 'runner_file_changed')
        stream = os.fdopen(fd, 'rb', closefd=True)
        fd = None
        raw = stream.read(maximum + 1)
        after, last = os.fstat(stream.fileno()), path.lstat()
        require(len(raw) == before.st_size and stamp(after) == stamp(opened)
                and stamp(last) == stamp(before) and cross_stamp(after) == cross_stamp(last),
                'runner_file_changed')
        if expected is not None:
            require(sha(raw) == digest(expected), 'runner_file_hash_changed')
        stream.seek(0)
        return stream, raw
    except BaseException:
        if stream is not None:
            stream.close()
        elif fd is not None:
            os.close(fd)
        raise


def read_file(path, maximum=MAX_SOURCE, *, empty=False, expected=None):
    stream, raw = open_verified(path, maximum, empty=empty, expected=expected)
    stream.close()
    return raw


def put(path, raw):
    require(type(raw) is bytes, 'runner_output_bytes')
    path = path_without_alias(path, exists=False)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                 | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(read_file(path, max(1, len(raw)), empty=not raw) == raw, 'runner_output_readback')


class BoundedPipe:
    """Retain at most MAX_OUTPUT bytes while draining overflow without signalling."""
    def __init__(self, raw):
        self.raw = raw
        self.data = bytearray()
        self.complete = self.overflow = False
        self.error = None
        self.lock = threading.Lock()

    def read(self, _size=-1):
        try:
            while True:
                chunk = self.raw.read(16384)
                if not chunk:
                    with self.lock:
                        self.complete = True
                    break
                with self.lock:
                    left = MAX_OUTPUT - len(self.data)
                    self.data.extend(chunk[:left])
                    self.overflow = self.overflow or len(chunk) > left
        except (OSError, ValueError) as exc:
            with self.lock:
                self.error = type(exc).__name__
        return self.snapshot()[0]

    def snapshot(self):
        with self.lock:
            return bytes(self.data), self.complete, self.overflow, self.error

    def close(self):
        self.raw.close()

    def fileno(self):
        return self.raw.fileno()

    @property
    def closed(self):
        return self.raw.closed


def communicate_bounded(process, observation, returned_at, *, seconds=COMMUNICATION_SECONDS):
    """Only one communicate call, with held-file/DEVNULL stdin, never PIPE input."""
    deadline = returned_at + seconds
    observation.update(finishedAt=None, error=None)
    def invoke():
        try:
            process.communicate(timeout=seconds)
        except BaseException as exc:
            observation['error'] = exc
        finally:
            observation['finishedAt'] = time.monotonic()
    worker = threading.Thread(target=invoke, name='r168-bounded-observation', daemon=True)
    observation['worker'] = worker
    worker.start()
    worker.join(timeout=max(0, deadline - time.monotonic()))
    require(not worker.is_alive() and observation['finishedAt'] is not None
            and observation['finishedAt'] <= deadline, 'runner_communication_deadline_unknown')
    if observation['error'] is not None:
        raise observation['error']
    require(type(process.returncode) is int, 'runner_terminal_unknown')


def git_read(directory, *args):
    """Fixed callers supply read-only Git arguments; optional index locks disabled."""
    process = subprocess.Popen(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
        '-C', str(directory), *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, close_fds=True, bufsize=0)
    readers = [BoundedPipe(process.stdout), BoundedPipe(process.stderr)]
    process.stdout, process.stderr = readers
    observation = {}
    try:
        communicate_bounded(process, observation, time.monotonic(), seconds=15)
        out, complete, overflow, error = readers[0].snapshot()
        err, err_complete, err_overflow, err_error = readers[1].snapshot()
        require(process.returncode == 0 and complete and err_complete and not err
                and not overflow and not err_overflow and error is None and err_error is None,
                'runner_git_read_refused')
        return out.decode('utf-8').replace('\r\n', '\n')
    except BaseException:
        _PENDING.append((process, readers, observation))
        raise


def host_actor():
    require(sys.platform == 'win32' and os.name == 'nt'
            and sys.implementation.name == 'cpython' and not sys.flags.optimize,
            'runner_windows_host_required')


def baseline_inputs():
    raw = read_file(ROOT / 'scratch/r168-service/baseline.json', MAX_OUTPUT, expected=BASELINE_SHA)
    baseline = parse(raw, framed=False)
    seal_raw = read_file(ROOT / 'scratch/r168-service/parent-r167-seal.json',
                         MAX_OUTPUT, expected=PARENT_SEAL_SHA)
    seal = parse(seal_raw, framed=False)
    require(baseline.get('kind') == 'R168_WORKTREE_BASELINE' and baseline.get('base') == BASE_COMMIT
            and baseline.get('branch') == BRANCH and baseline.get('parentSealSha256') == PARENT_SEAL_SHA,
            'runner_baseline_binding')
    require(seal.get('kind') == 'R167_PUBLICATION_RESULT' and seal.get('result') == 'PASS'
            and seal.get('details', {}).get('kind') == 'R167_SOURCE_PUBLICATION_COMPLETE'
            and seal['details'].get('head') == BASE_COMMIT, 'runner_parent_seal')
    require(type(baseline.get('protectedRepositories')) is list
            and len(baseline['protectedRepositories']) == 20
            and type(baseline.get('rootChangedFileHashes')) is dict
            and len(baseline['rootChangedFileHashes']) == 33, 'runner_baseline_scope')
    return baseline, raw, seal_raw


def allowed_current_change(name):
    return (name == 'status.md'
        or name == 'docs/status-history/r168-parent.md'
        or re.fullmatch(r'docs/P2-[A-Z0-9-]+-R168A1(?:-REPORT)?\.md', name) is not None
        or re.fullmatch(r'scripts/qa/r168a1_[a-z0-9_]+\.py', name) is not None
        or re.fullmatch(r'tests/test_[a-z0-9_]+_r168a1\.py', name) is not None
        or name.startswith('evidence/p2-service-lifecycle-r168a1/'))


def protection_snapshot(baseline):
    require(path_without_alias(ROOT) == path_without_alias(baseline['worktree']),
            'runner_wrong_worktree')
    require(git_read(ROOT, 'rev-parse', '--verify', 'HEAD').strip() == BASE_COMMIT
            and git_read(ROOT, 'branch', '--show-current').strip() == BRANCH,
            'runner_worktree_head_changed')
    changed = git_read(ROOT, 'diff', '--name-only', BASE_COMMIT, '--').splitlines()
    changed.extend(git_read(ROOT, 'ls-files', '--others', '--exclude-standard').splitlines())
    require(all(allowed_current_change(name) for name in changed), 'runner_existing_source_changed')
    observed = []
    for expected in baseline['protectedRepositories']:
        require(type(expected) is dict and set(expected) == {'path', 'head', 'branch', 'status'},
                'runner_repository_baseline')
        directory = path_without_alias(expected['path'])
        row = {'path': expected['path'],
               'head': git_read(directory, 'rev-parse', '--verify', 'HEAD').strip(),
               'branch': git_read(directory, 'branch', '--show-current').strip(),
               'status': git_read(directory, 'status', '--porcelain=v1', '--untracked-files=all')}
        require(row == expected, 'runner_protected_repository_changed')
        observed.append(row)
    repository_root = path_without_alias(baseline['protectedRepositories'][0]['path'])
    files = {}
    for name, expected in sorted(baseline['rootChangedFileHashes'].items()):
        require(type(name) is str and not name.startswith(('/', '\\'))
                and '..' not in Path(name).parts, 'runner_root_file_path')
        files[name] = sha(read_file(repository_root / name, 16 * 1024 * 1024, empty=True))
        require(files[name] == digest(expected), 'runner_protected_root_file_changed')
    return {'baseCommit': BASE_COMMIT, 'branch': BRANCH, 'baselineSha256': BASELINE_SHA,
        'parentSealSha256': PARENT_SEAL_SHA, 'protectedRepositoryCount': len(observed),
        'protectedRepositoriesSha256': sha(canonical(observed)),
        'rootChangedFileCount': len(files), 'rootChangedFilesSha256': sha(canonical(files)),
        'existingProductSourcesUnchanged': True}


def attempt_parameters(attempt, mode, qa_version, stage_mode):
    require(type(attempt) is str and re.fullmatch(r'(normal|lostreply)-[0-9]{2}', attempt)
            and mode in ('normal', 'lostreply') and attempt.startswith(mode + '-'),
            'runner_attempt')
    require(type(qa_version) is str and re.fullmatch('[0-9]{2}', qa_version)
            and stage_mode in ('fresh', 'reuse'), 'runner_stage')
    return {'attemptId': attempt, 'mode': mode, 'stageMode': stage_mode,
        'inputRoot': '/opt/alaz-r168a1-qa-' + qa_version,
        'stateRoot': '/srv/alaz-r168a1-' + attempt}


def owned_directory(attempt, *, exists):
    require(type(attempt) is str and re.fullmatch(r'(normal|lostreply)-[0-9]{2}', attempt),
            'runner_attempt')
    path = path_without_alias(ROOT / 'scratch/r168-service' / attempt, exists=exists)
    if exists:
        require(path.is_dir(), 'runner_attempt_directory')
    else:
        require(not os.path.lexists(path), 'runner_attempt_exists')
    return path


def current_inputs():
    sources = {}
    for name in sorted(SOURCES):
        path = ROOT / ('scratch/r168-service/bootstrap-contract.json'
                       if name == 'bootstrap-contract.json' else name)
        raw = read_file(path, MAX_SOURCE)
        if name.endswith('.py'):
            compile(raw, str(path), 'exec')
        else:
            require(parse(raw, framed=False).get('protocol') == 'alaz-r168a1-os-bootstrap-contract-v2',
                    'runner_bootstrap_contract')
        sources[name] = raw
    transport = read_file(ROOT / TRANSPORT, MAX_SOURCE)
    compile(transport, str(ROOT / TRANSPORT), 'exec')
    return sources, transport, read_file(SELF, MAX_SOURCE)


def make_bundle(sources, manifest):
    require(set(sources) == SOURCES, 'runner_source_inventory')
    require(all(type(raw) is bytes and 0 < len(raw) <= MAX_SOURCE for raw in sources.values()),
            'runner_source_bound')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted({**sources, 'manifest.json': manifest}.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system, info.external_attr = 3, 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, raw)
    raw = stream.getvalue()
    require(len(raw) <= MAX_BUNDLE, 'runner_bundle_bound')
    return raw


def prepared_files(parameters, sources, transport, host, baseline_raw, seal_raw):
    rows = {name: {'sha256': sha(raw), 'size': len(raw)} for name, raw in sorted(sources.items())}
    manifest = canonical({'protocol': 'alaz-r168a1-input-v1', 'files': rows})
    bundle = make_bundle(sources, manifest)
    intent = {'kind': 'R168A1_SERVICE_ACCEPT_INTENT', 'lab': LAB, **parameters,
        'manifestSha256': sha(manifest), 'bundleSha256': sha(bundle), 'bundleBytes': len(bundle),
        'transportSha256': sha(transport), 'hostRunnerSha256': sha(host), 'sourceFiles': rows,
        'baseCommit': BASE_COMMIT, 'parentSealSha256': PARENT_SEAL_SHA}
    receipt = {'kind': 'R168A1_HOST_PREPARATION', 'result': 'PREPARED', 'rootRequested': False,
        'intentSha256': sha(canonical(intent)), 'baselineSha256': BASELINE_SHA,
        'parentSealSha256': PARENT_SEAL_SHA, 'baseCommit': BASE_COMMIT,
        'automaticRetry': False, 'automaticCleanup': False}
    files = {'sources/' + name: raw for name, raw in sources.items()}
    files.update({'manifest.json': manifest, 'bundle.zip': bundle, 'transport.py': transport,
        'host-runner.py': host, 'baseline.json': baseline_raw, 'parent-seal.json': seal_raw,
        'intent.json': canonical(intent), 'prepared.json': canonical(receipt)})
    return files, intent, receipt


def prepare(attempt, mode, qa_version, stage_mode):
    host_actor()
    parameters = attempt_parameters(attempt, mode, qa_version, stage_mode)
    directory = owned_directory(attempt, exists=False)
    baseline, baseline_raw, seal_raw = baseline_inputs()
    protection_snapshot(baseline)
    sources, transport, host = current_inputs()
    files, intent, receipt = prepared_files(parameters, sources, transport, host, baseline_raw, seal_raw)
    command_for(files, intent)
    directory.mkdir(exist_ok=False)
    for name, raw in sorted(files.items()):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        put(target, raw)
    return receipt


def load_prepared(attempt, mode, qa_version, stage_mode, expected_intent):
    parameters = attempt_parameters(attempt, mode, qa_version, stage_mode)
    directory = owned_directory(attempt, exists=True)
    digest(expected_intent)
    require(not any(os.path.lexists(directory / name) for name in (
        'execution-start.json', 'stdout.txt', 'stderr.txt', 'result.json',
        'protection-before.json', 'protection-after.json')), 'runner_execution_no_replay')
    baseline, baseline_raw, seal_raw = baseline_inputs()
    before = protection_snapshot(baseline)
    sources, transport, host = current_inputs()
    files, intent, _ = prepared_files(parameters, sources, transport, host, baseline_raw, seal_raw)
    require(sha(files['intent.json']) == expected_intent, 'runner_expected_intent_changed')
    found = set()
    for path in directory.rglob('*'):
        path_without_alias(path)
        if path.is_file():
            found.add(path.relative_to(directory).as_posix())
        else:
            require(path.is_dir(), 'runner_frozen_object')
    require(found == set(files), 'runner_frozen_inventory')
    for name, raw in files.items():
        require(read_file(directory / name, max(MAX_OUTPUT, len(raw))) == raw,
                'runner_frozen_bytes_changed')
    return directory, intent, files, baseline, before


def command_for(files, intent):
    command = ['wsl.exe', '--distribution', LAB, '--user', 'root', '--cd', '/',
        '--exec', '/usr/bin/python3.12', '-I', '-S', '-B', '-c',
        files['transport.py'].decode('utf-8'), canonical(intent).decode('ascii')[:-1]]
    units = len(subprocess.list2cmdline(command).encode('utf-16-le')) // 2 + 1
    require(units < 32760, 'runner_windows_command_bound')
    return command


def number(value, minimum=0):
    require(type(value) is int and minimum <= value <= 2**63 - 1, 'runner_number')
    return value


def output_row(value, maximum=524288):
    require(type(value) is dict and set(value) == {'bytes', 'sha256', 'base64'},
            'runner_transport_output_fields')
    encoded = value['base64']
    require(type(encoded) is str and len(encoded) <= 4 * ((maximum + 2) // 3),
            'runner_transport_output_bound')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise RunnerRejected('runner_transport_output_encoding') from None
    require(len(raw) <= maximum and base64.b64encode(raw).decode('ascii') == encoded
            and number(value['bytes']) == len(raw) and digest(value['sha256']) == sha(raw),
            'runner_transport_output_digest')
    return raw


def transport_result(out, err, exit_code, intent):
    require(not err, 'runner_transport_stderr')
    report = parse(out)
    require(type(report) is dict and report.get('kind') == 'R168A1_ROOT_TRANSPORT'
            and report.get('rootUsed') is True and report.get('automaticRetry') is False
            and report.get('automaticCleanup') is False
            and type(exit_code) is int, 'runner_transport_identity')
    state = report.get('state')
    if state in ('TRANSPORT_REFUSED', 'TRANSPORT_OUTCOME_UNKNOWN'):
        require(report.get('result') == 'NOT_ACCEPTED' and exit_code == 2
                and report.get('partialStatePreserved') is True, 'runner_transport_negative')
        # Staging may already have begun before a transport refusal. The host
        # makes no "no effects" claim and preserves the one-shot marker.
        return {'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN', 'transport': report,
                'continuingLiveCustodyVerified': False, 'ownedCallerMayBeRunning': True}
    require(report.get('phase') == 'OBSERVED' and report.get('pipesComplete') is True
            and report.get('intentSha256') == sha(canonical(intent))
            and report.get('manifestSha256') == intent['manifestSha256']
            and report.get('attemptId') == intent['attemptId'] and report.get('mode') == intent['mode']
            and report.get('stageMode') == intent['stageMode'], 'runner_transport_binding')
    number(report.get('callerPid'), 1)
    number(report.get('callerStartTicks'), 1)
    caller_out, caller_err = output_row(report.get('stdout')), output_row(report.get('stderr'))
    if state == 'CALLER_TERMINAL_ACCEPTED':
        require(report.get('result') == 'PASS' and exit_code == 0
                and report.get('callerTerminalObserved') is True
                and number(report.get('callerExitCode')) == 0 and not caller_err,
                'runner_transport_acceptance')
        caller = parse(caller_out, 524288)
        require(type(caller) is dict and canonical(caller) == canonical(report.get('caller'))
                and caller.get('kind') == 'R168A1_REAL_SERVICE_LIFECYCLE'
                and caller.get('result') == 'PASS' and caller.get('state') == 'REAL_SERVICE_LIFECYCLE_CLOSED'
                and caller.get('manifestSha256') == intent['manifestSha256']
                and caller.get('attemptId') == intent['attemptId'] and caller.get('mode') == intent['mode'],
                'runner_caller_identity')
        require(type(caller.get('observations')) is dict
                and canonical(caller['observations'].get('controller')) ==
                    canonical({'pid': report['callerPid'], 'startTicks': report['callerStartTicks']}),
                'runner_original_caller_binding')
        require(all(caller.get(k) is True for k in ('taskFreeLifecycleAccepted',
            'realBrokerPingAccepted', 'serviceStarted', 'sameOriginalSupervisor',
            'sameOriginalServiceChild', 'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged',
            'hostMountTableUnchanged', 'installedSourcesAndRuntimesUnchanged')), 'runner_caller_close')
        require(all(caller.get(k) is False for k in ('taskExecutionAccepted', 'restartAccepted',
            'fullD3BAccepted', 'm1Accepted', 'productionReady', 'automaticCleanup', 'automaticRetry'))
            and all(number(caller.get(k)) == 0 for k in ('executedTasks', 'realModelCalls',
                                                       'providerBudget', 'toolBudget')),
            'runner_caller_scope')
        require(number(caller.get('sourceFiles')) == 878
                and number(caller.get('dependencyFiles')) == 1162
                and caller.get('installationReceiptSha256') ==
                    '0ba26bfbae1a216a595baf6fb935ed18f399bcfd0ecf29aa9c14bf61bd04232f'
                and ((caller.get('lostReply') is None) == (intent['mode'] == 'normal')),
                'runner_installed_scope')
        return {'result': 'PASS', 'state': 'REAL_SERVICE_LIFECYCLE_ACCEPTED',
                'transport': report, 'taskFreeLifecycleAccepted': True,
                'continuingLiveCustodyVerified': False, 'ownedCallerMayBeRunning': False}
    require(report.get('result') == 'NOT_ACCEPTED' and exit_code == 2 and not caller_out,
            'runner_caller_negative')
    caller = parse(caller_err, 524288)
    require(type(caller) is dict and canonical(caller) == canonical(report.get('caller'))
            and caller.get('kind') == 'R168A1_REAL_SERVICE_LIFECYCLE'
            and caller.get('result') == 'NOT_ACCEPTED'
            and caller.get('attemptId') == intent['attemptId'] and caller.get('mode') == intent['mode'],
            'runner_negative_identity')
    if state == 'CALLER_RETAINED_OUTCOME_UNKNOWN':
        custody = report.get('custody')
        require(report.get('verifiedLiveCustody') is True and report.get('callerTerminalObserved') is False
                and type(custody) is dict and set(custody) == {'state', 'pid', 'startTicks'}
                and custody['state'] == 'RETAINED_CONTROLLER'
                and number(custody['pid'], 1) == report['callerPid']
                and number(custody['startTicks'], 1) == report['callerStartTicks']
                and caller.get('state') == 'OUTCOME_UNKNOWN'
                and canonical(caller.get('custody')) == canonical(custody)
                and caller.get('partialStatePreserved') is True
                and all(caller.get(k) is False for k in ('normalCloseClaimed', 'automaticRetry',
                                                        'automaticCleanup', 'productionReady')),
                'runner_retained_identity')
        return {'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN', 'transport': report,
                'liveCustodyObservedByTransport': True, 'custodyObservedBeforeTransportExit': custody,
                'continuingLiveCustodyVerified': False, 'ownedCallerMayBeRunning': True}
    require(state == 'CALLER_TERMINAL_REFUSED' and report.get('callerTerminalObserved') is True
            and number(report.get('callerExitCode')) == 2 and caller.get('state') == 'REFUSED'
            and caller.get('custody') is None, 'runner_terminal_refusal')
    return {'result': 'NOT_ACCEPTED', 'state': 'REAL_SERVICE_LIFECYCLE_REFUSED', 'transport': report,
            'continuingLiveCustodyVerified': False, 'ownedCallerMayBeRunning': False}


def unknown(result, exc, *, reason=None):
    result.update(result='UNKNOWN', state='ROOT_OUTCOME_UNKNOWN', taskFreeLifecycleAccepted=False,
                  ownedCallerMayBeRunning=True,
                  reason=reason or (str(exc)[:160] if isinstance(exc, RunnerRejected) else type(exc).__name__),
                  reasonType=type(exc).__name__)


def apply(attempt, mode, qa_version, stage_mode, expected_intent):
    host_actor()
    directory, intent, files, baseline, before = load_prepared(
        attempt, mode, qa_version, stage_mode, expected_intent)
    command = command_for(files, intent)
    stream, raw = open_verified(directory / 'bundle.zip', MAX_BUNDLE, expected=intent['bundleSha256'])
    try:
        require(raw == files['bundle.zip'] and len(raw) == intent['bundleBytes'], 'runner_held_bundle')
        marker = {'kind': 'R168A1_HOST_EXECUTION_START', 'state': 'EXECUTION_STARTED_NO_REPLAY',
            'intentSha256': expected_intent, 'manifestSha256': intent['manifestSha256'],
            'bundleSha256': intent['bundleSha256'], 'hostRunnerSha256': intent['hostRunnerSha256'],
            'transportSha256': intent['transportSha256'], 'baseCommit': BASE_COMMIT,
            'parentSealSha256': PARENT_SEAL_SHA, 'rootRequested': True, 'lab': LAB,
            'hostPid': os.getpid(), 'attemptId': intent['attemptId'], 'mode': intent['mode'],
            'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        put(directory / 'execution-start.json', canonical(marker))
    except BaseException:
        stream.close()
        raise
    result = {'kind': 'R168A1_HOST_ACCEPTANCE', 'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN',
        'intentSha256': expected_intent, 'manifestSha256': intent['manifestSha256'],
        'baselineSha256': BASELINE_SHA, 'parentSealSha256': PARENT_SEAL_SHA,
        'attemptId': intent['attemptId'], 'mode': intent['mode'],
        'executionStartSha256': sha(canonical(marker)), 'rootRequested': True,
        'transportTerminalObserved': False, 'hostTransportMayBeRunning': True,
        'ownedCallerMayBeRunning': True, 'communicationDeadlineSeconds': COMMUNICATION_SECONDS,
        'communicationCompletedWithinDeadline': False, 'continuingLiveCustodyVerified': False,
        'taskFreeLifecycleAccepted': False, 'taskExecutionAccepted': False, 'restartAccepted': False,
        'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
        'automaticCleanup': False, 'automaticRetry': False, 'partialStatePreserved': True,
        'protectedWorkspacesUnchanged': False, 'frozenInputsUnchanged': False}
    process, readers, communication = None, [], {}
    out = err = b''
    keep_references = False
    try:
        put(directory / 'protection-before.json', canonical(before))
        process = subprocess.Popen(command, cwd=ROOT, stdin=stream, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True, bufsize=0)
        returned_at = time.monotonic()
        result['hostTransportPid'] = process.pid
        readers = [BoundedPipe(process.stdout), BoundedPipe(process.stderr)]
        process.stdout, process.stderr = readers
        communicate_bounded(process, communication, returned_at)
        result.update(transportTerminalObserved=True, hostTransportMayBeRunning=False,
                      transportExitCode=process.returncode, communicationCompletedWithinDeadline=True)
        out, complete, overflow, error = readers[0].snapshot()
        err, err_complete, err_overflow, err_error = readers[1].snapshot()
        require(complete and err_complete and not overflow and not err_overflow
                and error is None and err_error is None, 'runner_transport_capture_unknown')
        result.update(transport_result(out, err, process.returncode, intent))
    except BaseException as exc:
        keep_references = True
        unknown(result, exc)
    if readers:
        out, complete, overflow, error = readers[0].snapshot()
        err, err_complete, err_overflow, err_error = readers[1].snapshot()
        result.update(stdoutComplete=complete, stderrComplete=err_complete,
                      stdoutOverflow=overflow, stderrOverflow=err_overflow,
                      stdoutReadError=error, stderrReadError=err_error)
    try:
        after = protection_snapshot(baseline)
        require(after == before, 'runner_protection_changed')
        put(directory / 'protection-after.json', canonical(after))
        result['protectedWorkspacesUnchanged'] = True
        fresh_sources, fresh_transport, fresh_host = current_inputs()
        require(fresh_transport == files['transport.py'] and fresh_host == files['host-runner.py']
                and all(fresh_sources[name] == files['sources/' + name] for name in SOURCES),
                'runner_live_inputs_changed')
        for name, data in files.items():
            require(read_file(directory / name, max(MAX_OUTPUT, len(data))) == data,
                    'runner_frozen_inputs_changed')
        result['frozenInputsUnchanged'] = True
    except BaseException as exc:
        keep_references = True
        unknown(result, exc)
    result.update(stdoutSha256=sha(out), stderrSha256=sha(err), stdoutBytes=len(out), stderrBytes=len(err))
    if len(canonical(result)) > MAX_RECEIPT:
        result.pop('transport', None)
        result['transportReportAvailableInRawStdout'] = True
    try:
        put(directory / 'stdout.txt', out)
        put(directory / 'stderr.txt', err)
        result['evidenceWriteComplete'] = True
        receipt = canonical(result)
        require(len(receipt) <= MAX_RECEIPT, 'runner_receipt_bound')
        put(directory / 'result.json', receipt)
    except BaseException as exc:
        keep_references = True
        unknown(result, exc, reason='runner_evidence_write_failed')
        result['evidenceWriteComplete'] = False
    if keep_references:
        # No signal, wait, second communicate, replay, or state cleanup.
        _PENDING.append((process, readers, communication, stream))
    else:
        stream.close()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--mode', required=True, choices=('normal', 'lostreply'))
    parser.add_argument('--qa-version', required=True)
    parser.add_argument('--stage-mode', required=True, choices=('fresh', 'reuse'))
    parser.add_argument('--expected-intent-sha256')
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            require(args.expected_intent_sha256 is None, 'runner_prepare_arguments')
            result = prepare(args.attempt, args.mode, args.qa_version, args.stage_mode)
        else:
            require(args.expected_intent_sha256 is not None, 'runner_apply_arguments')
            result = apply(args.attempt, args.mode, args.qa_version, args.stage_mode,
                           args.expected_intent_sha256)
    except BaseException as exc:
        result = {'kind': 'R168A1_HOST_RUNNER_REFUSAL', 'result': 'NOT_ACCEPTED',
            'reason': str(exc)[:160] if isinstance(exc, RunnerRejected) else type(exc).__name__,
            'reasonType': type(exc).__name__, 'automaticRetry': False, 'automaticCleanup': False}
    print(canonical(result).decode('ascii'), end='')
    return 0 if result['result'] in ('PASS', 'PREPARED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
