"""Reusable R163 source fixtures, explicitly not privileged/native acceptance.

The original exact supervisor, new delegation and ServiceChannel are real.
Only a test-owned synthetic Python child is spawned. Kernel/lease/source-trust
ports are doubles; its READY/final receipts do not establish a native service,
confinement, store ownership, model result or volume-release permission.
"""
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_supervised_service as g
import service_volume_supervisor as sv
import test_gateway_state_projection as projection_fixture
import test_service_projection_r161a1 as receipt_fixture
from test_supervised_service_channel_r160a1 import CHILD

SID = 'a' * 32
INSTANCE = 'owned-service-2'
SCRATCH = '/srv/test/scratch'
_POPEN = subprocess.Popen


def launch_values():
    """Fresh typed receipt/config inputs; file/selection bytes are not secrets."""
    state = g.handoff.preopen.live.PreparedStoreExpectation(g.handoff.preopen.live.NATIVE_PIN,
        'a' * 64, 'b' * 64, '12345678-1234-4234-8234-123456789012',
        123, (1792, 21), (1792, 22), 1, 'previous-native-owner')
    reply = g.handoff.response.PreparedResponseExpectation(g.handoff.response.NATIVE_FEATURE,
        g.handoff.response.SCHEMA_SHA256, (1792, 23))
    record = g.handoff.ServiceStartup(state, reply, receipt_fixture.receipt())
    ipc = {**projection_fixture.V, 'version': 2, 'mode': 'projected_root_principal',
           'principalContract': dict(projection_fixture.P)}
    fs = json.loads(json.dumps(projection_fixture.FS))
    return ipc, fs, record, SCRATCH, INSTANCE, SID


class Harness:
    """Use as a context manager; cleanup terminates only this test's children.

    Attributes volume/ipc/filesystem/record/scratch/instance_id/service_id are
    accepted directly by ServiceControlServer. `lines()` exposes the synthetic
    child's journal; bootstrap and action counts prove no retransmission.
    """

    def __init__(self, mode='normal'):
        self.mode = mode
        self.stack = ExitStack()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.journal = self.path / 'child.jsonl'
        self.children = []
        self.launch_calls = []
        (self.ipc, self.filesystem, self.record, self.scratch,
         self.instance_id, self.service_id) = launch_values()
        self.volume = object.__new__(sv.ServiceVolumeSupervisor)
        owner = self.volume; b = projection_fixture.binding()
        owner.who = (os.getpid(), threading.get_ident())
        owner.pin = b.image; owner.scope = PurePosixPath(b.scope)
        owner.scope_id = b.scope_identity; owner.target = PurePosixPath(b.mountpoint)
        owner.token = b.token; owner.loop_number = b.loop_number
        owner.fence_bytes = b'R163 synthetic retained fence'
        owner.stage = 'RUNNING'; owner.spawn_uncertain = False
        owner.worker = Mock(pid=1000000 + os.getpid()); owner.worker.poll.return_value = None
        owner._service_child = None
        # /proc and privileged lifetime identities are explicit doubles. The
        # fixture Popen and all standard-pipe reads/writes remain actual.
        self.controller_ticks = 100
        self.binding = replace(b, controller_pid=os.getpid(), controller_start=self.controller_ticks,
            worker_pid=owner.worker.pid,
            fence_sha256=hashlib.sha256(owner.fence_bytes).hexdigest())
        self.popen = Mock(side_effect=self._spawn)
        self.close_namespace = Mock()
        self.owned_calls = 0

    def __enter__(self):
        def owned(owner):
            self.owned_calls += 1
            g.require(owner is self.volume and owner.who == (os.getpid(), threading.get_ident())
                      and owner.stage != 'CLOSED', 'fixture_original_actor')
        self.stack.enter_context(patch.object(sv.ServiceVolumeSupervisor, '_owned', owned))
        self.stack.enter_context(patch.object(g.volume, 'actor',
            side_effect=lambda: (os.getpid(), threading.get_ident())))
        self.stack.enter_context(patch.object(g, 'ROOT', PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(g.volume, 'trusted', return_value=(1, 2)))
        self.stack.enter_context(patch.object(g, '_binding', return_value=self.binding))
        self.stack.enter_context(patch.object(g.kernel, '_open_namespace', return_value=9))
        self.stack.enter_context(patch.object(g.kernel, '_close_namespace', self.close_namespace))
        self.stack.enter_context(patch.object(g.projection, '_live_root', side_effect=self._live_worker))
        self.stack.enter_context(patch.object(g.projection, 'process_start', side_effect=self._start))
        self.stack.enter_context(patch.object(g.mapping.os, 'makedev',
            side_effect=lambda major, minor: 1792 + minor, create=True))
        self.stack.enter_context(patch.object(g, 'subprocess',
            SimpleNamespace(Popen=self.popen, PIPE=subprocess.PIPE)))
        return self

    def _start(self, pid):
        if pid == self.binding.worker_pid:
            return self.binding.worker_start
        if pid == os.getpid():
            return self.controller_ticks
        return 300 + pid

    def _live_worker(self, pid, ticks):
        g.require((pid, ticks) == (self.binding.worker_pid, self.binding.worker_start),
                  'fixture_original_worker')

    def _spawn(self, *args, **kwargs):
        self.launch_calls.append((args, kwargs))
        process = _POPEN([sys.executable, '-u', '-c', CHILD, str(ROOT), self.mode, str(self.journal)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.children.append(process)
        return process

    def launch(self, *, timeout=2):
        return self.volume.launch_service(self.ipc, self.filesystem, self.record,
            scratch=self.scratch, instance_id=self.instance_id,
            service_id=self.service_id, timeout=timeout)

    def start_observed(self, *, timeout=2, observation_seconds=5):
        """Settle a scheduled bootstrap by read-only observation of that attempt.

        Tests expecting a normal READY do not assume the process is scheduled
        within the first wait. Intentionally lost/partial-input cases continue
        to use launch() directly. A partial write is never advanced here.
        """
        result = self.launch(timeout=timeout)
        deadline = time.monotonic() + observation_seconds
        while result['state'] == 'UNKNOWN':
            child = self.volume._service_child
            channel = child.channel if child is not None else None
            left = deadline - time.monotonic()
            if (left <= 0 or child.blocked or channel is None or channel.failure is not None
                    or not channel.input_started or channel.pending is None
                    or channel.pending['type'] != 'ready'
                    or channel.input_written != len(channel.input_bytes)):
                break
            result = self.observe(timeout=min(left, .05))
        return result

    def observe(self, *, timeout=0):
        return self.volume.observe_service(timeout=timeout)

    def close_service(self, *, timeout=2):
        return self.volume.close_service(timeout=timeout)

    def lines(self):
        if not self.journal.exists():
            return []
        return [json.loads(line) for line in self.journal.read_text().splitlines()]

    def cleanup(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=3)
            for name in ('stdin', 'stdout', 'stderr'):
                stream = getattr(child, name)
                if stream is not None and not stream.closed:
                    stream.close()
        self.stack.close()
        self.temp.cleanup()

    def __exit__(self, *exc):
        self.cleanup()
