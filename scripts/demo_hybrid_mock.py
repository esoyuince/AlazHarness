#!/usr/bin/env python3
"""Run only the labelled local wire fixture; cannot target a real agent endpoint."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node 24 is required')
    spec = importlib.util.spec_from_file_location('demo_wire', ROOT / 'tests/fixtures/hermes_wire.py')
    fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
    env = {k: v for k, v in os.environ.items() if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LANG')}
    with fixture.Fixture() as server:
        process = subprocess.run([node, str(ROOT / 'tests/node/wire-cases.mjs'), 'success', server.url, fixture.TOKEN],
                                 cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=15)
        if process.returncode:
            print(process.stderr); return process.returncode
        result = json.loads(process.stdout.strip().splitlines()[-1])
        result.update(real_model_calls=0, full_hermes_engine=False, autonomy=False,
                      endpoint='ephemeral_loopback_fixture')
        print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
