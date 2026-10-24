"""Four exact pre-publication test generations, never current runtime proof."""
import hashlib,json
NAMES=frozenset(('tests/fixtures/hermes_wire.py','tests/test_gateway_native_layout.py',
                 'tests/test_principal_export_replace_refs.py',
                 'tests/historical_owner_b129d6.py'))

def saved_generation_hash(root,name,expected):
    if name not in NAMES:return None
    e=root/'evidence/publication-24oct-p132l1'
    manifest=json.loads((e/'historical-source-bindings.json').read_text(encoding='utf-8'))
    assert manifest['base']=='ea7b48257ae741c81ff385bac596ceb884d02caf'
    assert set(manifest['sources'])==NAMES
    row=manifest['sources'][name]
    if row['sha256']!=expected:return None
    baseline=json.loads((root/'evidence/d3b-canonical-api-joint-j131d6/full-sources-after.json').read_text(encoding='utf-8'))
    assert baseline[name]==expected,'unrecognized pre-publication generation'
    digest=hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
    assert digest==expected,'saved historical test bytes changed'
    return digest
