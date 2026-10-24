"""Named immutable pre-B129 generations, for historical receipts only.

Expected digest must equal both saved baseline and archived bytes. Unknown source
or generation is not redirected; current acceptance has its own actual runs.
"""
import hashlib,json


def saved_generation_hash(root,name,expected):
    from historical_ci_p132l1 import saved_generation_hash as saved_ci
    previous=saved_ci(root,name,expected)
    if previous is not None:return previous
    e=root/'evidence/d3b-active-owner-b129d6'
    manifest=json.loads((e/'historical-source-bindings.json').read_text(encoding='utf-8'))
    item=manifest['sources'].get(name)
    if item is None or item['sha256']!=expected:return None
    baseline=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
    assert manifest['base']==baseline['base']=='ffa0d366b505848718f4e10f044af19350a4d947'
    assert baseline['sources'][name]==expected,'unknown historical B129 source'
    digest=hashlib.sha256((root/item['path']).read_bytes()).hexdigest()
    assert digest==expected,'historical B129 bytes changed'
    return digest


def executed_source_hash(root,name,expected):
    old=saved_generation_hash(root,name,expected)
    return old if old is not None else hashlib.sha256((root/name).read_bytes()).hexdigest()
