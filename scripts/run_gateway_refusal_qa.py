"""Independent native HTTP refusal QA. No agent executor, paid provider or source installs."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import time
from run_native_hermes_probe import isolated_environment, pinned_source
from gateway_process import OwnedGatewayProcess

ROOT=Path(__file__).resolve().parents[1]
CASES=(('missing-auth',401,'gateway_auth_failed'),('wrong-auth',401,'gateway_auth_failed'),
       ('unicode-auth',401,'gateway_auth_failed'),('invalid-idempotency-size',400,'invalid_idempotency_key'),
       ('invalid-idempotency-space',400,'invalid_idempotency_key'),
       ('native-owner-first-refusal',409,'permission_denied'),
       ('native-owner-keyed-retry-refusal',409,'permission_denied'),
       ('unknown-status-no-creation',404,'run_not_found'),('unknown-stop-no-creation',404,'run_not_found'))
PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'


def read_object(path: Path) -> dict:
    if path.stat().st_size>131072:raise ValueError('Oversized receipt')
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise ValueError('Receipt must be an object')
    return value


def validate_refusal(value: dict,nonce: str,pid: int) -> list[str]:
    try:
        errors=[]
        if value['result']!='PASS':errors.append('worker failed')
        if type(pid) is not int or pid<=0 or type(value['pid']) is not int or value['pid']!=pid or value['nonce']!=nonce:errors.append('wrong identity')
        if value['source_commit']!=PIN:errors.append('wrong source')
        rows=value['cases']
        if tuple((r['name'],r['http_status'],r['code']) for r in rows)!=CASES:errors.append('missing duplicate or wrong refusal case')
        if any(type(r['http_status']) is not int or r['no_admission_or_active_run_change'] is not True for r in rows):errors.append('unproven refusal')
        for k,n in [('passed',9),('failed',0),('model_inference_calls',0)]:
            if type(value[k]) is not int or value[k]!=n:errors.append('invalid '+k)
        expected={'native_admissions':0,'memory_run_statuses':0,'active_runs':0}
        for k in ('before','after'):
            if value[k]!=expected or any(type(n) is not int for n in value[k].values()):errors.append('unexpected state change')
        for k in ('native_store_identity_shared','owned_cleanup_completed'):
            if value[k] is not True:errors.append('unproven '+k)
        if value['unexpected_network_connections']!=[]:errors.append('unexpected network')
        if type(value['runtime_socketpair_connections']) is not int or value['runtime_socketpair_connections']<0:errors.append('invalid runtime socket count')
        if value['aiohttp_version']!='3.14.3':errors.append('unexpected dependency version')
        for k in ('full_gateway_lifecycle_tested','os_sandbox_claimed'):
            if value[k] is not False:errors.append('unsupported claim')
        return errors
    except (KeyError,TypeError,ValueError,AttributeError):return ['malformed refusal evidence']


def db_counts(path: Path) -> dict:
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
        db.execute('PRAGMA query_only=ON')
        return {'integrity':db.execute('PRAGMA integrity_check').fetchone()[0],
                'admissions':db.execute('SELECT count(*) FROM session_admissions').fetchone()[0],
                'tool_messages':db.execute("SELECT count(*) FROM messages WHERE role='tool'").fetchone()[0],
                'journal_mode':db.execute('PRAGMA journal_mode').fetchone()[0], 'read_only':True}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',required=True,type=Path)
    p.add_argument('--python',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();source=pinned_source(ROOT,args.source_workspace);out=args.output.absolute()
    runtime=(args.source_workspace.resolve()/'runtime').resolve()
    if not out.resolve().is_relative_to(runtime) or not args.python.resolve().is_relative_to(runtime):raise ValueError('Use project runtime paths')
    if out.exists() or not args.python.is_file():raise ValueError('Fresh output and prepared interpreter required')
    files=[ROOT/'scripts/qa/hermes_gateway_refusals.py',Path(__file__),ROOT/'scripts/gateway_process.py']
    hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
    out.mkdir(parents=True);env=isolated_environment(out);nonce=secrets.token_hex(16)
    result={'scope':'independent programmatic native Gateway/Authority/API HTTP refusals, no model execution',
            'source_commit':PIN,'nonce':nonce,'errors':[],'files_sha256':hashes}
    child=None;owned=None;timed_out=False
    try:
        with (out/'stdout.txt').open('w',encoding='utf-8') as stdout,(out/'stderr.txt').open('w',encoding='utf-8') as stderr:
            child=subprocess.Popen([str(args.python),'-I','-B',str(files[0]),str(source),str(out),nonce],cwd=out,env=env,
                stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            deadline=time.monotonic()+45
            while not (out/'qa-ready.json').exists():
                if child.poll() is not None:raise RuntimeError('QA exited before ready')
                if time.monotonic()>deadline:raise TimeoutError('No QA readiness')
                time.sleep(.025)
            ready=read_object(out/'qa-ready.json')
            if ready.get('nonce')!=nonce or type(ready.get('port')) is not int or not 0<ready['port']<65536:raise ValueError('Invalid ready receipt')
            owned=OwnedGatewayProcess(child,ready.get('pid'));result['ownership_chain']=owned.chain
            result['launcher_pid']=child.pid;result['native_pid']=owned.pid
            (out/'qa-continue.json').write_text(json.dumps(ready),encoding='utf-8')
            child.wait(timeout=45)
    except (TimeoutError,subprocess.TimeoutExpired):timed_out=True;result['errors'].append('timeout')
    except Exception as error:result['errors'].append(type(error).__name__+': '+str(error))
    finally:
        if child is not None:
            if child.poll() is None:
                if owned:owned.kill()
                child.kill()
            child.wait(timeout=5);result['exit_code']=child.returncode
            result['launcher_reaped']=True
            if child.returncode!=0:result['errors'].append('nonzero native exit')
        if owned:
            result['native_reaped']=owned.wait(5)
            if not result['native_reaped']:
                owned.kill();result['errors'].append('native worker outlived launcher')
            owned.close()
        else:result['errors'].append('ownership not established')
    result['timed_out']=timed_out
    if not result['errors']:
        value=read_object(out/'receipt.json');result['receipt']=value
        result['errors'].extend(validate_refusal(value,nonce,result['native_pid']))
        result['database']=db_counts(out/'profile/state.db')
        if result['database']['integrity']!='ok' or result['database']['admissions']!=0 or result['database']['tool_messages']!=0:result['errors'].append('unwanted persistent effect')
    after={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files}
    if after!=hashes:result['errors'].append('QA program drift')
    pinned_source(ROOT,args.source_workspace)
    result['result']='FAIL' if result['errors'] else 'PASS'
    (out/'independent-refusals.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 1 if result['errors'] else 0

if __name__=='__main__':raise SystemExit(main())
