"""Q104E ordinary-user Landlock metadata/exec inheritance audit in P71C.

Uses an immutable candidate source snapshot, not a modified runtime. Own temp
fixtures only. No root, namespace/mount change, Hermes, broker or provider call.
Forbidden metadata is OPENED for access controls only, NEVER read for content.
"""
from __future__ import annotations
import argparse
import ctypes
import errno
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]
D='AlazHarness-D3B-P71C'
E=ROOT/'evidence/d3b-native-profile-q104e'
DENIED={errno.EACCES,errno.EPERM}
MAX=2*1024*1024


def require(ok,why):
    if not ok:raise RuntimeError(why)


def access(path,flags=os.O_RDONLY):
    try:fd=os.open(path,flags|os.O_CLOEXEC)
    except OSError as exc:return {'allowed':False,'errno':exc.errno}
    os.close(fd)
    return {'allowed':True,'errno':None}


def mount_hash(path):
    with open(path,'rb') as f:data=f.read(MAX+1)
    require(0<len(data)<=MAX and data.endswith(b'\n'),'mount_table_bound')
    return hashlib.sha256(data).hexdigest()


def candidate():
    pin=json.loads((E/'candidate-001.json').read_text())['files']['packages/claw-hermes/credential_guard.py']
    path=E/pin['snapshot'];require(hashlib.sha256(path.read_bytes()).hexdigest()==pin['sha256'],'candidate_hash')
    loader=SourceFileLoader('q104e_candidate_guard',str(path));spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec);loader.exec_module(mod)
    return mod,pin['sha256']


def descendant(context):
    grant=context['grantPid'];own=access('/proc/self/mountinfo')
    original=access('/proc/'+str(grant)+'/mountinfo')
    checks={'new_pid_is_distinct':os.getpid()!=grant,
            'new_self_not_automatically_granted':not own['allowed'] and own['errno'] in DENIED,
            'original_numeric_grant_inherited':original['allowed']==context['enabled'],
            'no_new_privs_inherited':ctypes.CDLL(None).prctl(39,0,0,0,0)==1}
    if not context['enabled']:checks['original_denial_explicit']=original['errno'] in DENIED
    return {'pid':os.getpid(),'grantPid':grant,'checks':checks,'ownMountOpen':own,'originalMountOpen':original}


def fork_probe(context):
    read,write=os.pipe();pid=os.fork()
    if pid==0:
        os.close(read)
        try:
            result=descendant(context);raw=(json.dumps(result)+'\n').encode()
            require(len(raw)<4096,'child_output_bound');require(os.write(write,raw)==len(raw),'child_short_write')
            os.close(write);os._exit(0 if all(result['checks'].values()) else 9)
        except BaseException:os._exit(10)
    os.close(write);reaped=False
    try:
        require(bool(select.select([read],[],[],10)[0]),'fork_result_timeout')
        raw=os.read(read,4097);require(len(raw)<=4096 and raw.endswith(b'\n'),'fork_result_bound')
        data=json.loads(raw)
        end=time.monotonic()+10
        while True:
            done,status=os.waitpid(pid,os.WNOHANG)
            if done:reaped=True;break
            require(time.monotonic()<end,'fork_reap_timeout');time.sleep(.01)
        data['exitCode']=os.waitstatus_to_exitcode(status)
        require(data['pid']==pid,'fork_pid_changed')
        return data
    finally:
        os.close(read)
        if not reaped:
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
            os.waitpid(pid,0)


