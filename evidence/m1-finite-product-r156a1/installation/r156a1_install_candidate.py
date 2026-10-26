'One fixed R156 source installation in the dedicated P71C laboratory.\n\nGenerated from the exact reviewed R154 operator by literal binding changes.\nPreparation and apply remain explicit, one-shot and source-only. No native,\nmount, model, service, retry or cleanup action is added.\n'
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

ROOT = Path('C:\\Antigravity\\AlazHarness\\scratch\\worktrees\\m1-finite-product-r156a1')
LAB = 'AlazHarness-D3B-P71C'
NATIVE = 'd1516731308de8e87130dc68124e69aad35d6911'
SOURCE = 'e641a5000810efb2a453ae847f689b422f7d41a7'
ARCHIVE_SHA = '3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8'
MANIFEST_SHA = '7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a'
BUILDER_SHA = '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b'
PYTHON_SHA = 'e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'
INPUT = '/opt/alaz-r156a1-install-input'
DESTINATION = '/opt/alaz-r156a1'
DEPENDENCIES = '/opt/alaz-f126c1a6/dependencies'
MAX_BUNDLE = 24 * 1024 * 1024
MEMBERS = ('candidate/manifest.json', 'candidate/projected-source.tar',
           'scripts/build_projected_candidate.py', 'scripts/install_projected_candidate.py')


