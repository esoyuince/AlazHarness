"""Independent real HTTP refusal checks; no fake Gateway/authority/agent methods."""
import asyncio
from contextlib import suppress
import json
import os
from pathlib import Path
import secrets
import sys
import time
import traceback

source=Path(sys.argv[1]).resolve();work=Path(sys.argv[2]).resolve()
assert work==Path.cwd().resolve() and Path(os.environ['HERMES_HOME']).resolve()==work/'profile'
nonce=sys.argv[3]
assert len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce)
key=secrets.token_hex(32);network=[]
def audit(event,args):
    if event=='socket.connect' and isinstance(args[1],tuple):
        host,port=args[1][:2]
        stack=traceback.extract_stack()
        selfpipe=any(frame.name in ('socketpair','_fallback_socketpair') and Path(frame.filename).name=='socket.py' for frame in stack)
        network.append({'host':host,'port':port,'kind':'runtime_socketpair' if selfpipe else 'http','stack':[Path(x.filename).name+':'+x.name for x in stack[-12:]]})
        if host not in ('127.0.0.1','::1') or port==9:raise PermissionError('Unexpected provider or non-loopback connection blocked')
    if event=='socket.getaddrinfo' and args[0] not in ('127.0.0.1','::1','localhost',None):
        raise PermissionError('Non-loopback DNS blocked')
sys.addaudithook(audit)
os.environ.update(OPENAI_API_KEY='alaz-refusal-no-provider',OPENAI_BASE_URL='http://127.0.0.1:9/v1')
(work/'profile/config.yaml').write_text(json.dumps({
    'model':{'default':'alaz-refusal','provider':'custom','base_url':'http://127.0.0.1:9/v1','context_length':131072},
    'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
    'auxiliary':{'title_generation':{'enabled':False}},'memory':{'provider':'none'},
    'platform_toolsets':{'api_server':[]},'checkpoints':{'enabled':False},
    'security':{'allow_lazy_installs':False},'agent':{'max_iterations':1}}),encoding='utf-8')
sys.path.insert(0,str(source))

async def main():
    import aiohttp
    from gateway.config import GatewayConfig,Platform,PlatformConfig
    from gateway.run import GatewayRunner
    from gateway.platforms.api_server import APIServerAdapter
    from gateway.session_authority import initialize_session_authority
    from gateway.session_contract import Principal
    from gateway.session_local import create_local_session
    runner=GatewayRunner(GatewayConfig(multiplex_profiles=False,loop_watchdog=False,sessions_dir=work/'profile/sessions'))
    adapter=None;rows=[];port=None
    try:
        authority=await initialize_session_authority(runner,profile_id='default',instance_id='qa-'+secrets.token_hex(6))
        adapter=APIServerAdapter(PlatformConfig(enabled=True,extra={'host':'127.0.0.1','port':0,'key':key}))
        adapter.gateway_runner=runner;adapter.set_message_handler(runner._handle_message)
        runner.adapters[Platform.API_SERVER]=adapter
        assert await adapter.connect(),'Native adapter did not connect'
        assert adapter._ensure_session_db() is authority.db,'API not borrowing canonical store'
        port=adapter._site._server.sockets[0].getsockname()[1]
        ready={'pid':os.getpid(),'nonce':nonce,'port':port}
        tmp=work/'qa-ready.tmp';tmp.write_text(json.dumps(ready),encoding='utf-8');os.replace(tmp,work/'qa-ready.json')
        async with asyncio.timeout(12):
            while not (work/'qa-continue.json').exists():await asyncio.sleep(.02)
        assert json.loads((work/'qa-continue.json').read_text(encoding='utf-8'))==ready
        actor=Principal('uid:qa','default',frozenset({'session:create','session:read','session:submit','session:control'}),'socket')
        native=create_local_session(authority,actor,{'request_id':'qa-native','source':'cli','toolsets':[]}).session_id
        base=f'http://127.0.0.1:{port}';headers={'Authorization':'Bearer '+key,'Idempotency-Key':'refusal-key'}
        body={'session_id':native,'input':'This native session must not be adopted by the API.'}
        def counts():
            with authority.db._read_ctx() as db:
                n=db.execute('SELECT count(*) FROM session_admissions').fetchone()[0]
            return {'native_admissions':n,'memory_run_statuses':len(adapter._run_statuses),'active_runs':len(adapter._active_run_tasks)}
        initial=counts()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as client:
            async def case(name,method,path,expected,expected_code=None,**kwargs):
                before=counts()
                async with client.request(method,base+path,**kwargs) as r:
                    raw=await r.text()
                    try:value=json.loads(raw)
                    except ValueError:value={}
                    code=value.get('error',{}).get('code') if isinstance(value,dict) else None
                    assert r.status==expected,(name,r.status,code,raw[:100])
                    if expected_code:assert code==expected_code,(name,code)
                after=counts();assert before==after,(name,before,after)
                rows.append({'name':name,'http_status':r.status,'code':code,'no_admission_or_active_run_change':True})
            await case('missing-auth','POST','/v1/runs',401,'gateway_auth_failed',json=body)
            await case('wrong-auth','POST','/v1/runs',401,'gateway_auth_failed',json=body,headers={'Authorization':'Bearer wrong-test-value'})
            await case('unicode-auth','POST','/v1/runs',401,'gateway_auth_failed',json=body,headers={'Authorization':'Bearer test-şifre'})
            await case('invalid-idempotency-size','POST','/v1/runs',400,'invalid_idempotency_key',json=body,headers={**headers,'Idempotency-Key':'a'*256})
            await case('invalid-idempotency-space','POST','/v1/runs',400,'invalid_idempotency_key',json=body,headers={**headers,'Idempotency-Key':'a b'})
            await case('native-owner-first-refusal','POST','/v1/runs',409,'permission_denied',json=body,headers=headers)
            await case('native-owner-keyed-retry-refusal','POST','/v1/runs',409,'permission_denied',json=body,headers=headers)
            unknown='run_'+'f'*32
            await case('unknown-status-no-creation','GET','/v1/runs/'+unknown,404,headers=headers)
            await case('unknown-stop-no-creation','POST','/v1/runs/'+unknown+'/stop',404,headers=headers,json={})
        assert initial==counts()
        facts={'result':'PASS','scope':'native GatewayRunner SessionAuthority APIServerAdapter real HTTP refusal boundary; zero agent execution',
               'source_commit':'eb75627faf532fa6ffbdae59a0d14b0b385fc780','pid':os.getpid(),'nonce':nonce,'cases':rows,'passed':len(rows),'failed':0,
               'native_store_identity_shared':True,'before':initial,'after':counts(),'model_inference_calls':0,
               'unexpected_network_connections':[n for n in network if n['port']!=port and n['kind']!='runtime_socketpair'],
               'runtime_socketpair_connections':sum(n['kind']=='runtime_socketpair' for n in network),
               'aiohttp_version':aiohttp.__version__,'full_gateway_lifecycle_tested':False,'os_sandbox_claimed':False}
        assert not facts['unexpected_network_connections'],facts['unexpected_network_connections']

    finally:
        if adapter is not None:
            await adapter.cancel_background_tasks()
            await adapter.disconnect()
        pending=runner._shutdown_executor(drain_timeout=5)
        assert pending==0,'Gateway executor still alive'
        runner.session_store.close_all_db_handles();runner.close_all_session_db_handles()
    facts['owned_cleanup_completed']=True
    (work/'receipt.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8');print(json.dumps(facts))

async def bounded():
    async with asyncio.timeout(45):await main()

asyncio.run(bounded())
