"""Opt-in native Hermes Gateway -> guarded read_file -> Linux Docker probe.
The provider is scripted. The agent, PluginContext, native file handler, environment
registry, HTTP server, SQLite owner, and (when allowed) Docker executor are real.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from dataclasses import asdict
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
from isolated_tool import ToolSandboxPolicy, OWNER_LABEL
from execution_model_fixture import ExecutionModel
from run_native_host_gate import install_probe_plugin

PIN='eb75627faf532fa6ffbdae59a0d14b0b385fc780'
CASES=('normal','tool-limit','missing-isolation','wrong-backend','missing-image','cancel-native','timeout','live-revoke')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stamp(pid):return Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
def wait_file(path,child,timeout):
    end=time.monotonic()+timeout
    while not path.exists():
        if child.poll() is not None:raise RuntimeError('Native process exited before '+path.name)
        if time.monotonic()>=end:raise TimeoutError(path.name)
        time.sleep(.05)


def snapshot(home):
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        admissions=[dict(x) for x in db.execute('SELECT admission_id,request_id,status,outcome,generation FROM session_admissions')]
        messages=[dict(x) for x in db.execute('SELECT role,tool_name,content FROM messages')]
        rows=[json.loads(x[0]) for x in db.execute("SELECT value FROM state_meta WHERE key LIKE 'alaz.execution.claim.v1.%'")]
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    return {'admissions':admissions,'messages':messages,'claims':rows,'integrity':integrity}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--python',type=Path,required=True)
    p.add_argument('--node',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--image',required=True);p.add_argument('--scenario',choices=CASES,required=True)
    a=p.parse_args();source=a.source.resolve();out=a.output.absolute()
    if os.name!='posix' or out.exists() or not out.is_absolute():raise ValueError('Fresh Linux output required')
    manifest=read(source/'alaz-source-manifest.json')
    if manifest['sourceCommit']!=PIN or not all(digest(source/n)==h for n,h in manifest['files'].items()):raise ValueError('Native source mismatch')
    program_files=[p for folder in ['packages','scripts','config'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.mjs','.ts','.json')]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in program_files}
    out.mkdir(parents=True,mode=0o700)
    for n in ('home','profile','temp','locks','tools','capsules','receipts','xdg-data','xdg-config','xdg-cache'):(out/n).mkdir()
    fixture=out/'input.txt';marker='ISOLATED_NATIVE_'+secrets.token_hex(12)
    fixture.write_text(marker+'\nİkinci satır — α\nthird line\n',encoding='utf-8')
    scenario=a.scenario;model_scenario='isolated-backend-refusal' if scenario in ('missing-image','timeout') else scenario
    provider=ExecutionModel(fixture,marker,model_scenario,out/'must-not-exist.txt');provider.start()
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    token=secrets.token_hex(32);ptoken=secrets.token_hex(32);nonce=secrets.token_hex(16)
    policy={'model':'alaz-scripted','max_provider_calls':3,'max_tool_calls':0 if scenario=='tool-limit' else 1,
       'input_ceiling_tokens':131072,'output_ceiling_tokens':32768,'total_token_limit':491520,
       'total_cost_microusd':1000000,'input_rate_microusd_per_million':1000000,'output_rate_microusd_per_million':2000000}
    isolation={'capsule_root':str(out/'capsules'),'receipt_root':str(out/'receipts'),
       'policy':asdict(ToolSandboxPolicy('sha256:'+'0'*64 if scenario=='missing-image' else a.image,timeout_seconds=1 if scenario=='timeout' else 10)),'use_sudo':True}
    execution={'policy':policy,'upstream_base_url':provider.base_url,'provider_bearer':ptoken,'allowed_read_files':[str(fixture)]}
    if scenario!='missing-isolation':execution['isolated_read']=isolation
    config={'model':{'provider':'custom','base_url':f'http://127.0.0.1:{port}/alaz/provider/v1','default':'alaz-scripted',
         'context_length':163840,'streaming':False,'api_key':ptoken},
       'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},
       'platform_toolsets':{'api_server':['file']},'agent':{'max_turns':3,'api_max_retries':0},
       'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
       'updates':{'check':False},'plugins':{'enabled':['alaz-host-gate'],'disabled':['hermes-achievements','kanban'],
          'auto_update_check_hours':0,'alaz-host-gate':{'policy':{'allowed_models':['alaz-scripted'],'max_issued':4,'max_dispatches':1,'validity_seconds':300},'execution':execution}},
       'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},
       'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},
       'terminal':{'backend':'local' if scenario in ('missing-isolation','wrong-backend') else 'alaz_isolated_read','cwd':'/workspace'},
       'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    # Native plugin configuration contract, identical to the existing HYB005B probe.
    plugin_settings=config['plugins'].pop('alaz-host-gate')
    config['plugins']['entries']={'alaz-host-gate':{'allow_tool_override':True,'settings':plugin_settings}}
    config['approvals']={'mode':'manual'}
    install_probe_plugin(out/'profile',plugin_settings['policy'])
    (out/'profile/config.yaml').write_text(json.dumps(config),encoding='utf-8')
    env={'PATH':'/usr/bin:/bin','HOME':str(out/'home'),'HERMES_HOME':str(out/'profile'),
       'HERMES_RUNTIME_DIR':str(out/'tools'),'HERMES_GATEWAY_LOCK_DIR':str(out/'locks'),
       'TMPDIR':str(out/'temp'),'HERMES_DISABLE_LAZY_INSTALLS':'1','PYTHONDONTWRITEBYTECODE':'1',
       'PYTHONUNBUFFERED':'1','PYTHONIOENCODING':'utf-8','OPENAI_API_KEY':ptoken,
       'NO_PROXY':'127.0.0.1,localhost','AWS_EC2_METADATA_DISABLED':'true','ALAZ_PROBE_PRELOAD_OPENAI':'1',
       'TERM':'dumb','NO_COLOR':'1','LANG':'C.UTF-8',
       'XDG_DATA_HOME':str(out/'xdg-data'),'XDG_CONFIG_HOME':str(out/'xdg-config'),'XDG_CACHE_HOME':str(out/'xdg-cache')}
    record={'scope':'actual Linux Hermes Gateway and native registered file backend, scripted provider; not general isolation',
       'scenario':scenario,'source_commit':PIN,'programs':hashes,'errors':[],'inference_calls':0,'paid_calls':0}
    child=None;clientproc=None;start_token=None;started=time.monotonic();stdout=stderr=None
    try:
        stdout=(out/'stdout.txt').open('wb');stderr=(out/'stderr.txt').open('wb')
        child=subprocess.Popen([str(a.python),'-I','-B',str(ROOT/'scripts/native_gateway_worker.py'),str(source),str(out),nonce],
            cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
        start_token=stamp(child.pid)
        (out/'process.json').write_text(json.dumps({'pid':child.pid,'start_ticks':start_token,'nonce':nonce}))
        wait_file(out/'ready.json',child,180);ready=read(out/'ready.json')
        if ready['pid']!=child.pid or ready['nonce']!=nonce or not ready['profile_bound'] or stamp(child.pid)!=start_token:raise ValueError('Native ownership mismatch')
        record['ready']=ready
        params={'baseUrl':f'http://127.0.0.1:{port}','token':token,'nonce':nonce,'requestId':secrets.token_hex(16),'scenario':scenario,'cancelBarrier':str(out/'cancel-ready.json')}
        (out/'client-private.json').write_text(json.dumps(params))
        with (out/'client-stdout.txt').open('wb') as co,(out/'client-stderr.txt').open('wb') as ce:
            clientproc=subprocess.Popen([str(a.node),str(ROOT/'scripts/native_isolated_client.mjs'),str(out/'client-private.json'),str(out/'client-result.json')],
                cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=co,stderr=ce)
            if scenario in ('cancel-native','live-revoke'):
                deadline=time.monotonic()+35;observed=None
                while time.monotonic()<deadline and clientproc.poll() is None:
                    accepted=out/'client-result.json.accepted'
                    if accepted.exists():
                        identity=read(accepted)
                        assert identity['nonce']==nonce
                        for receipt in (out/'receipts').glob('*/ownership.json'):
                            own=read(receipt)
                            if not (receipt.parent/'prestart-validation.json').exists():continue
                            inspected=subprocess.run(['sudo','-n','/usr/bin/docker','inspect',own['name']],
                                capture_output=True,env={'PATH':'/usr/bin:/bin','HOME':str(out/'home')},timeout=5)
                            if inspected.returncode:continue
                            raw=json.loads(inspected.stdout)[0]
                            assert raw['Name']=='/'+own['name'] and raw['Config']['Labels'].get(OWNER_LABEL)==own['owner']
                            if raw['State']['Running'] is True and raw['State']['Pid']>0:
                                observed={'nonce':nonce,'runId':identity['runId'],'containerId':raw['Id'],
                                    'nativePid':child.pid,'state':'running','hostPid':raw['State']['Pid']}
                                break
                    if observed:break
                    time.sleep(.05)
                if observed is None:raise RuntimeError('No owned running container for cancellation')
                record['running_barrier']=observed
                if scenario=='cancel-native':
                    (out/'cancel-ready.json').write_text(json.dumps(observed))
                else:
                    revoked=json.loads((out/'profile/config.yaml').read_text())
                    revoked['plugins']['entries']['alaz-host-gate']['settings']['execution']['allowed_read_files']=[]
                    (out/'profile/config.yaml').write_text(json.dumps(revoked))
                    record['live_read_permission_revoked']=True
            clientproc.wait(timeout=90)
        record['client_exit']=clientproc.returncode
        if clientproc.returncode:raise RuntimeError('Native client failed; inspect private stderr')
        record['client']=read(out/'client-result.json')
        (out/'stop.json').write_text(json.dumps({'nonce':nonce,'pid':child.pid}))
        child.wait(timeout=40)
        shutdown=read(out/'shutdown.json')
        if child.returncode!=0 or shutdown['pid']!=child.pid or shutdown['nonce']!=nonce or shutdown['native_result'] is not True:raise RuntimeError('Native shutdown unconfirmed')
        record['shutdown']=shutdown
        data=snapshot(out/'profile');record['store_counts']={'admissions':len(data['admissions']),'messages':len(data['messages']),'claims':len(data['claims']),'integrity':data['integrity']}
        tool_messages=[m for m in data['messages'] if m['role']=='tool'];claims=[c for c in data['claims'] if c['kind']=='read_file']
        record['native_tool_results']=len(tool_messages);record['provider_requests']=len(provider.calls)
        bindings=[read(p) for p in (out/'receipts').glob('*/bridge-binding.json')];record['bindings']=bindings
        if scenario in ('missing-isolation','wrong-backend'):
            assert not data['admissions'] and not data['messages'] and not claims and not provider.calls and not bindings
        elif scenario in ('cancel-native','live-revoke'):
            assert len(data['admissions'])==1 and len(claims)==1 and len(bindings)==1
            assert len(provider.calls)==1 and claims[0]['state']=='reserved'
            binding=bindings[0]
            assert binding['outcome']=='cancelled' and binding['exited'] and binding['removed']
            assert binding['containerId']==record['running_barrier']['containerId']
            assert binding['ticket']==claims[0]['ticket'] and binding['runId']==record['client']['runId']
            assert all(marker not in x['content'] for x in tool_messages)
            assert record['client']['final']['run']['status']!='completed'
            record['tool_budget_reservations']=1
            record['cancellation_while_running_confirmed']=True
        else:
            assert len(data['admissions'])==1 and len(tool_messages)==1 and data['admissions'][0]['request_id']==record['client']['runId']
            assert len(provider.calls)==2
            text=tool_messages[0]['content'];record['tool_result_sha256']=hashlib.sha256(text.encode()).hexdigest()
            if scenario=='normal':
                assert marker in text and len(claims)==1 and claims[0]['state']=='settled' and len(bindings)==1
                b=bindings[0];assert b['ticket']==claims[0]['ticket'] and b['runId']==record['client']['runId']
                assert b['admissionId']==data['admissions'][0]['admission_id'] and b['outcome']=='completed' and b['exited'] and b['removed']
                assert record['client']['final']['run']['status']=='completed'
                record['actual_native_marker_read']=True
            elif scenario=='tool-limit':
                assert 'tool_attempt_limit' in text and marker not in text and not claims and not bindings
            else:
                assert 'error' in text and marker not in text and len(claims)==1 and claims[0]['state']=='reserved'
                assert not any(x.get('outcome')=='completed' for x in bindings)
                if scenario=='timeout':
                    assert len(bindings)==1 and bindings[0]['outcome']=='timeout' and bindings[0]['exited'] and bindings[0]['removed']
            record['tool_budget_reservations']=len(claims)
        assert data['integrity']=='ok' and not provider.errors and shutdown['nonloopback_attempts_blocked']==0
    except Exception as exc:
        record['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        if clientproc is not None and clientproc.poll() is None:
            clientproc.kill();clientproc.wait(timeout=10)
        if child is not None and child.poll() is None:
            try:
                if stamp(child.pid)!=start_token:raise RuntimeError('Owned process identity changed')
                (out/'stop.json').write_text(json.dumps({'nonce':nonce,'pid':child.pid}));child.wait(timeout=40)
            except subprocess.TimeoutExpired:
                if child.poll() is None and stamp(child.pid)==start_token:os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=10);record['forced_cleanup']=True
            except Exception as exc:record['errors'].append('cleanup: '+type(exc).__name__)
        if stdout:stdout.close()
        if stderr:stderr.close()
        provider.close()
    record['native_exit']=child.returncode if child is not None else None
    record['native_reaped']=child is not None and child.poll() is not None
    record['fixture_errors']=provider.errors;record['wire_calls']=provider.calls
    record['source_drift']=[n for n,d in hashes.items() if digest(ROOT/n)!=d]
    record['elapsed_seconds']=round(time.monotonic()-started,3)
    record['result']='PASS' if not record['errors'] and not record['source_drift'] and record['native_reaped'] else 'FAIL'
    (out/'isolated-native-result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('programs','client','wire_calls')},indent=2),flush=True)
    return 0 if record['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
