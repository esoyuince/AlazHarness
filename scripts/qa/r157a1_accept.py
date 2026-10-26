'Fixed R157 installed-runtime readiness preparation and one explicit attempt.\nReads only the exact accepted R156 ordinary001 proof and unchanged producer/driver.\nFresh R157 evidence and intent bind one seed/readiness/normal-close attempt; no finite work.\nApply revalidates every original/current/frozen byte before its exclusive execution marker.\n'
from __future__ import annotations

import argparse
import ast
import base64
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
BASE_COMMIT = 'cdc974728e69f590838b82421cd244e36554a74f'
LAB = 'AlazHarness-D3B-P71C'
SEED = 'scripts/bootstrap_retained_profile_r156.py'
CALLER = 'scripts/qa/r157a1_linux_accept.py'
CHILD = 'scripts/qa/r157a1_seed_child.py'
TRANSPORT = 'scripts/qa/r157a1_linux_transport.py'
ORDINARY_DRIVER = 'scripts/qa/r156a1_ordinary_seed.py'
SOURCES = {SEED, CALLER, CHILD}
PROOF_FILES = {'result.json', 'producer-source.py', 'linux-runner.py',
               'execution-start.json', 'stdout.txt', 'stderr.txt'}
REVIEWED_TRANSPORT_SHA = '166a1b33e4b2aa463ac0a9b6ca07b8f7f884eb1a98630c84dcdeb966eafdaa91'
REVIEWED_CALLER_SHA = '80d7855c047c11bb7154647cc4c978db08dfa2aa7dce98ab3328a8a4257fa2d9'
REVIEWED_CHILD_SHA = 'f742f9f6edc0132fbb3f331cbad5d52905c7af08109b24cdfe211551ef2824eb'
RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
HARNESS = 'e641a5000810efb2a453ae847f689b422f7d41a7'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
MAX_SOURCE = 262144
MAX_BUNDLE = 524288
MAX_OUTPUT = 2 * 1024 * 1024
MAX_RECEIPT = MAX_OUTPUT
COMMUNICATION_SECONDS = 240
CHECKS = ['preflight', 'response_preflight', 'before_epoch',
          'response_before_epoch', 'after_epoch', 'response_after_epoch']
SEED_FIELDS = set('''kind result state phase home pid parentPid startTicks gatewayUid
socketGroupGid supplementaryGroups resUid resGid mountNamespaceInode mountNamespace
profileIdentity databaseIdentities mount handoff handoffSha256 previousEpoch instanceId
ownerState consumerState allThreeConnectionsPhysicallyClosed profileLeaseReleasedNormally
retainedCapturedWhileLeaseHeld normalLoopShutdown outstandingAsyncTasks outstandingThreads
completedChecks coldHelperCalls sqliteOpenCount qualifiedNativeSourceCount auxiliaryInitialization
executedTasks realModelCalls listenersCreated apiAdmissionPublished installationReceiptSha256
harnessCommit nativeFeature verificationMillis nativeMillis totalMillis projectedReadinessAccepted
fullD3BAccepted automaticCleanup automaticRetry'''.split())
_PENDING = []  # Keep unresolved local process/pipe references; never terminate them.


