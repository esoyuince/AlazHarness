// PLAT-002A: bounded Windows -> WSL2 read-only identity probe.
//
// This deliberately is NOT an agent/tool execution adapter or trusted
// D3B sandbox. It never accepts a command, executable, model or guest
// path from an agent request. WSL's access to Windows host files remains
// a separate unaccepted host/guest security boundary.
import { createHash, randomBytes } from 'node:crypto';
import { readFileSync, lstatSync } from 'node:fs';
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FIELDS = Object.freeze([
  'version', 'type', 'requestId', 'nonce', 'result', 'observed',
  'sourceSha256', 'secureLaunchAuthorized', 'hostFilesystemIsolated',
  'realModelCalls', 'agentOrToolStarted', 'independentHostUidVerified',
]);
const OBSERVED_FIELDS = Object.freeze([
  'platform','arch','environment','uid','euid','gid','pid',
  'userNamespaceVisible','mountNamespaceVisible','kernelReleaseSha256',
  'noNewPrivs','seccomp',
]);
const SHA = /^[0-9a-f]{64}$/;
const NONCE = /^[0-9a-f]{64}$/;
const REQUEST_ID = /^[0-9a-f]{32}$/;
const MAX_STDOUT = 8192;
const DEFAULT_TIMEOUT = 15000;

export class WslBridgeRejected extends Error {
  constructor(code) {
    super(code);
    this.name = 'WslBridgeRejected';
    this.code = code;
  }
}
function need(condition, code) {
  if (!condition) throw new WslBridgeRejected(code);
}
function exact(value, fields, code) {
  need(value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).length === fields.length
    && fields.every(k => Object.hasOwn(value,k))
    && Object.keys(value).every(k => fields.includes(k)),code);
}
function digest(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}
const GUEST_FILE = fileURLToPath(
  new URL('../../scripts/qa/wsl2_bridge_guest_probe.py', import.meta.url));

