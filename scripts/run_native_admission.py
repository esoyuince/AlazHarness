"""Opt-in atomic admission experiments. No installs, external model calls or shared stores."""
from __future__ import annotations
import argparse
from contextlib import closing
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import time
from pi_probe_support import ROOT, check_source, digest, fresh_runtime_path, isolated_env

SCENARIOS=('canonical-write','canonical-input','concurrent-same','concurrent-conflict',
           'snapshot-mutation','legacy-rejected','validation-rollback','fault-before',
           'fault-after','kill-before','kill-after','kill-unsafe-effect')
CUTS={'kill-before':'before-commit','kill-after':'after-commit-before-ack',
      'kill-unsafe-effect':'external-effect-no-result'}


def read_object(path: Path) -> dict:
    if path.stat().st_size>262144:raise ValueError('Oversized receipt')
    obj=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj,dict):raise ValueError('Expected receipt object')
    return obj


def snapshot(work: Path) -> dict:
    # Only read after the exact worker has exited and before another is started.
    with closing(sqlite3.connect((work/'session.sqlite').resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        subs=[json.loads(row[0]) for row in db.execute('SELECT record FROM submissions ORDER BY id LIMIT 1001')]
        documents=[json.loads(row[0]) for row in db.execute('SELECT record FROM documents WHERE retired_at IS NULL LIMIT 1001')]
        if len(documents)>1000:raise ValueError('Unbounded documents')
        bindings=sum(d.get('kind')=='alaz.admission.v1' for d in documents)
        entries=[json.loads(row[0]) for row in db.execute('SELECT record FROM entries ORDER BY id LIMIT 1001')]
        if len(subs)>1000 or len(entries)>1000:raise ValueError('Unbounded fixture')
        value={'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
               'submissions':subs,'binding_count':bindings,'entry_kinds':[x['kind'] for x in entries],
               'read_only':True}
    value['effects']=0
    if (work/'external.sqlite').exists():
        with closing(sqlite3.connect((work/'external.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            value['effects']=db.execute('SELECT count(*) FROM effects').fetchone()[0]
    return value


def validate_boundary(data: dict,scenario: str,nonce: str,pid: int) -> None:
    if (data.get('scenario'),data.get('phase'),data.get('nonce'),data.get('pid'),data.get('boundary'))!=(scenario,'seed',nonce,pid,CUTS.get(scenario)):
        raise ValueError('Unproven owned crash boundary')
    if scenario not in CUTS or type(data.get('rootId')) is not int or data['rootId']<=0:
        raise ValueError('Invalid crash identity')


def validate_case(case: dict) -> list[str]:
    try:
        name=case['scenario'];procs=case['processes'];last=procs[-1]['receipt'];db=case['final_database']
        errors=[]
        if name not in SCENARIOS:return ['unknown scenario']
        expected_stages=['seed','resume'] if name.startswith(('kill-','fault-')) else ['single']
        if [p.get('phase') for p in procs]!=expected_stages:errors.append('wrong phases')
        if (last.get('nonce'),last.get('pid'),last.get('phase'))!=(case.get('nonce'),procs[-1].get('pid'),expected_stages[-1]):errors.append('receipt identity mismatch')
        if last.get('idle') is not True:errors.append('not idle')
        if type(last.get('modelCalls')) is not int or not 0<=last['modelCalls']<=4:errors.append('invalid model counter')
        if last.get('result')!='PASS' or last.get('scenario')!=name or not last.get('checks'):errors.append('missing native assertions')
        for proc in procs:
            if proc.get('reaped') is not True or proc.get('timed_out') is not False or proc.get('error'):errors.append('bad process outcome')
            if not proc.get('intentional_kill') and proc.get('exit_code')!=0:errors.append('nonzero exit')
            if type(proc.get('pid')) is not int or proc['pid']<=0:errors.append('invalid pid')
        if db.get('integrity')!='ok' or db.get('read_only') is not True:errors.append('no independent database proof')
        if type(db.get('binding_count')) is not int or db['binding_count']<0 or type(db.get('effects')) is not int or db['effects']<0:errors.append('invalid independent count')
        expected=2 if name in ('canonical-write','canonical-input') else 1
        if len(db['submissions'])!=expected or db['binding_count']!=(0 if name=='legacy-rejected' else expected):errors.append('admission/binding count mismatch')
        if any(x.get('status')!='done' for x in db['submissions']):errors.append('unfinished native submission')
        if len(procs)==2:
            first,second=procs
            if first['finished']>second['started']:errors.append('overlapping owners')
            if first['pid']==second['pid']:errors.append('new process not proven')
            interim=case['interim_database'];before=name.endswith('before');n=0 if before else 1
            if interim.get('read_only') is not True or interim.get('integrity')!='ok' or len(interim['submissions'])!=n or interim['binding_count']!=n:errors.append('torn admission/fingerprint boundary')
            if not before and db['submissions'][0]['id']!=interim['submissions'][0]['id']:errors.append('lost admitted identity')
            if last.get('reused') is not (not before):errors.append('wrong reopen disposition')
        elif name.startswith(('kill-','fault-')):errors.append('missing restart stage')
        if name in CUTS:
            if procs[0].get('intentional_kill') is not True or procs[0].get('exit_code') in (None,0):errors.append('not a real process interruption')
            validate_boundary(procs[0]['barrier'],name,case['nonce'],procs[0]['pid'])
        if name.startswith('fault-') and procs[0]['receipt'].get('failedClosed') is not True:errors.append('fault not failed closed')
        if name=='kill-unsafe-effect':
            if db['effects']!=1 or case['interim_database']['effects']!=1 or last.get('uncertainEffectPreserved') is not True:errors.append('unsafe effect repeated or hidden')
        elif db['effects']!=0:errors.append('unexpected external effect')
        if name.startswith('concurrent-') and (last.get('accepted'),last.get('conflicts'))!=((10,10) if name=='concurrent-conflict' else (20,0)):errors.append('bad concurrent admission')
        return errors
    except (KeyError,IndexError,TypeError,ValueError,AttributeError):return ['malformed evidence']


def phase(source: Path,work: Path,scenario: str,stage: str,nonce: str) -> dict:
    cmd=[shutil.which('node') or 'node','--import',(source/'packages/coding-agent/src/experimental/source-resolver.ts').as_uri(),str(ROOT/'scripts/native_admission_worker.mjs'),scenario,stage,str(work),nonce,str(source)]
    record={'phase':stage,'started':time.monotonic(),'timed_out':False,'intentional_kill':False,'reaped':False}
    with (work/(stage+'.stdout.txt')).open('w',encoding='utf-8') as out,(work/(stage+'.stderr.txt')).open('w',encoding='utf-8') as err:
        child=subprocess.Popen(cmd,cwd=work,env=isolated_env(work),stdout=out,stderr=err);record['pid']=child.pid
        try:
            if stage=='seed' and scenario in CUTS:
                end=time.monotonic()+12
                while not (work/'ready.json').exists():
                    if child.poll() is not None:raise RuntimeError('Seed exited before barrier')
                    if time.monotonic()>end:raise TimeoutError('No exact barrier')
                    time.sleep(.02)
                barrier=read_object(work/'ready.json');validate_boundary(barrier,scenario,nonce,child.pid)
                if child.poll() is not None:raise RuntimeError('Worker no longer alive')
                record['barrier']=barrier;child.kill();record['intentional_kill']=True
            child.wait(timeout=22)
        except (TimeoutError,subprocess.TimeoutExpired) as error:record.update(timed_out=True,error=type(error).__name__)
        except Exception as error:record['error']=str(error)
        finally:
            if child.poll() is None:child.kill()
            child.wait(timeout=5);record.update(reaped=True,exit_code=child.returncode,finished=time.monotonic())
    receipt=work/(stage+'-receipt.json')
    if receipt.exists():record['receipt']=read_object(receipt)
    (work/(stage+'-process.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace',type=Path,required=True);parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--scenario',choices=SCENARIOS)
    parser.add_argument('--repeats',type=int,choices=(1,2),default=2)
    args=parser.parse_args();source=args.prepared.resolve()/'source';pin=check_source(source)
    prep=read_object(args.prepared/'preparation.json')
    compat=read_object(ROOT/'config/admission-compatibility.lock.json')
    if prep.get('exit_code')!=0 or prep.get('source_commit')!=pin or compat['source_commit']!=pin or digest(source/compat['seam'])!=compat['seam_sha256']:raise ValueError('Unqualified source')
    if digest(source/'package-lock.json')!=prep['package_lock_sha256']:raise ValueError('Dependency lock drift')
    files=['packages/admission/strict-admission.mjs','scripts/native_admission_worker.mjs','scripts/run_native_admission.py','config/admission-compatibility.lock.json']
    source_hashes={p:digest(ROOT/p) for p in files}
    output=fresh_runtime_path(args.source_workspace,args.output);output.mkdir(parents=True)
    cases=[];selected=(args.scenario,) if args.scenario else SCENARIOS
    for repeat in range(1,args.repeats+1):
        for name in selected:
            work=output/f'{repeat}-{name}';work.mkdir();nonce=secrets.token_hex(16)
            (work/'probe.json').write_text(json.dumps({'scenario':name,'nonce':nonce}),encoding='utf-8')
            case={'scenario':name,'repeat':repeat,'nonce':nonce,'processes':[]}
            try:
                stages=('seed','resume') if name.startswith(('kill-','fault-')) else ('single',)
                for stage in stages:
                    proc=phase(source,work,name,stage,nonce);case['processes'].append(proc)
                    if proc.get('error') or (proc['exit_code']!=0 and not proc['intentional_kill']):raise RuntimeError('Invalid process result')
                    if stage=='seed':case['interim_database']=snapshot(work)
                case['final_database']=snapshot(work);case['errors']=validate_case(case)
            except Exception as error:case['errors']=[str(error)]
            case['result']='FAIL' if case['errors'] else 'PASS';cases.append(case)
            print(name,repeat,case['result'],case['errors'],flush=True)
            (work/'case.json').write_text(json.dumps(case,indent=2)+'\n',encoding='utf-8')
            (output/'progress.json').write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
    check_source(source)
    if source_hashes!={p:digest(ROOT/p) for p in files}:raise RuntimeError('Run source changed; acceptance unavailable')
    summary={'scope':'single-owner real Pi native admission and SQLite, controlled model and local effects',
      'source_commit':pin,'scenario_count':len(selected),'repeats':args.repeats,'passed':sum(c['result']=='PASS' for c in cases),
      'failed':sum(c['result']!='PASS' for c in cases),'process_kills':sum(p['intentional_kill'] for c in cases for p in c['processes']),
      'cases':cases,'model_inference_calls':0,'paid_calls':0,'power_loss_tested':False,'multiple_writer_processes_tested':False,
      'production_adoption_accepted':False,'files_sha256':source_hashes}
    (output/'suite.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='cases'},indent=2))
    return 1 if summary['failed'] else 0

if __name__=='__main__':raise SystemExit(main())
