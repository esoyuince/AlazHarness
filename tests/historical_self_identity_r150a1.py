"""Exact saved code for historical experiment receipts, not current acceptance.

The R158 resolver first handles its four pinned parent source generations.
This resolver's own named files require the immutable 31e0c54 baseline digest.
Unknown/current generations still hash their live file. Old test outcomes or
expected digests are never changed by either resolver.
"""
from pathlib import Path
import hashlib,json
BASE='31e0c54c530151bd25ebc43f617a853bb1736412'
NAMES=frozenset(('packages/claw-hermes/credential_guard.py', 'packages/claw-hermes/gateway_state_projection.py', 'packages/claw-hermes/gateway_retained_launch.py', 'tests/test_projected_launch_l145a8.py', 'tests/historical_projection_p142c6.py', 'tests/test_integrated_profile_metadata_q104e.py', 'tests/test_native_profile_admission_receipt.py', 'tests/test_projected_launch_receipt_l145a8.py', 'tests/test_retained_projection_receipt_p142c6.py'))

def _archived(root,name,expected):
    from historical_local_control_r158a1 import archived_source as before_local_control
    prior=before_local_control(root,name,expected)
    if prior is not None:return prior
    if name not in NAMES:return None
    folder=root/'evidence/d3b-self-identity-r150a1'
    record=json.loads((folder/'historical-source-bindings.json').read_text(encoding='utf-8'))
    baseline=json.loads((folder/'baseline.json').read_text(encoding='utf-8'))
    assert record['base']==baseline['base']==BASE,'unexpected historical base'
    assert set(record['sources'])==NAMES,'unexpected archived source set'
    row=record['sources'][name]
    assert row['sha256']==baseline['sources'][name],'archive not bound to original baseline'
    if expected!=row['sha256']:return None
    fixed='evidence/d3b-self-identity-r150a1/base-'+name.replace('/','__')+'.txt'
    assert row['path']==fixed,'unexpected archived source path'
    path=root/fixed
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'archived executed bytes changed'
    return path

def saved_generation_hash(root,name,expected):
    path=_archived(root,name,expected)
    return None if path is None else hashlib.sha256(path.read_bytes()).hexdigest()

def source_path(root,name,expected):
    path=_archived(root,name,expected)
    return root/name if path is None else path

def source_hash(root,name,expected):
    return hashlib.sha256(source_path(root,name,expected).read_bytes()).hexdigest()
