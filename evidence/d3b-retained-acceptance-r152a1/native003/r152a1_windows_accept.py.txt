"""Freeze and execute one bounded R152 ordinary-user component bundle.

No root/installation/supervisor action. Immutable Git blobs supply native sources;
all harness/product bytes must still equal the accepted base. Only these four QA
files are new. An exclusive execution record prevents replay after interruption.
"""
from pathlib import Path
import argparse
import ast
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = '8aae47fb7efa94fbfb45b22018747d4bb3178c2a'
FEATURE = 'd1516731308de8e87130dc68124e69aad35d6911'
NATIVE = Path(r'C:\Antigravity\AlazHarness\scratch\worktrees\hermes-finite-close-f135c6')
EVIDENCE = ROOT / 'evidence/d3b-retained-acceptance-r152a1'
QA = ('scripts/qa/r152a1_landlock_native.py', 'scripts/qa/r152a1_linux_transport.py',
      'scripts/qa/r152a1_windows_accept.py', 'scripts/qa/r152a1_landlock_bootstrap.py')
CONFIGS = ('config/prepared-consumer-s124b1-sources.json',
           'config/admission-consumer-b129d6-sources.json',
           'config/canonical-api-consumer-i133p1-sources.json',
           'config/finite-close-f135c6-sources.json',
           'config/retained-profile-r140c6-sources.json')
HELPERS = ('scripts/run_store_preopen.py', 'scripts/run_response_preopen.py')
DEPENDENCY_RECORD = 'evidence/d3b-confined-consumer-f126c1/native-006-result.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def git(repo, *args, data=None):
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args],
                            input=data, capture_output=True, timeout=60)
    assert result.returncode == 0, 'source_git_failed'
    return result.stdout


def tree(repo, revision):
    rows = git(repo, 'ls-tree', '-r', '-z', revision).split(b'\0')
    result = {}
    for row in rows:
        if row:
            metadata, path = row.split(b'\t', 1)
            result[path.decode('utf-8')] = metadata.decode('ascii').split()
    return result


def blobs(repo, revision, names, inventory):
    for name in names:
        assert '\n' not in name and '\r' not in name and inventory[name][0] in ('100644', '100755')
        assert inventory[name][1] == 'blob'
    request = ''.join(revision + ':' + name + '\n' for name in names).encode('utf-8')
    raw = git(repo, 'cat-file', '--batch', data=request)
    cursor = 0
    files = {}
    for name in names:
        end = raw.index(b'\n', cursor)
        oid, kind, length = raw[cursor:end].decode('ascii').split()
        length = int(length)
        assert kind == 'blob' and oid == inventory[name][2] and 0 <= length <= 2_000_000
        cursor = end + 1
        files[name] = raw[cursor:cursor + length]
        cursor += length
        assert raw[cursor:cursor + 1] == b'\n'
        cursor += 1
    assert cursor == len(raw)
    return files


def source():
    assert git(ROOT, 'rev-parse', '--verify', BASE + '^{commit}').decode().strip() == BASE
    current_tree = tree(ROOT, BASE)
    names = sorted({name for name in current_tree if name.startswith('packages/claw-hermes/') and name.endswith('.py')}
                   | set(CONFIGS) | set(HELPERS))
    accepted = blobs(ROOT, BASE, names + [DEPENDENCY_RECORD], current_tree)
    dependency_record = json.loads(accepted.pop(DEPENDENCY_RECORD))
    dependencies = {name.removeprefix('dependencies/'): value for name, value in dependency_record['sources'].items()
                    if name.startswith('dependencies/')}
    assert len(dependencies) == 1162
    # Product source custody is separate from new QA source custody.
    captured = {name: (ROOT / name).read_bytes() for name in names + list(QA)}
    assert all(captured[name] == value for name, value in accepted.items()), 'accepted_product_bytes_changed'
    native_expected = json.loads(captured[CONFIGS[-1]])
    assert native_expected['nativeFeature'] == FEATURE and len(native_expected['sources']) == 756
    assert git(NATIVE, 'rev-parse', 'HEAD').decode().strip() == FEATURE
    assert not git(NATIVE, 'status', '--porcelain').strip(), 'native_worktree_not_clean'
    native = blobs(NATIVE, FEATURE, sorted(native_expected['sources']), tree(NATIVE, FEATURE))
    assert {name: sha(value) for name, value in native.items()} == native_expected['sources']
    files = {'harness/' + name: value for name, value in captured.items()}
    files.update({'native/' + name: value for name, value in native.items()})
    files['accepted-dependencies.json'] = (json.dumps(dependencies, sort_keys=True) + '\n').encode('utf-8')
    assert sum(map(len, files.values())) < 70_000_000
    return dict(sorted(files.items()))


