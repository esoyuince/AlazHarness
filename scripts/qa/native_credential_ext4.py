"""Explicit credential-Gateway QA from byte-verified native Linux source copy.

WSL v9fs can deny Landlock-approved source opens. Copy only repository code,
never credentials, into a fresh native Linux tree; keep original guard rights.
No kernel policy change, fallback, system installation or real model call.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LINUX = Path('/home/ender/alaz-harness-d2b2-gateway-af21')
PYTHON = LINUX/'source-workspace/runtime/gateway-env-af21/env/bin/python-local'
SCENARIOS = ('normal', 'budget-limit', 'candidate-disconnect', 'review-revoked')
ROOTS = ('packages', 'scripts', 'config')
SKIP = {'.git', '__pycache__', 'node_modules', '.venv'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_files(root):
    """Bounded code-only inventory; reject aliases and changing source bytes."""
    files = [root/'sources.lock.json']
    for name in ROOTS:
        directory = root/name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError('snapshot_source_root_invalid')
        for current, dirs, names in os.walk(directory, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            for d in dirs:
                if (Path(current)/d).is_symlink():
                    raise ValueError('snapshot_source_symlink')
            for name in sorted(names):
                file = Path(current)/name
                if file.suffix not in ('.pyc', '.pyo'):
                    files.append(file)
    if len(files) > 2500:
        raise ValueError('snapshot_file_limit')
    result = {}
    total = 0
    for file in sorted(files):
        if file.is_symlink() or not file.is_file():
            raise ValueError('snapshot_regular_files_required')
        if file.stat().st_size > 4_194_304:
            raise ValueError('snapshot_file_size')
        raw = file.read_bytes()
        total += len(raw)
        if total > 67_108_864:
            raise ValueError('snapshot_size_limit')
        result[file.relative_to(root).as_posix()] = sha(raw)
    return result


def copy_verified(root, destination, expected):
    if destination.exists():
        raise ValueError('snapshot_destination_exists')
    destination.mkdir(mode=0o700)
    for relative, digest in expected.items():
        source = root/relative
        raw = source.read_bytes()
        if sha(raw) != digest:
            raise ValueError('snapshot_source_changed')
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        if sha(target.read_bytes()) != digest:
            raise ValueError('snapshot_copy_changed')
    if source_files(root) != expected or source_files(destination) != expected:
        raise ValueError('snapshot_inventory_changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--scenario', choices=SCENARIOS, default='normal')
    args = parser.parse_args()
    if sys.platform != 'linux' or not re.fullmatch('[a-z0-9-]{4,40}', args.run_id):
        raise ValueError('linux_and_unique_run_id_required')
    evidence = ROOT/'evidence/d3b-credential-fix-a613'
    report_path = evidence/('gateway-'+args.run_id+'.json')
    manifest_path = evidence/('source-'+args.run_id+'.json')
    if (not evidence.is_dir() or report_path.exists() or manifest_path.exists()
            or not PYTHON.is_file()):
        raise ValueError('fresh_evidence_and_prepared_python_required')
    expected = source_files(ROOT)
    with tempfile.TemporaryDirectory(prefix='alaz-credential-src-') as temporary:
        snapshot = Path(temporary)/'code'
        copy_verified(ROOT, snapshot, expected)
        fs = subprocess.check_output(['stat', '-f', '-c', '%T', str(snapshot)], text=True).strip()
        if fs in ('v9fs', '9p', 'drvfs'):
            raise ValueError('native_filesystem_snapshot_required')
        for folder in ('d2b2-gateway-af21', 'd3b-credential-6e42'):
            (snapshot/'evidence'/folder).mkdir(parents=True)
        env = {**os.environ, 'PATH':str(LINUX/'tools/bin')+':/usr/bin:/bin',
               'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONIOENCODING':'utf-8'}
        result = subprocess.run([str(PYTHON), '-I', '-B',
            str(snapshot/'scripts/qa/native_credential_gateway.py'),
            '--run-id', args.run_id, '--scenario', args.scenario],
            cwd=snapshot, env=env, capture_output=True, timeout=300)
        receipt_path = snapshot/'evidence/d3b-credential-6e42'/('gateway-'+args.run_id+'.json')
        receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
        source_unchanged = source_files(ROOT) == expected
        copied_unchanged = source_files(snapshot) == expected
        summary = {
            'observedAt':datetime.datetime.now().astimezone().isoformat(),
            'runId':args.run_id, 'scenario':args.scenario,
            'result':'PASS' if (result.returncode == 0 and receipt.get('result') == 'PASS'
                               and source_unchanged and copied_unchanged) else 'FAIL',
            'exitCode':result.returncode, 'snapshotFilesystem':fs,
            'sourceFiles':len(expected), 'sourceUnchanged':source_unchanged,
            'snapshotBytesMatch':copied_unchanged,
            'guardSourceSha256':expected['packages/claw-hermes/credential_guard.py'],
            'launcherSourceSha256':expected['scripts/run_credential_guard.py'],
            'sourceManifestSha256':sha(json.dumps(expected, sort_keys=True).encode()),
            'guardedGateway':receipt,
            'childStdoutSha256':sha(result.stdout), 'childStderrSha256':sha(result.stderr),
            'broadFilesystemGrantAdded':False, 'selfProcessMetadataOptin':True, 'networkBoundaryVerified':False,
            'kernelOrSystemConfigChanged':False, 'realModelInferenceVerified':False,
            'paidCalls':0, 'mainMerged':False}
    summary['temporaryCodeSnapshotRemoved'] = not snapshot.exists()
    with manifest_path.open('x', encoding='utf-8') as stream:
        json.dump({'files':expected, 'scope':'packages/scripts/config/sources.lock only'}, stream, indent=2)
        stream.write('\n')
    with report_path.open('x', encoding='utf-8') as stream:
        json.dump(summary, stream, indent=2)
        stream.write('\n')
    native = summary['guardedGateway'].get('native', {})
    print(json.dumps({'result':summary['result'], 'scenario':args.scenario,
        'snapshotFilesystem':fs, 'sourceFiles':len(expected),
        'guard':summary['guardedGateway'].get('guard'),
        'nativeGateway':native.get('nativeHermesGateway'),
        'nativeErrors':native.get('errors'), 'provenance':native.get('provenance')}))
    return 0 if summary['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
