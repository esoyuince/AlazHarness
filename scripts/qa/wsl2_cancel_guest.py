"""PLAT-002C bounded one-shot rootless Windows->WSL2 cancel protocol QA.

Uses exactly one private native Linux source copy and one fixed test-owned
child process group. This is NOT a general command runner or secure
Gateway adapter; host-wrapper midflight termination remains untested.
"""
from __future__ import annotations

import argparse
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

MAX_FRAME=1024
TYPE='alaz.wsl2.testcancel.v1'
WORKER_SCRIPT=(
    "import signal,time\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "print('WORKER_READY',flush=True)\n"
    "time.sleep(15)\n"
)

class Reject(ValueError):
    pass

def need(value,why):
    if not value:raise Reject(why)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'DUPLICATE_FIELD')
        result[key]=value
    return result

def parse_frame(data,phase,run_id,nonce=None):
    need(type(data) is bytes and 0<len(data)<=MAX_FRAME and
         data.endswith(b'\n') and data.count(b'\n')==1
         and b'\x00' not in data,'INVALID_FRAME')
    try:
        value=json.loads(data.decode('utf-8'),object_pairs_hook=unique_pairs)
    except (UnicodeError,json.JSONDecodeError):
        raise Reject('INVALID_JSON') from None
    fields={'version','action','runId','nonce'}
    if phase=='cancel':fields.add('reason')
    need(type(value) is dict and set(value)==fields,'INVALID_FIELDS')
    need(type(value['version']) is int and value['version']==1
         and type(value['action']) is str and value['action']==phase
         and type(value['runId']) is str and value['runId']==run_id,
         'INVALID_PROTOCOL')
    n=value['nonce']
    need(type(n) is str and re.fullmatch('[a-f0-9]{64}',n) is not None,
         'INVALID_NONCE')
    if nonce is not None:
        need(n==nonce,'NONCE_CHANGED')
    if phase=='cancel':
        need(type(value['reason']) is str and value['reason']=='user_cancel',
             'CANCEL_REASON_INVALID')
    return value

def read_one(timeout):
    fd=sys.stdin.buffer
    ready,_,_=select.select([fd],[],[],timeout)
    need(bool(ready),'FRAME_TIMEOUT')
    data=fd.readline(MAX_FRAME+1)
    need(bool(data),'FRAME_EOF')
    return data

def send(record):
    print(json.dumps(record,sort_keys=True,separators=(',',':')),flush=True)

def assert_guest():
    need(sys.platform=='linux' and platform.machine()=='x86_64',
         'LINUX_X64_REQUIRED')
    rel=platform.release().lower()
    need('microsoft' in rel and 'wsl2' in rel,'WSL2_GUEST_REQUIRED')
    need(os.getuid()==1000 and os.geteuid()==1000
         and os.getgid()==os.getegid(),
         'ROOTLESS_GUEST_UID_REQUIRED')

def native_dir(root):
    need(root.parent==Path('/tmp') and root.name.startswith('alaz-plat002c-')
         and not root.is_symlink(),'PRIVATE_NATIVE_ROOT_REQUIRED')
    st=root.stat()
    need(st.st_uid==os.getuid() and stat.S_ISDIR(st.st_mode)
         and stat.S_IMODE(st.st_mode)==0o700,'PRIVATE_NATIVE_OWNER_MODE')

def source_check(source,expected):
    need(source.is_file() and not source.is_symlink()
         and source.name=='wsl2_cancel_guest.py' and
         sha(source.read_bytes())==expected,'SOURCE_SHA_MISMATCH')

