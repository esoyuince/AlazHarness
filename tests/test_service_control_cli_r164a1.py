"""R164 real Node CLI -> private Unix server -> child pipes -> generic volume methods.

Mount worker, cgroup, loop/lease, native stores and process startTicks are
explicit fixture ports. This does not accept an installed service or kernel.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_service_control_cli_r163a1 import first_line

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('closed-lifecycle', 'lost-final-reply', 'deferred-close',
             'lost-stop-reply', 'autoclear-pending', 'stream-close-failure',
             'stale-after-closed')


@unittest.skipUnless(sys.platform == 'linux', 'Linux Unix sockets, SO_PEERCRED and process pipes')
class ServiceClosureCliIntegration(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if node is None:
            raise RuntimeError('Node required for cross-language closure source integration')
        env = {k: v for k, v in os.environ.items()
               if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        env['PYTHONIOENCODING'] = 'utf-8'
        with tempfile.TemporaryDirectory(prefix='az164-') as directory:
            server = subprocess.Popen([sys.executable, '-B',
                str(ROOT / 'tests/fixtures/service-control-server-r164a1.py'), directory, name],
                cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0)
            try:
                connection = first_line(server)
                self.assertEqual(connection['owner']['pid'], server.pid)
                run = subprocess.run([node, str(ROOT / 'tests/node/service-control-r164a1.mjs'), name],
                    input=json.dumps(connection).encode('ascii'), cwd=ROOT, env=env,
                    capture_output=True, timeout=30)
                self.assertEqual(run.returncode, 0,
                    (run.stdout + run.stderr).decode('utf-8', 'replace')[-9000:])
                report = json.loads(run.stdout)
                self.assertEqual((report['result'], report['scenario']), ('PASS', name))
                self.assertFalse(report['installedSupervisor'] or report['nativeRuntime']
                                 or report['kernelConfinementTested'])
                self.assertEqual(report['realProviderCalls'], 0)
                out, err = server.communicate(b'STOP FIXTURE\n', timeout=8)
                self.assertEqual((server.returncode, err), (0, b''),
                                 (out + err).decode('utf-8', 'replace')[-6000:])
                snapshot = json.loads(out)
                self.assertEqual(snapshot['result'], 'PASS')
                self.assertEqual(snapshot['spawnCount'], 1)
                self.assertEqual(snapshot['volumeStopCalls'], 1)
                self.assertEqual(snapshot['stopWrites'], 1)
                stop_lost = name == 'lost-stop-reply'
                self.assertEqual(snapshot['volumeFinishCalls'], 0 if stop_lost else 1)
                self.assertEqual(snapshot['loopCloses'], 0 if stop_lost else 1)
                self.assertEqual(snapshot['leaseCloses'],
                                 0 if name in ('lost-stop-reply', 'autoclear-pending') else 1)
                expected_stage = {'lost-stop-reply': 'STOPPING',
                                  'autoclear-pending': 'STOPPED'}.get(name, 'CLOSED')
                self.assertEqual(snapshot['volumeStage'], expected_stage)
                failed = name in ('lost-stop-reply', 'autoclear-pending', 'stream-close-failure')
                self.assertEqual(snapshot['volumeClosure']['state'], 'UNKNOWN' if failed else 'CLOSED')
                self.assertEqual(snapshot['volumeClosure']['imageLeaseReleased'], not failed)
                self.assertTrue(snapshot['originalVolumeRetained'])
                self.assertTrue(snapshot['originalPopenAndChannel'])
                self.assertEqual(snapshot['childReturnCode'], 0)
                self.assertTrue(snapshot['childExited'])
                self.assertFalse(snapshot['volumeMayClose'])
                self.assertEqual(snapshot['childCommandSequence'], 1)
                self.assertEqual(snapshot['lostFinalResponseInjected'], name == 'lost-final-reply')
                public = json.dumps({'node': report, 'server': snapshot})
                self.assertNotIn(connection['owner']['token'], public)
            finally:
                if server.poll() is None:
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
    setattr(ServiceClosureCliIntegration, 'test_' + scenario_name.replace('-', '_'), test)


if __name__ == '__main__':
    unittest.main()
