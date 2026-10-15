"""One unittest per actual Node/loopback contract scenario; no silent Node skips."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('hermes_wire_fixture', ROOT / 'tests/fixtures/hermes_wire.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)
SCENARIOS = ('success', 'duplicate', 'conflict', 'lost-ack', 'partial', 'budget', 'cancel', 'timeout',
             'unconfirmed', 'unknown', 'approval', 'resume', 'oversized', 'wrong-id', 'contradictory',
             'redirect', 'preaborted', 'bad-input', 'bad-endpoint', 'not-found', 'observer-failure',
             'terminal-freeze', 'cancel-idempotent', 'settlement-no-extension', 'disposed-no-revival', 'unsupported', 'unverified-terminal', 'reconcile-live',
             'resume-timeout-readonly', 'resume-abort-readonly')

class HybridWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which('node')
        if not cls.node:
            raise RuntimeError('Node 24 is required; hybrid tests cannot be skipped')
        v = subprocess.check_output([cls.node, '--version'], text=True).strip()
        if not v.startswith('v24.'):
            raise RuntimeError('The accepted hybrid toolchain is Node 24, found ' + v)
    def scenario(self, name):
        # Avoid passing ambient model credentials or personal agent-profile variables.
        env = {k: v for k, v in os.environ.items() if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LANG')}
        with FIXTURE.Fixture() as fixture:
            r = subprocess.run([self.node, str(ROOT / 'tests/node/wire-cases.mjs'), name, fixture.url, FIXTURE.TOKEN],
                               cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=15)
            self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-6000:])
            proof = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(proof['result'], 'PASS')
            with fixture.lock:
                rows = list(fixture.runs.values()); posts = [p for method, p in fixture.request_log if method == 'POST']
                if name in ('duplicate', 'conflict', 'lost-ack'):
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(posts.count('/v1/runs'), 2)
                if name in ('cancel', 'timeout', 'unconfirmed'):
                    self.assertEqual(rows[0]['stops'], 1)
                    if name != 'unconfirmed': self.assertGreaterEqual(rows[0]['stop_reads'], 2)
                if name in ('unknown', 'approval', 'resume', 'redirect', 'partial', 'budget'):
                    self.assertEqual(rows[0]['stops'], 0)
                    self.assertEqual(posts.count('/v1/runs'), 1)
                if name in ('preaborted', 'bad-input', 'bad-endpoint', 'terminal-freeze', 'cancel-idempotent', 'settlement-no-extension', 'disposed-no-revival', 'unsupported'):
                    self.assertEqual(fixture.request_log, [])
                if name in ('unverified-terminal','reconcile-live','resume-timeout-readonly','resume-abort-readonly'):
                    self.assertEqual(rows[0]['stops'],0);self.assertEqual(posts.count('/v1/runs'),1)
                    if name in ('unverified-terminal','reconcile-live'):
                        self.assertEqual(sum(method=='GET' for method,_ in fixture.request_log),1)
                self.assertEqual(fixture.foreign_hits, 0)

for scenario in SCENARIOS:
    def generated(self, name=scenario):
        self.scenario(name)
    generated.__name__ = 'test_' + scenario.replace('-', '_')
    setattr(HybridWireTests, generated.__name__, generated)

if __name__ == '__main__':
    unittest.main()
