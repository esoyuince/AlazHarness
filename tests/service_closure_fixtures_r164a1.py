"""R164 source fixtures: actual child pipes and original stop/finish functions.

Worker replies, kernel identities, cgroup/loop/mount and image-lease ports are
explicit doubles. Private temporary files back the fixture fence/target/scope;
they are not a kernel mount or cgroup. No installed/native acceptance is claimed.
Only the test-owned synthetic child is terminated during fixture teardown.
"""
from dataclasses import replace
import errno
import os
from pathlib import Path
from unittest.mock import Mock, patch

from service_supervisor_fixtures_r163a1 import Harness as ChildHarness, g, sv

_STOP = g.volume.VolumeSupervisor.stop
_FINISH = g.volume.VolumeSupervisor.finish
_OWNED = g.volume.VolumeSupervisor._owned
_EMPTY = g.volume.VolumeSupervisor._empty_scope
_SYNC = g.volume.VolumeSupervisor._sync_parent
_MEMBERS = g.kernel._members
_OS_CLOSE = os.close


class _PathPort:
    def __init__(self, harness, name, external, actual):
        self.harness, self.name, self.external, self.actual = harness, name, str(external), actual

    def __str__(self):
        return self.external

    def __fspath__(self):
        return self.external

    def __truediv__(self, value):
        return self.actual / value

    @property
    def parent(self):
        return self.actual.parent

    def stat(self):
        return self.actual.stat()

    def read_bytes(self):
        return self.actual.read_bytes()

    def iterdir(self):
        return self.actual.iterdir()

    def rmdir(self):
        h = self.harness
        h.events.append('scope_remove')
        if h.failure == 'finish_scope':
            raise OSError(errno.EBUSY, 'fixture cgroup busy')
        # Real cgroup control files do not prevent rmdir. These two ordinary
        # temporary files model those virtual files only inside this fixture.
        for name in ('cgroup.procs', 'cgroup.events'):
            (self.actual / name).unlink()
        self.actual.rmdir()
        if h.failure == 'finish_fence':
            h.fence_path.write_bytes(b'fixture changed fence')

    def unlink(self):
        self.harness.events.append('fence_unlink')
        self.actual.unlink()


class _LeasePort:
    def __init__(self, harness):
        self.harness = harness
        self.closed = False

    def confirm(self):
        g.volume.require(not self.closed, 'fixture_image_lease_closed')

    def close(self):
        h = self.harness
        h.lease_closes += 1
        h.events.append('lease_close')
        assert not h.scope_path.exists() and not h.fence_path.exists()
        assert h._worker_code == 0 and h.loop_closes == 1
        self.closed = True
        if h.failure == 'finish_lease':
            raise OSError('fixture lease close unconfirmed')


class _WorkerStream:
    def __init__(self, harness, name):
        self.harness, self.name = harness, name
        self.closed = False

    def write(self, data):
        h = self.harness
        assert self.name == 'stdin'
        assert data == ('STOP ' + h.volume.token + '\n').encode()
        assert h.volume.stage == 'STOPPING'
        assert h.volume._service_child.closure.state == 'STOPPING'
        assert h.volume._service_child.closure.stop_attempted
        h.stop_writes += 1
        h.events.append('worker_stop_write')
        if h.failure == 'stop_write':
            raise BrokenPipeError('fixture uncertain STOP write')
        return len(data)

    def flush(self):
        self.harness.events.append('worker_stop_flush')
        if self.harness.failure == 'stop_flush':
            raise BrokenPipeError('fixture uncertain STOP flush')

    def close(self):
        h = self.harness
        h.events.append('worker_' + self.name + '_close')
        self.closed = True
        if h.failure == 'finish_stream_close' and self.name == 'stdin':
            raise OSError('fixture post-release stream close')


