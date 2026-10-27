"""Fixed service projection -> exec -> live receiver, separate from finite work.

Only a trusted, already joined supervisor child calls launch. Transfer records
are data, not authentication or proof of a kernel boundary. The original volume,
projection, profile and native owner checks remain authoritative. No executable,
factory, cleanup callback, provider choice or credential comes from this wire.
"""
from dataclasses import asdict
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import sys

import gateway_retained_launch as common
import gateway_service_handoff as handoff
import gateway_service_projection as mapping
import gateway_state_projection as state
import gateway_storage_mounts as mounts

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/usr/bin/python3.12'
ENTRY = 'scripts/run_service_projected.py'
WIRE_ENV = 'ALAZ_SERVICE_WIRE'
CONTEXT_ENV = 'ALAZ_SERVICE_CONTEXT'
PROTOCOL = 'alaz-projected-service-exec-context-v1'
MAX_CONTEXT = 16384
ServiceLaunchRejected = common.ProjectedLaunchRejected
require = common.require
_bytes = common._bytes
_instance = common._instance
_namespaces = common._namespaces
_live = common._live
_mount = common._mount
_mount_shape = common._mount_shape


def _service_id(value):
    require(type(value) is str and re.fullmatch('[a-f0-9]{32}', value) is not None,
            'service_projected_service_id')
    return value


def _environment(wire, context):
    scratch = context['scratch']
    return {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
            'HOME': handoff.TARGET, 'HERMES_HOME': handoff.TARGET,
            'TMPDIR': scratch, 'TMP': scratch, 'TEMP': scratch,
            WIRE_ENV: wire.decode('ascii'),
            CONTEXT_ENV: _bytes(context).decode('ascii')}


def launch(value, filesystem, binding, record, *, scratch, instance_id, service_id):
    """Project once and exec the fixed receiver; never return after confinement.

    The caller must treat any exception as an unresolved dedicated child, not
    return to host work or retry projection. No lease or native store opens here.
    """
    require(type(record) is handoff.ServiceStartup, 'service_projected_record_type')
    handoff.validate(record, expected_home=record.service.home)
    _instance(instance_id, record.state.instance_id)
    _service_id(service_id)
    view, fs = state.gp.validate(value, filesystem)
    principal = view['principalContract']
    mapping.ServiceProjection(binding, record.service, principal)
    scratch = handoff.common._home(scratch)
    require(scratch != '/dev/null' and scratch in fs['writable'],
            'service_projected_scratch_not_exported')
    target = str(ROOT / ENTRY)
    for path in (str(ROOT), PYTHON, target):
        handoff.common._home(path)
        require(any(PurePosixPath(path).is_relative_to(root) for root in fs['readonly']),
                'service_projected_entry_not_readonly')
    projected = state.enter(view, fs, binding, observe_self_mount=True,
        observe_self_identity=True, profile_layout=state.NATIVE_SERVICE_LAYOUT,
        service_profile=record.service)
    wire = handoff.encode_projected(projected, record.state, record.response)
    received = handoff.decode_projected(wire)
    namespaces = _namespaces()
    _live(principal, namespaces, os.getpid())
    expected = _mount()
    _mount_shape(expected, received.service)
    context = {'protocol': PROTOCOL, 'pid': os.getpid(), 'principal': principal,
        'namespaces': namespaces, 'mount': asdict(expected), 'scratch': scratch,
        'instanceId': instance_id, 'serviceId': service_id,
        'wireSha256': hashlib.sha256(wire).hexdigest()}
    require(len(_bytes(context)) <= MAX_CONTEXT, 'service_projected_context_size')
    # Keep standard control pipes, while inheriting no ambient host environment.
    # The executable and argv are fixed in reviewed code, never in transfer JSON.
    os.execve(PYTHON, [PYTHON, '-I', '-B', target], _environment(wire, context))
    raise ServiceLaunchRejected('service_projected_exec_returned')


def receive(environment):
    """Recheck transfer, actual inherited confinement and selected profile.

    No lease, SQL or native import is permitted before these checks complete.
    The final profile snapshot is read-only; NativeStoreStartup still performs
    its original profile/config/source checks under the subsequently held lease.
    """
    try:
        require(sys.platform == 'linux' and sys.flags.isolated == 1
                and sys.dont_write_bytecode and sys.executable == PYTHON,
                'service_projected_fixed_interpreter')
        fields = {'PATH', 'LANG', 'HOME', 'HERMES_HOME', 'TMPDIR', 'TMP', 'TEMP',
                  WIRE_ENV, CONTEXT_ENV}
        require(type(environment) is dict and set(environment) == fields,
                'service_projected_environment_fields')
        raw = environment[WIRE_ENV]
        context_raw = environment[CONTEXT_ENV]
        require(type(raw) is str and 0 < len(raw) <= handoff.MAX_BYTES
                and type(context_raw) is str and 0 < len(context_raw) <= MAX_CONTEXT,
                'service_projected_transfer_bounds')
        wire = raw.encode('ascii')
        record = handoff.decode_projected(wire)
        context = handoff.common._json(context_raw)
        require(type(context) is dict and set(context) == {
            'protocol', 'pid', 'principal', 'namespaces', 'mount', 'scratch',
            'instanceId', 'serviceId', 'wireSha256'}, 'service_projected_context_fields')
        require(_bytes(context).decode('ascii') == context_raw
                and context['protocol'] == PROTOCOL, 'service_projected_context_canonical')
        require(type(context['pid']) is int and context['pid'] == os.getpid()
                and context['wireSha256'] == hashlib.sha256(wire).hexdigest(),
                'service_projected_context_binding')
        _instance(context['instanceId'], record.state.instance_id)
        _service_id(context['serviceId'])
        principal = state.gp.hp.policy(context['principal'])
        namespaces = context['namespaces']
        require(type(namespaces) is dict and set(namespaces) == {'user', 'mnt', 'net', 'ipc'}
                and all(type(v) is str and re.fullmatch(k + r':\[[0-9]{1,20}\]', v)
                        for k, v in namespaces.items()), 'service_projected_context_namespaces')
        scratch = handoff.common._home(context['scratch'])
        require(scratch not in ('/', '/dev/null')
                and not PurePosixPath(scratch).is_relative_to(handoff.TARGET)
                and not PurePosixPath(handoff.TARGET).is_relative_to(scratch),
                'service_projected_context_scratch')
        require(environment == _environment(wire, context), 'service_projected_environment_mismatch')
        mount = context['mount']
        require(type(mount) is dict and set(mount) == {
            'mount_id', 'device', 'root', 'mount_point', 'filesystem'}
            and type(mount['device']) is list and len(mount['device']) == 2,
            'service_projected_context_mount')
        expected = mounts.ExpectedMount(**{**mount, 'device': tuple(mount['device'])})
        _mount_shape(expected, record.service)
        _live(principal, namespaces, context['pid'])
        require(_mount() == expected, 'service_projected_mount_changed_after_exec')
        handoff.profile.inspect_profile(Path(handoff.TARGET),
            uid=principal['gatewayUid'], gid=principal['socketGroupGid'],
            device=record.service.home_identity[0], expectation=record.service)
        return record, expected, context['instanceId'], context['serviceId']
    except ServiceLaunchRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError,
            RecursionError, UnicodeError, OSError):
        raise ServiceLaunchRejected('service_projected_target_invalid') from None


def target_main():
    """Only the fixed verified receiver can enter the fixed service factory."""
    record, expected, instance, service_id = receive(dict(os.environ))
    from gateway_service_factory import execute
    return execute(record, expected, instance, service_id)