def prepare(attempt):
    assert not attempt.exists(), 'attempt_already_exists'
    files = source()
    for name, data in files.items():
        if name.endswith('.py'):
            ast.parse(data, filename=name)
    manifest = {'files': {name: sha(data) for name, data in files.items()},
                'nativeFeature': FEATURE, 'harnessBase': BASE}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('manifest.json', json.dumps(manifest, sort_keys=True))
    raw = stream.getvalue()
    assert len(raw) < 35_000_000
    attempt.mkdir(parents=True)
    with (attempt / 'bundle.zip').open('xb') as handle:
        handle.write(raw)
    write(attempt / 'manifest.json', manifest)
    for name in QA:
        with (attempt / (Path(name).name + '.txt')).open('xb') as handle:
            handle.write(files['harness/' + name])
    intent = {'at': now(), 'state': 'PREPARED_NOT_RUN', 'harnessBase': BASE, 'nativeFeature': FEATURE,
              'bundleSha256': sha(raw), 'bundleBytes': len(raw), 'sourceFileCount': len(files),
              'manifestSha256': sha((attempt / 'manifest.json').read_bytes()),
              'distribution': 'AlazHarness-D3B-P71C', 'user': 'alazgateway', 'uid': 23001, 'gid': 23003,
              'scenarios': ['normal', 'controlled-error'], 'rootRequested': False,
              'scope': 'actual Landlock before QA exec; original native retained finite lifecycle; no projected launcher acceptance',
              'outerTimeoutSeconds': 480, 'eachOwnedGroupTimeoutSeconds': 210}
    write(attempt / 'intent.json', intent)
    print(json.dumps({k: intent[k] for k in ('state', 'bundleSha256', 'bundleBytes', 'sourceFileCount')}))


