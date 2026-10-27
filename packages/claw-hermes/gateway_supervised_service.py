"""One fixed service child on the original service-volume owner.

The immutable launch plan is data, never mount or process authority. The exact
original supervisor, worker, lease, fence, namespace and Popen remain retained
through uncertain spawn or pipe results. Observation cannot send input or
retire a volume. Explicit close binds child completion to the original normal
worker stop and original finish; no uncertain cleanup attempt is replayed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

import gateway_service_handoff as handoff
import gateway_service_launch as launch
import gateway_service_projection as mapping
import gateway_state_projection as projection
import gateway_supervised_launch as kernel
import state_volume_supervisor as volume
import gateway_service_control as wire
from supervised_service_channel import ServiceChannel, MAX_BOOTSTRAP, MAX_WAIT

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/usr/bin/python3.12'
ENTRY = 'scripts/run_supervised_service.py'
PROTOCOL = 'alaz-supervised-service-v1'
PLAN_PROTOCOL = 'alaz-supervised-service-plan-v1'
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}


class SupervisedServiceRejected(RuntimeError):
    """Only fixed reason codes; never echo input, paths or native exceptions."""


def require(value, reason):
    if not value:
        raise SupervisedServiceRejected(reason)


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _json(raw, keys, protocol):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BOOTSTRAP,
            'service_supervised_input_bound')
    data = handoff.common._json(raw.decode('ascii', 'strict'))
    require(type(data) is dict and set(data) == keys,
            'service_supervised_input_fields')
    require(_bytes(data) == raw and data['protocol'] == protocol,
            'service_supervised_input_canonical')
    return data


def freeze_launch(ipc, filesystem, record, *, scratch, instance_id, service_id):
    """Detach and validate a bounded launch plan without I/O or authority."""
    try:
        require(type(record) is handoff.ServiceStartup,
                'service_supervised_record_type')
        raw = _bytes({'protocol': PLAN_PROTOCOL, 'ipc': ipc,
            'filesystem': filesystem, 'home': record.service.home,
            'record': handoff.encode(record, expected_home=record.service.home).decode('ascii'),
            'scratch': scratch, 'instanceId': instance_id, 'serviceId': service_id})
        decode_launch(raw)
        return raw
    except SupervisedServiceRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError,
            RecursionError, UnicodeError, RuntimeError):
        raise SupervisedServiceRejected('service_supervised_plan_invalid') from None


def decode_launch(raw):
    """Return six fresh values; the server retains only the canonical bytes."""
    try:
        data = _json(raw, {'protocol', 'ipc', 'filesystem', 'home', 'record',
                          'scratch', 'instanceId', 'serviceId'}, PLAN_PROTOCOL)
        home = handoff.common._home(data['home'])
        require(type(data['record']) is str and 0 < len(data['record']) <= handoff.MAX_BYTES,
                'service_supervised_record_bound')
        record = handoff.decode(data['record'].encode('ascii'), expected_home=home)
        require(record.state.epoch < 2**63 - 1, 'service_supervised_epoch_exhausted')
        ipc, fs = projection.gp.validate(data['ipc'], data['filesystem'])
        launch._instance(data['instanceId'], record.state.instance_id)
        launch._service_id(data['serviceId'])
        scratch = handoff.common._home(data['scratch'])
        require(scratch != '/dev/null' and scratch in fs['writable'],
                'service_supervised_scratch_export')
        for path in (str(ROOT), PYTHON, str(ROOT / ENTRY), str(ROOT / launch.ENTRY)):
            handoff.common._home(path)
            require(any(PurePosixPath(path).is_relative_to(root) for root in fs['readonly']),
                    'service_supervised_entry_not_readonly')
        return ipc, fs, record, scratch, data['instanceId'], data['serviceId']
    except SupervisedServiceRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError,
            RecursionError, UnicodeError, RuntimeError):
        raise SupervisedServiceRejected('service_supervised_plan_invalid') from None


def decode(raw):
    """Validate bootstrap data; live direct-parent and namespace checks follow."""
    try:
        data = _json(raw, {'protocol', 'binding', 'namespaceFd', 'plan'}, PROTOCOL)
        require(type(data['namespaceFd']) is int and 3 <= data['namespaceFd'] < 2**20,
                'service_supervised_namespace_fd')
        require(type(data['plan']) is str, 'service_supervised_plan_type')
        plan = decode_launch(data['plan'].encode('ascii'))
        binding = kernel._binding(data['binding'])
        ipc, fs, record, _, _, _ = plan
        handoff.validate(record, expected_home=binding.mountpoint + '/profile')
        mapping.ServiceProjection(binding, record.service, ipc['principalContract'])
        projection.validate_exports(binding, ipc, fs)
        return data, binding, plan
    except SupervisedServiceRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError,
            RecursionError, UnicodeError, RuntimeError):
        raise SupervisedServiceRejected('service_supervised_bootstrap_invalid') from None


def child_main(raw):
    """Dedicated trusted child; success execs only the fixed R162 receiver."""
    volume.actor()
    require(sys.executable == PYTHON and sys.flags.isolated == 1
            and sys.dont_write_bytecode and dict(os.environ) == ENVIRONMENT,
            'service_supervised_fixed_child')
    data, binding, plan = decode(raw)
    require(os.getppid() == binding.controller_pid
            and os.getpid() not in (binding.controller_pid, binding.worker_pid),
            'service_supervised_direct_parent')
    projection._live_root(binding.controller_pid, binding.controller_start)
    fd = data['namespaceFd']
    kernel._namespace_descriptor(fd, binding)
    kernel._members(binding, {binding.worker_pid})
    try:
        kernel._enroll(binding)
        kernel._members(binding, {binding.worker_pid, os.getpid()})
        kernel._join_namespace(fd)
    finally:
        kernel._close_namespace(fd)
    require(os.stat('/proc/self/ns/mnt').st_ino == binding.namespace_inode,
            'service_supervised_join_unconfirmed')
    ipc, fs, record, scratch, instance, service_id = plan
    launch.launch(ipc, fs, binding, record, scratch=scratch,
                  instance_id=instance, service_id=service_id)
    raise SupervisedServiceRejected('service_supervised_launch_returned')


@dataclass(frozen=True)
class _Custody:
    owner: object
    actor: tuple
    worker: object
    pin: object
    lease: object
    scope: object
    scope_id: tuple
    target: object
    target_id: tuple
    fence: object
    fence_id: tuple
    fence_bytes: bytes
    loop_fd: object
    loop_number: int
    binding: projection.VolumeBinding


@dataclass
class _Closure:
    child: object
    custody: _Custody
    process: object
    channel: ServiceChannel
    final_frame: bytes
    child_result: bytes
    state: str = 'NOT_STARTED'
    stop_attempted: bool = False
    finish_attempted: bool = False
    stop_reply: bytes | None = None
    finish_reply: bytes | None = None
    error: str | None = None


@dataclass
class _Child:
    owner: object
    actor: tuple
    worker: object
    pin: object
    binding: projection.VolumeBinding
    plan: bytes
    payload: bytes
    service_id: str
    previous_epoch: int
    instance_id: str
    custody: _Custody
    process: object = None
    pid: int | None = None
    start_ticks: int | None = None
    channel: ServiceChannel | None = None
    phase: str = 'SPAWNING'
    was_unknown: bool = False
    error: str | None = None
    blocked: bool = False
    process_anchor: object = None
    process_identity: tuple | None = None
    channel_anchor: ServiceChannel | None = None
    closure: _Closure | None = None


def _owner(owner):
    from service_volume_supervisor import ServiceVolumeSupervisor
    require(type(owner) is ServiceVolumeSupervisor and hasattr(owner, '_service_child'),
            'service_supervised_exact_owner')
    require(owner._service_child is owner._service_child_anchor,
            'service_supervised_child_slot_changed')
    owner._owned()
    require(owner.stage == 'RUNNING' and not owner.spawn_uncertain
            and owner.worker is not None and owner.worker.poll() is None,
            'service_supervised_worker_not_running')


def _actor(owner):
    from service_volume_supervisor import ServiceVolumeSupervisor
    require(type(owner) is ServiceVolumeSupervisor and hasattr(owner, '_service_child'),
            'service_supervised_exact_owner')
    require(volume.actor() == owner.who, 'service_supervised_original_actor')
    require(owner._service_child is owner._service_child_anchor,
            'service_supervised_child_slot_changed')


def _timeout(timeout, *, observe=False):
    require(type(timeout) in (int, float) and
            (0 <= timeout <= MAX_WAIT if observe else 0 < timeout <= MAX_WAIT),
            'service_supervised_wait_bound')


def _binding(owner, record, fd):
    handoff.validate(record, expected_home=str(owner.target) + '/profile')
    binding = projection.VolumeBinding(image=owner.pin, scope=str(owner.scope),
        scope_identity=owner.scope_id, token=owner.token, controller_pid=owner.who[0],
        controller_start=projection.process_start(owner.who[0]),
        worker_pid=owner.worker.pid, worker_start=projection.process_start(owner.worker.pid),
        namespace_inode=os.fstat(fd).st_ino, mountpoint=str(owner.target),
        profile_inode=record.service.home_identity[1], loop_number=owner.loop_number,
        fence_sha256=hashlib.sha256(owner.fence_bytes).hexdigest())
    kernel._namespace_descriptor(fd, binding)
    kernel._members(binding, {owner.worker.pid})
    require(os.readlink('/proc/self/ns/mnt') != 'mnt:[' + str(binding.namespace_inode) + ']',
            'service_supervised_controller_namespace_changed')
    return binding


def _unknown(child, reason, *, blocked=False):
    child.phase = 'UNKNOWN'; child.was_unknown = True; child.error = reason
    child.blocked = child.blocked or blocked


def _child_status(child=None):
    if child is not None and child.channel is not None:
        result = child.channel.status()
    else:
        empty = hashlib.sha256(b'').hexdigest()
        result = {'state': child.phase if child else 'NEW',
            'serviceId': child.service_id if child else None, 'pid': child.pid if child else None,
            'epoch': child.previous_epoch + 1 if child else None,
            'instanceId': child.instance_id if child else None, 'owner': None,
            'childExited': False, 'pendingSequence': None, 'observedAfterUnknown': False,
            'stdoutSha256': empty, 'stderrSha256': empty, 'stdoutBytes': 0, 'stderrBytes': 0,
            'retryAllowed': False, 'volumeMayClose': False, 'fullD3BAccepted': False}
    if child is not None and child.phase == 'UNKNOWN':
        result['state'] = 'UNKNOWN'; result['childExited'] = False
    result['observedAfterUnknown'] = result['observedAfterUnknown'] or bool(child and child.was_unknown)
    result['childStartTicks'] = child.start_ticks if child else None
    result['error'] = child.error if child else None
    return result


def _closure_view(child=None):
    closure = child.closure if child is not None else None
    return {'state': closure.state if closure is not None else 'NOT_STARTED',
            'volumeUnmounted': closure is not None and closure.stop_reply is not None,
            'fenceRemovedAfterCleanup': closure is not None and closure.state == 'CLOSED',
            'imageLeaseReleased': closure is not None and closure.state == 'CLOSED'}


def _status(child=None):
    result = _child_status(child)
    result['volumeClosure'] = _closure_view(child)
    if child is not None and child.closure is not None and child.closure.error is not None:
        result['error'] = child.closure.error
    return result


def _identity(child, *, live_process=True):
    """Original object custody; valid after successful unmount/lease release."""
    owner = child.owner; binding = child.binding
    custody = child.custody
    require(type(custody) is _Custody and custody.owner is owner
            and child.actor == custody.actor and child.worker is custody.worker
            and child.pin is custody.pin and child.binding is custody.binding,
            'service_supervised_custody_changed')
    require(owner._service_child is child and owner.who == child.actor
            and owner.pin is child.pin and owner.worker is child.worker
            and owner.lease is custody.lease
            and owner.scope is custody.scope and owner.scope_id == custody.scope_id
            and owner.target is custody.target and owner.target_id == custody.target_id
            and owner.fence is custody.fence and owner.fence_id == custody.fence_id
            and owner.fence_bytes == custody.fence_bytes
            and owner.token == binding.token and str(owner.scope) == binding.scope
            and owner.scope_id == binding.scope_identity and str(owner.target) == binding.mountpoint
            and owner.loop_number == binding.loop_number == custody.loop_number
            and hashlib.sha256(owner.fence_bytes).hexdigest() == binding.fence_sha256,
            'service_supervised_owner_changed')
    require((owner.loop_fd == custody.loop_fd if child.closure is None
             or not child.closure.finish_attempted else owner.loop_fd in (custody.loop_fd, None)),
            'service_supervised_loop_descriptor_changed')
    require(projection.process_start(binding.controller_pid) == binding.controller_start
            and child.worker.pid == binding.worker_pid,
            'service_supervised_controller_or_worker_changed')
    require(child.process is child.process_anchor and child.channel is child.channel_anchor,
            'service_supervised_original_process_channel')
    if not live_process:
        return
    if child.process is None:
        return
    require(child.process.pid == child.pid and type(child.start_ticks) is int
            and child.start_ticks > 0 and child.process_identity == (child.pid, child.start_ticks),
            'service_supervised_child_unconfirmed')
    if child.process.poll() is None:
        try:
            ticks = projection.process_start(child.pid)
        except Exception:
            # Exit can race poll. The original Popen still reaps/drains it.
            require(child.process.poll() is not None, 'service_supervised_child_changed')
        else:
            require(ticks == child.start_ticks, 'service_supervised_child_changed')
    if child.channel is not None:
        require(type(child.channel) is ServiceChannel and child.channel.process is child.process
                and child.channel.service_id == child.service_id
                and child.channel.identity == (child.pid, child.previous_epoch + 1, child.instance_id),
                'service_supervised_channel_changed')


def _check(child):
    _owner(child.owner)
    _identity(child)
    projection._live_root(child.binding.worker_pid, child.binding.worker_start)


def launch_service(owner, ipc, filesystem, record, *, scratch, instance_id,
                   service_id, timeout=30):
    """Attempt one fixed Popen; reserve its owner slot before the first effect."""
    _owner(owner); _timeout(timeout)
    require(owner._service_child is None, 'service_supervised_child_already_attempted')
    plan = freeze_launch(ipc, filesystem, record, scratch=scratch,
                         instance_id=instance_id, service_id=service_id)
    _, _, frozen_record, _, instance_id, service_id = decode_launch(plan)
    for name in ('packages/claw-hermes/service_volume_supervisor.py',
                 'packages/claw-hermes/gateway_supervised_service.py',
                 'packages/claw-hermes/supervised_service_channel.py', ENTRY,
                 'packages/claw-hermes/gateway_service_launch.py', launch.ENTRY):
        volume.trusted(ROOT / name)
    volume.trusted(Path(PYTHON))
    fd = kernel._open_namespace(owner.worker.pid)
    child = None
    try:
        binding = _binding(owner, frozen_record, fd)
        payload = _bytes({'protocol': PROTOCOL, 'binding': asdict(binding),
                          'namespaceFd': fd, 'plan': plan.decode('ascii')})
        decode(payload)
        _owner(owner)
        require(owner._service_child is None, 'service_supervised_child_already_attempted')
        custody = _Custody(owner, owner.who, owner.worker, owner.pin, owner.lease,
            owner.scope, owner.scope_id, owner.target, owner.target_id, owner.fence,
            owner.fence_id, owner.fence_bytes, owner.loop_fd, owner.loop_number, binding)
        child = _Child(owner, owner.who, owner.worker, owner.pin, binding, plan, payload,
                       service_id, frozen_record.state.epoch, instance_id, custody)
        owner._service_child = child
        owner._service_child_anchor = child
        try:
            child.process = subprocess.Popen([PYTHON, '-I', '-B', str(ROOT / ENTRY)],
                cwd='/', env=dict(ENVIRONMENT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, pass_fds=(fd,), close_fds=True, bufsize=0)
            child.process_anchor = child.process
            child.pid = child.process.pid
            child.start_ticks = projection.process_start(child.pid)
            child.process_identity = (child.pid, child.start_ticks)
            child.channel = ServiceChannel(child.process, service_id=service_id,
                previous_epoch=frozen_record.state.epoch, instance_id=instance_id)
            child.channel_anchor = child.channel
            child.phase = 'STARTING'
        except BaseException:
            _unknown(child, 'service_supervised_spawn_unknown', blocked=True)
    finally:
        try:
            kernel._close_namespace(fd)
        except BaseException:
            if child is None:
                raise
            _unknown(child, 'service_supervised_namespace_close_unknown', blocked=True)
    if child.blocked:
        return _status(child)
    try:
        _check(child)
        child.channel.start(payload, timeout=timeout)
        child.phase = child.channel.phase
        return _status(child)
    except BaseException:
        _unknown(child, 'service_supervised_start_unknown')
        return _status(child)


def _completed(child):
    """Recheck the original channel proof, never a serialized permission."""
    channel = child.channel
    require(not child.blocked and child.phase == 'COMPLETED'
            and type(channel) is ServiceChannel and channel is child.channel_anchor
            and channel.process is child.process is child.process_anchor
            and channel.phase == 'COMPLETED' and channel.failure is None
            and channel.input_started and channel.ready_seen and channel.stdin_closed
            and channel.stdout_eof and channel.stderr_eof and not channel.stdout
            and channel.pending is None and channel.input_bytes == b''
            and channel.input_written == 0
            and child.process.poll() == 0 and child.process.returncode == 0,
            'service_supervised_child_completion_required')
    final = channel.final_frame
    wire.validate_frame(final, service_id=child.service_id, identity=channel.identity)
    wire.validate_owner(final['owner'], identity=channel.identity, closed=True)
    require(final['type'] == 'final' and final['sequence'] == channel.sequence
            and final['requestId'] == wire.request_id(child.service_id, channel.sequence)
            and channel.last_frame is final,
            'service_supervised_final_changed')
    return _bytes(final)


def _stop_result(value, child):
    require(type(value) is dict and set(value) == {'state', 'pid', 'token'}
            and value['state'] == 'UNMOUNTED'
            and type(value['pid']) is int and value['pid'] == child.binding.worker_pid
            and value['token'] == child.binding.token,
            'service_supervised_stop_receipt')
    return _bytes(value)


_FINISH_RESULT = {'state': 'CLOSED', 'ownedUsersGone': True, 'loopAttachmentGone': True,
                  'fenceRemovedAfterCleanup': True, 'leaseReleasedLast': True,
                  'realHermesGatewayTested': False, 'fullD3BAccepted': False}


def _finish_result(value):
    require(type(value) is dict and value == _FINISH_RESULT
            and all(type(value[key]) is type(expected) for key, expected in _FINISH_RESULT.items()),
            'service_supervised_finish_receipt')
    return _bytes(value)


def _receipt(raw, validate, *args):
    require(type(raw) is bytes and 0 < len(raw) < 4096, 'service_supervised_receipt_bound')
    value = json.loads(raw.decode('ascii'))
    require(validate(value, *args) == raw, 'service_supervised_receipt_changed')


def _closure_unknown(child, reason):
    # Keep the verified child COMPLETED proof separate from volume uncertainty.
    child.closure.state = 'UNKNOWN'
    child.closure.error = reason
    # Generic finish removes this strong reference before closing its streams.
    # A failure in that tail must still retain the original owner and proof.
    volume._RETAINED.setdefault(child.binding.token, child.owner)


def _child_of(owner):
    _actor(owner)
    child = owner._service_child
    require(type(child) is _Child and child.owner is owner,
            'service_supervised_child_slot_changed')
    return child


def check_service_owner(owner):
    """Read-only original custody gate, including after volume retirement.

    A terminal flag or caller dict cannot bypass the original channel, stop and
    finish proofs. No path through this function sends input or runs cleanup.
    """
    _actor(owner)
    child = owner._service_child
    if child is None:
        _owner(owner)
        return _closure_view()
    require(type(child) is _Child and child.owner is owner,
            'service_supervised_child_slot_changed')
    if child.closure is None:
        # Admission to a read-only status request must survive an original
        # child's uncertain start identity or a lost mount worker. The normal
        # observer checks those live facts and reports UNKNOWN without cleanup.
        # Original actor/object/fence/lease custody is still mandatory here.
        _identity(child, live_process=False)
        owner._owned()
        return _closure_view(child)
    closure = child.closure
    require(type(closure) is _Closure and closure.child is child
            and closure.custody is child.custody and closure.process is child.process_anchor
            and closure.channel is child.channel_anchor
            and closure.state in ('NOT_STARTED', 'STOPPING', 'STOPPED', 'FINISHING', 'CLOSED', 'UNKNOWN')
            and type(closure.stop_attempted) is bool and type(closure.finish_attempted) is bool,
            'service_supervised_closure_custody_changed')
    _identity(child)
    require(_completed(child) == closure.final_frame
            and _bytes(_child_status(child)) == closure.child_result,
            'service_supervised_completion_changed')
    if closure.stop_reply is not None:
        _receipt(closure.stop_reply, _stop_result, child)
        require(closure.stop_attempted and owner.worker.poll() == 0
                and owner.worker.returncode == 0 and owner.stage in ('STOPPED', 'CLOSED'),
                'service_supervised_stop_proof_changed')
    require(not closure.finish_attempted or closure.stop_reply is not None,
            'service_supervised_finish_before_stop')
    if not closure.finish_attempted:
        # The original fence, cgroup and live lease still exist before finish.
        owner._owned()
    if closure.finish_reply is not None:
        _receipt(closure.finish_reply, _finish_result)
        require(closure.finish_attempted and closure.stop_reply is not None,
                'service_supervised_finish_proof_changed')
    if closure.state == 'CLOSED':
        require(closure.finish_reply is not None and owner.stage == 'CLOSED'
                and owner.loop_fd is None and closure.error is None,
                'service_supervised_closed_unconfirmed')
    else:
        require(closure.finish_reply is None, 'service_supervised_terminal_proof_changed')
    return dict(_closure_view(child))


def stop_service_volume(owner):
    """One original normal STOP, gated by the exact completed child."""
    child = _child_of(owner)
    require(child.closure is None, 'service_supervised_stop_already_attempted')
    _check(child)
    final = _completed(child)
    closure = _Closure(child, child.custody, child.process, child.channel,
                       final, _bytes(_child_status(child)))
    child.closure = closure
    try:
        kernel._members(child.binding, {child.worker.pid})
        _check(child)
        require(_completed(child) == final, 'service_supervised_completion_changed')
        # Reserve before generic stop can write or flush any bytes.
        closure.stop_attempted = True
        closure.state = 'STOPPING'
        result = volume.VolumeSupervisor.stop(owner)
        raw = _stop_result(result, child)
        _identity(child)
        require(owner.stage == 'STOPPED' and child.worker.poll() == 0
                and child.worker.returncode == 0, 'service_supervised_stop_unconfirmed')
        owner._owned()
        closure.stop_reply = raw
        closure.state = 'STOPPED'
        check_service_owner(owner)
        return json.loads(raw)
    except BaseException:
        _closure_unknown(child, 'service_supervised_volume_stop_unknown')
        raise SupervisedServiceRejected('service_supervised_volume_stop_unknown') from None


def finish_service_volume(owner):
    """One original finish, only after this owner's exact normal stop proof."""
    child = _child_of(owner)
    closure = child.closure
    require(type(closure) is _Closure and closure.state == 'STOPPED'
            and closure.stop_reply is not None and not closure.finish_attempted,
            'service_supervised_successful_stop_required')
    try:
        check_service_owner(owner)
        require(owner.stage == 'STOPPED', 'service_supervised_successful_stop_required')
        # The original finish also checks populated/procs; this rejects nested
        # empty cgroups before it can close the held loop descriptor.
        kernel._members(child.binding, set())
        closure.finish_attempted = True
        closure.state = 'FINISHING'
        result = volume.VolumeSupervisor.finish(owner)
        raw = _finish_result(result)
        _identity(child)
        require(owner.stage == 'CLOSED' and owner.loop_fd is None,
                'service_supervised_finish_unconfirmed')
        closure.finish_reply = raw
        closure.state = 'CLOSED'
        check_service_owner(owner)
        return json.loads(raw)
    except BaseException:
        # Even a tail stream.close exception may follow fence/lease removal.
        # Keep the attempt and its proof; never replay finish or invent CLOSED.
        closure.finish_reply = None
        _closure_unknown(child, 'service_supervised_volume_finish_unknown')
        raise SupervisedServiceRejected('service_supervised_volume_finish_unknown') from None


