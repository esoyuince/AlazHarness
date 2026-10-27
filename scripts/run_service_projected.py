"""Fixed installed service receiver; stdout belongs only to control frames."""
from pathlib import Path
import json
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'native'),
               str(ROOT / 'dependencies')]
from gateway_service_launch import target_main


def main():
    try:
        if len(sys.argv) != 1:
            raise ValueError('service_projected_extra_arguments')
        result = target_main()
        from gateway_service_control import validate_frame
        result = validate_frame(result)
        if result['type'] != 'final' or result['owner']['pid'] != os.getpid():
            raise ValueError('service_projected_final_unconfirmed')
        # The original control driver already wrote final to FD 1. Emitting it
        # again would corrupt that stream; successful return means exit 0 only.
        return 0
    except Exception as exc:
        # No retry, cleanup, cancellation or stdout fallback. A factory with
        # unresolved native effects retains its original attempt and event loop.
        reason = str(exc)
        if re.fullmatch('[a-z][a-z0-9_]{0,95}', reason) is None:
            reason = 'service_projected_target_rejected'
        kind = type(exc).__name__
        if re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,95}', kind) is None:
            kind = 'RuntimeError'
        print(json.dumps({'state': 'PROJECTED_SERVICE_REFUSED', 'type': kind,
                          'reason': reason}, sort_keys=True, separators=(',', ':')),
              file=sys.stderr, flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