def observe(context):
    checks={};details={};grant=context['grantPid'];enabled=context['enabled']
    checks['same_pid_across_real_exec']=os.getpid()==grant
    checks['isolated_interpreter']=sys.flags.isolated==1
    checks['ordinary_identity_unchanged']=os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3
    checks['same_mount_namespace']=os.readlink('/proc/self/ns/mnt')==context['namespace']
    own=access('/proc/self/mountinfo');numeric=access('/proc/'+str(grant)+'/mountinfo')
    details['selfMountOpen']=own;details['numericMountOpen']=numeric
    checks['self_mount_permission_exact']=own['allowed']==enabled and numeric['allowed']==enabled
    if enabled:
        checks['actual_kernel_mount_table_read']=mount_hash('/proc/self/mountinfo')==mount_hash('/proc/'+str(grant)+'/mountinfo')==context['mountHash']
    else:checks['default_denied_explicitly']=own['errno'] in DENIED and numeric['errno'] in DENIED
    denied_paths={'self_environ':'/proc/self/environ','self_mem':'/proc/self/mem',
        'self_maps':'/proc/self/maps','self_mounts':'/proc/self/mounts',
        'self_mountstats':'/proc/self/mountstats','self_fd_directory':'/proc/self/fd',
        'parent_mountinfo':'/proc/'+str(context['parentPid'])+'/mountinfo',
        'protected_canary':context['canary']}
    for label,path in denied_paths.items():
        observed=access(path);details[label]=observed
        checks[label+'_denied']=not observed['allowed'] and observed['errno'] in DENIED
    write=access('/proc/self/mountinfo',os.O_WRONLY);details['mountWrite']=write
    checks['mountinfo_not_write_opened']=not write['allowed'] and write['errno'] in DENIED
    # Write denial also exists in procfs; mocked rule tests separately prove READ_FILE only.
    fields={}
    for row in Path('/proc/self/status').read_text().splitlines():
        k,_,v=row.partition(':');fields[k]=v.split()
    checks['no_new_privs_enforced']=fields.get('NoNewPrivs')==['1']
    checks['zero_effective_capabilities']=int(fields['CapEff'][0],16)==0
    marker=Path(context['work'])/'allowed-write';marker.write_text('owned q104e fixture')
    checks['owned_workspace_still_writable']=marker.read_text()=='owned q104e fixture'
    forked=fork_probe(context);details['fork']=forked
    checks['fork_no_implicit_new_pid_grant']=forked['exitCode']==0 and all(forked['checks'].values())
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':context['work'],'Q104E_CONTEXT':json.dumps(context)}
    execed=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--phase','descendant'],
        env=env,cwd=context['work'],stdin=subprocess.DEVNULL,capture_output=True,timeout=12)
    require(execed.returncode==0 and not execed.stderr,'exec_descendant_failed')
    d=json.loads(execed.stdout);details['execDescendant']=d
    checks['exec_child_no_implicit_new_pid_grant']=all(d['checks'].values())
    checks['candidate_source_unchanged']=candidate()[1]==context['candidateSha256']
    return {'case':context['case'],'result':'PASS' if all(checks.values()) else 'FAIL',
        'pid':os.getpid(),'checks':checks,'checkCount':len(checks),'details':details,
        'beforeControls':context['controls'],'receipt':context['receipt'],
        'candidateSha256':context['candidateSha256'],'contentOfSensitiveMetadataRead':False,
        'fullGatewayIsolationTested':False,'rootUsed':False}


