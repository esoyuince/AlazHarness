"""PLAT-002C fixed one-run Windows/WSL2 test-owned cancel handshake.

No general tool/agent execution, user-supplied command, provider, auto retry,
privilege or Windows WSL-wrapper forced-cancellation acceptance.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import subprocess
import sys
import threading

ROOT=Path(__file__).resolve().parents[2]
GUEST=ROOT/'scripts/qa/wsl2_cancel_guest.py'
OUT=ROOT/'evidence/plat-002c-cancel-20oct/native-cancel-handshake-01.json'
TYPE='alaz.wsl2.testcancel.v1'
MAX_LINE=4096

class Rejected(ValueError):
    pass

def need(value,reason):
    if not value:raise Rejected(reason)

def source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fixed_linux_path(guest):
    s=str(guest.resolve(strict=True))
    need(re.fullmatch(r'[A-Za-z]:\\[A-Za-z0-9_.\\-]{15,280}',s) is not None,
         'BAD_PINNED_WINDOWS_PATH')
    return '/mnt/'+s[0].lower()+'/'+s[3:].replace('\\','/')

def validate_frame(body,expected,phase,ready=None):
    need(type(expected) is dict and
         set(expected)=={'runId','nonce','sha','uid'},
         'BAD_EXPECTATION')
    must={
      'version','type','phase','runId','nonce','sourceSha256',
      'guestUid','workerPid','secureExecutionAccepted',
      'hostFilesystemIsolated','realModelCalls',
    }
    if phase=='CANCELLED':
        must|={'workerIgnoredTerm','workerKilled','workerReaped',
               'sourceCopyRemoved','ownedTempRootRemoved'}
    need(type(body) is dict and set(body)==must,'REPLY_FIELDS')
    need(type(body['version']) is int and body['version']==1
         and type(body['type']) is str and body['type']==TYPE
         and type(body['phase']) is str and body['phase']==phase
         and body['runId']==expected['runId']
         and body['nonce']==expected['nonce']
         and body['sourceSha256']==expected['sha'],
         'WRONG_RUN_NONCE_SOURCE')
    need(type(body['guestUid']) is int and
         body['guestUid']==expected['uid']
         and type(body['workerPid']) is int and body['workerPid']>1,
         'WRONG_GUEST_UID_PID')
    need(body['secureExecutionAccepted'] is False
         and body['hostFilesystemIsolated'] is False
         and type(body['realModelCalls']) is int
         and body['realModelCalls']==0,
         'UNACCEPTED_SECURITY_CLAIM')
    if phase=='CANCELLED':
        need(ready is not None and
             body['workerPid']==ready['workerPid'],
             'WORKER_PID_CHANGED')
        for name in ('workerIgnoredTerm','workerKilled','workerReaped',
                     'sourceCopyRemoved','ownedTempRootRemoved'):
            need(body[name] is True,'GUEST_CANCEL_OR_CLEANUP_UNPROVEN')
    return True

def read_line(child,wait_seconds):
    # Windows pipes do not support select(). Read a single bounded line
    # in a daemon reader and time-bound the host, without logging raw stderr.
    q=queue.Queue(maxsize=1)
    def reader():
        try:q.put(child.stdout.readline(MAX_LINE+1),block=False)
        except (OSError,ValueError):
            try:q.put(b'',block=False)
            except queue.Full:pass
    threading.Thread(target=reader,daemon=True).start()
    try:line=q.get(timeout=wait_seconds)
    except queue.Empty:raise Rejected('GUEST_REPLY_UNKNOWN_TIMEOUT') from None
    need(type(line) is bytes and 0<len(line)<=MAX_LINE
         and line.endswith(b'\n') and line.count(b'\n')==1,
         'GUEST_REPLY_FRAME_INVALID')
    try:result=json.loads(line)
    except (ValueError,UnicodeError):
        raise Rejected('GUEST_REPLY_JSON_INVALID') from None
    return result

def run_cancel_once():
    need(sys.platform=='win32','WINDOWS_HOST_REQUIRED')
    need(GUEST.is_file() and not GUEST.is_symlink(),
         'PINNED_GUEST_SOURCE_REQUIRED')
    system=os.environ.get('SystemRoot','')
    need(re.fullmatch(r'[A-Za-z]:\\Windows',system,re.IGNORECASE),
         'WINDOWS_SYSTEM_ROOT_REQUIRED')
    wsl=Path(system)/'System32'/'wsl.exe'
    need(wsl.is_file() and not wsl.is_symlink(),
         'FIXED_WSL_UNAVAILABLE')
    expected={
      'runId':secrets.token_hex(12),
      'nonce':secrets.token_hex(32),
      'sha':source_hash(GUEST),'uid':1000,
    }
    cmd=[str(wsl),'--distribution','Ubuntu','--exec',
         '/usr/bin/python3','-I','-B',fixed_linux_path(GUEST),
         '--run-id',expected['runId'],
         '--source-sha256',expected['sha']]
    child=None
    try:
        child=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.PIPE,
              stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
              shell=False,creationflags=subprocess.CREATE_NO_WINDOW)
        start={'version':1,'action':'start',
               'runId':expected['runId'],'nonce':expected['nonce']}
        child.stdin.write((json.dumps(start,separators=(',',':'))+'\n').encode('utf-8'))
        child.stdin.flush()
        ready=read_line(child,18)
        validate_frame(ready,expected,'READY')
        cancel={'version':1,'action':'cancel','reason':'user_cancel',
                'runId':expected['runId'],'nonce':expected['nonce']}
        child.stdin.write((json.dumps(cancel,separators=(',',':'))+'\n').encode('utf-8'))
        child.stdin.flush()
        child.stdin.close()
        done=read_line(child,8)
        validate_frame(done,expected,'CANCELLED',ready)
        need(child.wait(timeout=7)==0,'WINDOWS_WSL_WRAPPER_NOT_EXITED_CLEANLY')
        return {
          'result':'PASS_EXPLICIT_CANCEL_HANDSHAKE_TEST_OWNED',
          'hostWslWrapperExit':0,'readyRunNonceSourceMatched':True,
          'cancelAckRunNonceSourceMatched':True,
          'guestUid':1000,'workerPid':ready['workerPid'],
          'workerIgnoredTerm':True,'workerKilled':True,
          'workerReaped':True,
          'nativeCopyRemoved':True,'nativeRootRemoved':True,
          'realModelCalls':0,'hostWslWrapperForcedCancelVerified':False,
          'hostFileIsolationAccepted':False,
          'fullPLAT002Accepted':False,'fullD3BAccepted':False,
          'automaticRetry':False,
        }
    except (Rejected,ValueError,subprocess.TimeoutExpired,OSError) as error:
        # Own WSL wrapper may be terminated on an UNKNOWN outcome.
        # Such action does NOT prove its Linux children were reaped.
        return {
          'result':'FAIL_OUTCOME_UNKNOWN_OR_REFUSED',
          'failureCode':error.args[0] if isinstance(error,Rejected)
                        else 'WSL_TRANSPORT_UNKNOWN',
          'guestPidClosure':'UNKNOWN','hostWslWrapperForcedCancelVerified':False,
          'fullPLAT002Accepted':False,'fullD3BAccepted':False,
          'realModelCalls':0,'automaticRetry':False,
        }
    finally:
        if child is not None:
            if child.poll() is None:
                try:
                    child.terminate()   # Only THIS controller-owned wrapper.
                    child.wait(timeout=2)
                except (subprocess.TimeoutExpired,PermissionError,OSError):
                    # No broad taskkill/WSL shutdown and no false cleanup claim.
                    pass
            for stream in (child.stdin,child.stdout):
                if stream:
                    try:stream.close()
                    except OSError:pass

def main():
    if (sys.argv[1:]!=['--explicit-test-cancel']
        or os.environ.get('ALAZ_PLAT002C_TEST_CANCEL')!='1'
        or OUT.exists() or OUT.is_symlink()
        or not OUT.parent.is_dir()):
        print('{"result":"REFUSED","code":"ONE_SHOT_QA_OPT_IN_REQUIRED"}')
        return 2
    result=run_cancel_once()
    # Never overwrite and never repeat an unknown guest result.
    with OUT.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'result':result['result'],
        'realModelCalls':0,'fullD3BAccepted':False,
        'receipt':'evidence/plat-002c-cancel-20oct/native-cancel-handshake-01.json'}))
    return 0 if result['result']=='PASS_EXPLICIT_CANCEL_HANDSHAKE_TEST_OWNED' else 1

if __name__=='__main__':
    raise SystemExit(main())
