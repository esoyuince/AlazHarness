// PLAT-001: side-effect-free cross-platform route planning; NEVER a sandbox launcher.
//
// Platform identity reported by Node is descriptive and NOT a security attestation.
// In particular, Windows/WSL2/macOS availability must never substitute for D3B
// native kernel/UID/IPC/model-budget proof or enable an unguarded fallback.
import os from 'node:os';

export const ROUTE_SCHEMA = 1;

export class PlatformRouteRejected extends Error {
  constructor(code) {
    super(code);
    this.name = 'PlatformRouteRejected';
    this.code = code;
  }
}

function requireShape(value, keys, code) {
  if (value === null || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).length !== keys.length ||
      Object.keys(value).some(k => !keys.includes(k)) ||
      keys.some(k => !Object.hasOwn(value, k))) {
    throw new PlatformRouteRejected(code);
  }
}

function safeString(value, pattern, code) {
  if (typeof value !== 'string' || !pattern.test(value)) {
    throw new PlatformRouteRejected(code);
  }
  return value;
}

// Pure input normalizer used for unit simulations. Never accept caller-supplied
// host data as proof to authorize the real execution of a process.
export function classifyHost(facts) {
  requireShape(facts, ['platform', 'arch', 'kernelRelease'], 'HOST_FACT_FIELDS');
  const platform = safeString(facts.platform, /^[a-z0-9_-]{1,32}$/, 'HOST_PLATFORM_INVALID');
  const arch = safeString(facts.arch, /^[a-z0-9_-]{1,32}$/, 'HOST_ARCH_INVALID');
  const release = safeString(facts.kernelRelease, /^[\x20-\x7e]{1,256}$/, 'HOST_KERNEL_RELEASE_INVALID');
  let environment = 'unsupported-host';
  if (platform === 'win32') environment = 'windows-host';
  if (platform === 'darwin') environment = 'macos-host';
  if (platform === 'linux') {
    if (/microsoft/i.test(release)) {
      environment = /wsl2/i.test(release) ? 'linux-wsl2-guest' : 'linux-wsl-unverified-guest';
    } else {
      environment = 'linux-host';
    }
  }
  const result = {
    schemaVersion: ROUTE_SCHEMA, platform, arch, environment,
    // This only says the existing x86_64 Linux adapter might be inspected.
    // It does not grant any capability to launch it.
    linuxX64Candidate: platform === 'linux' && arch === 'x64' &&
      environment !== 'linux-wsl-unverified-guest',
    kernelAttested: false, realHostUidIsolationAccepted: false,
  };
  return Object.freeze(result);
}

export function inspectCurrentHost() {
  return classifyHost({
    platform: process.platform,
    arch: process.arch,
    kernelRelease: os.release(),
  });
}

const COMMON_SECURITY = Object.freeze([
  'NATIVE_GUARD_AND_BROKER_ACCEPTANCE_REQUIRED',
  'PER_RUN_AUTHORITY_AND_BUDGET_REQUIRED',
  'NO_UNGUARDED_FALLBACK',
]);

