"""Read-only baseline oracle for HYB005C; does not run an agent or call a provider.

Reads the seven retained final HYB005B test profiles. Usage is counted directly
from claim rows. A committed reservation is NOT a confirmed physical request;
wire counts come only from the separately retained native probe receipt.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from recovery_inspector import LocalRecoveryContext,LocalRecoveryInspector,RESULT
CASES=('normal','provider-limit','tool-limit','denied-write','sdk-retry-limit','summary','unknown-price')
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def require(value,reason):
    if not value:raise ValueError(reason)


def read(case:Path)->dict:
    record=case/'execution-result.json'
    require(record.is_file(),'missing native receipt')
    raw=record.read_bytes();r=json.loads(raw)
    require(r['source_commit']==PIN and r['result']=='PASS' and not r['errors'] and not r['code_drift'],'unqualified baseline')
    scenario=r['scenario'];require(scenario in CASES,'unsupported case')
    for key in ('exit','restart_exit'):
        if key not in r:continue
        end=r[key];require(end['native_reaped'] is True and end['launcher_reaped'] is True and end['exit_code']==0,'native writer not proven closed')
    home=case/'profile';paths=[home/'state.db',home/'runs_idempotency.db']
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with closing(sqlite3.connect(paths[0].resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
        epoch,instance=db.execute('SELECT epoch,instance_id FROM runtime_epoch WHERE singleton=1').fetchone()
        rows=[(k,json.loads(v)) for k,v in db.execute("SELECT key,value FROM state_meta WHERE key LIKE 'alaz.execution.%'")]
        admissions=db.execute('SELECT count(*) FROM session_admissions').fetchone()[0]
        native_results={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM state_meta WHERE key LIKE ?',(RESULT+'%',))}
        require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','state integrity')
    config=json.loads((home/'config.yaml').read_text(encoding='utf-8'))
    token=config['platforms']['api_server']['key'];context=LocalRecoveryContext(home,token,epoch,instance)
    prefix='alaz.execution.claim.v1.'+context.scope+'.'
    claims=[v for k,v in rows if k.startswith(prefix)]
    counters=[v for k,v in rows if k=='alaz.execution.config.v1.'+context.scope]
    for row in claims+counters:
        actual=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='digest'},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        require(actual==row['digest'],'invalid claim seal')
    providers=[row for row in claims if row['kind']=='provider'];reads=[row for row in claims if row['kind']=='read_file']
    known=[row for row in providers if row['state']=='settled' and isinstance(row['usage'],dict)]
    summed={'input_tokens':sum(x['usage']['input_tokens'] for x in known),'output_tokens':sum(x['usage']['output_tokens'] for x in known)}
    summed['total_tokens']=sum(summed.values())
    answer={'scenario':scenario,'baseline_receipt_sha256':hashlib.sha256(raw).hexdigest(),'scope':'profile_principal_all_retained_claims',
       'per_run_attribution_supported':False,'confirmed_wire_count_from_ledger':None,'wire_count_only_from_historical_probe':len(r['wire_calls']),
       'provider_reservations':len(providers),'read_reservations':len(reads),'known_usage_claims':len(known),
       'unsettled_provider_claims':sum(x['state']=='reserved' for x in providers),'unknown_usage_claims':len(providers)-len(known),
       'known_usage_sum':summed,'reserved_tokens':sum(x['tokens'] for x in claims),'reserved_cost_microusd':sum(x['costMicrousd'] for x in claims),
       'scope_budget_present':bool(counters),'native_admissions':admissions,'new_native_run':False,'model_calls':0,'writes_to_source':False}
    if counters:
        require(len(counters)==1,'ambiguous budget')
        c=counters[0];require(c['providerCalls']==len(providers) and c['toolCalls']==len(reads),'counter mismatch')
        require(c['reservedTokens']==answer['reserved_tokens'] and c['reservedCostMicrousd']==answer['reserved_cost_microusd'],'exposure mismatch')
    client=r['client']
    if 'runId' in client:
        observed=client['final']['run']
        with closing(sqlite3.connect(paths[1].resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
            db.execute('PRAGMA query_only=ON')
            matches=db.execute('SELECT idempotency_key FROM run_idempotency WHERE scope=? AND run_id=?',(context.scope,client['runId'])).fetchall()
        require(len(matches)==1,'missing run-key binding')
        body={'input':'Use the indicated file tool and report its result.','model':'alaz-scripted'}
        checked=LocalRecoveryInspector(context).inspect(body=body,idempotency_key=matches[0][0],observed=observed)
        require(checked['canonicalVerified'] is True,'baseline task no longer verifiable: '+checked.get('reason','unknown'))
        answer.update(task_outcome=checked.get('outcome'),task_succeeded=checked['taskSucceeded'],retry_allowed=checked['retryAllowed'],native_reported_usage=observed.get('usage'),
          task_run_id=client['runId'],native_result_fields={k:v for k,v in native_results[RESULT+observed['admission_id']]['result'].items() if k in ('completed','partial','failed','interrupted','turn_exit_reason')})
    else:answer.update(task_outcome='no_task_requested' if scenario=='sdk-retry-limit' else 'not_admitted',task_succeeded=False,retry_allowed=False,native_reported_usage=None)
    require(before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'baseline stores changed')
    answer['database_bytes_unchanged']=True
    return answer


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.source_workspace.resolve();base=root/'runtime/hyb005b-close-3156';out=a.output.resolve()
    require(out.is_relative_to(root/'runtime') and not out.exists(),'fresh runtime output required')
    observations=[read(base/('final-'+s)) for s in CASES]
    result={'scope':'independent baseline row summation and existing recovery classification; not new Gateway execution','observations':observations,'count':len(observations),'paid_calls':0}
    with out.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'count':len(observations),'cases':[{k:r[k] for k in ('scenario','provider_reservations','known_usage_claims','task_outcome')} for r in observations]},indent=2))

if __name__=='__main__':main()
