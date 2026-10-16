"""Independent two-store crash characterization with the existing public Gateway worker.

The fault injector holds a rollback-only SQLite RESERVED write lock. It does not
edit rows, replace native methods, or synthesize a successful admission. One
fresh private profile is opened twice, separated by an OS-handle-verified kill.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import http.client
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import threading
import time
from gateway_gap_contract import validate_gap
from gateway_process import OwnedGatewayProcess
from gateway_scripted_model import ScriptedModel
from run_native_hermes_probe import isolated_environment, pinned_source
from run_native_gateway import free_port

ROOT=Path(__file__).resolve().parents[1]
CONTROL_FILES=('spawn.json','ready.json','stop.json','shutdown.json','failure.json')


def load(path: Path) -> dict:
    if path.stat().st_size>262144:raise ValueError('Oversized local record')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise ValueError('Expected object')
    return value


def read_state(home: Path) -> dict:
    result={'read_only':True}
    with closing(sqlite3.connect((home/'state.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        result.update(integrity=db.execute('PRAGMA integrity_check').fetchone()[0],
          admissions=[dict(row) for row in db.execute('SELECT admission_id,request_id,target_session_id,status,outcome,generation,owner_epoch FROM session_admissions ORDER BY seq')],
          messages=db.execute('SELECT count(*) FROM messages').fetchone()[0],
          journal_mode=db.execute('PRAGMA journal_mode').fetchone()[0])
    with closing(sqlite3.connect((home/'runs_idempotency.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        result['reservations']=[dict(row) for row in db.execute('SELECT run_id,status_json,owner_pid,owner_started,fingerprint FROM run_idempotency')]
        result['reservation_integrity']=db.execute('PRAGMA integrity_check').fetchone()[0]
    return result


class Generation:
    def __init__(self,python,source,out,env,number,*,worker=None,ready_timeout=70):
        if type(ready_timeout) is not int or not 1<=ready_timeout<=180:
            raise ValueError('Bounded integer startup timeout required')
        self.out=out;self.logdir=out/('generation-'+str(number));self.logdir.mkdir()
        if number>1:
            previous=out/('generation-'+str(number-1))
            for name in (*CONTROL_FILES,'sdk-preload.json'):
                p=out/name
                if p.exists():
                    target=previous/name
                    if target.exists():raise FileExistsError('Refuse overwriting previous control evidence')
                    p.rename(target)
        self.boot_started=time.monotonic()
        self.nonce=secrets.token_hex(16);self.owned=None;self.closed=False
        self.stdout=(self.logdir/'stdout.txt').open('w',encoding='utf-8')
        self.stderr=(self.logdir/'stderr.txt').open('w',encoding='utf-8')
        self.child=subprocess.Popen([str(python),'-I','-B',str(worker if worker is not None else ROOT/'scripts/native_gateway_worker.py'),str(source),str(out),self.nonce],
            cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=self.stdout,stderr=self.stderr)
        try:
            self.wait_file('spawn.json',20)
            born=load(out/'spawn.json')
            if born.get('nonce')!=self.nonce:raise ValueError('Wrong process nonce')
            self.owned=OwnedGatewayProcess(self.child,born['pid'])
            self.wait_file('ready.json',ready_timeout);self.ready=load(out/'ready.json')
            if self.ready['pid']!=self.owned.pid or self.ready['nonce']!=self.nonce:raise ValueError('Wrong native ready identity')
            if not self.ready['profile_bound']:raise ValueError('Wrong profile')
            self.startup_seconds=round(time.monotonic()-self.boot_started,3)
        except BaseException:
            self.finish(kill=True);raise
    def wait_file(self,name,seconds):
        end=time.monotonic()+seconds
        while not (self.out/name).exists():
            if self.child.poll() is not None:raise RuntimeError('Native child exited before '+name)
            if time.monotonic()>end:raise TimeoutError(name)
            time.sleep(.02)
    def finish(self,*,kill):
        if self.closed:return self.exit
        forced=kill
        try:
            if self.child.poll() is None:
                if kill:
                    if self.owned:self.owned.kill()
                    else:self.child.kill()
                else:
                    tmp=self.out/'stop.json.tmp';tmp.write_text(json.dumps({'nonce':self.nonce,'pid':self.owned.pid}),encoding='utf-8');tmp.replace(self.out/'stop.json')
                try:self.child.wait(timeout=35 if not kill else 10)
                except subprocess.TimeoutExpired:
                    forced=True
                    if self.owned:self.owned.kill()
                    self.child.kill();self.child.wait(timeout=5)
            native_exited=self.owned.wait(5) if self.owned else False
            if self.owned and not native_exited:self.owned.kill();native_exited=self.owned.wait(5)
            shutdown=load(self.out/'shutdown.json') if (self.out/'shutdown.json').exists() else None
            self.exit={'nonce':self.nonce,'launcher_pid':self.child.pid,'native_pid':self.owned.pid if self.owned else None,
              'ownership_chain':self.owned.chain if self.owned else [],'exit_code':self.child.returncode,
              'launcher_reaped':self.child.poll() is not None,'native_reaped':native_exited,'kill_requested':kill,
              'forced':forced,'shutdown':shutdown}
            with (self.logdir/'exit-observation.json').open('x',encoding='utf-8') as record:
                record.write(json.dumps(self.exit,indent=2)+'\n')
            return self.exit
        finally:
            if self.owned:self.owned.close()
            self.stdout.close();self.stderr.close();self.closed=True


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path)
    p.add_argument('--python',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.resolve()
    runtime=(a.source_workspace.resolve()/'runtime').resolve()
    if not out.is_relative_to(runtime) or out==runtime or out.exists():raise ValueError('Fresh runtime output required')
    if not a.python.resolve().is_relative_to(runtime) or not a.python.is_file():raise ValueError('Project prepared interpreter required')
    out.mkdir(parents=True);env=isolated_environment(out)
    for name in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/name).mkdir()
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY='alaz-gap-fixture',NO_PROXY='127.0.0.1,localhost',
      AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',
      XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    fixture=out/'input.txt';fixture.write_text('Unused no-agent fixture\n',encoding='utf-8')
    provider=ScriptedModel(fixture,'not-used');provider.start();port=free_port();token=secrets.token_hex(32)
    config={'model':{'provider':'custom','base_url':provider.base_url,'default':'alaz-scripted','context_length':131072,'streaming':False},
      'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},'platform_toolsets':{'api_server':[]},
      'agent':{'max_turns':1,'api_max_retries':0},'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
      'updates':{'check':False},'plugins':{'enabled':[],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0},
      'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},'memory':{'provider':'none'},
      'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},'terminal':{'backend':'local','cwd':str(out)},
      'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    profile=out/'profile';(profile/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    config_sha=hashlib.sha256((profile/'config.yaml').read_bytes()).hexdigest()
    paths=[Path(__file__),ROOT/'scripts/qa/gateway_gap_client.mjs',ROOT/'scripts/native_gateway_worker.py',ROOT/'scripts/gateway_process.py',ROOT/'scripts/gateway_gap_contract.py',ROOT/'packages/claw-hermes/hermes-runs.mjs']
    hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
    report={'scope':'independent two-store process crash observation; not general recovery acceptance','model_inference_calls':0,'paid_calls':0,'errors':[],
       'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'programs':hashes}
    generations=[];lock=None;thread=None;request={};started=time.monotonic()
    key='gap-'+secrets.token_hex(16);body={'input':'This request must not execute while the native store is write-locked.'}
    def post():
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=18)
        try:
            c.request('POST','/v1/runs',body=json.dumps(body),headers={'Authorization':'Bearer '+token,'Idempotency-Key':key,'Content-Type':'application/json'})
            reply=c.getresponse();request['http_status']=reply.status;reply.read(262144)
        except Exception as exc:request['error_type']=type(exc).__name__
        finally:c.close()
    try:
        first=Generation(a.python,source,out,env,1);generations.append(first);report['first_ready']=first.ready
        lock=sqlite3.connect(profile/'state.db',timeout=2);lock.execute('BEGIN IMMEDIATE')
        assert lock.execute('SELECT count(*) FROM session_admissions').fetchone()[0]==0
        thread=threading.Thread(target=post,daemon=True);thread.start()
        deadline=time.monotonic()+8
        while True:
            barrier=read_state(profile)
            if barrier['reservations']:break
            if time.monotonic()>deadline:raise TimeoutError('No reservation before authority write')
            time.sleep(.015)
        if len(barrier['reservations'])!=1 or barrier['admissions']:raise AssertionError('Not the intended two-store gap')
        report['barrier']=barrier
        report['first_exit']=first.finish(kill=True)
        if not report['first_exit']['native_reaped']:raise RuntimeError('Cannot inspect while native writer remains')
        lock.rollback();lock.close();lock=None
        thread.join(timeout=20)
        if thread.is_alive():raise RuntimeError('Unsettled request thread')
        report['first_request']=dict(request);report['after_crash']=read_state(profile)
        second=Generation(a.python,source,out,env,2);generations.append(second);report['second_ready']=second.ready
        run_id=barrier['reservations'][0]['run_id']
        params={'baseUrl':f'http://127.0.0.1:{port}','token':token,'key':key,'input':body['input'],'runId':run_id,'nonce':second.nonce}
        (out/'client-private.json').write_text(json.dumps(params),encoding='utf-8')
        client=subprocess.run([shutil.which('node') or 'node',str(ROOT/'scripts/qa/gateway_gap_client.mjs'),str(out/'client-private.json'),str(out/'client-result.json')],
          cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=35)
        report['client_exit']=client.returncode
        (out/'client-stderr.txt').write_text(client.stderr,encoding='utf-8')
        if client.returncode:raise RuntimeError('Replay observer failed')
        report['client']=load(out/'client-result.json');report['second_exit']=second.finish(kill=False)
        if not report['second_exit']['native_reaped']:raise RuntimeError('Native recovery writer remains')
        report['after_recovery']=read_state(profile)
        report['profile_config_unchanged']=config_sha==hashlib.sha256((profile/'config.yaml').read_bytes()).hexdigest()
        report['model_requests']=len(provider.calls)
        report['observation']='reservation_replayed_without_canonical_admission' if not report['after_recovery']['admissions'] else 'unexpected_canonical_admission'
        report['product_recovery_accepted']=False
        if report['first_request'].get('http_status')==202:raise AssertionError('Unexpected pre-crash success acknowledgement')
        if report['after_recovery']['admissions'] or report['after_recovery']['messages'] or provider.calls:raise AssertionError('Unexpected job execution')
        if report['client']['replay'].get('run_id')!=run_id or report['client']['replay'].get('replayed') is not True:raise AssertionError('Replay identity mismatch')
        if report['client']['conflict']!='http_409':raise AssertionError('Changed-payload conflict missing')
        if second.ready['epoch']<=first.ready['epoch'] or second.ready['instance_id']==first.ready['instance_id']:raise AssertionError('No new native owner generation')
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        for generation in reversed(generations):
            if not generation.closed:
                try:generation.finish(kill=True)
                except Exception as exc:report['errors'].append('Cleanup '+type(exc).__name__)
        if lock is not None:lock.rollback();lock.close()
        if thread is not None:thread.join(timeout=20)
        provider.close()
    report['model_requests']=len(provider.calls);report['fixture_errors']=provider.errors
    report['source_or_program_drift']=any(hashlib.sha256(x.read_bytes()).hexdigest()!=hashes[str(x.relative_to(ROOT))] for x in paths)
    try:pinned_source(ROOT,a.source_workspace)
    except Exception:report['source_or_program_drift']=True
    if report['source_or_program_drift']:report['errors'].append('Source or program drift')
    report['elapsed_seconds']=round(time.monotonic()-started,3)
    report['errors'].extend(validate_gap(report))
    report['result']='FAIL' if report['errors'] else 'OBSERVATION_CONFIRMED'
    (out/'gap-observation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('programs','barrier','after_crash','after_recovery')},indent=2))
    return 1 if report['errors'] else 0

if __name__=='__main__':raise SystemExit(main())
