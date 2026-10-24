"""Exact pre-finite-close sources for historical receipts, never new acceptance."""
import hashlib,json
NAMES=frozenset('packages/claw-hermes/'+n for n in (
 'gateway_prepared_consumer.py','gateway_store_startup.py',
 'gateway_consumer_admission.py','gateway_consumer_api.py'))
def saved_generation_hash(root,name,expected):
    if name not in NAMES:return None
    folder=root/'evidence/d3b-finite-close-f135c6'
    rows=json.loads((folder/'historical-source-bindings.json').read_text(encoding='utf-8'))
    row=rows['sources'][name]
    if row['sha256']!=expected:return None
    baseline=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
    assert rows['base']==baseline['harnessBase']
    assert baseline['sourceHashes'][name]==expected,'unknown pre-finite generation'
    digest=hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
    assert digest==expected,'pre-finite saved bytes changed'
    return digest
