"""Explicit native Gateway kill/reopen qualification. No model inference or automatic replay."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import time
from run_native_hermes_probe import isolated_environment,pinned_source
from run_native_gateway import free_port
from gateway_recovery_model import RecoveryModel
from gateway_recovery_contract import validate
from gateway_recovery_support import Instance,client,dump,snapshot

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('completed','before-model','after-tool','before-reserve','after-reserve')


def run(source: Path,python: Path,out: Path,scenario: str) -> dict:
    out.mkdir(parents=True,exist_ok=False)
    env=isolated_environment(out)
    for d in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/d).mkdir()
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY='alaz-loopback-fixture',
               NO_PROXY='127.0.0.1,localhost',AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',
               NO_COLOR='1',TERM='dumb',XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),
               XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    marker='ALAZ_RECOVERY_'+secrets.token_hex(16);nonce=secrets.token_hex(16);key='recovery-'+nonce
    fixture=out/'input.txt';fixture.write_text(marker+'\nışık:42\n',encoding='utf-8')
    model=RecoveryModel(fixture,marker,{'before-model':1,'after-tool':2}.get(scenario,0));model.start()
    token=secrets.token_hex(32);port=free_port();base=f'http://127.0.0.1:{port}'
    config={'model':{'provider':'custom','base_url':model.base_url,'default':'alaz-scripted','context_length':131072,'streaming':False},
        'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},
        'platform_toolsets':{'api_server':['file']},'agent':{'max_turns':3,'api_max_retries':0},
        'gateway':{'multiplex_profiles':False,'loop_watchdog':False,'api_server':{'max_concurrent_runs':1}},
        'updates':{'check':False},'plugins':{'enabled':[],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0},
        'auxiliary':{'title_generation':{'enabled':False}},'security':{'allow_lazy_installs':False},
        'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},
        'terminal':{'backend':'local','cwd':str(out)},'approvals':{'mode':'manual'},
        'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    dump(out/'profile/config.yaml',config)
    config_hash=hashlib.sha256((out/'profile/config.yaml').read_bytes()).hexdigest()
    files=['gateway_recovery_worker.py','gateway_recovery_client.mjs','gateway_recovery_model.py','gateway_recovery_support.py',
           'run_gateway_recovery.py','native_gateway_worker.py','gateway_process.py','gateway_recovery_contract.py']
    hashes={f:hashlib.sha256((ROOT/'scripts'/f).read_bytes()).hexdigest() for f in files}
    report={'scope':'native public Gateway process kill/reopen with scripted provider; not M1',
            'scenario':scenario,'nonce':nonce,'source_commit':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
            'errors':[],'model_inference_calls':0,'paid_calls':0,'files_sha256':hashes,'os_sandbox_claimed':False,
            'trace_checkpoint':scenario in ('before-reserve','after-reserve')}
    first=second=None;pending=None;start=time.monotonic()
    input_text='Read input.txt using read_file and report its first line.'
    def ask(action,**kwargs):return client(out,env,base,token,nonce,action,key=key,input_text=input_text,**kwargs)
    try:
        first=Instance(python,source,out,env,nonce,'first',scenario if report['trace_checkpoint'] else 'none')
        report['first_ready']=first.info['ready']
        if report['trace_checkpoint']:
            pending=ask('start',pending=True)
            point=first.wait_file('fault-checkpoint.json',12)
            if point.get('nonce')!=nonce or point.get('pid')!=first.owned.pid:raise RuntimeError('Unowned fault checkpoint')
            report['checkpoint']=point;run_id=point['run_id']
        else:
            accepted=ask('start');report['first_admission']=accepted
            if accepted.get('ok') is not True:raise RuntimeError('Native admission failed')
            run_id=accepted['value']['run_id']
            if scenario=='completed':
                final=ask('resume',run_id=run_id);report['first_final']=final
                if not final.get('ok') or final['value']['run']['status']!='completed':raise RuntimeError('Native completion missing')
            elif not model.entered.wait(15):raise RuntimeError('Expected provider boundary was not reached')
        report['run_id']=run_id
        report['first_exit']=first.finish(hard=True)
        model.forbid=scenario!='before-reserve';model.release.set()
        if pending:
            process,dest,log=pending;process.wait(20);log.close()
            if process.returncode!=0:raise RuntimeError('Pending adapter process failed')
            response=json.loads(dest.read_text(encoding='utf-8'));report['lost_response']=response
            if response.get('code')!='write_outcome_unknown' or not response.get('mayHaveBeenAccepted'):raise RuntimeError('Lost request was not unknown')
            pending=None
        report['before_restart']=snapshot(out/'profile',marker)
        report['model_calls_before_restart']=len(model.calls)
        second_nonce=secrets.token_hex(16)
        second=Instance(python,source,out,env,second_nonce,'second','none')
        report['second_ready']=second.info['ready']
        report['recovered_status']=ask('status',run_id=run_id)
        # Explicit same-key reoffer: test operation, never an adapter's hidden retry.
        report['reoffered']=ask('start')
        if scenario=='before-reserve':
            if not report['reoffered'].get('ok'):raise RuntimeError('Unreserved request could not be admitted')
            report['new_run_id']=report['reoffered']['value']['run_id']
            report['new_final']=ask('resume',run_id=report['new_run_id'])
        else:
            report['resumed']=ask('resume',run_id=run_id)
        report['conflict']=client(out,env,base,token,nonce,'start',key=key,input_text=input_text+' changed')
        report['second_exit']=second.finish()
        report['after_restart']=snapshot(out/'profile',marker)
    except Exception as exc:
        report['errors'].append(type(exc).__name__+': '+str(exc))
    finally:
        model.release.set()
        for instance in (first,second):
            if instance is not None and not instance.finished:
                try:instance.finish()
                except Exception as exc:report['errors'].append('Cleanup: '+type(exc).__name__+': '+str(exc))
        if pending:
            proc,dest,log=pending
            if proc.poll() is None:proc.kill()
            proc.wait(5);log.close()
        model.close()
        report['model_calls']=model.calls;report['fixture_errors']=model.errors
        report['profile_config_unchanged']=hashlib.sha256((out/'profile/config.yaml').read_bytes()).hexdigest()==config_hash
        report['program_drift']=any(hashlib.sha256((ROOT/'scripts'/f).read_bytes()).hexdigest()!=h for f,h in hashes.items())
        report['elapsed_seconds']=round(time.monotonic()-start,3)
        if model.errors:report['errors'].append('Provider fixture error')
        report['errors'].extend(validate(report))
        report['result']='FAIL' if report['errors'] else 'PASS'
        report['product_adoption']=False
        report['acceptance_scope']='characterization, not automatic recovery or atomic admission'
        report['orphan_reservation_observed']=scenario=='after-reserve'
        dump(out/'recovery.json',report)
    return report


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--python',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--scenario',choices=SCENARIOS,required=True)
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.absolute()
    if not out.resolve().is_relative_to((a.source_workspace/'runtime').resolve()):raise ValueError('Fresh project runtime required')
    if out.exists():raise FileExistsError('Output already exists')
    if not a.python.is_file():raise FileNotFoundError('Prepared interpreter required')
    r=run(source,a.python,out,a.scenario)
    print(json.dumps({k:r.get(k) for k in ('result','scenario','errors','elapsed_seconds','run_id','model_calls_before_restart','model_calls','recovered_status','reoffered','before_restart','after_restart')},indent=2))
    return int(bool(r['errors']))

if __name__=='__main__':raise SystemExit(main())
