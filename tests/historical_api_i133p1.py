"""Exact pre-I133 generations for old receipts, not new runtime acceptance."""
import hashlib,json
NAMES=frozenset(('packages/claw-hermes/gateway_prepared_consumer.py',
    'packages/claw-hermes/gateway_consumer_admission.py',
    'packages/claw-hermes/gateway_store_startup.py',
    'tests/historical_owner_b129d6.py','tests/test_active_owner_receipt_b129d6.py'))

def saved_generation_hash(root,name,expected):
    from historical_finite_close_f135c6 import saved_generation_hash as previous_finite
    old=previous_finite(root,name,expected)
    if old is not None:return old
    if name not in NAMES:return None
    folder=root/'evidence/d3b-api-owner-i133p1'
    record=json.loads((folder/'historical-source-bindings.json').read_text(encoding='utf-8'))
    assert set(record['sources'])==NAMES
    row=record['sources'][name]
    if row['sha256']!=expected:return None
    baseline=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
    assert baseline['sources'][name]==expected,'unknown pre-I133 generation'
    actual=hashlib.sha256((root/row['path']).read_bytes()).hexdigest()
    assert actual==expected,'historical pre-I133 bytes changed'
    return actual

def executed_source_hash(root,name,expected):
    old=saved_generation_hash(root,name,expected)
    return old if old is not None else hashlib.sha256((root/name).read_bytes()).hexdigest()
