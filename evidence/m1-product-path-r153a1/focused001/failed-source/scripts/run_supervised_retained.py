"""Fixed trusted-supervisor child; no caller-selected program or workload."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
from gateway_supervised_launch import MAX_INPUT, child_main


def main():
    try:
        if len(sys.argv) != 1:
            raise ValueError('unexpected arguments')
        raw = sys.stdin.buffer.readline(MAX_INPUT + 2)
        if not raw.endswith(b'\n') or len(raw) > MAX_INPUT + 1:
            raise ValueError('invalid frame')
        # The private parent closes stdin after exactly one bounded frame.
        if sys.stdin.buffer.read(1):
            raise ValueError('unexpected trailing data')
        child_main(raw[:-1])
        raise RuntimeError('fixed launch returned')
    except Exception as exc:
        print(json.dumps({'state': 'SUPERVISED_RETAINED_REFUSED',
                          'type': type(exc).__name__}), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
