'One fixed R156 seed -> scripted native finite qualification -> normal close.\nThe original R155 provisioning, seed ownership, capture and unknown custody remain.\nExactly one finite child uses original API/runner/authority/store/drain/close.\nModel factory/computation/close is an explicit fixture; external provider calls remain zero.\n'
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import types

PYTHON = '/usr/bin/python3.12'
INSTALLATION = Path('/opt/alaz-r156a1')
INPUT = Path('/opt/alaz-r156a1-accept-input')
BASE = Path('/srv/alaz-r156a1')
IMAGE = BASE / 'images/state.ext4'
MOUNT = BASE / 'mount'
PROFILE = MOUNT / 'profile'
SCRATCH = BASE / 'scratch'
SOCKET = BASE / 'broker/egress.sock'
CGROUP = Path('/sys/fs/cgroup/alaz-r156a1')
ANCHOR = Path('/tmp/alaz-ipc-r156a1')
CANARY = BASE / 'canary.txt'
SEED_ENTRY = 'scripts/bootstrap_retained_profile_r156.py'
CHILD_ENTRY = 'scripts/qa/r156a1_seed_child.py'
CALLER_ENTRY = 'scripts/qa/r156a1_linux_accept.py'
FINITE_ENTRY = 'scripts/qa/r156a1_finite_assert.py'
INPUT_FILES = {SEED_ENTRY, CHILD_ENTRY, CALLER_ENTRY, FINITE_ENTRY}
RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
HARNESS = 'e641a5000810efb2a453ae847f689b422f7d41a7'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
FORMATTER_SHA = '07cd24ce58a410cc9cee93c55ae5ac95986df016c5907dc7a49b55389bd41ed2'
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'}
USER_NS = 'user:[4026531837]'
PRINCIPAL = {'version': 1, 'enabled': True, 'gatewayUid': 23001, 'brokerUid': 23002,
             'socketGroupGid': 23003, 'hostUserNamespace': USER_NS}
CHECKS = ['preflight', 'response_preflight', 'before_epoch',
          'response_before_epoch', 'after_epoch', 'response_after_epoch']
SEED_INSTANCE = 'r156a1-seed'
FINITE_INSTANCE = 'r156a1-finite'
SEED_SECONDS = 35
FINITE_SECONDS = 60
STOP_MARGIN = 15
MAX_SOURCE = 262144
MAX_RESULT = 524288
SEED_FIELDS = set('''kind result state phase home pid parentPid startTicks gatewayUid
socketGroupGid supplementaryGroups resUid resGid mountNamespaceInode mountNamespace
profileIdentity databaseIdentities mount handoff handoffSha256 previousEpoch instanceId
ownerState consumerState allThreeConnectionsPhysicallyClosed profileLeaseReleasedNormally
retainedCapturedWhileLeaseHeld normalLoopShutdown outstandingAsyncTasks outstandingThreads
completedChecks coldHelperCalls sqliteOpenCount qualifiedNativeSourceCount auxiliaryInitialization
executedTasks realModelCalls listenersCreated apiAdmissionPublished installationReceiptSha256
harnessCommit nativeFeature verificationMillis nativeMillis totalMillis projectedReadinessAccepted
fullD3BAccepted automaticCleanup automaticRetry'''.split())


class AcceptanceRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise AcceptanceRejected(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value, minimum=0, maximum=(1 << 63) - 1):
    require(type(value) is int and minimum <= value <= maximum, 'caller_integer')
    return value


def exact(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), reason)
    return value


def frame(raw, maximum):
    require(type(raw) is bytes and 0 < len(raw) <= maximum and raw.endswith(b'\n')
            and raw.count(b'\n') == 1, 'caller_frame')
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'caller_duplicate_key')
            result[key] = value
        return result
    def no_number(_):
        raise AcceptanceRejected('caller_noninteger_json')
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=pairs,
                           parse_float=no_number, parse_constant=no_number)
    except (UnicodeError, ValueError, RecursionError):
        raise AcceptanceRejected('caller_json') from None
    require(canonical(value) == raw, 'caller_noncanonical_json')
    return value


def trusted_read(path, maximum=MAX_SOURCE):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'caller_source_alias')
    for parent in path.parents:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and not info.st_mode & 0o022, 'caller_source_ancestry')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_uid == before.st_gid == 0 and not before.st_mode & 0o022
                and 0 < before.st_size <= maximum, 'caller_source_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid,
                           s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(raw) == before.st_size and stamp(before) == stamp(os.fstat(fd)),
                'caller_source_changed')
        return raw
    finally:
        os.close(fd)


