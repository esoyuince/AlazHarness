"""Exact prior projection generation for historical proof only, never new kernel acceptance."""
import hashlib,json
NAME='packages/claw-hermes/gateway_state_projection.py'
BASE='1321699198805fad1909d40053e118a624dc23f2'
def saved_generation_hash(root,name,expected):
    from historical_self_identity_r150a1 import saved_generation_hash as before_identity
    prior=before_identity(root,name,expected)
    if prior is not None:return prior
    if name!=NAME:return None
    e=root/'evidence/d3b-retained-projection-p142c6'
    baseline=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
    assert baseline['base']==BASE
    recorded=baseline['sources'][NAME]
    if expected!=recorded:return None
    digest=hashlib.sha256((e/'gateway_state_projection.before.py.txt').read_bytes()).hexdigest()
    assert digest==expected,'prior projection source bytes changed'
    return digest