export function windowsPathToFixedWslMount(winPath) {
  // Mapping is for THIS source file only. No arbitrary shared paths,
  // UNC, device paths, relative paths, shell or user-supplied mounts.
  need(typeof winPath === 'string' && winPath.length < 3000,
    'HOST_PATH_INVALID');
  need(/^[A-Za-z]:\\[^:*?"<>|]+$/.test(winPath)
       && !winPath.startsWith('\\\\'), 'HOST_PATH_NOT_ORDINARY_DRIVE');
  const parts=winPath.slice(3).split('\\');
  need(parts.length > 2 && parts.every(p => p.length > 0
    && p !== '.' && p !== '..' && !p.endsWith(' ') && !p.endsWith('.')),
    'HOST_PATH_UNSAFE_COMPONENT');
  const drive=winPath[0].toLowerCase();
  return '/mnt/' + drive + '/' + parts.map(encodeURIComponent)
    .join('/').replace(/%20/g,' ');
}

export function validateGuestReport(reply, expected) {
  exact(expected, ['nonce','requestId','sourceSha256','expectedUid'],
    'BRIDGE_EXPECTATION_INVALID');
  need(NONCE.test(expected.nonce) && REQUEST_ID.test(expected.requestId)
    && SHA.test(expected.sourceSha256)
    && Number.isSafeInteger(expected.expectedUid)
    && expected.expectedUid > 0, 'BRIDGE_EXPECTATION_INVALID');
  exact(reply, FIELDS, 'BRIDGE_RESPONSE_FIELDS');
  need(reply.version === 1 && typeof reply.version === 'number'
    && reply.type === 'alaz.wsl2.identity.v1'
    && reply.result === 'GUEST_SELF_REPORTED_READ_ONLY',
    'BRIDGE_RESPONSE_VERSION');
  need(reply.nonce === expected.nonce && reply.requestId === expected.requestId,
    'BRIDGE_NONCE_OR_REQUEST_MISMATCH');
  need(reply.sourceSha256 === expected.sourceSha256,
    'BRIDGE_GUEST_SOURCE_MISMATCH');
  exact(reply.observed, OBSERVED_FIELDS, 'BRIDGE_GUEST_IDENTITY_FIELDS');
  const g=reply.observed;
  need(g.platform === 'linux' && g.arch === 'x64'
    && g.environment === 'linux-wsl2-guest',
    'BRIDGE_GUEST_PLATFORM_MISMATCH');
  need(Number.isSafeInteger(g.uid) && g.uid === expected.expectedUid
    && g.euid === g.uid && Number.isSafeInteger(g.gid)
    && g.gid >= 0 && Number.isSafeInteger(g.pid) && g.pid > 0
    && g.userNamespaceVisible === true && g.mountNamespaceVisible === true
    && typeof g.kernelReleaseSha256 === 'string'
    && SHA.test(g.kernelReleaseSha256)
    && ['0','1'].includes(g.noNewPrivs)
    && ['0','1','2'].includes(g.seccomp), 'BRIDGE_GUEST_IDENTITY_UNPROVEN');
  need(reply.secureLaunchAuthorized === false
    && reply.hostFilesystemIsolated === false
    && reply.independentHostUidVerified === false
    && reply.realModelCalls === 0
    && reply.agentOrToolStarted === false,
    'BRIDGE_GUARD_WIDENING_REFUSED');
  return Object.freeze({
    result: 'PASS_READ_ONLY_GUEST_SELF_REPORT',
    scope: 'test_owned_unprivileged_identity_only',
    guestPlatform: g.platform,
    guestArch: g.arch,
    guestEnvironment: g.environment,
    guestUid: g.uid,
    guestGid: g.gid,
    observedGuestPid: g.pid,
    guestUserNamespaceVisible: true,
    guestMountNamespaceVisible: true,
    guestNoNewPrivs: g.noNewPrivs,
    guestSeccomp: g.seccomp,
    requestIdMatched: true,
    nonceMatched: true,
    sourceSha256Matched: true,
    guestIdentitySelfReported: true,
    independentHostUidVerified: false,
    secureExecutionAccepted: false,
    hostFilesystemIsolated: false,
    agentOrToolStarted: false,
    realModelCalls: 0,
    automaticRetry: false,
  });
}

export function fixedProbePlan() {
  need(process.platform === 'win32' && process.arch === 'x64',
    'WINDOWS_X64_HOST_REQUIRED');
  const systemRoot=process.env.SystemRoot || '';
  need(/^[A-Za-z]:\\Windows$/i.test(systemRoot),
    'TRUSTED_WINDOWS_SYSTEM_ROOT_REQUIRED');
  const executable=path.win32.join(systemRoot,'System32','wsl.exe');
  const binary=lstatSync(executable);
  need(binary.isFile() && !binary.isSymbolicLink(),
    'WINDOWS_WSL_BINARY_NOT_FIXED');
  const source=lstatSync(GUEST_FILE);
  need(source.isFile() && !source.isSymbolicLink(),
    'BRIDGE_GUEST_SCRIPT_MUST_BE_REGULAR');
  const guestPath=windowsPathToFixedWslMount(GUEST_FILE);
  return Object.freeze({
    executable,
    args: Object.freeze(['--distribution','Ubuntu','--exec','python3',
      '-I','-B',guestPath]),
    guestSourceSha256: digest(readFileSync(GUEST_FILE)),
    expectedKind: 'single_read_only_guest_identity',
    shell: false,
    automaticRetry: false,
    secureExecutionAccepted: false,
    hostFilesystemIsolated: false,
  });
}

export async function probeFixedWindowsWsl2({expectedUid,signal,timeoutMs=DEFAULT_TIMEOUT}={}) {
  // One explicit QA-only operation. No request arguments contain shell
  // fragments, paths, executable overrides, route or tool instructions.
  need(Number.isSafeInteger(expectedUid) && expectedUid > 0,
       'EXPECTED_UNPRIVILEGED_GUEST_UID_REQUIRED');
  need(Number.isInteger(timeoutMs) && timeoutMs >= 1000 && timeoutMs <= 20000,
       'BRIDGE_TIMEOUT_INVALID');
  need(!signal || (typeof signal.aborted === 'boolean'
    && typeof signal.addEventListener === 'function'
    && typeof signal.removeEventListener === 'function'),
       'BRIDGE_ABORT_SIGNAL_INVALID');
  need(!signal?.aborted,'BRIDGE_ABORTED_BEFORE_START');
  const plan=fixedProbePlan();
  const expected={
    nonce: randomBytes(32).toString('hex'),
    requestId: randomBytes(16).toString('hex'),
    sourceSha256:plan.guestSourceSha256,
    expectedUid,
  };
  const frame=JSON.stringify({
    version:1,operation:'identify',
    nonce:expected.nonce,requestId:expected.requestId,
  })+'\n';
  need(Buffer.byteLength(frame)<=1024,'BRIDGE_REQUEST_TOO_LARGE');
  return new Promise((resolve,reject)=>{
    let child,settled=false,output='',truncated=false;
    let deadline,aborted=false;
    const onAbort=()=>{
      aborted=true;
      try { child?.kill(); } catch (_) {}
    };
    const finish=(error,result)=>{
      if (settled) return;
      settled=true;
      if (deadline) clearTimeout(deadline);
      signal?.removeEventListener('abort',onAbort);
      if (error) reject(error);
      else resolve(result);
    };
    try {
      const cleanEnv={SystemRoot:process.env.SystemRoot,
        WINDIR:process.env.WINDIR,
        PATH:path.win32.join(process.env.SystemRoot,'System32')};
      // Never trust PATH lookup, use cmd.exe, a shell, or arbitrary
      // binaries/scripts. Executable and one script are fixed.
      child=spawn(plan.executable,plan.args,{
        shell:false,windowsHide:true,stdio:['pipe','pipe','pipe'],
        env:cleanEnv,
      });
      deadline=setTimeout(()=>{
        aborted=true;
        try { child.kill(); } catch (_) {}
        finish(new WslBridgeRejected('GUEST_PROCESS_OUTCOME_UNKNOWN_TIMEOUT'));
      },timeoutMs);
      child.stdout.on('data',data=>{
        if (settled) return;
        output+=data.toString('utf8');
        if (Buffer.byteLength(output,'utf8')>MAX_STDOUT) {
          truncated=true;
          onAbort();
          finish(new WslBridgeRejected('GUEST_OUTPUT_LIMIT'));
        }
      });
      // Guest stderr is intentionally not exposed to avoid path/secret leaks.
      child.stderr.on('data',()=>{});
      child.stdin.on('error',()=>{});
      child.on('error',()=>{
        finish(new WslBridgeRejected('WSL_EXECUTION_UNAVAILABLE'));
      });
      child.on('close',(code,signalName)=>{
        if (settled) return;
        if (aborted || truncated || signalName) {
          finish(new WslBridgeRejected('GUEST_PROCESS_OUTCOME_UNKNOWN'));
          return;
        }
        if (code!==0) {
          finish(new WslBridgeRejected('GUEST_REFUSED_OR_EXIT_NONZERO'));
          return;
        }
        try {
          need(output.endsWith('\n') && output.split('\n').length===2,
               'BRIDGE_RESPONSE_FRAME_INVALID');
          const data=JSON.parse(output);
          const response=validateGuestReport(data,expected);
          finish(null,Object.freeze({
            ...response,
            transport:'fixed_wsl2_python_stdio',
            hostPlatform:'win32',
            hostArchitecture:'x64',
            childExitCode:0,
            childCloseObserved:true,
            fallback:false,
          }));
        } catch (_error) {
          finish(new WslBridgeRejected('BRIDGE_REPLY_VERIFICATION_FAILED'));
        }
      });
      signal?.addEventListener('abort',onAbort,{once:true});
      if (signal?.aborted) {
        onAbort();
      } else {
        child.stdin.end(frame,'utf8');
      }
    } catch (_) {
      // No orphaned owned WSL wrapper if even the probe setup fails.
      try { child?.kill(); } catch (_) {}
      finish(new WslBridgeRejected('BRIDGE_START_REFUSED'));
    }
  });
}
