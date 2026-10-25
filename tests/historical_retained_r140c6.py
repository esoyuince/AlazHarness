"""Exact pre-R140 source bytes for old evidence, never current runtime acceptance."""
import hashlib,json
NAMES=frozenset('packages/claw-hermes/'+n for n in (
    'gateway_native_layout.py','gateway_store_startup.py','gateway_prepared_consumer.py'))

def saved_generation_hash(root,name,expected):
    from historical_projection_p142c6 import saved_generation_hash as prior_projection
    prior=prior_projection(root,name,expected)
    if prior is not None:return prior
    if name not in NAMES:return None
    folder=root/'evidence/d3b-retained-profile-r140c6'
    record=json.loads((folder/'historical-source-bindings.json').read_text(encoding='utf-8'))
    baseline=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
    assert record['base']==baseline['base']=='508bf5af1bb0f20b8d526abbda974cde0aeac278'
    assert set(record['sources'])==NAMES
    item=record['sources'][name]
    if item['sha256']!=expected:return None
    assert baseline['sources'][name]==expected,'unknown pre-R140 source'
    digest=hashlib.sha256((root/item['path']).read_bytes()).hexdigest()
    assert digest==expected,'pre-R140 saved bytes changed'
    return digest
