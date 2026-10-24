"""Named immutable pre-O127 generations; no generic source mismatch bypass."""
import hashlib,json
from historical_layout_f126c1 import executed_source_hash as pre_f126_hash

def executed_source_hash(root,name,expected):
    current=hashlib.sha256((root/name).read_bytes()).hexdigest()
    if current==expected:return current
    e=root/'evidence/d3b-current-observers-o127b6'
    record=json.loads((e/'historical-bindings.json').read_text(encoding='utf-8'))
    item=record['sources'].get(name)
    if item is not None and item['sha256']==expected:
        baseline=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
        assert record['base']==baseline['base']=='e4968ae6c6265aa3f1841efacdee286a767d13a3'
        assert item['sha256']==baseline['sources'][name]
        digest=hashlib.sha256((root/item['path']).read_bytes()).hexdigest()
        assert digest==expected,'historical O127 source changed'
        return digest
    return pre_f126_hash(root,name,expected)
