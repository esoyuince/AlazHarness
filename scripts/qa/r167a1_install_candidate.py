"""Freeze, apply once, and independently read back the R167 service source install.

This driver owns only new /opt/alaz-r167a1-input and /opt/alaz-r167a1 paths in
the dedicated P71C lab. The existing dependency tree, R156 installation, and
separately provisioned Node binary are read-only inputs. Unknown installation
effects require reconciliation; no mode retries apply or removes a partial tree.
Runtime identity/version and exact installed bytes are narrower than service,
provider, shared-library, kernel, or real-model acceptance.
"""
from __future__ import annotations

import argparse
import contextlib
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
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BRANCH = 'alaz/p2-service-install-r167a1'
LAB = 'AlazHarness-D3B-P71C'
HARNESS = '1600eba430562795b9114209d1168bfa0d6ea5fd'
NATIVE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
MANIFEST_SHA = 'a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8'
ARCHIVE_SHA = '43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a'
PYTHON = '/usr/bin/python3.12'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
NODE = '/opt/alaz-r167a1-node-24.22.1/bin/node'
NODE_SHA = 'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb'
INPUT = '/opt/alaz-r167a1-input'
DESTINATION = '/opt/alaz-r167a1'
DEPENDENCIES = '/opt/alaz-f126c1a6/dependencies'
OLD_RECEIPT = '/opt/alaz-r156a1/.alaz-installation.json'
OLD_RECEIPT_SHA = 'a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
MAX_BUNDLE = 24 * 1024 * 1024
TOOL_PINS = {
    'scripts/install_service_candidate.py': 'bc014b7e4f9ac2a0c6d170e80501eee5e458d526a2b21c4f076bfa4f590de30a',
    'scripts/verify_service_candidate.py': 'ddd8fb60dc030c36c0aefcf2790c788d012dc13e39e37f1a14f5bcd0725e3288',
    'scripts/build_service_candidate.py': '54c83be327e3e9e08e0a149b096f5a4f873364461069711a4c2d3f20e862f6cf',
    'scripts/install_projected_candidate.py': 'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6',
    'scripts/build_projected_candidate.py': '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b',
    'scripts/ci_check.py': 'b55871b560f4f30d30fb22869ac63a3b47aaa5928d4aae9dee499c88c9fa94c8',
    'qa/r167a1_import_probe.py': '9261a63ab741cefe0df32296cdced122e29e420278075bb8a5f295de2b826bab',
    'qa/r167a1_cli_probe.py': '50ac1f0ed4e1944665588a505e4e916a280d5dc07e1a0682d4fbe9e07df7bdd8',
}
MEMBERS = ('candidate/manifest.json', 'candidate/service-source.tar', *TOOL_PINS)


