"""Three exact pre-C127 source generations for historical evidence only.

No arbitrary mismatch fallback: caller expected hash must name the saved base.
Unrecognized generations stay with the existing old resolver or current bytes.
"""
import hashlib,json

def saved_generation_hash(root,name,expected):
    e=root/'evidence/d3b-prepared-work-c127a6'
    bindings=json.loads((e/'historical-source-bindings.json').read_text(encoding='utf-8'))
    if name not in bindings['sources']:return None
    record=bindings['sources'][name]
    if expected!=record['sha256']:return None
    base=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
    assert bindings['base']==base['base']=='e4968ae6c6265aa3f1841efacdee286a767d13a3'
    assert record['sha256']==base['sources'][name]==expected
    digest=hashlib.sha256((root/record['path']).read_bytes()).hexdigest()
    assert digest==expected,'saved C127 source generation changed'
    return digest

def executed_source_hash(root,name,expected):
    saved=saved_generation_hash(root,name,expected)
    return saved if saved is not None else hashlib.sha256((root/name).read_bytes()).hexdigest()
