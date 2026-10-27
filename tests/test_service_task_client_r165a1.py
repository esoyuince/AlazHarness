"""Real Node/Unix task transport fixtures; no installed/native/model acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    'fetch-seam', 'workflow', 'lost-dispatch', 'lost-stop', 'native-rejection',
    'route-header-guards', 'input-bounds', 'response-bounds', 'response-schema',
    'framing', 'eof-required', 'stale-owner', 'socket-trust', 'abort-before',
    'abort-after', 'timeout', 'sanitized-errors', 'redirect', 'cli-task',
    'cli-lost-dispatch', 'cli-cancel', 'configuration',
)


class ServiceTaskClientTests(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node 24 required')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        run = subprocess.run([node, str(ROOT / 'tests/node/service-task-r165a1.mjs'), name],
                             cwd=ROOT, env=env, capture_output=True, text=True,
                             encoding='utf-8', timeout=20)
        self.assertEqual(run.returncode, 0, (run.stdout + run.stderr)[-6000:])
        value = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(value['result'], 'PASS')
        self.assertEqual(value['hostTcpCalls'], 0)
        self.assertFalse(value['installedSupervisor'])
        self.assertFalse(value['nativeRuntime'])
        self.assertEqual(value['realProviderCalls'], 0)


for name in SCENARIOS:
    def run(self, case=name):
        self.scenario(case)
    if name != 'fetch-seam':
        run = unittest.skipUnless(sys.platform == 'linux', 'Linux private Unix task transport')(run)
    setattr(ServiceTaskClientTests, 'test_' + name.replace('-', '_'), run)


if __name__ == '__main__':
    unittest.main()
