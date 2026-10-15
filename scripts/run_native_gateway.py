"""Actual isolated Hermes Gateway integration with a scripted loopback model."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import time
from run_native_hermes_probe import isolated_environment,pinned_source
from gateway_scripted_model import ScriptedModel
from gateway_process import OwnedGatewayProcess
from gateway_fault_relay import LostAckRelay
from gateway_probe_contract import database_evidence,validate

ROOT=Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--python',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',choices=('normal','lost-ack','stop'),default='normal')
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.absolute()
    if not out.resolve().is_relative_to((a.source_workspace/'runtime').resolve()):raise ValueError('Fresh runtime output required')
    if out.exists():raise FileExistsError('Output already exists')
    if not a.python.is_file():raise FileNotFoundError('Prepared Hermes interpreter required')
    out.mkdir(parents=True);env=isolated_environment(out)
    for d in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/d).mkdir()
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),
               OPENAI_API_KEY='alaz-loopback-fixture',NO_PROXY='127.0.0.1,localhost',
               AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',
               XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),
               XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    nonce=secrets.token_hex(16);marker='ALAZ_GATEWAY_'+secrets.token_hex(16)
    fixture=out/'input.txt';fixture.write_text(marker+'\nışık:42\n',encoding='utf-8')
    provider=ScriptedModel(fixture,marker,hold_directory=out if a.scenario=='stop' else None,nonce=nonce);provider.start();port=free_port();token=secrets.token_hex(32)
    relay=None
    if a.scenario=='lost-ack':
        relay=LostAckRelay(port,'gateway-'+nonce);relay.start()
    config={'model':{'provider':'custom','base_url':provider.base_url,'default':'alaz-scripted','context_length':131072,'streaming':False},
       'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},
       'platform_toolsets':{'api_server':['file']},'agent':{'max_turns':3,'api_max_retries':0},
       'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
       'updates':{'check':False},'plugins':{'enabled':[],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0},
       'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},
       'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},
       'terminal':{'backend':'local','cwd':str(out)},'approvals':{'mode':'manual'},
       'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    (out/'profile/config.yaml').write_text(json.dumps(config),encoding='utf-8')
    report={'scope':'native Gateway/Authority/API + real tool, scripted provider','nonce':nonce,'scenario':a.scenario,'errors':[],
            'model_inference_calls':0,'paid_calls':0,'os_sandbox_claimed':False}
    measured=('native_gateway_worker.py','native_gateway_client.mjs','run_native_gateway.py','gateway_scripted_model.py','gateway_fault_relay.py','gateway_process.py','gateway_probe_contract.py')
    hashes={n:hashlib.sha256((ROOT/'scripts'/n).read_bytes()).hexdigest() for n in measured}
    child=None;owned=None;started=time.monotonic()
    try:
        with (out/'gateway.stdout.txt').open('w',encoding='utf-8') as stdout,(out/'gateway.stderr.txt').open('w',encoding='utf-8') as stderr:
            child=subprocess.Popen([str(a.python),'-I','-B',str(ROOT/'scripts/native_gateway_worker.py'),str(source),str(out),nonce],
                                   cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            born=time.monotonic()+10
            while not (out/'spawn.json').exists():
                if child.poll() is not None or time.monotonic()>born:raise RuntimeError('No owned worker handshake')
                time.sleep(.02)
            spawn=json.loads((out/'spawn.json').read_text(encoding='utf-8'))
            if spawn.get('nonce')!=nonce:raise RuntimeError('Wrong spawn identity')
            owned=OwnedGatewayProcess(child,spawn.get('pid'))
            report['ownership_chain']=owned.chain;report['launcher_pid']=child.pid
            deadline=time.monotonic()+90
            while not (out/'ready.json').exists():
                if child.poll() is not None:raise RuntimeError('Native Gateway exited before ready')
                if time.monotonic()>deadline:raise TimeoutError('Gateway readiness deadline')
                time.sleep(.05)
            ready=json.loads((out/'ready.json').read_text(encoding='utf-8'))
            if ready.get('nonce')!=nonce or ready.get('api_port')!=port:raise RuntimeError('Readiness identity mismatch')
            if ready.get('pid')!=owned.pid:raise RuntimeError('Unexpected native process replacement')
            report['ready']=ready
            client={'baseUrl':relay.base_url if relay else f'http://127.0.0.1:{port}','token':token,'input':'Read input.txt using read_file and return its first line.',
                    'key':'gateway-'+nonce,'marker':marker,'nonce':nonce,'scenario':a.scenario,
                    'entered':str(out/'model-entered.json'),'release':str(out/'model-release.json')}
            (out/'client.json').write_text(json.dumps(client),encoding='utf-8')
            run=subprocess.run([shutil.which('node') or 'node',str(ROOT/'scripts/native_gateway_client.mjs'),str(out/'client.json'),str(out/'client-result.json')],
                               cwd=out,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=65)
            (out/'client.stdout.txt').write_text(run.stdout,encoding='utf-8');(out/'client.stderr.txt').write_text(run.stderr,encoding='utf-8')
            report['client_exit']=run.returncode
            if run.returncode:raise RuntimeError('Native adapter client failed')
            report['client']=json.loads((out/'client-result.json').read_text(encoding='utf-8'))
    except Exception as exc:
        report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        if child is not None:
            if child.poll() is None:
                (out/'stop.json').write_text(json.dumps({'nonce':nonce,'pid':owned.pid if owned else child.pid}),encoding='utf-8')
                provider.release.set()
                try:child.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    report['errors'].append('Graceful shutdown unconfirmed')
                    if owned:owned.kill()
                    child.kill()
            child.wait(timeout=5);report['child_exit']=child.returncode;report['child_reaped']=True
            if child.returncode!=0:report['errors'].append('Gateway nonzero exit')
            if owned:
                report['gateway_reaped']=owned.wait(5)
                if not report['gateway_reaped']:
                    owned.kill();report['errors'].append('Native descendant not reaped')
                owned.close()
        provider.close()
        if relay:
            relay.close();report['relay']={'dropped_run':relay.dropped_run,'records':relay.records}
        stop=out/'shutdown.json'
        if stop.is_file():report['shutdown']=json.loads(stop.read_text(encoding='utf-8'))
        report['files_sha256']=hashes
        report['source_commit']=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        report['source_or_program_drift']=any(hashlib.sha256((ROOT/'scripts'/n).read_bytes()).hexdigest()!=s for n,s in hashes.items())
        try:pinned_source(ROOT,a.source_workspace)
        except Exception:report['source_or_program_drift']=True
        if report.get('gateway_reaped') and 'client' in report:
            try:report['database']=database_evidence(out/'profile',report['client']['final'],marker)
            except Exception as exc:report['errors'].append('Native evidence '+type(exc).__name__)
        report['model_calls']=provider.calls;report['fixture_errors']=provider.errors
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        if provider.errors:report['errors'].append('Model fixture errors')
        report['errors'].extend(validate(report))
        report['result']='FAIL' if report['errors'] else 'PASS'
        (out/'suite.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('client','relay','model_calls','database','files_sha256')},indent=2))
    print('NATIVE_COUNTS',json.dumps({'scenario':a.scenario,'model_requests':len(report.get('model_calls',[])),
             'admissions':len(report.get('database',{}).get('admissions',[])),
             'tool_results':report.get('database',{}).get('tool_results')}))
    if report['errors']:
        for name in ['gateway.stderr.txt','gateway.stdout.txt','client.stderr.txt']:
            f=out/name
            if f.exists():print(name,f.read_text(encoding='utf-8')[-5500:])
    return 1 if report['errors'] else 0

if __name__=='__main__':raise SystemExit(main())
