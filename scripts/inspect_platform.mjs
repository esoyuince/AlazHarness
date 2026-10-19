// Read-only PLAT-001 inspector. Does not launch WSL, VM, Gateway or provider.
import { inspectCurrentHost, planExecution, requireGuardedLaunchApproved,
         PlatformRouteRejected, ROUTE_SCHEMA } from '../packages/hybrid-runtime/platform-routing.mjs';

function main(args) {
  let mode = 'scripted-mock';
  let requireAccepted = false;
  if (args.length > 2) throw new PlatformRouteRejected('INVALID_CLI_ARGUMENTS');
  for (const arg of args) {
    if (arg === '--mode=scripted-mock' || arg === '--mode=guarded') {
      mode = arg.slice('--mode='.length);
    } else if (arg === '--require-accepted') {
      if (requireAccepted) throw new PlatformRouteRejected('INVALID_CLI_ARGUMENTS');
      requireAccepted = true;
    } else {
      // No --os, --arch, --release or arbitrary command/hostname overrides.
      throw new PlatformRouteRejected('INVALID_CLI_ARGUMENTS');
    }
  }
  const host = inspectCurrentHost();
  const plan = planExecution({ schemaVersion: ROUTE_SCHEMA, mode }, host);
  if (requireAccepted && mode === 'guarded') {
    requireGuardedLaunchApproved(plan);
  }
  process.stdout.write(JSON.stringify({
    result: mode === 'guarded' ? 'NOT_ACCEPTED' : 'SCRIPTED_FIXTURE_PLAN',
    observedHost: host,
    executionPlan: plan,
    readOnlyInspector: true,
    processStarted: false,
  }) + '\n');
}

try {
  main(process.argv.slice(2));
} catch (error) {
  const code = error instanceof PlatformRouteRejected ? error.code : 'PLATFORM_INSPECTION_FAILED';
  process.stdout.write(JSON.stringify({
    result: 'REFUSED', code, processStarted: false, fallback: false,
  }) + '\n');
  process.exitCode = 2;
}
