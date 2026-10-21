"""Fixed post-exec broker target. No root transition, provisioning or fallback."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
import principal_target as target
from credential_guard import unique_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--principal', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        # No asyncio event loop (and its internal sockets) exists before FD cleanup.
        config = target.prepare(unique_json(args.principal), args.config,
                                args.config_sha256, args.output)
        # Isolated Python omits the script directory; use only this trusted install.
        sys.path.insert(0, str(ROOT/'scripts'))
        from run_provider_broker import serve
        asyncio.run(serve(config, Path(args.output)))
    except Exception as exc:
        print(json.dumps({'result': 'REFUSED', 'phase': 'principal_broker_target',
                          'reasonType': type(exc).__name__, 'fallback': False}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
