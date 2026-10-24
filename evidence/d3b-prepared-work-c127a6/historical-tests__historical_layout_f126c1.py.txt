"""Exact saved source generations for older receipts, never current acceptance.

Only nine named changed files are redirected. An expected digest must match the
immutable pre-F126 baseline AND saved bytes; no generic mismatch bypass.
"""
import hashlib,json

def executed_source_hash(root,name,expected):
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
