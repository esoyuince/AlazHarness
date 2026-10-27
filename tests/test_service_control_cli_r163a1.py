"""Real Node CLI/client -> Python Unix server -> original child pipes.

The server fixture uses the exact production ServiceVolumeSupervisor and
ServiceChannel. Kernel, mount, image lease and native runtime ports are doubled;
the child emits synthetic native owner receipts. This is source integration,
not installed service/kernel/model acceptance. Only fixture children are killed
on a test failure or teardown; no product cleanup authority is exercised.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('lifecycle', 'lost-start', 'lost-close', 'stale-owner',
             'id-conflict', 'trailing-frame', 'pending-start')


def first_line(process, seconds=10):
    deadline = time.monotonic() + seconds
    data = bytearray()
    while len(data) < 16384:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
            raise AssertionError('fixture server descriptor deadline')
        chunk = os.read(process.stdout.fileno(), 1)
        if not chunk:
            raise AssertionError('fixture server exited before descriptor: '
                                 + process.stderr.read(8192).decode('utf-8', 'replace'))
        data.extend(chunk)
        if chunk == b'\n':
            return json.loads(data)
    raise AssertionError('fixture descriptor bound')


@unittest.skipUnless(sys.platform == 'linux', 'Linux Unix sockets, SO_PEERCRED and process identity')
class ServiceControlCliIntegration(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if node is None:
            raise RuntimeError('Node required for the real cross-language source integration')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        env['PYTHONIOENCODING'] = 'utf-8'
        with tempfile.TemporaryDirectory(prefix='az163-') as directory:
            server = subprocess.Popen([sys.executable, '-B',
                str(ROOT / 'tests/fixtures/service-control-server-r163a1.py'),
                directory, name], cwd=ROOT, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=0)
            try:
                connection = first_line(server)
                self.assertEqual(connection['owner']['pid'], server.pid)
                run = subprocess.run([node, str(ROOT / 'tests/node/service-control-r163a1.mjs'), name],
                    input=json.dumps(connection).encode('ascii'), cwd=ROOT, env=env,
                    capture_output=True, timeout=30)
                self.assertEqual(run.returncode, 0,
                    (run.stdout + run.stderr).decode('utf-8', 'replace')[-9000:])
                report = json.loads(run.stdout)
                self.assertEqual(report['result'], 'PASS')
                self.assertEqual(report['scenario'], name)
                self.assertFalse(report['installedSupervisor'] or report['nativeRuntime']
                                 or report['kernelConfinementTested'])
                self.assertEqual(report['realProviderCalls'], 0)
                out, err = server.communicate(b'STOP FIXTURE\n', timeout=8)
                self.assertEqual((server.returncode, err), (0, b''),
                                 (out + err).decode('utf-8', 'replace')[-6000:])
                snapshot = json.loads(out)
                self.assertEqual(snapshot['result'], 'PASS')
                expected = 0 if name in ('stale-owner', 'trailing-frame') else 1
                self.assertEqual(snapshot['spawnCount'], expected)
                self.assertEqual(snapshot['volumeStopCalls'], 0)
                self.assertEqual(snapshot['volumeFinishCalls'], 0)
                self.assertEqual(snapshot['volumeStage'], 'RUNNING')
                self.assertTrue(snapshot['originalVolumeRetained'])
                if expected:
                    self.assertTrue(snapshot['originalPopenAndChannel'])
                    self.assertEqual(snapshot['childReturnCode'], 0)
                    self.assertTrue(snapshot['childExited'])
                    self.assertFalse(snapshot['volumeMayClose'])
                    self.assertEqual(snapshot['childCommandSequence'], 1)
                public = json.dumps({'node': report, 'server': snapshot})
                self.assertNotIn(connection['owner']['token'], public)
            finally:
                if server.poll() is None:
                    # Cooperative fixture exit first so its owned synthetic child
                    # is reaped even if an assertion failed. This is not a product
                    # close/unmount/lease path.
                    try:
                        server.communicate(b'STOP FIXTURE\n', timeout=8)
                    except (OSError, ValueError, subprocess.TimeoutExpired):
                        server.kill()
                        server.communicate(timeout=3)
                for stream in (server.stdin, server.stdout, server.stderr):
                    if stream is not None and not stream.closed:
                        stream.close()


for scenario_name in SCENARIOS:
    def test(self, name=scenario_name):
        self.scenario(name)
    setattr(ServiceControlCliIntegration, 'test_' + scenario_name.replace('-', '_'), test)


if __name__ == '__main__':
    unittest.main()
