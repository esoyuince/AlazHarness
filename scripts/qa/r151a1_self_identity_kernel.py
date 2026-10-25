"""R151A1: ordinary-user, disposable-child Landlock map-grant evidence.

Exec here is a fixed QA Python entry, NOT the projected product launcher.
No root, mount, namespace, service, native store, model or network operation.
All product functions are imported unchanged from a hash-checked source bundle.
"""
from pathlib import Path, PurePosixPath
import argparse
import ctypes
import errno
import hashlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile

PYTHON = '/usr/bin/python3.12'
ENTRY = 'scripts/qa/r151a1_self_identity_kernel.py'
PRODUCT = tuple('packages/claw-hermes/' + name + '.py' for name in (
    'credential_guard', 'principal_launch', 'host_principal',
    'combined_guard', 'linux_netns'))
FILES = (*PRODUCT, ENTRY)
ROOT = Path(__file__).resolve().parents[2] if '__file__' in globals() else None
PREFIX = 'R151_RESULT '
DENIED = (errno.EACCES, errno.EPERM)


def environment():
    assert sys.platform == 'linux' and sys.executable == PYTHON
    assert sys.flags.isolated == 1 and sys.dont_write_bytecode and not sys.flags.optimize
    assert os.getresuid() == (23001,) * 3 and os.getresgid() == (23003,) * 3


def modules():
    sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
    import credential_guard
    import principal_launch
    for name in PRODUCT:
        module = sys.modules[Path(name).stem]
        assert Path(module.__file__).resolve() == ROOT / name
    return credential_guard, principal_launch


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def open_only(path, flags=os.O_RDONLY):
    """Never reads sensitive content and never writes, truncates or creates files."""
    try:
        fd = os.open(path, flags | os.O_CLOEXEC)
    except OSError as exc:
        return {'opened': False, 'errno': exc.errno}
    os.close(fd)
    return {'opened': True, 'errno': 0}


def targets(pid, foreign):
    base = '/proc/' + str(pid)
    return {
        'foreign_uid_map': ('/proc/' + str(foreign) + '/uid_map', os.O_RDONLY),
        'foreign_gid_map': ('/proc/' + str(foreign) + '/gid_map', os.O_RDONLY),
        'foreign_status': ('/proc/' + str(foreign) + '/status', os.O_RDONLY),
        'own_environ': (base + '/environ', os.O_RDONLY),
        'own_mem': (base + '/mem', os.O_RDONLY),
        'own_fd_directory': (base + '/fd', os.O_RDONLY | os.O_DIRECTORY),
        'own_proc_directory': (base, os.O_RDONLY | os.O_DIRECTORY),
        'own_uid_map_write_open': (base + '/uid_map', os.O_WRONLY),
        'own_gid_map_write_open': (base + '/gid_map', os.O_WRONLY),
    }


def expected_denials(items, baseline):
    result = {}
    for name, (path, flags) in items.items():
        after = open_only(path, flags)
        result[name] = {'before': baseline[name], 'after': after,
                        'pass': baseline[name]['opened'] is True and
                                after['opened'] is False and after['errno'] in DENIED}
    return result


def emit(value):
    print(PREFIX + json.dumps(value, sort_keys=True), flush=True)
    return 0 if value['result'] == 'PASS' else 1