def validate_manifest(value):
    exact(value, {'protocol', 'files'}, 'caller_manifest_fields')
    require(value['protocol'] == 'alaz-r156a1-input-v1', 'caller_manifest_protocol')
    exact(value['files'], INPUT_FILES, 'caller_manifest_files')
    for row in value['files'].values():
        exact(row, {'sha256', 'size'}, 'caller_manifest_entry')
        require(type(row['sha256']) is str
                and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'caller_manifest_digest')
        integer(row['size'], 1, MAX_SOURCE)
    return value


def verify_inputs(expected_sha):
    require(type(expected_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_sha) is not None,
            'caller_manifest_pin')
    raw = trusted_read(INPUT / 'manifest.json', 8192)
    require(digest(raw) == expected_sha, 'caller_manifest_changed')
    manifest = validate_manifest(frame(raw, 8192))
    expected = INPUT_FILES | {'manifest.json'}
    found = set()
    for current, dirs, files in os.walk(INPUT, followlinks=False):
        for name in dirs:
            path = Path(current) / name
            info = path.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                    and stat.S_IMODE(info.st_mode) == 0o755
                    and str(path.relative_to(INPUT)) in {'scripts', 'scripts/qa'},
                    'caller_input_directory')
        for name in files:
            found.add(str((Path(current) / name).relative_to(INPUT)))
        require(len(found) <= len(expected), 'caller_input_extra')
    require(found == expected, 'caller_input_inventory')
    sources = {}
    for name, row in manifest['files'].items():
        data = trusted_read(INPUT / name)
        require(len(data) == row['size'] and digest(data) == row['sha256']
                and stat.S_IMODE((INPUT / name).stat().st_mode) == 0o644,
                'caller_input_source_changed')
        sources[name] = data
    require(Path(__file__) == INPUT / CALLER_ENTRY, 'caller_fixed_path')
    return manifest, sources


def load_source(name, path, raw):
    require(name not in sys.modules, 'caller_module_already_loaded')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def actor():
    import pwd
    import grp
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64'
            and sys.version_info[:2] == (3, 12) and sys.executable == PYTHON
            and sys.flags.isolated == 1 and sys.dont_write_bytecode and not sys.flags.optimize,
            'caller_interpreter')
    require(os.getresuid() == (0, 0, 0) and os.getresgid() == (0, 0, 0), 'caller_host_root')
    require(Path('/etc/alaz-p71c-lab-id').read_text().strip() == 'AlazHarness-D3B-P71C'
            and not Path('/mnt/c/Windows').exists(), 'caller_dedicated_lab')
    require(os.readlink('/proc/self/ns/user') == USER_NS
            and Path('/proc/self/uid_map').read_text().split() == ['0', '0', '4294967295']
            and Path('/proc/self/gid_map').read_text().split() == ['0', '0', '4294967295'],
            'caller_initial_user_namespace')
    require(threading.active_count() == 1 and threading.current_thread() is threading.main_thread(),
            'caller_single_thread')
    require(pwd.getpwuid(23001).pw_name == 'alazgateway' and pwd.getpwuid(23001).pw_gid == 23003
            and pwd.getpwuid(23002).pw_name == 'alazbroker' and pwd.getpwuid(23002).pw_gid == 23003
            and grp.getgrgid(23003).gr_name == 'alazipc', 'caller_existing_principals')
    for path in (BASE, CGROUP, ANCHOR):
        require(not os.path.lexists(path), 'caller_fresh_path_required')


def projection_contract():
    view = {'version': 2, 'mode': 'projected_root_principal', 'root': str(ANCHOR),
            'brokerSocket': str(SOCKET), 'principalContract': dict(PRINCIPAL)}
    filesystem = {'version': 1, 'enabled': True,
        'readonly': ['/usr/bin', '/usr/lib/python3.12', '/usr/lib/x86_64-linux-gnu',
                     '/usr/lib64', '/usr/lib/locale', str(INSTALLATION),
                     '/etc/ld.so.cache', '/etc/mime.types', '/dev/urandom'],
        'writable': ['/dev/null', str(SCRATCH)], 'protected': [str(CANARY)],
        'self_process_metadata': True}
    return view, filesystem


