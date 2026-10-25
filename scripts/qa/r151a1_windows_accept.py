"""Prepare/run one immutable R151A1 bundle as the existing ordinary lab user.

Each attempt has an exclusive execution record. Pending/unknown attempts cannot
be replayed. Only the dedicated lab is used; no root or service operations.
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
ENTRY = 'scripts/qa/r151a1_self_identity_kernel.py'
NAMES = tuple('packages/claw-hermes/' + name + '.py' for name in (
    'credential_guard', 'principal_launch', 'host_principal', 'combined_guard', 'linux_netns')) + (ENTRY,)
BASE = ROOT / 'evidence/d3b-self-identity-kernel-r151a1'


def now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def source():
    return {name: (ROOT / name).read_bytes() for name in NAMES}


def prepare(attempt):
    assert not attempt.exists(), 'attempt_already_exists'
    files = source()
    for name, data in files.items():
        ast.parse(data, filename=name)
    manifest = {'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
        bundle.writestr('manifest.json', json.dumps(manifest, sort_keys=True))
    raw = stream.getvalue()
    attempt.mkdir(parents=True)
    (attempt / 'bundle.zip').write_bytes(raw)
    write(attempt / 'intent.json', {'at': now(), 'state': 'PREPARED_NOT_RUN',
          'bundleSha256': hashlib.sha256(raw).hexdigest(), 'bundleBytes': len(raw),
          'sourceHashes': manifest['files'], 'distribution': 'AlazHarness-D3B-P71C',
          'user': 'alazgateway', 'uid': 23001, 'gid': 23003, 'rootRequested': False,
          'scope': 'four actual-kernel self-map component cases; no product startup acceptance'})
    print(json.dumps({'state': 'PREPARED_NOT_RUN', 'attempt': attempt.name,
                      'bundleSha256': hashlib.sha256(raw).hexdigest(), 'bundleBytes': len(raw)}))


def execute(attempt):
    assert sys.platform == 'win32'
    intent = json.loads((attempt / 'intent.json').read_text(encoding='utf-8'))
    raw = (attempt / 'bundle.zip').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == intent['bundleSha256']
    captured = source()
    current = {name: hashlib.sha256(data).hexdigest() for name, data in captured.items()}
    assert current == intent['sourceHashes'], 'candidate_changed_after_prepare'
    transport = captured[ENTRY].decode('utf-8')
    command = ['wsl.exe', '--distribution', 'AlazHarness-D3B-P71C', '--user', 'alazgateway',
               '--cd', '/', '--exec', '/usr/bin/python3.12', '-I', '-B', '-c', transport,
               '--transport', intent['bundleSha256']]
    # Exclusive start record prevents silent replay after a delivery interruption.
    write(attempt / 'execution-start.json', {'at': now(), 'state': 'IN_PROGRESS',
          'bundleSha256': intent['bundleSha256'], 'sourceHashes': current,
          'transportSource': ENTRY, 'ordinaryUserOnly': True})
    try:
        proc = subprocess.run(command, cwd=ROOT, input=raw, capture_output=True, timeout=130)
    except subprocess.TimeoutExpired as exc:
        (attempt / 'stdout.txt').write_bytes(exc.stdout or b'')
        (attempt / 'stderr.txt').write_bytes(exc.stderr or b'')
        write(attempt / 'terminal.json', {'at': now(), 'state': 'UNKNOWN_TIMEOUT',
              'ownedLinuxChildrenTerminationConfirmed': False, 'replayForbidden': True})
        raise SystemExit(2)
    (attempt / 'stdout.txt').write_bytes(proc.stdout)
    (attempt / 'stderr.txt').write_bytes(proc.stderr)
    outcome = None
    parse_error = None
    try:
        lines = proc.stdout.decode('utf-8', 'strict').splitlines()
        assert len(lines) == 1 and lines[0].startswith('R151_RESULT ')
        outcome = json.loads(lines[0].removeprefix('R151_RESULT '))
        write(attempt / 'result.json', outcome)
    except (AssertionError, ValueError, UnicodeError) as exc:
        parse_error = type(exc).__name__
    after = {name: hashlib.sha256(data).hexdigest() for name, data in source().items()}
    passed = (proc.returncode == 0 and proc.stderr == b'' and outcome is not None and
              outcome.get('result') == 'PASS' and outcome.get('caseCount') == 4 and
              outcome.get('sourceHashes') == current and after == current and
              outcome.get('ownedTemporaryTreeRemoved') is True and
              outcome.get('transportSourceUnchanged') is True and
              outcome.get('lifetime', {}).get('ownedProcessGroupEmpty') is True)
    terminal = {'at': now(), 'state': (outcome or {}).get('state', 'COMPLETED'), 'result': 'PASS' if passed else 'FAIL',
                'exitCode': proc.returncode, 'parseError': parse_error,
                'bundleSha256': intent['bundleSha256'], 'sourceHashesBefore': current,
                'sourceHashesAfter': after, 'sourceUnchanged': after == current,
                'stdoutSha256': hashlib.sha256(proc.stdout).hexdigest(),
                'stderrSha256': hashlib.sha256(proc.stderr).hexdigest()}
    write(attempt / 'terminal.json', terminal)
    print(json.dumps({'state': terminal['state'], 'result': terminal['result'],
                      'exitCode': proc.returncode, 'attempt': attempt.name,
                      'cases': [{'case': c['case'], 'exitCode': c['exitCode'],
                                 'result': c['evidence']['result']} for c in (outcome or {}).get('cases', [])],
                      'sourceUnchanged': after == current}))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch('[a-z][a-z0-9_-]{0,24}', args.attempt)
    attempt = BASE / args.attempt
    if args.prepare:
        prepare(attempt)
        return 0
    return execute(attempt)


if __name__ == '__main__':
    raise SystemExit(main())
