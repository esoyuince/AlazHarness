"""Opt-in Pi Durable tests: real SQLite and parent-owned child kill/reopen, no network models."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
from pi_probe_support import ROOT,check_source,digest,fresh_runtime_path,isolated_env

from pi_durable_contract import SCENARIOS,check_barrier,evaluate_case


def read_object(path: Path) -> dict:
    if path.stat().st_size > 256*1024:raise ValueError('Oversized probe receipt')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Expected a receipt object')
    return data


def effects(work: Path, name: str) -> list:
    p=work/name
    if not p.exists():return []
    if p.stat().st_size > 64*1024:raise ValueError('Unbounded effect log')
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line]


def persisted_state(work: Path) -> dict:
    # Called only AFTER the killed child was reaped, BEFORE recovery starts.
    # This is an independent read, not the agent's account of its own success.
    path=work/'session.sqlite'
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2) as db:
        db.execute('PRAGMA query_only=ON')
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        values={}
        for table in ('entries','tasks','submissions'):
            records=[json.loads(row[0]) for row in db.execute('SELECT record FROM '+table+' ORDER BY id LIMIT 1001')]
            if len(records)>1000:raise ValueError('Database exceeds probe bounds')
            values[table]=records
    return {'integrity':integrity,'read_only':True,'entry_kinds':[r['kind'] for r in values['entries']],
            'tasks':values['tasks'],'submissions':values['submissions']}


def execute(node: str, resolver: Path, worker: Path, work: Path, scenario: str, phase: str, env: dict) -> dict:
    cmd=[node,'--import',resolver.as_uri(),str(worker),scenario,phase]
    info={'phase':phase,'timed_out':False,'killed_at_barrier':False,'ready_received':False,'child_reaped':False}
    started=time.monotonic();info['started_monotonic']=started
    with (work/(phase+'.stdout.txt')).open('w',encoding='utf-8') as out,(work/(phase+'.stderr.txt')).open('w',encoding='utf-8') as err:
        child=subprocess.Popen(cmd,cwd=work,env=env,stdout=out,stderr=err)
        info['pid']=child.pid
        try:
            if phase=='before':
                deadline=time.monotonic()+20
                ready=work/'ready.json'
                while not ready.exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.025)
                if not ready.exists():
                    info['timed_out']=child.poll() is None
                    raise RuntimeError('Child did not reach the intended crash barrier')
                data=read_object(ready)
                if data.get('pid')!=child.pid or data.get('scenario')!=scenario or data.get('phase')!='before':
                    raise RuntimeError('Crash barrier is not from this exact child/scenario')
                issues=check_barrier(data,scenario)
                if issues:raise RuntimeError('Wrong cut: '+', '.join(issues))
                if child.poll() is not None:raise RuntimeError('Child exited before intended crash')
                info['ready_received']=True;info['barrier']=data
                # Terminate only this spawned process, then reap before another opens its DB.
                child.kill();info['killed_at_barrier']=True;child.wait(timeout=10)
            else:child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            info['timed_out']=True
        except Exception as error:
            info['error']=str(error)
        finally:
            if child.poll() is None:child.kill()
            child.wait(timeout=10)
            info['child_reaped']=True;info['exit_code']=child.returncode
            info['finished_monotonic']=time.monotonic()
            info['elapsed_seconds']=round(info['finished_monotonic']-started,3)
            (work/(phase+'.execution.json')).write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    return info


def run_case(node: str,resolver: Path,worker: Path,work: Path,scenario: str) -> dict:
    work.mkdir()
    env=isolated_env(work);env['PI_DURABLE_OUTPUT']=str(work)
    runs=[];snapshot=None
    try:
        if scenario.startswith('crash-'):
            first=execute(node,resolver,worker,work,scenario,'before',env);runs.append(first)
            if not first['killed_at_barrier'] or not first['child_reaped'] or first['timed_out']:
                raise RuntimeError('Unproven crash: recovery will not be launched')
            snapshot=persisted_state(work)
            second=execute(node,resolver,worker,work,scenario,'after',env);runs.append(second)
        else:runs.append(execute(node,resolver,worker,work,scenario,'single',env))
        record=read_object(work/'receipt.json')
        if runs[-1]['exit_code']!=0 or runs[-1]['timed_out'] or record.get('characterization')!='PASS':
            raise RuntimeError('Native assertions did not pass')
        independent={'attempts':len(effects(work,'attempts.jsonl')),'effects':len(effects(work,'effects.jsonl'))}
        if scenario.startswith('crash-'):
            if record.get('attempts')!=independent['attempts'] or record.get('effects')!=independent['effects']:
                raise RuntimeError('Native result disagrees with independent effect log')
        result={'scenario':scenario,'characterization':'PASS','observation':record,'processes':runs,'independent_effect_counts':independent,'database_after_crash':snapshot}
        issues=evaluate_case(result)
        if issues:raise RuntimeError('; '.join(issues))
    except Exception as error:
        result={'scenario':scenario,'characterization':'FAIL','error':str(error),'processes':runs,'database_after_crash':snapshot}
        p=work/'receipt.json'
        if p.exists():result['observation']=read_object(p)
        for phase in ('single','before','after'):
            p=work/(phase+'.stderr.txt')
            if p.exists():print(p.read_text(encoding='utf-8')[-4000:])
    (work/'case.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',choices=SCENARIOS)
    p.add_argument('--repeats',type=int,choices=(1,2),default=1)
    args=p.parse_args();source=args.prepared.resolve()/'source';pin=check_source(source)
    preparation=read_object(args.prepared/'preparation.json')
    if preparation.get('exit_code')!=0 or preparation.get('source_commit')!=pin:raise ValueError('Unqualified preparation')
    if digest(source/'package-lock.json')!=preparation['package_lock_sha256']:raise ValueError('Lock mismatch')
    if not (source/'node_modules/typebox/package.json').is_file():raise ValueError('Dependencies absent; no automatic install')
    node=shutil.which('node')
    if not node:raise RuntimeError('Node is required')
    output=fresh_runtime_path(args.source_workspace,args.output);output.mkdir(parents=True)
    worker=ROOT/'scripts/native_pi_durable_worker.mjs'
    resolver=source/'packages/coding-agent/src/experimental/source-resolver.ts'
    selected=(args.scenario,) if args.scenario else SCENARIOS
    all_results=[]
    for repeat in range(1,args.repeats+1):
        for scenario in selected:
            result=run_case(node,resolver,worker,output/(str(repeat)+'-'+scenario),scenario)
            result['repeat']=repeat;all_results.append(result)
            print(scenario,repeat,result['characterization'],result.get('error',''),flush=True)
            (output/'progress.json').write_text(json.dumps(all_results,indent=2)+'\n',encoding='utf-8')
    check_source(source)
    failures=sum(r['characterization']!='PASS' for r in all_results)
    summary={'scope':'real Pi Durable + node SQLite; faux provider responses and controlled local effect tools',
             'source_commit':pin,'worker_sha256':digest(worker),'runner_sha256':digest(Path(__file__)),'contract_sha256':digest(ROOT/'scripts/pi_durable_contract.py'),
             'scenario_count':len(selected),'repeats':args.repeats,'characterization_passed':len(all_results)-failures,
             'characterization_failed':failures,'adoption_accepted':False,'strict_payload_conflict':'FAIL' if any(r.get('observation',{}).get('strictPayloadConflict') is False for r in all_results) else 'NOT_RUN','model_inference_calls':0,'paid_calls':0,'cases':all_results}
    (output/'suite.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'},indent=2))
    return 1 if failures else 0

if __name__=='__main__':raise SystemExit(main())
