"""One fixed service child on the original service-volume owner.

The immutable launch plan is data, never mount or process authority. The exact
original supervisor, worker, lease, fence, namespace and Popen remain retained
through uncertain spawn or pipe results. Observation cannot send input. Child
completion is deliberately NOT permission to stop or release the volume.
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
    process: object = None
    pid: int | None = None
    start_ticks: int | None = None
    channel: ServiceChannel | None = None
    phase: str = 'SPAWNING'
    was_unknown: bool = False
    error: str | None = None
    blocked: bool = False


def _owner(owner):
    from service_volume_supervisor import ServiceVolumeSupervisor
    require(type(owner) is ServiceVolumeSupervisor and hasattr(owner, '_service_child'),
            'service_supervised_exact_owner')
    owner._owned()
    require(owner.stage == 'RUNNING' and not owner.spawn_uncertain
            and owner.worker is not None and owner.worker.poll() is None,
            'service_supervised_worker_not_running')


def _actor(owner):
    from service_volume_supervisor import ServiceVolumeSupervisor
    require(type(owner) is ServiceVolumeSupervisor and hasattr(owner, '_service_child'),
            'service_supervised_exact_owner')
    require(volume.actor() == owner.who, 'service_supervised_original_actor')


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


def _status(child=None):
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


def _check(child):
    owner = child.owner; binding = child.binding
    _owner(owner)
    require(owner._service_child is child and owner.who == child.actor
            and owner.pin is child.pin and owner.worker is child.worker
            and owner.token == binding.token and str(owner.scope) == binding.scope
            and owner.scope_id == binding.scope_identity and str(owner.target) == binding.mountpoint
            and owner.loop_number == binding.loop_number
            and hashlib.sha256(owner.fence_bytes).hexdigest() == binding.fence_sha256,
            'service_supervised_owner_changed')
    require(projection.process_start(binding.controller_pid) == binding.controller_start
            and child.worker.pid == binding.worker_pid,
            'service_supervised_controller_or_worker_changed')
    projection._live_root(binding.worker_pid, binding.worker_start)
    if child.process is None:
        return
    require(child.process.pid == child.pid and type(child.start_ticks) is int
            and child.start_ticks > 0, 'service_supervised_child_unconfirmed')
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
        child = _Child(owner, owner.who, owner.worker, owner.pin, binding, plan, payload,
                       service_id, frozen_record.state.epoch, instance_id)
        owner._service_child = child
        try:
            child.process = subprocess.Popen([PYTHON, '-I', '-B', str(ROOT / ENTRY)],
                cwd='/', env=dict(ENVIRONMENT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, pass_fds=(fd,), close_fds=True, bufsize=0)
            child.pid = child.process.pid
            child.start_ticks = projection.process_start(child.pid)
            child.channel = ServiceChannel(child.process, service_id=service_id,
                previous_epoch=frozen_record.state.epoch, instance_id=instance_id)
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
    return _observe(owner, timeout, close=True)
