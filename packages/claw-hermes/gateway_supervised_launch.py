"""Fixed retained readiness/finite children of the original volume supervisor.

The caller is trusted host root. A pipe payload is data, not authentication or
permission to create a volume. The existing mount worker, image lease, fence,
projection, identity drop and post-exec owner remain authoritative. An unresolved
child keeps that SAME supervisor from stopping or releasing its volume.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import gateway_retained_handoff as handoff
import gateway_finite_protocol as finite_protocol
import gateway_retained_launch as retained_launch
import gateway_retained_projection as retained_projection
import gateway_state_projection as projection
import state_volume_supervisor as volume
from state_image_lease import ImagePin
from supervised_pipe_capture import PipeCapture

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/usr/bin/python3.12'
ENTRY = 'scripts/run_supervised_retained.py'
PROTOCOL = 'alaz-supervised-retained-readiness-v1'
FINITE_ENTRY = 'scripts/run_supervised_finite.py'
FINITE_TARGET_ENTRY = 'scripts/run_finite_projected.py'
FINITE_PROTOCOL = 'alaz-supervised-finite-qualification-v1'
READINESS = 'readiness'
FINITE = 'finite'
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}
MAX_INPUT = 65536
MAX_OUTPUT = 65536
MAX_WAIT = 60
CLONE_NEWNS = 0x00020000
NSFS_MAGIC = 0x6e736673
WORKER_IDLE_SECONDS = 120
STOP_MARGIN_SECONDS = 15
COMPLETED_CHECKS = [
    "preflight", "response_preflight", "before_epoch",
    "response_before_epoch", "after_epoch", "response_after_epoch",
]


class SupervisedLaunchRejected(RuntimeError):
    """Bounded reason codes; never echo the input, paths or credentials."""


def require(value, reason):
    if not value:
        raise SupervisedLaunchRejected(reason)


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _binding(value):
    require(type(value) is dict and set(value) ==
            {f.name for f in fields(projection.VolumeBinding)}, 'supervised_binding_fields')
    image = value['image']
    require(type(image) is dict and set(image) == {f.name for f in fields(ImagePin)},
            'supervised_image_fields')
    pair = value['scope_identity']
    require(type(pair) is list and len(pair) == 2 and
            all(type(n) is int and 0 < n < 2**64 for n in pair),
            'supervised_scope_identity')
    return projection.VolumeBinding(**{**value, 'image': ImagePin(**image),
                                      'scope_identity': tuple(pair)})


def decode(raw):
    """Strict data validation; live parent/volume checks are still mandatory."""
    return _decode(raw, READINESS)


def decode_finite(raw):
    """Decode a fixed finite request; payload data grants no launch authority."""
    return _decode(raw, FINITE)


def _operation(operation):
    require(type(operation) is str and operation in (READINESS, FINITE),
            'supervised_operation')
    return ((PROTOCOL, ENTRY) if operation == READINESS else
            (FINITE_PROTOCOL, FINITE_ENTRY))


def _decode(raw, operation):
    protocol, _ = _operation(operation)
    try:
        require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT,
                'supervised_input_bound')
        data = handoff._json(raw.decode('ascii', 'strict'))
        keys = {
            'protocol', 'binding', 'ipc', 'filesystem', 'record',
            'namespaceFd', 'scratch', 'instanceId'}
        if operation == FINITE:
            keys.add('work')
        require(type(data) is dict and set(data) == keys, 'supervised_input_fields')
        require(_json_bytes(data) == raw and data['protocol'] == protocol,
                'supervised_input_canonical')
        binding = _binding(data['binding'])
        require(type(data['namespaceFd']) is int and 3 <= data['namespaceFd'] < 2**20,
                'supervised_namespace_fd')
        require(type(data['record']) is str and 0 < len(data['record']) <= handoff.MAX_BYTES,
                'supervised_record_bound')
        # The pipe comes only from the verified direct supervisor parent. Its
        # actual fence/mount identities are checked before projection uses it.
        home = binding.mountpoint + '/profile'
        record = handoff.decode(data['record'].encode('ascii'), expected_home=home)
        view, fs = projection.gp.validate(data['ipc'], data['filesystem'])
        retained_projection.RetainedProjection(binding, record.retained,
                                              view['principalContract'])
        retained_launch._instance(data['instanceId'], record.state.instance_id)
        scratch = handoff._home(data['scratch'])
        require(scratch != '/dev/null' and scratch in fs['writable'],
                'supervised_scratch_export')
        decoded = (data, binding, record, view, fs)
        if operation == FINITE:
            work = finite_protocol.validate_work(data['work'])
            return (*decoded, work)
        return decoded
    except SupervisedLaunchRejected:
        raise
    except finite_protocol.FiniteProtocolRejected:
        raise SupervisedLaunchRejected('supervised_finite_work_invalid') from None
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError,
            RecursionError, UnicodeError, RuntimeError):
        raise SupervisedLaunchRejected('supervised_input_invalid') from None


def _members(binding, expected):
    scope = Path(binding.scope)
    require(volume.trusted(scope, directory=True) == binding.scope_identity
            and volume.fs_type(scope) == volume.CGROUP2_MAGIC,
            'supervised_scope_changed')
    raw = (scope / 'cgroup.procs').read_text()
    require(len(raw) < 8192 and len(raw.split()) == len(expected)
            and set(raw.split()) == {str(p) for p in expected}
            and not any(p.is_dir() for p in scope.iterdir()),
            'supervised_other_volume_users')


def _namespace_descriptor(fd, binding):
    require(os.fstat(fd).st_ino == binding.namespace_inode
            and os.readlink('/proc/self/fd/' + str(fd)) ==
                'mnt:[' + str(binding.namespace_inode) + ']'
            and volume.fs_type('/proc/self/fd/' + str(fd)) == NSFS_MAGIC,
            'supervised_namespace_descriptor')
    projection._live_root(binding.worker_pid, binding.worker_start)
    require(os.readlink('/proc/' + str(binding.worker_pid) + '/ns/mnt') ==
            'mnt:[' + str(binding.namespace_inode) + ']',
            'supervised_worker_namespace_changed')


def _open_namespace(worker_pid):
    return os.open('/proc/' + str(worker_pid) + '/ns/mnt', os.O_RDONLY | os.O_CLOEXEC)


def _close_namespace(fd):
    os.close(fd)


def _join_namespace(fd):
    lib = ctypes.CDLL(None, use_errno=True)
    lib.setns.argtypes = [ctypes.c_int, ctypes.c_int]
    lib.setns.restype = ctypes.c_int
    require(lib.setns(fd, CLONE_NEWNS) == 0, 'supervised_namespace_join_failed')


def _enroll(binding):
    with (Path(binding.scope) / 'cgroup.procs').open('w') as stream:
        stream.write(str(os.getpid()))


def child_main(raw):
    """Dedicated child only. Success execs the unchanged fixed readiness target."""
    return _child_main(raw, READINESS)


def finite_child_main(raw):
    """Dedicated child only. Success execs the fixed finite qualification target."""
    return _child_main(raw, FINITE)


def _child_main(raw, operation):
    _operation(operation)
    volume.actor()
    require(sys.executable == PYTHON and sys.flags.isolated == 1
            and sys.dont_write_bytecode and dict(os.environ) == ENVIRONMENT,
            'supervised_fixed_child')
    decoded = _decode(raw, operation)
    data, binding, record, view, fs = decoded[:5]
    require(os.getppid() == binding.controller_pid
            and binding.controller_pid != os.getpid()
            and binding.worker_pid != os.getpid(), 'supervised_direct_parent')
    projection._live_root(binding.controller_pid, binding.controller_start)
    fd = data['namespaceFd']
    _namespace_descriptor(fd, binding)
    _members(binding, {binding.worker_pid})
    # Registration comes first. No child may use the volume while invisible to
    # its original cgroup/lease owner. This known passed descriptor is closed
    # before the unchanged inherited-FD and projection checks run.
    try:
        _enroll(binding)
        _members(binding, {binding.worker_pid, os.getpid()})
        _join_namespace(fd)
    finally:
        _close_namespace(fd)
    require(os.stat('/proc/self/ns/mnt').st_ino == binding.namespace_inode,
            'supervised_join_unconfirmed')
    # The original function repeats live controller/worker/cgroup/fence/loop,
    # mount/profile/export checks and owns the actual confinement transition.
    if operation == READINESS:
        retained_launch.launch(view, fs, binding, record, scratch=data['scratch'],
                               instance_id=data['instanceId'])
    else:
        retained_launch.launch_finite(view, fs, binding, record, decoded[5],
                                      scratch=data['scratch'], instance_id=data['instanceId'])
    raise SupervisedLaunchRejected('supervised_launch_returned')


@dataclass
class _Child:
    phase: str
    capture: PipeCapture
    payload_sha256: str
    previous_epoch: int
    binding: projection.VolumeBinding
    process: object = None
    start_ticks: int | None = None
    was_unknown: bool = False
    result: dict | None = None
    operation: str = READINESS
    expected_work: dict | None = None


class RetainedVolumeSupervisor(volume.VolumeSupervisor):
    """One fixed product-child attempt owned by the original lease/fence owner.

    Inherited begin/attach/start keep the original volume protocol. This class
    does not create a second image owner or alter the worker's lifetime. Failed
    or ambiguous children are retained; no destructor, signal or automatic
    stop/unmount/unlock is added. Both operations share one attempt slot, and
    each observer only reads the original child of its own fixed operation.
    """

    @classmethod
    def begin(cls, pin, cgroup_parent, mountpoint):
        require(cls is RetainedVolumeSupervisor, 'supervised_exact_controller')
        instance = super().begin(pin, cgroup_parent, mountpoint)
        instance._retained_child = None
        instance._worker_deadline = None
        return instance

    def start(self):
        # Earlier than the worker's MOUNTED/120-second STOP wait: conservative.
        started = time.monotonic()
        result = super().start()
        self._worker_deadline = started + WORKER_IDLE_SECONDS
        return result

    def _time_budget(self, timeout):
        require(self._worker_deadline is not None and
                time.monotonic() + timeout + STOP_MARGIN_SECONDS < self._worker_deadline,
                "supervised_worker_deadline_insufficient")

    def _child_clear(self):
        child = getattr(self, '_retained_child', None)
        require(child is None or child.phase == 'COMPLETED',
                'supervised_child_unresolved')

    def stop(self):
        self._owned()
        self._child_clear()
        return super().stop()

    def finish(self):
        self._owned()
        self._child_clear()
        return super().finish()

    def _launch_binding(self, record, fd):
        home = str(self.target) + '/profile'
        handoff.validate(record, expected_home=home)
        binding = projection.VolumeBinding(
            image=self.pin, scope=str(self.scope), scope_identity=self.scope_id,
            token=self.token, controller_pid=self.who[0],
            controller_start=projection.process_start(self.who[0]),
            worker_pid=self.worker.pid, worker_start=projection.process_start(self.worker.pid),
            namespace_inode=os.fstat(fd).st_ino, mountpoint=str(self.target),
            profile_inode=record.retained.home_identity[1], loop_number=self.loop_number,
            fence_sha256=hashlib.sha256(self.fence_bytes).hexdigest())
        _namespace_descriptor(fd, binding)
        _members(binding, {self.worker.pid})
        require(os.readlink('/proc/self/ns/mnt') !=
                'mnt:[' + str(binding.namespace_inode) + ']',
                'supervised_controller_namespace_changed')
        return binding

    def run_retained(self, ipc, filesystem, record, *, scratch, instance_id, timeout=60):
        """Run once on an already RUNNING, trusted, retained supervised volume.

        No image/profile initialization or finite admission. Timeout is an
        UNKNOWN outcome and leaves the owned process and volume retained.
        """
        return self._run(READINESS, ipc, filesystem, record, scratch=scratch,
                         instance_id=instance_id, timeout=timeout)

    def run_finite(self, ipc, filesystem, record, work, *, scratch, instance_id, timeout=60):
        """Run the fixed bounded qualification once on the original owned volume.

        Readiness and finite work share one child-attempt slot. Unknown effects
        retain that same child, original supervisor and image ownership.
        """
        return self._run(FINITE, ipc, filesystem, record, work=work, scratch=scratch,
                         instance_id=instance_id, timeout=timeout)

    def _run(self, operation, ipc, filesystem, record, *, scratch, instance_id,
             timeout, work=None):
        protocol, entry = _operation(operation)
        self._owned()
        require(type(self) is RetainedVolumeSupervisor and
                hasattr(self, '_retained_child'), 'supervised_exact_controller')
        require(self.stage == 'RUNNING' and not self.spawn_uncertain
                and self.worker is not None and self.worker.poll() is None,
                'supervised_worker_not_running')
        require(self._retained_child is None, 'supervised_child_already_attempted')
        require(type(timeout) is int and 1 <= timeout <= MAX_WAIT,
                'supervised_wait_bound')
        self._time_budget(timeout)
        validated_work = None
        if operation == FINITE:
            try:
                validated_work = finite_protocol.validate_work(work)
            except finite_protocol.FiniteProtocolRejected:
                raise SupervisedLaunchRejected('supervised_finite_work_invalid') from None
        trusted_sources = ['packages/claw-hermes/gateway_supervised_launch.py',
                           'packages/claw-hermes/supervised_pipe_capture.py', entry,
                           'packages/claw-hermes/gateway_retained_launch.py',
                           'packages/claw-hermes/gateway_finite_protocol.py',
                           retained_launch.ENTRY if operation == READINESS else FINITE_TARGET_ENTRY]
        if operation == FINITE:
            trusted_sources.append('packages/claw-hermes/gateway_finite_runtime.py')
        for name in trusted_sources:
            volume.trusted(ROOT / name)
        volume.trusted(Path(PYTHON))
        fd = _open_namespace(self.worker.pid)
        try:
            binding = self._launch_binding(record, fd)
            wire = handoff.encode(record, expected_home=binding.mountpoint + '/profile')
            data = {'protocol': protocol, 'binding': asdict(binding),
                'ipc': ipc, 'filesystem': filesystem, 'record': wire.decode('ascii'),
                'namespaceFd': fd, 'scratch': scratch, 'instanceId': instance_id}
            if operation == FINITE:
                data['work'] = validated_work
            payload = _json_bytes(data)
            decoded = _decode(payload, operation)  # Complete pre-effect validation.
            self._owned()
            self._time_budget(timeout)
            child = _Child('SPAWNING', PipeCapture(MAX_OUTPUT),
                           hashlib.sha256(payload).hexdigest(), record.state.epoch, binding,
                           operation=operation,
                           expected_work=decoded[5] if operation == FINITE else None)
            # Keep strong references BEFORE Popen: a thrown exception does not
            # establish that no process was created. stop/finish now fail closed.
            self._retained_child = child
            try:
                child.process = subprocess.Popen(
                    [PYTHON, '-I', '-B', str(ROOT / entry)], cwd='/',
                    env=dict(ENVIRONMENT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, pass_fds=(fd,), close_fds=True, bufsize=0)
                child.start_ticks = projection.process_start(child.process.pid)
                child.phase = 'RUNNING'
            except BaseException:
                child.phase = 'UNKNOWN'
                child.was_unknown = True
                raise
        finally:
            _close_namespace(fd)
        try:
            child.capture.send_once(child.process, payload + b'\n', timeout)
            return self._observe(operation)
        except BaseException:
            if child.phase != 'COMPLETED':
                child.phase = 'UNKNOWN'
                child.was_unknown = True
            raise

    def observe_retained(self):
        """Observe the original child; never resend input or start another job."""
        return self._observe(READINESS)

    def observe_finite(self):
        """Read the same finite child; never resend input or create another job."""
        return self._observe(FINITE)

    def _observe(self, operation):
        _operation(operation)
        self._owned()
        child = getattr(self, '_retained_child', None)
        require(child is not None and child.process is not None,
                'supervised_child_unobservable')
        require(child.operation == operation, 'supervised_operation_mismatch')
        if child.phase == 'COMPLETED':
            return json.loads(json.dumps(child.result))
        require(type(child.start_ticks) is int and child.start_ticks > 0,
                'supervised_child_start_unconfirmed')
        child.capture.drain_available(child.process)
        if child.process.poll() is None:
            return {'state': 'SUPERVISED_CHILD_RUNNING', 'pid': child.process.pid,
                    'volumeMayClose': False, 'fullD3BAccepted': False}
        try:
            child.process.wait(timeout=0)
            require(child.process.returncode == 0, 'supervised_child_failed')
            require(child.capture.complete, 'supervised_output_incomplete')
            out = bytes(child.capture.stdout_bytes)
            err = bytes(child.capture.stderr_bytes)
            require(out.endswith(b'\n') and out.count(b'\n') == 1,
                    'supervised_result_frame')
            result = handoff._json(out.decode('ascii', 'strict'))
            if operation == FINITE:
                try:
                    result = finite_protocol.validate_result(result,
                        work=child.expected_work, pid=child.process.pid,
                        previous_epoch=child.previous_epoch)
                except finite_protocol.FiniteProtocolRejected:
                    raise SupervisedLaunchRejected('supervised_finite_result_invalid') from None
            else:
                self._validate_readiness_result(result, child)
            self._owned()
            require(self.worker.poll() is None, 'supervised_mount_worker_lost')
            # A reaped child is insufficient while another cgroup user remains.
            _members(child.binding, {self.worker.pid})
            child.result = {'state': ('SUPERVISED_PROJECTED_OWNER_CLOSED'
                    if operation == READINESS else 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED'),
                'pid': child.process.pid, 'childStartTicks': child.start_ticks,
                'owner': result, 'inputSha256': child.payload_sha256,
                'stdoutSha256': hashlib.sha256(out).hexdigest(),
                'stderrSha256': hashlib.sha256(err).hexdigest(), 'stderrBytes': len(err),
                'observedAfterUnknown': child.was_unknown, 'childExited': True,
                'volumeMayClose': True, 'finiteWorkExecuted': operation == FINITE,
                'fullD3BAccepted': False}
            child.phase = 'COMPLETED'
            return json.loads(json.dumps(child.result))
        except BaseException:
            child.phase = 'UNKNOWN'
            child.was_unknown = True
            raise

    @staticmethod
    def _validate_readiness_result(result, child):
        expected_keys = {'state', 'pid', 'epoch', 'completedChecks', 'serviceStarted',
                         'runtimeAdmissionAuthorized', 'finiteWorkExecuted', 'fullD3BAccepted'}
        require(type(result) is dict and set(result) == expected_keys
                and result['state'] == 'PROJECTED_RETAINED_OWNER_CLOSED'
                and type(result['pid']) is int and result['pid'] == child.process.pid
                and type(result['epoch']) is int and result['epoch'] == child.previous_epoch + 1,
                'supervised_result_identity')
        checks = result['completedChecks']
        require(type(checks) is list and checks == COMPLETED_CHECKS
                and all(result[k] is False for k in ('serviceStarted',
                    'runtimeAdmissionAuthorized', 'finiteWorkExecuted', 'fullD3BAccepted')),
                'supervised_result_scope')
