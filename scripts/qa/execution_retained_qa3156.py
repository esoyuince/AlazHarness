"""Read-only corroboration of EXISTING native execution runs; never starts a worker.
The native report is required, but actual SQLite counters/tool rows are re-read
independently. Private config credentials and tool content never enter output.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[2]
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
REQUIRED_PROGRAMS=frozenset(('packages/claw-hermes/execution_budget.py','packages/claw-hermes/execution_boundary.py','packages/claw-hermes/host_gate_plugin.py','packages/claw-hermes/host-gate-client.mjs','scripts/run_native_execution_gate.py','scripts/native_execution_client.mjs','scripts/execution_model_fixture.py','scripts/native_execution_sdk.py','scripts/execution_gateway_worker.py','scripts/run_gateway_gap_qa.py','config/execution-gate/source-lock.json','scripts/native_gateway_worker.py','scripts/gateway_process.py','scripts/run_native_host_gate.py','scripts/run_native_hermes_probe.py','packages/claw-hermes/host_gate.py','packages/claw-hermes/hermes-runs.mjs'))
SCENARIOS={'normal','provider-limit','tool-limit','denied-write','sdk-retry-limit','summary','unknown-price'}

def require(ok,reason):
    if not ok:raise ValueError(reason)

def digest(value):
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def filehash(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_programs(programs,root):
    require(type(programs) is dict and REQUIRED_PROGRAMS<=set(programs),'incomplete measured program set')
    for name,sha in programs.items():
        require(type(name) is str and type(sha) is str and len(sha)==64,'malformed measured program')
        path=root/name
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),'escaping program path')
        require(filehash(path)==sha,'measured program changed: '+name)

def validate_client(client,scenario,nonce):
    require(type(nonce) is str and len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce),'invalid client nonce')
    require(type(client) is dict and client.get('nonce')==nonce,'wrong client receipt identity')
    if scenario=='sdk-retry-limit':
        require(client=={'success':False,'exception':'PermissionDeniedError','error_code':'provider_attempt_limit','nonce':nonce,'sdk_invocations':1},'SDK retry not specifically denied')
    if scenario=='unknown-price':require(client.get('refusal')=='host_http_404','missing guarded endpoint refusal not proven')

def check_run(directory:Path,source_workspace:Path) -> dict:
    directory=directory.resolve();runtime=(source_workspace.resolve()/'runtime').resolve()
    require(directory.is_relative_to(runtime) and directory!=runtime,'not a project test directory')
    report_path=directory/'execution-result.json'
    require(report_path.is_file() and report_path.stat().st_size<16_777_216,'missing or oversized receipt')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    scenario=report['scenario'];require(scenario in SCENARIOS,'unsupported scenario')
    require(report['result']=='PASS' and report['errors']==[] and report['code_drift']==[] and report['fixture_errors']==[],'native result not accepted')
    require(report['source_commit']==PIN,'unqualified upstream source')
    for field in ('paid_calls','inference_calls'):
        require(type(report[field]) is int and report[field]==0,'nonzero or malformed inference field')
    receipt_hash=filehash(report_path)
    validate_programs(report['product_sha256'],ROOT)
    private=json.loads((directory/'client-private.json').read_text(encoding='utf-8'))
    validate_client(report['client'],scenario,private['nonce'])
    require(report['client_exit']==0,'client process did not succeed')
    for prefix in ('', 'restart_') if scenario=='normal' else ('',):
        ready=report[prefix+'ready'];end=report[prefix+'exit'];shutdown=end['shutdown']
        require(ready['state']=='ready' and ready['profile_bound'] is True,'unverified native profile')
        require((ready['runner'],ready['adapter'],ready['authority'])==('gateway.run.GatewayRunner','gateway.platforms.api_server.APIServerAdapter','gateway.session_authority.SessionAuthority'),'non-native class')
        require(ready['pid']==end['native_pid']==shutdown['pid'] and ready['nonce']==end['nonce']==shutdown['nonce'],'mismatched native lifetime')
        require(end['native_reaped'] is True and end['launcher_reaped'] is True and end['exit_code']==0 and end['forced'] is False,'unclean native exit')
        require(shutdown['lifecycle_completed'] is True and shutdown['native_result'] is True,'native shutdown missing')
        chain=end['ownership_chain'];require(chain[0]==ready['pid'] and chain[-1]==end['launcher_pid'],'unowned process chain')
    if scenario=='normal':
        require(report['restart_ready']['epoch']>report['ready']['epoch'] and report['restart_ready']['instance_id']!=report['ready']['instance_id'],'no fresh owner')
        require(report['restart_no_refund'] is True,'restart exposure unproven')
    profile=directory/'profile';require(not profile.is_symlink() and profile.resolve().is_relative_to(directory),'escaping profile')
    config=json.loads((profile/'config.yaml').read_text(encoding='utf-8'))
    policy=config['plugins']['entries']['alaz-host-gate']['settings']['execution']['policy']
    state=profile/'state.db';before=filehash(state)
    with closing(sqlite3.connect(state.as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        db.execute('PRAGMA query_only=ON');require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','bad SQLite integrity')
        epoch=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        admissions=db.execute('SELECT request_id,status,outcome FROM session_admissions').fetchall()
        messages=db.execute('SELECT role,tool_name,content FROM messages').fetchall()
        rows=[(key,json.loads(value)) for key,value in db.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.execution.*' ORDER BY key")]
    require(filehash(state)==before,'database changed while reading')
    last=report['restart_ready'] if scenario=='normal' else report['ready']
    require(tuple(epoch or ())==(last['epoch'],last['instance_id']),'retained runtime owner differs')
    require([[k,v] for k,v in rows]==report['budget_store'],'retained budget differs from receipt')
    claims=[v for k,v in rows if k.startswith('alaz.execution.claim.v1.')]
    configurations=[v for k,v in rows if k.startswith('alaz.execution.config.v1.')]
    providers=[c for c in claims if c['kind']=='provider'];reads=[c for c in claims if c['kind']=='read_file']
    tool_results=[m for m in messages if m[0]=='tool'];user_results=[m for m in messages if m[0]=='user']
    expected_calls=0 if scenario=='unknown-price' else 1 if scenario in ('provider-limit','sdk-retry-limit') else 2
    require(len(report['wire_calls'])==len(providers)==expected_calls,'wire/claim count mismatch')
    require(len(admissions)==(0 if scenario in ('unknown-price','sdk-retry-limit') else 1),'unexpected admission count')
    if scenario=='unknown-price':
        require(not rows and not messages,'unknown tariff executed or created budget')
        reserved_tokens=reserved_cost=0
    else:
        require(len(configurations)==1 and len(claims)==len(providers)+len(reads),'invalid budget shape')
        cfg=configurations[0];tokens=policy['input_ceiling_tokens']+policy['output_ceiling_tokens']
        cost=(policy['input_ceiling_tokens']*policy['input_rate_microusd_per_million']+policy['output_ceiling_tokens']*policy['output_rate_microusd_per_million']+999999)//1000000
        for row in claims+configurations:
            require(row['digest']==digest({k:v for k,v in row.items() if k!='digest'}),'unsealed budget row')
            require(row['policy']==digest(policy),'wrong policy binding')
            require(row['scope']==cfg['scope'] and row['binding']==cfg['binding'],'mixed budget ownership')
        for row in claims:
            require(type(row['tokens']) is int and row['tokens']==(tokens if row['kind']=='provider' else 0),'wrong token reservation')
            require(type(row['costMicrousd']) is int and row['costMicrousd']==(cost if row['kind']=='provider' else 0),'wrong cost reservation')
        expected={'providerCalls':len(providers),'toolCalls':len(reads),'reservedTokens':len(providers)*tokens,'reservedCostMicrousd':len(providers)*cost}
        for key,value in expected.items():require(type(cfg[key]) is int and cfg[key]==value,'wrong retained '+key)
        require(cfg['providerCalls']<=policy['max_provider_calls'] and cfg['toolCalls']<=policy['max_tool_calls'],'call allowance exceeded')
        require(cfg['reservedTokens']<=policy['total_token_limit'] and cfg['reservedCostMicrousd']<=policy['total_cost_microusd'],'exposure allowance exceeded')
        reserved_tokens,reserved_cost=cfg['reservedTokens'],cfg['reservedCostMicrousd']
    if scenario in ('normal','summary','provider-limit'):
        marker=(directory/'input.txt').read_text(encoding='utf-8').splitlines()[0]
        require(len(reads)==1 and len(tool_results)==1 and tool_results[0][1]=='read_file' and marker in tool_results[0][2],'real read marker not retained')
        require(not any(marker in (m[2] or '') for m in user_results),'marker disclosed in initial user input')
    else:require(not reads,'unexpected native read dispatch')
    if scenario in ('denied-write','tool-limit'):
        require(len(tool_results)==1 and ('tool_not_allowed' in tool_results[0][2] or 'tool_attempt_limit' in tool_results[0][2]),'missing actual tool denial result')
    require(not (directory/'must-not-exist.txt').exists(),'forbidden target exists')
    if scenario=='normal':
        run=report['client']['final']['run']
        require(run['status']=='completed' and admissions[0][0]==run['run_id'] and admissions[0][2]=='completed','not a completed native task')
        require(any(m[0]=='assistant' and m[2]==run['output'] for m in messages),'HTTP final and transcript differ')
    if scenario=='summary':
        last_call=report['wire_calls'][-1]
        require(last_call.get('tool_result') is True and (last_call.get('tool_choice')=='none' or last_call.get('tools_present') is False),'summary-only physical call not proven')
    startup=report['startup_seconds'];deadline=report['ready_deadline_seconds']
    require(type(startup) in (int,float) and type(deadline) is int and 0<=startup<=deadline<=180,'invalid startup measurement')
    preload=report['sdk_preload']
    require(preload['nonce']==report['ready']['nonce'] and preload['pid']==report['ready']['pid'] and preload['client_constructed'] is False and preload['model_requests']==0,'SDK setup identity mismatch')
    require(filehash(report_path)==receipt_hash,'source receipt changed during corroboration')
    return {'scenario':scenario,'result':'CORROBORATED','source_receipt_sha256':filehash(report_path),
        'read_only_state_hash_unchanged':True,'native_admissions':len(admissions),
        'provider_claims':len(providers),'read_claims':len(reads),'reported_wire_requests':len(report['wire_calls']),
        'reserved_tokens':reserved_tokens,'reserved_cost_microusd':reserved_cost,
        'startup_seconds':startup,'readiness_deadline_seconds':deadline,
        'sdk_preload_seconds':preload['elapsed_seconds'],'tariff_is_fixture':True,'new_native_execution':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--run-dir',action='append',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    require(not args.output.exists(),'refuse replacing existing observation')
    records=[]
    for directory in args.run_dir:
        try:records.append(check_run(directory,args.source_workspace))
        except Exception as error:records.append({'result':'NOT_CORROBORATED','error_type':type(error).__name__,'reason':str(error)[:200]})
    value={'scope':'retrospective read-only checks; NOT additional native runs or provider-price qualification','records':records,'passed':sum(r['result']=='CORROBORATED' for r in records),'failed':sum(r['result']!='CORROBORATED' for r in records)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:f.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value,indent=2));return bool(value['failed'])
if __name__=='__main__':raise SystemExit(main())
