"""One explicit ordinary-user proof of the frozen R155 task-free producer.

No root, image, mount, cgroup, provider or service action. Every attempt uses a
new lab home and an exclusive execution-start record; failures preserve it.
Timeouts are unknown and never trigger terminate/kill/retry/cleanup.
"""
from __future__ import annotations
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PRODUCER_SHA = '02ac2d81d72e0ab11739081b3b95ccb05db2871581bc3494518fe2190a66a5aa'
LINUX = "import base64,hashlib,json,os,pathlib,re,sqlite3,stat,subprocess,sys,time\nP=pathlib.Path\ndef sha(raw):return hashlib.sha256(raw).hexdigest()\ndef canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\\n').encode('ascii')\ndef require(ok,reason):\n    if not ok:raise RuntimeError(reason)\ndef put(path,raw,mode):\n    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode)\n    with os.fdopen(fd,'wb') as stream:\n        stream.write(raw);stream.flush();os.fsync(stream.fileno())\nreport={'kind':'R156A1_ORDINARY_NATIVE_SEED_PROOF','result':'NOT_ACCEPTED','rootUsed':False,\n        'projectedReadinessAccepted':False,'sameImageReadinessAccepted':False,'fullD3BAccepted':False,\n        'automaticCleanup':False,'automaticRetry':False,'nativeAccepted':False,'phase':'PREFLIGHT'}\nprocess=None\ntry:\n    require(len(sys.argv)==4,'argument_count')\n    attempt,expected,size=sys.argv[1:]\n    require(re.fullmatch(r'ordinary00[1-9]',attempt) is not None,'attempt_id')\n    require(expected=='02ac2d81d72e0ab11739081b3b95ccb05db2871581bc3494518fe2190a66a5aa','source_pin')\n    require(os.getresuid()==(23001,)*3 and os.getresgid()==(23003,)*3\n            and set(os.getgroups())<={23003},'ordinary_actor')\n    require(sys.executable=='/usr/bin/python3.12' and sys.version_info[:2]==(3,12)\n            and sys.flags.isolated==1 and sys.dont_write_bytecode and not sys.flags.optimize,'interpreter')\n    require(sha(P(sys.executable).read_bytes())=='e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f','python_pin')\n    require(os.environ.get('WSL_DISTRO_NAME')=='AlazHarness-D3B-P71C'\n            and P('/etc/alaz-p71c-lab-id').read_text().strip()=='AlazHarness-D3B-P71C'\n            and not P('/mnt/c/Windows').exists(),'dedicated_lab')\n    base=P('/tmp/alaz-r156a1-'+attempt)\n    require(not os.path.lexists(base),'fresh_home_required')\n    raw=sys.stdin.buffer.read(262145)\n    require(len(raw)==int(size)<=262144 and sha(raw)==expected,'producer_bytes')\n    os.umask(0o077)\n    base.mkdir(mode=0o700)\n    report.update(phase='FRESH_HOME_CREATED',path=str(base),sourceSha256=expected,\n                  sqliteVersion=sqlite3.sqlite_version,sqliteVersionInfo=list(sqlite3.sqlite_version_info),\n                  controllerPid=os.getpid(),supplementaryGroups=os.getgroups())\n    source=base/'bootstrap_retained_profile_r156.py'\n    put(source,raw,0o444)\n    home=base/'profile';home.mkdir(mode=0o700);info=home.stat()\n    require(source.read_bytes()==raw and home.resolve()==home,'source_or_home_changed')\n    argv=['/usr/bin/python3.12','-I','-B',str(source),'--home',str(home),\n          '--instance-id','r156a1-'+attempt,'--expected-profile-device',str(info.st_dev),\n          '--expected-profile-inode',str(info.st_ino),'--gateway-uid','23001',\n          '--socket-group-gid','23003','--parent-pid',str(os.getpid())]\n    report.update(phase='PRODUCER_SPAWN_ATTEMPT',nativeProcessAttempted=True)\n    started=time.monotonic()\n    process=subprocess.Popen(argv,cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TZ':'UTC'},\n                             stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True)\n    report['producerPid']=process.pid\n    try:out,err=process.communicate(timeout=45)\n    except subprocess.TimeoutExpired as exc:\n        report.update(phase='PRODUCER_OUTCOME_UNKNOWN',processMayBeRunning=True,\n                      partialStdoutBase64=base64.b64encode((exc.output or b'')[:32768]).decode(),\n                      partialStderrBase64=base64.b64encode((exc.stderr or b'')[:65536]).decode())\n        raise RuntimeError('producer_timeout_unknown')\n    report.update(phase='PRODUCER_TERMINAL',producerExitCode=process.returncode,\n                  producerTerminalObserved=True,elapsedMillis=int((time.monotonic()-started)*1000),\n                  producerStdoutSha256=sha(out),producerStderrSha256=sha(err),\n                  producerStdoutBytes=len(out),producerStderrBytes=len(err))\n    put(base/'producer.stdout',out,0o600);put(base/'producer.stderr',err,0o600)\n    require(len(out)<=32768 and len(err)<=65536,'producer_output_bound')\n    report.update(producerStdoutBase64=base64.b64encode(out).decode(),\n                  producerStderrBase64=base64.b64encode(err).decode())\n    require(process.returncode==0,'producer_refused_or_failed')\n    require(out.endswith(b'\\n') and out.count(b'\\n')==1,'producer_frame')\n    value=json.loads(out)\n    require(canonical(value)==out,'producer_canonical_frame')\n    require(value['kind']=='R156A1_TASK_FREE_RETAINED_SEED' and value['result']=='PASS'\n            and value['state']=='RETAINED_SEED_CREATED' and value['phase']=='COMPLETE','producer_success')\n    require(value['pid']==process.pid and value['parentPid']==os.getpid()\n            and value['home']==str(home) and value['profileIdentity']==[info.st_dev,info.st_ino]\n            and value['instanceId']=='r156a1-'+attempt and value['previousEpoch']==1,'producer_identity')\n    require(value['resUid']==[23001]*3 and value['resGid']==[23003]*3\n            and value['supplementaryGroups']==os.getgroups(),'producer_principal')\n    require(value['mountNamespace']==os.readlink('/proc/self/ns/mnt')\n            and value['mountNamespaceInode']==P('/proc/self/ns/mnt').stat().st_ino\n            and value['mount']['filesystem']=='ext4','producer_actual_mount')\n    require(value['completedChecks']==['preflight','response_preflight','before_epoch',\n            'response_before_epoch','after_epoch','response_after_epoch'],'producer_six_checks')\n    require(value['ownerState']=='CLOSED' and value['consumerState']=='DETACHED'\n            and all(value[k] is True for k in ['allThreeConnectionsPhysicallyClosed',\n                'profileLeaseReleasedNormally','retainedCapturedWhileLeaseHeld','normalLoopShutdown']),\n            'producer_normal_close')\n    require(all(type(value[k]) is int and value[k]==0 for k in ['outstandingAsyncTasks',\n            'outstandingThreads','executedTasks','realModelCalls','listenersCreated'])\n            and all(value[k] is False for k in ['apiAdmissionPublished','projectedReadinessAccepted',\n                'fullD3BAccepted','automaticCleanup','automaticRetry']),'producer_scope')\n    require(value['installationReceiptSha256']=='a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845'\n            and value['harnessCommit']=='e641a5000810efb2a453ae847f689b422f7d41a7'\n            and value['nativeFeature']=='d1516731308de8e87130dc68124e69aad35d6911','producer_installed_source')\n    probe=value['auxiliaryInitialization']['blockedIpv6CapabilityProbe']\n    require(type(probe) is dict and set(probe)=={'count','socketClosed','bindPerformed'}\n            and type(probe['count']) is int and probe['count']==1\n            and probe['socketClosed'] is True and probe['bindPerformed'] is False,'producer_blocked_probe')\n    report.update(phase='COMPLETE',result='PASS',nativeAccepted=True,seed=value,\n                  realModelCalls=0,executedTasks=0,physicalDatabaseCloseAccepted=True)\nexcept BaseException as exc:\n    report.update(reasonType=type(exc).__name__,reason=str(exc)[:200] if type(exc) is RuntimeError else type(exc).__name__,\n                  partialStatePreserved=True)\nsys.stdout.buffer.write(canonical(report));sys.stdout.buffer.flush()\nraise SystemExit(0 if report['result']=='PASS' else 2)\n"


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('ascii')


