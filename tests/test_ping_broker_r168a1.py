"""R168 QA control/ownership tests; no privileged-host or installed-lab acceptance.

Filesystem and pipes below are owned temporary fixtures. Lifecycle doubles mark
the principal/source boundary explicitly; one Unix-socket test uses the real
broker in its existing same-UID fixture mode, without an upstream or send grant.
"""
import asyncio
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'scripts/qa/r168a1_ping_broker.py'
spec = importlib.util.spec_from_file_location('r168_ping_broker_test_module', path)
qa = importlib.util.module_from_spec(spec); spec.loader.exec_module(qa)


def request():
    return {'schema': 1, 'kind': 'R168A1_PING_BROKER', 'attemptId': 'unit-01',
        'brokerDirectory': '/run/alaz-r168a1-unit-01/broker',
        'principalContract': {'version': 1, 'enabled': True, 'gatewayUid': 23001,
            'brokerUid': 23002, 'socketGroupGid': 23003, 'hostUserNamespace': 'user:[4026531837]'},
        'signingKey': '1' * 64, 'scope': '2' * 64, 'binding': '3' * 64, 'policyFingerprint': '4' * 64,
        'owner': {'pid': 321, 'startTicks': 98765, 'uid': 0},
        'control': {'dev': 1, 'ino': 2, 'nonce': '5' * 32},
        'expectedPings': 1, 'maxLifetimeSeconds': 10}


def stop_message(value, broker_id='a' * 32):
    return qa.encode({'schema': 1, 'operation': 'shutdown', 'attemptId': value['attemptId'],
        'brokerId': broker_id, 'nonce': value['control']['nonce']})


class FixtureCustody(Exception):
    def __init__(self, record):
        self.record = record


