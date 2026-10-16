"""Opt-in execution boundary through real public Gateway and native-owned budget."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib,json,sqlite3,secrets,subprocess,time,shutil
from pathlib import Path
from run_native_hermes_probe import isolated_environment,pinned_source
from run_native_gateway import free_port
from run_gateway_gap_qa import Generation
from run_native_host_gate import install_probe_plugin,snapshot
from execution_model_fixture import ExecutionModel
ROOT=Path(__file__).resolve().parents[1]
PROGRAMS=['packages/claw-hermes/execution_budget.py','packages/claw-hermes/execution_boundary.py','packages/claw-hermes/host_gate_plugin.py','packages/claw-hermes/host-gate-client.mjs','scripts/run_native_execution_gate.py','scripts/native_execution_client.mjs','scripts/execution_model_fixture.py','scripts/native_execution_sdk.py','scripts/execution_gateway_worker.py','scripts/run_gateway_gap_qa.py','config/execution-gate/source-lock.json','scripts/native_gateway_worker.py','scripts/gateway_process.py','scripts/run_native_host_gate.py','scripts/run_native_hermes_probe.py','packages/claw-hermes/host_gate.py','packages/claw-hermes/hermes-runs.mjs']

def budget(home):
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as c:
        c.execute('PRAGMA query_only=ON')
        return [(k,json.loads(v)) for k,v in c.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.execution.*' ORDER BY key")]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--python',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ready-timeout-seconds',type=int,choices=range(1,181),default=70,metavar='1..180')
    p.add_argument('--scenario',choices=['normal','provider-limit','tool-limit','denied-write','sdk-retry-limit','summary','unknown-price'],default='normal');a=p.parse_args()
    source=pinned_source(ROOT,a.source_workspace);runtime=(a.source_workspace/'runtime').resolve();out=a.output.resolve()
    if out.exists() or not out.is_relative_to(runtime) or out==runtime:raise ValueError('Fresh runtime directory required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Prepared interpreter required')
    out.mkdir(parents=True);env=isolated_environment(out)
    for d in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/d).mkdir()
    provider_token=secrets.token_hex(32);api_token=secrets.token_hex(32);nonce=secrets.token_hex(16);marker='EXECUTION_'+secrets.token_hex(16)
    env['ALAZ_PROBE_PRELOAD_OPENAI']='1'
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY=provider_token,NO_PROXY='127.0.0.1,localhost',AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    fixture=out/'input.txt';fixture.write_text(marker+'\nışık:42\n',encoding='utf-8');target=out/'must-not-exist.txt'
    provider=ExecutionModel(fixture,marker,a.scenario,target);provider.start();port=free_port();provider_url=f'http://127.0.0.1:{port}/alaz/provider/v1'
    policy={'model':'alaz-scripted','max_provider_calls':1 if a.scenario in ('provider-limit','sdk-retry-limit') else 3,'max_tool_calls':0 if a.scenario=='tool-limit' else 1,
      'input_ceiling_tokens':131072,'output_ceiling_tokens':32768,'total_token_limit':491520,'total_cost_microusd':1000000,'input_rate_microusd_per_million':1000000,'output_rate_microusd_per_million':2000000}
    if a.scenario=='unknown-price':policy['input_rate_microusd_per_million']=None
    host_policy={'allowed_models':['alaz-scripted'],'max_issued':2,'max_dispatches':1,'validity_seconds':300}
    execution={'policy':policy,'upstream_base_url':provider.base_url,'provider_bearer':provider_token,'allowed_read_files':[str(fixture)]}
    config={'model':{'provider':'custom','base_url':provider_url,'api_key':provider_token,'default':'alaz-scripted','context_length':163840,'streaming':False},'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':api_token}},'platform_toolsets':{'api_server':['file']},'agent':{'max_turns':1 if a.scenario=='summary' else 3,'api_max_retries':0},
       'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},'plugins':{'enabled':['alaz-host-gate'],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0,'entries':{'alaz-host-gate':{'allow_tool_override':True,'settings':{'policy':host_policy,'execution':execution}}}},'updates':{'check':False},'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},'terminal':{'backend':'local','cwd':str(out)},'approvals':{'mode':'manual'},'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    home=out/'profile';(home/'config.yaml').write_text(json.dumps(config),encoding='utf-8');install_probe_plugin(home,host_policy)
    hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in PROGRAMS};started=time.monotonic();gens=[]
    report={'scenario':a.scenario,'scope':'native public Gateway + real SDK/registry/file handler + physical HTTP gate; upstream model scripted','source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'errors':[],'product_sha256':hashes,'paid_calls':0,'inference_calls':0,'tariff_is_fixture':True,'actual_billing_verified':False,'os_sandbox_claimed':False}
    try:
        first=Generation(a.python,source,out,env,1,worker=ROOT/'scripts/execution_gateway_worker.py',ready_timeout=a.ready_timeout_seconds);gens.append(first);report['ready']=first.ready;report['startup_seconds']=first.startup_seconds;report['ready_deadline_seconds']=a.ready_timeout_seconds
        report['sdk_preload']=json.loads((out/'sdk-preload.json').read_text(encoding='utf-8'))
        assert report['sdk_preload']['nonce']==first.nonce and report['sdk_preload']['client_constructed'] is False
        c={'nonce':nonce,'baseUrl':f'http://127.0.0.1:{port}','token':api_token,'providerUrl':provider_url,'providerToken':provider_token,'requestId':secrets.token_hex(16),'scenario':a.scenario}
        (out/'client-private.json').write_text(json.dumps(c),encoding='utf-8')
        if a.scenario=='sdk-retry-limit':cmd=[str(a.python),'-I','-B',str(ROOT/'scripts/native_execution_sdk.py'),str(source),str(out/'client-private.json'),str(out/'client-result.json')]
        else:cmd=[shutil.which('node') or 'node',str(ROOT/'scripts/native_execution_client.mjs'),str(out/'client-private.json'),str(out/'client-result.json')]
        process=subprocess.run(cmd,cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=80)
        (out/'client-stderr.txt').write_text(process.stderr,encoding='utf-8');report['client_exit']=process.returncode
        if process.returncode:raise RuntimeError('Native client failed; inspect local stderr')
        report['client']=json.loads((out/'client-result.json').read_text(encoding='utf-8'))
        assert report['client'].get('nonce')==nonce,'Wrong client receipt identity'
        if a.scenario=='normal':
            # Alter only this completed test profile; restore before its restart.
            # No production configuration or personal profile is read or written.
            import http.client
            before_config=(home/'config.yaml').read_bytes()
            before_budget=budget(home);before_wire=len(provider.calls)
            revoked=json.loads(before_config)
            revoked['plugins']['entries']['alaz-host-gate']['settings']['execution']['allowed_read_files']=[]
            checks=[]
            try:
                (home/'config.yaml').write_text(json.dumps(revoked),encoding='utf-8')
                for path,credential,expected in [('/alaz/host/v1/capabilities',api_token,503),('/alaz/provider/v1/models',provider_token,403)]:
                    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
                    try:
                        connection.request('GET',path,headers={'Authorization':'Bearer '+credential})
                        response=connection.getresponse();payload=json.loads(response.read(65536))
                        assert response.status==expected,(path,response.status)
                        checks.append({'path':path,'http_status':response.status,'code':payload.get('error',{}).get('code')})
                    finally:connection.close()
                assert budget(home)==before_budget and len(provider.calls)==before_wire
                report['live_revocation']={'checks':checks,'no_new_reservation':True,'no_new_model_request':True}
            finally:(home/'config.yaml').write_bytes(before_config)
        report['exit']=first.finish(kill=False)
        if report['exit']['exit_code']!=0 or not report['exit']['native_reaped']:raise RuntimeError('Unclean native exit')
        report['native_store']=snapshot(home);report['budget_store']=budget(home)
        claims=[v for k,v in report['budget_store'] if k.startswith('alaz.execution.claim.')]
        provider_claims=[v for v in claims if v['kind']=='provider'];tool_claims=[v for v in claims if v['kind']=='read_file']
        expected_calls=0 if a.scenario=='unknown-price' else 1 if a.scenario in ('provider-limit','sdk-retry-limit') else 2
        assert len(provider.calls)==len(provider_claims)==expected_calls,(len(provider.calls),len(provider_claims),expected_calls)
        assert not target.exists(),'Denied native write created target'
        messages=report['native_store']['messages'];tools=[m for m in messages if m['role']=='tool']
        if a.scenario in ('normal','summary','provider-limit'):
            assert len(tool_claims)==1 and len(tools)==1 and marker in tools[0]['content'],(len(tool_claims),tools)
        else:assert not tool_claims
        if a.scenario in ('denied-write','tool-limit'):assert len(tools)==1 and ('tool_not_allowed' in tools[0]['content'] or 'tool_attempt_limit' in tools[0]['content'])
        if a.scenario=='sdk-retry-limit':assert report['client']=={'success':False,'exception':'PermissionDeniedError','error_code':'provider_attempt_limit','nonce':nonce,'sdk_invocations':1}
        if a.scenario=='unknown-price':assert not claims and not report['native_store']['admissions']
        if a.scenario=='normal':
            assert report['client']['final']['run']['status']=='completed'
            previous=report['budget_store'];second=Generation(a.python,source,out,env,2,worker=ROOT/'scripts/execution_gateway_worker.py',ready_timeout=a.ready_timeout_seconds);gens.append(second);report['restart_ready']=second.ready
            report['restart_exit']=second.finish(kill=False)
            assert report['restart_exit']['exit_code']==0 and report['restart_exit']['native_reaped']
            assert budget(home)==previous and len(provider.calls)==2;report['restart_no_refund']=True
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        for g in reversed(gens):
            if not g.closed:
                try:report['cleanup_exit']=g.finish(kill=False)
                except Exception as exc:report['errors'].append('cleanup '+type(exc).__name__)
        provider.close()
    for index,g in enumerate(gens,1):
        assert g.closed and g.exit['native_reaped'] and g.exit['launcher_reaped'],'Owned process not reaped'
    pinned_source(ROOT,a.source_workspace)
    report['wire_calls']=provider.calls;report['fixture_errors']=provider.errors;report['write_target_exists']=target.exists()
    report['code_drift']=[n for n,h in hashes.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]
    if provider.errors or report['code_drift']:report['errors'].append('Fixture error or program drift')
    report['result']='FAIL' if report['errors'] else 'PASS';report['elapsed_seconds']=round(time.monotonic()-started,3)
    (out/'execution-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('product_sha256','native_store','budget_store','client')},indent=2))
    if report['errors']:
        for f in [*out.glob('generation-*/stderr.txt'),out/'client-stderr.txt']:
            if f.is_file():print(f.name,f.read_text(encoding='utf-8')[-4500:])
    return bool(report['errors'])
if __name__=='__main__':raise SystemExit(main())