def owned_stop(c):
    if c is None:return
    if c.poll() is None:
        try:
            need(c.pid>1 and os.getpgid(c.pid)==c.pid,
                 'OWNED_CHILD_PROCESS_GROUP_MISMATCH')
            os.killpg(c.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:c.wait(timeout=4)
    except subprocess.TimeoutExpired:
        raise Reject('OWNED_CHILD_REAP_FAILED') from None

def inner(run_id,expected,root_arg):
    assert_guest()
    root=Path(root_arg)
    native_dir(root)
    file=Path(__file__).resolve(strict=True)
    need(file.parent==root,'SOURCE_NOT_IN_NATIVE_ROOT')
    source_check(file,expected)
    child=None
    cleanup_ok=False
    phase_ok=False
    ready_sent=False
    try:
        first=parse_frame(read_one(7),'start',run_id)
        nonce=first['nonce']
        child=subprocess.Popen([sys.executable,'-I','-B','-c',WORKER_SCRIPT],
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,cwd=root,close_fds=True,
                start_new_session=True,
                env={'PATH':'/usr/bin:/bin','LANG':'C',
                     'PYTHONDONTWRITEBYTECODE':'1'})
        r,_,_=select.select([child.stdout],[],[],4)
        need(bool(r) and child.stdout.readline(128)==b'WORKER_READY\n',
             'OWNED_WORKER_NOT_READY')
        need(child.pid>1 and os.getpgid(child.pid)==child.pid,
             'OWNED_CHILD_PGID_INVALID')
        send({'version':1,'type':TYPE,'phase':'READY',
              'runId':run_id,'nonce':nonce,'sourceSha256':expected,
              'guestUid':os.getuid(),'workerPid':child.pid,
              'secureExecutionAccepted':False,
              'hostFilesystemIsolated':False,'realModelCalls':0})
        ready_sent=True
        parse_frame(read_one(7),'cancel',run_id,nonce)
        need(child.poll() is None,'OWNED_CHILD_EXITED_BEFORE_CANCEL')
        os.killpg(child.pid,signal.SIGTERM)
        ignored_term=False
        try:child.wait(timeout=0.35)
        except subprocess.TimeoutExpired:ignored_term=True
        need(ignored_term,'TEST_CHILD_DID_NOT_IGNORE_TERM')
        if child.poll() is None:
            need(os.getpgid(child.pid)==child.pid,'OWNED_CHILD_PGID_REPLACED')
            os.killpg(child.pid,signal.SIGKILL)
        need(child.wait(timeout=4)==-signal.SIGKILL,'OWNED_KILL_RESULT')
        need(child.poll()==-signal.SIGKILL,'OWNED_CHILD_NOT_REAPED')
        phase_ok=True
    finally:
        owned_stop(child)
        if child is not None and child.stdout is not None:
            child.stdout.close()
        # Remove only the owned, strictly verified single-file test root.
        native_dir(root)
        need(file.parent==root and file.is_file() and not file.is_symlink()
             and source_check(file,expected) is None,
             'SOURCE_CLEANUP_IDENTITY_MISMATCH')
        file.unlink()
        root.rmdir()
        cleanup_ok=not root.exists()
    need(phase_ok and ready_sent and cleanup_ok,'CANCEL_NOT_COMPLETE')
    send({'version':1,'type':TYPE,'phase':'CANCELLED',
          'runId':run_id,'nonce':nonce,'sourceSha256':expected,
          'guestUid':os.getuid(),'workerPid':child.pid,
          'workerIgnoredTerm':True,'workerKilled':True,
          'workerReaped':True,'sourceCopyRemoved':True,
          'ownedTempRootRemoved':True,
          'secureExecutionAccepted':False,
          'hostFilesystemIsolated':False,'realModelCalls':0})
    return 0

def outer(run_id,expected):
    assert_guest()
    original=Path(__file__).resolve(strict=True)
    need(original.parent!=Path('/tmp'),'OUTER_MUST_START_FROM_SOURCE_TREE')
    source_check(original,expected)
    root=Path(tempfile.mkdtemp(prefix='alaz-plat002c-',dir='/tmp'))
    root.chmod(0o700)
    native_dir(root)
    copy=root/original.name
    try:
        copy.write_bytes(original.read_bytes())
        copy.chmod(0o600)
        source_check(copy,expected)
        os.execve(sys.executable,[sys.executable,'-I','-B',str(copy),
                '--inner','--run-id',run_id,'--source-sha256',expected,
                '--private-root',str(root)],
                {'PATH':'/usr/bin:/bin','LANG':'C',
                 'PYTHONDONTWRITEBYTECODE':'1'})
    except Exception:
        if copy.exists() and not copy.is_symlink():copy.unlink()
        if root.exists():root.rmdir()
        raise

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--inner',action='store_true')
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--private-root')
    a=parser.parse_args()
    try:
        need(re.fullmatch('[a-f0-9]{24}',a.run_id or '') is not None,
             'BAD_RUN_ID')
        need(re.fullmatch('[a-f0-9]{64}',a.source_sha256 or '') is not None,
             'BAD_SHA')
        if a.inner:
            need(type(a.private_root) is str and a.private_root.startswith('/tmp/alaz-plat002c-'),
                 'PRIVATE_ROOT_REQUIRED')
            return inner(a.run_id,a.source_sha256,a.private_root)
        need(a.private_root is None,'OUTER_CANNOT_PICK_PRIVATE_ROOT')
        return outer(a.run_id,a.source_sha256)
    except Exception:
        # No uncontrolled retry, secret printing, or misleading DONE ACK.
        send({'result':'REFUSED','code':'PLAT002C_GUEST_NOT_ACCEPTED'})
        return 2

if __name__=='__main__':
    raise SystemExit(main())
