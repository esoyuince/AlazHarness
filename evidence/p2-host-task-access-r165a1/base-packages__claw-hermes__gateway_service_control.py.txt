"""Bounded control of one original borrowed service on its original event loop.

Only the fixed trusted child uses this private stdin/stdout protocol. A frame is
not an authentication token or proof of confinement. The parent must also check
its original process, generation, terminal exit and volume ownership. The final
frame proves the service/profile retirement only; it never releases the image.

The service's private network namespace is unchanged. This control channel does
not forward arbitrary HTTP, launch commands or grant a model/provider call.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import stat
import threading

from gateway_service_runtime import BorrowedServiceOwner

PROTOCOL = 'alaz-service-control-v1'
MAX_FRAME = 65536
MAX_SEQUENCE = 2**53 - 1
WRITE_SECONDS = 5
_attempt = None
_IDS = re.compile('[a-f0-9]{32}')
_STATES = frozenset(('NEW', 'STARTING', 'READY', 'DRAINING', 'CLOSING', 'UNKNOWN', 'CLOSED'))
_CLOSE_FLAGS = ('transportRetired', 'runtimeRetired', 'apiSessionsRetired',
                'consumerDetached', 'defaultExecutorJoined')


class ServiceControlRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceControlRejected(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _copy(value):
    return json.loads(canonical(value))


def _service_id(value):
    require(type(value) is str and _IDS.fullmatch(value) is not None,
            'service_control_service_id')
    return value


def request_id(service_id, sequence):
    """A sequence-bound internal ID; old IDs cannot name a new operation."""
    _service_id(service_id)
    require(type(sequence) is int and 1 <= sequence <= MAX_SEQUENCE,
            'service_control_sequence')
    return hashlib.sha256((service_id + ':' + str(sequence)).encode('ascii')).hexdigest()[:32]


def validate_command(value, *, service_id=None):
    require(type(value) is dict and set(value) ==
            {'protocol', 'serviceId', 'sequence', 'requestId', 'action'},
            'service_control_command_fields')
    require(value['protocol'] == PROTOCOL, 'service_control_protocol')
    sid = _service_id(value['serviceId'])
    require(service_id is None or sid == service_id, 'service_control_other_service')
    require(type(value['requestId']) is str and
            value['requestId'] == request_id(sid, value['sequence']),
            'service_control_request_binding')
    require(type(value['action']) is str and value['action'] in ('status', 'drain', 'close'),
            'service_control_action')
    return _copy(value)


def validate_owner(value, *, identity=None, closed=False):
    """Validate the entire native service receipt, never a descriptor label."""
    keys = {'protocol', 'state', 'pid', 'epoch', 'instanceId', 'endpoint',
            'serviceStarted', 'serviceReady', 'serviceClosed', 'admissionOpen',
            'close', 'reason', 'admissionSealReason', 'retryAllowed',
            'nativeStoresOwnedHere', 'imageLeaseOwnedHere', 'fullD3BAccepted'}
    require(type(value) is dict and set(value) == keys, 'service_control_owner_fields')
    require(value['protocol'] == 'alaz-borrowed-service-v1'
            and type(value['state']) is str and value['state'] in _STATES
            and type(value['pid']) is int and 0 < value['pid'] < 2**31,
            'service_control_owner_identity')
    epoch, instance = value['epoch'], value['instanceId']
    require((epoch is None and instance is None) or
            (type(epoch) is int and 0 < epoch < 2**63 and type(instance) is str
             and re.fullmatch('[A-Za-z0-9._-]{1,128}', instance) is not None),
            'service_control_owner_generation')
    if identity is not None:
        require(type(identity) is tuple and len(identity) == 3 and
                (value['pid'], epoch, instance) == identity,
                'service_control_owner_changed')
    endpoint = value['endpoint']
    match = (re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})', endpoint)
             if type(endpoint) is str else None)
    require(endpoint is None or match is not None and 1 <= int(match[1]) <= 65535,
            'service_control_owner_endpoint')
    for name in ('serviceStarted', 'serviceReady', 'serviceClosed', 'admissionOpen'):
        require(type(value[name]) is bool, 'service_control_owner_flags')
    require(value['serviceReady'] is (value['state'] == 'READY') and
            value['admissionOpen'] is (value['state'] == 'READY') and
            value['serviceClosed'] is (value['state'] == 'CLOSED'),
            'service_control_owner_state')
    require(value['serviceStarted'] is (endpoint is not None),
            'service_control_owner_listener')
    if value['state'] in ('READY', 'DRAINING', 'CLOSING', 'CLOSED'):
        require(epoch is not None and value['serviceStarted'],
                'service_control_owner_not_started')
    for name in ('retryAllowed', 'nativeStoresOwnedHere', 'imageLeaseOwnedHere', 'fullD3BAccepted'):
        require(value[name] is False, 'service_control_owner_scope')
    for name in ('reason', 'admissionSealReason'):
        require(value[name] is None or type(value[name]) is str and
                re.fullmatch('[a-z][a-z0-9_]{0,95}', value[name]) is not None,
                'service_control_owner_reason')
    close = value['close']
    require(type(close) is dict and set(close) == set(_CLOSE_FLAGS) |
            {'physicalStoresClosed', 'callerLeaseReleased', 'imageLeaseReleasedHere'},
            'service_control_close_fields')
    require(all(type(close[name]) is bool for name in (*_CLOSE_FLAGS, 'callerLeaseReleased'))
            and close['imageLeaseReleasedHere'] is False
            and type(close['physicalStoresClosed']) is int
            and close['physicalStoresClosed'] in (0, 3), 'service_control_close_scope')
    ordered = [close[name] for name in _CLOSE_FLAGS] + [
        close['physicalStoresClosed'] == 3, close['callerLeaseReleased']]
    require(not any(not before and after for before, after in zip(ordered, ordered[1:])),
            'service_control_close_order')
    if value['state'] in ('NEW', 'STARTING', 'READY', 'DRAINING'):
        require(not any(ordered), 'service_control_premature_retirement')
    if value['state'] == 'CLOSED' or closed:
        require(value['state'] == 'CLOSED' and all(ordered)
                and value['reason'] is None and value['admissionSealReason'] is None,
                'service_control_close_unconfirmed')
    return _copy(value)


def validate_frame(value, *, service_id=None, identity=None):
    require(type(value) is dict and set(value) ==
            {'protocol', 'type', 'serviceId', 'sequence', 'requestId', 'owner'},
            'service_control_frame_fields')
    require(value['protocol'] == PROTOCOL and type(value['type']) is str
            and value['type'] in ('ready', 'reply', 'final'), 'service_control_frame_type')
    sid = _service_id(value['serviceId'])
    require(service_id is None or service_id == sid, 'service_control_other_service')
    if value['type'] == 'ready':
        require(type(value['sequence']) is int and value['sequence'] == 0
                and value['requestId'] is None, 'service_control_ready_binding')
    else:
        require(value['requestId'] == request_id(sid, value['sequence']),
                'service_control_request_binding')
    owner = validate_owner(value['owner'], identity=identity, closed=value['type'] == 'final')
    if value['type'] == 'ready':
        require(owner['state'] == 'READY', 'service_control_ready_unconfirmed')
    return _copy(value)


def decode(raw):
    """One canonical bounded ASCII frame, excluding its newline delimiter."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_FRAME, 'service_control_frame_bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'service_control_duplicate_field')
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode('ascii'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        require(canonical(value) == raw, 'service_control_frame_not_canonical')
        return value
    except ServiceControlRejected:
        raise
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        raise ServiceControlRejected('service_control_frame_invalid') from None


class FDChannel:
    """Private pipe channel with bounded memory and no executor reader thread."""
    def __init__(self, loop, *, input_fd=0, output_fd=1):
        require(loop is asyncio.get_running_loop(), 'service_control_other_loop')
        require(type(input_fd) is int and type(output_fd) is int
                and input_fd >= 0 and output_fd >= 0 and input_fd != output_fd,
                'service_control_pipe_descriptors')
        require(stat.S_ISFIFO(os.fstat(input_fd).st_mode)
                and stat.S_ISFIFO(os.fstat(output_fd).st_mode), 'service_control_private_pipes_required')
        self.loop, self.input_fd, self.output_fd = loop, input_fd, output_fd
        self._buffer = bytearray()
        self._reading = self._writing = False
        os.set_blocking(input_fd, False)
        os.set_blocking(output_fd, False)

    async def _ready(self, fd, *, write=False, timeout=None):
        future = self.loop.create_future()
        def ready():
            if not future.done():
                future.set_result(None)
        add, remove = ((self.loop.add_writer, self.loop.remove_writer) if write else
                       (self.loop.add_reader, self.loop.remove_reader))
        add(fd, ready)
        try:
            if timeout is None:
                await future
            else:
                await asyncio.wait_for(future, timeout)
        except TimeoutError:
            raise ServiceControlRejected('service_control_output_timeout') from None
        finally:
            remove(fd)

    async def read(self):
        require(not self._reading, 'service_control_concurrent_read')
        self._reading = True
        try:
            while True:
                index = self._buffer.find(b'\n')
                if index >= 0:
                    raw = bytes(self._buffer[:index])
                    del self._buffer[:index + 1]
                    return decode(raw)
                require(len(self._buffer) <= MAX_FRAME, 'service_control_frame_bound')
                try:
                    data = os.read(self.input_fd, min(4096, MAX_FRAME + 1 - len(self._buffer)))
                except BlockingIOError:
                    await self._ready(self.input_fd)
                    continue
                require(bool(data), 'service_control_partial_eof' if self._buffer else 'service_control_eof')
                self._buffer.extend(data)
        finally:
            self._reading = False

    async def write(self, frame):
        require(not self._writing, 'service_control_concurrent_write')
        raw = canonical(frame)
        require(0 < len(raw) <= MAX_FRAME, 'service_control_frame_bound')
        self._writing = True
        try:
            data = raw + b'\n'
            end = self.loop.time() + WRITE_SECONDS
            while data:
                require(self.loop.time() < end, 'service_control_output_timeout')
                try:
                    count = os.write(self.output_fd, data)
                    require(count > 0, 'service_control_output_lost')
                    data = data[count:]
                except BlockingIOError:
                    await self._ready(self.output_fd, write=True, timeout=max(0, end - self.loop.time()))
                except (BrokenPipeError, OSError):
                    raise ServiceControlRejected('service_control_output_lost') from None
        finally:
            self._writing = False


class ServiceControl:
    """One native owner, one active command and exactly one retained reply.

    Awaiter cancellation does not cancel owned native work. A new sequence may
    retry a known pre-effect DRAINING close; an identical frame only observes the
    original task/reply. Unknown outcomes never cause an automatic close attempt.
    """
    def __init__(self, service, service_id):
        require(type(service) is BorrowedServiceOwner, 'service_control_exact_owner_required')
        require(service._state == 'NEW', 'service_control_fresh_owner_required')
        require(getattr(service, '_control_owner', None) is None, 'service_control_already_owned')
        self.service, self.service_id = service, _service_id(service_id)
        self.loop = asyncio.get_running_loop()
        self.actor = (os.getpid(), threading.get_ident())
        self.identity = None
        self._start_task = self._last_task = self._driver_task = None
        self._last_command = None
        self._last_sequence = 0
        self._observers = set()
        self._fenced = False
        self.reason = None
        self.final = None
        service._control_owner = self

    def _owned(self):
        require(self.actor == (os.getpid(), threading.get_ident())
                and asyncio.get_running_loop() is self.loop,
                'service_control_other_actor_or_loop')
        require(self.service._control_owner is self, 'service_control_owner_changed')

    @staticmethod
    def _retrieve(task):
        if not task.cancelled():
            task.exception()

    async def _observe(self, task):
        observer = asyncio.current_task()
        self._observers.add(observer)
        try:
            return _copy(await asyncio.shield(task))
        finally:
            self._observers.discard(observer)

    def _frame(self, kind, owner, command=None):
        value = {'protocol': PROTOCOL, 'type': kind, 'serviceId': self.service_id,
                 'sequence': 0 if command is None else command['sequence'],
                 'requestId': None if command is None else command['requestId'], 'owner': owner}
        return validate_frame(value, service_id=self.service_id, identity=self.identity)

    async def start(self, gateway_config, api_config):
        self._owned()
        require(self._start_task is None and not self._fenced, 'service_control_start_already_attempted')
        self._start_task = self.loop.create_task(self._start(gateway_config, api_config))
        self._start_task.add_done_callback(self._retrieve)
        return await self._observe(self._start_task)

    async def _start(self, gateway_config, api_config):
        try:
            owner = validate_owner(await self.service.start(gateway_config, api_config))
            require(owner['pid'] == os.getpid() and owner['state'] == 'READY',
                    'service_control_start_unconfirmed')
            self.identity = (owner['pid'], owner['epoch'], owner['instanceId'])
            return self._frame('ready', owner)
        except BaseException:
            self.fence('service_control_start_unknown')
            raise

    async def handle(self, command):
        self._owned()
        command = validate_command(command, service_id=self.service_id)
        require(self.identity is not None, 'service_control_not_started')
        sequence = command['sequence']
        if sequence == self._last_sequence and self._last_command is not None:
            require(command == self._last_command, 'service_control_request_conflict')
            return await self._observe(self._last_task)
        require(sequence == self._last_sequence + 1, 'service_control_sequence_not_next')
        require(self.final is None and (self._last_task is None or self._last_task.done()),
                'service_control_command_busy_or_closed')
        require(not self._fenced or command['action'] == 'status', 'service_control_unknown_effects_retained')
        self._last_command, self._last_sequence = command, sequence
        self._last_task = self.loop.create_task(self._handle(command))
        self._last_task.add_done_callback(self._retrieve)
        return await self._observe(self._last_task)

    async def _handle(self, command):
        try:
            action = command['action']
            if action == 'status':
                owner = self.service.status()
            elif action == 'drain':
                owner = self.service.begin_drain()
            else:
                owner = await self.service.close_when_idle()
            owner = validate_owner(owner, identity=self.identity)
            if action == 'close' and owner['state'] == 'CLOSED':
                # The native close task has returned, so it is terminal now.
                # No control reader/executor task is spawned in the background.
                await asyncio.sleep(0)
                allowed = self._observers | {asyncio.current_task(), self._driver_task}
                require(not any(task not in allowed and not task.done()
                                for task in asyncio.all_tasks(self.loop)),
                        'service_control_loop_obligations_remain')
                self.final = self._frame('final', owner, command)
                return self.final
            return self._frame('reply', owner, command)
        except BaseException:
            self.fence('service_control_command_unknown')
            raise

    def fence(self, reason):
        """Seal admissions once; retain the owner, loop and all cleanup tasks."""
        self._owned()
        if self._fenced:
            return
        self._fenced = True
        self.reason = reason if re.fullmatch('[a-z][a-z0-9_]{0,95}', reason) else 'service_control_unknown'
        try:
            if self.service.status()['state'] == 'READY':
                self.service.begin_drain()
        except BaseException:
            # No additional retry or teardown follows an unknown seal effect.
            self.reason = 'service_control_admission_seal_unknown'

    async def drive(self, channel, gateway_config, api_config):
        self._owned()
        require(self._driver_task is None, 'service_control_driver_already_owned')
        self._driver_task = self.loop.create_task(self._drive(channel, gateway_config, api_config))
        self._driver_task.add_done_callback(self._retrieve)
        return await self._observe(self._driver_task)

    async def _drive(self, channel, gateway_config, api_config):
        try:
            await channel.write(await self.start(gateway_config, api_config))
            while True:
                command = await channel.read()
                frame = await self.handle(command)
                await channel.write(frame)
                if frame['type'] == 'final':
                    return frame
        except BaseException:
            self.fence('service_control_channel_unknown')
            # Keep the event loop alive after pipe/observer failure. This is
            # deliberately not asyncio.run cleanup, task cancellation or exit.
            await self.loop.create_future()


async def drive_service(service, service_id, gateway_config, api_config, *, channel=None):
    """Fixed child entry after original launch/confinement/configuration checks."""
    global _attempt
    require(_attempt is None, 'service_control_process_already_owned')
    _attempt = ServiceControl(service, service_id)
    channel = FDChannel(asyncio.get_running_loop()) if channel is None else channel
    return await _attempt.drive(channel, gateway_config, api_config)
