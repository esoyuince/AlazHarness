"""Opt-in Windows AppContainer feasibility; never launches Hermes or changes firewall.

Fresh project runtime output only. Builds the adjacent reviewed C# probe with
Windows' existing Framework64 compiler. No download or dependency installation.
A narrow native QA probe, NOT permission for arbitrary agent execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(__file__).with_name('windows_appcontainer_probe.cs')


def validate_observation(value: dict) -> list[str]:
    """Validate the fixed proof contract. Child statements alone are insufficient."""
    problems=[]
    try:
        if type(value) is not dict:return ['not_object']
        for name,expected in [('result','PASS'),('errors',[]),('hermesIsolationAccepted',False),('firewallModified',False),('loopbackExemptionAdded',False),('listenersStopped',True),('fixtureSecretUnchanged',True)]:
            if type(value.get(name)) is not type(expected) or value[name]!=expected:problems.append(name)
        for name,expected in [('profileDeleteHresult',0),('modelCalls',0),('ipv4ListenerMessages',1),('ipv6ListenerMessages',1)]:
            if type(value.get(name)) is not int or value[name]!=expected:problems.append(name)
        if not re.fullmatch(r'AlazHarness\.QA\.[a-f0-9]{32}',value['profileName']):problems.append('profile_name')
        sid=value['appContainerSid']
        if type(sid) is not str or not re.fullmatch(r'S-1-15-2(?:-\d+){7}',sid):problems.append('app_sid')
        pids=[]
        for mode,isolated in [('baseline',False),('isolated',True),('timeoutProbe',True)]:
            run=value[mode];identity=run['identityBeforeResume'];pids.append(run['pid'])
            if type(run['pid']) is not int or run['pid']<=0:problems.append(mode+'_pid')
            if identity['isAppContainer'] is not isolated:problems.append(mode+'_container')
            if type(identity['capabilityCount']) is not int or identity['capabilityCount']!=0:problems.append(mode+'_capabilities')
            if isolated and (identity['appContainerSid']!=sid or identity['integritySid']!='S-1-16-4096'):problems.append(mode+'_identity')
            for k,expected in [('jobAssignedBeforeResume',True),('handlesInherited',False),('processReaped',True)]:
                if run[k] is not expected:problems.append(mode+'_'+k)
            hung=mode=='timeoutProbe'
            if run['timedOut'] is not hung or type(run['exitCode']) is not int or run['exitCode']!=(91 if hung else 0):problems.append(mode+'_exit')
            if hung:continue
            child=run['child']
            if child['isAppContainer'] is not isolated or child['parentSecretInEnvironment'] is not (not isolated):problems.append(mode+'_environment_or_token')
            if isolated and child['appContainerSid']!=sid:problems.append(mode+'_child_sid')
            for k in ('privateReadError','privateWriteError','allowedWriteError','parentMemoryOpenError'):
                if type(child[k]) is not int or child[k]!=(5 if isolated else 0):problems.append(mode+'_'+k)
            if type(child['allowedReadError']) is not int or child['allowedReadError']!=0:problems.append(mode+'_allowed_read')
            for k in ('ipv4Error','ipv6Error'):
                if type(child[k]) is not int or child[k]!=(10013 if isolated else 0):problems.append(mode+'_'+k)
            if isolated and (type(child['testNetError']) is not int or child['testNetError']!=10013):problems.append('test_net_not_access_denied')
        if len(set(pids))!=3:problems.append('nonunique_processes')
    except (KeyError,TypeError,ValueError,AttributeError):problems.append('malformed_evidence')
    return problems


def environment(out: Path) -> dict[str,str]:
    # Never forward parent API keys, proxy controls, PATH, HOME or Python settings.
    root=os.environ['SystemRoot']
    local=os.environ.get('LOCALAPPDATA','')
    if not local or not Path(local).is_absolute() or not Path(local).is_dir():
        raise ValueError('launcher local app-data path required')
    # Windows CreateProcess resolves its new package profile using the CALLER path.
    # This path is supplied only to our trusted launcher; child gets its own profile.
    return {'SystemRoot':root,'WINDIR':root,'LOCALAPPDATA':local,
            'TEMP':str(out/'compiler-temp'),'TMP':str(out/'compiler-temp')}


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if os.name!='nt':raise SystemExit('Windows native probe required; no fallback')
    root=a.source_workspace.resolve();out=a.output.absolute()
    for entry in (out,*out.parents):
        if entry.is_symlink() or (hasattr(entry,'is_junction') and entry.is_junction()):raise ValueError('linked output refused')
    out=out.resolve();runtime=root/'runtime'
    if not root.is_dir() or not out.is_relative_to(runtime) or out==runtime or out.exists():raise ValueError('fresh project runtime output required')
    compiler=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not compiler.is_file():raise SystemExit('existing compiler unavailable; no install')
    out.mkdir(parents=True);(out/'app').mkdir();(out/'compiler-temp').mkdir()
    hashes={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in [SOURCE,Path(__file__)]}
    env=environment(out);receipt={'scope':'Windows OS probe, not full Hermes/Gateway isolation','code':hashes,'environment_names':sorted(env),'inference_calls':0,'paid_calls':0}
    exe=out/'app/probe.exe';started=time.monotonic()
    build=subprocess.run([str(compiler),'/nologo','/target:exe','/platform:x64','/optimize+','/r:System.Web.Extensions.dll','/out:'+str(exe),str(SOURCE)],env=env,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=40)
    (out/'compile.txt').write_text(build.stdout+build.stderr,encoding='utf-8')
    receipt['compile_exit']=build.returncode
    if build.returncode:
        receipt['result']='BUILD_FAILED'
    else:
        receipt['executable_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
        try:
            result=subprocess.run([str(exe),'--probe',str(out)],env=env,cwd=out,stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=100)
            (out/'stdout.txt').write_text(result.stdout,encoding='utf-8');(out/'stderr.txt').write_text(result.stderr,encoding='utf-8')
            receipt['native_exit']=result.returncode
            observation=json.loads((out/'observation.json').read_text(encoding='utf-8'))
            receipt['observation']=observation;receipt['validation_errors']=validate_observation(observation)
            receipt['result']='PASS' if result.returncode==0 and not result.stderr and not receipt['validation_errors'] else 'FAIL'
        except (subprocess.TimeoutExpired,OSError,ValueError) as exc:
            receipt['result']='UNCONFIRMED';receipt['error_type']=type(exc).__name__
            # Do not retry, grant extra capabilities or call broad taskkill.
    receipt['elapsed_seconds']=round(time.monotonic()-started,3)
    receipt['code_drift']=[n for n,h in hashes.items() if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h]
    if receipt['code_drift']:receipt['result']='FAIL'
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    return 0 if receipt['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