LINUX_TRANSPORT = "\nimport hashlib,io,json,os,pathlib,re,stat,subprocess,sys,zipfile\nLAB='AlazHarness-D3B-P71C'\nPYTHON='/usr/bin/python3.12'\nINPUT=pathlib.Path('/opt/alaz-r156a1-install-input')\nDEST=pathlib.Path('/opt/alaz-r156a1')\nDEPS='/opt/alaz-f126c1a6/dependencies'\nMAX=24*1024*1024\nFILES=('candidate/manifest.json','candidate/projected-source.tar',\n       'scripts/build_projected_candidate.py','scripts/install_projected_candidate.py')\nreport={'kind':'R156A1_SOURCE_INSTALL_OPERATION','phase':'PREFLIGHT','installed':False,\n        'executionAuthorized':False,'projectedReadinessAccepted':False,\n        'finiteWorkExecuted':False,'realModelCalls':0,'mountsChanged':False,\n        'servicesChanged':False,'dependencyDownloads':0,'automaticCleanup':False}\ncreated=False\ndef sha(data):return hashlib.sha256(data).hexdigest()\ndef trusted(path,directory):\n    assert path.is_absolute() and path.resolve(strict=True)==path,'noncanonical_input_ancestry'\n    for p in (path,*path.parents):\n        s=p.lstat()\n        assert s.st_uid==s.st_gid==0 and not s.st_mode&0o022 and not stat.S_ISLNK(s.st_mode),'untrusted_input_ancestry'\n    assert path.is_dir() if directory else path.is_file()\ndef put(path,data):\n    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)\n    with os.fdopen(fd,'wb') as stream:\n        stream.write(data);stream.flush();os.fchmod(stream.fileno(),0o644);os.fsync(stream.fileno())\n    assert path.read_bytes()==data,'provisioning_readback_mismatch'\ndef new_directory(path):\n    path.mkdir(mode=0o700)\n    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)\n    try:os.fchmod(fd,0o755);os.fsync(fd)\n    finally:os.close(fd)\ntry:\n    assert len(sys.argv)==2,'transport_argument_count'\n    intent=json.loads(sys.argv[1])\n    assert intent['kind']=='R156A1_SOURCE_INSTALL_INTENT'\n    assert intent['lab']==LAB and intent['inputDirectory']==str(INPUT) and intent['destination']==str(DEST)\n    assert intent['dependencyRoot']==DEPS and intent['nativeFeature']=='d1516731308de8e87130dc68124e69aad35d6911'\n    assert intent['harnessCommit']=='e641a5000810efb2a453ae847f689b422f7d41a7'\n    assert intent['manifestSha256']=='7a886c32fd81d046d44715921bdaae5765a6f4e481d33182258cc7aa2bac465a'\n    assert intent['archiveSha256']=='3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8'\n    assert intent['pythonSha256']=='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f'\n    assert os.environ.get('WSL_DISTRO_NAME')==LAB\n    assert pathlib.Path('/etc/alaz-p71c-lab-id').read_text().strip()==LAB\n    assert not pathlib.Path('/mnt/c/Windows').exists(),'windows_mount_present'\n    assert sys.platform=='linux' and os.uname().machine=='x86_64'\n    assert sys.executable==PYTHON and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize\n    assert os.getresuid()==os.getresgid()==(0,0,0),'host_root_required'\n    for name in ('uid_map','gid_map'):\n        assert pathlib.Path('/proc/self',name).read_text().split()==['0','0','4294967295'],'initial_userns_required'\n    trusted(pathlib.Path(PYTHON),False)\n    assert sha(pathlib.Path(PYTHON).read_bytes())==intent['pythonSha256'],'interpreter_changed'\n    trusted(INPUT.parent,True)\n    assert not os.path.lexists(INPUT) and not os.path.lexists(DEST),'fresh_paths_required'\n    raw=sys.stdin.buffer.read(MAX+1)\n    assert len(raw)==intent['bundleBytes']<=MAX and sha(raw)==intent['bundleSha256'],'bundle_identity'\n    assert set(intent['members'])==set(FILES),'member_inventory'\n    data={}\n    with zipfile.ZipFile(io.BytesIO(raw)) as archive:\n        infos=archive.infolist()\n        assert len(infos)==len(FILES) and {i.filename for i in infos}==set(FILES),'bundle_members'\n        for info in infos:\n            assert info.compress_type==zipfile.ZIP_STORED and not info.is_dir(),'bundle_encoding'\n            expected=intent['members'][info.filename]\n            assert info.file_size==info.compress_size==expected['bytes'] and 0<info.file_size<=MAX,'member_bound'\n            value=archive.read(info)\n            assert len(value)==expected['bytes'] and sha(value)==expected['sha256'],'member_identity'\n            data[info.filename]=value\n    assert sha(data['candidate/manifest.json'])==intent['manifestSha256']\n    assert sha(data['candidate/projected-source.tar'])==intent['archiveSha256']\n    assert sha(data['scripts/build_projected_candidate.py'])=='7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b'\n    assert sha(data['scripts/install_projected_candidate.py'])==intent['installerSha256']\n    report['phase']='STAGING_REVIEWED_INPUTS'\n    new_directory(INPUT);created=True\n    for folder in ('candidate','scripts'):\n        new_directory(INPUT/folder)\n    put(INPUT/'operator-intent.json',(json.dumps(intent,sort_keys=True,indent=2)+'\\n').encode())\n    for name in FILES:put(INPUT/name,data[name])\n    report['phase']='INSTALLER_INVOKED'\n    command=[PYTHON,'-I','-B',str(INPUT/'scripts/install_projected_candidate.py'),\n        '--candidate-directory',str(INPUT/'candidate'),'--destination',str(DEST),\n        '--dependencies',DEPS,'--expected-manifest-sha256',intent['manifestSha256'],\n        '--expected-archive-sha256',intent['archiveSha256'],\n        '--expected-harness-commit',intent['harnessCommit'],\n        '--expected-python-sha256',intent['pythonSha256']]\n    report['installerSpawnAttempted']=True\n    process=subprocess.Popen(command,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','HOME':'/'},\n        stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)\n    report['installerPid']=process.pid\n    try:\n        out,err=process.communicate(timeout=90)\n    except subprocess.TimeoutExpired:\n        report.update(phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)\n        raise RuntimeError('installer_timeout_unknown')\n    report['installerTerminalObserved']=True\n    assert len(out)<=1024*1024 and len(err)<=65536,'installer_output_bound'\n    report.update(installerExitCode=process.returncode,installerStdout=out.decode('utf-8'),installerStderr=err.decode('utf-8'))\n    assert process.returncode==0,'installer_refused_or_failed'\n    result=json.loads(out)\n    assert type(result) is dict and result.get('result')=='PASS' and result.get('kind')=='VERIFIED_PROJECTED_INSTALLATION','installer_success_receipt_missing'\n    assert result.get('installed') is True and result.get('destination')==str(DEST),'installer_destination_receipt'\n    assert result.get('harnessCommit')==intent['harnessCommit'] and result.get('nativeFeature')==intent['nativeFeature'],'installer_source_receipt'\n    assert result.get('sourceManifestSha256')==intent['manifestSha256'] and result.get('archiveSha256')==intent['archiveSha256'],'installer_candidate_receipt'\n    assert type(result.get('sourceFileCount')) is int and result['sourceFileCount']==838 and type(result.get('dependencyFileCount')) is int and result['dependencyFileCount']==1162,'installer_inventory_receipt'\n    assert all(result.get(k) is False for k in ('executionAuthorized','projectedReadinessAccepted','finiteWorkExecuted')),'installer_execution_claim'\n    assert type(result.get('realModelCalls')) is int and result['realModelCalls']==0,'installer_model_claim'\n    assert result.get('sourceAndDependenciesReadBack') is True and result.get('rootControlledAncestryVerified') is True,'installer_readback_receipt'\n    assert type(result.get('receiptSha256')) is str and re.fullmatch('[0-9a-f]{64}',result['receiptSha256']),'installer_receipt_digest'\n    python=result.get('python')\n    assert type(python) is dict and python.get('path')==PYTHON and python.get('sha256')==intent['pythonSha256'] and python.get('uid')==python.get('gid')==0 and python.get('mode')==0o755,'installer_python_receipt'\n    report.update(phase='INSTALLED_SOURCE_ONLY',installed=True,installerResult=result,\n                  inputDirectory=str(INPUT),destination=str(DEST),pythonSha256=intent['pythonSha256'],\n                  bundleSha256=intent['bundleSha256'])\nexcept BaseException as exc:\n    report.update(errorType=type(exc).__name__,errorCode=str(exc) if isinstance(exc,(AssertionError,RuntimeError)) else 'local_io_or_parse_failed')\n    if report.get('installerSpawnAttempted') and not report.get('installerTerminalObserved'):\n        report.update(failurePhase=report['phase'],phase='INSTALLER_OUTCOME_UNKNOWN',processMayBeRunning=True)\nreport['inputDirectoryCreated']=created\nreport['destinationExists']=os.path.lexists(DEST)\nif created:\n    try:put(INPUT/'operator-result.json',(json.dumps(report,sort_keys=True,indent=2)+'\\n').encode())\n    except BaseException as exc:report['operatorResultWriteError']=type(exc).__name__;report['installed']=False\nprint(json.dumps(report,sort_keys=True),flush=True)\nraise SystemExit(0 if report['installed'] and report['phase']=='INSTALLED_SOURCE_ONLY' else 2)\n"


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
    return Path('C:\\Antigravity\\AlazHarness\\scratch\\worktrees\\m1-finite-product-r156a1\\scratch\\projected-candidates\\r156a1-native-finite-001')