def validate_seed(raw, context, handoff):
    value = exact(frame(raw, 32768), SEED_FIELDS, 'caller_seed_fields')
    expected = {'kind': 'R156A1_TASK_FREE_RETAINED_SEED', 'result': 'PASS',
        'state': 'RETAINED_SEED_CREATED', 'phase': 'COMPLETE', 'home': str(PROFILE),
        'pid': context['pid'], 'parentPid': context['parentPid'], 'startTicks': context['startTicks'],
        'gatewayUid': 23001, 'socketGroupGid': 23003, 'supplementaryGroups': [],
        'resUid': [23001] * 3, 'resGid': [23003] * 3,
        'mountNamespaceInode': context['namespaceInode'],
        'mountNamespace': 'mnt:[' + str(context['namespaceInode']) + ']',
        'previousEpoch': 1, 'instanceId': SEED_INSTANCE, 'ownerState': 'CLOSED',
        'consumerState': 'DETACHED', 'completedChecks': CHECKS,
        'coldHelperCalls': [{'phase': 'START_OWNER', 'script': name}
                            for name in ('run_store_preopen.py', 'run_response_preopen.py')],
        'installationReceiptSha256': RECEIPT_SHA, 'harnessCommit': HARNESS, 'nativeFeature': NATIVE}
    for key, wanted in expected.items():
        require(type(value[key]) is type(wanted) and value[key] == wanted, 'caller_seed_identity')
    for key in ('pid', 'parentPid', 'startTicks', 'gatewayUid', 'socketGroupGid',
                'mountNamespaceInode', 'previousEpoch'):
        integer(value[key], 1)
    require(all(type(n) is int for key in ('resUid', 'resGid') for n in value[key]),
            'caller_seed_principal_type')
    for key in ('allThreeConnectionsPhysicallyClosed', 'profileLeaseReleasedNormally',
                'retainedCapturedWhileLeaseHeld', 'normalLoopShutdown'):
        require(value[key] is True, 'caller_seed_close_unconfirmed')
    for key in ('outstandingAsyncTasks', 'outstandingThreads', 'executedTasks',
                'realModelCalls', 'listenersCreated'):
        integer(value[key], 0, 0)
    for key in ('apiAdmissionPublished', 'projectedReadinessAccepted', 'fullD3BAccepted',
                'automaticCleanup', 'automaticRetry'):
        require(value[key] is False, 'caller_seed_scope')
    for key in ('verificationMillis', 'nativeMillis', 'totalMillis'):
        integer(value[key], 0, SEED_SECONDS * 1000 - 1)
    require(abs(value['totalMillis'] - value['verificationMillis'] - value['nativeMillis']) <= 1,
            'caller_seed_timing')
    integer(value['sqliteOpenCount'], 1, 1024)
    integer(value['qualifiedNativeSourceCount'], 1, 4096)
    mount = exact(value['mount'], {'mount_id', 'device', 'root', 'mount_point', 'filesystem'},
                  'caller_seed_mount_fields')
    integer(mount['mount_id'], 1)
    require(mount['device'] == [7, context['loopNumber']]
            and type(mount['device']) is list and all(type(n) is int for n in mount['device'])
            and mount['root'] == '/' and mount['mount_point'] == str(MOUNT)
            and mount['filesystem'] == 'ext4', 'caller_seed_mount_identity')
    require(type(value['handoff']) is str, 'caller_seed_handoff_type')
    wire = value['handoff'].encode('ascii')
    require(digest(wire) == value['handoffSha256'], 'caller_seed_handoff_digest')
    record = handoff.decode(wire, expected_home=str(PROFILE))
    require(record.state.epoch == 1 and record.state.instance_id == SEED_INSTANCE
            and value['profileIdentity'] == list(record.retained.home_identity)
            and value['databaseIdentities'] == [list(x) for x in record.retained.database_identities]
            and value['profileIdentity'] == context['profileIdentity']
            and value['databaseIdentities'] == context['databaseIdentities'], 'caller_seed_store_identity')
    for pair in [value['profileIdentity'], *value['databaseIdentities']]:
        require(type(pair) is list and len(pair) == 2, 'caller_seed_identity_pair')
        for n in pair:
            integer(n, 1, (1 << 64) - 1)
    auxiliary = exact(value['auxiliaryInitialization'], {'sourceDerivedCacheEntries',
        'sourceDerivedCacheSha256', 'completeToolRegistrationPerformed', 'activeSessionEntries',
        'blockedIpv6CapabilityProbe'},
        'caller_seed_auxiliary_fields')
    integer(auxiliary['sourceDerivedCacheEntries'], 1, 1024)
    integer(auxiliary['activeSessionEntries'], 0, 0)
    require(auxiliary['completeToolRegistrationPerformed'] is False
            and auxiliary['sourceDerivedCacheSha256'] == record.retained.discovery_sha256,
            'caller_seed_auxiliary_identity')
    probe = exact(auxiliary['blockedIpv6CapabilityProbe'], {'count', 'socketClosed', 'bindPerformed'},
                  'caller_seed_blocked_probe_fields')
    integer(probe['count'], 1, 1)
    require(probe['socketClosed'] is True and probe['bindPerformed'] is False,
            'caller_seed_blocked_probe_effect')
    return value, record


