'Fixed R157 root staging and observation transport.\nThree sources are frozen once: unchanged R156 producer, R157 seed boundary and readiness caller.\nThe original R155 bounded observation and unknown custody algorithm is retained.\n'
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import time
import zipfile

LAB = 'AlazHarness-D3B-P71C'
PYTHON = '/usr/bin/python3.12'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
INPUT = Path('/opt/alaz-r157a1-accept-input')
CALLER = 'scripts/qa/r157a1_linux_accept.py'
SEED = 'scripts/bootstrap_retained_profile_r156.py'
FILES = {SEED, CALLER, 'scripts/qa/r157a1_seed_child.py'}
MAX_BUNDLE = 512 * 1024
MAX_OUTPUT = 524288
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'TZ': 'UTC'}


class TransportRejected(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise TransportRejected(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def parse(raw, maximum):
    require(type(raw) is bytes and 0 < len(raw) <= maximum and raw.endswith(b'\n')
            and raw.count(b'\n') == 1, 'transport_json_frame')
    def unique(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'transport_duplicate_key')
            value[key] = item
        return value
    def no_number(_):
        raise TransportRejected('transport_noninteger_json')
    try:
        result = json.loads(raw.decode('ascii'), object_pairs_hook=unique,
                            parse_float=no_number, parse_constant=no_number)
    except (UnicodeError, ValueError, RecursionError):
        raise TransportRejected('transport_json') from None
    require(canonical(result) == raw, 'transport_json_canonical')
    return result


def validate_intent(value):
    require(type(value) is dict and set(value) == {'kind', 'lab', 'inputRoot', 'stateRoot',
        'manifestSha256', 'bundleSha256', 'bundleBytes', 'transportSha256', 'hostRunnerSha256',
        'ordinaryProofSha256', 'ordinaryProducerSha256', 'sourceFiles', 'baseCommit'}, 'transport_intent_fields')
    require(value['kind'] == 'R157A1_SAME_IMAGE_ACCEPT_INTENT' and value['lab'] == LAB
            and value['inputRoot'] == str(INPUT) and value['stateRoot'] == '/srv/alaz-r157a1',
            'transport_fixed_target')
    for name in ('manifestSha256', 'bundleSha256', 'transportSha256', 'hostRunnerSha256',
                 'ordinaryProofSha256', 'ordinaryProducerSha256'):
        require(type(value[name]) is str and re.fullmatch('[0-9a-f]{64}', value[name]) is not None,
                'transport_digest')
    require(type(value['baseCommit']) is str and re.fullmatch('[0-9a-f]{40}', value['baseCommit']) is not None,
            'transport_base_commit')
    require(type(value['bundleBytes']) is int and 0 < value['bundleBytes'] <= MAX_BUNDLE,
            'transport_bundle_size')
    rows = value['sourceFiles']
    require(type(rows) is dict and set(rows) == FILES, 'transport_source_inventory')
    for row in rows.values():
        require(type(row) is dict and set(row) == {'sha256', 'size'}
                and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None
                and type(row['size']) is int and 0 < row['size'] <= 262144, 'transport_source_entry')
    require(value['ordinaryProducerSha256'] == rows[SEED]['sha256'], 'transport_ordinary_source_mismatch')
    return value


def unpack(raw, intent):
    validate_intent(intent)
    require(len(raw) == intent['bundleBytes'] and sha(raw) == intent['bundleSha256'], 'transport_bundle_identity')
    expected = FILES | {'manifest.json'}
    data = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        require(len(infos) == len(expected) and {x.filename for x in infos} == expected,
                'transport_archive_inventory')
        for info in infos:
            require(info.compress_type == zipfile.ZIP_STORED and not info.is_dir()
                    and 0 < info.file_size == info.compress_size <= 262144,
                    'transport_archive_entry')
            data[info.filename] = archive.read(info)
    require(sha(data['manifest.json']) == intent['manifestSha256'], 'transport_manifest_identity')
    manifest = parse(data['manifest.json'], 8192)
    require(manifest == {'protocol': 'alaz-r157a1-input-v1', 'files': intent['sourceFiles']},
            'transport_manifest_contract')
    for name, row in intent['sourceFiles'].items():
        require(len(data[name]) == row['size'] and sha(data[name]) == row['sha256'], 'transport_source_identity')
    return data


def trusted(path, directory):
    require(path.resolve(strict=True) == path and path.is_absolute(), 'transport_canonical_path')
    for item in (path, *path.parents):
        info = item.lstat()
        require(info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022
                and not stat.S_ISLNK(info.st_mode), 'transport_trusted_path')
    require(path.is_dir() if directory else path.is_file(), 'transport_object_type')


def stage(data):
    trusted(INPUT.parent, True)
    require(not os.path.lexists(INPUT), 'transport_input_exists')
    os.umask(0o022)
    INPUT.mkdir(mode=0o755)
    (INPUT / 'scripts').mkdir(mode=0o755)
    (INPUT / 'scripts/qa').mkdir(mode=0o755)
    for name, raw in sorted(data.items()):
        path = INPUT / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
            os.fsync(stream.fileno())
        trusted(path, False)
        require(path.read_bytes() == raw and stat.S_IMODE(path.stat().st_mode) == 0o644,
                'transport_staging_readback')


def process_identity(pid):
    raw = Path('/proc/' + str(pid) + '/stat').read_text()
    prefix, separator, tail = raw.rpartition(') ')
    fields = tail.split()
    require(separator and prefix.startswith(str(pid) + ' (') and len(fields) >= 20
            and fields[0] not in ('Z', 'X', 'x'), 'transport_process_not_live')
    status = {}
    for line in Path('/proc/' + str(pid) + '/status').read_text().splitlines():
        if line.startswith(('Uid:', 'Gid:')):
            key, value = line.split(':', 1)
            status[key] = list(map(int, value.split()))
    require(status == {'Uid': [0] * 4, 'Gid': [0] * 4}, 'transport_caller_not_root')
    return {'pid': pid, 'startTicks': int(fields[19])}


def collect(process, observation, seconds=210):
    """Bound both streams before accepting bytes. EOF is distinct from exit."""
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    observation['buffers'] = buffers
    deadline = time.monotonic() + seconds
    with selectors.DefaultSelector() as selector:
        for name in buffers:
            stream = getattr(process, name)
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            left = deadline - time.monotonic()
            require(left > 0, 'transport_caller_output_timeout_unknown')
            for key, _ in selector.select(min(left, .25)):
                target = buffers[key.data]
                try:
                    chunk = os.read(key.fileobj.fileno(), min(16384, MAX_OUTPUT - len(target) + 1))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                remaining = MAX_OUTPUT - len(target)
                target.extend(chunk[:remaining])
                require(len(chunk) <= remaining, 'transport_caller_output_overflow_unknown')
    observation['pipesComplete'] = True
    return bytes(buffers['stdout']), bytes(buffers['stderr'])


def classify(process, identity, out, err):
    if out:
        require(not err, 'transport_mixed_caller_frames')
        result = parse(out, MAX_OUTPUT)
        require(result.get('kind') == 'R157A1_SAME_IMAGE_SEED_READINESS'
                and result.get('result') == 'PASS'
                and result.get('state') == 'SAME_IMAGE_SEED_READINESS_CLOSED', 'transport_positive_result')
        require(process.wait(timeout=5) == 0, 'transport_caller_exit')
        require(all(result.get(k) is True for k in ('projectedReadinessAccepted',
            'sameImageSeedAndReadiness', 'sameOriginalSupervisor', 'allOwnedChildrenTerminal',
            'hostMountNamespaceUnchanged', 'hostMountTableUnchanged', 'brokerMetadataFixtureOnly')),
            'transport_positive_proof')
        require(all(result.get(k) is False for k in ('realBrokerExchangeAccepted', 'serviceStarted',
            'runtimeAdmissionAuthorized', 'finiteWorkExecuted', 'fullD3BAccepted', 'm1Accepted',
            'productionReady', 'automaticCleanup', 'automaticRetry'))
            and all(type(result.get(k)) is int and result[k] == 0 for k in ('executedTasks', 'realModelCalls')),
            'transport_positive_scope')
        return {'result': 'PASS', 'state': 'CALLER_TERMINAL_ACCEPTED', 'callerTerminalObserved': True,
                'callerExitCode': 0, 'caller': result}
    result = parse(err, MAX_OUTPUT)
    require(result.get('kind') == 'R157A1_SAME_IMAGE_SEED_READINESS'
            and result.get('result') == 'NOT_ACCEPTED', 'transport_negative_result')
    custody = result.get('custody')
    if custody is not None:
        require(type(custody) is dict and set(custody) == {'state', 'pid', 'startTicks'}
                and custody['state'] == 'RETAINED_CONTROLLER'
                and type(custody['pid']) is int and custody['pid'] == process.pid
                and type(custody['startTicks']) is int and custody['startTicks'] == identity['startTicks']
                and process.poll() is None and process_identity(process.pid) == identity,
                'transport_custody_not_live_unknown')
        return {'result': 'NOT_ACCEPTED', 'state': 'CALLER_RETAINED_OUTCOME_UNKNOWN',
                'callerTerminalObserved': False, 'verifiedLiveCustody': True, 'custody': custody,
                'caller': result}
    require(result.get('state') == 'REFUSED' and process.wait(timeout=5) == 2,
            'transport_unclassified_caller_unknown')
    return {'result': 'NOT_ACCEPTED', 'state': 'CALLER_TERMINAL_REFUSED',
            'callerTerminalObserved': True, 'callerExitCode': 2, 'caller': result}


def main():
    report = {'kind': 'R157A1_ROOT_TRANSPORT', 'result': 'NOT_ACCEPTED', 'phase': 'PREFLIGHT',
              'rootUsed': True, 'automaticRetry': False, 'automaticCleanup': False}
    observation = {'pipesComplete': False}
    process = None
    try:
        require(len(sys.argv) == 2, 'transport_argument_count')
        intent = validate_intent(parse(sys.argv[1].encode('ascii') + b'\n', 16384))
        require(len(sys.orig_argv) == 6 and sys.orig_argv[:4] == [PYTHON, '-I', '-B', '-c']
                and sha(sys.orig_argv[4].encode('utf-8')) == intent['transportSha256'], 'transport_source_pin')
        require(sys.executable == PYTHON and sys.version_info[:2] == (3, 12)
                and sys.flags.isolated == 1 and sys.dont_write_bytecode and not sys.flags.optimize,
                'transport_interpreter')
        require(os.getresuid() == os.getresgid() == (0, 0, 0)
                and os.environ.get('WSL_DISTRO_NAME') == LAB
                and Path('/etc/alaz-p71c-lab-id').read_text().strip() == LAB
                and not Path('/mnt/c/Windows').exists(), 'transport_dedicated_root_lab')
        require(os.readlink('/proc/self/ns/user') == 'user:[4026531837]', 'transport_initial_userns')
        for name in ('uid_map', 'gid_map'):
            require(Path('/proc/self', name).read_text().split() == ['0', '0', '4294967295'], 'transport_initial_ids')
        trusted(Path(PYTHON), False)
        require(sha(Path(PYTHON).read_bytes()) == PYTHON_SHA, 'transport_python_changed')
        for name in (str(INPUT), '/srv/alaz-r157a1', '/sys/fs/cgroup/alaz-r157a1', '/tmp/alaz-ipc-r157a1'):
            require(not os.path.lexists(name), 'transport_fresh_paths_required')
        data = unpack(sys.stdin.buffer.read(MAX_BUNDLE + 1), intent)
        report.update(phase='STAGING_INPUTS', intentSha256=sha(canonical(intent)), manifestSha256=intent['manifestSha256'])
        stage(data)
        report['phase'] = 'CALLER_SPAWN_ATTEMPT'
        process = subprocess.Popen([PYTHON, '-I', '-B', str(INPUT / CALLER),
            '--manifest-sha256', intent['manifestSha256']], cwd='/', env=dict(ENV),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            close_fds=True, bufsize=0, start_new_session=True)
        report['callerPid'] = process.pid
        identity = process_identity(process.pid)
        report['callerStartTicks'] = identity['startTicks']
        out, err = collect(process, observation)
        report.update(classify(process, identity, out, err), phase='OBSERVED')
    except BaseException as exc:
        report.update(state='TRANSPORT_OUTCOME_UNKNOWN' if process is not None else 'TRANSPORT_REFUSED',
                      reason=str(exc)[:160] if isinstance(exc, TransportRejected) else type(exc).__name__,
                      reasonType=type(exc).__name__, partialStatePreserved=True)
    report['pipesComplete'] = observation['pipesComplete']
    for name, raw in observation.get('buffers', {}).items():
        report[name] = {'bytes': len(raw), 'sha256': sha(raw), 'base64': base64.b64encode(raw).decode('ascii')}
    sys.stdout.buffer.write(canonical(report))
    sys.stdout.buffer.flush()
    return 0 if report['result'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