function targetFor(host) {
  if (host.environment === 'linux-host') {
    return host.arch === 'x64'
      ? ['linux-x64-direct-candidate', ['FULL_D3B_NOT_ACCEPTED']]
      : ['linux-other-arch-pending', ['LINUX_ARCH_ADAPTER_NOT_VALIDATED']];
  }
  if (host.environment === 'linux-wsl2-guest') {
    return host.arch === 'x64'
      ? ['linux-x64-wsl2-guest-candidate', ['WSL2_GUEST_BOUNDARY_NOT_ACCEPTED', 'FULL_D3B_NOT_ACCEPTED']]
      : ['linux-wsl2-other-arch-pending', ['LINUX_ARCH_ADAPTER_NOT_VALIDATED', 'WSL2_GUEST_BOUNDARY_NOT_ACCEPTED']];
  }
  if (host.environment === 'linux-wsl-unverified-guest') {
    return ['wsl-version-unverified', ['WSL2_GUEST_VERSION_UNVERIFIED']];
  }
  if (host.environment === 'windows-host') {
    return host.arch === 'x64'
      ? ['windows-wsl2-bridge-pending', ['WSL2_GUEST_NOT_PROBED', 'HOST_TO_GUEST_BRIDGE_NOT_IMPLEMENTED']]
      : ['windows-arm64-wsl2-or-remote-pending', ['WSL2_GUEST_NOT_PROBED', 'LINUX_ARM64_GUARD_NOT_VALIDATED', 'HOST_TO_GUEST_BRIDGE_NOT_IMPLEMENTED']];
  }
  if (host.environment === 'macos-host') {
    return host.arch === 'arm64'
      ? ['macos-arm64-remote-linux-x64-or-future-vm-pending',
         ['REMOTE_LINUX_WORKER_NOT_IMPLEMENTED', 'LINUX_ARM64_GUARD_NOT_VALIDATED',
          'MACOS_VM_HOST_BRIDGE_NOT_IMPLEMENTED']]
      : ['macos-linux-vm-or-remote-pending',
         ['MACOS_VM_HOST_BRIDGE_NOT_IMPLEMENTED', 'REMOTE_LINUX_WORKER_NOT_IMPLEMENTED']];
  }
  return ['unsupported-host', ['HOST_PLATFORM_NOT_SUPPORTED']];
}

// Strict API: planner output can inform orchestration but is never a
// capability token, privilege elevation, executable command or security proof.
// Missing mode, extra options and model-provider claims all fail closed.
export function planExecution(request, host = inspectCurrentHost()) {
  requireShape(request, ['schemaVersion', 'mode'], 'ROUTE_REQUEST_FIELDS');
  if (request.schemaVersion !== ROUTE_SCHEMA || !Number.isInteger(request.schemaVersion)) {
    throw new PlatformRouteRejected('ROUTE_SCHEMA_MISMATCH');
  }
  if (request.mode !== 'scripted-mock' && request.mode !== 'guarded') {
    throw new PlatformRouteRejected('ROUTE_MODE_NOT_SUPPORTED');
  }
  requireShape(host, [
    'schemaVersion','platform','arch','environment','linuxX64Candidate',
    'kernelAttested','realHostUidIsolationAccepted',
  ], 'HOST_DESCRIPTOR_FIELDS');
  // Re-classify the two public OS dimensions conservatively. Even a manually
  // forged "kernelAttested" field must not make a guarded route available.
  if (host.schemaVersion !== ROUTE_SCHEMA ||
      typeof host.platform !== 'string' || typeof host.arch !== 'string' ||
      typeof host.environment !== 'string' ||
      typeof host.linuxX64Candidate !== 'boolean' ||
      typeof host.kernelAttested !== 'boolean' ||
      typeof host.realHostUidIsolationAccepted !== 'boolean') {
    throw new PlatformRouteRejected('HOST_DESCRIPTOR_INVALID');
  }
  let route, requirements;
  if (request.mode === 'scripted-mock') {
    route = 'local-scripted-component-fixture';
    requirements = ['NODE24_AND_PYTHON_SCRIPTED_FIXTURE_ONLY'];
  } else {
    [route, requirements] = targetFor(host);
    requirements = [...requirements, ...COMMON_SECURITY];
  }
  return Object.freeze({
    schemaVersion: ROUTE_SCHEMA,
    requestMode: request.mode,
    hostPlatform: host.platform,
    hostArchitecture: host.arch,
    hostEnvironment: host.environment,
    route,
    // The planner CANNOT start a process: even if the kernel meets the
    // x86_64 prerequisites, D3B and every host binding remain incomplete.
    readiness: request.mode === 'scripted-mock' ? 'fixture-plan-only' : 'guarded-not-accepted',
    processLaunchAuthorized: false,
    realModelCallAuthorized: false,
    modelBudgetUsdAuthorized: 0,
    noFallback: true,
    requirements: Object.freeze(requirements),
  });
}

export function requireGuardedLaunchApproved(_plan) {
  // Deliberately never executable in PLAT-001. A later trusted runtime
  // must verify kernel, native subprocess isolation, user identity, broker
  // budget authority and permission grants independently of this planner.
  throw new PlatformRouteRejected('GUARDED_ADAPTER_NOT_ACCEPTED');
}
