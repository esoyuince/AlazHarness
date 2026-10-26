"""Portable local-control HTTP/CLI contract fixtures; no native runtime/model acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    'task', 'boundaries', 'lost-ack', 'request-states', 'request-malformed', 'watch', 'watch-timeout',
    'watch-interrupted', 'cancel-ack', 'cancel-timeout', 'cancel-lost-ack', 'cancel-malformed-ack',
    'cancel-unknown', 'cancel-race', 'cancel-invalid', 'result', 'failed-result',
    'unverified-result', 'contradiction', 'status-unknown', 'usage', 'usage-incomplete',
    'cli-task', 'cli-file', 'cli-input-errors', 'cli-lost-ack', 'cli-request',
    'cli-unsupported', 'cli-arguments', 'cli-watch-interrupted', 'errors-sanitized',
)


class LocalControlTests(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node24 required')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        run = subprocess.run(
            [node, str(ROOT / 'tests/node/local-control-cases.mjs'), name], cwd=ROOT,
            env=env, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(run.returncode, 0, (run.stdout + run.stderr)[-6000:])
        value = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(value['result'], 'PASS')
        self.assertEqual(value['rawStartCalls'], 0)
        self.assertEqual(value['realProviderCalls'], 0)


for name in SCENARIOS:
    def run(self, case=name):
        self.scenario(case)
    if name == 'cli-watch-interrupted':
        run = unittest.skipIf(os.name == 'nt', 'POSIX SIGINT delivery; AbortSignal cancellation is tested portably')(run)
    setattr(LocalControlTests, 'test_' + name.replace('-', '_'), run)


if __name__ == '__main__':
    unittest.main()