def _observe(owner, timeout, *, close=False):
    _timeout(timeout, observe=not close)
    # A foreign actor cannot mutate the original owner's attempt, even to mark
    # it UNKNOWN. Live identity loss by the original actor is retained below.
    _actor(owner)
    # An already retained attempt keeps a bounded UNKNOWN result if any live
    # identity guard fails. It cannot be replaced or commanded after that.
    child = getattr(owner, '_service_child', None)
    if child is None:
        _owner(owner)
        return _status()
    require(type(child) is _Child and child.owner is owner,
            'service_supervised_child_slot_changed')
    if child.closure is not None:
        try:
            check_service_owner(owner)
        except BaseException:
            _closure_unknown(child, 'service_supervised_closure_identity_unknown')
        return _status(child)
    try:
        _check(child)
    except BaseException:
        _unknown(child, 'service_supervised_identity_unknown', blocked=True)
        return _status(child)
    if child.blocked:
        return _status(child)
    if child.channel is None or not child.channel.input_started:
        _unknown(child, 'service_supervised_channel_unavailable', blocked=True)
        return _status(child)
    try:
        channel = child.channel
        if (close and channel.phase in ('READY', 'DRAINING') and channel.pending is None
                and channel.final_frame is None):
            channel.command('close', timeout=timeout)
        else:
            # This includes pending bootstrap/close, uncertain results and final
            # drainage. Never continue a partial input from a status operation.
            channel.observe(timeout=timeout if not close else 0)
        child.phase = channel.phase
        child.was_unknown = child.was_unknown or channel.was_unknown
        child.error = None
    except BaseException:
        _unknown(child, 'service_supervised_observation_unknown')
    return _status(child)


def observe_service(owner, *, timeout=0):
    return _observe(owner, timeout)


def close_service(owner, *, timeout=30):
    result = _observe(owner, timeout, close=True)
    child = owner._service_child
    if child is None or result['state'] != 'COMPLETED':
        return result
    try:
        if child.closure is None:
            owner.stop()
        if child.closure is not None and child.closure.state == 'STOPPED':
            owner.finish()
    except BaseException:
        # Lifecycle errors are bounded observations. Direct stop/finish callers
        # still receive an exception; the control protocol keeps original proof.
        if child.closure is None:
            _unknown(child, 'service_supervised_closure_preflight_unknown', blocked=True)
    return _status(child)
