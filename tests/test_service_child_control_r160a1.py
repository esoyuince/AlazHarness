"""Control/pipe behavior; native lifecycle methods are explicit doubles.

Real OS pipes/event-loop callbacks exercise framing and disconnect handling.
These tests do not qualify a mounted installation, native HTTP or model call.
"""
import asyncio
import copy
import os
from pathlib import Path
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_service_control as control
from gateway_service_runtime import BorrowedServiceOwner

SID = 'a' * 32


def owner_receipt(state='READY'):
    return {'protocol': 'alaz-borrowed-service-v1', 'state': state, 'pid': os.getpid(),
        'epoch': 2, 'instanceId': 'owned-service-2', 'endpoint': 'http://127.0.0.1:45550',
        'serviceStarted': True, 'serviceReady': state == 'READY',
        'serviceClosed': state == 'CLOSED', 'admissionOpen': state == 'READY',
        'close': {**{name: state == 'CLOSED' for name in control._CLOSE_FLAGS},
            'physicalStoresClosed': 3 if state == 'CLOSED' else 0,
            'callerLeaseReleased': state == 'CLOSED', 'imageLeaseReleasedHere': False},
        'reason': None, 'admissionSealReason': None, 'retryAllowed': False,
        'nativeStoresOwnedHere': False, 'imageLeaseOwnedHere': False,
        'fullD3BAccepted': False}


def command(sequence=1, action='status'):
    return {'protocol': control.PROTOCOL, 'serviceId': SID, 'sequence': sequence,
            'requestId': control.request_id(SID, sequence), 'action': action}


def frame(kind='ready', state='READY', sequence=0):
    return {'protocol': control.PROTOCOL, 'type': kind, 'serviceId': SID,
            'sequence': sequence,
            'requestId': control.request_id(SID, sequence) if sequence else None,
            'owner': owner_receipt(state)}


