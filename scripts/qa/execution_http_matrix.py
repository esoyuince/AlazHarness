"""Opt-in real aiohttp/ExecutionBoundary matrix with a synthetic native owner.
The profile/registry checker is explicitly substituted; this is NOT a Gateway.
"""
from __future__ import annotations
import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'));sys.path.insert(0,str(ROOT/'tests'))
from execution_boundary import ExecutionBoundary,PROVIDER_BASE
from test_execution_gate_qa import policy
from test_host_gate_qa import GateFixture
TOKEN='fixture-provider-credential-32bytes'
BODY={'model':'fixture-model','messages':[{'role':'user','content':'fixture'}],'max_tokens':20}

async def one(out,name,*,body=None,headers=None,raw=None,query='',mode='success',expected=200,claims=1):
    from aiohttp import web,ClientSession
    folder=out/name;folder.mkdir();f=GateFixture(folder);allowed=folder/'allowed.txt';allowed.write_text('fixture\n',encoding='utf-8')
    calls=[];forward=[]
    async def upstream(request):
        calls.append(await request.json())
        if mode=='redirect':return web.Response(status=307,headers={'Location':'http://127.0.0.1:1/not-called'})
        if mode=='error':return web.json_response({'error':{'message':'controlled transient'}},status=503)
        model='wrong-model' if mode=='wrong-response-model' else 'fixture-model'
        usage={'prompt_tokens':2,'completion_tokens':1,'total_tokens':3}
        value={'id':'fixture','object':'chat.completion','created':1,'model':model,'choices':[{'index':0,'message':{'role':'assistant','content':'fixture'},'finish_reason':'stop'}],'usage':usage}
        if mode=='unknown-usage':del value['usage']
        if mode=='bad-usage':value['usage']['prompt_tokens']=True
        if mode=='over-usage':value['usage']={'prompt_tokens':101,'completion_tokens':1,'total_tokens':102}
        if mode=='stream-compact-wrong-model':
            frames=[{'model':'wrong-model','choices':[],'usage':usage}]
            return web.Response(text=''.join('data:'+json.dumps(x)+'\n\n' for x in frames)+'data:[DONE]\n\n',content_type='text/event-stream')
        if mode=='stream-over-then-lower':
            frames=[{'model':'fixture-model','choices':[],'usage':{'prompt_tokens':101,'completion_tokens':1,'total_tokens':102}},
                    {'model':'fixture-model','choices':[],'usage':usage}]
            return web.Response(text=''.join('data: '+json.dumps(x)+'\n\n' for x in frames)+'data: [DONE]\n\n',content_type='text/event-stream')
        return web.json_response(value)
    uapp=web.Application();uapp.router.add_post('/v1/chat/completions',upstream)
    ur=web.AppRunner(uapp);await ur.setup();us=web.TCPSite(ur,'127.0.0.1',0);await us.start();up=us._server.sockets[0].getsockname()[1]
    p=policy(max_provider_calls=3)
    boundary=ExecutionBoundary({'policy':asdict(p),'upstream_base_url':f'http://127.0.0.1:{up}/v1','provider_bearer':TOKEN,'allowed_read_files':[str(allowed)]})
    adapter=SimpleNamespace(_port=0,_expected_api_key=lambda:f.context.api_token,
        gateway_runner=SimpleNamespace(session_authority=SimpleNamespace(db=f.db,epoch=1,retired=False,retiring=False),
         session_runtime_descriptor={'state':'ready','instance_id':'first-owner'}))
    # Explicit test-only substitution: config/registry/native launch are not under test here.
    boundary.validate_profile=lambda:None
    boundary.register(SimpleNamespace())
    boundary.tools.register=lambda ctx:None  # disclosed synthetic registry port, not real file-tool acceptance
    app=web.Application();boundary.bind(app,adapter)
    rr=web.AppRunner(app);await rr.setup();site=web.TCPSite(rr,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1];adapter._port=port
    try:
        packet=dict(BODY) if body is None else body
        h={'Authorization':'Bearer '+TOKEN} if headers is None else headers
        if raw is not None:h={**h,'Content-Type':'application/json'}
        async with ClientSession() as client:
            async with client.post(f'http://127.0.0.1:{port}'+PROVIDER_BASE+'/chat/completions'+query,headers=h,
                  data=raw,json=packet if raw is None else None,allow_redirects=False) as res:
                status=res.status;text=await res.text()
        snapshot=boundary.ledger().snapshot() if f.rows() else None
        count=snapshot['providerCalls'] if snapshot else 0
        row={'name':name,'expected_http_status':expected,'http_status':status,'provider_reservations':count,'upstream_http_calls':len(calls),
             'passed':status==expected and count==claims and len(calls)==claims,'quarantined':snapshot['quarantined'] if snapshot else None,
             'response_error':json.loads(text).get('error',{}).get('code') if text.startswith('{') else None}
        if calls:row['forwarded_output_ceiling']={k:calls[-1][k] for k in ('max_tokens','max_completion_tokens') if k in calls[-1]}
        return row
    finally:await rr.cleanup();await ur.cleanup()

