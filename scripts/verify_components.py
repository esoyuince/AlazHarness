#!/usr/bin/env python3
"""Check selected component provenance, optionally reproducing each source transform."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
from verify_workspace import confined_path

PREFIX = 'packages/upstream/'
EXPECTED_SOURCES = {('hermes-agent', 'LICENSE'): 'copy',
 ('hermes-agent', 'agent/iteration_budget.py'): 'copy',
 ('hermes-agent', 'gateway/platforms/api_server_runs.py'): 'function',
 ('hermes-agent', 'hermes_state_keys.py'): 'copy',
 ('hermes-agent', 'tui_gateway/transport.py'): 'copy',
 ('openclaw', 'LICENSE'): 'copy',
 ('openclaw', 'packages/normalization-core/src/number-coercion.ts'): 'copy',
 ('openclaw', 'packages/normalization-core/src/string-coerce.ts'): 'copy',
 ('openclaw', 'src/agents/harness/attempt-cancellation.ts'): 'copy',
 ('openclaw', 'src/agents/harness/attempt-deadlines.ts'): 'rewrite'}

def materialize(source: bytes, entry: dict) -> bytes:
    text = source.decode('utf-8')
    if entry['mode'] == 'function':
        found = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == entry['symbol']]
        if len(found) != 1:
            raise ValueError('Ambiguous source symbol')
        node = found[0]
        text = entry['prefix'] + '\n'.join(text.splitlines()[node.lineno - 1:node.end_lineno]) + '\n'
    elif entry['mode'] == 'rewrite':
        for old, new in entry['replacements']:
            if text.count(old) != 1:
                raise ValueError('Source replacement no longer unique')
            text = text.replace(old, new)
    elif entry['mode'] != 'copy':
        raise ValueError('Unknown source transform')
    return text.encode('utf-8')

def inspect(root: Path, with_vendor: bool = False, source_workspace: Path | None = None) -> dict:
    root = root.resolve()
    lock = json.loads((root / 'sources.lock.json').read_text(encoding='utf-8'))
    pins = {row['name']: row['commit'] for row in lock['repositories']}
    manifest = json.loads((root / 'config/components.lock.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version') != 1 or not manifest.get('entries'):
        raise ValueError('Invalid component manifest')
    pairs = [(e['repository'], e['source']) for e in manifest['entries']]
    if len(pairs) != len(EXPECTED_SOURCES) or set(pairs) != set(EXPECTED_SOURCES):
        raise ValueError('Unexpected component source set')
    for entry in manifest['entries']:
        if entry['mode'] != EXPECTED_SOURCES[(entry['repository'], entry['source'])]:
            raise ValueError('Unexpected component transformation')
    checked = []; destinations = set()
    for entry in manifest['entries']:
        name = entry['destination']
        if not name.startswith(PREFIX) or name in destinations:
            raise ValueError('Unexpected or duplicate destination')
        destinations.add(name)
        if pins.get(entry['repository']) != entry['commit']:
            raise ValueError('Component/source commit disagreement')
        target = confined_path(root, name)
        if hashlib.sha256(target.read_bytes()).hexdigest() != entry['destination_sha256']:
            raise ValueError('Selected source changed: ' + name)
        if with_vendor:
            source_root = confined_path((source_workspace or root).resolve(), 'vendor/' + entry['repository'])
            raw = confined_path(source_root, entry['source']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry['source_sha256']:
                raise ValueError('Upstream source bytes changed')
            if materialize(raw, entry) != target.read_bytes():
                raise ValueError('Source transform mismatch')
        checked.append(name)
    actual = {p.relative_to(root).as_posix() for p in (root / PREFIX).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p != root / PREFIX / 'README.md'}
    if actual != destinations:
        raise ValueError('Unregistered upstream payload')
    return {'result': 'PASS', 'components': len(checked), 'vendor_bytes_compared': with_vendor,
            'scope': 'selected source provenance; not complete upstream build acceptance'}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-vendor', action='store_true')
    parser.add_argument('--source-workspace', type=Path, help='Read pinned vendor bytes from another explicit checkout')
    args = parser.parse_args()
    try:
        result = inspect(Path(__file__).resolve().parents[1], args.with_vendor, args.source_workspace)
    except (ValueError, OSError, KeyError, TypeError) as error:
        result = {'result': 'FAIL', 'error': str(error)}
    print(json.dumps(result, indent=2))
    return 0 if result['result'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
