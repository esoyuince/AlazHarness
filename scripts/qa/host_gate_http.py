"""Explicit selected-component HTTP QA; NOT a native Gateway/agent run.
Uses the real aiohttp and host plugin, but a synthetic SessionDB owner/adapter.
The native-adapter provenance guard is replaced ONLY during test-app binding.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
sys.path.insert(0,str(ROOT/'tests'))
from host_gate import HostGatePolicy
from test_host_gate_qa import GateFixture
import host_gate_plugin

async def run(out: Path):
    from aiohttp import web,ClientSession
    fixture_dir=out/'fixture';fixture_dir.mkdir()
    f=GateFixture(fixture_dir)
    callbacks=[];fail_native=False
    async def native(request):
        matched=[json.loads(v) for k,v in f.rows() if k.startswith('alaz.host_gate.intent.') and json.loads(v)['key']==request.headers.get('Idempotency-Key')]
        callbacks.append({'matched_intents':len(matched),'already_consumed':len(matched)==1 and matched[0]['dispatchState']=='consumed'})
        if fail_native:raise OSError('controlled-native-refusal')
        return web.json_response({'run_id':'run_'+'1'*32,'status':'queued','replayed':False},status=202)
    adapter=SimpleNamespace(_host='127.0.0.1',_expected_api_key=lambda:f.context.api_token,_room_grant_token=lambda _:None,
      gateway_runner=SimpleNamespace(session_authority=SimpleNamespace(db=f.db,epoch=1,retiring=False,retired=False),
                                    session_runtime_descriptor={'state':'ready','instance_id':'first-owner'}),_handle_runs=native)
    app=web.Application();app.router.add_post('/v1/runs',native)
    # This substitution is the explicitly disclosed synthetic native port.
    with patch.object(host_gate_plugin,'validate_native_adapter',lambda _:None):
        host_gate_plugin.bind_host_gate(app,adapter,HostGatePolicy(frozenset({'test-model'}),max_issued=32,max_dispatches=8))
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    port=site._server.sockets[0].getsockname()[1];base=f'http://127.0.0.1:{port}';cases=[]
    auth={'Authorization':'Bearer '+f.context.api_token}
    async with ClientSession() as client:
        async def request(method,path,*,obj=None,headers=None,data=None):
            h=auth if headers is None else headers
            async with client.request(method,base+path,headers=h,json=obj,data=data,allow_redirects=False) as response:
                return response.status,await response.json()
        def check(name,condition,**details):
            cases.append({'name':name,'passed':bool(condition),**details})
            if not condition:raise AssertionError(name)
        try:
            packet={'requestId':f.rid,'body':f.body}
            code,_=await request('POST','/alaz/host/v1/intents',obj=packet,headers={});check('no_auth_refuses',code==401 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/intents',obj=packet,headers={'Authorization':'Bearer wrong'});check('wrong_auth_refuses',code==401 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/intents',obj=packet,headers=[('Authorization','Bearer '+f.context.api_token)]*2);check('duplicate_auth_refuses',code==401 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/intents?profile=other',obj=packet);check('query_refuses',code==409 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/intents',obj=packet,headers=auth|{'X-Hermes-Session-Key':'other'});check('foreign_session_header_refuses',code==409 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/intents',data='{"requestId":"a","requestId":"b"}',headers=auth|{'Content-Type':'application/json'});check('duplicate_json_key_refuses',code==409 and not f.rows())
            code,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=auth|{'Idempotency-Key':'legacy'});check('unissued_key_refuses',code==409 and not callbacks)
            code,doc=await request('POST','/alaz/host/v1/intents',obj=packet);check('issue_does_not_execute',code==201 and doc['dispatchState']=='issued' and not callbacks)
            before=f.rows();code,again=await request('POST','/alaz/host/v1/intents',obj=packet);check('same_id_replays_no_write',code==201 and again['idempotencyKey']==doc['idempotencyKey'] and again['replayed'] is True and f.rows()==before)
            code,_=await request('POST','/alaz/host/v1/intents',obj={'requestId':f.rid,'body':f.body|{'input':'changed'}});check('same_id_different_body_refuses',code==409 and f.rows()==before)
            keyheaders=auth|{'Idempotency-Key':doc['idempotencyKey']}
            code,_=await request('POST','/v1/runs',obj=f.body,headers=keyheaders);check('raw_post_refuses_while_plugin_installed',code==409 and f.rows()==before and not callbacks)
            code,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body|{'input':'changed'},headers=keyheaders);check('mutated_dispatch_refuses',code==409 and f.rows()==before and not callbacks)
            code,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=keyheaders);check('commit_precedes_callback',code==202 and len(callbacks)==1 and callbacks[0]['already_consumed'])
            code,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=keyheaders);check('duplicate_dispatch_refuses',code==409 and len(callbacks)==1)
            code,doc2=await request('POST','/alaz/host/v1/intents',obj={'requestId':'b'*32,'body':f.body});assert code==201
            results=await asyncio.gather(*[request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=auth|{'Idempotency-Key':doc2['idempotencyKey']}) for _ in range(20)])
            check('twenty_http_consumers_one_callback',sum(x[0]==202 for x in results)==1 and sum(x[0]==409 for x in results)==19 and len(callbacks)==2)
            code,doc3=await request('POST','/alaz/host/v1/intents',obj={'requestId':'c'*32,'body':f.body});assert code==201
            fail_native=True
            code,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=auth|{'Idempotency-Key':doc3['idempotencyKey']})
            code2,_=await request('POST','/alaz/host/v1/dispatch',obj=f.body,headers=auth|{'Idempotency-Key':doc3['idempotencyKey']})
            check('native_exception_never_refunds',code==503 and code2==409 and len(callbacks)==3)
            capcode,cap=await request('GET','/alaz/host/v1/capabilities');check('no_cost_or_sandbox_claim',capcode==200 and cap['modelTokenOrCostBudget'] is False and cap['toolSandbox'] is False)
        finally:await runner.cleanup()
    return {'scope':'selected-component real loopback HTTP; synthetic adapter/SessionDB/native callback; provenance guard substituted at binding ONLY',
      'native_gateway_executed':False,'agent_executed':False,'model_calls':0,'cases':cases,
      'native_callback_count':len(callbacks),'passed':sum(c['passed'] for c in cases),'failed':sum(not c['passed'] for c in cases)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    out=args.output.resolve()
    if out.exists():raise FileExistsError('Fresh output required')
    out.mkdir(parents=True)
    files=[ROOT/'packages/claw-hermes/host_gate.py',ROOT/'packages/claw-hermes/host_gate_plugin.py',ROOT/'tests/test_host_gate_qa.py',Path(__file__)]
    before={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    result=asyncio.run(run(out));result['code_hashes']=before
    result['code_drift']=[n for n,h in before.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]
    if result['code_drift']:raise RuntimeError('Code changed during component test')
    (out/'http-component.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
