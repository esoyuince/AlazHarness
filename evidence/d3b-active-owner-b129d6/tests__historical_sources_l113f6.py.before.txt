"""Historical source binding for receipts executed before optional three-store code.

Only explicitly saved baseline modules are redirected; the later T114 projection
change is also pinned to its prior executed source. Current acceptance
is tested independently by L113F6 native002; old kernel/HTTP runs are NOT called
current-code evidence. No other source change is silently ignored.
"""
import hashlib,json

def receipt_source_hash(root,name,expected):
    # T114 adds an explicit third-file selector; old two-file projection receipts
    # remain bound to their saved executed implementation, never the new one.
    if name=='packages/claw-hermes/gateway_state_projection.py':
        evidence=root/'evidence/d3b-three-projection-t114r6a'
        baseline=json.loads((evidence/'baseline.json').read_text(encoding='utf-8'))
        assert baseline['base']=='0be65aaff452bb8a4416f4a684efa6818c76f04c'
        assert baseline['sources'][name]==expected,'projection receipt generation mismatch'
        digest=hashlib.sha256((evidence/'gateway_state_projection.py.before.txt').read_bytes()).hexdigest()
        assert digest==expected,'historical projection source modified'
        return digest

    old={'packages/claw-hermes/'+n:n+'.before.txt' for n in
         ('gateway_store_startup.py','gateway_native_layout.py','gateway_http_readiness.py')}
    if name not in old:return hashlib.sha256((root/name).read_bytes()).hexdigest()
    evidence=root/'evidence/d3b-response-lifecycle-l113f6'
    baseline=json.loads((evidence/'baseline.json').read_text(encoding='utf-8'))
    assert baseline['base']=='a3951d764df291bebbf20f0452119a3d461d8832'
    assert baseline['sources'][name]==expected, 'historical receipt is not the saved baseline'
    digest=hashlib.sha256((evidence/old[name]).read_bytes()).hexdigest()
    assert digest==expected, 'saved executed source modified'
    return digest
