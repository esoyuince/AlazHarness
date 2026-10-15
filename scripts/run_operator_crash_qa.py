"""Actual operator transaction process kills on SYNTHETIC SQLite; no native Gateway tasks."""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
from gateway_process import OwnedGatewayProcess
from run_native_hermes_probe import isolated_environment,pinned_source
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_reconciliation_inspector_qa import StoreFixture,RID,TOKEN

def rows(home):
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True,timeout=3)) as c:
        c.execute('PRAGMA query_only=ON')
        if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Failed integrity')
        return c.execute("SELECT key,value FROM state_meta ORDER BY key").fetchall()

def stage(source,python,home,out,env,phase,sha):
    out.mkdir();nonce=secrets.token_hex(16);owned=None;receipt=None
    with (out/'stdout.txt').open('w',encoding='utf-8') as so,(out/'stderr.txt').open('w',encoding='utf-8') as se:
        proc=subprocess.Popen([str(python),'-I','-B',str(ROOT/'scripts/qa/operator_crash_worker.py'),str(source),str(ROOT),str(home),str(out),nonce,phase,sha],cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=so,stderr=se)
        try:
            deadline=time.monotonic()+30
            while not (out/'spawn.json').exists():
                if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Missing spawn')
                time.sleep(.01)
            spawn=json.loads((out/'spawn.json').read_text());assert spawn['nonce']==nonce
            if phase!='none':
                owned=OwnedGatewayProcess(proc,spawn['pid'])
                while not (out/'checkpoint.json').exists():
                    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Missing operator transaction checkpoint')
                    time.sleep(.01)
                point=json.loads((out/'checkpoint.json').read_text());assert point['pid']==owned.pid and point['nonce']==nonce and point['phase']==phase
                owned.kill();proc.wait(10);assert owned.wait(5)
                assert proc.returncode!=0 and not (out/'result.json').exists()
                receipt={'phase':phase,'launcher_pid':proc.pid,'native_pid':spawn['pid'],'ownership_chain':owned.chain,'checkpoint':point,'exit_code':proc.returncode,'native_reaped':True,'launcher_reaped':True,'result_received':False}
            else:
                proc.wait(30);assert proc.returncode==0
                value=json.loads((out/'result.json').read_text());assert value['nonce']==nonce and value['pid']==spawn['pid']
                receipt={'phase':phase,'exit_code':proc.returncode,'native_result':value['result'],'launcher_reaped':True}
        finally:
            if owned:
                if not owned.wait():owned.kill();owned.wait(5)
                owned.close()
            if proc.poll() is None:proc.kill();proc.wait(5)
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path);p.add_argument('--python',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);root=a.output.resolve();runtime=(a.source_workspace.resolve()/'runtime').resolve()
    if root.exists() or not root.is_relative_to(runtime) or root==runtime:raise ValueError('Fresh runtime required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Prepared project interpreter required')
    root.mkdir(parents=True);product=ROOT/'packages/claw-hermes/operator_resolution.py';sha=hashlib.sha256(product.read_bytes()).hexdigest()
    files=[product,ROOT/'packages/claw-hermes/resolution_receipts.py',ROOT/'packages/claw-hermes/recovery_inspector.py',Path(__file__),ROOT/'scripts/qa/operator_crash_worker.py']
    hashes={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    report={'scope':'actual operator and native maintenance with process kills on synthetic SQLite, NOT Gateway admission runs','source_commit':'eb75627faf532fa6ffbdae59a0d14b0b385fc780','operator_sha256':sha,'program_hashes':hashes,'cases':[],'errors':[],'model_calls':0}
    try:
        for phase in ('before-index','after-commit'):
            case=root/phase;case.mkdir();env=isolated_environment(case);home=case/'profile'
            f=StoreFixture(home);f.sql('DELETE FROM session_admissions');f.sql('DELETE FROM state_meta')
            for sql in ('CREATE TABLE sessions(id TEXT PRIMARY KEY)','CREATE TABLE messages(session_id TEXT,role TEXT,content TEXT)','CREATE TABLE worker_executions(session_id TEXT)'):f.sql(sql)
            departed=subprocess.Popen([sys.executable,'-I','-c','pass'],env=env);departed.wait(timeout=10)
            now=time.time();observed={'run_id':RID,'status':'interrupted'}
            f.sql('UPDATE run_idempotency SET status_json=?,owner_pid=?,created_at=?,updated_at=?',(json.dumps(observed),departed.pid,now,now),runs=True)
            context={'profile_home':str(home),'api_token':TOKEN,'epoch':2,'instance_id':'owner-two'}
            private={'context':context,'query':{'body':f.body,'idempotency_key':f.key,'observed':observed},'command_id':secrets.token_hex(16)}
            (case/'private.json').write_text(json.dumps(private),encoding='utf-8')
            replay_before=(home/'runs_idempotency.db').read_bytes()
            killed=stage(source,a.python,home,case/'first',env,phase,sha)
            after_kill=rows(home);expected_rows=0 if phase=='before-index' else 2
            assert len(after_kill)==expected_rows,(phase,len(after_kill))
            retried=stage(source,a.python,home,case/'repeat',env,'none',sha)
            assert retried['native_result']['status']==('recorded' if phase=='before-index' else 'already_recorded')
            final=rows(home);assert len(final)==2 and (home/'runs_idempotency.db').read_bytes()==replay_before
            if phase=='after-commit':assert after_kill==final
            assert retried['native_result']['taskSucceeded'] is False and retried['native_result']['retryAllowed'] is False
            report['cases'].append({'phase':phase,'first':killed,'repeat':retried,'rows_after_kill':len(after_kill),'rows_final':len(final),'replay_db_unchanged':True,'result':'PASS'})
        assert hashlib.sha256(product.read_bytes()).hexdigest()==sha,'Operator source drift'
    except Exception as e:report['errors'].append(type(e).__name__+': '+str(e))
    report['program_drift']=[f.relative_to(ROOT).as_posix() for f in files if hashlib.sha256(f.read_bytes()).hexdigest()!=hashes[f.relative_to(ROOT).as_posix()]]
    if report['program_drift']:report['errors'].append('Measured program drift')
    report['result']='PASS' if not report['errors'] else 'FAIL'
    (root/'transaction-crash.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));return int(bool(report['errors']))
if __name__=='__main__':raise SystemExit(main())
