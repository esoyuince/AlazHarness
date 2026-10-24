"""Exact saved source generations for older receipts, never current acceptance.

Only nine named changed files are redirected. An expected digest must match the
immutable pre-F126 baseline AND saved bytes; no generic mismatch bypass.
"""
import hashlib,json

def executed_source_hash(root,name,expected):
    from historical_owner_b129d6 import saved_generation_hash as saved_b129
    previous=saved_b129(root,name,expected)
    if previous is not None:return previous
    from historical_prepared_c127a6 import saved_generation_hash
    saved=saved_generation_hash(root,name,expected)
    if saved is not None:return saved
    e=root/'evidence/d3b-confined-consumer-f126c1'
    bindings=json.loads((e/'historical-source-bindings.json').read_text(encoding='utf-8'))
    if name not in bindings['sources']:
        return hashlib.sha256((root/name).read_bytes()).hexdigest()
    baseline=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
    assert bindings['base']==baseline['base']=='931e57045bdce466934838dffde7d54527ad3f12'
    record=bindings['sources'][name]
    assert record['sha256']==baseline['sources'][name]==expected,'unexpected historical generation'
    digest=hashlib.sha256((root/record['path']).read_bytes()).hexdigest()
    assert digest==expected,'saved historical source changed'
    return digest
