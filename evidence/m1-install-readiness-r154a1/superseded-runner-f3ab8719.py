"""One reviewed, source-only installation in the dedicated P71C laboratory.

Preparation freezes the exact R153 candidate and reviewed provisioning sources.
Apply is explicit and one-shot. No mount, cgroup, native startup, service, model,
dependency download, old-root cleanup or automatic retry is part of this driver.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
LAB = 'AlazHarness-D3B-P71C'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
SOURCE = 'e03f7fd4e47fea6a58b749564ab350aeb4237a26'
ARCHIVE_SHA = 'e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b'
MANIFEST_SHA = '182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9'
BUILDER_SHA = '97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
INPUT = '/opt/alaz-r154a1-input'
DESTINATION = '/opt/alaz-r154a1'
DEPENDENCIES = '/opt/alaz-f126c1a6/dependencies'
MAX_BUNDLE = 24 * 1024 * 1024
MEMBERS = ('candidate/manifest.json', 'candidate/projected-source.tar',
           'scripts/build_projected_candidate.py', 'scripts/install_projected_candidate.py')


LINUX_TRANSPORT = r'''
import hashlib,io,json,os,pathlib,stat,subprocess,sys,zipfile
LAB='AlazHarness-D3B-P71C'
PYTHON='/usr/bin/python3.12'
INPUT=pathlib.Path('/opt/alaz-r154a1-input')
DEST=pathlib.Path('/opt/alaz-r154a1')
DEPS='/opt/alaz-f126c1a6/dependencies'
MAX=24*1024*1024
FILES=('candidate/manifest.json','candidate/projected-source.tar',
       'scripts/build_projected_candidate.py','scripts/install_projected_candidate.py')
report={'kind':'R154A1_SOURCE_INSTALL_OPERATION','phase':'PREFLIGHT','installed':False,
        'executionAuthorized':False,'projectedReadinessAccepted':False,
        'finiteWorkExecuted':False,'realModelCalls':0,'mountsChanged':False,
        'servicesChanged':False,'dependencyDownloads':0,'automaticCleanup':False}
created=False
def sha(data):return hashlib.sha256(data).hexdigest()
def trusted(path,directory):
    assert path.is_absolute() and path.resolve(strict=True)==path,'noncanonical_input_ancestry'
    for p in (path,*path.parents):
        s=p.lstat()
        assert s.st_uid==s.st_gid==0 and not s.st_mode&0o022 and not stat.S_ISLNK(s.st_mode),'untrusted_input_ancestry'
    assert path.is_dir() if directory else path.is_file()
def put(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)
    with os.fdopen(fd,'wb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    assert path.read_bytes()==data,'provisioning_readback_mismatch'
try:
    assert len(sys.argv)==2,'transport_argument_count'
    intent=json.loads(sys.argv[1])
    assert intent['kind']=='R154A1_SOURCE_INSTALL_INTENT'
    assert intent['lab']==LAB and intent['inputDirectory']==str(INPUT) and intent['destination']==str(DEST)
    assert intent['dependencyRoot']==DEPS and intent['nativeFeature']=='d1516731308de8e87130dc68124e69aad35d6911'
    assert intent['harnessCommit']=='e03f7fd4e47fea6a58b749564ab350aeb4237a26'
    assert intent['manifestSha256']=='182b9d0198e4c7f39bd28e194bfe7fc6cfca844ed4a653e9d209b0db8d77eef9'
    assert intent['archiveSha256']=='e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b'
    assert intent['pythonSha256']=='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
    assert os.environ.get('WSL_DISTRO_NAME')==LAB
    assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()==LAB
    assert not pathlib.Path('/mnt/c/Windows').exists(),'windows_mount_present'
    assert sys.platform=='linux' and os.uname().machine=='x86_64'
    assert sys.executable==PYTHON and sys.flags.isolated==1 and sys.dont_write_bytecode
    assert os.getresuid()==os.getresgid()==(0,0,0),'host_root_required'
    for name in ('uid_map','gid_map'):
        assert pathlib.Path('/proc/self',name).read_text().split()==['0','0','4294967295'],'initial_userns_required'
    trusted(pathlib.Path(PYTHON),False)
    assert sha(pathlib.Path(PYTHON).read_bytes())==intent['pythonSha256'],'interpreter_changed'
    trusted(INPUT.parent,True)
    assert not os.path.lexists(INPUT) and not os.path.lexists(DEST),'fresh_paths_required'
    raw=sys.stdin.buffer.read(MAX+1)
    assert len(raw)==intent['bundleBytes']<=MAX and sha(raw)==intent['bundleSha256'],'bundle_identity'
    assert set(intent['members'])==set(FILES),'member_inventory'
    data={}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist()
        assert len(infos)==len(FILES) and {i.filename for i in infos}==set(FILES),'bundle_members'
        for info in infos:
            assert info.compress_type==zipfile.ZIP_STORED and not info.is_dir(),'bundle_encoding'
            expected=intent['members'][info.filename]
            assert info.file_size==info.compress_size==expected['bytes'] and 0<info.file_size<=MAX,'member_bound'
            value=archive.read(info)
            assert len(value)==expected['bytes'] and sha(value)==expected['sha256'],'member_identity'
            data[info.filename]=value
    assert sha(data['candidate/manifest.json'])==intent['manifestSha256']
    assert sha(data['candidate/projected-source.tar'])==intent['archiveSha256']
    assert sha(data['scripts/build_projected_candidate.py'])=='97be4be2a0aec7a045fd099b1f56b12c58501e312777e1ad67fee45cbe601cc7'
    assert sha(data['scripts/install_projected_candidate.py'])==intent['installerSha256']
    report['phase']='STAGING_REVIEWED_INPUTS'
    INPUT.mkdir(mode=0o755);created=True
    (INPUT/'candidate').mkdir(mode=0o755);(INPUT/'scripts').mkdir(mode=0o755)
    put(INPUT/'operator-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\n').encode())
    for name in FILES:put(INPUT/name,data[name])
    report['phase']='INSTALLER_INVOKED'
    command=[PYTHON,'-I','-B',str(INPUT/'scripts/install_projected_candidate.py'),
        '--candidate-directory',str(INPUT/'candidate'),'--destination',str(DEST),
        '--dependencies',DEPS,'--expected-manifest-sha256',intent['manifestSha256'],
        '--expected-archive-sha256',intent['archiveSha256'],
        '--expected-harness-commit',intent['harnessCommit'],
        '--expected-python-sha256',intent['pythonSha256']]
    process=subprocess.Popen(command,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},
        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)
    report['installerPid']=process.pid
    try:
        out,err=process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        report.update(phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)
        raise RuntimeError('installer_timeout_unknown')
    assert len(out)<=1024*1024 and len(err)<=65536,'installer_output_bound'
    report.update(installerExitCode=process.returncode,installerStdout=out.decode('utf-8'),installerStderr=err.decode('utf-8'))
    assert process.returncode==0,'installer_refused_or_failed'
    result=json.loads(out)
    assert type(result) is dict and result.get('installed') is True,'installer_success_receipt_missing'
    assert result.get('executionAuthorized') is False,'installer_execution_claim'
    report.update(phase='INSTALLED_SOURCE_ONLY',installed=True,installerResult=result,
                  inputDirectory=str(INPUT),destination=str(DEST),pythonSha256=intent['pythonSha256'],
                  bundleSha256=intent['bundleSha256'])
except BaseException as exc:
    report.update(errorType=type(exc).__name__,errorCode=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else 'local_io_or_parse_failed')
    if isinstance(exc,(KeyboardInterrupt,SystemExit)):report['processMayBeRunning']=True
report['inputDirectoryCreated']=created
report['destinationExists']=os.path.lexists(DEST)
if created:
    try:put(INPUT/'operator-result.json',(json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
    except BaseException as exc:report['operatorResultWriteError']=type(exc).__name__;report['installed']=False
print(json.dumps(report,sort_keys=True),flush=True)
raise SystemExit(0 if report['installed'] and report['phase']=='INSTALLED_SOURCE_ONLY' else 2)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)
    assert path.read_bytes() == data, 'host_readback_changed'


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True,
                          check=True, timeout=30).stdout.decode().strip()


def candidate():
    return (ROOT.parent / 'm1-product-path-r153a1' / 'scratch/projected-candidates'
            / 'r153a1-current-source-002')


def current_sources(installer_sha, runner_sha):
    runner = Path(__file__).read_bytes()
    installer = (ROOT / 'scripts/install_projected_candidate.py').read_bytes()
    builder = (ROOT / 'scripts/build_projected_candidate.py').read_bytes()
    assert sha(runner) == runner_sha, 'reviewed_driver_changed'
    assert sha(installer) == installer_sha, 'reviewed_installer_changed'
    assert sha(builder) == BUILDER_SHA, 'accepted_verifier_changed'
    return runner, installer, builder


def prepare(directory, installer_sha, runner_sha):
    assert not directory.exists(), 'attempt_already_exists'
    runner, installer, builder = current_sources(installer_sha, runner_sha)
    manifest = (candidate() / 'manifest.json').read_bytes()
    archive = (candidate() / 'projected-source.tar').read_bytes()
    assert sha(manifest) == MANIFEST_SHA and sha(archive) == ARCHIVE_SHA, 'candidate_changed'
    parsed = json.loads(manifest)
    assert parsed['harnessCommit'] == SOURCE and parsed['nativeFeature'] == NATIVE
    payload = {'candidate/manifest.json': manifest, 'candidate/projected-source.tar': archive,
               'scripts/build_projected_candidate.py': builder,
               'scripts/install_projected_candidate.py': installer}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as bundle:
        for name in MEMBERS:
            info = zipfile.ZipInfo(name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (0o100644 << 16)
            bundle.writestr(info, payload[name])
    raw = stream.getvalue()
    assert len(raw) <= MAX_BUNDLE
    intent = {'kind': 'R154A1_SOURCE_INSTALL_INTENT', 'lab': LAB,
              'inputDirectory': INPUT, 'destination': DESTINATION, 'dependencyRoot': DEPENDENCIES,
              'harnessCommit': SOURCE, 'nativeFeature': NATIVE, 'workspaceHead': git('rev-parse', 'HEAD'),
              'manifestSha256': MANIFEST_SHA, 'archiveSha256': ARCHIVE_SHA,
              'builderSha256': BUILDER_SHA, 'installerSha256': installer_sha,
              'runnerSha256': runner_sha, 'transportSha256': sha(LINUX_TRANSPORT.encode()),
              'pythonSha256': PYTHON_SHA, 'bundleSha256': sha(raw), 'bundleBytes': len(raw),
              'members': {n: {'sha256': sha(payload[n]), 'bytes': len(payload[n])} for n in MEMBERS},
              'installationOnly': True, 'mountsOrNativeExecutionAuthorized': False,
              'realModelCalls': 0, 'automaticRetry': False, 'automaticCleanup': False}
    directory.mkdir(parents=True, exist_ok=False)
    write_new(directory / 'input.zip', raw)
    write_new(directory / 'intent.json', canonical(intent))
    write_new(directory / 'linux-transport.py', LINUX_TRANSPORT.encode())
    write_new(directory / 'reviewed-runner.py', runner)
    return {'state': 'PREPARED_NOT_EXECUTED', 'attempt': str(directory),
            'bundleSha256': intent['bundleSha256'], 'bundleBytes': len(raw), 'installed': False}


def apply(directory, installer_sha, runner_sha):
    current_sources(installer_sha, runner_sha)
    intent_raw = (directory / 'intent.json').read_bytes()
    intent = json.loads(intent_raw)
    assert intent_raw == canonical(intent), 'intent_not_canonical'
    assert intent['workspaceHead'] == git('rev-parse', 'HEAD'), 'workspace_head_changed'
    assert intent['installerSha256'] == installer_sha and intent['runnerSha256'] == runner_sha
    assert intent['archiveSha256'] == ARCHIVE_SHA and intent['manifestSha256'] == MANIFEST_SHA
    assert intent['builderSha256'] == BUILDER_SHA and intent['pythonSha256'] == PYTHON_SHA
    assert intent['harnessCommit'] == SOURCE and intent['nativeFeature'] == NATIVE
    assert intent['lab'] == LAB and intent['inputDirectory'] == INPUT
    assert intent['destination'] == DESTINATION and intent['dependencyRoot'] == DEPENDENCIES
    transport = (directory / 'linux-transport.py').read_bytes()
    assert transport == LINUX_TRANSPORT.encode() and sha(transport) == intent['transportSha256']
    raw = (directory / 'input.zip').read_bytes()
    assert len(raw) == intent['bundleBytes'] <= MAX_BUNDLE and sha(raw) == intent['bundleSha256']
    start = {'state': 'EXECUTION_STARTED_NO_REPLAY', 'intentSha256': sha(intent_raw),
             'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'destination': DESTINATION, 'rootRequested': True, 'installationOnly': True}
    write_new(directory / 'execution-start.json', canonical(start))
    command = ['wsl.exe', '--distribution', LAB, '--user', 'root', '--cd', '/', '--exec',
               '/usr/bin/python3.12', '-I', '-B', '-c', transport.decode(),
               json.dumps(intent, sort_keys=True, separators=(',', ':'))]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        out, err = process.communicate(raw, timeout=150)
    except subprocess.TimeoutExpired:
        terminal = {'state': 'UNKNOWN', 'hostPid': process.pid, 'processMayBeRunning': True,
                    'installed': False, 'automaticRetry': False, 'automaticCleanup': False}
        write_new(directory / 'terminal.json', canonical(terminal))
        return terminal
    write_new(directory / 'stdout.txt', out)
    write_new(directory / 'stderr.txt', err)
    try:
        result = json.loads(out)
    except (ValueError, UnicodeError):
        result = None
    accepted = (process.returncode == 0 and not err and type(result) is dict
                and result.get('phase') == 'INSTALLED_SOURCE_ONLY' and result.get('installed') is True)
    terminal = {'state': 'INSTALLED_SOURCE_ONLY' if accepted else 'NOT_ACCEPTED',
                'exitCode': process.returncode, 'hostPid': process.pid,
                'stdoutSha256': sha(out), 'stderrSha256': sha(err),
                'installed': accepted, 'projectedReadinessAccepted': False,
                'finiteWorkExecuted': False, 'realModelCalls': 0,
                'automaticRetry': False, 'automaticCleanup': False}
    if result is not None:
        write_new(directory / 'result.json', canonical(result))
    write_new(directory / 'terminal.json', canonical(terminal))
    return terminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--expected-installer-sha256', required=True)
    parser.add_argument('--expected-runner-sha256', required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]{1,40}', args.attempt), 'invalid_attempt'
    for digest in (args.expected_installer_sha256, args.expected_runner_sha256):
        assert re.fullmatch('[0-9a-f]{64}', digest), 'exact_review_digest_required'
    directory = ROOT / 'scratch/install-candidates' / args.attempt
    function = prepare if args.prepare else apply
    result = function(directory, args.expected_installer_sha256, args.expected_runner_sha256)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['state'] in ('PREPARED_NOT_EXECUTED', 'INSTALLED_SOURCE_ONLY') else 2


if __name__ == '__main__':
    raise SystemExit(main())