def current_sources(installer_sha, runner_sha):
    runner = Path(__file__).read_bytes()
    installer = (ROOT / 'scripts/install_projected_candidate.py').read_bytes()
    builder = (ROOT / 'scripts/build_projected_candidate.py').read_bytes()
    assert sha(runner) == runner_sha, 'reviewed_driver_changed'
    assert sha(installer) == installer_sha, 'reviewed_installer_changed'
    assert sha(builder) == BUILDER_SHA, 'accepted_verifier_changed'
    return runner, installer, builder


def installation_terminal(returncode, out, err, result, host_pid):
    """Preserve unknown child effects across the Linux/Windows receipt boundary."""
    valid = type(result) is dict and result.get('kind') == 'R156A1_SOURCE_INSTALL_OPERATION'
    terminal = valid and result.get('installerTerminalObserved') is True
    unknown = (not valid or result.get('processMayBeRunning') is True
               or (result.get('installerSpawnAttempted') is True and not terminal)
               or result.get('phase') == 'INSTALLER_OUTCOME_UNKNOWN'
               or (result.get('phase') == 'INSTALLER_INVOKED' and not terminal))
    accepted = (not unknown and returncode == 0 and not err and terminal
                and result.get('phase') == 'INSTALLED_SOURCE_ONLY'
                and result.get('installed') is True and result.get('installerExitCode') == 0)
    return {'state': 'UNKNOWN' if unknown else ('INSTALLED_SOURCE_ONLY' if accepted else 'NOT_ACCEPTED'),
            'exitCode': returncode, 'hostPid': host_pid,
            'installerPid': result.get('installerPid') if valid else None,
            'installerTerminalObserved': bool(terminal), 'processMayBeRunning': bool(unknown),
            'rootPhase': result.get('phase') if valid else None,
            'stdoutSha256': sha(out), 'stderrSha256': sha(err),
            'installed': bool(accepted), 'projectedReadinessAccepted': False,
            'finiteWorkExecuted': False, 'realModelCalls': 0,
            'automaticRetry': False, 'automaticCleanup': False}


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
    intent = {'kind': 'R156A1_SOURCE_INSTALL_INTENT', 'lab': LAB,
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
    terminal = installation_terminal(process.returncode, out, err, result, process.pid)
    if result is not None:
        write_new(directory / 'result.json', canonical(result))
    write_new(directory / 'terminal.json', canonical(terminal))
    return terminal


def main():
    if sys.flags.optimize:
        raise RuntimeError('optimized_driver_refused')
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
