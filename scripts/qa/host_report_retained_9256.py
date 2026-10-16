"""Independent report/API/CLI comparisons to retained native records, read-only.

Does not create Gateway runs, change source profiles, invoke a provider, or
qualify actual invoices. Private input files are written only below fresh runtime.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionPolicy
from recovery_inspector import LocalRecoveryContext
from host_report import HostReportInspector,render_text
CASES=('normal','provider-limit','tool-limit','denied-write','summary')
PROGRAMS=('packages/claw-hermes/host_report.py','packages/claw-hermes/recovery_inspector.py',
 'packages/claw-hermes/execution_budget.py','scripts/inspect_host_report.py',
 'scripts/qa/host_report_retained_9256.py')


def require(value,reason):
    if not value:raise ValueError(reason)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def private_write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def check(root:Path,out:Path,scenario:str,expected:dict)->dict:
    case=root/'runtime/hyb005b-close-3156'/('final-'+scenario);home=case/'profile'
    receipt=json.loads((case/'execution-result.json').read_text(encoding='utf-8'))
    require(receipt['result']=='PASS' and not receipt['errors'] and not receipt['code_drift'],'invalid retained receipt')
    require(sha(case/'execution-result.json')==expected['baseline_receipt_sha256'],'oracle record changed')
    paths=(home/'state.db',home/'runs_idempotency.db');before={p.name:sha(p) for p in paths}
    config=json.loads((home/'config.yaml').read_text(encoding='utf-8'))
    policy_dict=config['plugins']['entries']['alaz-host-gate']['settings']['execution']['policy']
    with closing(sqlite3.connect(paths[0].resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as c:
        c.execute('PRAGMA query_only=ON');epoch,instance=c.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
    context_dict={'profile_home':str(home),'api_token':config['platforms']['api_server']['key'],'epoch':epoch,'instance_id':instance}
    context=LocalRecoveryContext(**context_dict)
    with closing(sqlite3.connect(paths[1].resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as c:
        c.execute('PRAGMA query_only=ON');rows=c.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',(context.scope,receipt['client']['runId'])).fetchall()
    require(len(rows)==1,'native key/run binding missing')
    request={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},
             'idempotency_key':rows[0][0],'observed':receipt['client']['final']['run']}
    report=HostReportInspector(context,ExecutionPolicy(**policy_dict)).inspect(**request)
    require(report['reportStatus']=='verified_snapshot','unverified report: '+report.get('reason','unknown'))
    for key in ('writesPerformed','retryAllowed','repairAllowed','executionAllowed'):require(report[key] is False,'unexpected authority')
    e=report['execution'];task=report['task'];native=report['nativeReportedUsage']
    require(task['runId']==expected['task_run_id'] and task['outcome']==expected['task_outcome'],'task identity/outcome mismatch')
    require(task['taskSucceeded'] is expected['task_succeeded'],'native task classification mismatch')
    require(task['goalAchievementIndependentlyVerified'] is False,'unsupported independent success claim')
    require(e['attributedToThisRun'] is False and e['runAttribution']=='unavailable' and e['scope']=='profile_principal','misattributed profile amounts')
    require(report['usageComparison']['comparable'] is False and report['usageComparison']['numericDifference'] is None,'unsupported numeric comparison')
    a=e['providerAttempts'];usage=e['observedUsage'];risk=e['reservedExposure']
    for field,oracle in [('reserved','provider_reservations'),('usageKnown','known_usage_claims'),('usageUnknown','unknown_usage_claims'),('unsettled','unsettled_provider_claims')]:
        require(a[field]==expected[oracle],'claim count mismatch: '+field)
    require(a['wireDeliveryCount'] is None,'ledger claimed physical wire evidence')
    require(e['toolAttempts']['reserved']==expected['read_reservations'],'read reservation mismatch')
    for field,oracle in [('inputTokens','input_tokens'),('outputTokens','output_tokens'),('totalTokens','total_tokens')]:
        require(usage[field]==expected['known_usage_sum'][oracle],'scope usage mismatch: '+field)
        require(native[field]==expected['native_reported_usage'][oracle],'native usage mismatch: '+field)
    require(risk['tokens']==expected['reserved_tokens'] and risk['costMicrousd']==expected['reserved_cost_microusd'],'exposure mismatch')
    require(risk['isInvoice'] is False and risk['actualBilledMicrousd'] is None and risk['automaticRefund'] is False,'unsupported billing claim')
    text=render_text(report);serialized=json.dumps(report)+text
    for secret in (context_dict['api_token'],request['idempotency_key'],request['body']['input'],request['observed']['output']):
        require(secret not in serialized,'private input was echoed')
    work=out/scenario;work.mkdir()
    for name,value in [('context.json',context_dict),('policy.json',policy_dict),('request.json',request)]:private_write(work/name,value)
    cli_results=[]
    for format_name in ('json','text'):
        p=subprocess.run([sys.executable,'-I','-B','-X','utf8',str(ROOT/'scripts/inspect_host_report.py'),
             '--context',str(work/'context.json'),'--policy',str(work/'policy.json'),'--request',str(work/'request.json'),
             '--format',format_name],cwd=work,capture_output=True,text=True,encoding='utf-8',errors='strict',timeout=20)
        require(p.returncode==0 and not p.stderr,'CLI failed')
        require(json.loads(p.stdout)==report if format_name=='json' else p.stdout==text,'CLI/API mismatch')
        private_write(work/('cli-'+format_name+'-receipt.json'),{'exit_code':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest()})
        cli_results.append({'format':format_name,'exit_code':p.returncode,'matches_api':True})
    require(before=={p.name:sha(p) for p in paths},'source DB changed')
    private_write(work/'report.json',report)
    with (work/'report.txt').open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    return {'scenario':scenario,'result':'CORROBORATED','task_outcome':task['outcome'],'native_task_succeeded':task['taskSucceeded'],
      'independent_goal_achievement_verified':False,'scope_provider_reservations':a['reserved'],'scope_known_usage':expected['known_usage_sum'],
      'native_run_usage':expected['native_reported_usage'],'scope_reserved_tokens':risk['tokens'],'scope_reserved_cost_microusd':risk['costMicrousd'],
      'per_run_attribution':False,'wire_count_proven_by_ledger':False,'cli':cli_results,'source_database_bytes_unchanged':True,
      'native_baseline_receipt_sha256':expected['baseline_receipt_sha256'],'report_sha256':sha(work/'report.json'),'new_native_execution':False}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    root=a.source_workspace.resolve();out=a.output.resolve()
    require(out.is_relative_to(root/'runtime') and not out.exists(),'fresh runtime output required');out.mkdir(parents=True)
    oracle=json.loads((ROOT/'evidence/hyb-005c-qa9256/baseline-oracle.json').read_text(encoding='utf-8'))
    expected={x['scenario']:x for x in oracle['observations']};hashes={name:sha(ROOT/name) for name in PROGRAMS}
    results=[];errors=[]
    for scenario in CASES:
        try:results.append(check(root,out,scenario,expected[scenario]));print('CORROBORATED',scenario,flush=True)
        except Exception as e:errors.append({'scenario':scenario,'type':type(e).__name__,'reason':str(e)[:240]});print('NOT_ACCEPTED',scenario,type(e).__name__,flush=True)
    drift=[name for name,h in hashes.items() if sha(ROOT/name)!=h]
    record={'scope':'independent report/API/CLI validation against five existing real native profiles, not new Gateway executions',
      'results':results,'count':len(results),'errors':errors,'hashes':hashes,'code_drift':drift,'paid_calls':0,'inference_calls':0,
      'result':'PASS' if len(results)==len(CASES) and not errors and not drift else 'FAIL'}
    private_write(out/'retained-report-qa.json',record);print(json.dumps({'result':record['result'],'count':len(results),'errors':errors,'code_drift':drift},indent=2))
    return 0 if record['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