def put(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)


def run(attempt, evidence):
    if not re.fullmatch('ordinary00[1-9]', attempt):
        raise ValueError('fixed ordinary attempt ID required')
    evidence = evidence.resolve()
    if not evidence.is_relative_to(ROOT / 'evidence/m1-native-finite-r156a1'):
        raise ValueError('owned evidence path required')
    raw = (ROOT / 'scripts/bootstrap_retained_profile_r156.py').read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRODUCER_SHA:
        raise ValueError('reviewed producer source changed')
    evidence.mkdir(exist_ok=False)
    put(evidence / 'producer-source.py', raw)
    put(evidence / 'linux-runner.py', LINUX.encode('utf-8'))
    put(evidence / 'execution-start.json', canonical({'state': 'EXECUTION_STARTED_NO_REPLAY',
        'attempt': attempt, 'startedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producerSha256': PRODUCER_SHA, 'linuxRunnerSha256': hashlib.sha256(LINUX.encode()).hexdigest(),
        'rootRequested': False, 'lab': 'AlazHarness-D3B-P71C'}))
    command = ['wsl.exe', '--distribution', 'AlazHarness-D3B-P71C', '--user', 'alazgateway',
        '--cd', '/', '--exec', '/usr/bin/python3.12', '-I', '-B', '-c', LINUX,
        attempt, PRODUCER_SHA, str(len(raw))]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = process.communicate(raw, timeout=75)
    except subprocess.TimeoutExpired as exc:
        put(evidence / 'stdout.txt', exc.output or b'')
        put(evidence / 'stderr.txt', exc.stderr or b'')
        result = {'result': 'UNKNOWN', 'state': 'WSL_OUTCOME_UNKNOWN', 'hostPid': process.pid,
                  'rootRequested': False, 'automaticRetry': False, 'automaticCleanup': False}
        put(evidence / 'result.json', canonical(result))
        print(json.dumps(result, sort_keys=True))
        return 2
    put(evidence / 'stdout.txt', out)
    put(evidence / 'stderr.txt', err)
    result = {'result': 'NOT_ACCEPTED', 'exitCode': process.returncode, 'rootRequested': False,
        'stdoutSha256': hashlib.sha256(out).hexdigest(), 'stderrSha256': hashlib.sha256(err).hexdigest(),
        'producerSha256': PRODUCER_SHA, 'automaticRetry': False, 'automaticCleanup': False}
    if len(out) <= 262144:
        try:
            parsed = json.loads(out)
            result['proof'] = parsed
            if process.returncode == 0 and parsed.get('result') == 'PASS' and parsed.get('nativeAccepted') is True:
                result['result'] = 'PASS'
        except (ValueError, UnicodeError):
            result['reason'] = 'invalid_linux_report'
    put(evidence / 'result.json', canonical(result))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'PASS' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--evidence-directory', type=Path, required=True)
    args = parser.parse_args()
    return run(args.attempt, args.evidence_directory)


if __name__ == '__main__':
    raise SystemExit(main())
