"""Read-only post-run checks of real execution probes; this launches no Gateway."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import re
import sqlite3
from pathlib import Path

SCENARIOS=('normal','provider-limit','tool-limit','denied-write','sdk-retry-limit','summary','unknown-price')
ROOT=Path(__file__).resolve().parents[1]
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def digest(value):
    return hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!='digest'},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def require(condition,reason):
    if not condition:raise ValueError(reason)


def verify_exit(ready,exit_record,*,allow_blocked_network=False):
    require(type(ready['pid']) is int and ready['pid']>0,'native pid')
    require(ready['state']=='ready' and ready['profile_bound'] is True and ready['api_host']=='127.0.0.1','native readiness')
    require((ready['runner'],ready['authority'],ready['adapter'])==('gateway.run.GatewayRunner','gateway.session_authority.SessionAuthority','gateway.platforms.api_server.APIServerAdapter'),'native classes')
    require(type(exit_record['exit_code']) is int and exit_record['exit_code']==0,'nonzero exit')
    require(exit_record['forced'] is False and exit_record['kill_requested'] is False,'forced close')
    require(exit_record['native_reaped'] is True and exit_record['launcher_reaped'] is True,'live owned process')
    require(exit_record['native_pid']==ready['pid'] and exit_record['nonce']==ready['nonce'],'process identity')
    chain=exit_record['ownership_chain']
    require(chain and chain[0]==ready['pid'] and chain[-1]==exit_record['launcher_pid'] and len(set(chain))==len(chain),'ownership chain')
    shutdown=exit_record['shutdown']
    require(shutdown['native_result'] is True and shutdown['lifecycle_completed'] is True,'native lifecycle')
    require(shutdown['pid']==ready['pid'] and shutdown['nonce']==ready['nonce'],'shutdown identity')
    blocked=shutdown['nonloopback_attempts_blocked']
    require(type(blocked) is int and blocked>=0,'invalid network counter')
    require(blocked==0 or allow_blocked_network is True,'blocked external attempts: strict clean-network check failed')
    return blocked


def verify(case:Path, scenario:str, *, check_current=True,allow_blocked_network=False):
    require(scenario in SCENARIOS,'scenario')
    receipt=case/'execution-result.json';raw=receipt.read_bytes();r=json.loads(raw)
    require(r['result']=='PASS' and r['errors']==[] and r['fixture_errors']==[] and r['code_drift']==[],'failed/incomplete/drifted receipt')
    require(r['scenario']==scenario and r['source_commit']==PIN,'source identity')
    require(type(r['client_exit']) is int and r['client_exit']==0,'client exit')
    require(type(r['ready_deadline_seconds']) is int and 1<=r['ready_deadline_seconds']<=180,'bounded startup')
    require(type(r['startup_seconds']) in (int,float) and 0<r['startup_seconds']<=r['ready_deadline_seconds'],'late startup')
    for name in ('paid_calls','inference_calls'):require(type(r[name]) is int and r[name]==0,'unexpected inference')
    require(r['tariff_is_fixture'] is True and r['actual_billing_verified'] is False and r['os_sandbox_claimed'] is False,'unsupported acceptance claim')
    require(r['write_target_exists'] is False and not (case/'must-not-exist.txt').exists(),'unexpected write target')
    hashes=r['product_sha256'];require(type(hashes) is dict and len(hashes)>=16,'unmeasured code')
    for name,value in hashes.items():
        require(type(name) is str and not Path(name).is_absolute() and '..' not in Path(name).parts and re.fullmatch('[a-f0-9]{64}',value),'invalid program digest')
        if check_current:require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,'current code differs: '+name)
    first_ready=r['ready'];blocked=verify_exit(first_ready,r['exit'],allow_blocked_network=allow_blocked_network)
    recorded_exit=json.loads((case/'generation-1/exit-observation.json').read_text(encoding='utf-8'))
    require(recorded_exit==r['exit'],'first exit receipt')
    preload=r['sdk_preload'];require(preload['pid']==first_ready['pid'] and preload['nonce']==first_ready['nonce'] and preload['client_constructed'] is False and preload['model_requests']==0,'SDK prewarm identity')
    if scenario=='normal':
        blocked+=verify_exit(r['restart_ready'],r['restart_exit'],allow_blocked_network=allow_blocked_network)
        require(r['restart_ready']['epoch']>first_ready['epoch'] and r['restart_ready']['instance_id']!=first_ready['instance_id'],'restart generation')
        require(json.loads((case/'generation-2/exit-observation.json').read_text(encoding='utf-8'))==r['restart_exit'],'restart exit receipt')
        require(r['restart_no_refund'] is True,'restart budget')
    home=case/'profile'
    with closing(sqlite3.connect((home/'state.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        actual={'admissions':[dict(x) for x in db.execute('SELECT request_id,status,outcome FROM session_admissions')],
            'messages':[dict(x) for x in db.execute('SELECT role,tool_name,content FROM messages')],
            'gate_rows':[[k,json.loads(v)] for k,v in db.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.host_gate.*'")],
            'integrity':db.execute('PRAGMA integrity_check').fetchone()[0]}
        budget=[[k,json.loads(v)] for k,v in db.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.execution.*' ORDER BY key")]
    require(actual==r['native_store'] and actual['integrity']=='ok','native store changed/mismatch')
    require(budget==r['budget_store'],'budget changed/mismatch')
    for _,row in budget:require(row.get('digest')==digest(row),'budget seal')
    claims=[row for key,row in budget if key.startswith('alaz.execution.claim.')]
    config=[row for key,row in budget if key.startswith('alaz.execution.config.')]
    providers=[row for row in claims if row['kind']=='provider'];reads=[row for row in claims if row['kind']=='read_file']
    wanted=0 if scenario=='unknown-price' else 1 if scenario in ('provider-limit','sdk-retry-limit') else 2
    require(len(providers)==len(r['wire_calls'])==wanted,'wire/reservation count')
    wanted_reads=1 if scenario in ('normal','summary','provider-limit') else 0
    require(len(reads)==wanted_reads and len(claims)==len(providers)+len(reads),'read reservation count')
    if wanted:
        require(len(config)==1 and config[0]['quarantined'] is False,'budget configuration')
        require(config[0]['providerCalls']==wanted and config[0]['toolCalls']==wanted_reads,'budget counters')
        require(config[0]['reservedTokens']==wanted*163840 and config[0]['reservedCostMicrousd']==wanted*196608,'reserved exposure')
        require(all(row['tokens']==163840 and row['costMicrousd']==196608 for row in providers),'reservation amounts')
        require(all(c['path']=='/v1/chat/completions' and c['model']=='alaz-scripted' and type(c['max_tokens']) is int and 0<c['max_tokens']<=32768 for c in r['wire_calls']),'wire model/cap')
    else:require(not config and not claims,'invalid price creates no budget')
    admissions=actual['admissions'];tools=[m for m in actual['messages'] if m['role']=='tool']
    marker=(case/'input.txt').read_text(encoding='utf-8').splitlines()[0]
    client=r['client'];require(re.fullmatch('[a-f0-9]{32}',client['nonce']),'client nonce')
    if scenario in ('sdk-retry-limit','unknown-price'):
        require(not admissions and not tools,'unexpected native admission')
        if scenario=='sdk-retry-limit':
            require(client['success'] is False and client['exception']=='PermissionDeniedError' and client['error_code']=='provider_attempt_limit' and client['sdk_invocations']==1,'wrong SDK refusal')
            require(providers[0]['outcome']=='transport_error' and providers[0]['usage'] is None,'error budget refund')
        else:require(client['refusal']=='host_http_404','wrong missing price refusal')
    else:
        require(len(admissions)==1 and admissions[0]['request_id']==client['runId'] and len(tools)==1,'native run identity')
        require(not any(marker in (m['content'] or '') for m in actual['messages'] if m['role']=='user'),'marker disclosed in prompt')
        if wanted_reads:require(tools[0]['tool_name']=='read_file' and marker in tools[0]['content'],'real read result')
        if scenario in ('denied-write','tool-limit'):
            reason='tool_not_allowed' if scenario=='denied-write' else 'tool_attempt_limit'
            require(reason in tools[0]['content'],'wrong tool refusal')
        if scenario in ('normal','summary'):
            run=client['final']['run'];require(run['status']=='completed' and marker in run['output'],'final result')
            require(admissions[0]['status']=='terminal' and admissions[0]['outcome']=='completed','native terminal outcome')
            require(any(m['role']=='assistant' and m['content']==run['output'] for m in actual['messages']),'stored final response')
    return {'scenario':scenario,'result':'CORROBORATED_WITH_BLOCKED_NETWORK' if blocked else 'CORROBORATED','blocked_nonloopback_attempts':blocked,'clean_network_accepted':blocked==0,'blocked_destination_attribution':'not captured by existing observer' if blocked else None,'receipt_sha256':hashlib.sha256(raw).hexdigest(),
        'startup_seconds':r['startup_seconds'],'startup_budget_seconds':r['ready_deadline_seconds'],
        'provider_wire_requests':wanted,'native_read_claims':wanted_reads,'native_admissions':len(admissions),
        'reserved_tokens':wanted*163840,'reserved_cost_microusd':wanted*196608,
        'read_only_post_run_check':True,'new_native_execution':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',required=True,type=Path);p.add_argument('--prefix',default='sdk-ready-')
    p.add_argument('--scenario',choices=SCENARIOS,action='append');p.add_argument('--output',required=True,type=Path)
    p.add_argument('--allow-blocked-network-observation',action='store_true',help='Keep blocked attempts as explicit non-acceptance warning, never a clean-network PASS')
    a=p.parse_args();require(not a.output.exists(),'output exists')
    selected=a.scenario or list(SCENARIOS)
    require(len(set(selected))==len(selected),'duplicate scenarios')
    results=[verify(a.runtime/(a.prefix+s),s,allow_blocked_network=a.allow_blocked_network_observation) for s in selected]
    with a.output.open('x',encoding='utf-8') as stream:stream.write(json.dumps({'scope':'post-run native SQLite/receipt corroboration, not additional executions','checks':results,'count':len(results)},indent=2)+'\n')
    print(json.dumps({'count':len(results),'results':results}))

if __name__=='__main__':main()