def child(fixture, case, foreign):
    environment()
    guard, observer = modules()
    before = observer.observation()
    assert before['pid'] != foreign and before['threads'] == 1
    assert before['caps']['CapEff'] == before['caps']['CapPrm'] == 0
    source = hashes()
    canary = str(fixture / 'private/canary.txt')
    items = targets(os.getpid(), foreign)
    items['protected_canary'] = (canary, os.O_RDONLY)
    if case == 'default':
        items['own_uid_map_default'] = ('/proc/self/uid_map', os.O_RDONLY)
        items['own_gid_map_default'] = ('/proc/self/gid_map', os.O_RDONLY)
    baseline = {name: open_only(*item) for name, item in items.items()}
    assert all(value['opened'] for value in baseline.values()), 'baseline_open_not_allowed'
    policy = {'version': 1, 'enabled': True, 'self_process_metadata': True,
              'readonly': ['/usr', '/etc/ld.so.cache', str(ROOT / 'packages'), str(ROOT / 'scripts')],
              'writable': [str(fixture / 'rw'), '/dev/null'], 'protected': [canary]}
    receipt = guard.apply(policy, self_mount_metadata=True,
                          self_identity_metadata=case != 'default')
    carry = {'before': before, 'source': source, 'receipt': receipt,
             'baseline': baseline, 'fixture': str(fixture), 'foreign': foreign, 'case': case}
    if case == 'same-pid-exec':
        # Fixed QA target; no arbitrary executable, inherited environment or retry.
        os.execve(PYTHON, [PYTHON, '-I', '-B', str(ROOT / ENTRY),
                          '--after-exec', json.dumps(carry, sort_keys=True)],
                  {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        raise AssertionError('exec_returned')
    return inspect(carry, guard, observer, items)


def inspect(carry, guard, observer, items=None):
    before = carry['before']
    case = carry['case']
    fixture = Path(carry['fixture'])
    if items is None:
        items = targets(os.getpid(), carry['foreign'])
        items['protected_canary'] = (str(fixture / 'private/canary.txt'), os.O_RDONLY)
    denials = expected_denials(items, carry['baseline'])
    checks = {'kernel_enforced': carry['receipt']['state'] == 'enforced',
              'abi_at_least_3': carry['receipt']['landlockAbi'] >= 3,
              'source_unchanged': hashes() == carry['source'],
              'pid_preserved': os.getpid() == before['pid'],
              'all_previously_accessible_targets_now_denied': all(x['pass'] for x in denials.values()),
              'no_new_privs': guard.kernel().prctl(39, 0, 0, 0, 0) == 1,
              'mountinfo_readable': bool(Path('/proc/self/mountinfo').read_bytes())}
    after = None
    observer_error = None
    try:
        after = observer.observation()
    except PermissionError as exc:
        observer_error = {'type': type(exc).__name__, 'errno': exc.errno, 'path': exc.filename}
    if case == 'default':
        checks['original_observer_denied_at_uid_map'] = (observer_error is not None and
            observer_error['errno'] in DENIED and observer_error['path'] == '/proc/self/uid_map')
        checks['default_receipt_unchanged'] = (carry['receipt']['metadataReadFileCount'] == 6 and
                                              'selfIdentityMetadata' not in carry['receipt'])
    else:
        expected = dict(before, nnp=1)
        # Wire JSON turns tuples into lists; compare canonical JSON, never relax field sets.
        checks['original_observer_exact_identity'] = json.dumps(after, sort_keys=True) == json.dumps(expected, sort_keys=True)
        checks['two_selected_maps_readable'] = (after is not None and all(
            Path('/proc/' + str(os.getpid()) + '/' + name).read_text().split() == after[key]
            for name, key in (('uid_map', 'uidMap'), ('gid_map', 'gidMap'))))
        checks['selected_receipt_exact'] = (carry['receipt']['metadataReadFileCount'] == 8 and
                                           carry['receipt'].get('selfIdentityMetadata') is True)
    descendant_result = None
    if case == 'descendant':
        proc = subprocess.run([PYTHON, '-I', '-B', str(ROOT / ENTRY), '--descendant',
                               str(os.getpid()), '--canary', str(fixture / 'private/canary.txt')],
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=10,
                              cwd='/', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        descendant_result = decode(proc)
        checks['descendant_completed_and_denied_new_pid'] = (proc.returncode == 0 and
            descendant_result['result'] == 'PASS' and descendant_result['pid'] != os.getpid() and
            descendant_result['loadedSources'] == carry['source'])
    result = {'result': 'PASS' if all(checks.values()) else 'FAIL', 'case': case,
              'pid': os.getpid(), 'before': before, 'after': after,
              'observerError': observer_error, 'checks': checks, 'denials': denials,
              'guard': carry['receipt'], 'loadedSources': carry['source'],
              'descendant': descendant_result, 'fullProjectedLaunchAccepted': False}
    return emit(result)


def descendant(parent, canary):
    environment()
    guard, observer = modules()
    checks = {'fresh_pid': os.getpid() != parent,
              'inherited_no_new_privs': guard.kernel().prctl(39, 0, 0, 0, 0) == 1}
    attempts = {}
    for name, path in {'own_uid_map': '/proc/self/uid_map', 'own_gid_map': '/proc/self/gid_map',
                       'own_status': '/proc/self/status', 'protected_canary': canary}.items():
        attempts[name] = open_only(path)
        checks[name + '_denied'] = not attempts[name]['opened'] and attempts[name]['errno'] in DENIED
    checks['original_parent_maps_remain_granted'] = all(open_only('/proc/' + str(parent) + '/' + name)['opened']
                                                       for name in ('uid_map', 'gid_map'))
    try:
        observer.observation()
    except PermissionError as exc:
        checks['observer_denied_for_new_pid'] = exc.errno in DENIED and exc.filename == '/proc/self/status'
    else:
        checks['observer_denied_for_new_pid'] = False
    return emit({'result': 'PASS' if all(checks.values()) else 'FAIL', 'pid': os.getpid(),
                 'parentPid': parent, 'checks': checks, 'attempts': attempts, 'loadedSources': hashes()})


def decode(proc):
    text = proc.stdout.decode('utf-8', 'strict')
    lines = text.splitlines()
    assert len(lines) == 1 and lines[0].startswith(PREFIX), 'unexpected_child_output'
    assert proc.stderr == b'', 'unexpected_child_stderr'
    result = json.loads(lines[0][len(PREFIX):])
    assert type(result) is dict and result.get('result') in ('PASS', 'FAIL')
    return result


def group_absent(pgid, seconds=2):
    """Query only the process group created by this transport, never other PIDs."""
    end = time.monotonic() + seconds
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        if time.monotonic() >= end:
            return False
        time.sleep(0.02)


def owned_run(command):
    """Own one fresh session/group; confirm it is empty before deleting its files."""
    proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd='/', start_new_session=True,
                            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    timed_out = False
    signal_sent = False
    complete_output = True
    try:
        stdout, stderr = proc.communicate(timeout=100)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
    clean_normal_exit = not timed_out and proc.returncode == 0
    absent_before_signal = group_absent(proc.pid, seconds=0)
    if not absent_before_signal:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            signal_sent = True
        except ProcessLookupError:
            pass
        except PermissionError:
            complete_output = False
    if timed_out:
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = exc.stdout or b'', exc.stderr or b''
            complete_output = False
    absent = group_absent(proc.pid)
    state = {'processGroup': proc.pid, 'timedOut': timed_out,
             'signalSent': signal_sent, 'groupEmptyBeforeSignal': absent_before_signal,
             'ownedProcessGroupEmpty': absent, 'completeOutput': complete_output,
             'normalExitWithoutStragglers': clean_normal_exit and absent_before_signal}
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr), state


def run():
    environment()
    results = []
    initial = hashes()
    for case in ('default', 'selected', 'same-pid-exec', 'descendant'):
        fixture = ROOT / 'fixtures' / case
        fixture.mkdir(parents=True, mode=0o700)
        (fixture / 'rw').mkdir(mode=0o700)
        (fixture / 'private').mkdir(mode=0o700)
        canary = fixture / 'private/canary.txt'
        canary.write_bytes(b'R151 synthetic canary; no user data\n')
        canary.chmod(0o600)
        before = hashlib.sha256(canary.read_bytes()).hexdigest()
        proc = subprocess.run([PYTHON, '-I', '-B', str(ROOT / ENTRY), '--child', case,
                               '--fixture', str(fixture), '--foreign', str(os.getpid())],
                              stdin=subprocess.DEVNULL, capture_output=True, timeout=20,
                              cwd='/', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        try:
            value = decode(proc)
        except (AssertionError, ValueError, UnicodeError) as exc:
            value = {'result': 'FAIL', 'case': case, 'transportError': type(exc).__name__,
                     'stdout': proc.stdout.decode('utf-8', 'replace')[-8000:],
                     'stderr': proc.stderr.decode('utf-8', 'replace')[-8000:]}
        results.append({'case': case, 'exitCode': proc.returncode, 'evidence': value,
                        'canaryUnchanged': hashlib.sha256(canary.read_bytes()).hexdigest() == before})
    passed = all(r['exitCode'] == 0 and r['evidence']['result'] == 'PASS' and r['canaryUnchanged']
                 and r['evidence'].get('loadedSources') == initial for r in results)
    return emit({'result': 'PASS' if passed and hashes() == initial else 'FAIL',
                 'cases': results, 'sourceHashes': initial, 'sourceUnchanged': hashes() == initial,
                 'realKernel': True, 'ordinaryUid': os.getuid(), 'rootUsed': False,
                 'caseCount': 4, 'productFunctionsPatched': False,
                 'scope': 'actual Landlock map grants, original identity observer, QA exec and descendant',
                 'productProjectedExecAccepted': False, 'nativeStartupAccepted': False,
                 'networkIsolationAccepted': False, 'fullD3BAccepted': False})


def transport(digest):
    environment()
    assert os.environ.get('WSL_DISTRO_NAME') == 'AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip() == 'AlazHarness-D3B-P71C'
    raw = sys.stdin.buffer.read(1024 * 1024 + 1)
    assert 0 < len(raw) <= 1024 * 1024 and hashlib.sha256(raw).hexdigest() == digest
    root = Path(tempfile.mkdtemp(prefix='alaz-r151a1-'))
    root.chmod(0o700)
    custody = (root.stat().st_dev, root.stat().st_ino, root.stat().st_uid)
    assert custody[2] == os.getuid()
    cleanup_safe = True
    result = None
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert set(archive.namelist()) == set(FILES) | {'manifest.json'}
            assert len(archive.namelist()) == len(FILES) + 1
            assert archive.getinfo('manifest.json').file_size < 16384
            manifest = json.loads(archive.read('manifest.json'))
            assert set(manifest) == {'files'} and set(manifest['files']) == set(FILES)
            for name in FILES:
                path = PurePosixPath(name)
                assert not path.is_absolute() and '..' not in path.parts and str(path) == name
                assert archive.getinfo(name).file_size <= 128 * 1024
                data = archive.read(name)
                assert hashlib.sha256(data).hexdigest() == manifest['files'][name]
                destination = root / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                destination.chmod(0o600)
        cleanup_safe = False
        proc, lifetime = owned_run([PYTHON, '-I', '-B', str(root / ENTRY), '--run'])
        cleanup_safe = lifetime['ownedProcessGroupEmpty']
        try:
            result = decode(proc)
        except (AssertionError, ValueError, UnicodeError) as exc:
            result = {'result': 'FAIL', 'transportError': type(exc).__name__,
                      'runnerStdout': proc.stdout.decode('utf-8', 'replace')[-16000:],
                      'runnerStderr': proc.stderr.decode('utf-8', 'replace')[-16000:],
                      'sourceHashes': manifest['files']}
        unchanged = all(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
                        for name, digest in manifest['files'].items())
        assert result.get('sourceHashes') == manifest['files']
        result['lifetime'] = lifetime
        result['transportSourceUnchanged'] = unchanged
        result['transportExitCode'] = proc.returncode
        if not unchanged or not lifetime['normalExitWithoutStragglers'] or not lifetime['completeOutput']:
            result['result'] = 'FAIL'
        if not cleanup_safe:
            result['state'] = 'UNKNOWN_CHILD_LIFETIME'
            result['ownedTemporaryTreeRetained'] = str(root)
    finally:
        # Only this freshly-created, inode-checked, ordinary-user temporary tree.
        assert not root.is_symlink() and (root.stat().st_dev, root.stat().st_ino, root.stat().st_uid) == custody
        if cleanup_safe:
            shutil.rmtree(root)
    result['ownedTemporaryTreeRemoved'] = not root.exists()
    return emit(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--transport')
    modes.add_argument('--run', action='store_true')
    modes.add_argument('--child', choices=('default', 'selected', 'same-pid-exec', 'descendant'))
    modes.add_argument('--after-exec')
    modes.add_argument('--descendant', type=int)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--foreign', type=int)
    parser.add_argument('--canary')
    args = parser.parse_args()
    if args.transport:
        return transport(args.transport)
    if args.run:
        return run()
    if args.child:
        assert args.fixture.is_dir() and args.foreign > 0
        return child(args.fixture, args.child, args.foreign)
    if args.after_exec:
        environment()
        guard, observer = modules()
        carry = json.loads(args.after_exec)
        assert carry['case'] == 'same-pid-exec'
        return inspect(carry, guard, observer)
    return descendant(args.descendant, args.canary)


if __name__ == '__main__':
    raise SystemExit(main())