ORIGINAL_ORDINARY_DIRECTORY = 'evidence/m1-native-finite-r156a1/ordinary001'
REVIEWED_ORIGINAL_PROOF = {'execution-start.json': {'sha256': '49f960fc0727a550f263be79643d2aa54de4543b674e020d8b2a52257ce13108', 'size': 363}, 'linux-runner.py': {'sha256': '3a89fb5cbd74642b67876ffe3ada4f429318a68eff9db41ecb0c11dc670642ab', 'size': 7402}, 'producer-source.py': {'sha256': '02ac2d81d72e0ab11739081b3b95ccb05db2871581bc3494518fe2190a66a5aa', 'size': 35124}, 'result.json': {'sha256': 'e42a277a3371f168a08cd78f07af2253840d6004b5730c3b4dbb4de095469ae8', 'size': 11738}, 'stderr.txt': {'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0}, 'stdout.txt': {'sha256': '2851d36fb219f6b82959f30647c792a82dd969e22e7512367fea65fcc14b195c', 'size': 10142}}
REVIEWED_PRODUCER_SHA = '02ac2d81d72e0ab11739081b3b95ccb05db2871581bc3494518fe2190a66a5aa'
REVIEWED_ORDINARY_DRIVER_SHA = 'baa56be5f0df56a1e9679bb8efccb445aafd31c32c0fc0c4b2c22ce17fde13a7'

def original_ordinary_directory(path, *, exists):
    require(exists is True, 'runner_original_ordinary_read_only')
    path = path_without_alias(path, exists=True)
    expected = path_without_alias(ROOT / ORIGINAL_ORDINARY_DIRECTORY, exists=True)
    require(path == expected and path.is_dir(), 'runner_original_ordinary_directory')
    require({p.name for p in path.iterdir()} == PROOF_FILES, 'runner_original_ordinary_inventory')
    return path


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


def pretty(value):
    return (json.dumps(value, sort_keys=True, indent=2,
                       ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')


def parse(raw, maximum, *, form='frame'):
    require(type(raw) is bytes and 0 < len(raw) <= maximum, 'runner_json_size')
    def unique(rows):
        value = {}
        for key, item in rows:
            require(key not in value, 'runner_duplicate_json_key')
            value[key] = item
        return value
    def no_number(_):
        raise RunnerRejected('runner_noninteger_json')
    def integer(value):
        require(len(value.lstrip('-')) <= 20, 'runner_json_integer_bound')
        return int(value)
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=unique,
                           parse_int=integer, parse_float=no_number, parse_constant=no_number)
    except (UnicodeError, ValueError, RecursionError):
        raise RunnerRejected('runner_json_invalid') from None
    encoded = pretty(value) if form == 'pretty' else canonical(value)
    if form == 'wire':
        encoded = encoded[:-1]
    require(encoded == raw, 'runner_json_noncanonical')
    return value


def exact(value, fields, reason):
    require(type(value) is dict and set(value) == set(fields), reason)
    return value


def number(value, low=0, high=2**63 - 1):
    require(type(value) is int and low <= value <= high, 'runner_integer')
    return value


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'runner_digest')
    return value


def flags(value, names, expected, reason):
    require(all(value.get(name) is expected for name in names), reason)


def path_without_alias(path, *, exists=True):
    path = Path(os.path.abspath(path))
    require(path.resolve(strict=exists) == path
            and not any(p.is_symlink() for p in (path, *path.parents)), 'runner_path_alias')
    return path


def owned_directory(path, *, exists):
    path = path_without_alias(path, exists=exists)
    base = path_without_alias(ROOT / 'evidence/m1-installed-readiness-r157a1', exists=False)
    require(path.parent == base and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,63}', path.name),
            'runner_owned_evidence_directory')
    if exists:
        require(path.is_dir(), 'runner_evidence_directory')
    else:
        require(not os.path.lexists(path), 'runner_evidence_exists')
    return path


def read_file(path, maximum=MAX_SOURCE, *, empty=False):
    path = path_without_alias(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and int(not empty) <= before.st_size <= maximum, 'runner_regular_file')
    options = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, options)
    try:
        opened = os.fstat(fd)
        def common(s):
            return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_nlink,
                    getattr(s, 'st_birthtime_ns', getattr(s, 'st_birthtime', None)))
        def stamp(s):
            return common(s) + (s.st_ctime_ns,)
        # Windows can expose creation time through path ctime and change time
        # through descriptor ctime. Compare only common metadata across views;
        # retain the full, including-ctime stamp separately within each view.
        cross = common if sys.platform == 'win32' else stamp
        require(cross(opened) == cross(before), 'runner_file_changed')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after, last = os.fstat(fd), path.lstat()
        require(len(raw) == before.st_size and stamp(after) == stamp(opened)
                and stamp(last) == stamp(before) and cross(after) == cross(last),
                'runner_file_changed')
        return raw
    finally:
        os.close(fd)


