"""Bind earlier native/Linux receipts to their exact pre-consumer startup bytes.

Only gateway_store_startup is redirected, and only to this saved immutable base.
These old runs are explicitly NOT acceptance of the new prepared consumer.
"""
import hashlib,json

def executed_source_hash(root,name,expected):
    if name!='packages/claw-hermes/gateway_store_startup.py':
        return hashlib.sha256((root/name).read_bytes()).hexdigest()
    e=root/'evidence/d3b-startup-consumer-s124b1'
    base=json.loads((e/'baseline.json').read_text(encoding='utf-8'))
    assert base['base']=='66a7bf776bd8df0ea0e0562efa4b03604f93b1fa'
    assert base['sources'][name]==expected,'receipt generation does not match saved pre-consumer source'
    digest=hashlib.sha256((e/'gateway_store_startup.py.before.txt').read_bytes()).hexdigest()
    assert digest==expected,'executed historical startup bytes changed'
    return digest
