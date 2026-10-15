"""Independent native ownership qualification; no operator mutation or model inference."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import time
from gateway_process import OwnedGatewayProcess
from gateway_recovery_support import Instance,dump,snapshot
from gateway_scripted_model import ScriptedModel
from run_native_hermes_probe import isolated_environment,pinned_source
from run_native_gateway import free_port
ROOT=Path(__file__).resolve().parents[1]


def native_lock(source,python,profile,out,env,mode,*,hold=False):
    out.mkdir();nonce=secrets.token_hex(16)
    stdout=(out/'stdout.txt').open('w',encoding='utf-8');stderr=(out/'stderr.txt').open('w',encoding='utf-8')
    proc=subprocess.Popen([str(python),'-I','-B',str(ROOT/'scripts/qa/maintenance_lock_worker.py'),str(source),str(profile),str(out),nonce,mode],cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
    owned=None;returned_holder=False
    try:
        end=time.monotonic()+15
        while not (out/'spawn.json').exists():
            if proc.poll() is not None or time.monotonic()>end:raise RuntimeError('Maintenance spawn missing')
            time.sleep(.01)
        spawn=json.loads((out/'spawn.json').read_text());assert spawn['nonce']==nonce
        # Short-lived try workers can exit before handle capture; wait/reap through Popen.
        if hold:
            owned=OwnedGatewayProcess(proc,spawn['pid'])
            while not (out/'held.json').exists():
                if proc.poll() is not None or time.monotonic()>end:raise RuntimeError('Maintenance acquisition missing')
                time.sleep(.01)
            assert json.loads((out/'held.json').read_text())==spawn
            returned_holder=True
            return proc,owned,stdout,stderr,spawn
        proc.wait(timeout=20)
        assert proc.returncode==0
        result=json.loads((out/'result.json').read_text());assert result['nonce']==nonce and result['pid']==spawn['pid']
        return result
    finally:
        if not returned_holder:
            if owned is not None and not owned.wait():owned.kill();owned.wait(5)
            if proc.poll() is None:proc.kill();proc.wait(5)
            stdout.close();stderr.close()
            if owned:owned.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True);p.add_argument('--python',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();source=pinned_source(ROOT,a.source_workspace);out=a.output.resolve();runtime=(a.source_workspace.resolve()/'runtime').resolve()
    if out.exists() or not out.is_relative_to(runtime) or out==runtime:raise ValueError('Fresh runtime output required')
    if not a.python.is_file() or not a.python.resolve().is_relative_to(runtime):raise ValueError('Project interpreter required')
    out.mkdir(parents=True);env=isolated_environment(out)
    for name in ('locks','xdg-state','xdg-config','xdg-data','xdg-cache'):(out/name).mkdir()
    env.update(HERMES_GATEWAY_LOCK_DIR=str(out/'locks'),OPENAI_API_KEY='alaz-lock-fixture',NO_PROXY='127.0.0.1,localhost',AWS_EC2_METADATA_DISABLED='true',PYTHONUNBUFFERED='1',NO_COLOR='1',TERM='dumb',XDG_STATE_HOME=str(out/'xdg-state'),XDG_CONFIG_HOME=str(out/'xdg-config'),XDG_DATA_HOME=str(out/'xdg-data'),XDG_CACHE_HOME=str(out/'xdg-cache'))
    fixture=out/'input.txt';fixture.write_text('No model work requested',encoding='utf-8')
    provider=ScriptedModel(fixture,'unused');provider.start();port=free_port();token=secrets.token_hex(32)
    config={'model':{'provider':'custom','base_url':provider.base_url,'default':'alaz-scripted','context_length':131072,'streaming':False},'platforms':{'api_server':{'enabled':True,'host':'127.0.0.1','port':port,'key':token}},'platform_toolsets':{'api_server':[]},'agent':{'max_turns':1,'api_max_retries':0},'gateway':{'multiplex_profiles':False,'loop_watchdog':False},'updates':{'check':False},'plugins':{'enabled':[],'disabled':['hermes-achievements','kanban'],'auto_update_check_hours':0},'security':{'allow_lazy_installs':False},'memory':{'provider':'none'},'checkpoints':{'enabled':False},'sessions':{'auto_archive':False,'auto_prune':False},'auxiliary':{'title_generation':{'enabled':False}},'telemetry':{'shared_metrics':{'enabled':False,'send':False}}}
    dump(out/'profile/config.yaml',config)
    programs=[Path(__file__),ROOT/'scripts/qa/maintenance_lock_worker.py',ROOT/'scripts/gateway_process.py',ROOT/'scripts/gateway_recovery_support.py',ROOT/'scripts/native_gateway_worker.py']
    hashes={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in programs}
    report={'scope':'actual native profile ownership locks plus public Gateway; no operator transaction tested','source_commit':'eb75627faf532fa6ffbdae59a0d14b0b385fc780','checks':[],'errors':[],'model_inference_calls':0,'program_hashes':hashes}
    gateway=None;held=None;blocked_gateway=None;blocked_owned=None
    def check(name,valid,details=None):
        report['checks'].append({'name':name,'passed':bool(valid),'details':details})
        if not valid:raise AssertionError(name)
    def dbhash():return {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (out/'profile').glob('*.db')}
    try:
        gateway=Instance(a.python,source,out,env,secrets.token_hex(16),'gateway-live','none')
        result=native_lock(source,a.python,out/'profile',out/'while-gateway-live',env,'try')
        check('live_gateway_excludes_maintenance',result['result']=='refused',result)
        report['gateway_exit']=gateway.finish();gateway=None
        before=dbhash();inode=(out/'profile/gateway.lock').stat().st_ino
        result=native_lock(source,a.python,out/'profile',out/'after-gateway-stop',env,'try')
        check('stopped_gateway_allows_maintenance',result['result']=='acquired' and result['lock_released'],result)
        check('lock_acquisition_does_not_modify_managed_db',before==dbhash())
        result=native_lock(source,a.python,out/'profile',out/'nested',env,'nested')
        check('nested_same_thread_canonical_alias',result.get('nested_same_canonical_home') is True,result)
        check('independent_owner_in_same_process_refused',result.get('independent_owner_refused') is True)
        held=native_lock(source,a.python,out/'profile',out/'held-owner',env,'hold',hold=True)
        result=native_lock(source,a.python,out/'profile',out/'concurrent-maintenance',env,'try')
        check('other_maintenance_process_refused',result['result']=='refused',result)
        # Attempt the actual public Gateway startup while maintenance remains held.
        blocker_dir=out/'blocked-gateway';blocker_dir.mkdir()
        nonce=secrets.token_hex(16)
        for name in ('spawn.json','ready.json','shutdown.json','failure.json','stop.json'):
            f=out/name
            if f.exists():f.rename(blocker_dir/('prior-'+name))
        with (blocker_dir/'stdout.txt').open('w',encoding='utf-8') as so,(blocker_dir/'stderr.txt').open('w',encoding='utf-8') as se:
            blocked_gateway=subprocess.Popen([str(a.python),'-I','-B',str(ROOT/'scripts/native_gateway_worker.py'),str(source),str(out),nonce],cwd=out,env=env,stdin=subprocess.DEVNULL,stdout=so,stderr=se)
            deadline=time.monotonic()+15
            while not (out/'spawn.json').exists():
                if blocked_gateway.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Blocked Gateway spawn missing')
                time.sleep(.01)
            blocked_spawn=json.loads((out/'spawn.json').read_text());assert blocked_spawn['nonce']==nonce
            blocked_owned=OwnedGatewayProcess(blocked_gateway,blocked_spawn['pid'])
            blocked_gateway.wait(timeout=35)
            assert blocked_owned.wait(5)
            report['blocked_gateway_exit']={'launcher_pid':blocked_gateway.pid,'native_pid':blocked_spawn['pid'],
                'chain':blocked_owned.chain,'native_reaped':True,'launcher_reaped':True,'exit_code':blocked_gateway.returncode}
            blocked_owned.close();blocked_owned=None
        failure=json.loads((out/'failure.json').read_text())
        check('maintenance_excludes_public_gateway',blocked_gateway.returncode!=0 and not (out/'ready.json').exists() and failure['nonce']==nonce and not held[1].wait(),{'exit_code':blocked_gateway.returncode,'failure_type':failure['type']})
        proc,owned,so,se,spawn=held
        owned.kill();proc.wait(8);reaped=owned.wait(5)
        report['maintenance_kill']={'launcher_pid':proc.pid,'native_pid':spawn['pid'],'chain':owned.chain,'exit_code':proc.returncode,'native_reaped':reaped,'launcher_reaped':proc.poll() is not None}
        owned.close();so.close();se.close();held=None
        check('owned_maintenance_kill_reaped',reaped and proc.returncode!=0)
        result=native_lock(source,a.python,out/'profile',out/'after-owner-kill',env,'try')
        check('process_death_releases_native_lock',result['result']=='acquired',result)
        check('lock_inode_preserved',inode==(out/'profile/gateway.lock').stat().st_ino)
        check('managed_databases_unchanged_through_contention',before==dbhash())
        gateway=Instance(a.python,source,out,env,secrets.token_hex(16),'gateway-after-maintenance','none')
        report['restarted_gateway_exit']=gateway.finish();gateway=None
        check('same_gateway_restarts_after_lock_release',report['restarted_gateway_exit']['exit_code']==0 and report['restarted_gateway_exit']['ready']['epoch']>report['gateway_exit']['ready']['epoch'])
        final=snapshot(out/'profile','unused');check('no_admissions_or_tools',final['admissions']==[] and final['user_count']==final['tool_count']==0)
        report['snapshot']=final
    except Exception as e:report['errors'].append(type(e).__name__+': '+str(e))
    finally:
        if gateway is not None and not gateway.finished:
            try:gateway.finish()
            except Exception as e:report['errors'].append('cleanup '+type(e).__name__)
        if held:
            proc,owned,so,se,spawn=held
            try:
                if not owned.wait():owned.kill()
                proc.wait(8);owned.wait(5)
            finally:owned.close();so.close();se.close()
        if blocked_owned is not None:
            try:
                if not blocked_owned.wait():blocked_owned.kill();blocked_owned.wait(5)
            finally:blocked_owned.close()
        if blocked_gateway is not None and blocked_gateway.poll() is None:blocked_gateway.kill();blocked_gateway.wait(5)
        provider.close()
    report['model_http_calls']=len(provider.calls);report['fixture_errors']=provider.errors
    report['code_drift']=[f.relative_to(ROOT).as_posix() for f in programs if hashlib.sha256(f.read_bytes()).hexdigest()!=hashes[f.relative_to(ROOT).as_posix()]]
    if report['model_http_calls'] or provider.errors or report['code_drift']:report['errors'].append('unexpected activity or code drift')
    report['result']='PASS' if not report['errors'] else 'FAIL'
    dump(out/'maintenance-ownership.json',report);print(json.dumps(report,indent=2));return int(bool(report['errors']))
if __name__=='__main__':raise SystemExit(main())
