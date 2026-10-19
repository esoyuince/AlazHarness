"""PLAT-002B opt-in Windows->Ubuntu rootless test-owned lifecycle QA.

No caller-controlled WSL path/command, no shell, no host/guest privileged
operation, no real model, no automatic retry, and immutable own receipt.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
GUEST=ROOT/'scripts/qa/wsl2_owned_lifecycle.py'
RECEIPT=ROOT/'evidence/plat-002b-lifecycle-19oct/native-owned-lifecycle-01.json'
CHECK_NAMES={
    'clean_exit_zero','clean_exit_reaped','term_exit_code','term_reaped',
    'kill_required_after_ignored_term','kill_exit_code','kill_reaped',
    'all_children_reaped'
}

def fixed_wsl_mount(path):
    # Only maps the bundled code path; not a reusable user path router.
    raw=str(path.resolve(strict=True))
    if not re.fullmatch(r'[A-Za-z]:\\[A-Za-z0-9_.\\-]{15,240}',raw):
        raise ValueError('not_a_fixed_repository_file')
    drive=raw[0].lower()
    return '/mnt/'+drive+'/'+raw[3:].replace('\\','/')

def validate_native(value,run_id,sha):
    return (
        type(value) is dict and value.get('result')==
            'PASS_SCOPED_LINUX_OWNED_CHILD_LIFECYCLE'
        and value.get('runId')==run_id
        and value.get('guestUid')==1000
        and value.get('sourceSha256')==sha
        and value.get('linuxFilesystem') in ('ext2/ext3','ext4')
        and value.get('sourceCopyExt4ShaVerified') is True
        and value.get('sourceCopyRemoved') is True
        and type(value.get('guestChildChecks')) is dict
        and set(value['guestChildChecks'])==CHECK_NAMES
        and all(x is True for x in value['guestChildChecks'].values())
        and value.get('guestChildChecksCount')==len(CHECK_NAMES)
        and value.get('guestOwnedChildrenReaped') is True
        and value.get('hostWslWrapperCancelVerified') is False
        and value.get('hostFilesystemIsolated') is False
        and value.get('separateHostUidVerified') is False
        and value.get('secureAdapterActivated') is False
        and value.get('fullD3BAccepted') is False
        and value.get('realModelCalls')==0
        and value.get('automaticRetry') is False
    )

def main():
    if (sys.platform!='win32' or sys.argv[1:]!=['--run-owned-once']
            or os.environ.get('ALAZ_PLAT002B_TEST_OWNED')!='1'
            or not GUEST.is_file() or not RECEIPT.parent.is_dir()
            or RECEIPT.exists() or RECEIPT.is_symlink()):
        print('{"result":"REFUSED","code":"EXPLICIT_OWNED_QA_REQUIRED"}')
        return 2
    fixed_exe=Path(os.environ.get('SystemRoot',''))/'System32'/'wsl.exe'
    if (not fixed_exe.is_file() or fixed_exe.is_symlink()):
        print('{"result":"REFUSED","code":"FIXED_WSL_UNAVAILABLE"}')
        return 2
    run_id=secrets.token_hex(6)
    raw=GUEST.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    cmd=[str(fixed_exe),'--distribution','Ubuntu','--exec',
         '/usr/bin/python3','-B',fixed_wsl_mount(GUEST),
         '--run-id',run_id,'--source-sha256',digest]
    # Exactly one execution, bounded; no echo of raw command/stderr.
    try:
        done=subprocess.run(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,
           capture_output=True,timeout=32,check=False)
        if done.returncode==0 and 0<len(done.stdout)<=6000:
            try:
                value=json.loads(done.stdout)
            except (ValueError,UnicodeError):
                value={}
        else:
            value={}
        valid=done.returncode==0 and validate_native(value,run_id,digest)
        state='PASS_SCOPED_TEST_OWNED_CHILDREN' if valid else 'FAIL_NATIVE'
        result={'status':state,'windowsWslWrapperExit':done.returncode,
                'guestReport':value if valid else {'result':'REFUSED_OR_UNVERIFIED'},
                'guestSourceSha256':digest,'realModelCalls':0,
                'guestChildLifeCycleVerified':bool(valid),
                'wslWrapperCancellationNativeVerified':False,
                'fullD3BAccepted':False,'noAutomaticRetry':True,
                'mainMerged':False}
    except subprocess.TimeoutExpired:
        result={'status':'FAIL_NATIVE_OUTCOME_UNKNOWN_TIMEOUT',
                'guestReport':{'result':'UNKNOWN'},'guestSourceSha256':digest,
                'guestChildLifeCycleVerified':False,
                'wslWrapperCancellationNativeVerified':False,
                'fullD3BAccepted':False,'realModelCalls':0,
                'noAutomaticRetry':True,'mainMerged':False}
    # Write both success and failure without replaying, never overwrite.
    with RECEIPT.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'status':result['status'],
                      'fullD3BAccepted':False,'realModelCalls':0,
                      'receipt':'evidence/plat-002b-lifecycle-19oct/native-owned-lifecycle-01.json'}))
    return 0 if result['status']=='PASS_SCOPED_TEST_OWNED_CHILDREN' else 1

if __name__=='__main__':
    raise SystemExit(main())
