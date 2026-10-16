"""Verify the new host report on retained HYB005B native stores; no new agent run.

Creates only fresh verification outputs and private CLI input files below runtime.
The source stores, configs, receipts and historical native code are never edited.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from execution_budget import ExecutionPolicy
from host_report import HostReportInspector,render_text
from recovery_inspector import LocalRecoveryContext,PIN,_load
CASES=('normal','provider-limit','tool-limit','denied-write','sdk-retry-limit','summary','unknown-price')
PROGRAMS=('packages/claw-hermes/host_report.py','scripts/inspect_host_report.py',
          'scripts/verify_host_report_retained.py','packages/claw-hermes/recovery_inspector.py',
          'packages/claw-hermes/execution_budget.py')


def require(value,code):
    if not value:raise ValueError(code)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def object_file(path,limit=2097152):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size<=limit,'invalid evidence file')
    obj=_load(path.read_text(encoding='utf-8'),limit);require(type(obj) is dict,'invalid evidence object');return obj


def verify(workspace,out,scenario):
    case=workspace/'runtime/hyb005b-close-3156'/('final-'+scenario)
    receipt=case/'execution-result.json';record=object_file(receipt)
    require(record['source_commit']==PIN and record['scenario']==scenario,'source mismatch')
    require(record['errors']==[] and record['fixture_errors']==[] and record['code_drift']==[],'failed historical execution')
    for name,sha in record['product_sha256'].items():
        rel=Path(name)
        require(not rel.is_absolute() and '..' not in rel.parts and ':' not in name,'invalid historical program path')
        require(digest(ROOT/rel)==sha,'historical execution code changed')
    for stage in ('exit','restart_exit'):
        if stage in record:
            end=record[stage]
            require(end['native_reaped'] is True and end['launcher_reaped'] is True and end['exit_code']==0,'unclosed historical writer')
    home=case/'profile';paths=[home/'state.db',home/'runs_idempotency.db',home/'config.yaml',receipt]
    before={p.name:digest(p) for p in paths};cfg=object_file(home/'config.yaml')
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        epoch,instance=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
    token=cfg['platforms']['api_server']['key'];context=LocalRecoveryContext(home,token,epoch,instance)
    policy=cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']['policy']
    own=out/scenario;own.mkdir();private=own/'private';private.mkdir()
    cc=asdict(context);cc['profile_home']=str(cc['profile_home']);cc.pop('profile_name')
    (private/'context.json').write_text(json.dumps(cc),encoding='utf-8')
    (private/'policy.json').write_text(json.dumps(policy),encoding='utf-8')
    cmd=[sys.executable,'-B',str(ROOT/'scripts/inspect_host_report.py'),'--context',str(private/'context.json'),'--policy',str(private/'policy.json')]
    client=record['client']
    if 'runId' in client:
        with closing(sqlite3.connect((home/'runs_idempotency.db').as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            keys=db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',(context.scope,client['runId'])).fetchall()
        require(len(keys)==1,'missing retained request')
        original={'body':{'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'},
                  'idempotency_key':keys[0][0],'observed':client['final']['run']}
        (private/'request.json').write_text(json.dumps(original),encoding='utf-8')
        cmd+=['--request',str(private/'request.json')]
        direct=HostReportInspector(context,ExecutionPolicy(**policy)).inspect(**original)
    else:
        cmd+=['--scope-only']
        direct=None if scenario=='unknown-price' else HostReportInspector(context,ExecutionPolicy(**policy)).inspect_scope()
    proc=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20)
    require(proc.returncode==(2 if scenario=='unknown-price' else 0),'unexpected report CLI exit')
    require(not proc.stderr,'unexpected report CLI diagnostic')
    report=json.loads(proc.stdout)
    if direct is not None:require(report==direct,'CLI/module mismatch')
    text=render_text(report)
    forbidden=[token,str(home),cfg['plugins']['entries']['alaz-host-gate']['settings']['execution']['provider_bearer']]
    if 'runId' in client:forbidden += [original['idempotency_key'],original['body']['input'],client['final']['run'].get('output','')]
    require(not any(value and value in proc.stdout+text for value in forbidden),'private content leaked')
    require(all(report[k] is False for k in ('writesPerformed','retryAllowed','repairAllowed','executionAllowed')),'report granted authority')
    if scenario=='unknown-price':
        require(report['reportStatus']=='unverified' and report['execution']['available'] is False,'unknown policy accepted')
    else:
        e=report['execution'];claims=[v for k,v in record['budget_store'] if k.startswith('alaz.execution.claim.v1.') and v['kind']=='provider']
        known=[v['usage'] for v in claims if v['usage'] is not None]
        require(e['providerAttempts']['reserved']==len(claims),'reserved attempts mismatch')
        require(e['providerAttempts']['wireDeliveryCount'] is None,'reservation became delivery proof')
        require(e['runAttribution']=='unavailable' and e['attributedToThisRun'] is False,'unproven per-run usage')
        require(e['reservedExposure']['tokens']==sum(x['tokens'] for x in claims),'token exposure mismatch')
        require(e['reservedExposure']['costMicrousd']==sum(x['costMicrousd'] for x in claims),'money exposure mismatch')
        require(e['providerAttempts']['usageUnknown']==len(claims)-len(known),'unknown usage lost')
        if known:
            require(e['observedUsage']['inputTokens']==sum(x['input_tokens'] for x in known),'input usage mismatch')
            require(e['observedUsage']['outputTokens']==sum(x['output_tokens'] for x in known),'output usage mismatch')
        else:require(e['observedUsage']['totalTokens'] is None,'unknown usage turned into zero')
        if 'runId' in client:
            task=report['task'];require(task['nativeStatus']==client['final']['run']['status'],'task status changed')
            require(task['goalAchievementIndependentlyVerified'] is False,'native result became independent goal proof')
        if scenario=='summary':
            require(report['task']['taskSucceeded'] is False and report['task']['completionReason']=='max_iterations_reached(1/1)','summary relabeled success')
            require(report['nativeReportedUsage']['inputTokens']==120 and e['observedUsage']['inputTokens']==240,'summary scopes collapsed')
        if scenario=='sdk-retry-limit':require(report['scopeOnly'] is True and report['task']['classification']=='not_selected','invented SDK task')
    require(before=={p.name:digest(p) for p in paths},'historical evidence modified')
    (own/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (own/'report.txt').write_text(text,encoding='utf-8')
    return {'scenario':scenario,'result':'PASS','mode':'run_and_scope' if 'runId' in client else 'scope_only',
            'native_receipt_sha256':before[receipt.name],'reportStatus':report['reportStatus'],
            'report_sha256':digest(own/'report.json'),'cli_exit':proc.returncode,
            'source_files_unchanged':True,'new_gateway_executions':0,'model_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    workspace=a.source_workspace.resolve();out=a.output.resolve();source=workspace/'runtime/hyb005b-close-3156'
    require(out.is_relative_to(workspace/'runtime') and not out.is_relative_to(source) and not out.exists(),'fresh distinct runtime output required')
    out.mkdir(parents=True);hashes={name:digest(ROOT/name) for name in PROGRAMS};rows=[];errors=[]
    for scenario in CASES:
        try:rows.append(verify(workspace,out,scenario))
        except Exception as exc:errors.append({'scenario':scenario,'type':type(exc).__name__,'reason':str(exc)[:200]})
    drift=[n for n,h in hashes.items() if digest(ROOT/n)!=h]
    result={'scope':'current report/CLI against seven historical native profiles; NOT seven new Gateway runs',
            'checks':rows,'passed':len(rows),'errors':errors,'code_drift':drift,'programs':hashes,
            'new_gateway_executions':0,'inference_calls':0,'paid_calls':0}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 1 if errors or drift or len(rows)!=len(CASES) else 0

if __name__=='__main__':raise SystemExit(main())
