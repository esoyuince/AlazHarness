"""Opt-in true-process-crash Pi Durable probe. Default root CI never runs this module."""
from __future__ import annotations
import argparse
from contextlib import closing
import re
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import time
from pi_probe_support import ROOT, check_source, digest, fresh_runtime_path, isolated_env

SCENARIOS=('duplicate-reopen','before-effect','unsafe-effect','safe-effect','idempotent-effect','after-result','wait-cancel','task-cancel','storage-failure')
CRASH={'before-effect':'admitted-before-model-answer','unsafe-effect':'external-effect-before-native-result','safe-effect':'external-effect-before-native-result','idempotent-effect':'external-effect-before-native-result','after-result':'native-result-before-final-answer'}


def validate_ready(value: dict, scenario: str, nonce: str, pid: int) -> None:
    if scenario not in CRASH or type(pid) is not int or pid<=0 or not isinstance(nonce,str) or re.fullmatch(r'[a-f0-9]{32}',nonce) is None:
        raise ValueError('Invalid expected crash identity')
    if not isinstance(value,dict) or value.get('scenario')!=scenario or value.get('nonce')!=nonce or value.get('pid')!=pid or value.get('phase')!='seed' or value.get('boundary')!=CRASH.get(scenario):
        raise ValueError('Crash boundary identity mismatch')
    if any(type(value.get(k)) is not int or value[k]<0 for k in ('submissionId','rootId')):
        raise ValueError('Missing durable admission identity')


