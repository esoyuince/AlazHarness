// PLAT-002A offline Node source-contract scenarios; never launches WSL
// unless the separately gated read-only developer CLI is explicitly used.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  validateGuestReport, windowsPathToFixedWslMount, fixedProbePlan,
  probeFixedWindowsWsl2, WslBridgeRejected,
} from '../../packages/hybrid-runtime/wsl2-readonly-bridge.mjs';

const HEX64='a'.repeat(64);
const REQUEST='b'.repeat(32);
const SOURCE='c'.repeat(64);
const EXPECT=Object.freeze({
  nonce:HEX64,requestId:REQUEST,sourceSha256:SOURCE,expectedUid:1000,
});
const guest=()=>{
  return {
    version:1,type:'alaz.wsl2.identity.v1',requestId:REQUEST,nonce:HEX64,
    result:'GUEST_SELF_REPORTED_READ_ONLY',
    observed:{
      platform:'linux',arch:'x64',environment:'linux-wsl2-guest',
      uid:1000,euid:1000,gid:1000,pid:482,
      userNamespaceVisible:true,mountNamespaceVisible:true,
      kernelReleaseSha256:'d'.repeat(64),noNewPrivs:'0',seccomp:'0',
    },
    sourceSha256:SOURCE,
    secureLaunchAuthorized:false,hostFilesystemIsolated:false,
    realModelCalls:0,agentOrToolStarted:false,independentHostUidVerified:false,
  };
};
const refuse=(action,code)=>assert.throws(action,e=>
  e instanceof WslBridgeRejected && e.code===code);
const rejectAsync=async(action,code)=>await assert.rejects(action,e=>
  e instanceof WslBridgeRejected && e.code===code);
const accepted=()=>validateGuestReport(guest(),EXPECT);
const cli=fileURLToPath(new URL('../../scripts/qa/wsl2_bridge_host_probe.mjs', import.meta.url));

