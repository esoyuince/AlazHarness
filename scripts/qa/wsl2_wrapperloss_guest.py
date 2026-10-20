"""PLAT-002D fixed rootless Linux private-lease test worker.

No general commands, agent, provider or real D3B confinement. A detached
test-only Linux guardian enforces a short TTL on its OWN worker and its
single descendant even if a Windows WSL wrapper disappears. Native
owner/result evidence remains under a 0700 /tmp root for separate QA.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import select
import signal
import stat
import subprocess
import sys
import tempfile
import time

TAG='PLAT002D'
TTL_SEC=7
FILENAME='wsl2_wrapperloss_guest.py'
PR_SET_CHILD_SUBREAPER=36
# Only the guardian launches these two hard-coded, nonnetworked Python programs.
GRANDCHILD="import time;time.sleep(24)"
WORKER=r"""import json,os,signal,subprocess,sys,time
run=sys.argv[1]
assert os.getpgrp()==os.getpid() and len(run)==24
child=subprocess.Popen([sys.executable,'-I','-B','-c',
  'import time;time.sleep(24)',run],stdin=subprocess.DEVNULL,
  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
  close_fds=True)
assert os.getpgid(child.pid)==os.getpid()
signal.signal(signal.SIGTERM,signal.SIG_IGN)
print(json.dumps({'workerPid':os.getpid(),
 'grandchildPid':child.pid,'pgid':os.getpgrp()}),flush=True)
# Independent last-resort self-cleanup if the detached guardian dies.
# At 12s, clean ONLY this worker's owned grandchild. Normal lease 7s
# will have terminated and reaped both processes already.
expiry=time.monotonic()+12
while time.monotonic()<expiry:
    time.sleep(0.1)
if child.poll() is None:
    child.kill()
