"""Bounded pipes of one already-owned service child; no launch or cleanup authority.

The supervisor supplies its original Popen object and immutable child identity.
Timeout preserves the outstanding request and its partial bytes. Observation
never resends it, kills a process, closes a store or releases a volume. The
private loopback endpoint in a READY frame is not a host-reachable endpoint.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import subprocess
import time

import gateway_service_control as wire

MAX_FRAME = 65536
MAX_BOOTSTRAP = 131072
MAX_WAIT = 60
STDERR_TAIL = 16384


class ServiceChannelRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceChannelRejected(reason)


class ServiceChannel:
    """One launch, one in-flight control command, streaming bounded observations.

    Reaping and EOF are separate from the child's final CLOSED report. The
    owning supervisor must still verify its mount worker and complete cgroup
    inventory before any volume stop/finish can become eligible.
    """

    def __init__(self, process, *, service_id, previous_epoch, instance_id):
        wire.request_id(service_id, 1)
        require(type(previous_epoch) is int and 0 < previous_epoch < 2**63 - 1,
                'service_channel_previous_epoch')
        require(type(instance_id) is str and
                re.fullmatch('[A-Za-z0-9._-]{1,128}', instance_id) is not None,
                'service_channel_instance')
        require(type(process.pid) is int and 0 < process.pid < 2**31,
                'service_channel_process')
        self.process = process
        self.service_id = service_id
        self.identity = (process.pid, previous_epoch + 1, instance_id)
        self.phase = 'NEW'
        self.sequence = 0
        self.pending = None
        self.last_frame = None
        self.final_frame = None
        self.ready_seen = False
        self.was_unknown = False
        self.input_started = False
        self.input_bytes = b''
        self.input_written = 0
        self.stdout = bytearray()
        self.stdout_eof = self.stderr_eof = False
        self.stdin_closed = False
        self.stderr_tail = bytearray()
        self.stderr_bytes = 0
        self.stderr_digest = hashlib.sha256()
        self.stdout_bytes = 0
        self.stdout_digest = hashlib.sha256()
        self.failure = None

    def _unknown(self, reason, *, fatal=False):
        self.phase = 'UNKNOWN'
        self.was_unknown = True
        if fatal:
            self.failure = reason

    def start(self, payload, *, timeout=30):
        require(not self.input_started and self.phase == 'NEW',
                'service_channel_start_once')
        require(type(payload) is bytes and 0 < len(payload) <= MAX_BOOTSTRAP
                and b'\n' not in payload, 'service_channel_bootstrap_bound')
        self._timeout(timeout)
        self.input_started = True
        self.phase = 'STARTING'
        self.pending = {'type': 'ready', 'sequence': 0, 'requestId': None}
        self.input_bytes = payload + b'\n'
        self.input_written = 0
        return self._wait(timeout)

    def command(self, action, *, timeout=30):
        require(self.ready_seen and self.phase in ('READY', 'DRAINING')
                and self.pending is None and self.final_frame is None,
                'service_channel_command_unavailable')
        sequence = self.sequence + 1
        value = {'protocol': wire.PROTOCOL, 'serviceId': self.service_id,
                 'sequence': sequence, 'requestId': wire.request_id(self.service_id, sequence),
                 'action': action}
        wire.validate_command(value, service_id=self.service_id)
        data = wire.canonical(value)
        require(0 < len(data) <= MAX_FRAME, 'service_channel_command_bound')
        self._timeout(timeout)
        # Retain the request BEFORE the first byte can reach the child.
        self.sequence = sequence
        self.pending = {'type': 'reply', 'sequence': sequence,
                        'requestId': value['requestId'], 'action': action}
        self.input_bytes = data + b'\n'
        self.input_written = 0
        return self._wait(timeout)

    @staticmethod
    def _timeout(timeout):
        require(type(timeout) in (int, float) and 0 < timeout <= MAX_WAIT,
                'service_channel_wait_bound')

    def _wait(self, timeout):
        self._timeout(timeout)
        deadline = time.monotonic() + timeout
        try:
            while self.pending is not None or (self.final_frame is not None
                                               and self.phase != 'COMPLETED'):
                left = deadline - time.monotonic()
                if left <= 0:
                    self._unknown('service_channel_observation_timeout')
                    return self.status()
                self._pump(min(left, .25), allow_write=True)
                self._reap()
            return self.status()
        except BaseException:
            self._unknown('service_channel_observation_failed')
            raise

    def observe(self, *, timeout=0):
        require(self.input_started and type(timeout) in (int, float)
                and 0 <= timeout <= MAX_WAIT, 'service_channel_observe_bound')
        require(self.failure is None, self.failure or 'service_channel_invalid')
        try:
            # A timed-out partial write remains uncertain. Observation is not
            # permission to transmit its remaining bytes or restart the frame.
            self._pump(timeout, allow_write=False)
            self._reap()
            return self.status()
        except BaseException:
            self._unknown('service_channel_observation_failed')
            raise

    def _selector(self, *, allow_write):
        selected = selectors.DefaultSelector()
        try:
            for name in ('stdout', 'stderr'):
                if not getattr(self, name + '_eof'):
                    stream = getattr(self.process, name)
                    os.set_blocking(stream.fileno(), False)
                    selected.register(stream, selectors.EVENT_READ, name)
            if allow_write and self.input_written < len(self.input_bytes) and not self.stdin_closed:
                os.set_blocking(self.process.stdin.fileno(), False)
                selected.register(self.process.stdin, selectors.EVENT_WRITE, 'stdin')
            return selected
        except BaseException:
            selected.close()
            raise

    def _pump(self, timeout, *, allow_write=False):
        require(self.failure is None, self.failure or 'service_channel_invalid')
        with self._selector(allow_write=allow_write) as selected:
            if not selected.get_map():
                # A final frame and closed pipes are not a process exit. Avoid
                # burning a core while waiting for the original child to exit.
                if timeout > 0:
                    time.sleep(timeout)
                return
            for key, _ in selected.select(timeout):
                fd = key.fileobj.fileno()
                try:
                    if key.data == 'stdin':
                        size = os.write(fd, self.input_bytes[self.input_written:self.input_written+16384])
                        require(size > 0, 'service_channel_input_stalled')
                        self.input_written += size
                        continue
                    data = os.read(fd, 16384)
                except BlockingIOError:
                    continue
                if not data:
                    setattr(self, key.data + '_eof', True)
                    key.fileobj.close()
                    continue
                if key.data == 'stderr':
                    self.stderr_bytes += len(data)
                    self.stderr_digest.update(data)
                    self.stderr_tail.extend(data)
                    if len(self.stderr_tail) > STDERR_TAIL:
                        del self.stderr_tail[:-STDERR_TAIL]
                else:
                    self.stdout_bytes += len(data)
                    self.stdout_digest.update(data)
                    self._frames(data)

    def _frames(self, data):
        # Process one frame at a time. Even a hostile continuous producer cannot
        # grow a queue of frames or an unbounded log inside the supervisor.
        for part in data.splitlines(keepends=True):
            self.stdout.extend(part)
            if len(self.stdout) > MAX_FRAME + 1:
                self._unknown('service_channel_frame_bound', fatal=True)
                raise ServiceChannelRejected(self.failure)
            if not self.stdout.endswith(b'\n'):
                continue
            raw = bytes(self.stdout[:-1])
            self.stdout.clear()
            try:
                value = json.loads(raw.decode('ascii'))
                require(wire.canonical(value) == raw, 'service_channel_noncanonical_frame')
                wire.validate_frame(value, service_id=self.service_id, identity=self.identity)
                self._accept(value)
            except Exception:
                self._unknown('service_channel_invalid_frame', fatal=True)
                raise ServiceChannelRejected(self.failure) from None

    def _accept(self, value):
        require(self.final_frame is None, 'service_channel_after_final')
        pending = self.pending
        require(pending is not None and value['sequence'] == pending['sequence']
                and value['requestId'] == pending['requestId'],
                'service_channel_unsolicited_frame')
        require(self.input_written == len(self.input_bytes),
                'service_channel_reply_before_input_complete')
        kind = value['type']
        if kind == 'ready':
            require(not self.ready_seen and pending['type'] == 'ready'
                    and value['owner']['state'] == 'READY', 'service_channel_ready_mismatch')
            self.ready_seen = True
        elif kind == 'final':
            require(self.ready_seen and pending.get('action') == 'close'
                    and value['owner']['state'] == 'CLOSED', 'service_channel_final_mismatch')
            wire.validate_owner(value['owner'], identity=self.identity, closed=True)
            self.final_frame = value
            self.process.stdin.close()
            self.stdin_closed = True
        else:
            require(kind == 'reply' and self.ready_seen and pending['type'] == 'reply'
                    and value['owner']['state'] != 'CLOSED', 'service_channel_reply_mismatch')
        self.last_frame = value
        self.phase = ('CHILD_CLOSED' if kind == 'final' else value['owner']['state'])
        if self.phase == 'UNKNOWN':
            self.was_unknown = True
        self.pending = None
        self.input_bytes = b''
        self.input_written = 0

    def _reap(self):
        code = self.process.poll()
        if code is None:
            if self.stdout_eof or self.stderr_eof:
                # A deliberately closed stderr is allowed. Losing the protocol
                # stream before final never yields retirement permission.
                if self.stdout_eof and self.final_frame is None:
                    self._unknown('service_channel_stdout_lost', fatal=True)
                    raise ServiceChannelRejected(self.failure)
            return
        self.process.wait(timeout=0)
        if code != 0 or self.final_frame is None:
            # Exit is already authoritative even when pipe EOF or a buffered
            # final frame has not arrived. Seal command eligibility now, but
            # retain read-only output drainage; an exit-0 child may still have
            # its valid final frame buffered before both EOFs are observed.
            self._unknown('service_channel_child_exit_pending_output')
        if not (self.stdout_eof and self.stderr_eof):
            return
        if code != 0 or self.final_frame is None or self.stdout or self.pending is not None:
            self._unknown('service_channel_child_exit_unconfirmed', fatal=True)
            raise ServiceChannelRejected(self.failure)
        self.phase = 'COMPLETED'

    def status(self):
        return {'state': self.phase, 'serviceId': self.service_id,
                'pid': self.process.pid, 'epoch': self.identity[1],
                'instanceId': self.identity[2],
                'owner': json.loads(json.dumps(self.last_frame['owner'])) if self.last_frame else None,
                'childExited': self.phase == 'COMPLETED',
                'pendingSequence': self.pending['sequence'] if self.pending else None,
                'observedAfterUnknown': self.was_unknown,
                'stdoutSha256': self.stdout_digest.hexdigest(),
                'stderrSha256': self.stderr_digest.hexdigest(),
                'stdoutBytes': self.stdout_bytes, 'stderrBytes': self.stderr_bytes,
                'retryAllowed': False, 'volumeMayClose': False,
                'fullD3BAccepted': False}
