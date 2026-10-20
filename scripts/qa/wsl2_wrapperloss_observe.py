"""PLAT-002D fixed read-only independent guest lease observer.

Optionally delete ONLY an exactly identified, completely verified and
closed, owned test root. Does not start or terminate any process,
read outside fixed /tmp test files, launch models or alter host config.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys

ROOT_PREFIX='alaz-plat002d-'
SOURCE_NAME='wsl2_wrapperloss_guest.py'
TYPE='alaz.wsl2.wrapperloss.test.v1'

class Refused(ValueError):pass
def require(ok,why):
    if not ok:raise Refused(why)
def digest(data):
    return hashlib.sha256(data).hexdigest()
def sha_valid(value,n):
    return type(value) is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',value) is not None

def ensure_guest():
    require(sys.platform=='linux' and platform.machine()=='x86_64' and
            'microsoft' in platform.release().lower() and
            'wsl2' in platform.release().lower(),'UNVERIFIED_GUEST')
    require(os.getuid()==1000 and os.geteuid()==1000,'WRONG_HOST_IDENTITY')

def exact_root(run):
    roots=[p for p in Path('/tmp').glob(ROOT_PREFIX+run+'-*')]
    require(len(roots)<=1,'DUPLICATE_OWNED_TEST_ROOTS')
    if not roots:return None
    p=roots[0]
    require(p.parent==Path('/tmp') and
            p.name.startswith(ROOT_PREFIX+run+'-') and
            p.is_dir() and not p.is_symlink(),'TEST_ROOT_NOT_ORDINARY')
    meta=p.stat()
    require(meta.st_uid==os.getuid()
            and stat.S_IMODE(meta.st_mode)==0o700,
            'TEST_ROOT_OWNER_MODE_INVALID')
    names={f.name for f in p.iterdir()}
    require(names.issubset({SOURCE_NAME,'ready.json','result.json'}),
            'UNEXPECTED_TEST_FILES')
    for f in p.iterdir():
        st=f.lstat()
        require(stat.S_ISREG(st.st_mode) and st.st_uid==os.getuid()
                and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,
                'UNTRUSTED_LEDGER_SOURCE_OBJECT')
    return p

def load_record(folder,name,maxlen=3500):
    f=folder/name
    require(f.is_file() and not f.is_symlink() and f.stat().st_size<=maxlen,
            'LEDGER_MISSING_OR_OVERSIZED')
    data=f.read_bytes()
    require(data.endswith(b'\n') and data.count(b'\n')==1,
            'LEDGER_FRAME_MALFORMED')
    value=json.loads(data)
    require(type(value) is dict,'LEDGER_WRONG_TYPE')
    return value

def get_stat(pid):
    try:
        s=(Path('/proc')/str(pid)/'stat').read_text(encoding='ascii',errors='replace')
        tail=s.rsplit(') ',1)[1].split()
        return {'state':tail[0],'pgid':int(tail[2]),'startTick':int(tail[19])}
    except (FileNotFoundError,ProcessLookupError):
        return None

def scan_current(run):
    # Exact process-argument token. Exclude this observer and never
    # mistake a code string containing the run id for a test-owned proc.
    pid_list=[]
    unreadable=0
    scanned=0
    for item in Path('/proc').iterdir():
        if not item.name.isdecimal():continue
        pid=int(item.name)
        if pid==os.getpid():continue
        try:
            raw=(item/'cmdline').read_bytes()[:8192]
        except (PermissionError,OSError):
            unreadable+=1
            continue
        scanned+=1
        tokens=raw.split(b'\x00')
        if run.encode('ascii') in tokens:
            st=get_stat(pid)
            pid_list.append({'pid':pid,'state':st['state'] if st else 'GONE'})
    return {'matching':pid_list,'scanned':scanned,'unreadable':unreadable}

def closure(run,expected,nonce_hash):
    ensure_guest()
    require(sha_valid(run,24) and sha_valid(expected,64)
            and sha_valid(nonce_hash,64),'REQUEST_FIELDS_INVALID')
    root=exact_root(run)
    survey=scan_current(run)
    result={'runId':run,'sourceSha256':expected,
            'nonceSha256':nonce_hash,
            'rootPresent':root is not None,'rootName':root.name if root else None,
            'matchingProcesses':survey['matching'],
            'procEntriesInspected':survey['scanned'],
            'unreadableProcEntries':survey['unreadable'],
            'externalEffectOutcome':'UNKNOWN_DO_NOT_REPLAY',
            'fullD3BAccepted':False,'realModelCalls':0}
    if root is None:
        result['state']='NO_OWNED_ROOT'
        return result,root
    manifest=load_record(root,'ready.json')
    done=load_record(root,'result.json') if (root/'result.json').is_file() else None
    require(manifest.get('version')==1 and manifest.get('type')==TYPE
            and manifest.get('runId')==run
            and manifest.get('sourceSha256')==expected
            and manifest.get('nonceSha256')==nonce_hash
            and manifest.get('uid')==1000 and manifest.get('ready') is True
            and manifest.get('maxLeaseSec')==7
            and manifest.get('secureExecutionAccepted') is False
            and manifest.get('realModelCalls')==0,
            'MANIFEST_NOT_BOUND')
    for key in ('guardianPid','workerPid','grandchildPid',
                'guardianStartTick','workerStartTick','grandchildStartTick'):
        require(type(manifest.get(key)) is int and manifest[key]>0,
                'MANIFEST_PID_IDENTITY_INVALID')
    source=root/SOURCE_NAME
    require(source.is_file() and not source.is_symlink() and
            digest(source.read_bytes())==expected,
            'NATIVE_COPIED_SOURCE_CHANGED')
    result['pidsVerifiedFromManifest']=[
        manifest['guardianPid'],manifest['workerPid'],manifest['grandchildPid']]
    live=[]
    for prefix in ('guardian','worker','grandchild'):
        pid=manifest[prefix+'Pid']
        state=get_stat(pid)
        if state and state['startTick']==manifest[prefix+'StartTick']:
            live.append({'pid':pid,'state':state['state']})
    result['matchingManifestPidsStillPresent']=live
    if done is not None:
        require(done.get('version')==1 and done.get('type')==TYPE
                and done.get('runId')==run and
                done.get('sourceSha256')==expected and
                done.get('nonceSha256')==nonce_hash and
                done.get('guestUid')==1000
                and done.get('guardianPid')==manifest['guardianPid']
                and done.get('workerPid')==manifest['workerPid']
                and done.get('grandchildPid')==manifest['grandchildPid']
                and done.get('hostWrapperKillIsSuccess') is False
                and done.get('externalToolOutcome')=='UNKNOWN_DO_NOT_REPLAY'
                and done.get('fullD3BAccepted') is False
                and done.get('realModelCalls')==0,
                'TERMINAL_LEDGER_NOT_BOUND')
    result['nativeResultWritten']=done is not None
    result['leaseExpired']=done.get('leaseExpired') is True if done else False
    result['testOwnedProcessesReaped']=done.get('testOwnedProcessesReaped') is True if done else False
    result['terminal']=done.get('terminal') if done else 'PENDING_UNKNOWN'
    clear=(done is not None and
        done.get('leaseExpired') is True and
        done.get('testOwnedProcessesReaped') is True and
        done.get('terminal')=='LEASE_EXPIRED_OUTCOME_UNKNOWN' and
        not live and not survey['matching'] and
        survey['unreadable']==0)
    result['state']='CLOSED_LEASE_OUTCOME_UNKNOWN' if clear else 'UNKNOWN_NOT_PROVEN_CLOSED'
    return result,root

def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--mode',required=True,choices=['observe','cleanup'])
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--nonce-sha256',required=True)
    parser.add_argument('--observer-sha256',required=True)
    a=parser.parse_args()
    try:
        require(sha_valid(a.observer_sha256,64) and
                digest(Path(__file__).read_bytes())==a.observer_sha256,
                'OBSERVER_SOURCE_NOT_PINNED')
        result,root=closure(a.run_id,a.source_sha256,a.nonce_sha256)
        if a.mode=='cleanup':
            require(result['state']=='CLOSED_LEASE_OUTCOME_UNKNOWN'
                    and root is not None,'UNCLOSED_RUN_MUST_NOT_BE_REMOVED')
            # Three and ONLY three regular pinned test files may be
            # removed after independent closure. No broad rm/recursive delete.
            for name in (SOURCE_NAME,'ready.json','result.json'):
                f=root/name
                require(f.is_file() and not f.is_symlink(),'CLEANUP_TARGET_INVALID')
                f.unlink()
            root.rmdir()
            result['state']='CLEANED_VERIFIED_TEST_ROOT'
            result['rootPresentAfterCleanup']=root.exists()
            require(result['rootPresentAfterCleanup'] is False,
                    'CLEANUP_STILL_PRESENT')
        print(json.dumps(result,sort_keys=True,separators=(',',':')),flush=True)
        return 0
    except Exception:
        print('{"state":"REFUSED","code":"TEST_LEDGER_NOT_VERIFIED"}',flush=True)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