def read_external(work: Path) -> dict:
    with closing(sqlite3.connect((work/'external.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        return {'attempts':db.execute('SELECT count(*) FROM attempts').fetchone()[0],
                'effects':db.execute('SELECT count(*) FROM effects').fetchone()[0],
                'logical_keys':db.execute('SELECT count(DISTINCT task_key) FROM attempts').fetchone()[0]}


def evaluate(scenario: str, phases: list[dict], external: dict) -> list[str]:
    errors=[]
    if scenario not in SCENARIOS or not isinstance(phases,list) or not isinstance(external,dict):
        return ['invalid evaluation input']
    expected_phases=['single'] if scenario in ('wait-cancel','task-cancel') else ['seed','resume']
    if any(not isinstance(p,dict) for p in phases) or [p.get('phase') for p in phases]!=expected_phases:
        return ['missing or out-of-order process phases']
    if any(type(external.get(k)) is not int or external[k]<0 for k in ('attempts','effects','logical_keys')):
        return ['invalid external counters']
    last=phases[-1].get('receipt',{})
    if not isinstance(last,dict):return ['invalid final receipt']
    if any(type(p.get('pid')) is not int or p['pid']<=0 or type(p.get('exit_code')) is not int or
           type(p.get('intentional_kill')) is not bool or type(p.get('timed_out')) is not bool for p in phases):
        return ['invalid process receipts']
    if any(p['intentional_kill'] and not (i==0 and scenario in CRASH) for i,p in enumerate(phases)):
        errors.append('unexpected killed phase')
    if len(phases)==2 and phases[0]['pid']==phases[1]['pid']:
        errors.append('process identity was reused')
    if external['logical_keys']!=(0 if scenario=='duplicate-reopen' else 1):
        errors.append('logical tool identity mismatch')
    if last.get('result')!='PASS' or last.get('scenario')!=scenario:errors.append('missing final receipt')
    if any(p.get('timed_out') for p in phases):errors.append('process timeout')
    if any(p.get('failure') for p in phases):errors.append('phase protocol failure')
    if any(p.get('exit_code')!=0 for p in phases if not p.get('intentional_kill')):errors.append('phase exit failure')
    if last.get('modelInferenceCalls')!=0 or last.get('paidCalls')!=0:errors.append('unexpected model inference')
    if last.get('liveIdle') is not True:errors.append('native runtime not idle')
    if scenario in CRASH:
        if len(phases)!=2 or not phases[0].get('intentional_kill') or phases[0].get('exit_code') in (None,0) or phases[0].get('pid')==phases[-1].get('pid'):errors.append('not a verified new-process restart')
        if last.get('sameSubmissionAfterReopen') is not True:errors.append('lost submission')
        ready=phases[0].get('barrier',{})
        if not isinstance(ready,dict) or any(ready.get(k)!=last.get(k) for k in ('rootId','submissionId')):
            errors.append('reopened admission identity mismatch')
        checkpoint=phases[0].get('post_exit_external',{})
        seed_expected=(0,0) if scenario=='before-effect' else (1,1)
        if not isinstance(checkpoint,dict) or (checkpoint.get('attempts'),checkpoint.get('effects'))!=seed_expected:
            errors.append('independent crash boundary counters mismatch')
    expected={'duplicate-reopen':(0,0),'before-effect':(1,1),'unsafe-effect':(1,1),'safe-effect':(2,2),'idempotent-effect':(2,1),'after-result':(1,1),'wait-cancel':(1,1),'task-cancel':(1,0),'storage-failure':(1,0)}
    if (external.get('attempts'),external.get('effects'))!=expected.get(scenario):errors.append('independent external counter mismatch')
    if (last.get('attempts'),last.get('effects'))!=(external.get('attempts'),external.get('effects')):errors.append('native receipt/counter disagreement')
    if scenario=='duplicate-reopen':
        if last.get('changedPayloadSameId') is not True or last.get('payloadConflictEnforced') is not False or last.get('typeMismatchRejected') is not True:errors.append('upstream dedup behavior changed')
        if last.get('inputChangedPayloadSameId') is not True or last.get('inputOriginalPreserved') is not True or last.get('newModelCallsOnInputRetry')!=0:
            errors.append('input retry differs from pinned contract')
    elif scenario in ('unsafe-effect','storage-failure'):
        if last.get('toolErrors')!=1 or last.get('interrupted') is not True:errors.append('missing explicit interrupted tool result')
    elif scenario in ('before-effect','safe-effect','idempotent-effect','after-result','wait-cancel'):
        if last.get('toolResults')!=1 or last.get('toolErrors')!=0 or last.get('submissionStatus')!='done':errors.append('normal result not committed')
    if scenario=='wait-cancel' and last.get('waitCancelledWorkSurvived') is not True:errors.append('wait cancellation affected work')
    if scenario=='task-cancel' and (last.get('submissionAbort')!='already_placed' or last.get('submissionStatus')!='unanswered' or last.get('toolAborts')!=1):errors.append('task cancellation failed')
    if scenario=='storage-failure':
        first=phases[0].get('receipt',{})
        if not isinstance(first,dict):return errors+['invalid failure-phase receipt']
        if first.get('closedReason')!='failed' or first.get('rejectedAfterFailure') is not True or first.get('pendingWaitRejected') is not True or last.get('phantomWrite') is not False:errors.append('storage failure not closed and recovered')
    return errors


def run_phase(source: Path, work: Path, scenario: str, phase: str, nonce: str) -> dict:
    command=[shutil.which('node') or 'node','--import',(source/'packages/coding-agent/src/experimental/source-resolver.ts').as_uri(),str(ROOT/'scripts/native_durable_sqlite_worker.mjs'),scenario,phase,str(work),nonce]
    started=time.monotonic();killed=False;timed_out=False;ready=None;failure=None
    with (work/(phase+'.stdout.txt')).open('w',encoding='utf-8') as out,(work/(phase+'.stderr.txt')).open('w',encoding='utf-8') as err:
        child=subprocess.Popen(command,cwd=work,env=isolated_env(work),stdout=out,stderr=err)
        try:
            if phase=='seed' and scenario in CRASH:
                deadline=time.monotonic()+12
                while not (work/'ready.json').is_file():
                    if child.poll() is not None:raise RuntimeError('Seed exited before crash boundary')
                    if time.monotonic()>deadline:raise TimeoutError('Crash barrier missing')
                    time.sleep(.02)
                ready=json.loads((work/'ready.json').read_text(encoding='utf-8'))
                validate_ready(ready,scenario,nonce,child.pid)
                if child.poll() is not None:raise RuntimeError('Seed already exited')
                child.kill();killed=True
            child.wait(timeout=15)
        except (TimeoutError,subprocess.TimeoutExpired) as error:
            timed_out=True;failure=type(error).__name__
        except Exception as error:
            failure=type(error).__name__+': '+str(error)
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
            code=child.returncode
    receipt_path=work/(phase+'-receipt.json')
    record={'phase':phase,'pid':child.pid,'exit_code':code,'intentional_kill':killed,'timed_out':timed_out,'elapsed_seconds':round(time.monotonic()-started,3)}
    if failure is not None:record['failure']=failure
    if ready is not None:record['barrier']=ready
    if (work/'external.sqlite').exists():record['post_exit_external']=read_external(work)
    if receipt_path.exists():record['receipt']=json.loads(receipt_path.read_text(encoding='utf-8'))
    elif not killed:record['missing_receipt']=True
    (work/(phase+'-process.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--prepared',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--scenario',choices=SCENARIOS)
    p.add_argument('--repeats',type=int,choices=(1,2),default=1)
    args=p.parse_args();source=args.prepared.resolve()/'source'
    if not source.is_relative_to(args.source_workspace.resolve()/'runtime'):
        raise ValueError('Prepared source must be inside the selected workspace runtime')
    pin=check_source(source)
    output=fresh_runtime_path(args.source_workspace,args.output);output.mkdir(parents=True)
    selected=(args.scenario,) if args.scenario else SCENARIOS
    runs=[]
    try:
        for repeat in range(1,args.repeats+1):
            for scenario in selected:
                work=output/f'{scenario}-{repeat}';work.mkdir();nonce=secrets.token_hex(16)
                (work/'probe.json').write_text(json.dumps({'scenario':scenario,'nonce':nonce}),encoding='utf-8')
                phases=[]
                try:
                    for phase in (('single',) if scenario in ('wait-cancel','task-cancel') else ('seed','resume')):
                        phases.append(run_phase(source,work,scenario,phase,nonce))
                        if phases[-1].get('failure') or (phases[-1]['exit_code']!=0 and not phases[-1]['intentional_kill']):
                            break
                    external=read_external(work);errors=evaluate(scenario,phases,external)
                    record={'scenario':scenario,'repeat':repeat,'phases':phases,'external':external,'errors':errors,'result':'FAIL' if errors else 'PASS'}
                except Exception as error:
                    record={'scenario':scenario,'repeat':repeat,'phases':phases,'result':'FAIL','errors':[str(error)]}
                    print((work/'seed.stderr.txt').read_text(encoding='utf-8')[-3000:] if (work/'seed.stderr.txt').exists() else '')
                runs.append(record);(work/'outcome.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
                print(scenario,repeat,record['result'],record.get('external'),record['errors'],flush=True)
    finally:
        summary={'scope':'native Pi Durable/SQLite local experiments, scripted model, real bounded fixture effects',
                 'source_commit':pin,'worker_sha256':digest(ROOT/'scripts/native_durable_sqlite_worker.mjs'),
                 'runner_sha256':digest(Path(__file__)),'scenario_count':len(selected),'repeats':args.repeats,
                 'passed':sum(r['result']=='PASS' for r in runs),'failed':sum(r['result']!='PASS' for r in runs),
                 'complete':len(runs)==len(selected)*args.repeats,'runs':runs,
                 'adoption_status':'NOT_ACCEPTED_without_host_payload_conflict_and_effect_policy',
                 'power_failure_tested':False,'multi_process_writer_safety_tested':False,'model_inference_calls':0,'paid_calls':0}
        (output/'suite.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='runs'},indent=2))
    return 0 if summary['complete'] and summary['failed']==0 else 1

if __name__=='__main__':raise SystemExit(main())
