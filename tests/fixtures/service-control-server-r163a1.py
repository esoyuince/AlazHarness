"""Disposable integration fixture, never an installed service launcher.

Real production Unix server/ServiceVolumeSupervisor/ServiceChannel and real
test-owned Popen pipes. The fixture doubles privileged kernel/mount/lease,
source-trust and /proc startTicks ports; the child reports synthetic native
receipts. No volume or native runtime is created. Teardown owns only fixture
processes and must never call product stop/finish.
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
import select
import sys
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
import service_supervisor_fixtures_r163a1 as fixture
from service_control_server import ServiceControlServer


def main():
    directory, scenario = sys.argv[1:]
    mode = 'fragment_ready' if scenario in ('lost-start', 'pending-start') else (
        'close_gate' if scenario == 'lost-close' else 'normal')
    child_script = fixture.CHILD
    if mode == 'close_gate':
        marker = "    if action=='close':\n"
        assert child_script.count(marker) == 1
        child_script = child_script.replace(marker, marker + """        release=pathlib.Path(journal+'.close-release')
        deadline=time.monotonic()+6
        while not release.exists():
            if time.monotonic()>=deadline:raise SystemExit(3)
            time.sleep(.005)
""")
    harness = fixture.Harness(mode)
    # This reusable upstream fixture has token == serviceId. Use distinct
    # synthetic private/public values so substring non-disclosure assertions
    # measure the token rather than the deliberately public service ID.
    harness.volume.token = 'c' * 32
    harness.volume.scope = harness.volume.scope.parent / ('volume-' + harness.volume.token)
    harness.binding = replace(harness.binding, token=harness.volume.token,
                              scope=str(harness.volume.scope))
    with patch.object(fixture, 'CHILD', child_script), harness as h:
        # This original pipe/protocol fixture intentionally has no real volume
        # closure ports. R164 must refuse at the worker-only preflight, before
        # either generic stop or finish can run. New R164 fixtures exercise the
        # complete original generic cleanup against explicit kernel/lease ports.
        def no_volume_closure(*args, **kwargs):
            raise fixture.g.kernel.SupervisedLaunchRejected('fixture_volume_unavailable')
        h.stack.enter_context(patch.object(fixture.g.kernel, '_members', no_volume_closure))
        stop = Mock(side_effect=AssertionError('source fixture must not stop volume'))
        finish = Mock(side_effect=AssertionError('source fixture must not release image'))
        with patch.object(fixture.g.volume.VolumeSupervisor, 'stop', stop), \
                patch.object(fixture.g.volume.VolumeSupervisor, 'finish', finish):
            server = ServiceControlServer(h.volume, h.ipc, h.filesystem, h.record,
                socket_path=str(Path(directory) / 'control.sock'), scratch=h.scratch,
                instance_id=h.instance_id, service_id=h.service_id,
                request_seconds=1, response_seconds=1,
                operation_seconds=.03 if scenario == 'pending-start' else 3).bind()
            try:
                connection = server.connection()
                connection['journal'] = str(h.journal)
                print(json.dumps(connection), flush=True)  # Private pipe to the owning test only.
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
                original = child is not None and child.process is h.children[0]
                original = bool(original and child.channel.process is child.process
                                and child.owner is h.volume)
                snapshot = {'result': 'PASS', 'spawnCount': len(h.children),
                    'volumeStopCalls': stop.call_count, 'volumeFinishCalls': finish.call_count,
                    'volumeStage': h.volume.stage,
                    'originalVolumeRetained': (server._volume is h.volume
                        and h.volume._service_control_server is server),
                    'originalPopenAndChannel': original,
                    'childReturnCode': child.process.returncode if child else None,
                    'childExited': view['childExited'], 'volumeMayClose': view['volumeMayClose'],
                    'childCommandSequence': child.channel.sequence if child else 0,
                    'installedSupervisor': False, 'nativeRuntime': False,
                    'kernelConfinementTested': False, 'startTicksPortIsFixture': True,
                    'realModelCalls': 0, 'realProviderCalls': 0}
                print(json.dumps(snapshot), flush=True)
            finally:
                server.close_listener()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
