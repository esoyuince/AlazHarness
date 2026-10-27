"""R165 complete source transport integration, with actual Node, pipes and HTTP.

Production Unix server, supervisor/channel, child ServiceControl and HTTP relay
are composed. Native API/lifecycle/store and kernel/worker/lease methods remain
explicit fixture doubles. This does not qualify an installed service or model.
"""
from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_service_control_cli_r163a1 import first_line

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('task-lifecycle', 'wrong-bearer', 'lost-dispatch-reply')


@unittest.skipUnless(sys.platform == 'linux', 'Linux private Unix sockets and real child pipes')
@unittest.skipUnless(importlib.util.find_spec('aiohttp') is not None,
                     'aiohttp unavailable; cross-layer real HTTP fixture not run')
class ServiceTaskIntegration(unittest.TestCase):
    def scenario(self, name):
        node = shutil.which('node')
        if node is None:
            raise RuntimeError('Node required for cross-language task transport integration')
        env = {key: value for key, value in os.environ.items()
               if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')}
        env['PYTHONIOENCODING'] = 'utf-8'
        with tempfile.TemporaryDirectory(prefix='az165-') as directory:
            server = subprocess.Popen([sys.executable, '-B',
                str(ROOT / 'tests/fixtures/service-task-server-r165a1.py'), directory, name],
                cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, bufsize=0)
            try:
                connection = first_line(server)
                self.assertEqual(connection['owner']['pid'], server.pid)
                run = subprocess.run([node, str(ROOT / 'tests/node/service-task-integration-r165a1.mjs'), name],
                    input=json.dumps(connection).encode('ascii'), cwd=ROOT, env=env,
                    capture_output=True, timeout=40)
                self.assertEqual(run.returncode, 0,
                    (run.stdout + run.stderr).decode('utf-8', 'replace')[-9000:])
                report = json.loads(run.stdout)
                self.assertEqual((report['result'], report['scenario']), ('PASS', name))
                self.assertEqual(report['hostTcpCalls'], 0)
                self.assertEqual(report['serviceStateAfterTasks'], 'READY')
                self.assertEqual(report['lifecycleState'], 'CLOSED')
                self.assertFalse(report['installedSupervisor'] or report['nativeRuntime']
                                 or report['kernelConfinementTested'])
                self.assertTrue(report['nativeApiHandlersDoubled'])
                self.assertEqual((report['realModelCalls'], report['realProviderCalls']), (0, 0))
                out, err = server.communicate(b'STOP FIXTURE\n', timeout=8)
                self.assertEqual((server.returncode, err), (0, b''),
                                 (out + err).decode('utf-8', 'replace')[-9000:])
                snapshot = json.loads(out)
                self.assertEqual(snapshot['result'], 'PASS')
                for field in ('spawnCount', 'volumeStopCalls', 'volumeFinishCalls',
                              'stopWrites', 'loopCloses', 'leaseCloses'):
                    self.assertEqual(snapshot[field], 1, field)
                self.assertEqual(snapshot['volumeStage'], 'CLOSED')
                self.assertEqual(snapshot['volumeClosure']['state'], 'CLOSED')
                self.assertTrue(snapshot['volumeClosure']['imageLeaseReleased'])
                self.assertTrue(snapshot['originalVolumeRetained'])
                self.assertTrue(snapshot['originalPopenAndChannel'])
                self.assertEqual(snapshot['childReturnCode'], 0)
                self.assertTrue(snapshot['childExited'])
                self.assertFalse(snapshot['volumeMayClose'])
                rows = snapshot['journal']
                self.assertEqual(sum(row['event'] == 'bootstrap' for row in rows), 1)
                commands = [row for row in rows if row['event'] == 'command']
                self.assertEqual([row['sequence'] for row in commands], list(range(1, len(commands) + 1)))
                self.assertEqual([row['action'] for row in commands][-1], 'close')
                self.assertEqual(sum(row['action'] == 'close' for row in commands), 1)
                self.assertEqual(snapshot['childCommandSequence'], len(commands))
                finals = [row for row in rows if row['event'] == 'final']
                self.assertEqual(len(finals), 1)
                final = finals[0]
                self.assertTrue(final['sameOriginalOwner'])
                self.assertFalse(final['controlFenced'])
                self.assertEqual(final['pendingTasks'], 0)
                self.assertEqual(final['nativeLifecycleCalls'], ['start', 'close'])
                self.assertTrue(final['nativeMethodsDoubled'])
                self.assertTrue(final['nativeApiHandlersDoubled'])
                self.assertFalse(final['installedRuntime'])
                self.assertEqual(final['bindingChecks'], 2 * final['httpRequests'])
                http_rows = [row for row in rows if row['event'] == 'http']
                self.assertEqual(len(http_rows), final['httpRequests'])
                self.assertEqual(sum(row['action'] == 'http' for row in commands), len(http_rows))
                replies = [row for row in rows if row['event'] == 'reply' and row['type'] == 'task-reply']
                self.assertEqual(len(replies), len(http_rows))
                if name == 'wrong-bearer':
                    self.assertEqual((final['intents'], final['dispatches'], final['stops'], final['queries']), (0, 0, 0, 0))
                    self.assertEqual((final['httpRequests'], final['unauthorized']), (1, 1))
                    self.assertEqual(replies[0]['httpStatus'], 401)
                    self.assertIsNone(replies[0]['error'])
                    self.assertEqual(snapshot['taskMutationCount'], 0)
                else:
                    self.assertEqual((final['intents'], final['dispatches'], final['stops'], final['queries']), (1, 1, 1, 1))
                    self.assertEqual(final['unauthorized'], 0)
                    self.assertEqual(snapshot['taskMutationCount'], 3)
                    self.assertEqual(final['lossInjected'], name == 'lost-dispatch-reply')
                    routes = {row['path'] for row in http_rows}
                    self.assertEqual(routes, {'/alaz/host/v1/capabilities', '/alaz/host/v1/intents',
                        '/alaz/host/v1/dispatch', '/alaz/host/v1/requests/' + 'b' * 32,
                        '/v1/runs/run_' + 'd' * 32, '/v1/runs/run_' + 'd' * 32 + '/stop'})
                    errors = [row['error'] for row in replies if row['error'] is not None]
                    self.assertEqual(errors, ['service_task_http_outcome_unknown']
                                     if name == 'lost-dispatch-reply' else [])
                public = json.dumps({'node': report, 'server': snapshot})
                for private in (connection['owner']['token'], connection['socketPath'],
                                'fixture-task-bearer', 'fixture-wrong-bearer'):
                    self.assertNotIn(private, public)
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
    setattr(ServiceTaskIntegration, 'test_' + scenario_name.replace('-', '_'), test)


if __name__ == '__main__':
    unittest.main()
