"""PLAT-002D second independent one-shot Windows WSL-wrapper loss QA.

Only terminate the wsl.exe Popen child THIS test created, never a PID
enumerated elsewhere. Native Linux guardian owns one fixed nonnetwork
worker and grandchild with 7s nonrenewable lease. Result of the
interrupted operation remains UNKNOWN, never automatically replayed.
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
import time

ROOT=Path(__file__).resolve().parents[2]
GUEST=ROOT/'scripts/qa/wsl2_wrapperloss_guest.py'
OBSERVER=ROOT/'scripts/qa/wsl2_wrapperloss_observe.py'
RECEIPT=ROOT/'evidence/plat-002d-wrapperloss-20oct/native-wrapperloss-02.json'
TYPE='alaz.wsl2.wrapperloss.test.v1'
# Separate fresh QA pilot after original 7s READY timeout with zero residue.
READY_TIMEOUT_SECONDS=20

class Refused(ValueError):pass
def need(ok,reason):
    if not ok:raise Refused(reason)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def sha_file(path):
    return sha(path.read_bytes())

def trusted_path(p):
    need(p.is_file() and not p.is_symlink(),'SOURCE_NOT_REGULAR')
    raw=str(p.resolve(strict=True))
    need(re.fullmatch('[A-Za-z]:\\\\[A-Za-z0-9_.\\\\-]{15,340}',raw)
         is not None,'PINNED_WINDOWS_PATH_UNMAPPABLE')
    return '/mnt/'+raw[0].lower()+'/'+raw[3:].replace('\\','/')

def host_wsl():
    need(sys.platform=='win32','WINDOWS_HOST_REQUIRED')
    root=os.environ.get('SystemRoot','')
    need(re.fullmatch('[A-Za-z]:\\\\Windows',root,re.IGNORECASE)
         is not None,'WINDOWS_SYSTEMROOT_INVALID')
    exe=Path(root)/'System32'/'wsl.exe'
    need(exe.is_file() and not exe.is_symlink(),'FIXED_WSL_EXE_REQUIRED')
    return str(exe)

def validated_ready(reply,expected):
    need(type(reply) is dict and set(reply)=={
      'phase','version','type','runId','nonce','sourceSha256',
      'guestUid','guardianPid','workerPid','grandchildPid',
      'hostFileIsolated','secureExecutionAccepted','realModelCalls'},
      'READY_REPLY_FIELDS')
    need(reply['phase']=='READY' and type(reply['version']) is int
      and reply['version']==1 and reply['type']==TYPE
      and reply['runId']==expected['runId']
      and reply['nonce']==expected['nonce']
      and reply['sourceSha256']==expected['sourceSha256'],
      'READY_BINDING_NOT_VERIFIED')
    need(type(reply['guestUid']) is int and reply['guestUid']==1000,
         'GUEST_UID_INCORRECT')
    pids=[reply[k] for k in ('guardianPid','workerPid','grandchildPid')]
    need(all(type(p) is int and p>1 for p in pids)
         and len(set(pids))==3,'GUEST_PIDS_NOT_DISTINCT')
    need(reply['hostFileIsolated'] is False
         and reply['secureExecutionAccepted'] is False
         and type(reply['realModelCalls']) is int
         and reply['realModelCalls']==0,'FALSE_GUARD_OR_MODEL_CLAIM')
    return True

def validated_audit(value,expected):
    need(type(value) is dict and value.get('runId')==expected['runId']
        and value.get('sourceSha256')==expected['sourceSha256']
        and value.get('nonceSha256')==expected['nonceSha256']
        and value.get('state') in ('CLOSED_LEASE_OUTCOME_UNKNOWN',
                                  'UNKNOWN_NOT_PROVEN_CLOSED',
                                  'NO_OWNED_ROOT','CLEANED_VERIFIED_TEST_ROOT')
        and value.get('externalEffectOutcome')=='UNKNOWN_DO_NOT_REPLAY'
        and value.get('fullD3BAccepted') is False
        and value.get('realModelCalls')==0
        and value.get('unreadableProcEntries')==0,
        'AUDIT_CANNOT_AUTHORIZE_REPLAY')
    return True

def read_first_line(child,seconds):
    q=queue.Queue(maxsize=1)
    def receive():
        try:q.put(child.stdout.readline(4097),block=False)
        except (OSError,ValueError):
            try:q.put(b'',block=False)
            except queue.Full:pass
    threading.Thread(target=receive,daemon=True).start()
    try:payload=q.get(timeout=seconds)
    except queue.Empty:raise Refused('READY_TIMEOUT_UNKNOWN') from None
    need(type(payload) is bytes and 0<len(payload)<=4096
         and payload.endswith(b'\n') and payload.count(b'\n')==1,
         'READY_FRAME_INVALID')
    try:return json.loads(payload)
    except (UnicodeError,ValueError):
        raise Refused('READY_JSON_INVALID') from None

def observe(mode,expected,wsl):
    need(mode in ('observe','cleanup'),'AUDIT_MODE_INVALID')
    cmd=[wsl,'--distribution','Ubuntu','--exec','/usr/bin/python3',
         '-I','-B',trusted_path(OBSERVER),
         '--mode',mode,'--run-id',expected['runId'],
         '--source-sha256',expected['sourceSha256'],
         '--nonce-sha256',expected['nonceSha256'],
         '--observer-sha256',expected['observerSha256']]
    z=subprocess.run(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,
          capture_output=True,timeout=15,check=False)
    need(z.returncode==0 and 0<len(z.stdout)<=10000
         and z.stdout.count(b'\n')==1,
         'AUDITOR_NONZERO_UNKNOWN')
    try:reply=json.loads(z.stdout)
    except (ValueError,UnicodeError):
        raise Refused('AUDITOR_JSON_INVALID') from None
    validated_audit(reply,expected)
    return reply

def one_native_test():
    wsl=host_wsl()
    guest=trusted_path(GUEST)
    observer=trusted_path(OBSERVER)
    expected={
        'runId':secrets.token_hex(12),
        'nonce':secrets.token_hex(32),
        'sourceSha256':sha_file(GUEST),
        'observerSha256':sha_file(OBSERVER),
    }
    expected['nonceSha256']=sha(expected['nonce'].encode('ascii'))
    child=None
    status='UNKNOWN_NOT_REPLAYED'
    ready=None
    terminal=None
    cleaned=None
    after=None
    wrapper_exit=None
    wrapper_terminated=False
    issue=None
    try:
        child=subprocess.Popen(
           [wsl,'--distribution','Ubuntu','--exec','/usr/bin/python3',
            '-I','-B',guest,
            '--run-id',expected['runId'],
            '--nonce',expected['nonce'],
            '--source-sha256',expected['sourceSha256']],
           cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
           stderr=subprocess.DEVNULL,shell=False,close_fds=True,
           creationflags=subprocess.CREATE_NO_WINDOW)
        ready=read_first_line(child,READY_TIMEOUT_SECONDS)
        validated_ready(ready,expected)
        # The ONLY deliberate Windows termination targets the exact
        # Popen wrapper handle created by this test; no taskkill/pid scan.
        need(child.poll() is None and child.pid>1,
             'OWNED_WINDOWS_WRAPPER_ALREADY_EXITED')
        child.terminate()
        wrapper_exit=child.wait(timeout=4)
        wrapper_terminated=True
        status='WRAPPER_INTERRUPTED_OPERATION_UNKNOWN'
    except (Refused,ValueError,subprocess.TimeoutExpired,OSError) as error:
        issue=(error.args[0] if isinstance(error,Refused)
               else 'WSL_START_OR_WRAPPER_OUTCOME_UNKNOWN')
    finally:
        if child is not None:
            if child.poll() is None:
                try:
                    # Still only the original test-owned Popen process.
                    child.terminate()
                    child.wait(timeout=3)
                except (subprocess.TimeoutExpired,PermissionError,OSError):
                    issue='OWNED_WRAPPER_TERMINATION_UNKNOWN'
            if child.stdout is not None:
                try:child.stdout.close()
                except OSError:pass
    # One test run, no agent task replay. Sleep beyond both the
    # guardian's 7s TTL and the starter's <=14s lifetime.
    time.sleep(16)
    try:
        terminal=observe('observe',expected,wsl)
        if wrapper_terminated and terminal['state']=='CLOSED_LEASE_OUTCOME_UNKNOWN':
            cleaned=observe('cleanup',expected,wsl)
            need(cleaned['state']=='CLEANED_VERIFIED_TEST_ROOT'
                 and cleaned['rootPresentAfterCleanup'] is False,
                 'INDEPENDENT_CLEANUP_UNPROVEN')
            after=observe('observe',expected,wsl)
            need(after['state']=='NO_OWNED_ROOT' and
                 after['matchingProcesses']==[],
                 'POST_CLEANUP_GUEST_NOT_EMPTY')
            status='PASS_SCOPED_LEASE_CLOSED_EXTERNAL_OUTCOME_UNKNOWN'
        else:
            status='FAIL_OR_UNKNOWN_GUEST_LEASE'
    except (Refused,ValueError,subprocess.TimeoutExpired,OSError) as error:
        issue=(error.args[0] if isinstance(error,Refused)
               else 'INDEPENDENT_AUDIT_OUTCOME_UNKNOWN')
        status='FAIL_OR_UNKNOWN_GUEST_LEASE'
    return {
      'gate':'PLAT-002D_TEST_OWNED_WRAPPER_LOSS',
      'scope':'one_native_test_owned_wsl_wrapper_and_fixed_guest_lease',
      'status':status,'externalToolOutcome':'UNKNOWN_DO_NOT_REPLAY',
      'runId':expected['runId'],
      'nonceSha256':expected['nonceSha256'],
      'nativeGuestSourceSha256':expected['sourceSha256'],
      'nativeObserverSourceSha256':expected['observerSha256'],
      'readyBindingVerified':ready is not None and
          all(ready.get(k)==expected[k] for k in ('runId','nonce','sourceSha256')),
      'readyGuestUid':ready.get('guestUid') if ready else None,
      'wrapperOwnedProcessTerminated':wrapper_terminated,
      'wrapperExitCode':wrapper_exit,
      'observedResult':terminal,
      'cleanupResult':cleaned,
      'postCleanupObserved':after,
      'errorCode':issue,
      'automaticRetry':False,
      'noTaskOutputReplayed':True,
      'realModelCalls':0,'fullPLAT002Accepted':False,'fullD3BAccepted':False,
      'windowsHostFilesystemIsolated':False,'separateBrokerHostUidVerified':False,
      'macOsNativeTested':False,'mainMerged':False,
    }

def main():
    if (sys.argv[1:]!=['--explicit-owned-wrapper-loss-v2']
        or os.environ.get('ALAZ_PLAT002D_TEST_WRAPPER_LOSS_V2')!='1'
        or RECEIPT.exists() or RECEIPT.is_symlink()
        or not RECEIPT.parent.is_dir()):
        print('{"status":"REFUSED","code":"ONE_SHOT_QA_OPT_IN_REQUIRED"}')
        return 2
    try:record=one_native_test()
    except Exception:
        record={'gate':'PLAT-002D_TEST_OWNED_WRAPPER_LOSS',
           'status':'FAIL_NATIVE_OUTCOME_UNKNOWN',
           'externalToolOutcome':'UNKNOWN_DO_NOT_REPLAY',
           'realModelCalls':0,'fullPLAT002Accepted':False,
           'fullD3BAccepted':False,'automaticRetry':False}
    with RECEIPT.open('x',encoding='utf-8') as f:
        json.dump(record,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'status':record['status'],
        'externalToolOutcome':'UNKNOWN_DO_NOT_REPLAY',
        'realModelCalls':0,'fullD3BAccepted':False,
        'receipt':'evidence/plat-002d-wrapperloss-20oct/native-wrapperloss-01.json'}))
    return 0 if record['status']=='PASS_SCOPED_LEASE_CLOSED_EXTERNAL_OUTCOME_UNKNOWN' else 1

if __name__=='__main__':
    raise SystemExit(main())
