"""Explicit native queued-cancellation reports across the portable HTTP client."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('valid', 'null-alone', 'identity', 'shape', 'authority',
             'contradictions', 'http-valid', 'http-lost-ack', 'http-malformed')


class QueuedCancellationControlTests(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node24 required')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        result = subprocess.run([node, str(ROOT / 'tests/node/queued-cancel-control-r159a1.mjs'), name],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-6000:])
        value = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(value['result'], 'PASS')
        self.assertEqual(value['realProviderCalls'], 0)
        self.assertIs(value['nativeWorkerStarted'], False)


for scenario in SCENARIOS:
    def run(self, name=scenario):
        self.scenario(name)
    setattr(QueuedCancellationControlTests, 'test_' + scenario.replace('-', '_'), run)


if __name__ == '__main__':
    unittest.main()
