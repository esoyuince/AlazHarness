"""Owned process lifecycle and read-only records for recovery experiments only."""
from __future__ import annotations
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
from gateway_process import OwnedGatewayProcess

ROOT=Path(__file__).resolve().parents[1]


def dump(path: Path,value: dict) -> None:
    import os
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,path)


def snapshot(home: Path,marker: str) -> dict:
    with closing(sqlite3.connect((home/'state.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
        journal=db.execute('PRAGMA journal_mode').fetchone()[0]
        rows=[dict(r) for r in db.execute('SELECT admission_id,request_id,target_session_id,status,outcome,owner_epoch,generation,payload_digest FROM session_admissions ORDER BY seq')]
        messages=[dict(r) for r in db.execute('SELECT role,tool_name,tool_call_id,content FROM messages')]
    with closing(sqlite3.connect((home/'runs_idempotency.db').resolve().as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        db.row_factory=sqlite3.Row
        runs=[dict(r) for r in db.execute('SELECT run_id,fingerprint,status_json FROM run_idempotency')]
        run_integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    for run in runs:run['status']=json.loads(run.pop('status_json')).get('status')
    tools=[m for m in messages if m['role']=='tool']
    finals=[m['content'] or '' for m in messages if m['role']=='assistant' and marker in (m['content'] or '')]
    return {'integrity':integrity,'run_integrity':run_integrity,'journal':journal,'read_only':True,
            'admissions':rows,'runs':runs,'user_count':sum(m['role']=='user' for m in messages),
            'tool_count':len(tools),'read_count':sum(m['tool_name']=='read_file' for m in tools),
            'tool_marker':any(marker in (m['content'] or '') for m in tools),
            'marker_in_user':any(marker in (m['content'] or '') for m in messages if m['role']=='user'),
            'final_digests':[hashlib.sha256(x.encode()).hexdigest() for x in finals]}


class Instance:
    def __init__(self,python: Path,source: Path,out: Path,env: dict,nonce: str,stage: str,phase: str):
        self.out,self.nonce=out,nonce;self.dir=out/stage;self.dir.mkdir()
        self.owned=None;self.child=None;self.info={'stage':stage,'nonce':nonce};self.files=[]
        self.finished=False
        # Archive only our preceding incarnation's known coordination files.
        for name in ('spawn.json','ready.json','shutdown.json','failure.json','stop.json','fault-checkpoint.json'):
            p=out/name
            if p.exists():p.rename(self.dir/('prior-'+name))
        stdout=(self.dir/'stdout.txt').open('w',encoding='utf-8');stderr=(self.dir/'stderr.txt').open('w',encoding='utf-8')
        self.files=[stdout,stderr]
        digest=hashlib.sha256((source/'gateway/platforms/api_server_runs.py').read_bytes()).hexdigest()
        try:
            self.child=subprocess.Popen([str(python),'-I','-B',str(ROOT/'scripts/gateway_recovery_worker.py'),str(source),str(out),nonce,phase,digest],
                    cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            spawn=self.wait_file('spawn.json',15)
            if spawn['nonce']!=nonce:raise RuntimeError('Unowned worker handshake')
            self.owned=OwnedGatewayProcess(self.child,spawn['pid'])
            self.info.update(launcher_pid=self.child.pid,pid=self.owned.pid,chain=self.owned.chain)
            ready=self.wait_file('ready.json',85)
            if ready['nonce']!=nonce or ready['pid']!=self.owned.pid:raise RuntimeError('Readiness mismatch')
            self.info['ready']=ready;dump(self.dir/'ready-observation.json',self.info)
        except BaseException:
            self.finish(hard=True);raise
    def wait_file(self,name: str,seconds: float) -> dict:
        end=time.monotonic()+seconds;p=self.out/name
        while not p.exists():
            if self.child is not None and self.child.poll() is not None:raise RuntimeError('Owned Gateway exited before '+name)
            if time.monotonic()>end:raise TimeoutError('Missing '+name)
            time.sleep(.025)
        return json.loads(p.read_text(encoding='utf-8'))
    def finish(self,hard: bool=False) -> dict:
        if self.finished:return self.info
        self.info['hard_kill']=False
        try:
            if self.owned is not None:
                if hard:
                    if self.owned.wait():raise RuntimeError('Gateway already exited before planned crash')
                    self.owned.kill();self.info['hard_kill']=True
                elif not self.owned.wait():dump(self.out/'stop.json',{'nonce':self.nonce,'pid':self.owned.pid})
                if not self.owned.wait(40):
                    self.owned.kill();self.owned.wait(5)
                    raise RuntimeError('Native Gateway shutdown timed out')
            if self.child is not None:
                try:self.child.wait(8)
                except subprocess.TimeoutExpired:self.child.kill();self.child.wait(5);raise
                self.info['exit_code']=self.child.returncode;self.info['launcher_reaped']=True
            self.info['native_reaped']=bool(self.owned and self.owned.wait())
            shut=self.out/'shutdown.json'
            if shut.exists():self.info['shutdown']=json.loads(shut.read_text(encoding='utf-8'))
            if not hard and (self.info.get('exit_code')!=0 or self.info.get('shutdown',{}).get('native_result') is not True):
                raise RuntimeError('No successful native shutdown')
            return self.info
        finally:
            if self.owned:self.owned.close()
            # When startup failed before ownership, only our direct Popen child may be terminated.
            if self.child is not None and self.child.poll() is None:self.child.kill();self.child.wait(5)
            for file in self.files:file.close()
            self.finished=True;dump(self.dir/'exit-observation.json',self.info)


def client(out: Path,env: dict,base: str,token: str,nonce: str,action: str,*,key: str='',run_id: str='',input_text: str='',pending: bool=False):
    number=len(list(out.glob('client-*-input.json')))
    src=out/f'client-{number:03d}-input.json';dest=out/f'client-{number:03d}-output.json'
    dump(src,{'baseUrl':base,'token':token,'nonce':nonce,'action':action,'key':key,'runId':run_id,'input':input_text})
    command=[shutil.which('node') or 'node',str(ROOT/'scripts/gateway_recovery_client.mjs'),str(src),str(dest)]
    if pending:
        log=(out/f'client-{number:03d}-log.txt').open('w',encoding='utf-8')
        process=subprocess.Popen(command,cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        return process,dest,log
    result=subprocess.run(command,cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=35)
    if result.returncode!=0:raise RuntimeError('Recovery client process failed: '+result.stderr[-500:])
    value=json.loads(dest.read_text(encoding='utf-8'))
    if value.get('nonce')!=nonce or value.get('action')!=action:raise RuntimeError('Client receipt mismatch')
    return value