class PureContracts(unittest.TestCase):
    def test_spec_accepts_bounded_contract_and_refuses_scope_or_type_changes(self):
        self.assertEqual(qa.validate_spec(request()), request())
        changes = [('schema', True), ('expectedPings', True), ('expectedPings', 0), ('expectedPings', 9),
            ('maxLifetimeSeconds', 301), ('brokerDirectory', '/tmp/foreign/broker'),
            ('brokerDirectory', '/run/alaz-r168a1-x/../broker'), ('signingKey', 'not-a-key')]
        for key, value in changes:
            with self.subTest(key=key, value=value), self.assertRaises(qa.Refused):
                item = request(); item[key] = value; qa.validate_spec(item)
        for change in ('extra', 'same_uid', 'root_broker', 'owner_not_root'):
            item = request()
            if change == 'extra': item['launchUpstream'] = True
            if change == 'same_uid': item['principalContract']['brokerUid'] = 23001
            if change == 'root_broker': item['principalContract']['brokerUid'] = 0
            if change == 'owner_not_root': item['owner']['uid'] = 23001
            with self.subTest(change=change), self.assertRaises(qa.Refused): qa.validate_spec(item)

    def test_duplicate_and_nonfinite_json_are_refused(self):
        for raw in (b'{"schema":1,"schema":1}', b'{"value":NaN}', b'{"value":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(qa.Refused): qa.decode(raw)

    def test_shutdown_is_single_bounded_frame_bound_to_owner_attempt_and_broker(self):
        value = request(); raw = stop_message(value); qa.validate_shutdown(raw, value, 'a' * 32)
        for changed in (raw.rstrip(), raw + raw, b'x' * 1025 + b'\n',
                        raw.replace(b'unit-01', b'unit-02'), raw.replace(b'aaaa', b'bbbb', 1),
                        raw.replace(b'5555', b'6666', 1), raw.replace(b'"schema":1', b'"schema":true')):
            with self.subTest(changed=changed[:30]), self.assertRaises((qa.Refused, ValueError)):
                qa.validate_shutdown(changed, value, 'a' * 32)

    def test_terminal_counters_distinguish_bool_and_require_exact_one_ping(self):
        value = {'brokerId': 'a' * 32, 'pid': os.getpid(), 'socketRemoved': True, 'activeRequests': 0,
            'counters': {'physicalAttempts': 0, 'responses': 0, 'refused': 0, 'pings': 1}}
        qa.validate_closed(value, 'a' * 32, 1)
        for key, change in (('physicalAttempts', 1), ('responses', 1), ('refused', 1),
                            ('pings', 0), ('pings', True)):
            altered = copy.deepcopy(value); altered['counters'][key] = change
            with self.subTest(key=key, change=change), self.assertRaises(qa.Refused):
                qa.validate_closed(altered, 'a' * 32, 1)
        for key, change in (('activeRequests', False), ('activeRequests', 1), ('socketRemoved', False)):
            with self.subTest(key=key), self.assertRaises(qa.Refused):
                qa.validate_closed(dict(value, **{key: change}), 'a' * 32, 1)

    def test_parent_stat_handles_parentheses_and_refuses_reused_identity(self):
        raw = '321 (name with ) parentheses) ' + ' '.join(['S'] + ['0'] * 18 + ['98765'])
        self.assertEqual(qa.proc_start_ticks(raw), 98765)
        with patch.object(qa.os, 'getppid', return_value=321), patch.object(Path, 'read_text',
                side_effect=[raw, 'Name:\tpython\nUid:\t0\t0\t0\t0\n']):
            qa.check_parent(request()['owner'])
        with patch.object(qa.os, 'getppid', return_value=322), self.assertRaisesRegex(qa.Refused, 'parent_changed'):
            qa.check_parent(request()['owner'])
        with patch.object(qa.os, 'getppid', return_value=321), patch.object(Path, 'read_text',
                return_value=raw.replace('98765', '98766')), self.assertRaisesRegex(qa.Refused, 'parent_reused'):
            qa.check_parent(request()['owner'])

    def test_no_upstream_guard_refuses_connect_inet_spawn_and_foreign_bind(self):
        guard = qa.NoUpstream('/owned/egress.sock')
        # Declared Linux audit-event numbers; no real socket is created here.
        # Only the QA module binding is replaced, not the shared socket module.
        linux_socket = SimpleNamespace(AF_UNIX=1, AF_INET=2, SOCK_STREAM=1)
        with patch.object(qa, 'socket', linux_socket):
            guard('socket.__new__', (None, linux_socket.AF_UNIX, linux_socket.SOCK_STREAM, 0))
            guard('socket.bind', (None, '/owned/egress.sock'))
            for event, args in (('socket.connect', (None, '/other')),
                    ('socket.__new__', (None, linux_socket.AF_INET, linux_socket.SOCK_STREAM, 0)),
                    ('subprocess.Popen', ()), ('socket.bind', (None, '/other'))):
                with self.subTest(event=event), self.assertRaises(qa.Refused): guard(event, args)
        self.assertEqual(guard.denied_count, 4)


@unittest.skipUnless(sys.platform == 'linux', 'Linux owned descriptors and anonymous pipes')
class OwnedDescriptors(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.reader, self.writer = os.pipe()
        self.addCleanup(lambda: os.close(self.reader))
        self.addCleanup(self.close_writer)
        self.value = request()

    def close_writer(self):
        if self.writer is not None:
            os.close(self.writer); self.writer = None

    async def test_owned_pipe_valid_command_and_fd_mode_restored(self):
        os.write(self.writer, stop_message(self.value))
        before = os.get_blocking(self.reader)
        self.assertTrue(await asyncio.wait_for(qa.wait_shutdown(self.reader, self.value, 'a' * 32,
            owner_check=lambda _: None), 1))
        self.assertEqual(os.get_blocking(self.reader), before)

    async def test_control_eof_is_refusal_not_shutdown(self):
        self.close_writer()
        with self.assertRaisesRegex(qa.Refused, 'control_eof'):
            await asyncio.wait_for(qa.wait_shutdown(self.reader, self.value, 'a' * 32,
                owner_check=lambda _: None), 1)

    async def test_oversize_control_refused_without_unbounded_read(self):
        os.write(self.writer, b'x' * 1025)
        with self.assertRaisesRegex(qa.Refused, 'shutdown_frame'):
            await asyncio.wait_for(qa.wait_shutdown(self.reader, self.value, 'a' * 32,
                owner_check=lambda _: None), 1)

    async def test_lost_parent_refused_and_registration_failure_restores_fd(self):
        def gone(_): raise qa.Refused('fixture_parent_lost')
        with self.assertRaisesRegex(qa.Refused, 'fixture_parent_lost'):
            await qa.wait_shutdown(self.reader, self.value, 'a' * 32, owner_check=gone)
        loop = asyncio.get_running_loop()
        with patch.object(loop, 'add_reader', side_effect=OSError('fixture_reader_failure')):
            with self.assertRaises(OSError):
                await qa.wait_shutdown(self.reader, self.value, 'a' * 32, owner_check=lambda _: None)
        self.assertTrue(os.get_blocking(self.reader))

    async def test_held_spec_bytes_pin_and_descriptor_access_are_enforced(self):
        # Metadata double declares the trusted-root boundary; only the actual
        # owned descriptor bytes/access mode are exercised on ordinary CI UID.
        with tempfile.TemporaryFile(mode='w+b') as stream:
            raw = qa.encode(self.value); stream.write(raw); stream.flush()
            read_fd = os.open('/proc/self/fd/' + str(stream.fileno()), os.O_RDONLY)
            try:
                info = os.fstat(read_fd)
                fields = {k: getattr(info, k) for k in ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')}
                trusted = SimpleNamespace(**dict(fields, st_uid=0, st_gid=0, st_nlink=1, st_mode=stat.S_IFREG | 0o600))
                with patch.object(qa.os, 'fstat', return_value=trusted):
                    self.assertEqual(qa.read_spec(read_fd, qa.sha(raw)), self.value)
                    with self.assertRaisesRegex(qa.Refused, 'spec_bytes'): qa.read_spec(read_fd, '0' * 64)
                    with self.assertRaisesRegex(qa.Refused, 'private_spec_fd'): qa.read_spec(stream.fileno(), qa.sha(raw))
            finally:
                os.close(read_fd)


@unittest.skipUnless(sys.platform == 'linux', 'Linux exclusive receipt publication')
class Receipts(unittest.TestCase):
    def test_exclusive_publication_preserves_existing_receipt_and_cleans_own_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                first = qa.publish_receipt(fd, 'ready.json', {'result': 'first'})
                raw = Path(directory, 'ready.json').read_bytes()
                self.assertEqual(first['sha256'], qa.sha(raw))
                with self.assertRaises(FileExistsError): qa.publish_receipt(fd, 'ready.json', {'result': 'second'})
                self.assertEqual(Path(directory, 'ready.json').read_bytes(), raw)
                self.assertEqual({p.name for p in Path(directory).iterdir()}, {'ready.json'})
                self.assertEqual(stat.S_IMODE(Path(directory, 'ready.json').stat().st_mode), 0o600)
            finally:
                os.close(fd)


@unittest.skipUnless(sys.platform == 'linux', 'Linux owned lifecycle fixtures')
class Lifecycle(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='r168-broker-unit-'); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name); self.value = request(); self.value['brokerDirectory'] = str(self.directory)
        self.fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY); self.addCleanup(os.close, self.fd)
        self.instances = []; self.start_error = False; self.acquire = True; self.close_error = False; self.foreign = False
        self.start_wait = None; self.close_wait = None; self.pending_start = None; self.pending_close = None
        owner = self
        class Server:
            def __init__(self, config, directory):
                self.config = config; self.directory = directory; self.server = None; self.close_calls = 0
                self.counts = {'physicalAttempts': 0, 'responses': 0, 'refused': 0, 'pings': 0}
                owner.instances.append(self)
            async def start(self):
                owner.pending_start = asyncio.current_task()
                if owner.acquire: self.server = object()
                if owner.start_wait is not None: await owner.start_wait.wait()
                if owner.foreign: (self.directory / 'egress.sock').write_bytes(b'foreign-owned-marker')
                if owner.start_error: raise OSError('fixture_start')
                return {'brokerId': 'a' * 32, 'socketPath': str(self.directory / 'egress.sock'),
                    'routeFingerprint': self.config.route, 'pid': os.getpid(), 'backend': 'linux_unix_credential_broker'}
            async def close(self):
                owner.pending_close = asyncio.current_task()
                self.close_calls += 1
                if owner.close_wait is not None: await owner.close_wait.wait()
                if owner.close_error: raise OSError('fixture_close')
                return {'brokerId': 'a' * 32, 'pid': os.getpid(), 'socketRemoved': True,
                    'activeRequests': 0, 'counters': dict(self.counts)}
        self.api = (SimpleNamespace(ProviderBrokerServer=Server),
            SimpleNamespace(BrokerConfig=lambda *a, **k: SimpleNamespace(route='b' * 64)),
            SimpleNamespace(socket_identity=lambda *a: {'fixturePrincipalOnly': True}))

    async def invoke(self, *, wait_control=None, readback=lambda: {'fixtureSourceBoundary': True}, publish=qa.publish_receipt):
        async def stop(*a, **k):
            self.instances[0].counts['pings'] = 1; return True
        async def retain(record):
            # Explicit unit-fixture escape, unavailable through the CLI.
            raise FixtureCustody(record)
        out = io.StringIO()
        with redirect_stdout(out):
            try:
                result = await qa.serve(self.api, self.value, -1, self.fd, qa.NoUpstream('/unused'),
                    owner_check=lambda _: None, readback=readback, publish=publish,
                    wait_control=wait_control or stop, retain=retain)
            except FixtureCustody as held:
                result = held.record
        return result, [json.loads(line) for line in out.getvalue().splitlines()]

    async def test_success_binds_both_receipts_and_exact_counters(self):
        result, frames = await self.invoke()
        self.assertEqual(result['result'], 'PASS', result); self.assertEqual(len(frames), 2)
        self.assertEqual(self.instances[0].close_calls, 1)
        for frame, name in zip(frames, ('ready.json', 'shutdown.json')):
            raw = (self.directory / name).read_bytes(); self.assertEqual(frame['receipt']['sha256'], qa.sha(raw))
            self.assertEqual(json.loads(raw), {k: v for k, v in frame.items() if k != 'receipt'})

    async def test_control_loss_retains_original_server_without_close(self):
        async def lost(*a, **k): raise qa.Refused('fixture_control_lost')
        result, _ = await self.invoke(wait_control=lost)
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertTrue(result['processRetained'])
        self.assertFalse(result['shutdownCommandAccepted']); self.assertTrue(result['controllerMustRetainOwnership'])
        self.assertEqual(self.instances[0].close_calls, 0)

    async def test_unacknowledged_stop_is_not_success(self):
        async def no_ack(*a, **k): return False
        result, _ = await self.invoke(wait_control=no_ack)
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertFalse(result['shutdownCommandAccepted'])
        self.assertEqual(self.instances[0].close_calls, 0)

    async def test_partial_start_retains_acquired_server_without_close(self):
        self.start_error = True
        result, frames = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertEqual(len(frames), 1)
        self.assertEqual(self.instances[0].close_calls, 0); self.assertTrue(result['serverAcquired'])

    async def test_unacquired_socket_and_close_failure_retain_unknown_ownership(self):
        self.start_error = True; self.acquire = False; self.foreign = True
        result, _ = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertEqual(self.instances[0].close_calls, 0)
        self.assertEqual((self.directory / 'egress.sock').read_bytes(), b'foreign-owned-marker')

    async def test_close_failure_does_not_unlink_socket(self):
        self.close_error = True; self.foreign = True
        result, _ = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertTrue(result['controllerMustRetainOwnership'])
        self.assertEqual((self.directory / 'egress.sock').read_bytes(), b'foreign-owned-marker')

    async def test_ready_collision_retains_server_without_replacing_receipt(self):
        (self.directory / 'ready.json').write_bytes(b'prior-receipt')
        result, _ = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertEqual(self.instances[0].close_calls, 0)
        self.assertEqual((self.directory / 'ready.json').read_bytes(), b'prior-receipt')

    async def test_terminal_publication_failure_is_unknown_even_after_close(self):
        def publish(fd, name, value):
            if name == 'shutdown.json': raise OSError('fixture_publish')
            return qa.publish_receipt(fd, name, value)
        result, _ = await self.invoke(publish=publish)
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertTrue(result['closedObservation']['socketRemoved'])
        self.assertTrue(result['controllerMustRetainOwnership'])

    async def test_start_timeout_does_not_cancel_original_start_or_close_server(self):
        self.start_wait = asyncio.Event()
        with patch.object(qa, 'START_OBSERVATION_SECONDS', 0.01):
            result, _ = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertFalse(result['startTaskDone'])
        self.assertFalse(self.pending_start.done()); self.assertEqual(self.instances[0].close_calls, 0)
        self.start_wait.set(); await self.pending_start

    async def test_close_timeout_retains_original_close_without_retry(self):
        self.close_wait = asyncio.Event()
        with patch.object(qa, 'CLOSE_OBSERVATION_SECONDS', 0.01):
            result, _ = await self.invoke()
        self.assertEqual(result['result'], 'UNKNOWN'); self.assertTrue(result['shutdownCommandAccepted'])
        self.assertFalse(self.pending_close.done()); self.assertEqual(self.instances[0].close_calls, 1)
        self.close_wait.set(); await self.pending_close

    async def test_default_unknown_custody_keeps_event_loop_task_alive(self):
        held = asyncio.Event()
        async def lost(*a, **k): raise qa.Refused('fixture_control_eof')
        def publish(fd, name, value):
            receipt = qa.publish_receipt(fd, name, value)
            if name == 'unknown.json': held.set()
            return receipt
        with redirect_stdout(io.StringIO()):
            task = asyncio.create_task(qa.serve(self.api, self.value, -1, self.fd, qa.NoUpstream('/unused'),
                owner_check=lambda _: None, readback=lambda: {'fixtureSourceBoundary': True},
                publish=publish, wait_control=lost))
            try:
                await asyncio.wait_for(held.wait(), 1)
                self.assertFalse(task.done()); self.assertEqual(self.instances[0].close_calls, 0)
            finally:
                # The test explicitly ends its fake-only fixture; production
                # has no automatic path that cancels this custody task.
                task.cancel()
                with self.assertRaises(asyncio.CancelledError): await task

    async def test_source_readback_change_is_not_accepted(self):
        values = iter(({'pin': 'before'}, {'pin': 'after'}))
        result, _ = await self.invoke(readback=lambda: next(values))
        self.assertEqual(result['result'], 'FAIL'); self.assertEqual(result['reason'], 'ping_broker_source_changed')

    async def test_real_same_uid_unix_broker_ping_has_no_physical_send(self):
        # This exercises real installed-class logic from the checkout, while
        # deliberately retaining the existing same-UID unit-fixture boundary.
        sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
        try:
            import provider_broker
            import provider_egress
        finally:
            sys.path.pop(0)
        directory = self.directory / 'real-broker'; self.value['brokerDirectory'] = str(directory)
        def config(*args, **kwargs):
            kwargs['principal_contract'] = None
            return provider_egress.BrokerConfig(*args, **kwargs)
        self.api = (provider_broker, SimpleNamespace(BrokerConfig=config), self.api[2])
        async def ping(fd, value, broker_id, **kwargs):
            client = provider_broker.ProviderBrokerClient({'socket_path': str(directory / 'egress.sock'),
                'broker_id': broker_id, 'route_fingerprint': provider_egress.route_fingerprint(qa.UPSTREAM, qa.MODEL),
                'signing_key': value['signingKey']})
            await client.ready(); return True
        def publish(fd, name, value):
            actual_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try: return qa.publish_receipt(actual_fd, name, value)
            finally: os.close(actual_fd)
        result, frames = await self.invoke(wait_control=ping, publish=publish)
        self.assertEqual(result['result'], 'PASS', result); self.assertEqual(len(frames), 2)
        self.assertEqual(result['closed']['counters'], {'physicalAttempts': 0, 'responses': 0, 'refused': 0, 'pings': 1})
        self.assertFalse((directory / 'egress.sock').exists())


if __name__ == '__main__':
    unittest.main()
