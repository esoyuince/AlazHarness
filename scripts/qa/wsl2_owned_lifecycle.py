"""PLAT-002B one-shot owned Linux subprocess lifecycle pilot.

NO Gateway, broker, network, model, privileged operation, production service,
external process termination, shell or retry. Test files/processes owned by
unprivileged WSL user and sourced from exact file SHA into private Linux /tmp.
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
import shutil
import signal
import subprocess
import sys
import tempfile
import time

class Refused(ValueError):
    pass

def require(condition,code):
    if not condition:raise Refused(code)

def source_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require_environment():
    require(sys.platform=='linux' and platform.machine()=='x86_64',
            'linux_x64_required')
    release=platform.release().lower()
    require('microsoft' in release and 'wsl2' in release,
            'wsl2_required')
    require(os.getuid()>0 and os.getuid()==os.geteuid(),
            'unprivileged_identity_required')
    require(os.getgid()==os.getegid(),
            'unprivileged_group_required')

def expected_tmp_type(folder):
    result=subprocess.run(['/usr/bin/stat','-f','-c','%T',str(folder)],
             capture_output=True,text=True,timeout=4,check=False)
    require(result.returncode==0 and
            result.stdout.strip() in ('ext2/ext3','ext4'),
            'private_native_linux_filesystem_required')
    return result.stdout.strip()

def launch(program,folder,*,stdio=subprocess.DEVNULL):
    # NO shell, no fd inheritance, and a new process group for owned children.
    return subprocess.Popen([sys.executable,'-I','-B','-c',program],
         cwd=folder,stdin=subprocess.DEVNULL,stdout=stdio,
         stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True,
         env={'PATH':'/usr/bin:/bin','LANG':'C','PYTHONDONTWRITEBYTECODE':'1'})

def terminate_owned(child):
    # Never signal any PID/process group except one we just created.
    if child.poll() is None:
        try:
            require(child.pid>1 and os.getpgid(child.pid)==child.pid,
                    'owned_process_group_required')
            os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:child.wait(timeout=4)
    except subprocess.TimeoutExpired:
        raise Refused('owned_child_unreaped') from None

def native_checks(folder):
    tests={}
    active=[]
    try:
        c=launch("print('PLAT002B_OK',flush=True)",folder,stdio=subprocess.PIPE)
        active.append(c)
        data,_=c.communicate(timeout=4)
        tests['clean_exit_zero']=c.returncode==0 and data==b'PLAT002B_OK\n'
        tests['clean_exit_reaped']=c.poll()==0

        c=launch("import time;time.sleep(15)",folder)
        active.append(c)
        require(c.pid>1 and os.getpgid(c.pid)==c.pid,
                'term_group_not_test_owned')
        os.killpg(c.pid,signal.SIGTERM)
        tests['term_exit_code']=c.wait(timeout=4)==-signal.SIGTERM
        tests['term_reaped']=c.poll()==-signal.SIGTERM

        script=("import signal,time\n"
                "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                "print('READY',flush=True)\n"
                "time.sleep(15)\n")
        c=launch(script,folder,stdio=subprocess.PIPE)
        active.append(c)
        ready,_,_=select.select([c.stdout],[],[],4)
        require(bool(ready) and c.stdout.readline()==b'READY\n',
                'kill_child_not_ready')
        require(c.pid>1 and os.getpgid(c.pid)==c.pid,
                'kill_group_not_test_owned')
        os.killpg(c.pid,signal.SIGTERM)
        try:
            c.wait(timeout=0.25)
            tests['kill_required_after_ignored_term']=False
        except subprocess.TimeoutExpired:
            tests['kill_required_after_ignored_term']=True
        if c.poll() is None:
            os.killpg(c.pid,signal.SIGKILL)
        tests['kill_exit_code']=c.wait(timeout=4)==-signal.SIGKILL
        tests['kill_reaped']=c.poll()==-signal.SIGKILL

        tests['all_children_reaped']=all(c.poll() is not None for c in active)
        return tests
    finally:
        for child in active:
            try:terminate_owned(child)
            except (Refused,ProcessLookupError,PermissionError):
                raise Refused('owned_child_cleanup_unknown') from None
            if child.stdout is not None:child.stdout.close()

def inner(run_id,expected):
    source=Path(__file__).resolve(strict=True)
    require(source.name=='wsl2_owned_lifecycle.py' and
            source_sha(source)==expected,'inner_source_mismatch')
    require_environment()
    root=source.parent
    require(root.name.startswith('alaz-plat002b-')
            and root.parent==Path('/tmp') and
            root.stat().st_uid==os.getuid()
            and not root.is_symlink(),'inner_private_root_required')
    fs=expected_tmp_type(root)
    checks=native_checks(root)
    result={
        'result':'PASS_GUEST_OWNED_PROCESS_LIFECYCLE' if all(checks.values())
                   else 'FAIL_GUEST_PROCESS_LIFECYCLE',
        'runId':run_id,'sourceSha256':expected,
        'linuxRootFsType':fs,'guestUid':os.getuid(),
        'checks':checks,'checksCount':len(checks),
        'testOwnedChildrenOnly':True,'shell':False,
        'realModelCalls':0,'hostWslWrapperCancelVerified':False,
        'fullD3BAccepted':False,
    }
    return result

def outer(run_id,expected):
    src=Path(__file__).resolve(strict=True)
    require(source_sha(src)==expected,'outer_source_mismatch')
    require_environment()
    require(src.parent!=Path('/tmp'),'stage_from_repo_only')
    source_root=None
    with tempfile.TemporaryDirectory(prefix='alaz-plat002b-',dir='/tmp') as tmp:
        folder=Path(tmp)
        folder.chmod(0o700)
        fs=expected_tmp_type(folder)
        target=folder/src.name
        with src.open('rb') as reader,target.open('xb') as writer:
            shutil.copyfileobj(reader,writer)
        target.chmod(0o600)
        require(source_sha(target)==expected,'source_copy_sha_mismatch')
        require(target.stat().st_uid==os.getuid() and not target.is_symlink(),
                'untrusted_native_copy')
        source_root=folder
        command=[sys.executable,'-I','-B',str(target),'--inner',
                 '--run-id',run_id,'--source-sha256',expected]
        runner=subprocess.run(command,cwd=folder,capture_output=True,
                              timeout=24,check=False,
                              env={'PATH':'/usr/bin:/bin','LANG':'C',
                                   'PYTHONDONTWRITEBYTECODE':'1'})
        require(runner.returncode==0 and
                runner.stdout.count(b'\n')==1 and
                len(runner.stdout)<=6000,
                'native_inner_lifecycle_failed')
        value=json.loads(runner.stdout)
        require(value.get('result')=='PASS_GUEST_OWNED_PROCESS_LIFECYCLE'
                and value.get('runId')==run_id and
                value.get('sourceSha256')==expected
                and value.get('linuxRootFsType')==fs
                and value.get('testOwnedChildrenOnly') is True
                and value.get('hostWslWrapperCancelVerified') is False
                and value.get('fullD3BAccepted') is False,
                'native_inner_receipt_invalid')
    require(source_root is not None and not source_root.exists(),
            'native_temp_cleanup_unproven')
    return {
        'result':'PASS_SCOPED_LINUX_OWNED_CHILD_LIFECYCLE',
        'runId':run_id,'guestUid':os.getuid(),
        'sourceSha256':expected,'linuxFilesystem':fs,
        'sourceCopyExt4ShaVerified':True,
        'sourceCopyRemoved':True,
        'guestChildChecks':value['checks'],
        'guestChildChecksCount':value['checksCount'],
        'guestOwnedChildrenReaped':True,
        'hostWslWrapperCancelVerified':False,
        'hostFilesystemIsolated':False,
        'separateHostUidVerified':False,
        'secureAdapterActivated':False,
        'fullD3BAccepted':False,
        'realModelCalls':0,
        'automaticRetry':False,
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--inner',action='store_true')
    a=parser.parse_args()
    try:
        require(re.fullmatch(r'[a-z0-9]{8,24}',a.run_id) is not None,
                'run_id_invalid')
        require(re.fullmatch(r'[a-f0-9]{64}',a.source_sha256) is not None,
                'source_sha_invalid')
        response=(inner(a.run_id,a.source_sha256) if a.inner
                  else outer(a.run_id,a.source_sha256))
        print(json.dumps(response,sort_keys=True,separators=(',',':')),
              flush=True)
        return 0 if response['result'].startswith('PASS_') else 1
    except Exception:
        # Paths, child process output, and command contents never emitted.
        print('{"result":"REFUSED","code":"LIFECYCLE_PILOT_NOT_ACCEPTED"}',
              flush=True)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
