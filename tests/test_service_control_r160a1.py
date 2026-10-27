"""Bounded Unix owner-channel and CLI fixtures; no installed/native service acceptance."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    'schema', 'identity', 'owner-precondition', 'ready', 'drain-ack', 'closed', 'command-completion', 'partial-close', 'framing',
    'response-bound', 'eof-required', 'lost-response', 'status-recovery', 'unknown',
    'invalid-input', 'socket-trust', 'abort-before', 'abort-after', 'sanitized-error',
    'cli-start', 'cli-close', 'cli-status', 'cli-config', 'cli-interrupted',
)


class ServiceControlTests(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node24 required')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        run = subprocess.run([node, str(ROOT / 'tests/node/service-control-r160a1.mjs'), name],
                             cwd=ROOT, env=env, capture_output=True, text=True,
                             encoding='utf-8', timeout=15)
        self.assertEqual(run.returncode, 0, (run.stdout + run.stderr)[-6000:])
        value = json.loads(run.stdout.strip().splitlines()[-1])
        self.assertEqual(value['result'], 'PASS')
        self.assertFalse(value['installedSupervisor'])
        self.assertFalse(value['nativeRuntime'])
        self.assertEqual(value['realProviderCalls'], 0)


for name in SCENARIOS:
    def run(self, case=name):
        self.scenario(case)
    if name != 'schema':
        run = unittest.skipUnless(sys.platform == 'linux',
            'Linux private Unix supervisor channel; schema validation is portable')(run)
    setattr(ServiceControlTests, 'test_' + name.replace('-', '_'), run)


if __name__ == '__main__':
    unittest.main()
