"""One private Unix control endpoint for an original service volume owner.

The caller supplies the already RUNNING, exact ServiceVolumeSupervisor and a
fixed launch selection. A connection can name only start, close or observation;
it cannot supply launch configuration or acquire another owner. Explicit close
can complete the original child's and volume's ordered retirement. The original
main thread owns every lifecycle call. Client loss never cancels that call or
replays child input, volume stop or cleanup. Observation remains read-only.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import select
import socket
import stat
import struct
import threading
import time

import gateway_service_control as child_wire
import gateway_state_projection as projection
import gateway_supervised_service as launch
from service_volume_supervisor import ServiceVolumeSupervisor

PROTOCOL = 'alaz-supervisor-control-v1'
MAX_FRAME = 65536  # external frame INCLUDING the one newline
MAX_SECONDS = 60
MAX_MUTATIONS = 64
_IDS = re.compile('[a-f0-9]{32}')
_CODES = re.compile('[a-z][a-z0-9_]{0,95}')
_COMMANDS = frozenset(('start', 'close', 'status'))
_OWNER_FIELDS = frozenset(('pid', 'startTicks', 'token'))
_REQUEST_FIELDS = frozenset(('command', 'expectedOwner', 'protocol', 'requestId', 'serviceId'))
_NATIVE_FLAGS = ('transportRetired', 'runtimeRetired', 'apiSessionsRetired',
                 'consumerDetached', 'defaultExecutorJoined')
_COMPLETION_FLAGS = (*_NATIVE_FLAGS, 'profileLeaseReleased', 'childExited',
                     'volumeUnmounted', 'imageLeaseReleased', 'fenceRemovedAfterCleanup')
_STATES = frozenset(('NEW', 'STARTING', 'READY', 'DRAINING', 'UNKNOWN', 'CLOSED'))
_VOLUME_FLAGS = ('volumeUnmounted', 'fenceRemovedAfterCleanup', 'imageLeaseReleased')
_VOLUME_FIELDS = frozenset(('state', *_VOLUME_FLAGS))
_VOLUME_STATES = frozenset(('NOT_STARTED', 'STOPPING', 'STOPPED', 'FINISHING',
                          'CLOSED', 'UNKNOWN'))


class ServiceControlServerRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceControlServerRejected(reason)


def _seconds(value, *, zero=False):
    require(type(value) in (int, float) and math.isfinite(value)
            and (0 <= value if zero else 0 < value) and value <= MAX_SECONDS,
            'service_server_timeout_bound')
    return value


def _owner(value):
    require(type(value) is dict and set(value) == _OWNER_FIELDS,
            'service_server_owner_fields')
    require(type(value['pid']) is int and 0 < value['pid'] < 2**31
            and type(value['startTicks']) is int and 0 < value['startTicks'] <= 2**53 - 1
            and type(value['token']) is str and _IDS.fullmatch(value['token']) is not None,
            'service_server_owner_identity')
    return dict(value)


def validate_request(value):
    require(type(value) is dict and set(value) == _REQUEST_FIELDS,
            'service_server_request_fields')
    require(value['protocol'] == PROTOCOL and type(value['command']) is str
            and value['command'] in _COMMANDS, 'service_server_request_protocol')
    for name in ('requestId', 'serviceId'):
        require(type(value[name]) is str and _IDS.fullmatch(value[name]) is not None,
                'service_server_request_identity')
    return {**value, 'expectedOwner': _owner(value['expectedOwner'])}


def _compact(value, *, sorted_keys=False):
    return json.dumps(value, ensure_ascii=True, allow_nan=False,
                      separators=(',', ':'), sort_keys=sorted_keys).encode('ascii')


def decode_request(raw):
    """The client's compact ASCII object, one newline and complete write EOF.

    Object key order is preserved rather than required to be sorted: the Node
    client accepts owner objects in any insertion order. Values in this exact
    schema have the same compact representation in Python and JSON.stringify.
    """
    require(type(raw) is bytes and 3 <= len(raw) <= MAX_FRAME
            and raw.endswith(b'\n') and b'\n' not in raw[:-1],
            'service_server_request_frame')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'service_server_duplicate_field')
            value[key] = item
        return value
    def constant(_):
        raise ValueError()
    try:
        value = json.loads(raw[:-1].decode('ascii'), object_pairs_hook=pairs,
                           parse_constant=constant)
        require(_compact(value) == raw[:-1], 'service_server_request_not_compact')
        return validate_request(value)
    except ServiceControlServerRejected:
        raise
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        raise ServiceControlServerRejected('service_server_request_frame') from None


def _empty_completion():
    return {**{name: False for name in _COMPLETION_FLAGS}, 'physicalStoresClosed': 0}


def _new_view():
    return {'state': 'NEW', 'endpoint': None, 'completion': _empty_completion(), 'error': None}


def _volume_closure(value):
    require(type(value) is dict and set(value) == _VOLUME_FIELDS
            and type(value['state']) is str and value['state'] in _VOLUME_STATES
            and all(type(value[name]) is bool for name in _VOLUME_FLAGS),
            'service_server_volume_snapshot_fields')
    require(not value['fenceRemovedAfterCleanup'] or value['volumeUnmounted'],
            'service_server_volume_snapshot_order')
    require(not value['imageLeaseReleased'] or value['fenceRemovedAfterCleanup'],
            'service_server_volume_snapshot_order')
    if value['state'] in ('NOT_STARTED', 'STOPPING'):
        require(not any(value[name] for name in _VOLUME_FLAGS),
                'service_server_volume_snapshot_premature')
    if value['state'] in ('STOPPED', 'FINISHING'):
        require(value['volumeUnmounted'], 'service_server_volume_snapshot_stop_unconfirmed')
    if value['state'] == 'STOPPED':
        require(not value['fenceRemovedAfterCleanup'], 'service_server_volume_snapshot_premature')
    if value['state'] == 'CLOSED':
        require(all(value[name] for name in _VOLUME_FLAGS),
                'service_server_volume_snapshot_incomplete')
    else:
        require(not value['imageLeaseReleased'], 'service_server_volume_snapshot_terminal')
    return dict(value)


def _reason(exc):
    # Never format a foreign exception, request, path or caller credential.
    if type(exc) is not ServiceControlServerRejected:
        return 'service_server_unavailable'
    try:
        value = str(exc)
    except BaseException:
        return 'service_server_unavailable'
    return value if _CODES.fullmatch(value) is not None else 'service_server_unavailable'


class ServiceControlServer:
    """Bounded request memory and one original volume/server identity.

    bind() is explicit and never replaces an existing path. serve_one() accepts
    at most one client; timeout=0 is a nonblocking accept. Connection read/write
    deadlines are independent of the retained operation's bounded wait.
    """
    def __init__(self, volume, ipc, filesystem, record, *, socket_path, scratch,
                 instance_id, service_id, request_seconds=5, response_seconds=5,
                 operation_seconds=30, max_mutations=64):
        require(type(volume) is ServiceVolumeSupervisor, 'service_server_exact_volume')
        volume._owned()
        require(volume.stage == 'RUNNING' and not volume.spawn_uncertain
                and volume.worker is not None and volume.worker.poll() is None
                and getattr(volume, '_service_child', None) is None,
                'service_server_fresh_running_volume')
        require(getattr(volume, '_service_control_server', None) is None,
                'service_server_already_owned')
        self._request_seconds = _seconds(request_seconds)
        self._response_seconds = _seconds(response_seconds)
        self._operation_seconds = _seconds(operation_seconds)
        require(type(max_mutations) is int and 1 <= max_mutations <= MAX_MUTATIONS,
                'service_server_mutation_bound')
        self._max_mutations = max_mutations
        self._launch = launch.freeze_launch(ipc, filesystem, record, scratch=scratch,
                                           instance_id=instance_id, service_id=service_id)
        _, _, frozen, _, frozen_instance, frozen_service = launch.decode_launch(self._launch)
        require(frozen_service == service_id and frozen_instance == instance_id,
                'service_server_launch_identity')
        self._service_id, self._instance_id = frozen_service, frozen_instance
        self._epoch = frozen.state.epoch + 1
        self._volume = volume
        self._actor = (os.getpid(), threading.get_ident())
        require(volume.who == self._actor and threading.current_thread() is threading.main_thread(),
                'service_server_original_actor')
        self._owner = _owner({'pid': self._actor[0],
                              'startTicks': projection.process_start(self._actor[0]),
                              'token': volume.token})
        self._uid, self._gid = os.getuid(), os.getgid()
        value = os.fspath(socket_path)
        require(type(value) is str and value.startswith('/') and not value.startswith('//')
                and str(PurePosixPath(value)) == value and '..' not in PurePosixPath(value).parts
                and not any(c in value for c in '\0\r\n') and len(os.fsencode(value)) <= 107,
                'service_server_socket_path')
        self._path = Path(value)
        self._parent_identity = self._inspect_parent()
        self._socket_identity = None
        self._listener = None
        self._bind_attempted = self._listener_closed = False
        self._mutations = {}  # Never evicted: old IDs cannot become new effects.
        self._start_request = None
        self._request_dispatched = False
        self._serving = False
        self._view = _new_view()
        self._terminal_view = None  # Canonical detached bytes; never erased by reply loss.
        self._terminal_child = None
        # The volume's original retained ownership keeps this server and its
        # deduplication history alive even after a caller or socket disappears.
        volume._service_control_server = self

    def _actor_check(self):
        require(type(self._volume) is ServiceVolumeSupervisor
                and self._volume._service_control_server is self
                and self._actor == (os.getpid(), threading.get_ident()) == self._volume.who
                and threading.current_thread() is threading.main_thread()
                and self._volume.token == self._owner['token']
                and projection.process_start(self._owner['pid']) == self._owner['startTicks']
                and (os.getuid(), os.getgid()) == (self._uid, self._gid),
                'service_server_original_actor')

    def _owned(self):
        self._actor_check()
        # This gate retains the original typed closure proof after normal
        # finish has removed the fence/scope and released the lease. A CLOSED
        # label alone cannot substitute for the original owner's evidence.
        return _volume_closure(launch.check_service_owner(self._volume))

    def _inspect_parent(self):
        parent = self._path.parent
        require(parent.is_absolute() and parent.resolve(strict=True) == parent,
                'service_server_parent_path')
        value = parent.lstat()
        require(stat.S_ISDIR(value.st_mode) and not stat.S_ISLNK(value.st_mode)
                and (value.st_uid, value.st_gid) == (self._uid, self._gid)
                and stat.S_IMODE(value.st_mode) & 0o077 == 0,
                'service_server_private_parent')
        return value.st_dev, value.st_ino, value.st_uid, value.st_gid, stat.S_IMODE(value.st_mode)

    def _inspect_socket(self):
        require(self._inspect_parent() == self._parent_identity, 'service_server_parent_changed')
        value = self._path.lstat()
        require(stat.S_ISSOCK(value.st_mode) and not stat.S_ISLNK(value.st_mode)
                and (value.st_uid, value.st_gid) == (self._uid, self._gid)
                and stat.S_IMODE(value.st_mode) == 0o600 and value.st_nlink == 1,
                'service_server_socket_changed')
        return value.st_dev, value.st_ino, value.st_uid, value.st_gid, stat.S_IMODE(value.st_mode)

    def _bound(self):
        self._owned()
        require(self._listener is not None and not self._listener_closed
                and self._socket_identity is not None
                and self._inspect_socket() == self._socket_identity,
                'service_server_endpoint_changed')

    def bind(self):
        self._owned()
        require(not self._bind_attempted, 'service_server_bind_once')
        require(self._inspect_parent() == self._parent_identity, 'service_server_parent_changed')
        try:
            self._path.lstat()
        except FileNotFoundError:
            pass
        else:
            raise ServiceControlServerRejected('service_server_existing_socket_path')
        require(hasattr(socket, 'SO_PEERCRED') and hasattr(socket, 'AF_UNIX'),
                'service_server_linux_socket_required')
        self._bind_attempted = True
        try:
            self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._listener.set_inheritable(False)
            self._listener.bind(str(self._path))
            os.chmod(self._path, 0o600, follow_symlinks=False)
            self._socket_identity = self._inspect_socket()
            self._listener.listen(8)
            self._listener.setblocking(False)
            self._bound()
        except BaseException:
            # Retain a possibly bound descriptor/path. No adoption, unlink,
            # retry or lifecycle cleanup follows an uncertain bind.
            self._unknown('service_server_bind_unknown')
            raise ServiceControlServerRejected('service_server_bind_unknown') from None
        return self

    def connection(self):
        """Private caller configuration. The token is NOT a diagnostic field."""
        self._bound()
        return {'socketPath': str(self._path), 'serviceId': self._service_id,
                'owner': dict(self._owner)}

    def _unknown(self, reason):
        self._view = {**self._view, 'state': 'UNKNOWN', 'error': reason}

    def _snapshot(self, value):
        require(type(value) is dict and value.get('retryAllowed') is False
                and value.get('volumeMayClose') is False and value.get('fullD3BAccepted') is False,
                'service_server_snapshot_scope')
        closure = _volume_closure(value.get('volumeClosure'))
        require(closure == self._owned(), 'service_server_volume_snapshot_binding')
        phase = value.get('state')
        require(phase in ('NEW', 'SPAWNING', 'STARTING', 'READY', 'DRAINING',
                          'CLOSING', 'CHILD_CLOSED', 'COMPLETED', 'UNKNOWN'),
                'service_server_snapshot_state')
        if phase == 'NEW':
            require(self._volume._service_child is None and value.get('owner') is None,
                    'service_server_snapshot_new')
            require(closure['state'] == 'NOT_STARTED', 'service_server_snapshot_new_closure')
            self._view = _new_view()
            return
        require(self._volume._service_child is not None, 'service_server_snapshot_unowned')
        state = ('STARTING' if phase == 'SPAWNING' else
                 'DRAINING' if phase in ('CLOSING', 'CHILD_CLOSED', 'COMPLETED') else phase)
        completion = _empty_completion()
        owner = value.get('owner')
        endpoint = None
        if owner is not None:
            require(value.get('serviceId') == self._service_id
                    and type(value.get('pid')) is int and 0 < value['pid'] < 2**31
                    and type(value.get('epoch')) is int and value['epoch'] == self._epoch
                    and value.get('instanceId') == self._instance_id,
                    'service_server_snapshot_identity')
            owner = child_wire.validate_owner(owner, identity=(value.get('pid'), self._epoch, self._instance_id))
            require(type(value.get('childStartTicks')) is int and value['childStartTicks'] > 0,
                    'service_server_snapshot_process')
            closed = owner['close']
            completion.update({name: closed[name] for name in _NATIVE_FLAGS})
            completion['physicalStoresClosed'] = closed['physicalStoresClosed']
            completion['profileLeaseReleased'] = closed['callerLeaseReleased']
            if phase == 'COMPLETED':
                require(owner['state'] == 'CLOSED' and value.get('childExited') is True,
                        'service_server_snapshot_child_close')
                completion['childExited'] = True
            else:
                require(value.get('childExited') is False, 'service_server_snapshot_premature_exit')
            endpoint = owner['endpoint'] if not closed['transportRetired'] else None
            if state == 'READY':
                require(owner['state'] == 'READY' and endpoint is not None,
                        'service_server_snapshot_ready')
        else:
            require(state in ('STARTING', 'UNKNOWN'), 'service_server_snapshot_missing_owner')
        if closure['state'] != 'NOT_STARTED':
            require(phase == 'COMPLETED' and completion['childExited'],
                    'service_server_volume_before_child')
            completion.update({name: closure[name] for name in _VOLUME_FLAGS})
            state = ('CLOSED' if closure['state'] == 'CLOSED' else
                     'UNKNOWN' if closure['state'] == 'UNKNOWN' else 'DRAINING')
        if state == 'CLOSED':
            require(self._volume.stage == 'CLOSED' and endpoint is None
                    and all(completion[name] for name in _COMPLETION_FLAGS)
                    and completion['physicalStoresClosed'] == 3,
                    'service_server_volume_closed_unconfirmed')
        if state in ('NEW', 'STARTING', 'READY'):
            require(completion == _empty_completion(), 'service_server_snapshot_premature_cleanup')
        self._view = {'state': state, 'endpoint': endpoint, 'completion': completion,
                      'error': 'service_server_operation_unknown' if state == 'UNKNOWN'
                               else 'service_server_child_unavailable' if value.get('error') is not None else None}
        if state == 'CLOSED':
            require(self._view['error'] is None, 'service_server_closed_error')
            sealed = _compact(self._view, sorted_keys=True)
            require(self._terminal_view is None or (self._terminal_view == sealed
                    and self._terminal_child is self._volume._service_child),
                    'service_server_terminal_changed')
            self._terminal_child = self._volume._service_child
            self._terminal_view = sealed

    def _observe(self):
        try:
            closure = self._owned()
            if self._terminal_view is not None:
                require(closure['state'] == 'CLOSED'
                        and self._terminal_child is self._volume._service_child,
                        'service_server_terminal_owner_changed')
                self._view = json.loads(self._terminal_view)
            else:
                self._snapshot(self._volume.observe_service(timeout=0))
        except BaseException:
            self._unknown('service_server_observation_unknown')

    def _reply(self, request, *, error=None):
        state = self._view['state']
        require(state in _STATES, 'service_server_response_state')
        completion = dict(self._view['completion'])
        require(not completion['volumeUnmounted'] or completion['childExited'],
                'service_server_response_close_order')
        require(not completion['fenceRemovedAfterCleanup'] or completion['volumeUnmounted'],
                'service_server_response_close_order')
        require(not completion['imageLeaseReleased'] or completion['fenceRemovedAfterCleanup'],
                'service_server_response_close_order')
        if state == 'CLOSED':
            require(self._terminal_view is not None
                    and self._view == json.loads(self._terminal_view)
                    and all(completion[name] for name in _COMPLETION_FLAGS)
                    and completion['physicalStoresClosed'] == 3,
                    'service_server_response_close_unconfirmed')
        reason = self._view['error'] if error is None else error
        require(reason is None or type(reason) is str and _CODES.fullmatch(reason) is not None
                and self._owner['token'] not in reason, 'service_server_error_scope')
        endpoint = self._view['endpoint']
        return {'protocol': PROTOCOL, 'command': request['command'], 'requestId': request['requestId'],
                'serviceId': self._service_id, 'owner': dict(self._owner), 'state': state,
                'endpoint': endpoint, 'endpointScope': 'private-service-loopback' if endpoint else None,
                'completion': completion, 'retryAllowed': False, 'error': reason}

    def _dispatch(self, request):
        request = validate_request(request)
        # Before even read-only lifecycle dispatch, compare all original owner
        # fields. A reply comparison cannot substitute for this precondition.
        require(request['serviceId'] == self._service_id and request['expectedOwner'] == self._owner,
                'service_server_owner_precondition')
        self._bound()
        action, request_id = request['command'], request['requestId']
        if action == 'status':
            self._request_dispatched = True
            self._observe()
            return self._reply(request)
        previous = self._mutations.get(request_id)
        if previous is not None:
            if previous['command'] != action:
                return self._reply(request, error='service_server_request_conflict')
            if previous['dispatched']:
                self._request_dispatched = True
                self._observe()
            return self._reply(request, error=previous['error'])
        if len(self._mutations) >= self._max_mutations:
            return self._reply(request, error='service_server_request_capacity')
        # Reserve the caller's ID before a launch/close can partly take effect.
        entry = {'command': action, 'dispatched': False, 'error': None}
        self._mutations[request_id] = entry
        if action == 'start' and self._start_request is not None:
            entry['error'] = 'service_server_start_already_attempted'
            return self._reply(request, error=entry['error'])
        if action == 'close' and self._volume._service_child is None:
            entry['error'] = 'service_server_not_started'
            return self._reply(request, error=entry['error'])
        if action == 'start':
            self._start_request = request_id
        # Record actual lifecycle dispatch BEFORE the call. A subsequent reply
        # failure cannot erase it. Capacity/conflict refusals do not reach here.
        entry['dispatched'] = True
        self._request_dispatched = True
        try:
            if action == 'start':
                ipc, filesystem, record, scratch, instance, service_id = launch.decode_launch(self._launch)
                self._snapshot(self._volume.launch_service(ipc, filesystem, record, scratch=scratch,
                    instance_id=instance, service_id=service_id, timeout=self._operation_seconds))
            else:
                if self._terminal_view is not None:
                    self._observe()
                else:
                    self._snapshot(self._volume.close_service(timeout=self._operation_seconds))
        except BaseException:
            self._unknown('service_server_operation_unknown')
        return self._reply(request)

    def _peer(self, client):
        raw = client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
        pid, uid, gid = struct.unpack('3i', raw)
        require(0 < pid < 2**31 and (uid, gid) == (self._uid, self._gid),
                'service_server_peer_identity')

    @staticmethod
    def _ready(client, deadline, *, write=False):
        left = deadline - time.monotonic()
        require(left > 0, 'service_server_connection_timeout')
        ready = select.select([] if write else [client], [client] if write else [], [], left)
        require(bool(ready[1] if write else ready[0]), 'service_server_connection_timeout')

    def _read(self, client):
        end = time.monotonic() + self._request_seconds
        data = bytearray()
        while True:
            self._ready(client, end)
            try:
                raw = client.recv(min(4096, MAX_FRAME + 1 - len(data)))
            except BlockingIOError:
                continue
            if not raw:
                return decode_request(bytes(data))
            data.extend(raw)
            require(len(data) <= MAX_FRAME, 'service_server_request_bound')
            # Do not dispatch on a newline. EOF is required so an additional
            # frame cannot arrive after a lifecycle effect was already started.
            if b'\n' in data:
                require(data.count(b'\n') == 1 and data.endswith(b'\n'),
                        'service_server_multiple_requests')

    def _write(self, client, value):
        data = _compact(value, sorted_keys=True) + b'\n'
        require(len(data) <= MAX_FRAME, 'service_server_response_bound')
        end = time.monotonic() + self._response_seconds
        while data:
            self._ready(client, end, write=True)
            try:
                count = client.send(data)
            except BlockingIOError:
                continue
            require(count > 0, 'service_server_response_lost')
            data = data[count:]
        client.shutdown(socket.SHUT_WR)

    def serve_one(self, *, timeout=.25):
        """Accept one bounded request; return only sanitized server diagnostics."""
        # A foreign thread or a reentrant caller must not even reset the
        # original request's diagnostic marker or alter its retained view.
        self._actor_check()
        require(not self._serving, 'service_server_reentrant_request')
        _seconds(timeout, zero=True)
        self._serving = True
        try:
            return self._serve_connection(timeout)
        finally:
            self._serving = False

    def _serve_connection(self, timeout):
        self._request_dispatched = False
        try:
            self._bound()
            ready, _, _ = select.select([self._listener], [], [], timeout)
        except BaseException as exc:
            self._unknown('service_server_listener_unknown')
            raise ServiceControlServerRejected(_reason(exc)) from None
        if not ready:
            return {'state': 'IDLE', 'requestDispatched': False, 'ownerRetained': True}
        client = None
        try:
            client, _ = self._listener.accept()
            client.set_inheritable(False)
            client.setblocking(False)
            self._peer(client)
            request = self._read(client)
            reply = self._dispatch(request)
            self._write(client, reply)
            return {'state': 'REPLIED', 'requestDispatched': self._request_dispatched, 'ownerRetained': True}
        except BaseException as exc:
            # Closing this caller socket does not close or cancel the retained
            # operation. Diagnostics never contain request/exception contents.
            dispatched = self._request_dispatched
            if dispatched:
                # Losing an observation is not permission to undo or repeat
                # the operation; preserve its reserved ID and original owner.
                self._unknown('service_server_reply_unknown')
            return {'state': 'REPLY_LOST' if dispatched else 'REFUSED',
                    'reason': _reason(exc), 'requestDispatched': dispatched, 'ownerRetained': True}
        finally:
            if client is not None:
                try:
                    client.close()
                except BaseException:
                    pass

    def serve_forever(self):
        """Retain the same owner on listener or observer errors; never teardown."""
        self._actor_check()
        require(not self._serving, 'service_server_reentrant_request')
        while True:
            try:
                result = self.serve_one(timeout=.25)
                if result['state'] == 'IDLE' and self._volume._service_child is not None:
                    self._observe()
            except BaseException:
                self._unknown('service_server_listener_unknown')
                # No replacement listener/owner or cleanup. Avoid a busy loop
                # if the original descriptor/path is no longer usable.
                try:
                    time.sleep(.25)
                except BaseException:
                    pass

    def close_listener(self):
        """Explicit descriptor close only. The socket path and owner are retained."""
        self._actor_check()
        self._listener_closed = True
        if self._listener is not None:
            self._listener.close()
        return {'state': 'LISTENER_CLOSED', 'ownerRetained': True, 'volumeCleanupStarted': False}
