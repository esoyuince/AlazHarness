"""Real unprivileged exec/filter inheritance and broker-target refusal only.

No root invocation, UID change, namespace creation, provider call or service.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import principal_launch as launch
import principal_target as target
SOURCES=('packages/claw-hermes/principal_launch.py','packages/claw-hermes/principal_target.py',
         'packages/claw-hermes/host_principal.py','packages/claw-hermes/linux_netns.py',
         'scripts/run_principal_broker_target.py','scripts/run_principal_broker.py',
         'scripts/run_provider_broker.py','scripts/qa/principal_postexec_linux.py',
         'tests/test_principal_target.py','tests/test_principal_postexec_binding.py')

def hashes():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    arg=parser.parse_args().output;dest=arg.resolve()
    if (sys.platform!='linux' or os.getuid()==0 or os.getgid()==0 or arg.is_symlink()
            or dest.exists() or dest.parent!=(ROOT/'evidence/d3b-postexec-21oct').resolve()):
        raise SystemExit('unprivileged_fresh_owned_output_required')
    before=hashes();parent=launch.observation();parent_filter=target.seccomp_mode()
    checks={};details={};error=None
    env={'PATH':'/usr/bin:/bin','HOME':'/','LANG':'C.UTF-8','PYTHONNOUSERSITE':'1'}
    p={'version':1,'enabled':True,'gatewayUid':os.getuid(),'brokerUid':os.getuid()+10000,
       'socketGroupGid':os.getgid(),'hostUserNamespace':parent['userns']}
    with tempfile.TemporaryDirectory(prefix='alaz-postexec-') as tmp:
        base=Path(tmp);config=base/'not-a-real-config.json';config.write_text('owned fixture; no keys')
        digest=hashlib.sha256(config.read_bytes()).hexdigest();out=base/'no-broker'
        try:
            r=subprocess.run([sys.executable,'-I','-B',str(ROOT/'scripts/run_principal_broker_target.py'),
                '--principal',json.dumps(p),'--config',str(config),'--config-sha256',digest,
                '--output',str(out)],stdin=subprocess.DEVNULL,capture_output=True,env=env,cwd='/',timeout=15)
            diagnostic=json.loads(r.stderr)
            checks['actual_target_cli_refused']=r.returncode==2 and not r.stdout
            checks['bounded_diagnostic_no_fallback']=diagnostic=={'result':'REFUSED',
                'phase':'principal_broker_target','reasonType':'TargetRejected','fallback':False}
            setup='import sys,os,json,ctypes,errno;sys.path.insert(0,'+repr(str(ROOT/'packages/claw-hermes'))+');import principal_launch as launch;import principal_target as target;import linux_netns as net\n'
            after=setup+"""
expected=json.loads(sys.argv[1]);p=json.loads(sys.argv[2]);config=sys.argv[3];digest=sys.argv[4];out=sys.argv[5]
state=launch.observation();lib=ctypes.CDLL(None,use_errno=True)
lib.recvmsg.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int];lib.recvmsg.restype=ctypes.c_ssize_t
ctypes.set_errno(0);rc=lib.recvmsg(-1,None,0);received_errno=ctypes.get_errno()
opened=[]
def audit(event,args):
    if event=='open' and str(args[0])==config:opened.append(True)
sys.addaudithook(audit)
reason=None
try:target.prepare(p,config,digest,out)
except target.TargetRejected as ex:reason=str(ex)
print(json.dumps({'checks':{
 'same_pid_across_exec':state['pid']==expected['pid'],
 'same_real_host_identity_across_exec':list(state['uids'])==expected['uids'] and list(state['gids'])==expected['gids'],
 'same_namespace_across_exec':state['userns']==expected['userns'] and state['uidMap']==expected['uidMap'] and state['gidMap']==expected['gidMap'],
 'no_new_privs_inherited':state['nnp']==1,
 'seccomp_filter_mode_inherited':target.seccomp_mode()==2,
 'known_recvmsg_deny_inherited':rc==-1 and received_errno==errno.EPERM,
 'target_rejects_wrong_host_uid_after_exec':reason=='target_wrong_identity',
 'private_config_not_opened':not opened},
 'pid':state['pid'],'uid':os.getuid(),'recvmsgErrno':received_errno}))
"""
            child=setup+"""
state=launch.observation();lib=ctypes.CDLL(None,use_errno=True)
lib.recvmsg.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_int];lib.recvmsg.restype=ctypes.c_ssize_t
ctypes.set_errno(0);rc=lib.recvmsg(-1,None,0)
assert rc==-1 and ctypes.get_errno()==errno.EBADF,'baseline_recvmsg_not_available'
seccomp=net._load_seccomp();lib.prctl.restype=ctypes.c_int
assert lib.prctl(38,1,0,0,0)==0,'nnp_failed'
net._filter(seccomp)
os.execve(sys.executable,[sys.executable,'-I','-B','-c',sys.argv[1],json.dumps(state),*sys.argv[2:]],
          {'PATH':'/usr/bin:/bin','HOME':'/','LANG':'C.UTF-8','PYTHONNOUSERSITE':'1'})
"""
            r=subprocess.run([sys.executable,'-I','-B','-c',child,after,json.dumps(p),str(config),digest,str(out)],
                stdin=subprocess.DEVNULL,capture_output=True,env=env,cwd='/',timeout=20)
            checks['owned_exec_child_completed']=r.returncode==0 and not r.stderr
            if r.returncode==0:
                result=json.loads(r.stdout);checks.update(result['checks'])
                details={k:v for k,v in result.items() if k!='checks'}
            else:details={'childExit':r.returncode,'stderrType':'retained-digest-only',
                          'stderrSha256':hashlib.sha256(r.stderr).hexdigest()}
        except Exception as ex:error=type(ex).__name__
        checks['broker_directory_never_created']=not out.exists()
        checks['fixture_bytes_unchanged']=hashlib.sha256(config.read_bytes()).hexdigest()==digest
    checks['temporary_fixture_removed']=not base.exists()
    checks['parent_identity_privileges_unchanged']=parent==launch.observation() and parent_filter==target.seccomp_mode()
    current=hashes();checks['source_bytes_unchanged']=before==current
    report={'result':'PASS_SCOPED_POSTEXEC' if error is None and len(checks)==16 and all(v is True for v in checks.values()) else 'FAIL',
        'scope':'unprivileged real exec, NNP/seccomp inheritance, target refusal before config/socket; NOT positive UID reduction',
        'observedAt':datetime.datetime.now().astimezone().isoformat(),'checks':checks,'checkCount':len(checks),
        'details':details,'errorType':error,'sourceSha256':before,'sourceAfterSha256':current,
        'observerUid':os.getuid(),'positiveUidTransitionTested':False,'brokerStarted':False,
        'gatewayBrokerTwoUidTested':False,'ipcV2MountTested':False,'fullD3BAccepted':False,'realModelCalls':0}
    with dest.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('sourceSha256','sourceAfterSha256','scope','details')}))
    return 0 if report['result']=='PASS_SCOPED_POSTEXEC' else 1

if __name__=='__main__':raise SystemExit(main())
