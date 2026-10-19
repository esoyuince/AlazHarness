// PLAT-001 real Node assert scenarios; simulated OS descriptions only.
// Neither scenarios nor the inspector start Gateway, Linux namespaces or models.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { classifyHost, inspectCurrentHost, planExecution,
         requireGuardedLaunchApproved, ROUTE_SCHEMA,
         PlatformRouteRejected } from '../../packages/hybrid-runtime/platform-routing.mjs';

const fixture = (platform, arch, kernelRelease = 'generic-6.6') =>
  classifyHost({ platform, arch, kernelRelease });
const plan = (host, mode = 'guarded') =>
  planExecution({ schemaVersion: ROUTE_SCHEMA, mode }, host);
const linux = () => fixture('linux', 'x64', '6.6.87.2-generic');
const wsl = () => fixture('linux', 'x64', '6.6.87.2-microsoft-standard-WSL2');
const denied = (action, code) => assert.throws(action,
  error => error instanceof PlatformRouteRejected && error.code === code);
const blocked = result => {
  assert.equal(result.processLaunchAuthorized, false);
  assert.equal(result.realModelCallAuthorized, false);
  assert.equal(result.modelBudgetUsdAuthorized, 0);
  assert.equal(result.noFallback, true);
  assert.equal(result.readiness, 'guarded-not-accepted');
  assert.ok(result.requirements.includes('NATIVE_GUARD_AND_BROKER_ACCEPTANCE_REQUIRED'));
  assert.ok(result.requirements.includes('NO_UNGUARDED_FALLBACK'));
};

const inspector = fileURLToPath(new URL('../../scripts/inspect_platform.mjs', import.meta.url));
function inspect(args) {
  const env = { ...process.env, ALAZ_MODEL_API_KEY: 'do-not-use-in-inspector' };
  const child = spawnSync(process.execPath, [inspector, ...args], {
    encoding: 'utf8', timeout: 8000, env, windowsHide: true,
  });
  assert.equal(child.error, undefined);
  assert.ok(child.stdout.trim());
  return { code: child.status, body: JSON.parse(child.stdout.trim()) };
}

