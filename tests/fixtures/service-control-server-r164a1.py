"""R164 disposable source fixture: real server/channel/child pipes and generic cleanup.

Kernel, mount worker, cgroup, image lease, native receipts, source trust and
startTicks are explicit doubles. No installed service or actual volume is used.
The unchanged generic stop/finish methods run through ClosureHarness ports.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import select
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
import service_supervisor_fixtures_r163a1 as child_fixture
from service_closure_fixtures_r164a1 import ClosureHarness
from service_control_server import ServiceControlServer

FAILURES = {'lost-stop-reply': 'stop_lost_reply',
            'autoclear-pending': 'finish_attachment',
            'stream-close-failure': 'finish_stream_close'}


def main():
    directory, scenario = sys.argv[1:]
    mode = 'close_gate' if scenario == 'deferred-close' else 'normal'
    script = child_fixture.CHILD
    if mode == 'close_gate':
        marker = "    if action=='close':\n"
        assert script.count(marker) == 1
        script = script.replace(marker, marker + """        release=pathlib.Path(journal+'.close-release')
        deadline=time.monotonic()+6
        while not release.exists():
            if time.monotonic()>=deadline:raise SystemExit(3)
            time.sleep(.005)
""")
    harness = ClosureHarness(mode, failure=FAILURES.get(scenario))
    harness.volume.token = 'c' * 32
    harness.volume.scope = harness.volume.scope.parent / ('volume-' + harness.volume.token)
    harness.binding = replace(harness.binding, token=harness.volume.token,
                              scope=str(harness.volume.scope))
    with patch.object(child_fixture, 'CHILD', script), harness as h:
        server = ServiceControlServer(h.volume, h.ipc, h.filesystem, h.record,
            socket_path=str(Path(directory) / 'control.sock'), scratch=h.scratch,
            instance_id=h.instance_id, service_id=h.service_id,
            request_seconds=1, response_seconds=1,
            operation_seconds=.03 if scenario == 'deferred-close' else 3).bind()
        lost_final = []
        actual_write = server._write
        def write(client, value):
            if scenario == 'lost-final-reply' and value['state'] == 'CLOSED' and not lost_final:
                # Inject loss only AFTER the real server validates/seals CLOSED.
                # serve_one then closes this real socket; no response is sent.
                lost_final.append(True)
                raise BrokenPipeError('fixture final response loss')
            return actual_write(client, value)
        server._write = write
        try:
            connection = server.connection()
            connection['journal'] = str(h.journal)
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
            original = (child is not None and child.process is h.children[0]
                        and child.channel.process is child.process and child.owner is h.volume)
            print(json.dumps({'result': 'PASS', 'spawnCount': len(h.children),
                'volumeStopCalls': h.stop_calls, 'volumeFinishCalls': h.finish_calls,
                'stopWrites': h.stop_writes, 'loopCloses': h.loop_closes,
                'leaseCloses': h.lease_closes, 'events': h.events,
                'volumeStage': h.volume.stage, 'volumeClosure': view['volumeClosure'],
                'originalVolumeRetained': server._volume is h.volume
                    and h.volume._service_control_server is server,
                'originalPopenAndChannel': bool(original),
                'childReturnCode': child.process.returncode,
                'childExited': view['childExited'], 'volumeMayClose': view['volumeMayClose'],
                'childCommandSequence': child.channel.sequence,
                'lostFinalResponseInjected': bool(lost_final),
                'installedSupervisor': False, 'nativeRuntime': False,
                'kernelConfinementTested': False, 'startTicksPortIsFixture': True,
                'realModelCalls': 0, 'realProviderCalls': 0}), flush=True)
        finally:
            server.close_listener()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
