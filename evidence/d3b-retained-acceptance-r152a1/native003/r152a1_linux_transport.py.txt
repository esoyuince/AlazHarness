"""Bounded ordinary-user transport for two current Landlock/native component cases.

No installation, root, namespace/mount/service or real provider action. The model
computation remains the existing explicit finite fixture. Own each fresh process
group through terminal observation before considering its temporary tree removable.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile

PYTHON = '/usr/bin/python3.12'
DRIVER = 'harness/scripts/qa/r152a1_landlock_native.py'
DEPS = Path('/opt/alaz-f126c1a6/dependencies')
FEATURE = 'd1516731308de8e87130dc68124e69aad35d6911'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def group_absent(pgid, seconds=2):
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


def owned_run(command, environment, cwd):
    proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=cwd, env=environment,
                            start_new_session=True)
    timed_out = signal_sent = False
    complete_output = True
    try:
        stdout, stderr = proc.communicate(timeout=210)
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
    lifetime = {'processGroup': proc.pid, 'timedOut': timed_out, 'signalSent': signal_sent,
                'groupEmptyBeforeSignal': absent_before_signal, 'ownedProcessGroupEmpty': absent,
                'completeOutput': complete_output,
                'normalExitWithoutStragglers': clean_normal_exit and absent_before_signal}
    return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr), lifetime


def unpack(raw, sha256):
    assert 0 < len(raw) <= 35_000_000 and digest(raw) == sha256
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)) < 1300
        assert archive.getinfo('manifest.json').file_size < 256_000
        manifest = json.loads(archive.read('manifest.json'))
        assert set(manifest) == {'files', 'nativeFeature', 'harnessBase'}
        assert manifest['nativeFeature'] == FEATURE
        assert set(names) == set(manifest['files']) | {'manifest.json'}
        assert sum(info.file_size for info in archive.infolist()) < 70_000_000
        assert DRIVER in manifest['files'] and 'accepted-dependencies.json' in manifest['files']
        for name, expected in manifest['files'].items():
            path = PurePosixPath(name)
            assert str(path) == name and not path.is_absolute() and '..' not in path.parts
            assert '\\' not in name and ':' not in name
            assert name.startswith(('harness/', 'native/')) or name == 'accepted-dependencies.json'
            info = archive.getinfo(name)
            assert not stat.S_ISLNK(info.external_attr >> 16) and info.file_size <= 2_000_000
            data = archive.read(name)
            assert digest(data) == expected
            files[name] = data
    envelope = json.loads(files['harness/config/retained-profile-r140c6-sources.json'])
    assert envelope['nativeFeature'] == FEATURE
    assert {name.removeprefix('native/'): digest(data) for name, data in files.items()
            if name.startswith('native/')} == envelope['sources']
    return manifest, files


def dependencies(expected):
    assert len(expected) == 1162 and DEPS.is_dir() and not DEPS.is_symlink()
    actual = {}
    for path in DEPS.rglob('*'):
        assert not path.is_symlink()
        if path.is_file():
            actual[path.relative_to(DEPS).as_posix()] = digest(path.read_bytes())
    assert actual == expected, 'installed_dependency_bytes_changed'
    return len(actual)


def run_case(name, files, manifest):
    root = Path(tempfile.mkdtemp(prefix='alaz-r152a1-' + name + '-'))
    root.chmod(0o700)
    custody = (root.stat().st_dev, root.stat().st_ino, root.stat().st_uid)
    assert custody[2] == os.getuid()
    for item, data in files.items():
        path = root / item
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o600)
    for directory in ('tmp', 'envhome'):
        (root / directory).mkdir(mode=0o700)
    canary = root / 'kernel-denied.txt'
    canary.write_bytes(b'R152 synthetic file canary; no user secrets\n')
    canary.chmod(0o600)
    canary_before = digest(canary.read_bytes())
    environment = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': str(root / 'envhome'),
                   'HERMES_HOME': str(root / 'envhome'), 'TMPDIR': str(root / 'tmp'),
                   'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'), 'PYTHONUTF8': '1',
                   'TZ': 'UTC', 'WSL_DISTRO_NAME': 'AlazHarness-D3B-P71C'}
    entry = "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')"
    command = [PYTHON, '-I', '-B', '-c', entry, str(DEPS), str(root / DRIVER),
               '--native', str(root / 'native'), '--output', str(root / 'result')]
    if name == 'controlled-error':
        command.append('--compute-failure')
    proc, lifetime = owned_run(command, environment, root / 'envhome')
    artifacts = {}
    inspection_error = None
    result = None
    unchanged = canary_unchanged = False
    audit_events_accounted = False
    blocked_import_probes = []
    # Do not inspect mutable results or delete the tree while any owned child remains.
    try:
        if lifetime['ownedProcessGroupEmpty']:
            output = root / 'result'
            if output.is_dir():
                for path in output.rglob('*'):
                    assert not path.is_symlink()
                    if path.is_file():
                        assert path.stat().st_size < 2_000_000
                        artifacts[path.relative_to(output).as_posix()] = path.read_text(encoding='utf-8')
            result = json.loads(artifacts['result.json']) if 'result.json' in artifacts else None
            unchanged = all(digest((root / item).read_bytes()) == value for item, value in manifest['files'].items())
            canary_unchanged = digest(canary.read_bytes()) == canary_before
            if result is not None:
                assert result['nativeImports'] and all(manifest['files'].get('native/' + name) == value
                                                      for name, value in result['nativeImports'].items())
                if result.get('preExec') is not None:
                    assert result['preExec']['nativeImports'] and all(manifest['files'].get('native/' + name) == value
                            for name, value in result['preExec']['nativeImports'].items())
                expected_probe = json.loads(files['accepted-dependencies.json'])['urllib3/util/connection.py']
                roles = [('after_exec', result.get('deniedEvents'))]
                if result.get('preExec') is not None:
                    roles.append(('before_bootstrap', result['preExec'].get('deniedEvents')))
                for role, denied in roles:
                    assert type(denied) is list and len(denied) <= 1
                    for event in denied:
                        origin = event.get('origin', {})
                        assert event['event'] == 'socket.bind' and event['phase'] in ('PREPARE_FINITE', 'RESTART_AFTER_NORMAL_CLOSE')
                        assert origin == {'function': '_has_ipv6', 'file': str(DEPS / 'urllib3/util/connection.py'),
                                          'sha256': expected_probe}
                        blocked_import_probes.append({'role': role, **event})
                audit_events_accounted = True
    except Exception as exc:
        inspection_error = type(exc).__name__
    passed = (proc.returncode == 0 and lifetime['normalExitWithoutStragglers'] and
              lifetime['completeOutput'] and unchanged and canary_unchanged and inspection_error is None and result is not None and
              result.get('result') == 'PASS_REAL_LANDLOCK_RETAINED_NATIVE_LIFECYCLE' and
              result.get('landlockAfterExec') is not None and result.get('temporaryProfileRemoved') is False and
              result.get('profileCleanupDeferredToTransport') is True and
              result.get('computeFailure') is (name == 'controlled-error') and
              result.get('restartReport', {}).get('newPersistedResultMatchesApi') is True and
              result.get('failureFixtureCleanupUsed') is False and audit_events_accounted)
    assert not root.is_symlink() and (root.stat().st_dev, root.stat().st_ino, root.stat().st_uid) == custody
    report = {'case': name, 'result': 'PASS' if passed else 'FAIL', 'exitCode': proc.returncode,
              'stdout': proc.stdout.decode('utf-8', 'replace'), 'stderr': proc.stderr.decode('utf-8', 'replace'),
              'artifacts': artifacts, 'lifetime': lifetime, 'sourcesUnchanged': unchanged,
              'canaryUnchanged': canary_unchanged, 'temporaryTreeRemoved': not root.exists(),
              'inspectionError': inspection_error, 'blockedOptionalImportProbes': blocked_import_probes,
              'allNetworkAuditDenialsAccounted': audit_events_accounted,
              'landlockComponentTested': result is not None and result.get('landlockFilesystemComponentTested') is True,
              'temporaryTreeIdentity': list(custody)}
    if root.exists():
        report['retainedTemporaryTree'] = str(root)
    if not lifetime['ownedProcessGroupEmpty']:
        report['state'] = 'UNKNOWN_CHILD_LIFETIME'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    assert sys.platform == 'linux' and sys.executable == PYTHON
    assert sys.flags.isolated and sys.dont_write_bytecode and not sys.flags.optimize
    assert os.getresuid() == (23001,) * 3 and os.getresgid() == (23003,) * 3
    assert os.environ.get('WSL_DISTRO_NAME') == 'AlazHarness-D3B-P71C'
    assert Path('/etc/alaz-p71c-lab-id').read_text().strip() == 'AlazHarness-D3B-P71C'
    assert not Path('/mnt/c/Windows').exists()
    os.umask(0o077)
    manifest, files = unpack(sys.stdin.buffer.read(35_000_001), args.sha256)
    expected = json.loads(files['accepted-dependencies.json'])
    dependencies(expected)
    cases = []
    for case in ('normal', 'controlled-error'):
        result = run_case(case, files, manifest)
        cases.append(result)
        if result['result'] != 'PASS':
            break
    dependency_error = None
    try:
        dependencies(expected)
    except Exception as exc:
        dependency_error = type(exc).__name__
    passed = len(cases) == 2 and all(case['result'] == 'PASS' for case in cases) and dependency_error is None
    # Failed or uncertain experiments keep every tree. Cleanup is owned here,
    # after both groups are empty and all case/dependency acceptance checks pass.
    cleanup_error = None
    if passed:
        try:
            for case in cases:
                root = Path(case['retainedTemporaryTree'])
                assert case['lifetime']['ownedProcessGroupEmpty']
                assert not root.is_symlink() and list((root.stat().st_dev, root.stat().st_ino, root.stat().st_uid)) == case['temporaryTreeIdentity']
            for case in cases:
                root = Path(case['retainedTemporaryTree'])
                shutil.rmtree(root)
                case['temporaryTreeRemoved'] = not root.exists()
                assert case['temporaryTreeRemoved']
                case.pop('retainedTemporaryTree')
        except Exception as exc:
            cleanup_error = type(exc).__name__
            passed = False
    outcome = {'state': 'COMPLETED' if all(c.get('state') != 'UNKNOWN_CHILD_LIFETIME' for c in cases) else 'UNKNOWN_CHILD_LIFETIME',
               'result': 'PASS' if passed else 'FAIL', 'cases': cases, 'bundleSha256': args.sha256,
               'sourceHashes': manifest['files'], 'dependencyFiles': len(expected),
               'dependencyHashesUnchanged': dependency_error is None, 'dependencyVerificationError': dependency_error,
               'cleanupError': cleanup_error,
               'rootUsed': False, 'productFunctionsPatched': False,
               'modelComputationFixture': True, 'landlockComponentTested': any(case['landlockComponentTested'] for case in cases),
               'fullProjectionAccepted': False, 'actualProjectedEntrypointUsed': False,
               'networkIsolationAccepted': False, 'fullD3BAccepted': False}
    print('R152_RESULT ' + json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