async def run(out):
    cases=[('normal',{}),('unknown-usage',{'mode':'unknown-usage'}),
      ('missing-auth',{'headers':{},'expected':401,'claims':0}),
      ('wrong-auth',{'headers':{'Authorization':'Bearer wrong'},'expected':401,'claims':0}),
      ('foreign-query',{'query':'?profile=other','expected':401,'claims':0}),
      ('foreign-header',{'headers':{'Authorization':'Bearer '+TOKEN,'X-Hermes-Session-Key':'other'},'expected':401,'claims':0}),
      ('wrong-model',{'body':BODY|{'model':'foreign'},'expected':403,'claims':0}),
      ('no-messages',{'body':BODY|{'messages':[]},'expected':403,'claims':0}),
      ('multimodal-content',{'body':BODY|{'messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://unused.invalid'}}]}]},'expected':403,'claims':0}),
      ('unknown-role',{'body':BODY|{'messages':[{'role':'foreign','content':'fixture'}]},'expected':403,'claims':0}),
      ('multiple-completions',{'body':BODY|{'n':2},'expected':403,'claims':0}),
      ('bool-completions',{'body':BODY|{'n':True},'expected':403,'claims':0}),
      ('nonbool-stream',{'body':BODY|{'stream':1},'expected':403,'claims':0}),
      ('above-output-cap',{'body':BODY|{'max_tokens':21},'expected':403,'claims':0}),
      ('null-output-cap',{'body':BODY|{'max_tokens':None},'expected':403,'claims':0}),
      ('bool-output-cap',{'body':BODY|{'max_tokens':True},'expected':403,'claims':0}),
      ('float-output-cap',{'body':BODY|{'max_tokens':1.5},'expected':403,'claims':0}),
      ('two-output-caps',{'body':BODY|{'max_completion_tokens':20},'expected':403,'claims':0}),
      ('missing-output-cap',{'body':{k:v for k,v in BODY.items() if k!='max_tokens'}}),
      ('duplicate-json',{'raw':'{"model":"fixture-model","model":"other","messages":[]}','expected':403,'claims':0}),
      ('provider-503',{'mode':'error','expected':503}),
      ('provider-redirect',{'mode':'redirect','expected':403}),
      ('provider-bool-usage',{'mode':'bad-usage','expected':403}),
      ('provider-over-usage',{'mode':'over-usage','expected':403}),
      ('wrong-response-model',{'mode':'wrong-response-model','expected':403}),
      ('stream-over-then-lower',{'body':BODY|{'stream':True},'mode':'stream-over-then-lower','expected':403}),
      ('stream-compact-wrong-model',{'body':BODY|{'stream':True},'mode':'stream-compact-wrong-model','expected':403})]
    rows=[]
    for name,options in cases:
        try:row=await one(out,name,**options)
        except Exception as exc:row={'name':name,'passed':False,'exception_type':type(exc).__name__,'error':str(exc)}
        rows.append(row)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve()
    if out.exists():raise FileExistsError('Fresh output required')
    out.mkdir(parents=True)
    files=[ROOT/'packages/claw-hermes/execution_boundary.py',ROOT/'packages/claw-hermes/execution_budget.py',ROOT/'tests/test_execution_gate_qa.py',Path(__file__)]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    rows=asyncio.run(run(out));result={'scope':'real aiohttp/ExecutionBoundary/provider route; synthetic adapter/SessionDB owner, config and registry verifier explicitly substituted. NOT native Gateway','cases':rows,'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows),'model_inference_calls':0,'paid_calls':0,'hashes':hashes,'code_drift':[n for n,h in hashes.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]}
    (out/'http-matrix.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['failed']==0 and not result['code_drift'] else 1)
