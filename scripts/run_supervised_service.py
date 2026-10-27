"""Fixed service bootstrap; preserve stdin for the post-exec control stream."""
from pathlib import Path
import os
import select
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
from gateway_supervised_service import MAX_BOOTSTRAP, child_main


def read_frame():
    # Reading one byte at a time prevents buffered read-ahead from stealing the
    # first R160 command. Newline, not EOF, completes the bootstrap.
    raw = bytearray()
    deadline = time.monotonic() + 30
    while len(raw) <= MAX_BOOTSTRAP:
        left = deadline - time.monotonic()
        if left <= 0 or not select.select([0], [], [], left)[0]:
            raise ValueError('service bootstrap deadline')
        byte = os.read(0, 1)
        if byte == b'\n':
            if not raw:
                raise ValueError('empty service bootstrap')
            return bytes(raw)
        if not byte:
            raise ValueError('incomplete service bootstrap')
        raw.extend(byte)
    raise ValueError('service bootstrap bound')


def main():
    try:
        if len(sys.argv) != 1:
            raise ValueError('unexpected arguments')
        child_main(read_frame())
        raise RuntimeError('fixed service launch returned')
    except BaseException:
        try:
            sys.stderr.write('{"state":"SUPERVISED_SERVICE_REFUSED"}\n')
            sys.stderr.flush()
        except BaseException:
            pass
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
