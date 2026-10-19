"""PLAT-002A one-shot Windows/native WSL identity receipt capture.

Starts only the pinned read-only QA responder. No model, extra host
account, WSL installation, privileged operation or arbitrary agent tool.
Never replaces an existing receipt; preserves a failed attempt.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'evidence/plat-002a-wsl-19oct'
HOST=ROOT/'scripts/qa/wsl2_bridge_host_probe.mjs'
FIXED=[
    'packages/hybrid-runtime/wsl2-readonly-bridge.mjs',
    'scripts/qa/wsl2_bridge_host_probe.mjs',
    'scripts/qa/wsl2_bridge_guest_probe.py',
    'scripts/qa/capture_wsl2_bridge_identity.py',
    'tests/node/wsl2-bridge-cases.mjs',
    'tests/test_wsl2_bridge.py',
    'tests/test_wsl2_guest_protocol.py',
]

def run(node,args,optin):
    env={name:value for name,value in os.environ.items()
         if name.upper() in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP')}
    if optin:env['ALAZ_WSL2_READONLY_PROBE']='1'
    cmd=[node,str(HOST),*args]
    proc=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,
                        text=True,encoding='utf-8',errors='replace',timeout=35)
    try:
        result=json.loads(proc.stdout.strip())
    except ValueError:
        return {'exitCode':proc.returncode,'result':'INVALID_OUTPUT'}
    # Omit stderr and all child process paths from the public record.
    return {'exitCode':proc.returncode,'report':result}

def main():
    # Python platform.machine() is blank in this Windows invocation,
    # so the pinned Node probe is the authoritative x64 process gate.
    assert sys.platform=='win32'
    assert EVIDENCE.is_dir()
    dest=EVIDENCE/'native-win-wsl-identity-01.json'
    assert not dest.exists() and not dest.is_symlink()
    node=shutil.which('node')
    assert node and HOST.is_file()
    cases={
      'positive':run(node,['--read-only','--expected-uid=1000'],True),
      'wrongExpectedUid':run(node,['--read-only','--expected-uid=65534'],True),
      'missingQaOptIn':run(node,['--read-only','--expected-uid=1000'],False),
      'unknownCommand':run(node,['--read-only','--expected-uid=1000',
                                '--shell=cmd.exe'],True),
      'missingArgs':run(node,[],True),
    }
    pos=cases['positive']
    protected=pos.get('report',{})
    correct=(pos.get('exitCode')==0 and
      protected.get('result')=='PASS_READ_ONLY_GUEST_SELF_REPORT' and
      protected.get('hostPlatform')=='win32' and
      protected.get('guestPlatform')=='linux' and
      protected.get('guestEnvironment')=='linux-wsl2-guest' and
      protected.get('guestUid')==1000 and
      protected.get('sourceSha256Matched') is True and
      protected.get('nonceMatched') is True and
      protected.get('requestIdMatched') is True and
      protected.get('childExitCode')==0 and
      protected.get('childCloseObserved') is True and
      protected.get('hostFilesystemIsolated') is False and
      protected.get('secureExecutionAccepted') is False and
      protected.get('independentHostUidVerified') is False and
      protected.get('realModelCalls')==0)
    refusals={
      'wrongExpectedUid':'BRIDGE_REPLY_VERIFICATION_FAILED',
      'missingQaOptIn':'EXPLICIT_QA_OPT_IN_REQUIRED',
      'unknownCommand':'INVALID_READONLY_PROBE_ARGUMENTS',
      'missingArgs':'INVALID_READONLY_PROBE_ARGUMENTS',
    }
    for name,expected in refusals.items():
        obj=cases[name]
        correct=(correct and obj.get('exitCode')==2 and
                 obj.get('report',{}).get('result')=='REFUSED' and
                 obj['report'].get('code')==expected and
                 obj['report'].get('fallback') is False and
                 obj['report'].get('realModelCalls')==0)
    source={}
    for name in FIXED:
        path=ROOT/name
        payload=path.read_bytes()
        source[name]=hashlib.sha256(payload.replace(b'\r\n',b'\n')).hexdigest()
    report={'gate':'PLAT-002A-WINDOWS-WSL2-READONLY',
            'result':'PASS_SCOPED_READ_ONLY_IDENTITY' if correct else 'FAIL',
            'host':'Windows-x64','guest':'WSL2-Linux-x64',
            'nativeCases':cases,
            'nativeCheckCount':len(cases),
            'sourceCanonicalLfSha256':source,
            'realModelCalls':0,'privilegedCommands':0,
            'independentHostUidVerified':False,
            'hostFilesystemIsolated':False,
            'fullD3BAccepted':False,
            'agentOrToolStarted':False,
            'guestProcessCancellationNativeTested':False,
            'guestRestartOrReplayNativeTested':False,
            'secureAdapterActivated':False,
            'mainMerged':False}
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',
                    encoding='utf-8')
    print(json.dumps({'result':report['result'],'nativeCases':len(cases),
                      'readOnlyPositive':bool(correct),
                      'realModelCalls':0,
                      'fullD3BAccepted':False}))
    return 0 if correct else 1

if __name__=='__main__':
    raise SystemExit(main())
