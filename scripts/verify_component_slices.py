"""Check copied component provenance; --full also checks the pinned local vendor bytes.

Offline: never clones, imports an agent, installs dependencies or mutates a copy.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from verify_workspace import confined_path

SOURCES = {
    'openclaw': {'src/agents/harness/attempt-cancellation.ts', 'src/agents/harness/attempt-deadlines.ts',
                 'packages/normalization-core/src/number-coercion.ts', 'packages/normalization-core/src/string-coerce.ts', 'LICENSE'},
    'hermes-agent': {'tui_gateway/transport.py', 'agent/iteration_budget.py', 'LICENSE'},
}

def transform(data: bytes, kind: str) -> bytes:
    if kind == 'verbatim': return data
    if kind != 'relocate-deadline-import': raise ValueError('Unknown transformation')
    old = b'"@openclaw/normalization-core/number-coercion"'
    if data.count(old) != 1: raise ValueError('Expected exactly one deadline import')
    return data.replace(old, b'"./number-coercion.ts"')


def verify(root: Path, full: bool = False) -> dict:
    root = root.resolve()
    manifest = json.loads((root/'components.lock.json').read_text(encoding='utf-8'))
    lock = json.loads((root/'sources.lock.json').read_text(encoding='utf-8'))
    sources = {s['name']: s for s in lock['repositories']}
    expected = {(n,p) for n,ps in SOURCES.items() for p in ps}
    rows = manifest.get('files', [])
    actual = [(r['source_name'],r['source_path']) for r in rows]
    if manifest.get('schema_version') != 1 or len(actual) != len(expected) or set(actual) != expected:
        raise ValueError('Unexpected component set')
    if full:
        for name in SOURCES:
            repo = confined_path(root, sources[name]['path'])
            head = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], timeout=30, text=True).strip()
            if head != sources[name]['commit']: raise ValueError('Unpinned source checkout')
    for row in rows:
        name = row['source_name']; source = sources[name]
        prefix = 'hermes' if name == 'hermes-agent' else 'openclaw'
        expected_target = f"packages/upstream/{prefix}/{Path(row['source_path']).name}"
        if row['target_path'] != expected_target or row['source_commit'] != source['commit']:
            raise ValueError('Source identity or destination mismatch')
        kind = 'relocate-deadline-import' if row['source_path'].endswith('attempt-deadlines.ts') else 'verbatim'
        if row['transformation'] != kind: raise ValueError('Unexpected component modification')
        data = confined_path(root,row['target_path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['target_sha256']: raise ValueError('Copied component changed: '+row['target_path'])
        if kind == 'verbatim' and row['target_sha256'] != row['source_sha256']:
            raise ValueError('Verbatim digest mismatch')
        if full:
            original = confined_path(confined_path(root,source['path']),row['source_path']).read_bytes()
            if hashlib.sha256(original).hexdigest() != row['source_sha256'] or transform(original,kind) != data:
                raise ValueError('Source byte provenance mismatch')
    return {'result':'PASS','scope':'component copy provenance','copies':len(rows),
            'source_bytes_checked':full,'upstream_runtime_tested':False}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true')
    args=parser.parse_args()
    try: result=verify(Path(__file__).resolve().parents[1], args.full)
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result={'result':'FAIL','error':str(error)}
    print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
