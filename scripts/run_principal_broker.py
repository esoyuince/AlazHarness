"""Explicit trusted-install broker launcher; never invoke through sudo fallback.

The isolated supervisor must already hold the authorized host identity. This
entrypoint is not SUID and does not provision users, permissions or namespaces.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import principal_launch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', required=True, type=Path)
    args = parser.parse_args()
    try:
        principal_launch.launch(principal_launch.load_contract(args.contract))
    except Exception as exc:
        print(json.dumps({'result': 'REFUSED', 'phase': 'principal_broker_launch',
                          'reasonType': type(exc).__name__, 'fallback': False,
                          'targetExecutionVerified': False}), file=sys.stderr)
        return 2
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
