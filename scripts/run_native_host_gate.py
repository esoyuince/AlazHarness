"""Opt-in actual Hermes plugin/Gateway host-gate probe; model service is scripted.

Uses the existing public-lifecycle worker and owned process manager. No provider
inference, dependency install, native source edit or personal profile is involved.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import time
from run_native_hermes_probe import isolated_environment,pinned_source
from run_native_gateway import free_port
from run_gateway_gap_qa import Generation
from gateway_scripted_model import ScriptedModel
from gateway_fault_relay import LostAckRelay

ROOT=Path(__file__).resolve().parents[1]
PROGRAMS=('packages/claw-hermes/host_gate.py','packages/claw-hermes/host_gate_plugin.py',
    'packages/claw-hermes/host-gate-client.mjs','packages/claw-hermes/hermes-runs.mjs',
    'scripts/run_native_host_gate.py','scripts/native_host_gate_client.mjs','scripts/native_gateway_worker.py',
    'scripts/gateway_process.py','scripts/run_gateway_gap_qa.py','scripts/gateway_fault_relay.py',
    'config/host-gate/source-lock.json')


def snapshot(home:Path) -> dict:
    with closing(sqlite3.connect((home/'state.db').as_uri()+'?mode=ro',uri=True)) as db:
        db.execute('PRAGMA query_only=ON');db.row_factory=sqlite3.Row
        admissions=[dict(x) for x in db.execute('SELECT request_id,status,outcome FROM session_admissions')]
        messages=[dict(x) for x in db.execute('SELECT role,tool_name,content FROM messages')]
        rows=[(k,json.loads(v)) for k,v in db.execute("SELECT key,value FROM state_meta WHERE key GLOB 'alaz.host_gate.*'")]
        integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    return {'admissions':admissions,'messages':messages,'gate_rows':rows,'integrity':integrity}


def install_probe_plugin(home:Path,policy:dict):
    """Fresh test-profile linking shim; native discovery still owns register(ctx)."""
    plugin=home/'plugins/alaz-host-gate';plugin.mkdir(parents=True)
    (plugin/'plugin.yaml').write_text('name: alaz-host-gate\nversion: 0.1.0\nkind: standalone\nlicense: MIT\ndescription: Alaz one-use host dispatch gate\n',encoding='utf-8')
    loader=('import sys\nfrom pathlib import Path\n'
        f'PRODUCT=Path({str(ROOT/"packages/claw-hermes")!r})\n'
        'def register(ctx):\n'
        '    sys.path.insert(0,str(PRODUCT))\n'
        '    try:\n'
        '        from host_gate_plugin import register as actual_register\n'
        '        actual_register(ctx)\n'
        '    finally:\n'
        '        if sys.path[0]==str(PRODUCT):sys.path.pop(0)\n')
    (plugin/'__init__.py').write_text(loader,encoding='utf-8')
    return {'manifest_sha256':hashlib.sha256((plugin/'plugin.yaml').read_bytes()).hexdigest(),
        'entrypoint_sha256':hashlib.sha256(loader.encode()).hexdigest(),'method':'normal enabled user-plugin discovery; test shim points at the measured product checkout'}


def run_client(out:Path,env:dict,params:dict,*,relay_callback=None):
    stage=params['mode'];config=out/(stage+'-client-private.json');result=out/(stage+'-client-result.json')
    config.write_text(json.dumps(params),encoding='utf-8')
    with (out/(stage+'-client.stdout.txt')).open('w',encoding='utf-8') as stdout,(out/(stage+'-client.stderr.txt')).open('w',encoding='utf-8') as stderr:
        child=subprocess.Popen([shutil.which('node') or 'node',str(ROOT/'scripts/native_host_gate_client.mjs'),str(config),str(result)],
            cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:
            deadline=time.monotonic()+70
            while child.poll() is None:
                if time.monotonic()>deadline:raise TimeoutError('Owned client deadline')
                if relay_callback:relay_callback()
                time.sleep(.03)
            if child.returncode!=0:raise RuntimeError('Host client nonzero exit; see local stderr')
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
    data=json.loads(result.read_text(encoding='utf-8'))
    if data.get('nonce')!=params['nonce'] or data.get('result')!='PASS':raise ValueError('Unbound client result')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--python',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--scenario',choices=('normal','missing-plugin','invalid-policy','lost-ack'),default='normal')
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.resolve();runtime=(a.source_workspace/'runtime').resolve()
    if not out.is_relative_to(runtime) or out==runtime or out.exists():raise ValueError('Fresh project runtime output required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Prepared project interpreter required')
    out.mkdir(parents=True);env=isolated_environment(out)
    for name in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/name).mkdir()
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY='alaz-loopback-fixture',
        NO_PROXY='127.0.0.1,localhost',AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',
        XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    marker='HOST_GATE_'+secrets.token_hex(16);nonce=secrets.token_hex(16);request_id=secrets.token_hex(16)
    fixture=out/'input.txt';fixture.write_text(marker+'\nışık:42\n',encoding='utf-8')
    provider=ScriptedModel(fixture,marker);provider.start();port=free_port();token=secrets.token_hex(32)
    policy={'allowed_models':['alaz-scripted'],'max_issued':4,'max_dispatches':1,'validity_seconds':300}
    if a.scenario=='invalid-policy':policy['allowed_models']=[]
    config={'model':{'provider':'custom','base_url':provider.base_url,'default':'alaz-scripted','context_length':131072,'streaming':False},
      'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},
      'platform_toolsets':{'api_server':['file']},'agent':{'max_turns':3,'api_max_retries':0},
      'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
      'plugins':{'enabled':[] if a.scenario=='missing-plugin' else ['alaz-host-gate'],
         'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0,
         'entries':{'alaz-host-gate':{'settings':{'policy':policy}}}},
      'updates':{'check':False},'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},
      'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},
      'terminal':{'backend':'local','cwd':str(out)},'approvals':{'mode':'manual'},'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    profile=out/'profile';(profile/'config.yaml').write_text(json.dumps(config),encoding='utf-8')
    plugin=install_probe_plugin(profile,policy) if a.scenario!='missing-plugin' else None
    hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in PROGRAMS}
    report={'scope':'real plugin discovery, public Gateway, native SessionDB writer, actual read_file; scripted model',
       'scenario':a.scenario,'errors':[],'product_sha256':hashes,'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
       'plugin_install':plugin,'model_inference_calls':0,'paid_calls':0,'os_sandbox_claimed':False,'model_budget_enforced':False}
    generations=[];relay=None;started=time.monotonic()
    try:
        first=Generation(a.python,source,out,env,1);generations.append(first);report['first_ready']=first.ready
        params={'baseUrl':f'http://127.0.0.1:{port}','token':token,'mode':a.scenario,'requestId':request_id,'marker':marker,'nonce':nonce,
            'permitFile':str(out/'relay-permit.json'),'relayFile':str(out/'relay-ready.json'),
            'droppedFile':str(out/'relay-dropped-seen.json'),'runFile':str(out/'relay-run.json')}
        def advance_relay():
            nonlocal relay
            if relay is None and (out/'relay-permit.json').exists():
                permission=json.loads((out/'relay-permit.json').read_text(encoding='utf-8'))
                if permission['nonce']!=nonce:raise ValueError('Foreign relay request')
                relay=LostAckRelay(port,permission['key'],path='/alaz/host/v1/dispatch');relay.start()
                (out/'relay-ready.json').write_text(json.dumps({'nonce':nonce,'url':relay.base_url}),encoding='utf-8')
            if relay is not None and relay.dropped_run and not (out/'relay-run.json').exists():
                (out/'relay-run.json').write_text(json.dumps({'nonce':nonce,'runId':relay.dropped_run}),encoding='utf-8')
        report['client']=run_client(out,env,params,relay_callback=advance_relay if a.scenario=='lost-ack' else None)
        report['first_exit']=first.finish(kill=False)
        if report['first_exit']['exit_code']!=0 or not report['first_exit']['native_reaped']:raise RuntimeError('Unclean initial shutdown')
        before=snapshot(profile);report['before_restart']=before
        if a.scenario in ('normal','lost-ack'):
            assert len(before['admissions'])==1 and before['admissions'][0]['outcome']=='completed'
            tools=[m for m in before['messages'] if m['role']=='tool'];assert len(tools)==1 and marker in tools[0]['content']
            assert len(provider.calls)==2 and not provider.errors
            second=Generation(a.python,source,out,env,2);generations.append(second);report['second_ready']=second.ready
            report['restart_client']=run_client(out,env,params|{'mode':'restart','key':report['client']['permit']['idempotencyKey'],'runId':report['client']['final']['run']['run_id']})
            report['second_exit']=second.finish(kill=False)
            after=snapshot(profile);report['after_restart']=after
            assert before==after and len(provider.calls)==2
            assert second.ready['epoch']>first.ready['epoch'] and second.ready['instance_id']!=first.ready['instance_id']
            assert report['second_exit']['exit_code']==0 and report['second_exit']['native_reaped']
            intents=[v for k,v in after['gate_rows'] if k.startswith('alaz.host_gate.intent.v1.')]
            counters=[v for k,v in after['gate_rows'] if k.startswith('alaz.host_gate.config.v1.')]
            assert len(intents)==len(counters)==1 and intents[0]['dispatchState']=='consumed'
            assert counters[0]['issued']==counters[0]['spent']==1
        else:
            assert not before['admissions'] and not before['messages'] and not before['gate_rows'] and not provider.calls
        if relay:report['relay']={'records':relay.records,'dropped_run':relay.dropped_run}
    except Exception as exc:report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        for generation in reversed(generations):
            if not generation.closed:
                try:report['cleanup_exit']=generation.finish(kill=False)
                except Exception as exc:report['errors'].append('Cleanup '+type(exc).__name__)
        if relay:relay.close()
        provider.close()
    report['model_requests']=len(provider.calls);report['fixture_errors']=provider.errors
    report['code_drift']=[n for n,h in hashes.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]
    if report['code_drift'] or provider.errors:report['errors'].append('Code drift or model fixture error')
    report['elapsed_seconds']=round(time.monotonic()-started,3);report['result']='FAIL' if report['errors'] else 'PASS'
    (out/'native-host-gate.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('before_restart','after_restart','client','restart_client','product_sha256')},indent=2))
    if report['errors']:
        for p in out.glob('generation-*/stderr.txt'):print(p.name,p.read_text(encoding='utf-8')[-5000:])
        for p in out.glob('*client.stderr.txt'):print(p.name,p.read_text(encoding='utf-8')[-5000:])
    return bool(report['errors'])

if __name__=='__main__':raise SystemExit(main())