LINUX_TRANSPORT = r'''
import hashlib,io,json,os,pathlib,re,stat,subprocess,sys,zipfile
if sys.flags.optimize:raise RuntimeError('optimized_transport_refused')
LAB='AlazHarness-D3B-P71C'
PYTHON='/usr/bin/python3.12'
NODE='/opt/alaz-r167a1-node-24.22.1/bin/node'
INPUT=pathlib.Path('/opt/alaz-r167a1-input')
DEST=pathlib.Path('/opt/alaz-r167a1')
DEPS='/opt/alaz-f126c1a6/dependencies'
OLD=pathlib.Path('/opt/alaz-r156a1/.alaz-installation.json')
OLD_SHA='a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'
MAX=24*1024*1024
PINS={
 'harnessCommit':'1600eba430562795b9114209d1168bfa0d6ea5fd',
 'nativeFeature':'5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d',
 'manifestSha256':'a3fde8b0ac808c375c4ecd0eab9f26938828b0d01cd4632ffa4234e47de38af8',
 'archiveSha256':'43fc186b8f21e4f39e34364ae100c82e520317d6b06c8a100b29f3b26adcd56a',
 'pythonSha256':'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f',
 'nodeSha256':'e32e2d16081cf644f88392934288086e7662529d0d43277c34f7aad2207cfafb'}
TOOLS={
 'scripts/install_service_candidate.py':'bc014b7e4f9ac2a0c6d170e80501eee5e458d526a2b21c4f076bfa4f590de30a',
 'scripts/verify_service_candidate.py':'ddd8fb60dc030c36c0aefcf2790c788d012dc13e39e37f1a14f5bcd0725e3288',
 'scripts/build_service_candidate.py':'54c83be327e3e9e08e0a149b096f5a4f873364461069711a4c2d3f20e862f6cf',
 'scripts/install_projected_candidate.py':'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6',
 'scripts/build_projected_candidate.py':'7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b',
 'scripts/ci_check.py':'b55871b560f4f30d30fb22869ac63a3b47aaa5928d4aae9dee499c88c9fa94c8',
 'qa/r167a1_import_probe.py':'9261a63ab741cefe0df32296cdced122e29e420278075bb8a5f295de2b826bab',
 'qa/r167a1_cli_probe.py':'50ac1f0ed4e1944665588a505e4e916a280d5dc07e1a0682d4fbe9e07df7bdd8'}
FILES=('candidate/manifest.json','candidate/service-source.tar',*TOOLS)
report={'kind':'R167A1_SERVICE_INSTALL_OPERATION','phase':'PREFLIGHT','installed':False,
 'verifiedInstalledBytesNow':False,'executionAuthorized':False,'serviceReadinessAccepted':False,
 'providerDependencyCompletenessAccepted':False,'sharedLibraryClosureAccepted':False,
 'kernelAcceptance':False,'realModelCalls':0,'servicesChanged':False,'mountsChanged':False,
 'dependencyDownloads':0,'automaticRetry':False,'automaticCleanup':False}
created=False
mode=None
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
def unique(pairs):
    result={}
    for key,value in pairs:
        assert key not in result,'duplicate_json_key'
        result[key]=value
    return result
def parse(raw):return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('json_constant')))
def stamp(s):return (s.st_dev,s.st_ino,s.st_size,s.st_uid,s.st_gid,s.st_mode,s.st_nlink,s.st_mtime_ns,s.st_ctime_ns)
def trusted(path,directory):
    assert path.is_absolute() and path.resolve(strict=True)==path,'noncanonical_input_ancestry'
    for p in (path,*path.parents):
        s=p.lstat()
        assert s.st_uid==s.st_gid==0 and not s.st_mode&0o022 and not stat.S_ISLNK(s.st_mode),'untrusted_input_ancestry'
    assert path.is_dir() if directory else path.is_file()
def read_file(path,limit,hash_only=False):
    trusted(path,False)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<before.st_size<=limit,'input_file_bound'
        digest=hashlib.sha256();parts=[];total=0
        while True:
            chunk=os.read(fd,min(1024*1024,limit-total+1))
            if not chunk:break
            total+=len(chunk)
            assert total<=limit,'input_file_growth'
            digest.update(chunk)
            if not hash_only:parts.append(chunk)
        assert total==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(path.lstat()),'input_file_changed'
        trusted(path,False)
        return digest.hexdigest() if hash_only else b''.join(parts)
    finally:os.close(fd)
def put(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fchmod(stream.fileno(),0o644);os.fsync(stream.fileno())
    assert read_file(path,MAX)==data,'staged_input_readback'
def new_directory(path):
    global created
    path.mkdir(mode=0o700)
    if path==INPUT:created=True
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:os.fchmod(fd,0o755);os.fsync(fd)
    finally:os.close(fd)
def check_inputs(intent,include_result):
    trusted(INPUT,True)
    names={'candidate','scripts','qa','operator-intent.json',*FILES}
    if include_result:names.add('operator-result.json')
    assert {p.relative_to(INPUT).as_posix() for p in INPUT.rglob('*')}==names,'staged_inventory_changed'
    assert read_file(INPUT/'operator-intent.json',1024*1024)==canonical(intent),'staged_intent_changed'
    for name in FILES:
        value=read_file(INPUT/name,MAX)
        assert len(value)==intent['members'][name]['bytes'] and sha(value)==intent['members'][name]['sha256'],'staged_member_changed'
def check_result(result,intent,verification):
    assert type(result) is dict and result.get('result')=='PASS' and result.get('kind')=='VERIFIED_SERVICE_INSTALLATION','installer_receipt_missing'
    assert result.get('installed') is True and result.get('destination')==str(DEST),'installer_destination'
    for key in ('harnessCommit','nativeFeature','archiveSha256'):
        assert result.get(key)==intent[key],'installer_source_pin'
    assert result.get('sourceManifestSha256')==intent['manifestSha256'],'installer_manifest_pin'
    assert type(result.get('sourceFileCount')) is int and result['sourceFileCount']==878,'installer_source_count'
    assert type(result.get('dependencyFileCount')) is int and result['dependencyFileCount']==1162,'installer_dependency_count'
    assert result.get('dependencyInventorySha256')=='1e1c4d0a5a9f0d4d25c66aaabe0765c75cdca0dd84121f79883b9e3bf2b4ee18','installer_dependency_inventory'
    for key in ('executionAuthorized','dependenciesAcceptedForService','serviceReadinessAccepted','nativeRuntimeAccepted','kernelAcceptance','realModelAcceptance'):
        assert result.get(key) is False,'installer_scope_claim'
    assert type(result.get('realModelCalls')) is int and result['realModelCalls']==0,'installer_model_claim'
    for key in ('sourceAndDependenciesReadBack','runtimeExecutableBytesVerified','runtimeVersionReadback','rootControlledAncestryVerified'):
        assert result.get(key) is True,'installer_readback_claim'
    assert type(result.get('receiptSha256')) is str and re.fullmatch('[0-9a-f]{64}',result['receiptSha256']),'installer_receipt_hash'
    runtimes=result.get('runtimes')
    assert type(runtimes) is dict and set(runtimes)=={'python','node'},'installer_runtime_fields'
    for kind,path,size,version,text in (('python',PYTHON,8020928,[3,12,3],'Python 3.12.3'),('node',NODE,126879696,[24,22,1],'v24.22.1')):
        row=runtimes[kind]
        assert type(row) is dict and set(row)=={'path','sha256','bytes','device','inode','uid','gid','mode','version','versionTuple','observedVersion','versionStdoutSha256'},'installer_runtime_record'
        expected={'path':path,'sha256':intent[kind+'Sha256'],'bytes':size,'uid':0,'gid':0,'mode':0o755,'version':'.'.join(map(str,version)),'versionTuple':version,'observedVersion':text,'versionStdoutSha256':sha((text+'\n').encode())}
        assert canonical({k:row[k] for k in expected})==canonical(expected),'installer_runtime_pin'
        assert all(type(row[k]) is int and row[k]>=0 for k in ('device','inode')),'installer_runtime_stat'
    if verification:assert result.get('verifiedInstalledBytesNow') is True,'installer_verification_claim'
    else:assert 'verifiedInstalledBytesNow' not in result,'unexpected_verification_claim'
    receipt={k:v for k,v in result.items() if k not in ('result','receiptSha256','verifiedInstalledBytesNow')}
    raw=read_file(DEST/'.alaz-service-installation.json',2*1024*1024)
    assert raw==canonical(receipt) and sha(raw)==result['receiptSha256'],'installed_receipt_readback'
    root=DEST.lstat()
    assert type(receipt.get('rootDevice')) is int and type(receipt.get('rootInode')) is int and (root.st_dev,root.st_ino)==(receipt['rootDevice'],receipt['rootInode']),'installed_root_identity'
try:
    assert len(sys.argv)==2,'transport_argument_count'
    request=parse(sys.argv[1]);mode=request['mode'];intent=request['intent']
    assert mode in ('apply','verify'),'transport_mode'
    report['mode']=mode
    if mode=='verify':report['kind']='R167A1_SERVICE_VERIFY_OPERATION'
    assert intent['kind']=='R167A1_SERVICE_INSTALL_INTENT' and intent['lab']==LAB,'intent_kind'
    assert intent['inputDirectory']==str(INPUT) and intent['destination']==str(DEST) and intent['dependencyRoot']==DEPS,'intent_paths'
    assert intent['pythonPath']==PYTHON and intent['nodePath']==NODE and intent['priorReceiptPath']==str(OLD) and intent['priorReceiptSha256']==OLD_SHA,'intent_runtime_paths'
    assert all(intent[k]==v for k,v in PINS.items()) and intent['toolSha256']==TOOLS,'intent_pins'
    assert set(intent['members'])==set(FILES),'intent_members'
    assert os.environ.get('WSL_DISTRO_NAME')==LAB and pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()==LAB,'wrong_lab'
    assert not pathlib.Path('/mnt/c/Windows').exists(),'windows_mount_present'
    assert sys.platform=='linux' and os.uname().machine=='x86_64','linux_x64_required'
    assert sys.executable==PYTHON and sys.version_info[:2]==(3,12) and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize,'python_actor'
    actor=(0,0) if mode=='apply' else (23001,23003)
    assert os.getresuid()==(actor[0],)*3 and os.getresgid()==(actor[1],)*3,'wrong_actor'
    for name in ('uid_map','gid_map'):
        assert pathlib.Path('/proc/self',name).read_text().split()==['0','0','4294967295'],'initial_userns_required'
    if mode=='apply':
        assert os.readlink('/proc/self/ns/user')==os.readlink('/proc/1/ns/user'),'initial_userns_identity'
    assert read_file(pathlib.Path(PYTHON),256*1024*1024,True)==intent['pythonSha256'],'python_changed'
    assert read_file(pathlib.Path(NODE),256*1024*1024,True)==intent['nodeSha256'],'node_changed'
    assert read_file(OLD,2*1024*1024,True)==OLD_SHA,'prior_receipt_changed'
    report['priorReceiptSha256Before']=OLD_SHA
    trusted(pathlib.Path(DEPS),True)
    trusted(INPUT.parent,True)
    if mode=='apply':
        assert not os.path.lexists(INPUT) and not os.path.lexists(DEST),'fresh_paths_required'
        raw=sys.stdin.buffer.read(MAX+1)
        assert type(intent['bundleBytes']) is int and len(raw)==intent['bundleBytes']<=MAX and sha(raw)==intent['bundleSha256'],'bundle_identity'
        data={}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist()
            assert len(infos)==len(FILES) and {i.filename for i in infos}==set(FILES),'bundle_members'
            for info in infos:
                expected=intent['members'][info.filename]
                assert info.compress_type==zipfile.ZIP_STORED and not info.is_dir(),'bundle_encoding'
                assert type(expected['bytes']) is int and 0<info.file_size==info.compress_size==expected['bytes']<=MAX,'member_bound'
                value=archive.read(info)
                assert len(value)==expected['bytes'] and sha(value)==expected['sha256'],'member_identity'
                data[info.filename]=value
        assert sha(data['candidate/manifest.json'])==intent['manifestSha256'] and sha(data['candidate/service-source.tar'])==intent['archiveSha256'],'candidate_identity'
        assert all(sha(data[name])==digest for name,digest in TOOLS.items()),'tool_identity'
        report['phase']='STAGING_REVIEWED_INPUTS'
        new_directory(INPUT)
        for name in ('candidate','scripts','qa'):new_directory(INPUT/name)
        put(INPUT/'operator-intent.json',canonical(intent))
        for name in FILES:put(INPUT/name,data[name])
        check_inputs(intent,False)
    else:
        assert sys.stdin.buffer.read(1)==b'','verify_stdin_not_empty'
        prior=request['priorOperation']
        assert prior['kind']=='R167A1_SERVICE_INSTALL_OPERATION' and prior['phase']=='INSTALLED_SOURCE_ONLY' and prior['installed'] is True,'verified_apply_required'
        assert sha(canonical(prior))==request['priorOperationSha256'],'prior_operation_pin'
        check_inputs(intent,True)
        assert read_file(INPUT/'operator-result.json',2*1024*1024)==canonical(prior),'prior_operator_result_changed'
        check_result(prior['installerResult'],intent,False)
        report['installationOperationSha256']=request['priorOperationSha256']
    command=[PYTHON,'-I','-B',str(INPUT/'scripts/install_service_candidate.py'),
        '--candidate-directory',str(INPUT/'candidate'),'--destination',str(DEST),
        '--dependencies',DEPS,'--expected-manifest-sha256',intent['manifestSha256'],
        '--expected-archive-sha256',intent['archiveSha256'],'--expected-harness-commit',intent['harnessCommit'],
        '--expected-native-feature',intent['nativeFeature'],'--expected-python-sha256',intent['pythonSha256'],
        '--node-path',NODE,'--expected-node-sha256',intent['nodeSha256']]
    if mode=='verify':command.append('--verify-installed')
    report['phase']='INSTALLER_INVOKED' if mode=='apply' else 'VERIFIER_INVOKED'
    report['installerSpawnAttempted']=True
    process=subprocess.Popen(command,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','HOME':'/'},
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    report['installerPid']=process.pid
    try:out,err=process.communicate(timeout=180)
    except subprocess.TimeoutExpired as exc:
        report.update(phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True,
            partialStdoutSha256=sha(exc.output or b''),partialStderrSha256=sha(exc.stderr or b''))
        raise RuntimeError('installer_timeout_unknown')
    report['installerTerminalObserved']=True
    report['installerExitCode']=process.returncode
    assert len(out)<=1024*1024 and len(err)<=65536,'installer_output_bound'
    report.update(installerStdout=out.decode('utf-8'),installerStderr=err.decode('utf-8'),
        installerStdoutSha256=sha(out),installerStderrSha256=sha(err))
    assert process.returncode==0 and not err,'installer_refused_or_failed'
    result=parse(out)
    check_result(result,intent,mode=='verify')
    if mode=='verify':
        comparable={k:v for k,v in result.items() if k!='verifiedInstalledBytesNow'}
        assert canonical(comparable)==canonical(prior['installerResult']),'installed_receipt_changed_since_apply'
    check_inputs(intent,mode=='verify')
    assert read_file(OLD,2*1024*1024,True)==OLD_SHA,'prior_receipt_changed_after_operation'
    report.update(phase='INSTALLED_SOURCE_ONLY' if mode=='apply' else 'VERIFIED_INSTALLED_SOURCE_ONLY',
        installed=True,verifiedInstalledBytesNow=mode=='verify',installerResult=result,
        inputDirectory=str(INPUT),destination=str(DEST),bundleSha256=intent['bundleSha256'],
        intentSha256=sha(canonical(intent)),priorReceiptSha256After=OLD_SHA)
except BaseException as exc:
    report.update(errorType=type(exc).__name__,errorCode=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else 'local_io_or_parse_failed')
    if report.get('installerSpawnAttempted') and not report.get('installerTerminalObserved'):
        report.update(failurePhase=report['phase'],phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)
report['inputDirectoryCreated']=created
report['destinationExists']=os.path.lexists(DEST)
if created:
    try:put(INPUT/'operator-result.json',canonical(report))
    except BaseException as exc:report['operatorResultWriteError']=type(exc).__name__;report['installed']=False
print(json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
raise SystemExit(0 if report['installed'] and report['phase'] in ('INSTALLED_SOURCE_ONLY','VERIFIED_INSTALLED_SOURCE_ONLY') else 2)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'duplicate_json_key'
        result[key] = value
    return result


def parse(raw):
    def invalid(value):
        raise ValueError('json_constant')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    assert path.read_bytes() == data, 'host_readback_changed'


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True,
                          check=True, timeout=30).stdout.decode().strip()


def candidate():
    return (ROOT.parent / 'p2-service-candidate-r166a1' / 'scratch/service-candidates'
            / 'r166a1-primary-01')


def current_sources(installer_sha, runner_sha, node_sha):
    runner = Path(__file__).read_bytes()
    assert sha(runner) == runner_sha, 'reviewed_driver_changed'
    assert installer_sha == TOOL_PINS['scripts/install_service_candidate.py'], 'reviewed_installer_pin'
    assert node_sha == NODE_SHA, 'reviewed_node_pin'
    scripts = {name: (ROOT / ('scripts/' + name if name.startswith('qa/') else name)).read_bytes()
               for name in TOOL_PINS}
    assert all(sha(scripts[name]) == digest for name, digest in TOOL_PINS.items()), 'reviewed_tools_changed'
    return runner, scripts


def bundle_members(raw):
    assert 0 < len(raw) <= MAX_BUNDLE, 'bundle_bound'
    data = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        assert len(infos) == len(MEMBERS) and {i.filename for i in infos} == set(MEMBERS), 'bundle_inventory'
        for info in infos:
            assert info.compress_type == zipfile.ZIP_STORED and not info.is_dir(), 'bundle_encoding'
            assert 0 < info.file_size == info.compress_size <= MAX_BUNDLE, 'member_bound'
            data[info.filename] = archive.read(info)
    assert sha(data['candidate/manifest.json']) == MANIFEST_SHA, 'candidate_manifest_changed'
    assert sha(data['candidate/service-source.tar']) == ARCHIVE_SHA, 'candidate_archive_changed'
    manifest = parse(data['candidate/manifest.json'])
    assert manifest['harnessCommit'] == HARNESS and manifest['nativeFeature'] == NATIVE, 'candidate_source_changed'
    assert all(sha(data[name]) == digest for name, digest in TOOL_PINS.items()), 'candidate_tool_changed'
    return data


def make_intent(raw, payload, runner_sha, head):
    return {'kind': 'R167A1_SERVICE_INSTALL_INTENT', 'lab': LAB,
            'inputDirectory': INPUT, 'destination': DESTINATION, 'dependencyRoot': DEPENDENCIES,
            'harnessCommit': HARNESS, 'nativeFeature': NATIVE, 'workspaceHead': head,
            'workspaceBranch': BRANCH, 'workspaceRoot': str(ROOT),
            'manifestSha256': MANIFEST_SHA, 'archiveSha256': ARCHIVE_SHA,
            'toolSha256': TOOL_PINS, 'installerSha256': TOOL_PINS['scripts/install_service_candidate.py'],
            'runnerSha256': runner_sha, 'transportSha256': sha(LINUX_TRANSPORT.encode()),
            'pythonPath': PYTHON, 'pythonSha256': PYTHON_SHA, 'nodePath': NODE, 'nodeSha256': NODE_SHA,
            'priorReceiptPath': OLD_RECEIPT, 'priorReceiptSha256': OLD_RECEIPT_SHA,
            'bundleSha256': sha(raw), 'bundleBytes': len(raw),
            'members': {name: {'sha256': sha(payload[name]), 'bytes': len(payload[name])} for name in MEMBERS},
            'installationOnly': True, 'runtimeIdentityAndVersionProbesAuthorized': True,
            'serviceStartupAuthorized': False, 'kernelAcceptance': False,
            'providerDependencyCompletenessAccepted': False, 'sharedLibraryClosureAccepted': False,
            'realModelCalls': 0, 'automaticRetry': False, 'automaticCleanup': False}


def prepare(directory, installer_sha, runner_sha, node_sha):
    assert not directory.exists(), 'attempt_already_exists'
    runner, scripts = current_sources(installer_sha, runner_sha, node_sha)
    payload = {'candidate/manifest.json': (candidate() / 'manifest.json').read_bytes(),
               'candidate/service-source.tar': (candidate() / 'service-source.tar').read_bytes(), **scripts}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as bundle:
        for name in MEMBERS:
            info = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, payload[name])
    raw = stream.getvalue()
    bundle_members(raw)
    assert git('branch', '--show-current') == BRANCH, 'wrong_worktree_branch'
    intent = make_intent(raw, payload, runner_sha, git('rev-parse', 'HEAD'))
    directory.mkdir(parents=True, exist_ok=False)
    write_new(directory / 'input.zip', raw)
    write_new(directory / 'intent.json', canonical(intent))
    write_new(directory / 'linux-transport.py', LINUX_TRANSPORT.encode())
    write_new(directory / 'reviewed-runner.py', runner)
    return {'state': 'PREPARED_NOT_EXECUTED', 'attempt': str(directory),
            'bundleSha256': intent['bundleSha256'], 'bundleBytes': len(raw),
            'intentSha256': sha(canonical(intent)), 'installed': False}


def prepared(directory, installer_sha, runner_sha, node_sha, intent_sha):
    runner, scripts = current_sources(installer_sha, runner_sha, node_sha)
    raw = (directory / 'input.zip').read_bytes()
    payload = bundle_members(raw)
    assert all(payload[name] == scripts[name] for name in TOOL_PINS), 'frozen_tools_changed'
    intent_raw = (directory / 'intent.json').read_bytes()
    assert type(intent_sha) is str and re.fullmatch('[0-9a-f]{64}', intent_sha), 'exact_intent_pin_required'
    assert sha(intent_raw) == intent_sha, 'reviewed_intent_changed'
    intent = parse(intent_raw)
    assert git('branch', '--show-current') == BRANCH, 'wrong_worktree_branch'
    assert intent_raw == canonical(make_intent(raw, payload, runner_sha, git('rev-parse', 'HEAD'))), 'frozen_intent_changed'
    assert (directory / 'reviewed-runner.py').read_bytes() == runner, 'frozen_driver_changed'
    assert (directory / 'linux-transport.py').read_bytes() == LINUX_TRANSPORT.encode(), 'frozen_transport_changed'
    return intent, raw


def operation_terminal(returncode, out, err, result, host_pid, mode):
    """No missing/malformed receipt or unobserved child becomes an accepted install."""
    expected_kind = 'R167A1_SERVICE_INSTALL_OPERATION' if mode == 'apply' else 'R167A1_SERVICE_VERIFY_OPERATION'
    success = 'INSTALLED_SOURCE_ONLY' if mode == 'apply' else 'VERIFIED_INSTALLED_SOURCE_ONLY'
    valid = type(result) is dict and result.get('kind') == expected_kind and result.get('mode') == mode
    terminal = valid and result.get('installerTerminalObserved') is True
    unknown = (not valid or result.get('processMayBeRunning') is True
               or (result.get('installerSpawnAttempted') is True and not terminal)
               or result.get('phase') == 'INSTALLER_OUTCOME_UNKNOWN'
               or (result.get('phase') in ('INSTALLER_INVOKED', 'VERIFIER_INVOKED') and not terminal))
    accepted = (not unknown and returncode == 0 and not err and terminal
                and result.get('phase') == success and result.get('installed') is True
                and result.get('installerExitCode') == 0)
    if mode == 'verify':
        accepted = accepted and result.get('verifiedInstalledBytesNow') is True
    return {'state': 'UNKNOWN' if unknown else (success if accepted else 'NOT_ACCEPTED'),
            'mode': mode, 'exitCode': returncode, 'hostPid': host_pid,
            'installerPid': result.get('installerPid') if valid else None,
            'installerTerminalObserved': bool(terminal), 'processMayBeRunning': bool(unknown),
            'rootPhase': result.get('phase') if valid else None,
            'stdoutSha256': sha(out), 'stderrSha256': sha(err),
            'installed': bool(accepted), 'verifiedInstalledBytesNow': bool(accepted and mode == 'verify'),
            'serviceReadinessAccepted': False, 'kernelAcceptance': False, 'realModelCalls': 0,
            'automaticRetry': False, 'automaticCleanup': False}


def frozen_bundle_stream(path, expected):
    """Retain one verified regular-file handle, avoiding blocking Windows pipe writes."""
    assert not any(p.is_symlink() for p in (path, *path.parents)), 'bundle_host_symlink'
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    stream = os.fdopen(fd, 'rb')
    try:
        before = os.fstat(stream.fileno())
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == len(expected), 'held_bundle_metadata'
        held = stream.read(MAX_BUNDLE + 1)
        after = os.fstat(stream.fileno())
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        assert held == expected and all(getattr(before, key) == getattr(after, key) for key in fields), 'held_bundle_changed'
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def unknown_terminal(directory, prefix, process, intent, mode, reason, out=None, err=None):
    value = {'state': 'UNKNOWN', 'mode': mode, 'hostPid': process.pid if process else None,
             'exitCode': process.returncode if process else None, 'intentSha256': sha(canonical(intent)),
             'processMayBeRunning': True, 'installed': False, 'verifiedInstalledBytesNow': False,
             'reason': reason, 'serviceReadinessAccepted': False, 'kernelAcceptance': False,
             'realModelCalls': 0, 'automaticRetry': False, 'automaticCleanup': False, 'outputComplete': False}
    for name, data in (('stdout', out), ('stderr', err)):
        if data is not None:
            assert type(data) is bytes, 'partial_output_type'
            write_new(directory / (prefix + 'partial-' + name + '.txt'), data)
            value[name + 'Sha256'] = sha(data)
    target = directory / (prefix + 'terminal.json')
    if target.exists():
        target = directory / (prefix + 'terminal-observation-failure.json')
    write_new(target, canonical(value))
    return value


def invoke(directory, intent, raw, mode, prior=None):
    prefix = '' if mode == 'apply' else 'verification-'
    request = {'mode': mode, 'intent': intent}
    if prior is not None:
        request.update(priorOperation=prior, priorOperationSha256=sha(canonical(prior)))
    start = {'state': 'EXECUTION_STARTED_NO_REPLAY' if mode == 'apply' else 'VERIFICATION_STARTED',
             'intentSha256': sha(canonical(intent)), 'requestSha256': sha(canonical(request)),
             'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'destination': DESTINATION, 'rootRequested': mode == 'apply', 'mode': mode}
    actor = 'root' if mode == 'apply' else 'alazgateway'
    command = ['wsl.exe', '--distribution', LAB, '--user', actor, '--cd', '/', '--exec',
               PYTHON, '-I', '-B', '-c', LINUX_TRANSPORT,
               json.dumps(request, sort_keys=True, separators=(',', ':'), allow_nan=False)]
    context = frozen_bundle_stream(directory / 'input.zip', raw) if mode == 'apply' else contextlib.nullcontext()
    with context as bundle:
        write_new(directory / (prefix + 'execution-start.json'), canonical(start))
        process = None
        out = err = None
        try:
            process = subprocess.Popen(command, stdin=bundle if mode == 'apply' else subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate(timeout=240)
            write_new(directory / (prefix + 'stdout.txt'), out)
            write_new(directory / (prefix + 'stderr.txt'), err)
            assert len(out) <= 2 * 1024 * 1024 and len(err) <= 65536, 'transport_output_bound'
            try:
                result = parse(out)
            except (ValueError, UnicodeError, AssertionError):
                result = None
            terminal = operation_terminal(process.returncode, out, err, result, process.pid, mode)
            if result is not None:
                write_new(directory / (prefix + 'result.json'), canonical(result))
            write_new(directory / (prefix + 'terminal.json'), canonical(terminal))
            return terminal
        except subprocess.TimeoutExpired as exc:
            return unknown_terminal(directory, prefix, process, intent, mode, 'transport_timeout', exc.output, exc.stderr)
        except BaseException as exc:
            return unknown_terminal(directory, prefix, process, intent, mode,
                                    'host_observation_failed:' + type(exc).__name__, out, err)


def apply(directory, installer_sha, runner_sha, node_sha, intent_sha):
    assert {p.name for p in directory.iterdir()} == {'input.zip', 'intent.json', 'linux-transport.py', 'reviewed-runner.py'}, 'attempt_not_fresh'
    intent, raw = prepared(directory, installer_sha, runner_sha, node_sha, intent_sha)
    return invoke(directory, intent, raw, 'apply')


def verify_installed(directory, installer_sha, runner_sha, node_sha, intent_sha):
    intent, raw = prepared(directory, installer_sha, runner_sha, node_sha, intent_sha)
    terminal_raw = (directory / 'terminal.json').read_bytes()
    terminal = parse(terminal_raw)
    result_raw = (directory / 'result.json').read_bytes()
    result = parse(result_raw)
    out, err = (directory / 'stdout.txt').read_bytes(), (directory / 'stderr.txt').read_bytes()
    assert terminal_raw == canonical(terminal) and result_raw == canonical(result), 'prior_noncanonical_receipt'
    assert canonical(parse(out)) == result_raw, 'prior_output_changed'
    expected = operation_terminal(terminal['exitCode'], out, err, result, terminal['hostPid'], 'apply')
    assert canonical(terminal) == canonical(expected) and terminal['state'] == 'INSTALLED_SOURCE_ONLY', 'accepted_installation_required'
    assert result['intentSha256'] == sha(canonical(intent)) and result['bundleSha256'] == intent['bundleSha256'], 'prior_installation_intent_changed'
    return invoke(directory, intent, raw, 'verify', result)


def main():
    if sys.flags.optimize:
        raise RuntimeError('optimized_driver_refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--expected-installer-sha256', required=True)
    parser.add_argument('--expected-runner-sha256', required=True)
    parser.add_argument('--expected-node-sha256', default=NODE_SHA)
    parser.add_argument('--expected-intent-sha256')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    action.add_argument('--verify-installed', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]{1,40}', args.attempt), 'invalid_attempt'
    for digest in (args.expected_installer_sha256, args.expected_runner_sha256, args.expected_node_sha256):
        assert re.fullmatch('[0-9a-f]{64}', digest), 'exact_review_digest_required'
    directory = ROOT / 'scratch/install-candidates' / args.attempt
    pins = (args.expected_installer_sha256, args.expected_runner_sha256, args.expected_node_sha256)
    result = (prepare(directory, *pins) if args.prepare else
              (apply if args.apply else verify_installed)(directory, *pins, args.expected_intent_sha256))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state'] in ('PREPARED_NOT_EXECUTED', 'INSTALLED_SOURCE_ONLY',
                                   'VERIFIED_INSTALLED_SOURCE_ONLY') else 2


if __name__ == '__main__':
    raise SystemExit(main())