child.wait(timeout=3)
"""

class Denied(ValueError): pass
def check(ok,why):
    if not ok:raise Denied(why)
def hexid(value,n):
    return type(value) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is not None
def sha(data):
    return hashlib.sha256(data).hexdigest()
def source_sha(path):
    return sha(path.read_bytes())

def guest_environment():
    check(sys.platform=='linux' and platform.machine()=='x86_64','LINUX_X64_REQUIRED')
    release=platform.release().lower()
    check('microsoft' in release and 'wsl2' in release,'LINUX_WSL2_REQUIRED')
    check(os.getuid()==1000 and os.geteuid()==1000
          and os.getgid()==os.getegid(),'UNPRIVILEGED_GUEST_ID_REQUIRED')

def own_root(root,run):
    check(root.parent==Path('/tmp') and
          root.name.startswith('alaz-plat002d-'+run+'-') and
          not root.is_symlink(),'PRIVATE_ROOT_NAME')
    st=root.stat()
    check(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==0o700
          and st.st_uid==os.getuid(),'PRIVATE_ROOT_OWNER_MODE')

def trusted_source(path,expected):
    check(path.name==FILENAME and path.is_file() and not path.is_symlink()
          and source_sha(path)==expected,'SOURCE_NOT_PINNED')

def pid_start_tick(pid):
    # /proc/<pid>/stat: field22; comm can contain whitespace/parentheses.
    data=Path('/proc')/str(pid)/'stat'
    text=data.read_text(encoding='ascii',errors='replace')
    tail=text.rsplit(') ',1)[1].split()
    return int(tail[19])

def write_once(folder,name,payload):
    check(name in ('ready.json','result.json'),'RECEIPT_FILE_INVALID')
    f=folder/name
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW
    fd=os.open(f,flags,0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
        json.dump(payload,stream,sort_keys=True,separators=(',',':'))
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    return f

def set_subreaper():
    libc=ctypes.CDLL(None,use_errno=True)
    check(libc.prctl(PR_SET_CHILD_SUBREAPER,1,0,0,0)==0,
          'LINUX_SUBREAPER_REQUIRED')

def read_worker_ready(child):
    ready,_,_=select.select([child.stdout],[],[],4)
    check(bool(ready),'OWNED_WORKER_READY_TIMEOUT')
    data=child.stdout.readline(512)
    check(len(data)<=512 and data.endswith(b'\n') and data.count(b'\n')==1,
          'OWNED_WORKER_READY_FRAME')
    obj=json.loads(data)
    check(type(obj) is dict and set(obj)==
          {'workerPid','grandchildPid','pgid'},'OWNED_WORKER_FIELDS')
    check(type(obj['workerPid']) is int and obj['workerPid']==child.pid
          and type(obj['grandchildPid']) is int
          and obj['grandchildPid']>1 and obj['grandchildPid']!=child.pid
          and type(obj['pgid']) is int and obj['pgid']==child.pid,
          'OWNED_WORKER_PID_INVALID')
    check(os.getpgid(child.pid)==child.pid and
          os.getpgid(obj['grandchildPid'])==child.pid,
          'OWNED_GRANDCHILD_GROUP_INVALID')
    return obj

def owned_group_kill(child,grandchild,worker_tick,grand_tick):
    # Never signal a PID/group without an exact PID+birth-tick and
    # matching group. This is a test-owned Popen child only.
    if child.poll() is None:
        check(pid_start_tick(child.pid)==worker_tick
              and os.getpgid(child.pid)==child.pid,
              'OWNED_WORKER_REPLACED')
        os.killpg(child.pid,signal.SIGKILL)
    else:
        try:
            if (pid_start_tick(grandchild)==grand_tick
                    and os.getpgid(grandchild)==child.pid):
                os.killpg(child.pid,signal.SIGKILL)
        except FileNotFoundError:
            pass
    check(child.wait(timeout=3)==-signal.SIGKILL,
          'OWNED_WORKER_KILL_RESULT_INVALID')
    try:
        pid,status=os.waitpid(grandchild,os.WNOHANG)
        if pid==0:
            pid,status=os.waitpid(grandchild,0)
        check(pid==grandchild,'GRANDCHILD_REAP_UNKNOWN')
    except ChildProcessError:
        raise Denied('GRANDCHILD_NOT_REPARENTED_TO_GUARDIAN') from None
    return True

def guardian(run,nonce,expected,root):
    guest_environment()
    own_root(root,run)
    source=Path(__file__).resolve(strict=True)
    check(source.parent==root,'GUARDIAN_MUST_USE_NATIVE_COPY')
    trusted_source(source,expected)
    set_subreaper()
    child=None
    ready=False
    done=False
    reason='UNKNOWN'
    worker_tick=None
    grand_tick=None
    grandchild_pid=None
    try:
        child=subprocess.Popen([sys.executable,'-I','-B','-c',WORKER,run],
             stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
             stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True,
             cwd=root,env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'})
        meta=read_worker_ready(child)
        grandchild_pid=meta['grandchildPid']
        worker_tick=pid_start_tick(child.pid)
        grand_tick=pid_start_tick(grandchild_pid)
        manifest={'version':1,'type':'alaz.wsl2.wrapperloss.test.v1',
             'runId':run,'nonceSha256':sha(nonce.encode('ascii')),
             'sourceSha256':expected,'uid':os.getuid(),
             'guardianPid':os.getpid(),'guardianStartTick':pid_start_tick(os.getpid()),
             'workerPid':child.pid,'workerStartTick':worker_tick,
             'grandchildPid':grandchild_pid,'grandchildStartTick':grand_tick,
             'ready':True,'maxLeaseSec':TTL_SEC,
             'secureExecutionAccepted':False,'realModelCalls':0}
        write_once(root,'ready.json',manifest)
        ready=True
        # Fixed non-renewable lease: wrapper exit does not authorize
        # success/replay; detached guardian closes owned group at TTL.
        end=time.monotonic()+TTL_SEC
        while time.monotonic()<end:
            time.sleep(min(0.12,end-time.monotonic()))
        reason='LEASE_EXPIRED_OUTCOME_UNKNOWN'
    except Exception:
        reason='GUEST_SETUP_OR_LEASE_FAILED_UNKNOWN'
    finally:
        if child is not None:
            try:
                if ready and worker_tick is not None and grand_tick is not None:
                    done=owned_group_kill(child,grandchild_pid,worker_tick,grand_tick)
                elif child.poll() is None:
                    if child.pid>1 and os.getpgid(child.pid)==child.pid:
                        os.killpg(child.pid,signal.SIGKILL)
                    child.wait(timeout=4)
            except Exception:
                done=False
            if child.stdout is not None:child.stdout.close()
        result={'version':1,'type':'alaz.wsl2.wrapperloss.test.v1',
              'runId':run,'sourceSha256':expected,'nonceSha256':sha(nonce.encode('ascii')),
              'guestUid':os.getuid(),'guardianPid':os.getpid(),
              'workerPid':child.pid if child else None,
              'grandchildPid':grandchild_pid,
              'leaseExpired':reason=='LEASE_EXPIRED_OUTCOME_UNKNOWN',
              'testOwnedProcessesReaped':done,
              'terminal':reason,
              'externalToolOutcome':'UNKNOWN_DO_NOT_REPLAY',
              'hostWrapperKillIsSuccess':False,
              'fullD3BAccepted':False,'realModelCalls':0}
        try:write_once(root,'result.json',result)
        except Exception:pass
    return 0 if done else 2

def starter(run,nonce,expected):
    guest_environment()
    src=Path(__file__).resolve(strict=True)
    check(src.parent!=Path('/tmp'),'ORIGINAL_SOURCE_MUST_NOT_BE_NATIVE_COPY')
    trusted_source(src,expected)
    root=Path(tempfile.mkdtemp(prefix='alaz-plat002d-'+run+'-',dir='/tmp'))
    root.chmod(0o700)
    own_root(root,run)
    target=root/FILENAME
    guardian_proc=None
    try:
        with src.open('rb') as fin,target.open('xb') as fout:
            fout.write(fin.read())
        target.chmod(0o600)
        trusted_source(target,expected)
        guardian_proc=subprocess.Popen(
           [sys.executable,'-I','-B',str(target),'--guardian',
            '--run-id',run,'--nonce',nonce,'--source-sha256',expected,
            '--private-root',str(root)],
           cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True,
           env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'})
        started=time.monotonic()
        ready_file=root/'ready.json'
        info=None
        while time.monotonic()-started<5:
            if ready_file.is_file():
                info=json.loads(ready_file.read_text(encoding='utf-8'))
                break
            check(guardian_proc.poll() is None,'GUARDIAN_EARLY_EXIT')
            time.sleep(0.07)
        check(type(info) is dict and info.get('ready') is True
              and info['runId']==run and info['sourceSha256']==expected
              and info['nonceSha256']==sha(nonce.encode('ascii'))
              and info['guardianPid']==guardian_proc.pid
              and info['uid']==1000,'GUARDIAN_NOT_READY_BOUND')
        print(json.dumps({'phase':'READY','version':1,
             'type':'alaz.wsl2.wrapperloss.test.v1',
             'runId':run,'nonce':nonce,'sourceSha256':expected,
             'guestUid':1000,'guardianPid':guardian_proc.pid,
             'workerPid':info['workerPid'],'grandchildPid':info['grandchildPid'],
             'hostFileIsolated':False,'secureExecutionAccepted':False,
             'realModelCalls':0},sort_keys=True,separators=(',',':')),flush=True)
        # Keep starter attached to WSL wrapper, intentionally interruptible.
        # Detached guardian controls owned worker regardless of starter.
        time.sleep(14)
        return 0
    except Exception:
        # Even if no host acknowledgement, detached guardian TTL closes
        # test-owned worker. Do not remove an uncertain root or retry.
        print('{"phase":"REFUSED","code":"GUEST_START_UNKNOWN"}',flush=True)
        return 2

def main():
    args=argparse.ArgumentParser(allow_abbrev=False)
    args.add_argument('--run-id',required=True)
    args.add_argument('--nonce',required=True)
    args.add_argument('--source-sha256',required=True)
    args.add_argument('--guardian',action='store_true')
    args.add_argument('--private-root')
    a=args.parse_args()
    try:
        check(hexid(a.run_id,24) and hexid(a.nonce,64)
              and hexid(a.source_sha256,64),'BOUND_REQUEST_INVALID')
        if a.guardian:
            check(type(a.private_root) is str and
                  a.private_root.startswith('/tmp/alaz-plat002d-'),
                  'GUARDIAN_ROOT_ARGUMENT')
            return guardian(a.run_id,a.nonce,a.source_sha256,Path(a.private_root))
        check(a.private_root is None,'STARTER_ROOT_CANNOT_BE_SUPPLIED')
        return starter(a.run_id,a.nonce,a.source_sha256)
    except Exception:
        print('{"phase":"REFUSED","code":"GUEST_PROBE_NOT_ACCEPTED"}',flush=True)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