def enter(context):
    require(os.getuid()==os.geteuid()==23001 and os.getgid()==23003,'ordinary_lab_identity')
    fixture=Path(context['fixture']);require(fixture.parent.parent==Path('/tmp')
        and fixture.parent.name.startswith('alaz-q104e-fixtures-'),'owned_fixture_required')
    guard,digest=candidate();pid=os.getpid()
    controls={n:access(p) for n,p in {'self_mountinfo':'/proc/self/mountinfo',
        'self_environ':'/proc/self/environ','self_mem':'/proc/self/mem','self_maps':'/proc/self/maps',
        'self_mounts':'/proc/self/mounts','self_mountstats':'/proc/self/mountstats','self_fd_directory':'/proc/self/fd',
        'parent_mountinfo':'/proc/'+str(os.getppid())+'/mountinfo','protected_canary':str(fixture/'private/canary')}.items()}
    require(all(x['allowed'] for x in controls.values()),'positive_access_controls_required')
    policy={'version':1,'enabled':True,'readonly':['/usr',str(ROOT)],
        'writable':[str(fixture/'work'),'/dev/null'],'protected':[str(fixture/'private/canary')],
        'self_process_metadata':True}
    context.update(grantPid=pid,parentPid=os.getppid(),controls=controls,
        namespace=os.readlink('/proc/self/ns/mnt'),mountHash=mount_hash('/proc/self/mountinfo'),
        candidateSha256=digest,work=str(fixture/'work'),canary=str(fixture/'private/canary'))
    if context['case']=='default':receipt=guard.apply(policy)
    else:receipt=guard.apply(policy,self_mount_metadata=context['enabled'])
    context['receipt']=receipt
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':context['work'],'Q104E_CONTEXT':json.dumps(context)}
    os.execve(sys.executable,[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--phase','observe'],env)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=('main','enter','observe','descendant'),default='main')
    a=parser.parse_args()
    if a.phase=='enter':return enter(json.loads(sys.stdin.buffer.read(32769)))
    if a.phase=='observe':
        r=observe(json.loads(os.environ['Q104E_CONTEXT']));print(json.dumps(r),flush=True)
        return 0 if r['result']=='PASS' else 1
    if a.phase=='descendant':
        r=descendant(json.loads(os.environ['Q104E_CONTEXT']));print(json.dumps(r),flush=True)
        return 0 if all(r['checks'].values()) else 1
    require(sys.platform=='linux' and os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3,'ordinary_lab_identity')
    require(os.environ.get('WSL_DISTRO_NAME')==D and Path('/etc/alaz-p71c-lab-id').read_text().strip()==D,'lab_required')
    require(ROOT.parent==Path('/tmp') and ROOT.name.startswith('alaz-q104e-code-'),'owned_code_required')
    identity=(os.getresuid(),os.getresgid(),tuple(os.getgroups()),os.readlink('/proc/self/ns/mnt'),os.readlink('/proc/self/ns/user'))
    before=mount_hash('/proc/self/mountinfo');results=[]
    with tempfile.TemporaryDirectory(prefix='alaz-q104e-fixtures-',dir='/tmp') as temporary:
        for label,opt in (('default',False),('explicit_false',False),('opt_in_true',True)):
            fixture=Path(temporary)/label;fixture.mkdir(mode=0o700)
            for sub in ('work','private'):(fixture/sub).mkdir(mode=0o700)
            canary=fixture/'private/canary';canary.write_text('owned permission canary');canary.chmod(0o600)
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(fixture/'work')}
            r=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--phase','enter'],
                input=json.dumps({'case':label,'enabled':opt,'fixture':str(fixture)}).encode(),
                cwd=fixture,env=env,capture_output=True,timeout=35)
            entry={'case':label,'exitCode':r.returncode,'stderr':r.stderr.decode('utf-8','replace')[-2500:]}
            try:entry['proof']=json.loads(r.stdout)
            except ValueError:entry['stdout']=r.stdout.decode('utf-8','replace')[-1500:]
            results.append(entry)
    checks={'three_actual_exec_cases':len(results)==3 and all(r['exitCode']==0 and not r['stderr'] and r.get('proof',{}).get('result')=='PASS' for r in results),
        'parent_identity_unchanged':identity==(os.getresuid(),os.getresgid(),tuple(os.getgroups()),os.readlink('/proc/self/ns/mnt'),os.readlink('/proc/self/ns/user')),
        'mount_table_unchanged':before==mount_hash('/proc/self/mountinfo'),'owned_fixtures_removed':not Path(temporary).exists()}
    report={'result':'PASS_SCOPED_METADATA_INHERITANCE' if all(checks.values()) else 'FAIL','checks':checks,'cases':results,
        'candidateSha256':candidate()[1],'probeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'uid':os.getuid(),'gid':os.getgid(),'rootUsed':False,'mountsChanged':False,'namespacesChanged':False,
        'actualNativeProfileTested':False,'realHermesGatewayStarted':False,'providerCalls':0,'fullD3BAccepted':False}
    print(json.dumps(report),flush=True)
    return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
