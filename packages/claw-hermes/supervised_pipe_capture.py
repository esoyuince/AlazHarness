"""Bounded main-thread I/O for an already-owned Linux child, never a launcher.

Timeout/overflow preserves the Popen object, pipes and bounded partial buffers.
There is no signal, retry, second send or volume/lease operation in this module.
"""
from dataclasses import dataclass, field
import os
import selectors
import subprocess
import time


class CaptureRejected(RuntimeError):
    pass


@dataclass
class PipeCapture:
    limit: int = 65536
    stdout_bytes: bytearray = field(default_factory=bytearray)
    stderr_bytes: bytearray = field(default_factory=bytearray)
    stdout_eof: bool = False
    stderr_eof: bool = False
    stdin_closed: bool = False
    send_started: bool = False
    input_written: int = 0
    overflowed: bool = False

    def __post_init__(self):
        if type(self.limit) is not int or not 1 <= self.limit <= 65536:
            raise CaptureRejected('capture_limit')

    def _selector(self, process, *, write):
        selector = selectors.DefaultSelector()
        try:
            for name in ('stdout', 'stderr'):
                if not getattr(self, name + '_eof'):
                    stream = getattr(process, name)
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
            if write and not self.stdin_closed:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            return selector
        except BaseException:
            selector.close()
            raise

    def _event(self, selector, key, payload):
        stream = key.fileobj
        if key.data == 'stdin':
            part = payload[self.input_written:self.input_written + 16384]
            try:
                size = os.write(stream.fileno(), part)
            except BlockingIOError:
                return
            if size <= 0:
                raise CaptureRejected('capture_input_stalled')
            self.input_written += size
            if self.input_written == len(payload):
                selector.unregister(stream)
                stream.close()
                self.stdin_closed = True
            return
        name = key.data
        buffer = getattr(self, name + '_bytes')
        try:
            chunk = os.read(stream.fileno(), min(16384, self.limit - len(buffer) + 1))
        except BlockingIOError:
            return
        if not chunk:
            selector.unregister(stream)
            stream.close()
            setattr(self, name + '_eof', True)
            return
        remaining = self.limit - len(buffer)
        buffer.extend(chunk[:remaining])
        if len(chunk) > remaining:
            self.overflowed = True
            raise CaptureRejected('capture_output_bound')

    def send_once(self, process, payload, timeout):
        if self.send_started or type(payload) is not bytes or not 0 < len(payload) <= 65537:
            raise CaptureRejected('capture_single_bounded_send')
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise CaptureRejected('capture_timeout_bound')
        self.send_started = True
        deadline = time.monotonic() + timeout
        with self._selector(process, write=True) as selector:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired('fixed supervised child', timeout)
                for key, _ in selector.select(min(remaining, 0.25)):
                    self._event(selector, key, payload)
        remaining = deadline - time.monotonic()
        if remaining <= 0 and process.poll() is None:
            raise subprocess.TimeoutExpired('fixed supervised child', timeout)
        process.wait(timeout=max(0, remaining))

    def drain_available(self, process):
        """Read already available output only; never write or wait for input."""
        if not self.send_started or self.overflowed:
            raise CaptureRejected('capture_observation_unavailable')
        with self._selector(process, write=False) as selector:
            while selector.get_map():
                ready = selector.select(0)
                if not ready:
                    break
                for key, _ in ready:
                    self._event(selector, key, None)

    @property
    def complete(self):
        return self.stdin_closed and self.stdout_eof and self.stderr_eof and not self.overflowed
