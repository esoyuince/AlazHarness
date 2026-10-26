"""Fixed installed scripted-native qualification target; no arbitrary workload."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'native'),
               str(ROOT / 'dependencies')]
from gateway_retained_launch import finite_target_main


def main():
    try:
        if len(sys.argv) != 1:
            raise ValueError('unexpected arguments')
        result = finite_target_main()
        print(json.dumps(result, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False), flush=True)
        return 0
    except Exception as exc:
        # Do not cancel native tasks, force-close stores, release the lease or
        # turn unknown effects into a valid application-error completion.
        reason = str(exc)
        if re.fullmatch('[a-z][a-z_]{0,95}', reason) is None:
            reason = 'finite_target_rejected'
        attempt = getattr(sys.modules.get('gateway_finite_runtime'), '_attempt', None)
        phase = getattr(attempt, 'failed_stage', 'TRANSFER')
        if phase not in ('RESERVED', 'OWNER_START', 'CONSUMER_PREPARE',
                         'NATIVE_WORK', 'NATIVE_DRAIN', 'OWNER_CLOSE', 'TRANSFER'):
            phase = 'UNKNOWN'
        print(json.dumps({'state': 'PROJECTED_FINITE_REFUSED', 'type': type(exc).__name__,
                          'phase': phase, 'reason': reason}), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
