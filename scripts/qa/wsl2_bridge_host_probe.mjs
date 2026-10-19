// Explicit read-only QA. NOT the AlazHarness production tool launcher.
import { probeFixedWindowsWsl2, WslBridgeRejected } from
  '../../packages/hybrid-runtime/wsl2-readonly-bridge.mjs';

function parse(args) {
  if (args.length !== 2 || args[0] !== '--read-only' ||
      !/^--expected-uid=[1-9][0-9]{0,9}$/.test(args[1])) {
    throw new WslBridgeRejected('INVALID_READONLY_PROBE_ARGUMENTS');
  }
  const expectedUid=Number(args[1].slice('--expected-uid='.length));
  if (!Number.isSafeInteger(expectedUid) || expectedUid > 2147483646) {
    throw new WslBridgeRejected('INVALID_READONLY_PROBE_UID');
  }
  return expectedUid;
}

try {
  const expectedUid=parse(process.argv.slice(2));
  if (process.env.ALAZ_WSL2_READONLY_PROBE !== '1') {
    throw new WslBridgeRejected('EXPLICIT_QA_OPT_IN_REQUIRED');
  }
  const result=await probeFixedWindowsWsl2({expectedUid,timeoutMs:15000});
  process.stdout.write(JSON.stringify(result)+'\n');
} catch (error) {
  const reason=error instanceof WslBridgeRejected ? error.code : 'BRIDGE_QA_REFUSED';
  process.stdout.write(JSON.stringify({
    result:'REFUSED',code:reason,
    autoRetry:false,processLaunchAuthorized:false,
    realModelCalls:0,fallback:false,
  })+'\n');
  process.exitCode=2;
}
