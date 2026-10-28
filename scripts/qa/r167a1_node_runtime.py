"""Provision two pinned official Node files once in the dedicated P71C lab.

Preparation binds the already verified official signature receipt and freezes
the exact archive, driver and Linux transport. Apply reserves an exclusive
attempt before invoking WSL. No Node executable, service, package manager,
model, mount, overwrite, cleanup or automatic retry is part of this driver.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD = ROOT / 'scratch/r167-install/node-download-01'
DOWNLOAD_RECEIPT = DOWNLOAD / 'download-receipt-02.json'
CONFIG = {
    'lab': 'AlazHarness-D3B-P71C', 'version': '24.22.1',
    'destination': '/opt/alaz-r167a1-node-24.22.1',
    'receiptName': '.alaz-node-runtime.json',
    'archiveName': 'node-v24.22.1-linux-x64.tar.xz',
    'archiveBytes': 32026916,
    'archiveSha256': '6c172a9ab6718f7b801fb5a7bd486af2ee5e32758086a04b84fcce2aa77095e6',
    'archiveUrl': 'https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-x64.tar.xz',
    'releaseSigner': '5BE8A3F6C8A5C01D106C0AD820B1A390B168D356',
    'downloadReceiptSha256': 'd9f19fd0be92b466ea270c044c7b46725c6e97dc986cd23337a073519025e499',
    'python': '/usr/bin/python3.12',
    'pythonSha256': 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
    'oldReceipt': '/opt/alaz-r156a1/.alaz-installation.json',
    'oldReceiptSha256': 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845',
    'selectedMembers': {
        'bin/node': {'tarName': 'node-v24.22.1-linux-x64/bin/node',
            'bytes': 126879696, 'mode': 0o755,
            'sha256': 'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb'},
        'LICENSE': {'tarName': 'node-v24.22.1-linux-x64/LICENSE',
            'bytes': 157609, 'mode': 0o644,
            'sha256': '5888dbb9a1d2b18f2c3e6c5f6af1b39de658372b402a0577b002777f14c62ace'},
    },
}
MAX_ARCHIVE = 64 * 1024 * 1024
PREPARED_FILES = {'intent.json', 'input.tar.xz', 'download-receipt.json',
                  'linux-transport.py', 'reviewed-runner.py'}


# The same fixed selector executes on both sides. It never extracts a pathname.
SELECTION_CODE = r'''
def select_members(raw):
    def require(ok, reason):
        if not ok: raise ValueError(reason)
    require(type(raw) is bytes and len(raw)==CONFIG['archiveBytes']
            and len(raw)<=64*1024*1024
            and hashlib.sha256(raw).hexdigest()==CONFIG['archiveSha256'], 'node_archive_identity')
    wanted={item['tarName']:name for name,item in CONFIG['selectedMembers'].items()}
    selected={}; seen=0; expanded=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:xz') as archive:
        for member in archive:
            seen+=1; expanded+=member.size
            require(seen<=10000 and type(member.size) is int and 0<=member.size<=256*1024*1024
                    and expanded<=512*1024*1024, 'node_archive_expansion_bound')
            if member.name not in wanted: continue
            name=wanted[member.name]; expected=CONFIG['selectedMembers'][name]
            require(name not in selected and member.isreg() and member.sparse is None
                    and not member.linkname and member.size==expected['bytes']
                    and member.mode==expected['mode'], 'node_selected_member_metadata')
            with archive.extractfile(member) as stream:
                value=stream.read(expected['bytes']+1)
            require(len(value)==expected['bytes']
                    and hashlib.sha256(value).hexdigest()==expected['sha256'], 'node_selected_member_identity')
            selected[name]=value
    require(set(selected)==set(CONFIG['selectedMembers']), 'node_selected_member_inventory')
    node=selected['bin/node']
    require(node[:6]==b'\x7fELF\x02\x01' and node[18:20]==b'\x3e\x00'
            and node[16:18] in (b'\x02\x00',b'\x03\x00'), 'node_selected_member_elf')
    return selected
'''


LINUX_BODY = r'''
import ctypes,errno,os,pathlib,stat,sys
def require(ok,reason):
    if not ok: raise ValueError(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
def stamp(s):return(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def trusted(s,directory):
    require((stat.S_ISDIR(s.st_mode) if directory else stat.S_ISREG(s.st_mode))
            and s.st_uid==s.st_gid==0 and not s.st_mode&0o022,'node_untrusted_entry')
    if not directory:require(s.st_nlink==1,'node_hardlink_refused')
def directory(path):
    value=pathlib.PurePosixPath(path)
    require(value.is_absolute() and str(value)==str(path) and '..' not in value.parts,'node_noncanonical_path')
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
    fd=os.open('/',flags)
    try:
        trusted(os.fstat(fd),True)
        for part in value.parts[1:]:
            child=os.open(part,flags,dir_fd=fd);os.close(fd);fd=child
            trusted(os.fstat(fd),True)
        return fd
    except BaseException:os.close(fd);raise
def read_at(parent,name,maximum):
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent)
    try:
        before=os.fstat(fd);trusted(before,False)
        require(0<=before.st_size<=maximum,'node_read_bound')
        chunks=[];size=0
        while True:
            part=os.read(fd,min(1024*1024,maximum-size+1))
            if not part:break
            size+=len(part);require(size<=maximum,'node_read_bound');chunks.append(part)
        require(size==before.st_size and stamp(before)==stamp(os.fstat(fd)),'node_read_changed')
        return b''.join(chunks),before
    finally:os.close(fd)
def read_path(path,maximum):
    value=pathlib.PurePosixPath(path);fd=directory(value.parent)
    try:return read_at(fd,value.name,maximum)
    finally:os.close(fd)
def put(parent,name,raw,mode):
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view);require(count>0,'node_short_write');view=view[count:]
        os.fchmod(fd,mode);os.fsync(fd)
    finally:os.close(fd)
def absent(parent,name):
    try:os.stat(name,dir_fd=parent,follow_symlinks=False)
    except FileNotFoundError:return
    raise ValueError('node_destination_exists')
def rename(parent,source,destination):
    libc=ctypes.CDLL(None,use_errno=True)
    try:call=libc.renameat2
    except AttributeError:raise ValueError('node_atomic_publish_unavailable')
    call.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    call.restype=ctypes.c_int
    if call(parent,os.fsencode(source),parent,os.fsencode(destination),1):
        code=ctypes.get_errno()
        raise ValueError('node_destination_exists' if code==errno.EEXIST else 'node_atomic_publish_failed')
def entries(fd):
    with os.scandir(fd) as values:return {item.name for item in values}
def file_record(parent,name,expected):
    raw,info=read_at(parent,name,expected['bytes'])
    require(len(raw)==expected['bytes'] and sha(raw)==expected['sha256']
            and stat.S_IMODE(info.st_mode)==expected['mode'],'node_installed_member_changed')
    return {'sha256':sha(raw),'bytes':len(raw),'mode':stat.S_IMODE(info.st_mode),
            'device':info.st_dev,'inode':info.st_ino,'uid':info.st_uid,'gid':info.st_gid}
def old_receipt():
    raw,info=read_path(CONFIG['oldReceipt'],2*1024*1024)
    require(sha(raw)==CONFIG['oldReceiptSha256'],'node_old_installation_changed')
    return {'sha256':sha(raw),'device':info.st_dev,'inode':info.st_ino,'bytes':len(raw)}

report={'kind':'R167_NODE24_PROVISION_OPERATION','phase':'PREFLIGHT','installed':False,
        'nodeExecuted':False,'runtimeVersionReadback':'NOT_RUN','serviceStarted':False,
        'kernelAcceptance':False,'realModelCalls':0,'automaticRetry':False,'automaticCleanup':False,
        'stageCreated':False,'destinationPublished':False,'receiptPublished':False}
parent=root=binfd=None;dest=pathlib.PurePosixPath(CONFIG['destination']);stage=None
try:
    require(len(sys.argv)==2,'node_transport_arguments')
    intent=json.loads(sys.argv[1])
    require(type(intent) is dict and intent.get('kind')=='R167_NODE24_PROVISION_INTENT'
            and canonical(intent.get('config'))==canonical(CONFIG),'node_intent_identity')
    require(type(intent.get('attemptToken')) is str and re.fullmatch('[0-9a-f]{32}',intent['attemptToken']),
            'node_attempt_token')
    require(all(intent.get(k) is False for k in ('nodeExecutionAuthorized','automaticRetry','automaticCleanup')),
            'node_execution_scope')
    require(os.environ.get('WSL_DISTRO_NAME')==CONFIG['lab'],'node_lab_environment')
    marker,_=read_path('/etc/alaz-p71c-lab-id',256)
    require(marker.decode('ascii').strip()==CONFIG['lab'],'node_lab_marker')
    require(not pathlib.Path('/mnt/c/Windows').exists(),'node_windows_mount_present')
    require(sys.platform=='linux' and os.uname().machine=='x86_64'
            and sys.version_info[:2]==(3,12) and sys.executable==CONFIG['python']
            and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize,
            'node_transport_interpreter')
    require(os.getresuid()==os.getresgid()==(0,0,0),'node_initial_root_actor')
    for name in ('uid_map','gid_map'):
        require(pathlib.Path('/proc/self',name).read_text().split()==['0','0','4294967295'],'node_initial_userns')
    require(os.readlink('/proc/self/ns/user')==os.readlink('/proc/1/ns/user'),'node_initial_userns_identity')
    python_raw,_=read_path(CONFIG['python'],64*1024*1024)
    require(sha(python_raw)==CONFIG['pythonSha256'],'node_python_changed')
    old_before=old_receipt()
    mounts_before=sha(pathlib.Path('/proc/self/mountinfo').read_bytes())
    mount_ns=os.readlink('/proc/self/ns/mnt')
    parent=directory(dest.parent);absent(parent,dest.name)
    stage='.'+dest.name+'.partial-'+intent['attemptToken']
    require(intent.get('partialPath')==str(dest.parent/stage),'node_intent_partial_path')
    absent(parent,stage)
    raw=sys.stdin.buffer.read(64*1024*1024+1)
    payload=select_members(raw)
    report['phase']='WRITING_NEW_NODE_FILES'
    os.mkdir(stage,0o700,dir_fd=parent);report['stageCreated']=True
    root=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
    trusted(os.fstat(root),True)
    os.mkdir('bin',0o700,dir_fd=root)
    binfd=os.open('bin',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
    trusted(os.fstat(binfd),True);os.fchmod(binfd,0o755)
    put(binfd,'node',payload['bin/node'],0o755)
    put(root,'LICENSE',payload['LICENSE'],0o644)
    os.fsync(binfd);os.fsync(root)
    require(entries(root)=={'bin','LICENSE'} and entries(binfd)=={'node'},'node_stage_inventory')
    node=file_record(binfd,'node',CONFIG['selectedMembers']['bin/node'])
    license=file_record(root,'LICENSE',CONFIG['selectedMembers']['LICENSE'])
    require(old_receipt()==old_before and sha(pathlib.Path('/proc/self/mountinfo').read_bytes())==mounts_before
            and os.readlink('/proc/self/ns/mnt')==mount_ns,'node_preservation_before_publish')
    os.fchmod(root,0o755);os.fsync(root)
    rename(parent,stage,dest.name);report['destinationPublished']=True;os.fsync(parent)
    report['phase']='PUBLISHED_NODE_FILES_PENDING_RECEIPT'
    # Resolve the published pathname again and compare it with the held stage.
    current=directory(dest)
    try:require(stamp(os.fstat(current))==stamp(os.fstat(root)),'node_destination_path_changed')
    finally:os.close(current)
    old_after=old_receipt();mounts_after=sha(pathlib.Path('/proc/self/mountinfo').read_bytes())
    require(old_after==old_before and mounts_after==mounts_before
            and os.readlink('/proc/self/ns/mnt')==mount_ns,'node_preservation_after_publish')
    info=os.fstat(root)
    receipt={'schemaVersion':1,'kind':'VERIFIED_NODE_RUNTIME_FILES','distributionVersion':CONFIG['version'],
        'destination':str(dest),'rootDevice':info.st_dev,'rootInode':info.st_ino,
        'archiveSha256':CONFIG['archiveSha256'],'archiveBytes':CONFIG['archiveBytes'],
        'archiveUrl':CONFIG['archiveUrl'],'releaseSigner':CONFIG['releaseSigner'],
        'downloadReceiptSha256':CONFIG['downloadReceiptSha256'],
        'operatorIntentSha256':sha(canonical(intent)),'node':node,'license':license,
        'oldInstallationReceipt':old_after,'mountInfoSha256':mounts_after,'mountNamespace':mount_ns,
        'sourceFilesReadBack':True,'installed':True,'nodeExecuted':False,
        'runtimeVersionReadback':'NOT_RUN','serviceStarted':False,'kernelAcceptance':False,'realModelCalls':0}
    receipt_raw=canonical(receipt);pending=CONFIG['receiptName']+'.pending'
    put(root,pending,receipt_raw,0o644)
    observed,_=read_at(root,pending,2*1024*1024)
    require(observed==receipt_raw,'node_receipt_readback')
    os.fsync(root);rename(root,pending,CONFIG['receiptName']);report['receiptPublished']=True;os.fsync(root)
    require(entries(root)=={'bin','LICENSE',CONFIG['receiptName']} and entries(binfd)=={'node'},
            'node_final_inventory')
    require(old_receipt()==old_before and sha(pathlib.Path('/proc/self/mountinfo').read_bytes())==mounts_before,
            'node_final_preservation')
    report.update(phase='NODE_FILES_PROVISIONED_NOT_EXECUTED',installed=True,
        receipt=receipt,receiptSha256=sha(receipt_raw),oldInstallationPreserved=True,mountsUnchanged=True)
except BaseException as exc:
    report.update(errorType=type(exc).__name__,errorCode=str(exc) if isinstance(exc,ValueError) else 'node_local_io_failed')
finally:
    report['partialPath']=str(dest) if report['destinationPublished'] else (str(dest.parent/stage) if report['stageCreated'] else None)
    for fd in (binfd,root,parent):
        if fd is not None:os.close(fd)
print(json.dumps(report,sort_keys=True),flush=True)
raise SystemExit(0 if report['installed'] and report['phase']=='NODE_FILES_PROVISIONED_NOT_EXECUTED' else 2)
'''


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def read_file(path, maximum):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'node_host_symlink')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_CLOEXEC', 0))
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 <= before.st_size <= maximum, 'node_host_file_bound')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                           s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(raw) == before.st_size and stamp(before) == stamp(after), 'node_host_file_changed')
        return raw
    finally:
        os.close(fd)


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(read_file(path, len(raw)) == raw, 'node_host_readback')


def git(*args):
    return subprocess.run(['git', '--no-optional-locks', '-C', str(ROOT), *args],
        capture_output=True, check=True, timeout=30).stdout.decode('utf-8').strip()


def transport():
    return ('CONFIG=' + repr(CONFIG) + '\nimport hashlib,io,json,re,tarfile\n'
            + SELECTION_CODE + LINUX_BODY).encode('utf-8')


def select_archive(raw):
    namespace = {'CONFIG': CONFIG, 'hashlib': hashlib, 'io': io, 'tarfile': tarfile}
    exec(compile(SELECTION_CODE, '<reviewed-node-member-selector>', 'exec'), namespace)
    return namespace['select_members'](raw)


def checked_driver(expected):
    require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected), 'node_driver_pin')
    raw = read_file(Path(__file__).absolute(), 2 * 1024 * 1024)
    require(sha(raw) == expected, 'node_reviewed_driver_changed')
    return raw


def checked_download():
    receipt_raw = read_file(DOWNLOAD_RECEIPT, 1024 * 1024)
    require(sha(receipt_raw) == CONFIG['downloadReceiptSha256'], 'node_download_receipt_changed')
    receipt = json.loads(receipt_raw)
    require(receipt['kind'] == 'R167_NODE24_OFFICIAL_DOWNLOAD'
            and receipt['result'] == 'VERIFIED_OFFICIAL_NODE_ARCHIVE'
            and receipt['signatureVerified'] is True
            and type(receipt['signature']['exitCode']) is int and receipt['signature']['exitCode'] == 0
            and receipt['releaseSigner'] == CONFIG['releaseSigner']
            and '[GNUPG:] VALIDSIG ' + CONFIG['releaseSigner'] + ' ' in receipt['signature']['stdout']
            and receipt['version'] == CONFIG['version']
            and receipt['archiveExpectedSha256'] == CONFIG['archiveSha256']
            and receipt['archive']['sha256'] == CONFIG['archiveSha256']
            and receipt['archive']['bytes'] == CONFIG['archiveBytes']
            and receipt['archive']['file'] == CONFIG['archiveName']
            and receipt['archive']['url'] == receipt['archive']['finalUrl'] == CONFIG['archiveUrl']
            and canonical(receipt['selectedMembers']) == canonical(CONFIG['selectedMembers'])
            and receipt['binaryExecuted'] is False and receipt['labModified'] is False,
            'node_download_receipt_contract')
    archive = read_file(DOWNLOAD / CONFIG['archiveName'], MAX_ARCHIVE)
    select_archive(archive)
    return archive, receipt_raw


def prepare(directory, runner_sha):
    require(not directory.exists(), 'node_attempt_exists')
    runner = checked_driver(runner_sha)
    raw, receipt = checked_download()
    token = uuid.uuid4().hex
    linux = transport()
    intent = {'kind': 'R167_NODE24_PROVISION_INTENT', 'config': CONFIG,
        'workspaceHead': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
        'runnerSha256': runner_sha, 'transportSha256': sha(linux), 'attemptToken': token,
        'partialPath': '/opt/.alaz-r167a1-node-24.22.1.partial-' + token,
        'nodeExecutionAuthorized': False, 'automaticRetry': False, 'automaticCleanup': False}
    require(intent['branch'] == 'alaz/p2-service-install-r167a1', 'node_worktree_branch')
    directory.mkdir(exist_ok=False)
    write_new(directory / 'input.tar.xz', raw)
    write_new(directory / 'download-receipt.json', receipt)
    write_new(directory / 'linux-transport.py', linux)
    write_new(directory / 'reviewed-runner.py', runner)
    write_new(directory / 'intent.json', canonical(intent))
    return {'state': 'PREPARED_NOT_EXECUTED', 'attempt': str(directory),
            'intentSha256': sha(canonical(intent)), 'archiveSha256': sha(raw),
            'nodeSha256': CONFIG['selectedMembers']['bin/node']['sha256'],
            'destination': CONFIG['destination'], 'installed': False, 'nodeExecuted': False}


def terminal(returncode, stdout, stderr, result, host_pid, expected_intent_sha256):
    valid = (type(returncode) is int and type(result) is dict
             and result.get('kind') == 'R167_NODE24_PROVISION_OPERATION')
    accepted = (valid and type(expected_intent_sha256) is str
        and re.fullmatch('[0-9a-f]{64}', expected_intent_sha256)
        and returncode == 0 and not stderr
        and result.get('phase') == 'NODE_FILES_PROVISIONED_NOT_EXECUTED'
        and result.get('installed') is True and result.get('nodeExecuted') is False
        and result.get('runtimeVersionReadback') == 'NOT_RUN'
        and all(result.get(k) is False for k in ('serviceStarted', 'kernelAcceptance',
            'automaticRetry', 'automaticCleanup'))
        and type(result.get('realModelCalls')) is int and result['realModelCalls'] == 0
        and all(result.get(k) is True for k in ('stageCreated', 'destinationPublished',
            'receiptPublished', 'oldInstallationPreserved', 'mountsUnchanged')))
    if accepted:
        receipt = result.get('receipt')
        receipt_fields = {'schemaVersion', 'kind', 'distributionVersion', 'destination',
            'rootDevice', 'rootInode', 'archiveSha256', 'archiveBytes', 'archiveUrl',
            'releaseSigner', 'downloadReceiptSha256', 'operatorIntentSha256', 'node',
            'license', 'oldInstallationReceipt', 'mountInfoSha256', 'mountNamespace',
            'sourceFilesReadBack', 'installed', 'nodeExecuted', 'runtimeVersionReadback',
            'serviceStarted', 'kernelAcceptance', 'realModelCalls'}
        accepted = (type(receipt) is dict and set(receipt) == receipt_fields
            and type(receipt.get('schemaVersion')) is int and receipt['schemaVersion'] == 1
            and result.get('receiptSha256') == sha(canonical(receipt))
            and receipt.get('kind') == 'VERIFIED_NODE_RUNTIME_FILES'
            and receipt.get('destination') == CONFIG['destination']
            and receipt.get('operatorIntentSha256') == expected_intent_sha256
            and receipt.get('distributionVersion') == CONFIG['version']
            and receipt.get('archiveSha256') == CONFIG['archiveSha256']
            and receipt.get('archiveBytes') == CONFIG['archiveBytes']
            and receipt.get('archiveUrl') == CONFIG['archiveUrl']
            and receipt.get('releaseSigner') == CONFIG['releaseSigner']
            and receipt.get('downloadReceiptSha256') == CONFIG['downloadReceiptSha256']
            and all(type(receipt.get(k)) is int and receipt[k] > 0 for k in ('rootDevice', 'rootInode'))
            and type(receipt.get('oldInstallationReceipt')) is dict
            and set(receipt['oldInstallationReceipt']) == {'sha256', 'device', 'inode', 'bytes'}
            and receipt['oldInstallationReceipt'].get('sha256') == CONFIG['oldReceiptSha256']
            and all(type(receipt['oldInstallationReceipt'][k]) is int
                    and receipt['oldInstallationReceipt'][k] > 0 for k in ('device', 'inode', 'bytes'))
            and type(receipt.get('mountInfoSha256')) is str
            and re.fullmatch('[0-9a-f]{64}', receipt['mountInfoSha256'])
            and type(receipt.get('mountNamespace')) is str
            and re.fullmatch(r'mnt:\[[0-9]+\]', receipt['mountNamespace'])
            and receipt.get('installed') is True and receipt.get('sourceFilesReadBack') is True
            and all(receipt.get(k) is False for k in ('nodeExecuted', 'serviceStarted', 'kernelAcceptance'))
            and type(receipt.get('realModelCalls')) is int and receipt['realModelCalls'] == 0
            and receipt.get('runtimeVersionReadback') == 'NOT_RUN')
        for key, member in (('node', 'bin/node'), ('license', 'LICENSE')):
            actual = receipt.get(key) if type(receipt) is dict else None
            expected = CONFIG['selectedMembers'][member]
            accepted = bool(accepted and type(actual) is dict
                and set(actual) == {'sha256', 'bytes', 'mode', 'device', 'inode', 'uid', 'gid'}
                and all(type(actual.get(k)) is type(expected[k]) and actual[k] == expected[k]
                        for k in ('sha256', 'bytes', 'mode'))
                and all(type(actual.get(k)) is int and actual[k] == 0 for k in ('uid', 'gid'))
                and all(type(actual.get(k)) is int and actual[k] > 0 for k in ('device', 'inode')))
    return {'state': 'NODE_FILES_PROVISIONED_NOT_EXECUTED' if accepted else ('NOT_ACCEPTED' if valid else 'UNKNOWN'),
        'hostPid': host_pid, 'exitCode': returncode, 'intentSha256': expected_intent_sha256,
        'transportTerminalObserved': valid,
        'processMayBeRunning': not valid, 'rootPhase': result.get('phase') if valid else None,
        'stdoutSha256': sha(stdout), 'stderrSha256': sha(stderr), 'installed': bool(accepted),
        'nodeExecuted': False, 'runtimeVersionReadback': 'NOT_RUN',
        'automaticRetry': False, 'automaticCleanup': False}


def frozen_archive_stream(path):
    """Validate and retain the exact regular-file handle handed to WSL stdin."""
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'node_host_symlink')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_CLOEXEC', 0))
    stream = os.fdopen(fd, 'rb')
    try:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size == CONFIG['archiveBytes'], 'node_frozen_archive_metadata')
        raw = stream.read(MAX_ARCHIVE + 1)
        select_archive(raw)
        after = os.fstat(stream.fileno())
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink,
                           s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(stamp(before) == stamp(after), 'node_frozen_archive_changed')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def unknown_terminal(directory, process, intent_sha, reason, stdout=None, stderr=None):
    """Retain uncertain transport/mutation evidence; never terminate or replay it."""
    value = {'state': 'UNKNOWN', 'hostPid': process.pid if process is not None else None,
        'exitCode': process.returncode if process is not None else None,
        'intentSha256': intent_sha, 'reason': reason, 'processMayBeRunning': True,
        'installed': False, 'nodeExecuted': False, 'runtimeVersionReadback': 'NOT_RUN',
        'automaticRetry': False, 'automaticCleanup': False, 'outputComplete': False}
    for name, raw in (('stdout', stdout), ('stderr', stderr)):
        if raw is not None:
            require(type(raw) is bytes, 'node_partial_output_type')
            write_new(directory / ('partial-' + name + '.txt'), raw)
            value[name + 'Sha256'] = sha(raw)
    path = directory / 'terminal.json'
    if path.exists():
        # Preserve even an existing terminal whose durability/readback failed.
        path = directory / 'terminal-observation-failure.json'
    write_new(path, canonical(value))
    return value


def apply(directory, runner_sha, expected_intent_sha):
    runner = checked_driver(runner_sha)
    require(type(expected_intent_sha) is str and re.fullmatch('[0-9a-f]{64}', expected_intent_sha),
            'node_intent_external_pin')
    require({p.name for p in directory.iterdir()} == PREPARED_FILES, 'node_attempt_not_fresh')
    raw_intent = read_file(directory / 'intent.json', 2 * 1024 * 1024)
    require(sha(raw_intent) == expected_intent_sha, 'node_intent_changed')
    intent = json.loads(raw_intent)
    require(raw_intent == canonical(intent) and intent['kind'] == 'R167_NODE24_PROVISION_INTENT'
            and canonical(intent['config']) == canonical(CONFIG), 'node_intent_contract')
    require(intent['workspaceHead'] == git('rev-parse', 'HEAD')
            and intent['branch'] == git('branch', '--show-current') == 'alaz/p2-service-install-r167a1',
            'node_workspace_changed')
    require(intent['runnerSha256'] == runner_sha
            and read_file(directory / 'reviewed-runner.py', 2 * 1024 * 1024) == runner,
            'node_frozen_runner_changed')
    linux = read_file(directory / 'linux-transport.py', 2 * 1024 * 1024)
    require(linux == transport() and sha(linux) == intent['transportSha256'], 'node_transport_changed')
    download = read_file(directory / 'download-receipt.json', 1024 * 1024)
    require(sha(download) == CONFIG['downloadReceiptSha256'], 'node_frozen_download_changed')
    command = ['wsl.exe', '--distribution', CONFIG['lab'], '--user', 'root', '--cd', '/',
        '--exec', CONFIG['python'], '-I', '-B', '-c', linux.decode('utf-8'),
        json.dumps(intent, sort_keys=True, separators=(',', ':'))]
    # A redirected frozen file avoids a potentially blocking large Windows
    # stdin pipe write. Linux independently validates every received byte.
    with frozen_archive_stream(directory / 'input.tar.xz') as stream:
        write_new(directory / 'execution-start.json', canonical({
            'state': 'EXECUTION_STARTED_NO_REPLAY', 'intentSha256': expected_intent_sha,
            'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'destination': CONFIG['destination'], 'nodeExecutionAuthorized': False}))
        process = None
        out = err = None
        try:
            process = subprocess.Popen(command, stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate(timeout=180)
            write_new(directory / 'stdout.txt', out)
            write_new(directory / 'stderr.txt', err)
            require(len(out) <= 1024 * 1024 and len(err) <= 65536, 'node_transport_output_bound')
            try:
                result = json.loads(out)
            except (ValueError, UnicodeError):
                result = None
            value = terminal(process.returncode, out, err, result, process.pid, expected_intent_sha)
            if result is not None: write_new(directory / 'result.json', canonical(result))
            write_new(directory / 'terminal.json', canonical(value))
            return value
        except subprocess.TimeoutExpired as exc:
            return unknown_terminal(directory, process, expected_intent_sha,
                                    'node_transport_timeout', exc.output, exc.stderr)
        except BaseException as exc:
            return unknown_terminal(directory, process, expected_intent_sha,
                                    'node_host_observation_failed:' + type(exc).__name__, out, err)


def main():
    require(not sys.flags.optimize, 'node_optimized_driver_refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--expected-runner-sha256', required=True)
    parser.add_argument('--expected-intent-sha256')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    require(re.fullmatch('[a-z0-9-]{1,40}', args.attempt), 'node_attempt_name')
    directory = ROOT / 'scratch/r167-install' / args.attempt
    result = (prepare(directory, args.expected_runner_sha256) if args.prepare else
              apply(directory, args.expected_runner_sha256, args.expected_intent_sha256))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state'] in ('PREPARED_NOT_EXECUTED', 'NODE_FILES_PROVISIONED_NOT_EXECUTED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