const cases = {
  'linux-x64': () => {
    const host = linux(), result = plan(host);
    assert.equal(host.environment, 'linux-host');
    assert.equal(host.linuxX64Candidate, true);
    assert.equal(result.route, 'linux-x64-direct-candidate');
    assert.ok(result.requirements.includes('FULL_D3B_NOT_ACCEPTED'));
    blocked(result);
  },
  'linux-arm64': () => {
    const host = fixture('linux', 'arm64');
    assert.equal(host.linuxX64Candidate, false);
    const result = plan(host);
    assert.equal(result.route, 'linux-other-arch-pending');
    assert.ok(result.requirements.includes('LINUX_ARCH_ADAPTER_NOT_VALIDATED'));
    blocked(result);
  },
  'wsl2-guest': () => {
    const host = wsl();
    assert.equal(host.environment, 'linux-wsl2-guest');
    assert.equal(plan(host).route, 'linux-x64-wsl2-guest-candidate');
    assert.ok(plan(host).requirements.includes('WSL2_GUEST_BOUNDARY_NOT_ACCEPTED'));
    blocked(plan(host));
  },
  'wsl-version-unknown': () => {
    const host = fixture('linux', 'x64', '4.19.128-microsoft');
    assert.equal(host.environment, 'linux-wsl-unverified-guest');
    assert.equal(host.linuxX64Candidate, false);
    assert.equal(plan(host).route, 'wsl-version-unverified');
    blocked(plan(host));
  },
  'windows-x64': () => {
    const result = plan(fixture('win32', 'x64'));
    assert.equal(result.route, 'windows-wsl2-bridge-pending');
    assert.ok(result.requirements.includes('WSL2_GUEST_NOT_PROBED'));
    assert.ok(result.requirements.includes('HOST_TO_GUEST_BRIDGE_NOT_IMPLEMENTED'));
    blocked(result);
  },
  'windows-arm64': () => {
    const result = plan(fixture('win32', 'arm64'));
    assert.equal(result.route, 'windows-arm64-wsl2-or-remote-pending');
    assert.ok(result.requirements.includes('LINUX_ARM64_GUARD_NOT_VALIDATED'));
    blocked(result);
  },
  'macos-arm64': () => {
    const result = plan(fixture('darwin', 'arm64', '24.6.0'));
    assert.equal(result.route, 'macos-arm64-remote-linux-x64-or-future-vm-pending');
    assert.ok(result.requirements.includes('LINUX_ARM64_GUARD_NOT_VALIDATED'));
    assert.ok(result.requirements.includes('REMOTE_LINUX_WORKER_NOT_IMPLEMENTED'));
    blocked(result);
  },
  'macos-intel': () => {
    const result = plan(fixture('darwin', 'x64', '24.6.0'));
    assert.equal(result.route, 'macos-linux-vm-or-remote-pending');
    assert.ok(result.requirements.includes('MACOS_VM_HOST_BRIDGE_NOT_IMPLEMENTED'));
    blocked(result);
  },
  'unsupported-os': () => {
    const host = fixture('freebsd', 'x64');
    assert.equal(host.environment, 'unsupported-host');
    assert.equal(plan(host).route, 'unsupported-host');
    blocked(plan(host));
  },
  'bad-host-shapes': () => {
    for (const value of [null, {}, [], { platform: 'linux', arch: 'x64' },
      { platform: 'linux', arch: 'x64', kernelRelease: '1', approved: true }]) {
      denied(() => classifyHost(value), 'HOST_FACT_FIELDS');
    }
  },
  'untrusted-release': () => {
    for (const release of ['', '\nWSL2', 'v1\nv2', '\x00WSL2', 'a'.repeat(400)]) {
      denied(() => fixture('linux', 'x64', release), 'HOST_KERNEL_RELEASE_INVALID');
    }
  },
  'bad-platform-arch': () => {
    denied(() => fixture('LINUX', 'x64'), 'HOST_PLATFORM_INVALID');
    denied(() => fixture('linux', '../../root'), 'HOST_ARCH_INVALID');
    denied(() => fixture('linux', ''), 'HOST_ARCH_INVALID');
    denied(() => fixture('linux', 'x64\nmalicious'), 'HOST_ARCH_INVALID');
  },
  'missing-mode': () => {
    denied(() => planExecution({ schemaVersion: ROUTE_SCHEMA }, linux()), 'ROUTE_REQUEST_FIELDS');
    denied(() => planExecution({}, linux()), 'ROUTE_REQUEST_FIELDS');
  },
  'unsupported-mode': () => {
    for (const mode of ['direct','legacy','unconfined','paid',null,0]) {
      denied(() => planExecution({ schemaVersion: 1, mode }, linux()), 'ROUTE_MODE_NOT_SUPPORTED');
    }
  },
  'unknown-request-fields': () => {
    denied(() => planExecution({ schemaVersion: 1, mode: 'guarded',
      force: true }, linux()), 'ROUTE_REQUEST_FIELDS');
    denied(() => planExecution({ schemaVersion: 1, mode: 'guarded',
      skipSandbox: true }, linux()), 'ROUTE_REQUEST_FIELDS');
  },
  'strict-schema': () => {
    for (const schemaVersion of [0,2,'1',true]) {
      denied(() => planExecution({ schemaVersion, mode: 'guarded' }, linux()), 'ROUTE_SCHEMA_MISMATCH');
    }
  },
  'forged-guard-attestation': () => {
    const forged = { ...linux(), kernelAttested: true, realHostUidIsolationAccepted: true };
    blocked(plan(forged));
    denied(() => requireGuardedLaunchApproved(plan(forged)), 'GUARDED_ADAPTER_NOT_ACCEPTED');
  },
  'unknown-descriptor-fields': () => {
    denied(() => plan({ ...linux(), fullD3B: true }), 'HOST_DESCRIPTOR_FIELDS');
    denied(() => plan({ ...linux(), sysroot: '/' }), 'HOST_DESCRIPTOR_FIELDS');
  },
  'mock-only': () => {
    for (const host of [linux(), fixture('win32','x64'), fixture('darwin','arm64')]) {
      const result = plan(host, 'scripted-mock');
      assert.equal(result.route, 'local-scripted-component-fixture');
      assert.equal(result.readiness, 'fixture-plan-only');
      assert.equal(result.processLaunchAuthorized, false);
      assert.equal(result.realModelCallAuthorized, false);
      assert.equal(result.noFallback, true);
      assert.equal(result.modelBudgetUsdAuthorized, 0);
    }
  },
  'frozen-results': () => {
    const host = linux(), result = plan(host);
    assert.ok(Object.isFrozen(host));
    assert.ok(Object.isFrozen(result));
    assert.ok(Object.isFrozen(result.requirements));
    assert.equal(result.schemaVersion, ROUTE_SCHEMA);
  },
  'actual-host-inspector': () => {
    const host = inspectCurrentHost();
    assert.equal(host.platform, process.platform);
    assert.equal(host.arch, process.arch);
    assert.equal(host.kernelAttested, false);
    assert.equal(host.realHostUidIsolationAccepted, false);
    blocked(plan(host));
  },
  'cli-mock': () => {
    const { code, body } = inspect([]);
    assert.equal(code, 0);
    assert.equal(body.result, 'SCRIPTED_FIXTURE_PLAN');
    assert.equal(body.observedHost.platform, process.platform);
    assert.equal(body.processStarted, false);
    assert.equal(body.executionPlan.processLaunchAuthorized, false);
    assert.equal(body.readOnlyInspector, true);
    assert.equal(JSON.stringify(body).includes('do-not-use-in-inspector'), false);
  },
  'cli-guarded': () => {
    const { code, body } = inspect(['--mode=guarded']);
    assert.equal(code, 0);
    assert.equal(body.result, 'NOT_ACCEPTED');
    blocked(body.executionPlan);
  },
  'cli-require-accepted': () => {
    const { code, body } = inspect(['--mode=guarded', '--require-accepted']);
    assert.equal(code, 2);
    assert.equal(body.result, 'REFUSED');
    assert.equal(body.code, 'GUARDED_ADAPTER_NOT_ACCEPTED');
    assert.equal(body.processStarted, false);
    assert.equal(body.fallback, false);
  },
  'cli-os-spoof-refused': () => {
    for (const arg of ['--platform=linux','--arch=x64','--kernel=WSL2','--force','--mode=direct']) {
      const { code, body } = inspect([arg]);
      assert.equal(code, 2);
      assert.equal(body.result, 'REFUSED');
      assert.equal(body.code, 'INVALID_CLI_ARGUMENTS');
      assert.equal(body.fallback, false);
    }
  },
  'cli-duplicate-refused': () => {
    const { code, body } = inspect(['--require-accepted','--require-accepted']);
    assert.equal(code, 2);
    assert.equal(body.code, 'INVALID_CLI_ARGUMENTS');
  },
  'no-release-or-env-leak': () => {
    const key = 'untrusted-secret-not-for-output';
    const host = fixture('linux','x64',key);
    const result = plan(host);
    assert.equal(JSON.stringify(host).includes(key), false);
    assert.equal(JSON.stringify(result).includes(key), false);
  },
};

const requested = process.argv[2];
if (!Object.hasOwn(cases, requested) && requested !== 'all') {
  process.stderr.write('UNKNOWN_PLATFORM_CASE\n');
  process.exitCode = 2;
} else {
  try {
    const names = requested === 'all' ? Object.keys(cases) : [requested];
    for (const name of names) cases[name]();
    process.stdout.write(JSON.stringify({
      result: 'PASS', suite: 'PLAT-001_NO_LAUNCH',
      cases: names.length, scenarios: names,
      realModelCalls: 0, privilegedActions: 0, secureAdapterAccepted: false,
    }) + '\n');
  } catch (error) {
    process.stderr.write('PLAT_001_ASSERTION_FAILED:' + (error?.code || error?.name || 'Unknown') + '\n');
    process.exitCode = 1;
  }
}