def put(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def current_head():
    process = subprocess.Popen(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, close_fds=True)
    try:
        out, err = process.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        _PENDING.append(process)
        raise RunnerRejected('runner_git_observation_unknown') from None
    require(process.returncode == 0 and not err and out.strip() == BASE_COMMIT.encode('ascii')
            and len(out) <= 64, 'runner_base_commit_changed')
    return BASE_COMMIT


def ordinary_literals(raw):
    """Read only the ordinary driver's fixed literals; never execute its module."""
    tree = ast.parse(raw.decode('utf-8'))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name not in ('PRODUCER_SHA', 'LINUX'):
                continue
            require(name not in values, 'runner_ordinary_literal_duplicate')
            value = node.value
            if (name == 'LINUX' and isinstance(value, ast.Call) and not value.args
                    and not value.keywords and isinstance(value.func, ast.Attribute)
                    and value.func.attr == 'lstrip'):
                values[name] = ast.literal_eval(value.func.value).lstrip()
            else:
                values[name] = ast.literal_eval(value)
    exact(values, {'PRODUCER_SHA', 'LINUX'}, 'runner_ordinary_literals')
    require(all(type(v) is str for v in values.values()), 'runner_ordinary_literal_types')
    return values['PRODUCER_SHA'], values['LINUX'].encode('utf-8')


def b64(raw, maximum):
    require(type(raw) is str and len(raw) <= 4 * ((maximum + 2) // 3), 'runner_base64_size')
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, UnicodeError):
        raise RunnerRejected('runner_base64') from None
    require(len(decoded) <= maximum and base64.b64encode(decoded).decode('ascii') == raw, 'runner_base64')
    return decoded


def pair(value):
    require(type(value) is list and len(value) == 2, 'runner_identity_pair')
    return [number(x, 1, 2**64 - 1) for x in value]


def validate_seed(seed, *, home, instance):
    exact(seed, SEED_FIELDS, 'runner_seed_fields')
    expected = {'kind': 'R156A1_TASK_FREE_RETAINED_SEED', 'result': 'PASS',
                'state': 'RETAINED_SEED_CREATED', 'phase': 'COMPLETE', 'home': home,
                'instanceId': instance, 'previousEpoch': 1, 'gatewayUid': 23001,
                'socketGroupGid': 23003, 'ownerState': 'CLOSED', 'consumerState': 'DETACHED',
                'installationReceiptSha256': RECEIPT_SHA, 'harnessCommit': HARNESS, 'nativeFeature': NATIVE}
    for key, value in expected.items():
        require(type(seed[key]) is type(value) and seed[key] == value, 'runner_seed_identity')
    for key in ('pid', 'parentPid', 'startTicks', 'mountNamespaceInode', 'sqliteOpenCount', 'qualifiedNativeSourceCount'):
        number(seed[key], 1)
    require(seed['pid'] != seed['parentPid'] and seed['resUid'] == [23001] * 3
            and seed['resGid'] == [23003] * 3
            and type(seed['supplementaryGroups']) is list
            and all(type(x) is int and x == 23003 for x in seed['supplementaryGroups']),
            'runner_seed_principal')
    require(seed['mountNamespace'] == 'mnt:[' + str(seed['mountNamespaceInode']) + ']',
            'runner_seed_namespace')
    flags(seed, ('allThreeConnectionsPhysicallyClosed', 'profileLeaseReleasedNormally',
                 'retainedCapturedWhileLeaseHeld', 'normalLoopShutdown'), True, 'runner_seed_close')
    flags(seed, ('apiAdmissionPublished', 'projectedReadinessAccepted', 'fullD3BAccepted',
                 'automaticCleanup', 'automaticRetry'), False, 'runner_seed_scope')
    require(all(number(seed[k]) == 0 for k in ('outstandingAsyncTasks', 'outstandingThreads',
                'executedTasks', 'realModelCalls', 'listenersCreated')), 'runner_seed_work')
    require(seed['completedChecks'] == CHECKS and seed['coldHelperCalls'] == [
        {'phase': 'START_OWNER', 'script': name}
        for name in ('run_store_preopen.py', 'run_response_preopen.py')], 'runner_seed_checks')
    for name in ('verificationMillis', 'nativeMillis', 'totalMillis'):
        number(seed[name], 0, 34999)
    require(seed['verificationMillis'] + seed['nativeMillis'] <= seed['totalMillis'], 'runner_seed_timing')
    profile = pair(seed['profileIdentity'])
    require(type(seed['databaseIdentities']) is list and len(seed['databaseIdentities']) == 3,
            'runner_seed_stores')
    identities = [pair(x) for x in seed['databaseIdentities']]
    require(len({tuple(x) for x in identities}) == 3
            and all(x[0] == profile[0] for x in identities), 'runner_seed_stores')
    mount = exact(seed['mount'], {'mount_id', 'device', 'root', 'mount_point', 'filesystem'}, 'runner_seed_mount')
    number(mount['mount_id'], 1)
    require(type(mount['device']) is list and len(mount['device']) == 2, 'runner_seed_mount_device')
    for value in mount['device']:
        number(value)
    for name in ('root', 'mount_point'):
        value = mount[name]
        require(type(value) is str and value.startswith('/') and str(PurePosixPath(value)) == value
                and '..' not in PurePosixPath(value).parts, 'runner_seed_mount_path')
    require(mount['filesystem'] == 'ext4', 'runner_seed_mount_filesystem')
    auxiliary = exact(seed['auxiliaryInitialization'], {'sourceDerivedCacheEntries', 'sourceDerivedCacheSha256',
        'completeToolRegistrationPerformed', 'activeSessionEntries', 'blockedIpv6CapabilityProbe'},
        'runner_seed_auxiliary')
    number(auxiliary['sourceDerivedCacheEntries'], 1, 1024)
    digest(auxiliary['sourceDerivedCacheSha256'])
    require(auxiliary['completeToolRegistrationPerformed'] is False
            and number(auxiliary['activeSessionEntries']) == 0, 'runner_seed_auxiliary_scope')
    probe = exact(auxiliary['blockedIpv6CapabilityProbe'], {'count', 'socketClosed', 'bindPerformed'},
                  'runner_seed_ipv6_probe_fields')
    require(number(probe['count']) == 1 and probe['socketClosed'] is True
            and probe['bindPerformed'] is False, 'runner_seed_ipv6_probe')
    require(type(seed['handoff']) is str, 'runner_seed_handoff')
    wire = seed['handoff'].encode('ascii')
    require(sha(wire) == digest(seed['handoffSha256']), 'runner_seed_handoff_digest')
    handoff = exact(parse(wire, 16384, form='wire'), {'protocol', 'state', 'response', 'retained'},
                    'runner_seed_handoff_fields')
    require(handoff['protocol'] == 'alaz-retained-startup-v1', 'runner_seed_handoff_protocol')
    retained = exact(handoff['retained'], {'native_feature', 'home', 'home_identity', 'database_identities',
        'epoch', 'instance_id', 'discovery_sha256'}, 'runner_seed_retained_fields')
    number(retained['epoch'], 1, 1)
    require(retained == {'native_feature': NATIVE, 'home': home, 'home_identity': profile,
        'database_identities': identities, 'epoch': 1, 'instance_id': instance,
        'discovery_sha256': auxiliary['sourceDerivedCacheSha256']}, 'runner_seed_retained_identity')
    state, response = handoff['state'], handoff['response']
    require(type(state) is dict and type(response) is dict and state.get('journal_mode') == 'delete'
            and state.get('epoch') == 1 and type(state.get('epoch')) is int
            and state.get('instance_id') == instance and state.get('state_identity') == identities[0]
            and state.get('replay_identity') == identities[1]
            and response.get('response_identity') == identities[2], 'runner_seed_handoff_identity')
    return seed


def validate_ordinary(files, producer, driver):
    exact(files, PROOF_FILES, 'runner_ordinary_inventory')
    producer_sha = sha(producer)
    literal_sha, linux = ordinary_literals(driver)
    require(literal_sha == producer_sha and files['producer-source.py'] == producer
            and files['linux-runner.py'] == linux, 'runner_ordinary_source_changed')
    start = parse(files['execution-start.json'], 8192, form='pretty')
    exact(start, {'state', 'attempt', 'startedUtc', 'producerSha256', 'linuxRunnerSha256',
                  'rootRequested', 'lab'}, 'runner_ordinary_start_fields')
    require(start['state'] == 'EXECUTION_STARTED_NO_REPLAY' and start['rootRequested'] is False
            and start['lab'] == LAB and start['producerSha256'] == producer_sha
            and start['linuxRunnerSha256'] == sha(linux)
            and type(start['attempt']) is str and re.fullmatch('ordinary00[1-9]', start['attempt']),
            'runner_ordinary_start')
    require(type(start['startedUtc']) is str and len(start['startedUtc']) <= 64
            and datetime.datetime.fromisoformat(start['startedUtc']).utcoffset() == datetime.timedelta(0),
            'runner_ordinary_started_time')
    result = parse(files['result.json'], MAX_OUTPUT, form='pretty')
    exact(result, {'result', 'exitCode', 'rootRequested', 'stdoutSha256', 'stderrSha256',
                   'producerSha256', 'automaticRetry', 'automaticCleanup', 'proof'}, 'runner_ordinary_result_fields')
    require(result['result'] == 'PASS' and result['rootRequested'] is False
            and number(result['exitCode']) == 0 and result['producerSha256'] == producer_sha
            and result['automaticRetry'] is False and result['automaticCleanup'] is False
            and result['stdoutSha256'] == sha(files['stdout.txt'])
            and result['stderrSha256'] == sha(files['stderr.txt']), 'runner_ordinary_not_accepted')
    proof = parse(files['stdout.txt'], MAX_SOURCE)
    require(type(proof) is dict and result['proof'] == proof
            and proof.get('kind') == 'R156A1_ORDINARY_NATIVE_SEED_PROOF'
            and proof.get('phase') == 'COMPLETE' and proof.get('result') == 'PASS'
            and proof.get('sourceSha256') == producer_sha, 'runner_ordinary_proof')
    flags(proof, ('rootUsed', 'projectedReadinessAccepted', 'sameImageReadinessAccepted',
                  'fullD3BAccepted', 'automaticCleanup', 'automaticRetry'), False, 'runner_ordinary_scope')
    flags(proof, ('nativeAccepted', 'physicalDatabaseCloseAccepted', 'producerTerminalObserved',
                  'nativeProcessAttempted'), True, 'runner_ordinary_terminal')
    require(number(proof.get('producerExitCode')) == 0
            and number(proof.get('executedTasks')) == number(proof.get('realModelCalls')) == 0,
            'runner_ordinary_exit_or_work')
    for name in ('producerPid', 'controllerPid'):
        number(proof.get(name), 1)
    attempt = start['attempt']
    base = '/tmp/alaz-r156a1-' + attempt
    require(proof.get('path') == base, 'runner_ordinary_home')
    out, err = b64(proof.get('producerStdoutBase64'), 32768), b64(proof.get('producerStderrBase64'), 65536)
    require(number(proof.get('producerStdoutBytes')) == len(out)
            and number(proof.get('producerStderrBytes')) == len(err)
            and proof.get('producerStdoutSha256') == sha(out)
            and proof.get('producerStderrSha256') == sha(err), 'runner_ordinary_producer_output')
    seed = validate_seed(parse(out, 32768), home=base + '/profile', instance='r156a1-' + attempt)
    require(proof.get('seed') == seed and seed['pid'] == proof['producerPid']
            and seed['parentPid'] == proof['controllerPid']
            and seed['supplementaryGroups'] == proof.get('supplementaryGroups'),
            'runner_ordinary_producer_identity')
    return result


def proof_bytes(directory):
    directory = original_ordinary_directory(directory, exists=True)
    files = {name: read_file(directory / name, MAX_OUTPUT if name in ('result.json', 'stderr.txt')
                           else MAX_SOURCE, empty=name == 'stderr.txt') for name in sorted(PROOF_FILES)}
    require({name: row(raw) for name, raw in files.items()} == REVIEWED_ORIGINAL_PROOF,
            'runner_original_ordinary_bytes_changed')
    return files


def row(raw):
    return {'sha256': sha(raw), 'size': len(raw)}


def proof_binding(directory, files, driver):
    return {'kind': 'R157A1_ORDINARY_PROOF_BINDING', 'ordinaryDirectory': str(directory),
            'files': {name: row(raw) for name, raw in sorted(files.items())},
            'ordinaryDriver': row(driver)}


def current_inputs():
    sources = {name: read_file(ROOT / name) for name in sorted(SOURCES)}
    transport = read_file(ROOT / TRANSPORT)
    require(sha(transport) == REVIEWED_TRANSPORT_SHA and sha(sources[CALLER]) == REVIEWED_CALLER_SHA
            and sha(sources[CHILD]) == REVIEWED_CHILD_SHA,
            'runner_reviewed_sources_changed')
    driver = read_file(ROOT / ORDINARY_DRIVER)
    require(sha(sources[SEED]) == REVIEWED_PRODUCER_SHA
            and sha(driver) == REVIEWED_ORDINARY_DRIVER_SHA, 'runner_original_r156_sources_changed')
    return sources, transport, read_file(SELF), driver


def make_bundle(sources, manifest):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted({**sources, 'manifest.json': manifest}.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, raw)
    raw = stream.getvalue()
    require(len(raw) <= MAX_BUNDLE, 'runner_bundle_bound')
    return raw


def prepared_files(directory, sources, transport, host, driver, ordinary, head):
    binding = canonical(proof_binding(directory, ordinary, driver))
    source_rows = {name: row(raw) for name, raw in sorted(sources.items())}
    manifest = canonical({'protocol': 'alaz-r157a1-input-v1', 'files': source_rows})
    bundle = make_bundle(sources, manifest)
    intent = {'kind': 'R157A1_SAME_IMAGE_ACCEPT_INTENT', 'lab': LAB,
        'inputRoot': '/opt/alaz-r157a1-accept-input', 'stateRoot': '/srv/alaz-r157a1',
        'manifestSha256': sha(manifest), 'bundleSha256': sha(bundle), 'bundleBytes': len(bundle),
        'transportSha256': sha(transport), 'hostRunnerSha256': sha(host),
        'ordinaryProofSha256': sha(binding), 'ordinaryProducerSha256': sha(sources[SEED]),
        'sourceFiles': source_rows, 'baseCommit': head}
    receipt = {'kind': 'R157A1_HOST_PREPARATION', 'result': 'PREPARED', 'rootRequested': False,
        'intentSha256': sha(canonical(intent)), 'ordinaryProofSha256': sha(binding),
        'ordinaryResultSha256': sha(ordinary['result.json']), 'producerSha256': sha(sources[SEED]),
        'baseCommit': head, 'automaticRetry': False, 'automaticCleanup': False}
    files = {'sources/' + name: raw for name, raw in sources.items()}
    files.update({'ordinary/' + name: raw for name, raw in ordinary.items()})
    files.update({'manifest.json': manifest,
                  'bundle.zip.b64': base64.b64encode(bundle) + b'\n', 'transport.py': transport,
                  'host-runner.py': host, 'ordinary-driver-source.py': driver, 'ordinary-proof.json': binding,
                  'intent.json': canonical(intent), 'prepared.json': canonical(receipt)})
    return files, intent, receipt


def prepare(evidence, ordinary_directory):
    evidence = owned_directory(evidence, exists=False)
    ordinary_directory = original_ordinary_directory(ordinary_directory, exists=True)
    head = current_head()
    sources, transport, host, driver = current_inputs()
    ordinary = proof_bytes(ordinary_directory)
    validate_ordinary(ordinary, sources[SEED], driver)
    files, _, receipt = prepared_files(ordinary_directory, sources, transport, host, driver, ordinary, head)
    # No evidence directory or application input exists before the full PASS gate.
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(exist_ok=False)
    for name, raw in sorted(files.items()):
        path = evidence / name
        path.parent.mkdir(parents=True, exist_ok=True)
        put(path, raw)
    return receipt


def load_prepared(evidence, expected_intent):
    evidence = owned_directory(evidence, exists=True)
    digest(expected_intent)
    require(not any(os.path.lexists(evidence / name)
                    for name in ('execution-start.json', 'stdout.txt', 'stderr.txt', 'result.json')),
            'runner_execution_no_replay')
    head = current_head()
    sources, transport, host, driver = current_inputs()
    raw_intent = read_file(evidence / 'intent.json', 16384)
    require(sha(raw_intent) == expected_intent, 'runner_expected_intent_changed')
    intent = parse(raw_intent, 16384)
    binding_raw = read_file(evidence / 'ordinary-proof.json', 8192)
    require(intent.get('ordinaryProofSha256') == sha(binding_raw), 'runner_ordinary_binding_changed')
    binding = parse(binding_raw, 8192)
    exact(binding, {'kind', 'ordinaryDirectory', 'files', 'ordinaryDriver'}, 'runner_ordinary_binding_fields')
    ordinary_directory = original_ordinary_directory(binding['ordinaryDirectory'], exists=True)
    ordinary = proof_bytes(ordinary_directory)
    validate_ordinary(ordinary, sources[SEED], driver)
    files, wanted, receipt = prepared_files(ordinary_directory, sources, transport, host, driver, ordinary, head)
    require(intent == wanted and canonical(wanted) == raw_intent, 'runner_intent_changed')
    found = set()
    for path in evidence.rglob('*'):
        require(not path.is_symlink() and path.resolve(strict=True) == path, 'runner_frozen_alias')
        if path.is_file():
            found.add(path.relative_to(evidence).as_posix())
        else:
            require(path.is_dir(), 'runner_frozen_object')
    require(found == set(files), 'runner_frozen_inventory')
    for name, raw in files.items():
        require(read_file(evidence / name, max(MAX_OUTPUT, len(raw)), empty=not raw) == raw,
                'runner_frozen_bytes_changed')
    frozen_bundle = read_file(evidence / 'bundle.zip.b64', 4 * ((MAX_BUNDLE + 2) // 3) + 1)
    require(frozen_bundle.endswith(b'\n') and frozen_bundle.count(b'\n') == 1,
            'runner_bundle_base64_frame')
    decoded = b64(frozen_bundle[:-1].decode('ascii'), MAX_BUNDLE)
    require(len(decoded) == wanted['bundleBytes'] and sha(decoded) == wanted['bundleSha256'],
            'runner_bundle_bytes_changed')
    return evidence, wanted, files


class BoundedPipe:
    """Bound the buffers used by Windows communicate() reader threads.

    Overflow is drained and discarded while the fixed timeout continues. The
    retained prefix is always bounded; timeout never closes or signals a child.
    """
    def __init__(self, raw):
        self.raw = raw
        self.data = bytearray()
        self.overflow = self.complete = False
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
                    remaining = MAX_OUTPUT - len(self.data)
                    self.data.extend(chunk[:remaining])
                    self.overflow = self.overflow or len(chunk) > remaining
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


def host_actor():
    require(sys.platform == 'win32' and os.name == 'nt'
            and sys.implementation.name == 'cpython', 'runner_windows_host_required')


def communicate_bounded(process, bundle, observation, returned_at):
    """Bound stdin write, both reader joins and terminal observation together.

    Windows communicate() can block synchronously while writing stdin. Its own
    timeout therefore runs inside a daemon worker, with a separate main-thread
    deadline measured immediately after Popen returns. On uncertainty the caller
    keeps this observation, worker, process and reader references without closing
    handles, signalling the process or invoking communicate a second time.
    """
    deadline = returned_at + COMMUNICATION_SECONDS
    observation.update(finishedAt=None, error=None)
    def invoke():
        try:
            process.communicate(bundle, timeout=COMMUNICATION_SECONDS)
        except BaseException as exc:
            observation['error'] = exc
        finally:
            observation['finishedAt'] = time.monotonic()
    worker = threading.Thread(target=invoke, name='r157-wsl-communication', daemon=True)
    observation['worker'] = worker
    worker.start()
    worker.join(timeout=max(0, deadline - time.monotonic()))
    require(not worker.is_alive() and observation['finishedAt'] is not None
            and observation['finishedAt'] <= deadline, 'runner_communication_deadline_unknown')
    if observation['error'] is not None:
        raise observation['error']
    require(type(process.returncode) is int, 'runner_terminal_observation_unknown')


def command_for(files, intent):
    command = ['wsl.exe', '--distribution', LAB, '--user', 'root', '--cd', '/',
               '--exec', '/usr/bin/python3.12', '-I', '-B', '-c',
               files['transport.py'].decode('utf-8'), canonical(intent).decode('ascii')[:-1]]
    require(len(subprocess.list2cmdline(command)) < 32760, 'runner_windows_command_bound')
    return command


def output_row(value, maximum):
    exact(value, {'bytes', 'sha256', 'base64'}, 'runner_transport_output_fields')
    raw = b64(value['base64'], maximum)
    require(number(value['bytes']) == len(raw) and value['sha256'] == sha(raw), 'runner_transport_output_digest')
    return raw


def transport_result(out, err, exit_code, intent):
    require(not err, 'runner_transport_stderr')
    report = parse(out, MAX_OUTPUT)
    require(type(report) is dict and report.get('kind') == 'R157A1_ROOT_TRANSPORT'
            and report.get('rootUsed') is True and report.get('automaticRetry') is False
            and report.get('automaticCleanup') is False, 'runner_transport_identity')
    if report.get('result') != 'PASS':
        # A live-custody claim was observed inside the Linux transport only.
        # This host does not claim the root PID remains live after WSL exits.
        observation = {'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN', 'transport': report,
                       'continuingLiveCustodyVerified': False}
        if report.get('state') == 'CALLER_RETAINED_OUTCOME_UNKNOWN':
            require(exit_code == 2 and report.get('intentSha256') == sha(canonical(intent))
                    and report.get('manifestSha256') == intent['manifestSha256']
                    and report.get('verifiedLiveCustody') is True
                    and report.get('callerTerminalObserved') is False
                    and report.get('pipesComplete') is True, 'runner_retained_observation')
            custody = exact(report.get('custody'), {'state', 'pid', 'startTicks'}, 'runner_retained_fields')
            require(custody['state'] == 'RETAINED_CONTROLLER'
                    and number(custody['pid'], 1) == number(report.get('callerPid'), 1)
                    and number(custody['startTicks'], 1) == number(report.get('callerStartTicks'), 1),
                    'runner_retained_identity')
            caller = parse(output_row(report.get('stderr'), 524288), 524288)
            require(not output_row(report.get('stdout'), 524288) and caller == report.get('caller')
                    and caller.get('kind') == 'R157A1_SAME_IMAGE_SEED_READINESS'
                    and caller.get('result') == 'NOT_ACCEPTED'
                    and caller.get('state') == 'OUTCOME_UNKNOWN' and caller.get('custody') == custody,
                    'runner_retained_diagnostic')
            observation.update(custodyObservedBeforeTransportExit=custody)
        return observation
    require(type(exit_code) is int and exit_code == 0 and report.get('phase') == 'OBSERVED'
            and report.get('state') == 'CALLER_TERMINAL_ACCEPTED'
            and report.get('intentSha256') == sha(canonical(intent))
            and report.get('manifestSha256') == intent['manifestSha256']
            and report.get('pipesComplete') is True and report.get('callerTerminalObserved') is True
            and type(report.get('callerExitCode')) is int and report['callerExitCode'] == 0,
            'runner_transport_acceptance')
    number(report.get('callerPid'), 1)
    number(report.get('callerStartTicks'), 1)
    caller = parse(output_row(report.get('stdout'), 524288), 524288)
    require(not output_row(report.get('stderr'), 524288) and caller == report.get('caller')
            and caller.get('kind') == 'R157A1_SAME_IMAGE_SEED_READINESS'
            and caller.get('result') == 'PASS' and caller.get('state') == 'SAME_IMAGE_SEED_READINESS_CLOSED'
            and caller.get('manifestSha256') == intent['manifestSha256'], 'runner_caller_identity')
    flags(caller, ('projectedReadinessAccepted', 'sameImageSeedAndReadiness', 'sameOriginalSupervisor',
                  'allOwnedChildrenTerminal', 'hostMountNamespaceUnchanged', 'hostMountTableUnchanged',
                  'brokerMetadataFixtureOnly'), True, 'runner_caller_close')
    flags(caller, ('realBrokerExchangeAccepted', 'serviceStarted', 'runtimeAdmissionAuthorized',
                  'finiteWorkExecuted', 'fullD3BAccepted', 'm1Accepted', 'productionReady',
                  'automaticCleanup', 'automaticRetry'), False, 'runner_caller_scope')
    require(number(caller.get('executedTasks')) == number(caller.get('realModelCalls')) == 0,
            'runner_caller_work')
    validate_seed(caller.get('seedResult'), home='/srv/alaz-r157a1/mount/profile', instance='r157a1-seed')
    ready = caller.get('readiness')
    require(type(ready) is dict and ready.get('state') == 'SUPERVISED_PROJECTED_OWNER_CLOSED'
            and ready.get('childExited') is True and ready.get('volumeMayClose') is True
            and ready.get('observedAfterUnknown') is False
            and ready.get('finiteWorkExecuted') is False and ready.get('fullD3BAccepted') is False
            and type(ready.get('owner')) is dict and type(ready['owner'].get('epoch')) is int
            and ready['owner']['epoch'] == 2 and ready['owner'].get('completedChecks') == CHECKS,
            'runner_readiness_close')
    closure = caller.get('closure')
    require(type(closure) is dict and type(closure.get('finish')) is dict
            and closure['finish'].get('state') == 'CLOSED', 'runner_volume_close')
    flags(closure['finish'], ('ownedUsersGone', 'loopAttachmentGone', 'fenceRemovedAfterCleanup',
                             'leaseReleasedLast'), True, 'runner_volume_close')
    return {'result': 'PASS', 'state': 'SAME_IMAGE_SEED_READINESS_ACCEPTED', 'transport': report,
            'projectedReadinessAccepted': True, 'continuingLiveCustodyVerified': False}


def apply(evidence, expected_intent):
    host_actor()
    evidence, intent, files = load_prepared(evidence, expected_intent)
    command = command_for(files, intent)
    marker = {'kind': 'R157A1_HOST_EXECUTION_START', 'state': 'EXECUTION_STARTED_NO_REPLAY',
        'intentSha256': expected_intent, 'ordinaryProofSha256': intent['ordinaryProofSha256'],
        'manifestSha256': intent['manifestSha256'], 'bundleSha256': intent['bundleSha256'],
        'hostRunnerSha256': intent['hostRunnerSha256'], 'baseCommit': BASE_COMMIT,
        'rootRequested': True, 'lab': LAB, 'hostPid': os.getpid(),
        'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    put(evidence / 'execution-start.json', canonical(marker))
    result = {'kind': 'R157A1_HOST_ACCEPTANCE', 'result': 'UNKNOWN', 'state': 'ROOT_OUTCOME_UNKNOWN',
        'intentSha256': expected_intent, 'ordinaryProofSha256': intent['ordinaryProofSha256'],
        'manifestSha256': intent['manifestSha256'], 'rootRequested': True,
        'executionStartSha256': sha(canonical(marker)), 'transportTerminalObserved': False,
        'communicationDeadlineSeconds': COMMUNICATION_SECONDS,
        'communicationCompletedWithinDeadline': False,
        'continuingLiveCustodyVerified': False, 'projectedReadinessAccepted': False,
        'fullD3BAccepted': False, 'm1Accepted': False, 'productionReady': False,
        'automaticCleanup': False, 'automaticRetry': False, 'partialStatePreserved': True}
    process = None
    readers = []
    communication = {}
    out = err = b''
    try:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True, bufsize=0)
        returned_at = time.monotonic()
        result['hostTransportPid'] = process.pid
        readers = [BoundedPipe(process.stdout), BoundedPipe(process.stderr)]
        process.stdout, process.stderr = readers
        bundle = b64(files['bundle.zip.b64'][:-1].decode('ascii'), MAX_BUNDLE)
        communicate_bounded(process, bundle, communication, returned_at)
        out, out_complete, out_overflow, out_error = readers[0].snapshot()
        err, err_complete, err_overflow, err_error = readers[1].snapshot()
        result.update(transportTerminalObserved=True, transportExitCode=process.returncode,
                      communicationCompletedWithinDeadline=True,
                      stdoutOverflow=out_overflow, stderrOverflow=err_overflow)
        require(out_complete and err_complete and not out_overflow and not err_overflow
                and out_error is None and err_error is None, 'runner_transport_capture_unknown')
        result.update(transport_result(out, err, process.returncode, intent))
    except BaseException as exc:
        if process is not None:
            _PENDING.append((process, readers, communication))
        if readers:
            out, _, out_overflow, _ = readers[0].snapshot()
            err, _, err_overflow, _ = readers[1].snapshot()
            result.update(stdoutOverflow=out_overflow, stderrOverflow=err_overflow)
        result.update(result='UNKNOWN', state='ROOT_OUTCOME_UNKNOWN',
                      reason=str(exc)[:160] if isinstance(exc, RunnerRejected) else type(exc).__name__,
                      reasonType=type(exc).__name__)
    require(len(out) <= MAX_OUTPUT and len(err) <= MAX_OUTPUT, 'runner_capture_bound')
    result.update(stdoutSha256=sha(out), stderrSha256=sha(err),
                  stdoutBytes=len(out), stderrBytes=len(err))
    if len(canonical(result)) > MAX_RECEIPT:
        result.pop('transport', None)
        result['transportReportAvailableInRawStdout'] = True
    try:
        put(evidence / 'stdout.txt', out)
        put(evidence / 'stderr.txt', err)
        raw = canonical(result)
        require(len(raw) <= MAX_RECEIPT, 'runner_receipt_bound')
        put(evidence / 'result.json', raw)
    except BaseException as exc:
        result.update(result='UNKNOWN', state='ROOT_OUTCOME_UNKNOWN',
                      reason='runner_evidence_write_failed', reasonType=type(exc).__name__,
                      evidenceWriteComplete=False, projectedReadinessAccepted=False)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    parser.add_argument('--evidence-directory', type=Path, required=True)
    parser.add_argument('--ordinary-evidence-directory', type=Path)
    parser.add_argument('--expected-intent-sha256')
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            require(args.ordinary_evidence_directory is not None and args.expected_intent_sha256 is None,
                    'runner_prepare_arguments')
            result = prepare(args.evidence_directory, args.ordinary_evidence_directory)
        else:
            require(args.ordinary_evidence_directory is None and args.expected_intent_sha256 is not None,
                    'runner_apply_arguments')
            result = apply(args.evidence_directory, args.expected_intent_sha256)
    except BaseException as exc:
        result = {'kind': 'R157A1_HOST_RUNNER_REFUSAL', 'result': 'NOT_ACCEPTED',
                  'reason': str(exc)[:160] if isinstance(exc, RunnerRejected) else type(exc).__name__,
                  'reasonType': type(exc).__name__, 'automaticRetry': False, 'automaticCleanup': False}
    print(canonical(result).decode('ascii'), end='')
    return 0 if result['result'] in ('PASS', 'PREPARED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