const scenarios={
  'valid-bound-guest-self-report':()=>{
    const info=accepted();
    assert.equal(info.result,'PASS_READ_ONLY_GUEST_SELF_REPORT');
    assert.equal(info.guestUid,1000);
    assert.equal(info.nonceMatched,true);
    assert.equal(info.requestIdMatched,true);
    assert.equal(info.sourceSha256Matched,true);
    assert.equal(info.secureExecutionAccepted,false);
    assert.equal(info.agentOrToolStarted,false);
    assert.equal(info.automaticRetry,false);
  },
  'not-a-sandbox-certificate':()=>{
    const info=accepted();
    assert.equal(info.hostFilesystemIsolated,false);
    assert.equal(info.independentHostUidVerified,false);
    assert.equal(info.realModelCalls,0);
    assert.equal(info.guestIdentitySelfReported,true);
  },
  'wrong-nonce-refused':()=>{
    const item=guest();item.nonce='f'.repeat(64);
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_NONCE_OR_REQUEST_MISMATCH');
  },
  'wrong-request-id-refused':()=>{
    const item=guest();item.requestId='f'.repeat(32);
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_NONCE_OR_REQUEST_MISMATCH');
  },
  'wrong-guest-source-refused':()=>{
    const item=guest();item.sourceSha256='f'.repeat(64);
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_SOURCE_MISMATCH');
  },
  'invalid-frame-fields-refused':()=>{
    refuse(()=>validateGuestReport({...guest(),task:'run'},EXPECT),
      'BRIDGE_RESPONSE_FIELDS');
  },
  'missing-frame-fields-refused':()=>{
    const item=guest();delete item.nonce;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_RESPONSE_FIELDS');
  },
  'wrong-result-type-refused':()=>{
    const item=guest();item.result='EXECUTION_ALLOWED';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_RESPONSE_VERSION');
  },
  'fake-windows-as-linux-refused':()=>{
    const item=guest();item.observed.platform='win32';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_PLATFORM_MISMATCH');
  },
  'fake-linux-arm64-refused':()=>{
    const item=guest();item.observed.arch='arm64';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_PLATFORM_MISMATCH');
  },
  'fake-wsl2-guest-refused':()=>{
    const item=guest();item.observed.environment='linux-host';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_PLATFORM_MISMATCH');
  },
  'guest-root-refused':()=>{
    const item=guest();item.observed.uid=0;item.observed.euid=0;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'wrong-uid-refused':()=>{
    const item=guest();item.observed.uid=65534;item.observed.euid=65534;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'uid-effective-mismatch-refused':()=>{
    const item=guest();item.observed.euid=0;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'namespace-visibility-required':()=>{
    const item=guest();item.observed.userNamespaceVisible=false;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'kernel-hash-required':()=>{
    const item=guest();item.observed.kernelReleaseSha256='nope';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'seccomp-metadata-bounded':()=>{
    const item=guest();item.observed.seccomp='unverified';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  },
  'extra-observed-fields-refused':()=>{
    const item=guest();item.observed.hostCommand='cmd.exe';
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUEST_IDENTITY_FIELDS');
  },
  'secure-launch-claim-refused':()=>{
    const item=guest();item.secureLaunchAuthorized=true;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUARD_WIDENING_REFUSED');
  },
  'host-filesystem-isolation-claim-refused':()=>{
    const item=guest();item.hostFilesystemIsolated=true;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUARD_WIDENING_REFUSED');
  },
  'independent-host-uid-claim-refused':()=>{
    const item=guest();item.independentHostUidVerified=true;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUARD_WIDENING_REFUSED');
  },
  'real-model-claim-refused':()=>{
    const item=guest();item.realModelCalls=1;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUARD_WIDENING_REFUSED');
  },
  'tool-start-claim-refused':()=>{
    const item=guest();item.agentOrToolStarted=true;
    refuse(()=>validateGuestReport(item,EXPECT),'BRIDGE_GUARD_WIDENING_REFUSED');
  },
  'expected-root-refused':()=>{
    refuse(()=>validateGuestReport(guest(),{...EXPECT,expectedUid:0}),
      'BRIDGE_EXPECTATION_INVALID');
  },
  'expected-extra-field-refused':()=>{
    refuse(()=>validateGuestReport(guest(),{...EXPECT,allowLegacy:true}),
      'BRIDGE_EXPECTATION_INVALID');
  },
  'canonical-fixed-windows-mount':()=>{
    assert.equal(windowsPathToFixedWslMount(
      'C:\\Antigravity\\AlazHarness\\scripts\\qa\\wsl2_bridge_guest_probe.py'),
      '/mnt/c/Antigravity/AlazHarness/scripts/qa/wsl2_bridge_guest_probe.py');
  },
  'windows-unc-refused':()=>{
    refuse(()=>windowsPathToFixedWslMount('\\\\server\\share\\code\\file.py'),
      'HOST_PATH_NOT_ORDINARY_DRIVE');
  },
  'windows-relative-path-refused':()=>{
    refuse(()=>windowsPathToFixedWslMount('scripts\\qa\\file.py'),
      'HOST_PATH_NOT_ORDINARY_DRIVE');
  },
  'windows-parent-traversal-refused':()=>{
    refuse(()=>windowsPathToFixedWslMount(
      'C:\\Antigravity\\AlazHarness\\..\\cmd.exe'),
      'HOST_PATH_UNSAFE_COMPONENT');
  },
  'host-gate-not-remote-authority':()=>{
    if (process.platform !== 'win32' || process.arch !== 'x64') {
      refuse(()=>fixedProbePlan(),'WINDOWS_X64_HOST_REQUIRED');
    } else {
      const p=fixedProbePlan();
      assert.equal(p.expectedKind,'single_read_only_guest_identity');
      assert.equal(p.shell,false);
      assert.equal(p.automaticRetry,false);
      assert.equal(p.secureExecutionAccepted,false);
      assert.equal(p.hostFilesystemIsolated,false);
      assert.equal(p.args[0],'--distribution');
      assert.equal(p.args[1],'Ubuntu');
      assert.equal(p.args[2],'--exec');
      assert.equal(p.args[3],'python3');
      assert.equal(p.args[4],'-I');
      assert.equal(p.args[5],'-B');
      assert.equal(p.args.length,7);
    }
  },
  'pre-aborted-no-process':async()=>{
    const controller=new AbortController();
    controller.abort();
    await rejectAsync(()=>probeFixedWindowsWsl2({
      expectedUid:1000,signal:controller.signal
    }),'BRIDGE_ABORTED_BEFORE_START');
  },
  'invalid-uid-no-process':async()=>{
    await rejectAsync(()=>probeFixedWindowsWsl2({expectedUid:0}),
      'EXPECTED_UNPRIVILEGED_GUEST_UID_REQUIRED');
  },
  'invalid-signal-no-process':async()=>{
    await rejectAsync(()=>probeFixedWindowsWsl2({
      expectedUid:1000,signal:{aborted:false}
    }),'BRIDGE_ABORT_SIGNAL_INVALID');
  },
  'invalid-timeout-no-process':async()=>{
    await rejectAsync(()=>probeFixedWindowsWsl2({
      expectedUid:1000,timeoutMs:500000
    }),'BRIDGE_TIMEOUT_INVALID');
  },
  'cli-no-optin-refused':()=>{
    const env={...process.env};
    delete env.ALAZ_WSL2_READONLY_PROBE;
    const cp=spawnSync(process.execPath,[cli,'--read-only','--expected-uid=1000'],
      {encoding:'utf8',timeout:8000,env,windowsHide:true});
    assert.equal(cp.status,2);
    const obj=JSON.parse(cp.stdout.trim());
    assert.equal(obj.result,'REFUSED');
    assert.equal(obj.code,'EXPLICIT_QA_OPT_IN_REQUIRED');
    assert.equal(obj.realModelCalls,0);
    assert.equal(obj.fallback,false);
  },
  'cli-arbitrary-command-refused':()=>{
    const env={...process.env,ALAZ_WSL2_READONLY_PROBE:'1'};
    const cp=spawnSync(process.execPath,[cli,'--read-only','--expected-uid=1000','--shell=cmd'],
      {encoding:'utf8',timeout:8000,env,windowsHide:true});
    assert.equal(cp.status,2);
    const obj=JSON.parse(cp.stdout.trim());
    assert.equal(obj.result,'REFUSED');
    assert.equal(obj.code,'INVALID_READONLY_PROBE_ARGUMENTS');
    assert.equal(obj.fallback,false);
  },
};

const wanted=process.argv[2];
if (wanted!=='all' && !Object.hasOwn(scenarios,wanted)) {
  process.stderr.write('UNKNOWN_WSL_BRIDGE_CASE\n');
  process.exitCode=2;
} else {
  const names=wanted==='all' ? Object.keys(scenarios) : [wanted];
  try {
    for (const name of names) await scenarios[name]();
    process.stdout.write(JSON.stringify({
      result:'PASS',suite:'PLAT-002A_READONLY_FIXED_GUEST',
      count:names.length,names,agentOrToolStarted:false,
      realModelCalls:0,guardedExecutionAccepted:false,
    })+'\n');
  } catch (error) {
    // No raw runtime payload, host paths, nonce or process stderr.
    process.stderr.write('PLAT002A_CASE_FAILED:'+(error?.code||error?.name||'Error')+'\n');
    process.exitCode=1;
  }
}