def process_report(attempt):
    if attempt is None:
        return None
    process = attempt.get('process')
    capture = attempt.get('capture')
    result = {key: attempt[key] for key in ('phase', 'startTicks', 'payloadSha256') if key in attempt}
    result.update(pid=process.pid if process is not None else None,
                  exitCode=process.poll() if process is not None else None)
    if capture is not None:
        for name in ('stdout', 'stderr'):
            raw = bytes(getattr(capture, name + '_bytes'))
            result[name] = {'bytes': len(raw), 'sha256': digest(raw),
                            'base64': base64.b64encode(raw).decode('ascii')}
        result.update(complete=capture.complete, overflowed=capture.overflowed,
                      inputWritten=capture.input_written)
    elif 'stdout' in attempt:
        for name in ('stdout', 'stderr'):
            raw = attempt[name]
            result[name] = {'bytes': len(raw), 'sha256': digest(raw),
                            'base64': base64.b64encode(raw).decode('ascii')}
        result['complete'] = attempt.get('complete', False)
    return result


class Controller:
    def __init__(self):
        self.phase = 'PRECHECK'
        self.effects = False
        self.volume = self.seed = self.broker = self.formatter = None
        self.finite = self.seed_result = None
        self.events = []
        self.modules = None

    def event(self, label):
        self.phase = label
        self.events.append(label)

    def format_image(self):
        # The exact root-controlled formatter has fixed argv and no stdin. It
        # emits ordinary diagnostic output, not the product child protocol.
        attempt = {'phase': 'SPAWNING', 'process': None, 'complete': False}
        self.formatter = attempt
        try:
            attempt['process'] = subprocess.Popen(['/usr/sbin/mke2fs', '-t', 'ext4', '-q', '-F',
                '-E', 'lazy_itable_init=0,lazy_journal_init=0', str(IMAGE)], cwd='/', env=dict(ENV),
                close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            attempt['phase'] = 'RUNNING'
            out, err = attempt['process'].communicate(timeout=20)
            attempt.update(stdout=out[:8192], stderr=err[:8192], complete=True)
            require(len(out) <= 8192 and len(err) <= 8192, 'caller_formatter_output_bound')
            require(attempt['process'].returncode == 0,
                    'caller_fixed_process_failed')
            attempt['phase'] = 'COMPLETED'
        except subprocess.TimeoutExpired as exc:
            attempt.update(phase='UNKNOWN', stdout=(exc.output or b'')[:8192],
                           stderr=(exc.stderr or b'')[:8192])
            raise  # communicate() does not terminate or retry this process.
        except BaseException:
            attempt['phase'] = 'UNKNOWN'
            raise

    def provision(self):
        self.event('PROVISION_FRESH_PATHS')
        self.effects = True
        os.umask(0o022)
        BASE.mkdir(mode=0o755)
        for path, mode, uid, gid in ((IMAGE.parent, 0o700, 0, 0), (MOUNT, 0o700, 0, 0),
                (SCRATCH, 0o700, 23001, 23003), (SOCKET.parent, 0o710, 23002, 23003),
                (CGROUP, 0o755, 0, 0), (ANCHOR, 0o700, 0, 0)):
            path.mkdir(mode=mode)
            os.chown(path, uid, gid)
            require(stat.S_IMODE(path.stat().st_mode) == mode, 'caller_directory_mode')
        fd = os.open(CANARY, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(b'R156A1 owned protected export; no secret.\n')
        fd = os.open(IMAGE, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'r+b') as stream:
            stream.truncate(64 * 1024 * 1024)
            stream.flush()
            os.fsync(stream.fileno())
        self.event('FORMAT_FRESH_IMAGE')
        self.format_image()
        s, p = IMAGE.stat(), IMAGE.parent.stat()
        return self.modules.image.ImagePin(str(IMAGE), s.st_dev, s.st_ino, s.st_size,
                                          s.st_uid, s.st_gid, p.st_dev, p.st_ino)

    def start_broker(self, manifest_sha):
        self.event('START_METADATA_SOCKET_FIXTURE')
        self.broker = {'phase': 'SPAWNING', 'process': None,
                       'capture': self.modules.capture.PipeCapture(4096)}
        try:
            p = subprocess.Popen([PYTHON, '-I', '-B', str(INPUT / CALLER_ENTRY), '--broker',
                    '--manifest-sha256', manifest_sha], cwd='/', env=dict(ENV), close_fds=True,
                    user=23002, group=23003, extra_groups=[], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            self.broker['process'] = p
            self.broker['startTicks'] = self.modules.projection.process_start(p.pid)
            ready = self.modules.volume.read_line(p, seconds=5)
            require(ready == {'state': 'METADATA_SOCKET_BOUND', 'pid': p.pid,
                'resUid': [23002] * 3, 'resGid': [23003] * 3, 'groups': [],
                'userNamespace': USER_NS, 'listenersCreated': 0, 'providerCalls': 0},
                'caller_broker_fixture_identity')
            self.modules.principal.socket_identity(PRINCIPAL, str(SOCKET))
            self.broker.update(phase='READY', ready=ready)
        except BaseException:
            self.broker['phase'] = 'UNKNOWN'
            raise

    def seed_contract(self, namespace_fd, manifest):
        v, p = self.volume, self.modules.projection
        return {'protocol': 'alaz-seed-child-r156a1-v1',
            'controller': {'pid': os.getpid(), 'startTicks': p.process_start(os.getpid())},
            'worker': {'pid': v.worker.pid, 'startTicks': p.process_start(v.worker.pid)},
            'scope': {'path': str(v.scope), 'device': v.scope_id[0], 'inode': v.scope_id[1]},
            'namespace': {'fd': namespace_fd, 'inode': os.fstat(namespace_fd).st_ino},
            'image': asdict(v.pin), 'token': v.token,
            'fence': {'path': str(v.fence), 'sha256': digest(v.fence_bytes)},
            'mountpoint': str(MOUNT), 'profile': str(PROFILE), 'loopNumber': v.loop_number,
            'principal': dict(PRINCIPAL), 'installation': {'path': str(INSTALLATION), 'receiptSha256': RECEIPT_SHA},
            'bootstrap': {'path': str(INPUT / SEED_ENTRY), 'sha256': manifest['files'][SEED_ENTRY]['sha256']},
            'seedInstanceId': SEED_INSTANCE}

    def scope_only_worker(self):
        v = self.volume
        v._owned()
        require(v.worker.poll() is None and (v.scope / 'cgroup.procs').read_text().split() == [str(v.worker.pid)]
                and not any(p.is_dir() for p in v.scope.iterdir()), 'caller_other_volume_users')

    def run_seed(self, manifest, child):
        self.event('SEED_ATTEMPT')
        v = self.volume
        require(self.seed is None and v.stage == 'RUNNING', 'caller_seed_once')
        self.scope_only_worker()
        require(time.monotonic() + SEED_SECONDS + FINITE_SECONDS + STOP_MARGIN < v._worker_deadline,
                'caller_worker_budget')
        require(digest(trusted_read(INPUT / CHILD_ENTRY)) == manifest['files'][CHILD_ENTRY]['sha256'],
                'caller_child_source_changed')
        fd = os.open('/proc/' + str(v.worker.pid) + '/ns/mnt', os.O_RDONLY | os.O_CLOEXEC)
        try:
            contract = self.seed_contract(fd, manifest)
            payload = child.encode_contract(contract)
            self.seed = {'phase': 'SPAWNING', 'capture': self.modules.capture.PipeCapture(32768),
                         'process': None, 'payloadSha256': digest(payload)}
            try:
                p = subprocess.Popen([PYTHON, '-I', '-B', str(INPUT / CHILD_ENTRY)], cwd='/',
                    env=dict(ENV), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    pass_fds=(fd,), close_fds=True, bufsize=0)
                self.seed['process'] = p
                self.seed['startTicks'] = self.modules.projection.process_start(p.pid)
                self.seed['phase'] = 'RUNNING'
            except BaseException:
                self.seed['phase'] = 'UNKNOWN'
                raise
        finally:
            os.close(fd)  # Only the known parent copy; no image/volume release.
        try:
            capture = self.seed['capture']
            capture.send_once(p, payload, SEED_SECONDS)
            require(p.returncode == 0 and capture.complete, 'caller_seed_exit_or_output')
            self.scope_only_worker()
            root = Path('/proc/' + str(v.worker.pid) + '/root')
            ids = []
            for relative in ('', '/state.db', '/runs_idempotency.db', '/response_store.db'):
                info = (root / (str(PROFILE).lstrip('/') + relative)).lstat()
                require((stat.S_ISDIR(info.st_mode) if not relative else stat.S_ISREG(info.st_mode))
                        and info.st_uid == 23001 and info.st_gid == 23003, 'caller_actual_profile_identity')
                ids.append([info.st_dev, info.st_ino])
            context = {'pid': p.pid, 'parentPid': os.getpid(), 'startTicks': self.seed['startTicks'],
                'namespaceInode': contract['namespace']['inode'], 'loopNumber': v.loop_number,
                'profileIdentity': ids[0], 'databaseIdentities': ids[1:]}
            self.seed_result, record = validate_seed(bytes(capture.stdout_bytes), context, self.modules.handoff)
            self.seed['phase'] = 'COMPLETED'
            self.event('SEED_COMPLETED')
            return record
        except BaseException:
            self.seed['phase'] = 'UNKNOWN'
            raise

    def run_finite(self, view, filesystem, record):
        require(self.seed is not None and self.seed['phase'] == 'COMPLETED'
                and self.finite is None, 'caller_finite_requires_seed')
        self.event('PROJECTED_FINITE_ATTEMPT')
        self.finite = self.volume.run_finite(view, filesystem, record, self.modules.finite.WORK,
            scratch=str(SCRATCH), instance_id=FINITE_INSTANCE, timeout=FINITE_SECONDS)
        self.modules.finite.validate_supervised(self.finite)
        require(self.volume.observe_finite() == self.finite, 'caller_finite_observation_changed')
        self.event('PROJECTED_FINITE_COMPLETED')

    def close_volume(self):
        require(self.seed is not None and self.seed['phase'] == 'COMPLETED'
                and self.finite is not None and self.finite.get('volumeMayClose') is True
                and self.finite.get('state') == 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED',
                'caller_unresolved_child_blocks_close')
        self.event('NORMAL_STOP')
        stopped = self.volume.stop()
        self.event('NORMAL_FINISH')
        closed = self.volume.finish()
        require(closed['state'] == 'CLOSED' and closed['ownedUsersGone'] is True
                and closed['loopAttachmentGone'] is True and closed['fenceRemovedAfterCleanup'] is True
                and closed['leaseReleasedLast'] is True, 'caller_close_unconfirmed')
        self.event('VOLUME_CLOSED')
        return {'stop': stopped, 'finish': closed}

    def stop_broker(self):
        require(self.broker['phase'] == 'READY' and self.volume.stage == 'CLOSED',
                'caller_broker_stop_order')
        self.broker['phase'] = 'STOPPING'
        try:
            self.broker['capture'].send_once(self.broker['process'], b'STOP\n', 5)
            require(self.broker['process'].returncode == 0 and self.broker['capture'].complete
                    and frame(bytes(self.broker['capture'].stdout_bytes), 4096)
                        == {'state': 'METADATA_SOCKET_CLOSED', 'pid': self.broker['process'].pid},
                    'caller_broker_close_unconfirmed')
            self.broker['phase'] = 'COMPLETED'
        except BaseException:
            self.broker['phase'] = 'UNKNOWN'
            raise

    def snapshot(self):
        v = self.volume
        retained = getattr(v, '_retained_child', None) if v is not None else None
        retained_attempt = ({'phase': retained.phase, 'process': retained.process,
            'capture': retained.capture, 'startTicks': retained.start_ticks,
            'payloadSha256': retained.payload_sha256} if retained is not None else None)
        preparing = []
        if self.modules is not None:
            preparing = [{'stage': x.stage, 'scope': str(x.scope), 'fence': str(x.fence),
                          'token': x.token} for x in self.modules.volume._RETAINED.values()
                         if x.who[0] == os.getpid()]
        return {'phase': self.phase, 'effectsAttempted': self.effects, 'events': self.events,
            'volumeStage': v.stage if v is not None else None,
            'workerPid': v.worker.pid if v is not None and v.worker is not None else None,
            'scope': str(v.scope) if v is not None else None,
            'fence': str(v.fence) if v is not None else None,
            'seed': process_report(self.seed), 'retained': process_report(retained_attempt),
            'formatter': process_report(self.formatter), 'brokerFixture': process_report(self.broker),
            'originalRetainedVolumes': preparing}


def broker_main(manifest_sha):
    verify_inputs(manifest_sha)
    require(os.getresuid() == (23002,) * 3 and os.getresgid() == (23003,) * 3
            and not os.getgroups() and os.readlink('/proc/self/ns/user') == USER_NS,
            'caller_broker_actor')
    require(dict(os.environ) == ENV and sys.flags.isolated and sys.dont_write_bytecode
            and sys.executable == PYTHON, 'caller_broker_environment')
    require(not os.path.lexists(SOCKET), 'caller_broker_fresh_socket')
    os.umask(0o007)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET))
    os.chmod(SOCKET, 0o660)
    # Deliberately no listen/connect/accept: only the original readiness metadata
    # guard is in scope, not the real broker's peer exchange or budget policy.
    sys.stdout.buffer.write(canonical({'state': 'METADATA_SOCKET_BOUND', 'pid': os.getpid(),
        'resUid': list(os.getresuid()), 'resGid': list(os.getresgid()), 'groups': os.getgroups(),
        'userNamespace': os.readlink('/proc/self/ns/user'), 'listenersCreated': 0, 'providerCalls': 0}))
    sys.stdout.buffer.flush()
    require(select.select([sys.stdin.buffer], [], [], 180)[0], 'caller_broker_deadline')
    require(os.read(0, 16) == b'STOP\n', 'caller_broker_stop_frame')
    sock.close()
    sys.stdout.buffer.write(canonical({'state': 'METADATA_SOCKET_CLOSED', 'pid': os.getpid()}))
    sys.stdout.buffer.flush()


def execute(controller, manifest_sha):
    actor()
    manifest, sources = verify_inputs(manifest_sha)
    seed = load_source('_r156_reviewed_seed', INPUT / SEED_ENTRY, sources[SEED_ENTRY])
    installed = seed.verify_installation()
    require(installed['receiptSha256'] == RECEIPT_SHA, 'caller_installation_changed')
    require(digest(trusted_read('/usr/sbin/mke2fs', 4 * 1024 * 1024)) == FORMATTER_SHA,
            'caller_formatter_changed')
    child = load_source('_r156_reviewed_child', INPUT / CHILD_ENTRY, sources[CHILD_ENTRY])
    finite = load_source('_r156_reviewed_finite_assertion', INPUT / FINITE_ENTRY, sources[FINITE_ENTRY])
    sys.path.insert(0, str(INSTALLATION / 'packages/claw-hermes'))
    import gateway_supervised_launch as supervised
    import gateway_retained_handoff as handoff
    import gateway_state_projection as projection
    import gateway_projection as gateway_projection
    import state_volume_supervisor as volume
    import state_image_lease as image
    import supervised_pipe_capture as capture
    import host_principal as principal
    controller.modules = types.SimpleNamespace(supervised=supervised, handoff=handoff, projection=projection,
        volume=volume, image=image, capture=capture, principal=principal, finite=finite)
    volume.actor()
    view, filesystem = projection_contract()
    gateway_projection.validate(view, filesystem)
    host_namespace = os.readlink('/proc/self/ns/mnt')
    host_mounts = Path('/proc/self/mountinfo').read_bytes()
    pin = controller.provision()
    controller.start_broker(manifest_sha)
    export_preflight = gateway_projection.inspect(view, filesystem)
    controller.event('BEGIN_ORIGINAL_SUPERVISOR')
    controller.volume = supervised.RetainedVolumeSupervisor.begin(pin, CGROUP, MOUNT)
    v = controller.volume
    controller.event('ATTACH_ORIGINAL_SUPERVISOR')
    loop = v.attach()
    controller.event('START_ORIGINAL_WORKER')
    mounted = v.start()
    record = controller.run_seed(manifest, child)
    controller.run_finite(view, filesystem, record)
    closure = controller.close_volume()
    controller.stop_broker()
    controller.event('VERIFY_NORMAL_CLOSE')
    require(os.readlink('/proc/self/ns/mnt') == host_namespace
            and Path('/proc/self/mountinfo').read_bytes() == host_mounts
            and not os.path.ismount(MOUNT) and not any(MOUNT.iterdir())
            and not os.path.lexists(v.fence) and not os.path.lexists(v.scope)
            and not volume.attachments(pin) and not (CGROUP / 'cgroup.procs').read_text().strip()
            and not volume.populated((CGROUP / 'cgroup.events').read_text()), 'caller_close_postconditions')
    current, parent = IMAGE.stat(), IMAGE.parent.stat()
    require(asdict(pin) == asdict(image.ImagePin(str(IMAGE), current.st_dev, current.st_ino, current.st_size,
        current.st_uid, current.st_gid, parent.st_dev, parent.st_ino)), 'caller_final_image_identity')
    controller.event('COMPLETE')
    result = {'kind': 'R156A1_SAME_IMAGE_SEED_FINITE', 'result': 'PASS',
        'state': 'SAME_IMAGE_SEED_FINITE_CLOSED', 'manifestSha256': manifest_sha,
        'installation': installed, 'image': asdict(pin), 'loopPath': loop, 'workerMounted': mounted,
        'seedResult': controller.seed_result, 'finite': controller.finite, 'closure': closure,
        'observations': controller.snapshot(), 'exportEntriesScanned': export_preflight['scanned'],
        'hostMountNamespaceUnchanged': True, 'hostMountTableUnchanged': True,
        'allOwnedChildrenTerminal': True, 'sameOriginalSupervisor': True,
        'sameImageSeedAndFinite': True, 'projectedFiniteAccepted': True,
        'brokerMetadataFixtureOnly': True, 'realBrokerExchangeAccepted': False,
        'executedTasks': 3, 'scriptedModelInvocations': 3, 'realModelCalls': 0, 'realProviderCalls': 0,
        'serviceStarted': False, 'runtimeAdmissionAuthorized': False, 'finiteWorkExecuted': True,
        'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
        'automaticCleanup': False, 'automaticRetry': False}
    return finite.validate_caller(result, manifest_sha)


def retain_alive(controller):
    """Keep the original PID, supervisor and lease objects after unknown effects.

    The reviewed transport starts this caller in its own session. The complete
    diagnostic is flushed first; closing only stdio lets that transport observe
    EOF and return UNKNOWN without waiting for or terminating this custodian.
    A separately authorized reconciliation is required. No new worker is made.
    """
    require(controller.effects, 'caller_retention_without_effects')
    for fd in (0, 1, 2):
        try:
            os.close(fd)
        except OSError:
            pass
    while True:
        signal.pause()  # Keep strong references; never stop, unlock or retry.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--broker', action='store_true')
    args = parser.parse_args(argv)
    controller = Controller()
    try:
        if args.broker:
            broker_main(args.manifest_sha256)
            return 0
        result = execute(controller, args.manifest_sha256)
        raw = canonical(result)
        require(len(raw) <= MAX_RESULT, 'caller_output_bound')
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
        return 0
    except BaseException as exc:
        try:
            reason = str(exc) if isinstance(exc, AcceptanceRejected) else type(exc).__name__
            result = {'kind': 'R156A1_SAME_IMAGE_SEED_FINITE', 'result': 'NOT_ACCEPTED',
                'state': 'OUTCOME_UNKNOWN' if controller.effects else 'REFUSED',
                'reason': reason[:160], 'reasonType': type(exc).__name__,
                'observations': controller.snapshot(), 'partialStatePreserved': True,
                'normalCloseClaimed': False, 'projectedFiniteAccepted': False,
                'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
                'automaticCleanup': False, 'automaticRetry': False}
            if controller.effects:
                result['custody'] = {'state': 'RETAINED_CONTROLLER', 'pid': os.getpid(),
                    'startTicks': int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])}
            raw = canonical(result)
            if len(raw) > MAX_RESULT:
                raw = canonical({'kind': 'R156A1_SAME_IMAGE_SEED_FINITE', 'result': 'NOT_ACCEPTED',
                    'state': 'OUTCOME_UNKNOWN', 'reason': 'caller_failure_report_bound',
                    'custody': result.get('custody'), 'normalCloseClaimed': False,
                    'automaticCleanup': False, 'automaticRetry': False})
            sys.stderr.buffer.write(raw)
            sys.stderr.buffer.flush()
        finally:
            # A report/snapshot error or broken transport must not drop custody.
            if controller.effects:
                retain_alive(controller)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