def execute(attempt):
    assert sys.platform == 'win32'
    intent = json.loads((attempt / 'intent.json').read_text(encoding='utf-8'))
    raw = (attempt / 'bundle.zip').read_bytes()
    manifest_bytes = (attempt / 'manifest.json').read_bytes()
    assert sha(raw) == intent['bundleSha256'] and sha(manifest_bytes) == intent['manifestSha256']
    manifest = json.loads(manifest_bytes)
    captured = source()
    current = {name: sha(data) for name, data in captured.items()}
    assert current == manifest['files'], 'candidate_changed_after_prepare'
    # Execute the exact captured-and-hashed transport bytes, without another read.
    transport = captured['harness/' + QA[1]].decode('utf-8')
    command = ['wsl.exe', '--distribution', 'AlazHarness-D3B-P71C', '--user', 'alazgateway', '--cd', '/',
               '--exec', '/usr/bin/python3.12', '-I', '-B', '-c', transport, '--sha256', intent['bundleSha256']]
    write(attempt / 'execution-start.json', {'at': now(), 'state': 'IN_PROGRESS',
          'bundleSha256': intent['bundleSha256'], 'transportSha256': current['harness/' + QA[1]],
          'ordinaryUserOnly': True, 'outerTimeoutSeconds': 480})
    try:
        proc = subprocess.run(command, cwd=ROOT, input=raw, capture_output=True, timeout=480)
    except subprocess.TimeoutExpired as exc:
        (attempt / 'stdout.txt').write_bytes(exc.stdout or b'')
        (attempt / 'stderr.txt').write_bytes(exc.stderr or b'')
        write(attempt / 'terminal.json', {'at': now(), 'state': 'UNKNOWN_TIMEOUT',
              'ownedLinuxChildrenTerminationConfirmed': False, 'replayForbidden': True})
        return 2
    (attempt / 'stdout.txt').write_bytes(proc.stdout)
    (attempt / 'stderr.txt').write_bytes(proc.stderr)
    outcome = parse_error = None
    try:
        lines = proc.stdout.decode('utf-8', 'strict').splitlines()
        assert len(lines) == 1 and lines[0].startswith('R152_RESULT ')
        candidate = json.loads(lines[0].removeprefix('R152_RESULT '))
        assert type(candidate) is dict and type(candidate.get('cases')) is list
        assert 1 <= len(candidate['cases']) <= 2
        for index, case in enumerate(candidate['cases']):
            assert type(case) is dict and case.get('case') == ('normal', 'controlled-error')[index]
            assert type(case.get('lifetime')) is dict and type(case.get('artifacts')) is dict
            assert case.get('result') in ('PASS', 'FAIL') and type(case.get('temporaryTreeRemoved')) is bool
            assert 'exitCode' in case and (case['exitCode'] is None or type(case['exitCode']) is int)
            assert all(type(case['lifetime'].get(key)) is bool for key in
                       ('ownedProcessGroupEmpty', 'normalExitWithoutStragglers', 'completeOutput'))
            assert all(type(name) is str and type(content) is str for name, content in case['artifacts'].items())
        outcome = candidate
        write(attempt / 'result.json', outcome)
        for case in outcome['cases']:
            assert case['case'] in ('normal', 'controlled-error')
            for name, content in case['artifacts'].items():
                assert name in ('pre-exec.json', 'kernel-proof.json', 'result.json')
                with (attempt / (case['case'] + '-' + name)).open('x', encoding='utf-8', newline='\n') as handle:
                    handle.write(content)
    except (AssertionError, ValueError, UnicodeError, KeyError, TypeError, AttributeError) as exc:
        parse_error = type(exc).__name__
        outcome = None
    after = None
    custody_error = None
    try:
        after = {name: sha(data) for name, data in source().items()}
    except Exception as exc:
        custody_error = type(exc).__name__
    passed = (proc.returncode == 0 and proc.stderr == b'' and outcome is not None and parse_error is None and
              outcome.get('result') == 'PASS' and outcome.get('sourceHashes') == current and after == current and
              outcome.get('dependencyHashesUnchanged') is True and
              [case['case'] for case in outcome.get('cases', [])] == ['normal', 'controlled-error'] and
              all(case['result'] == 'PASS' and case['temporaryTreeRemoved'] is True and
                  case['lifetime']['normalExitWithoutStragglers'] is True for case in outcome.get('cases', [])))
    children_confirmed = (outcome is not None and bool(outcome.get('cases')) and
                          all(case.get('lifetime', {}).get('ownedProcessGroupEmpty') is True
                              for case in outcome['cases']))
    terminal_state = ('UNKNOWN_RESULT' if outcome is None or parse_error is not None else
                      'UNKNOWN_CHILD_LIFETIME' if not children_confirmed else
                      'COMPLETED_WITH_SOURCE_CUSTODY_FAILURE' if custody_error is not None else
                      outcome.get('state', 'COMPLETED'))
    terminal = {'at': now(), 'state': terminal_state,
                'result': 'PASS' if passed else 'FAIL', 'exitCode': proc.returncode,
                'parseError': parse_error, 'bundleSha256': intent['bundleSha256'],
                'sourceCustodyError': custody_error, 'ownedLinuxChildrenTerminationConfirmed': children_confirmed,
                'replayForbidden': True,
                'sourceUnchanged': after == current, 'stdoutSha256': sha(proc.stdout), 'stderrSha256': sha(proc.stderr)}
    write(attempt / 'terminal.json', terminal)
    print(json.dumps({**terminal, 'cases': [{'case': case['case'], 'result': case['result'], 'exitCode': case['exitCode']}
                                          for case in (outcome or {}).get('cases', [])]}))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch('[a-z][a-z0-9_-]{0,24}', args.attempt)
    attempt = EVIDENCE / args.attempt
    if args.prepare:
        prepare(attempt)
        return 0
    return execute(attempt)


if __name__ == '__main__':
    raise SystemExit(main())