class ClosureHarness(ChildHarness):
    """Same public child fixture API, plus counted original volume teardown.

    ``mode`` selects the existing synthetic child (normal/delayed_reply/etc).
    ``failure`` selects one explicit kernel/worker/lease fault. The caller may
    change the owner token/scope and matching binding before entering.
    """
    def __init__(self, mode='normal', *, failure=None):
        super().__init__(mode)
        self.failure = failure
        self.events = []
        self.stop_calls = self.finish_calls = self.stop_writes = 0
        self.loop_closes = self.lease_closes = 0
        self._worker_code = None
        self.scope_path = self.path / 'volume-scope'
        self.target_path = self.path / 'volume-target'
        self.fence_path = self.path / 'volume-fence.json'
        self.loop_fd = 9999999

    def __enter__(self):
        owner = self.volume
        self.scope_path.mkdir()
        self.target_path.mkdir()
        self.fence_path.write_bytes(owner.fence_bytes)
        self.fence_path.chmod(0o600)
        owner.scope = _PathPort(self, 'scope', owner.scope, self.scope_path)
        owner.target = _PathPort(self, 'target', owner.target, self.target_path)
        owner.fence = _PathPort(self, 'fence', owner.fence, self.fence_path)
        owner.scope_id = self._identity(self.scope_path)
        owner.target_id = self._identity(self.target_path)
        owner.fence_id = self._identity(self.fence_path)
        owner.lease = _LeasePort(self)
        owner.loop_fd = self.loop_fd
        owner.worker.stdin = _WorkerStream(self, 'stdin')
        owner.worker.stdout = _WorkerStream(self, 'stdout')
        owner.worker.stderr = _WorkerStream(self, 'stderr')
        owner.worker.poll = Mock(side_effect=lambda: self._worker_code)
        owner.worker.wait = Mock(side_effect=self._wait_worker)
        owner.worker.returncode = None
        self._scope_members([owner.worker.pid], populated=True)
        self.binding = replace(self.binding, token=owner.token, scope=str(owner.scope),
                               scope_identity=owner.scope_id)
        super().__enter__()
        # These are the unchanged production ownership/cleanup implementations;
        # only their explicit OS/worker/lease ports below are fixture doubles.
        self.stack.enter_context(patch.object(sv.ServiceVolumeSupervisor, '_owned', _OWNED))
        self.stack.enter_context(patch.object(g.volume, 'trusted', side_effect=self._trusted))
        self.stack.enter_context(patch.object(g.volume, 'fs_type', return_value=g.volume.CGROUP2_MAGIC))
        self.stack.enter_context(patch.object(g.kernel, 'Path', side_effect=self._kernel_path))
        self.stack.enter_context(patch.object(g.kernel, '_members', side_effect=self._members))
        self.stack.enter_context(patch.object(g.volume, 'read_line', side_effect=self._read_worker))
        self.stack.enter_context(patch.object(g.volume, 'attachments', side_effect=self._attachments))
        self.stack.enter_context(patch.object(g.volume.os, 'close', side_effect=self._close_fd))
        self.stack.enter_context(patch.object(g.volume.os.path, 'ismount', side_effect=self._is_mount))
        self.stack.enter_context(patch.object(g.volume.VolumeSupervisor, 'stop', self._original_stop))
        self.stack.enter_context(patch.object(g.volume.VolumeSupervisor, 'finish', self._original_finish))
        self.stack.enter_context(patch.object(owner, '_empty_scope', side_effect=self._empty_scope))
        self.stack.enter_context(patch.object(owner, '_sync_parent', side_effect=self._sync_parent))
        self._previous_retained = g.volume._RETAINED.get(owner.token)
        g.volume._RETAINED[owner.token] = owner
        self._retained_token = owner.token
        if self.failure == 'preflight_members':
            self._scope_members([owner.worker.pid, owner.worker.pid + 1], populated=True)
        if self.failure == 'preflight_nested':
            (self.scope_path / 'nested').mkdir()
        return self

    @staticmethod
    def _identity(path):
        value = path.stat()
        return value.st_dev, value.st_ino

    def _trusted(self, path, **unused):
        actual = path.actual if isinstance(path, _PathPort) else Path(path)
        if actual in (self.scope_path, self.target_path, self.fence_path):
            return self._identity(actual)
        return (1, 2)  # Source/interpreter trust remains an explicit R163 port.

    def _kernel_path(self, path):
        return self.scope_path if str(path) == str(self.volume.scope) else Path(path)

    def _scope_members(self, pids, *, populated):
        (self.scope_path / 'cgroup.procs').write_text(''.join(str(pid) + '\n' for pid in pids))
        (self.scope_path / 'cgroup.events').write_text('populated ' + str(int(populated)) + '\n')

    def _members(self, binding, expected):
        self.events.append('members_worker' if expected else 'members_empty')
        return _MEMBERS(binding, expected)

    def _read_worker(self, process, seconds=15):
        assert process is self.volume.worker
        if self.failure == 'stop_lost_reply':
            self._exit_worker(0)
            raise g.volume.SupervisorRejected('supervisor_worker_timeout')
        if self.failure == 'stop_busy':
            return {'state': 'BUSY', 'pid': process.pid, 'token': self.volume.token}
        token = 'foreign-token' if self.failure == 'stop_foreign' else self.volume.token
        pid = process.pid + 1 if self.failure == 'stop_foreign_pid' else process.pid
        self.events.append('worker_unmounted')
        return {'state': 'UNMOUNTED', 'pid': pid, 'token': token}

    def _exit_worker(self, code):
        self._worker_code = code
        self.volume.worker.returncode = code
        self._scope_members([], populated=self.failure == 'finish_populated')
        self.events.append('worker_exit_' + str(code))
        if self.failure == 'finish_members':
            self._scope_members([self.volume.worker.pid + 1], populated=True)
        if self.failure == 'finish_nested':
            (self.scope_path / 'nested').mkdir()
        if self.failure == 'finish_target_nonempty':
            (self.target_path / 'foreign').write_text('fixture preserved')

    def _wait_worker(self, timeout):
        if self._worker_code is None:
            self._exit_worker(2 if self.failure == 'stop_exit' else 0)
        return self._worker_code

    def _original_stop(self, owner=None):
        owner = self.volume if owner is None else owner
        assert owner is self.volume
        self.stop_calls += 1
        self.events.append('original_stop')
        return _STOP(owner)

    def _original_finish(self, owner=None):
        owner = self.volume if owner is None else owner
        assert owner is self.volume
        self.finish_calls += 1
        self.events.append('original_finish')
        return _FINISH(owner)

    def _empty_scope(self):
        self.events.append('empty_scope')
        return _EMPTY(self.volume)

    def _attachments(self, pin):
        assert pin is self.volume.pin
        self.events.append('attachments')
        if self.failure == 'finish_inventory':
            raise g.volume.SupervisorRejected('fixture_loop_inventory_unknown')
        return [{'device': pin.device, 'inode': pin.inode}] if self.failure == 'finish_attachment' else []

    def _close_fd(self, fd):
        if fd != self.loop_fd:
            return _OS_CLOSE(fd)
        self.loop_closes += 1
        self.events.append('loop_close')
        if self.failure == 'finish_loop_close':
            raise OSError('fixture loop close unconfirmed')

    def _is_mount(self, path):
        return path is self.volume.target and self.failure == 'finish_hostmount'

    def _sync_parent(self):
        self.events.append('fence_fsync')
        if self.failure == 'finish_fsync':
            raise OSError('fixture parent fsync failure')
        return _SYNC(self.volume)

    def cleanup(self):
        if hasattr(self, '_retained_token'):
            if g.volume._RETAINED.get(self._retained_token) is self.volume:
                g.volume._RETAINED.pop(self._retained_token)
            if self._previous_retained is not None:
                g.volume._RETAINED.setdefault(self._retained_token, self._previous_retained)
        super().cleanup()


Harness = ClosureHarness
