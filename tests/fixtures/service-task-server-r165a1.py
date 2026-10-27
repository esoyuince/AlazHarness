"""Real private Unix server, original supervisor/channel and real Popen pipes.

Only the child launch port selects a disposable static HTTP fixture. The R164
ClosureHarness keeps kernel/mount/lease ports explicit and counts original
VolumeSupervisor.stop/finish. No installed/native/kernel acceptance is claimed.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import select
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
from service_closure_fixtures_r164a1 import ClosureHarness
from service_control_server import ServiceControlServer


class TaskHarness(ClosureHarness):
    def _spawn(self, *args, **kwargs):
        self.launch_calls.append((args, kwargs))
        process = subprocess.Popen([sys.executable, '-B', '-u',
            str(ROOT / 'tests/fixtures/service-task-child-r165a1.py'), self.mode,
            str(self.journal)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
        self.children.append(process)
        return process


def main():
    directory, scenario = sys.argv[1:]
    assert scenario in ('task-lifecycle', 'wrong-bearer', 'lost-dispatch-reply')
    harness = TaskHarness(scenario)
    harness.volume.token = 'c' * 32
    harness.volume.scope = harness.volume.scope.parent / ('volume-' + harness.volume.token)
    harness.binding = replace(harness.binding, token=harness.volume.token,
                              scope=str(harness.volume.scope))
    with harness as h:
        server = ServiceControlServer(h.volume, h.ipc, h.filesystem, h.record,
            socket_path=str(Path(directory) / 'control.sock'), scratch=h.scratch,
            instance_id=h.instance_id, service_id=h.service_id,
            request_seconds=2, response_seconds=2, operation_seconds=3).bind()
        try:
            connection = server.connection()
            print(json.dumps(connection), flush=True)
            incoming = bytearray()
            while True:
                server.serve_one(timeout=.02)
                if select.select([0], [], [], 0)[0]:
                    chunk = os.read(0, 64)
                    if not chunk:
                        break
                    incoming.extend(chunk)
                    if b'\n' in incoming:
                        assert bytes(incoming) == b'STOP FIXTURE\n'
                        break
            view = h.observe(timeout=0)
            child = h.volume._service_child
            rows = h.lines()
            print(json.dumps({'result': 'PASS', 'spawnCount': len(h.children),
                'volumeStopCalls': h.stop_calls, 'volumeFinishCalls': h.finish_calls,
                'stopWrites': h.stop_writes, 'loopCloses': h.loop_closes,
                'leaseCloses': h.lease_closes, 'volumeStage': h.volume.stage,
                'volumeClosure': view['volumeClosure'],
                'originalVolumeRetained': server._volume is h.volume
                    and h.volume._service_control_server is server,
                'originalPopenAndChannel': child is not None and len(h.children) == 1
                    and child.process is h.children[0] and child.channel.process is child.process
                    and child.owner is h.volume,
                'childReturnCode': None if child is None else child.process.returncode,
                'childExited': view['childExited'], 'volumeMayClose': view['volumeMayClose'],
                'childCommandSequence': None if child is None else child.channel.sequence,
                'taskMutationCount': len(server._task_mutations), 'journal': rows,
                'installedSupervisor': False, 'nativeRuntime': False,
                'kernelConfinementTested': False, 'startTicksPortIsFixture': True,
                'realModelCalls': 0, 'realProviderCalls': 0}), flush=True)
        finally:
            server.close_listener()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
