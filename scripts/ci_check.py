#!/usr/bin/env python3
"""Offline M0 CI gate. Does not import, clone, build or execute vendor agents."""
from __future__ import annotations
import argparse
import configparser
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path, PurePosixPath

EXPECTED = {
    'openclaw': ('vendor/openclaw', 'https://github.com/esoyuince/openclaw.git', 'https://github.com/openclaw/openclaw.git'),
    'hermes-agent': ('vendor/hermes-agent', 'https://github.com/esoyuince/hermes-agent.git', 'https://github.com/NousResearch/hermes-agent.git'),
}
PUBLIC_FILES = ('LICENSE', 'README.md', 'SECURITY.md', 'CONTRIBUTING.md', 'docs/CI.md', 'docs/THIRD-PARTY.md')
PATTERNS = {
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'github-token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'model-key': re.compile(rb'\bsk-(?:proj-|ant-api\d+-)?[A-Za-z0-9_-]{32,}'),
    'aws-access-key': re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'credential-url': re.compile(rb'https?://[^\s/<>"\x27]+:[^\s/<>"\x27]+@'),
}


def credential_hits(data: bytes) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if pattern.search(data)]


def private_path(name: str) -> bool:
    p = PurePosixPath(name.lower())
    if any(x in p.parts for x in ('runtime', 'artifacts', 'scratch', '.alaz-ci', '.ssh', '.hermes', '.openclaw')):
        return True
    if p.name.startswith('.env') and not p.name.endswith('.example'):
        return True
    return p.suffix in ('.pem', '.key', '.p12', '.pfx', '.sqlite', '.db') or bool(re.search(r'(?:credentials|secrets).*\.json$', p.name))


def git(root: Path, *args: str) -> bytes:
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30, check=False)
    if r.returncode:
        raise RuntimeError('git ' + args[0] + ' failed: exit ' + str(r.returncode))
    return r.stdout


def index_entries(root: Path) -> dict[str, tuple[str, str]]:
    entries = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, raw_path = row.split(b'\t', 1)
        mode, sha, stage = meta.decode('ascii').split()
        name = raw_path.decode('utf-8')
        if stage != '0' or name in entries:
            raise ValueError('Unmerged or duplicate index entry')
        entries[name] = (mode, sha)
    if not entries:
        raise ValueError('Empty Git index')
    return entries


def validate_sources(lock: dict, modules_text: str, entries: dict) -> list[str]:
    errors = []
    modules = configparser.ConfigParser(interpolation=None, strict=True)
    modules.read_string(modules_text)
    sources = lock.get('repositories', [])
    if lock.get('schema_version') != 1 or lock.get('project') != 'AlazHarness':
        errors.append('source schema/project')
    if len(sources) != 2 or {s.get('name') for s in sources} != set(EXPECTED):
        errors.append('exact source set')
    expected_sections = {f'submodule "{n}"' for n in EXPECTED}
    if set(modules.sections()) != expected_sections or modules.defaults():
        errors.append('exact submodule sections')
    links = {p: sha for p, (mode, sha) in entries.items() if mode == '160000'}
    if set(links) != {x[0] for x in EXPECTED.values()}:
        errors.append('exact gitlink paths')
    for source in sources:
        name = source.get('name')
        if name not in EXPECTED:
            continue
        path, origin, upstream = EXPECTED[name]
        sha = source.get('commit', '')
        if not re.fullmatch(r'[0-9a-f]{40}', sha) or set(sha) == {'0'}:
            errors.append(name + ': immutable commit')
        if (source.get('path'), source.get('origin'), source.get('upstream')) != (path, origin, upstream):
            errors.append(name + ': source identity')
        if links.get(path) != sha:
            errors.append(name + ': gitlink mismatch')
        section = f'submodule "{name}"'
        if not modules.has_section(section) or dict(modules[section]) != {'path': path, 'url': origin}:
            errors.append(name + ': submodule configuration')
        hashes = source.get('file_sha256', {})
        if 'LICENSE' not in hashes or any(not re.fullmatch(r'[0-9a-f]{64}', h) for h in hashes.values()):
            errors.append(name + ': source file digest')
    return errors


def require_nonzero_tests(count: int) -> None:
    if count <= 0:
        raise ValueError('No tests discovered')


def inspect(root: Path) -> dict:
    entries = index_entries(root)
    errors = []
    checked = 0
    for name in PUBLIC_FILES:
        if name not in entries or not (root / name).is_file():
            errors.append(name + ': missing public document')
    for name, (mode, _) in entries.items():
        if private_path(name):
            errors.append(name + ': forbidden tracked path')
        if mode == '160000':
            continue
        path = root / name
        if mode not in ('100644', '100755') or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            errors.append(name + ': unsupported or escaping file')
            continue
        data = path.read_bytes()
        if len(data) > 2 * 1024 * 1024 or b'\0' in data:
            errors.append(name + ': unscanned large/binary file; explicit review required')
            continue
        checked += 1
        errors.extend(name + ': ' + detector for detector in credential_hits(data))
        if name.endswith('.py'):
            compile(data, name, 'exec')
        if name.endswith('.json'):
            json.loads(data)
    lock = json.loads((root / 'sources.lock.json').read_text(encoding='utf-8'))
    errors.extend(validate_sources(lock, (root / '.gitmodules').read_text(encoding='utf-8'), entries))
    example = json.loads((root / 'config/development.example.json').read_text(encoding='utf-8'))
    if not (example.get('mode') == 'mock' and example.get('autonomy_enabled') is False
            and example.get('scheduler_enabled') is False and example.get('real_model_budget_usd') == 0):
        errors.append('unsafe example defaults')
    if 'MIT License' not in (root / 'LICENSE').read_text(encoding='utf-8'):
        errors.append('root license')
    suite = unittest.TestLoader().discover(str(root / 'tests'))
    require_nonzero_tests(suite.countTestCases())
    for path in ('runtime/probe', 'scratch/probe', 'artifacts/probe', '.alaz-ci/tests.json', '.env', 'config/private.key'):
        result = subprocess.run(['git', '-C', str(root), 'check-ignore', '--no-index', '--quiet', '--', path], timeout=15)
        if result.returncode != 0:
            errors.append('not ignored: ' + path)
    return {'scope': 'M0_root_preparation_only', 'result': 'FAIL' if errors else 'PASS',
            'root_files_checked': checked, 'source_gitlinks_checked': len(EXPECTED),
            'discovered_tests': suite.countTestCases(), 'errors': errors,
            'vendor_bytes_checked': False, 'runtime_tested': False, 'model_called': False,
            'secret_scan': 'bounded root tracked text patterns; not a complete security audit'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = inspect(args.root.resolve())
    except Exception as error:
        result = {'scope': 'M0_root_preparation_only', 'result': 'FAIL', 'error_type': type(error).__name__, 'errors': ['Gate failed; inspect local code without exposing secret values.']}
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