class ProtocolTests(unittest.TestCase):
    def test_request_id_binds_internal_service_and_sequence(self):
        self.assertEqual(control.request_id(SID, 1), control.request_id(SID, 1))
        self.assertNotEqual(control.request_id(SID, 1), control.request_id(SID, 2))
        self.assertNotEqual(control.request_id(SID, 1), control.request_id('b' * 32, 1))
        old = command();old['sequence'] = 2
        with self.assertRaisesRegex(control.ServiceControlRejected, 'request_binding'):
            control.validate_command(old)

    def test_sequence_and_id_bounds_fail_before_any_control(self):
        for value in (True, False, None, 0, -1, 1.0, '1', control.MAX_SEQUENCE + 1):
            with self.subTest(value=value), self.assertRaises(control.ServiceControlRejected):
                control.request_id(SID, value)
        for value in ('', 'g' * 32, 'a' * 31, 'a' * 33, 'A' * 32, None):
            with self.subTest(value=value), self.assertRaises(control.ServiceControlRejected):
                control.request_id(value, 1)
        control.validate_command(command(control.MAX_SEQUENCE))

    def test_command_exact_schema_action_and_service(self):
        for change in ({'argv': ['sh']}, {'action': 'task'}, {'protocol': 'other'},
                       {'action': True}, {'requestId': 'b' * 32}):
            with self.subTest(change=change), self.assertRaises(control.ServiceControlRejected):
                control.validate_command(command() | change)
        with self.assertRaisesRegex(control.ServiceControlRejected, 'other_service'):
            control.validate_command(command(), service_id='b' * 32)

    def test_decode_requires_canonical_ascii_unique_fields(self):
        value = command()
        self.assertEqual(control.decode(control.canonical(value)), value)
        bad = [b'', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.0, "y":2}',
               b'\xff', b'{"x":', b'{}\n', b'0' * (control.MAX_FRAME + 1)]
        for raw in bad:
            with self.subTest(raw=raw[:50]), self.assertRaises(control.ServiceControlRejected):
                control.decode(raw)

    def test_owner_flags_and_scope_are_validated(self):
        baseline = owner_receipt()
        control.validate_owner(baseline)
        changes = [{'pid': True}, {'epoch': True}, {'instanceId': None},
            {'endpoint': 'http://localhost:45550'}, {'endpoint': 'http://127.0.0.1:65536'},
            {'endpoint': 'http://127.0.0.1:45550/path'}, {'serviceReady': False},
            {'admissionOpen': False}, {'serviceStarted': False}, {'imageLeaseOwnedHere': True},
            {'nativeStoresOwnedHere': True}, {'retryAllowed': True}, {'fullD3BAccepted': True},
            {'reason': 'exception includes a secret'}, {'extra': False}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(control.ServiceControlRejected):
                control.validate_owner(baseline | change)

    def test_identity_drift_cannot_reuse_ready(self):
        value = owner_receipt()
        identity = (value['pid'], value['epoch'], value['instanceId'])
        control.validate_owner(value, identity=identity)
        for change in ({'pid': value['pid'] + 1}, {'epoch': value['epoch'] + 1},
                       {'instanceId': 'replacement'}):
            with self.subTest(change=change), self.assertRaisesRegex(
                    control.ServiceControlRejected, 'owner_changed'):
                control.validate_owner(value | change, identity=identity)

    def test_closed_requires_every_original_retirement_and_no_image_release(self):
        value = owner_receipt('CLOSED')
        control.validate_owner(value, closed=True)
        for name in control._CLOSE_FLAGS + ('callerLeaseReleased',):
            broken = copy.deepcopy(value);broken['close'][name] = False
            with self.subTest(name=name), self.assertRaises(control.ServiceControlRejected):
                control.validate_owner(broken, closed=True)
        for change in ({'physicalStoresClosed': 2}, {'physicalStoresClosed': True},
                       {'imageLeaseReleasedHere': True}, {'extra': False}):
            broken = copy.deepcopy(value);broken['close'].update(change)
            with self.subTest(change=change), self.assertRaises(control.ServiceControlRejected):
                control.validate_owner(broken, closed=True)

    def test_partial_ordered_close_is_not_terminal(self):
        value = owner_receipt('CLOSING')
        value['close']['transportRetired'] = True
        control.validate_owner(value)
        with self.assertRaises(control.ServiceControlRejected):
            control.validate_owner(value, closed=True)
        value['close']['consumerDetached'] = True
        with self.assertRaisesRegex(control.ServiceControlRejected, 'close_order'):
            control.validate_owner(value)

    def test_ready_and_final_frames_cannot_be_relabelled(self):
        control.validate_frame(frame())
        control.validate_frame(frame('final', 'CLOSED', 1))
        bad = [frame('ready', 'DRAINING'), frame('final', 'DRAINING', 1),
               frame('reply', 'READY', 0), frame() | {'sequence': True},
               frame() | {'requestId': 'b' * 32}, frame() | {'extra': 1}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(control.ServiceControlRejected):
                control.validate_frame(value)


class ServiceDouble:
    """Exact wrapper class with only its native lifecycle methods doubled."""
    def __init__(self):
        self.service = object.__new__(BorrowedServiceOwner)
        self.service._state = 'NEW'
        self.value = owner_receipt()
        self.calls = []
        self.busy = False
        self.close_error = False
        self.start_release = self.close_release = None
        self.start_entered, self.close_entered = asyncio.Event(), asyncio.Event()
        async def start(*args):
            self.calls.append('start');self.start_entered.set()
            if self.start_release is not None:
                await self.start_release.wait()
            self.service._state = 'READY'
            return copy.deepcopy(self.value)
        def status():
            return copy.deepcopy(self.value)
        def drain():
            self.calls.append('drain')
            self.value = owner_receipt('DRAINING');self.service._state = 'DRAINING'
            return status()
        async def close():
            self.calls.append('close');self.close_entered.set()
            if self.close_release is not None:
                await self.close_release.wait()
            if self.close_error:
                self.value = owner_receipt('UNKNOWN');self.service._state = 'UNKNOWN'
                raise RuntimeError('native_cleanup_unknown')
            self.value = owner_receipt('DRAINING' if self.busy else 'CLOSED')
            self.service._state = self.value['state']
            return status()
        self.service.start = start;self.service.status = status
        self.service.begin_drain = drain;self.service.close_when_idle = close


class ControlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = ServiceDouble()
        self.control = control.ServiceControl(self.f.service, SID)

    async def start(self):
        return await self.control.start(object(), object())

    async def test_start_is_once_and_ready_uses_original_identity(self):
        result = await self.start()
        self.assertEqual(result, frame())
        with self.assertRaisesRegex(control.ServiceControlRejected, 'already_attempted'):
            await self.start()
        with self.assertRaises(control.ServiceControlRejected):
            control.ServiceControl(self.f.service, SID)
        self.assertEqual(self.f.calls, ['start'])

    async def test_exact_owner_required_before_reserved_control(self):
        with self.assertRaisesRegex(control.ServiceControlRejected, 'exact_owner'):
            control.ServiceControl(object(), SID)

    async def test_ready_status_drain_then_known_busy_and_new_close(self):
        await self.start()
        self.assertEqual((await self.control.handle(command()))['owner']['state'], 'READY')
        self.assertEqual((await self.control.handle(command(2, 'drain')))['owner']['state'], 'DRAINING')
        self.f.busy = True
        busy = await self.control.handle(command(3, 'close'))
        self.assertEqual((busy['type'], busy['owner']['state']), ('reply', 'DRAINING'))
        self.f.busy = False
        self.assertEqual(await self.control.handle(command(3, 'close')), busy)
        self.assertEqual(self.f.calls.count('close'), 1)
        final = await self.control.handle(command(4, 'close'))
        self.assertEqual((final['type'], final['owner']['state']), ('final', 'CLOSED'))
        self.assertFalse(final['owner']['close']['imageLeaseReleasedHere'])
        self.assertEqual(await self.control.handle(command(4, 'close')), final)
        self.assertEqual(self.f.calls.count('close'), 2)
        with self.assertRaises(control.ServiceControlRejected):
            await self.control.handle(command(5))

    async def test_changed_old_gap_and_new_id_replay_fail_without_effect(self):
        await self.start()
        await self.control.handle(command())
        before = list(self.f.calls)
        for value in (command(1, 'close'), command(3, 'close'),
                      command(2, 'close') | {'requestId': command(1)['requestId']}):
            with self.subTest(value=value), self.assertRaises(control.ServiceControlRejected):
                await self.control.handle(value)
            self.assertEqual(self.f.calls, before)
        await self.control.handle(command(2))
        with self.assertRaises(control.ServiceControlRejected):
            await self.control.handle(command(1))
        self.assertEqual(self.f.calls, before)

    async def test_cancelled_close_observer_retains_one_native_operation(self):
        await self.start()
        self.f.close_release = asyncio.Event()
        observer = asyncio.create_task(self.control.handle(command(1, 'close')))
        await self.f.close_entered.wait()
        task = self.control._last_task
        observer.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await observer
        self.assertFalse(task.done())
        self.f.close_release.set()
        final = await self.control.handle(command(1, 'close'))
        self.assertEqual(final['type'], 'final')
        self.assertIs(self.control._last_task, task)
        self.assertEqual(self.f.calls.count('close'), 1)

    async def test_cancelled_start_observer_never_starts_again(self):
        self.f.start_release = asyncio.Event()
        observer = asyncio.create_task(self.start())
        await self.f.start_entered.wait()
        task = self.control._start_task
        observer.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await observer
        self.assertFalse(task.done())
        with self.assertRaises(control.ServiceControlRejected):
            await self.start()
        self.f.start_release.set()
        ready = await task
        self.assertEqual(ready['type'], 'ready')
        self.assertEqual(self.f.calls, ['start'])

    async def test_unknown_close_never_reexecutes_or_cleans_up(self):
        await self.start();self.f.close_error = True
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'cleanup_unknown'):
                await self.control.handle(command(1, 'close'))
        with self.assertRaisesRegex(control.ServiceControlRejected, 'unknown_effects'):
            await self.control.handle(command(2, 'close'))
        self.assertEqual(self.f.calls.count('close'), 1)
        self.assertIsNone(self.control.final)
        result = await self.control.handle(command(2))
        self.assertEqual(result['owner']['state'], 'UNKNOWN')

    async def test_identity_loss_is_fenced_without_false_reply(self):
        await self.start()
        self.f.value['epoch'] += 1
        with self.assertRaisesRegex(control.ServiceControlRejected, 'owner_changed'):
            await self.control.handle(command())
        self.assertTrue(self.control._fenced)
        self.assertIsNone(self.control.final)

    async def test_unretired_loop_task_prevents_final_even_with_closed_owner(self):
        await self.start()
        blocker = asyncio.create_task(asyncio.Event().wait())
        try:
            with self.assertRaisesRegex(control.ServiceControlRejected, 'loop_obligations'):
                await self.control.handle(command(1, 'close'))
            self.assertIsNone(self.control.final)
            self.assertFalse(blocker.cancelled())
        finally:
            blocker.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await blocker

    async def test_cached_reply_is_copied_and_only_latest_command_retained(self):
        await self.start()
        for sequence in range(1, 80):
            result = await self.control.handle(command(sequence))
            result['owner']['epoch'] = 999
            self.assertEqual((await self.control.handle(command(sequence)))['owner']['epoch'], 2)
        self.assertEqual(self.control._last_sequence, 79)
        self.assertEqual(self.control._last_command, command(79))
        self.assertFalse(self.control._observers)
        self.assertEqual(self.f.calls, ['start'])

    async def test_channel_eof_seals_and_retains_driver(self):
        class Channel:
            def __init__(self):self.frames = []
            async def write(self, value):self.frames.append(value)
            async def read(self):raise control.ServiceControlRejected('service_control_eof')
        channel = Channel()
        observer = asyncio.create_task(self.control.drive(channel, object(), object()))
        for _ in range(30):
            if self.control._fenced:break
            await asyncio.sleep(0)
        self.assertTrue(self.control._fenced)
        self.assertFalse(self.control._driver_task.done())
        self.assertEqual(self.f.calls, ['start', 'drain'])
        self.assertEqual([f['type'] for f in channel.frames], ['ready'])
        observer.cancel()
        with self.assertRaises(asyncio.CancelledError):await observer
        self.assertFalse(self.control._driver_task.done())
        # Test-only teardown of the retained double. Product has no such cleanup.
        self.control._driver_task.cancel()
        with self.assertRaises(asyncio.CancelledError):await self.control._driver_task

    async def test_output_loss_never_reports_final_or_releases_owner(self):
        class Channel:
            async def write(self, value):raise BrokenPipeError()
            async def read(self):raise AssertionError('must not read after failed ready')
        observer = asyncio.create_task(self.control.drive(Channel(), object(), object()))
        for _ in range(30):
            if self.control._fenced:break
            await asyncio.sleep(0)
        self.assertTrue(self.control._fenced)
        self.assertEqual(self.f.calls, ['start', 'drain'])
        self.assertIsNone(self.control.final)
        observer.cancel()
        with self.assertRaises(asyncio.CancelledError):await observer
        self.control._driver_task.cancel()
        with self.assertRaises(asyncio.CancelledError):await self.control._driver_task


@unittest.skipUnless(os.name == 'posix', 'requires POSIX pipe readiness')
class PipeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.input_read, self.input_write = os.pipe()
        self.output_read, self.output_write = os.pipe()
        self.fds = {self.input_read, self.input_write, self.output_read, self.output_write}
        self.channel = control.FDChannel(asyncio.get_running_loop(), input_fd=self.input_read,
                                         output_fd=self.output_write)

    async def asyncTearDown(self):
        for fd in self.fds:
            os.close(fd)

    def close(self, fd):
        os.close(fd);self.fds.remove(fd)

    async def test_fragmented_frames_and_multiple_frames_are_bounded(self):
        raw = control.canonical(command()) + b'\n' + control.canonical(command(2)) + b'\n'
        waiting = asyncio.create_task(self.channel.read())
        os.write(self.input_write, raw[:12]);await asyncio.sleep(0)
        self.assertFalse(waiting.done())
        os.write(self.input_write, raw[12:])
        self.assertEqual(await waiting, command())
        self.assertEqual(await self.channel.read(), command(2))
        self.assertEqual(self.channel._buffer, bytearray())

    async def test_eof_and_partial_eof_are_explicit(self):
        os.write(self.input_write, b'{')
        self.close(self.input_write)
        with self.assertRaisesRegex(control.ServiceControlRejected, 'partial_eof'):
            await self.channel.read()
        self.channel._buffer.clear()
        with self.assertRaisesRegex(control.ServiceControlRejected, 'control_eof'):
            await self.channel.read()

    async def test_cancelled_pipe_observer_does_not_steal_next_frame(self):
        waiting = asyncio.create_task(self.channel.read());await asyncio.sleep(0)
        waiting.cancel()
        with self.assertRaises(asyncio.CancelledError):await waiting
        os.write(self.input_write, control.canonical(command()) + b'\n')
        self.assertEqual(await self.channel.read(), command())

    async def test_output_uses_one_canonical_newline_without_executor_thread(self):
        before = threading.active_count()
        value = frame()
        await self.channel.write(value)
        self.assertEqual(os.read(self.output_read, 65536), control.canonical(value) + b'\n')
        self.assertEqual(threading.active_count(), before)

    async def test_output_reader_loss_is_explicit_and_does_not_close_pipes(self):
        self.close(self.output_read)
        with self.assertRaisesRegex(control.ServiceControlRejected, 'output_lost'):
            await self.channel.write(frame())
        os.fstat(self.output_write)


if __name__ == '__main__':
    unittest.main()
