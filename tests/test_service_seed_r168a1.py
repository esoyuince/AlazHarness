"""R168 seed contracts only; never execute native Hermes, a broker or a model.

Filesystem/SQLite handles used here are disposable local test resources.
Capture ports declare fake native ownership and bypass native layout inspection;
the actual service handoff codec and typed field checks remain real.
No audit hook, profile hook, privileged launcher or installed acceptance runs.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/qa/r168a1_service_seed.py'
spec = importlib.util.spec_from_file_location('_tested_r168_seed', SOURCE)
seed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed)


def args_for(home='/owned/profile', config='/owned/private/config.json'):
    return argparse.Namespace(home=home, config_file=config, instance_id='r168-seed-test',
        expected_profile_device=1, expected_profile_inode=2, parent_pid=3, parent_start_ticks=4,
        expected_mount_namespace_inode=5, expected_user_namespace='user:[6]',
        expected_config_sha256='a' * 64, expected_seed_sha256='b' * 64)


def config_raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


class BinaryOutput:
    def __init__(self):
        self.buffer = io.BytesIO()


class InputContractTests(unittest.TestCase):
    def test_explicit_cli_interface_roundtrips_all_parent_pins(self):
        values = args_for()
        argv = []
        for name, value in vars(values).items():
            argv += ['--' + name.replace('_', '-'), str(value)]
        parsed = seed.arguments(argv)
        self.assertEqual(vars(parsed), vars(values))
        self.assertEqual(seed.validate_arguments(parsed), (Path(values.home), Path(values.config_file)))

    def test_actor_and_namespace_arguments_reject_boolean_or_noncanonical_identity(self):
        for name in ('parent_pid', 'parent_start_ticks', 'expected_profile_device',
                     'expected_profile_inode', 'expected_mount_namespace_inode'):
            for invalid in (True, 0, -1, 2**64, '1'):
                with self.subTest(name=name, invalid=invalid):
                    args = args_for()
                    setattr(args, name, invalid)
                    with self.assertRaises(seed.SeedRejected):
                        seed.validate_arguments(args)
        for invalid in ('mnt:[6]', 'user:[0]', 'user:[06]', 'user:6', True):
            with self.subTest(namespace=invalid), self.assertRaises(seed.SeedRejected):
                args = args_for()
                args.expected_user_namespace = invalid
                seed.validate_arguments(args)

    def test_private_input_and_profile_cannot_overlap_installation(self):
        for home in (str(seed.INSTALLATION), str(seed.INSTALLATION / 'new'), '/opt',
                     str(seed.INPUT), str(seed.DEPENDENCIES / 'new')):
            with self.subTest(home=home), self.assertRaises(seed.SeedRejected):
                seed.validate_arguments(args_for(home=home))
        for config in ('/owned/profile', '/owned/profile/config.json'):
            with self.subTest(config=config), self.assertRaises(seed.SeedRejected):
                seed.validate_arguments(args_for(config=config))

    def test_paths_and_decimal_pins_are_unambiguous_and_bounded(self):
        for value in ('relative', '/', '//owned/profile', '/owned//profile',
                      '/owned/./profile', '/owned/../profile', '/owned/profile/',
                      '/owned/\x00profile', '/owned\\profile'):
            with self.subTest(path=value), self.assertRaises(seed.SeedRejected):
                seed.canonical_path(value)
        self.assertEqual(seed.decimal(str(2**64 - 1)), 2**64 - 1)
        for value in ('0', '01', '+1', '-1', ' 1', '1e3', str(2**64), True, 1):
            with self.subTest(number=value), self.assertRaises(seed.SeedRejected):
                seed.decimal(value)

    def test_config_canonical_utf8_roundtrip_is_distinct_from_result_frame(self):
        value = {'enabled': False, 'label': 'Türkçe', 'nested': [0, None]}
        raw = config_raw(value)
        self.assertEqual(seed.config_document(raw), value)
        self.assertFalse(raw.endswith(b'\n'))
        self.assertTrue(seed.canonical(value).endswith(b'\n'))
        self.assertEqual(seed.canonical(value).count(b'\n'), 1)

    def test_config_refuses_ambiguous_or_excessive_documents(self):
        invalid = [b'{}\\n', b'{}\n', b'{"x": 1}', b'{"x":1,"x":2}', b'[]',
                   b'{"x":NaN}', b'{"x":1e999}', b'{"x":123456789012345678901}',
                   b'\xff', b'{"x":"\\u0000"}',
                   config_raw({'x': '$' + '{TOKEN}'}),
                   config_raw({'x': 'a' * 4097}),
                   config_raw({'x': [0] * 4096}), b' ' * (seed.MAX_CONFIG + 1)]
        nested = {}
        for _ in range(18):
            nested = {'x': nested}
        invalid.append(config_raw(nested))
        for raw in invalid:
            with self.subTest(prefix=raw[:40]), self.assertRaises(seed.SeedRejected):
                seed.config_document(raw)

    def test_provider_free_capacity_requires_typed_zeros_and_exact_principal(self):
        principal = {'version': 1, 'enabled': True, 'gatewayUid': seed.GATEWAY_UID,
                     'brokerUid': 23002, 'socketGroupGid': seed.SOCKET_GID,
                     'hostUserNamespace': 'user:[6]'}
        zeros = dict.fromkeys(('max_provider_calls', 'max_tool_calls',
                              'total_token_limit', 'total_cost_microusd'), 0)
        settings = types.SimpleNamespace(execution={'policy': zeros,
            'provider_broker': {'principal_contract': principal}})
        seed.zero_capacity(settings, 'user:[6]')
        for field in zeros:
            for invalid in (False, 1, -1, None):
                with self.subTest(field=field, invalid=invalid), patch.dict(zeros, {field: invalid}):
                    with self.assertRaises(seed.SeedRejected):
                        seed.zero_capacity(settings, 'user:[6]')
        with patch.dict(principal, {'version': True}), self.assertRaises(seed.SeedRejected):
            seed.zero_capacity(settings, 'user:[6]')
        with self.assertRaises(seed.SeedRejected):
            seed.zero_capacity(settings, 'user:[7]')


@unittest.skipUnless(os.name == 'posix', 'POSIX owned files/FD semantics')
class PrivateFilesTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(directory).resolve()
        self.home = self.root / 'profile'
        self.home.mkdir(mode=0o700)
        self.config = self.root / 'private.json'
        self.raw = config_raw({'fixture': 'private'})
        self.config.write_bytes(self.raw)
        self.config.chmod(0o600)
        # Declared actor normalization for disposable fixture files only.
        self.stack.enter_context(patch.object(seed, 'GATEWAY_UID', os.getuid()))
        self.stack.enter_context(patch.object(seed, 'SOCKET_GID', os.getgid()))
        self.args = args_for(str(self.home), str(self.config))
        info = self.home.stat()
        self.args.expected_profile_device, self.args.expected_profile_inode = info.st_dev, info.st_ino
        self.args.expected_config_sha256 = seed.sha(self.raw)

    def test_private_config_readback_requires_external_hash_and_private_mode(self):
        self.assertEqual(seed.read_private_config(self.config, seed.sha(self.raw)),
                         (self.raw, {'fixture': 'private'}))
        with self.assertRaisesRegex(seed.SeedRejected, 'input_changed'):
            seed.read_private_config(self.config, '0' * 64)
        self.config.chmod(0o644)
        with self.assertRaisesRegex(seed.SeedRejected, 'metadata'):
            seed.read_private_config(self.config, seed.sha(self.raw))

    def test_linked_config_and_linked_profile_are_refused(self):
        link = self.root / 'link'
        link.symlink_to(self.config)
        with self.assertRaises(seed.SeedRejected):
            seed.read_private_config(link, seed.sha(self.raw))
        os.link(self.config, self.root / 'hardlink')
        with self.assertRaises(seed.SeedRejected):
            seed.read_private_config(self.config, seed.sha(self.raw))
        alias = self.root / 'profile-alias'
        alias.symlink_to(self.home)
        with self.assertRaises(seed.SeedRejected):
            seed.home_identity(alias, self.args, fresh=True)

    def test_home_identity_requires_freshness_and_original_inode(self):
        seed.home_identity(self.home, self.args, fresh=True)
        (self.home / 'unexpected').write_text('owned')
        with self.assertRaisesRegex(seed.SeedRejected, 'not_empty'):
            seed.home_identity(self.home, self.args, fresh=True)
        seed.home_identity(self.home, self.args, fresh=False)
        self.args.expected_profile_inode += 1
        with self.assertRaisesRegex(seed.SeedRejected, 'identity'):
            seed.home_identity(self.home, self.args, fresh=False)

    def test_config_write_is_exclusive_fsynced_and_does_not_adopt_existing_file(self):
        real_fsync = os.fsync
        seen = []
        def fsync(fd):
            seen.append(os.fstat(fd).st_mode)
            return real_fsync(fd)
        with patch.object(seed.os, 'fsync', side_effect=fsync):
            result = seed.write_config_once(self.home, self.raw, self.args)
        target = self.home / 'config.yaml'
        self.assertEqual(target.read_bytes(), self.raw)
        self.assertEqual(result.st_ino, target.stat().st_ino)
        self.assertEqual(len(seen), 2)
        with self.assertRaises(FileExistsError):
            seed.write_config_once(self.home, self.raw, self.args)
        self.assertEqual(target.read_bytes(), self.raw)

    def test_partial_write_failure_is_preserved_without_unlink_or_retry(self):
        with patch.object(seed.os, 'fsync', side_effect=OSError('owned fixture failure')):
            with self.assertRaises(OSError):
                seed.write_config_once(self.home, self.raw, self.args)
        self.assertEqual((self.home / 'config.yaml').read_bytes(), self.raw)
        with self.assertRaises(FileExistsError):
            seed.write_config_once(self.home, self.raw, self.args)

    def test_open_descriptor_outside_home_cannot_bypass_write_guard(self):
        boundary = seed.OfflineBoundary(self.home, {'phase': 'CAPTURE_SERVICE'})
        outside = os.open(self.config, os.O_RDWR)
        self.addCleanup(os.close, outside)
        with self.assertRaisesRegex(seed.SeedRejected, 'outside_profile'):
            boundary('open', (outside, 'r+', os.O_RDWR))
        self.assertEqual(boundary.denied[0]['event'], 'open')

    def test_guard_resolves_relative_mutations_against_the_actual_directory_fd(self):
        boundary = seed.OfflineBoundary(self.home, {'phase': 'INITIALIZE_AUXILIARIES'})
        inside = os.open(self.home, os.O_RDONLY | os.O_DIRECTORY)
        outside = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, inside)
        self.addCleanup(os.close, outside)
        boundary('os.mkdir', ('child', 0o700, inside))
        with self.assertRaises(seed.SeedRejected):
            boundary('os.mkdir', ('child', 0o700, outside))
        with self.assertRaises(seed.SeedRejected):
            boundary('os.rename', ('child', 'moved', inside, outside))


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        # Declared Linux lexical fixture; this class performs no owned-file I/O.
        paths = patch.object(seed, 'INSTALLATION', PurePosixPath('/opt/alaz-r167a1'))
        paths.start()
        self.addCleanup(paths.stop)

    def boundary(self, phase='PREPARE_CONSUMER'):
        return seed.OfflineBoundary(PurePosixPath('/owned/profile'), {'phase': phase})

    def test_no_network_or_arbitrary_process_events_are_allowed(self):
        for event, arguments in (
                ('socket.connect', (object(), ('127.0.0.1', 80))),
                ('socket.bind', (object(), ('127.0.0.1', 0))),
                ('socket.sendto', (object(), ('127.0.0.1', 80))),
                ('socket.getaddrinfo', ('example.invalid', 443, 0, 0, 0)),
                ('os.system', ('anything',)), ('os.exec', ('anything', [], {})),
                ('os.fork', ()), ('subprocess.Popen', ('anything', [], '/', {}))):
            boundary = self.boundary()
            with self.subTest(event=event), self.assertRaises(seed.SeedRejected):
                boundary(event, arguments)
            self.assertEqual(boundary.denied[-1]['event'], event)

    def test_only_the_two_original_cold_helpers_in_order_are_allowed(self):
        boundary = self.boundary('START_OWNER')
        for name in seed.HELPERS:
            argv = [seed.PYTHON, '-I', '-B', str(seed.INSTALLATION / 'scripts' / name)]
            boundary('subprocess.Popen', (seed.PYTHON, argv, seed.INSTALLATION,
                {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}))
        self.assertEqual([row['script'] for row in boundary.helpers], list(seed.HELPERS))
        with self.assertRaises(seed.SeedRejected):
            boundary('subprocess.Popen', (seed.PYTHON, argv, seed.INSTALLATION,
                {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}))
        wrong = self.boundary('START_OWNER')
        with self.assertRaises(seed.SeedRejected):
            wrong('subprocess.Popen', (seed.PYTHON,
                [seed.PYTHON, '-I', '-B', str(seed.INSTALLATION / 'scripts' / seed.HELPERS[1])],
                seed.INSTALLATION, {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}))

    def test_database_paths_and_phases_are_limited_without_memory_fallback(self):
        boundary = self.boundary('CREATE_COLD_STORES')
        for name in ('state.db', 'runs_idempotency.db', 'response_store.db'):
            boundary('sqlite3.connect', ('/owned/profile/' + name,))
        for path in (':memory:', '/other/state.db', '/owned/profile/other.db'):
            with self.subTest(path=path), self.assertRaises(seed.SeedRejected):
                boundary('sqlite3.connect', (path,))
        boundary.progress['phase'] = 'COMPLETE'
        with self.assertRaises(seed.SeedRejected):
            boundary('sqlite3.connect', ('/owned/profile/state.db',))

    def test_metadata_mutators_cannot_write_outside_the_owned_home(self):
        cases = (('os.chmod', ('/outside', 0o600, -1)),
                 ('os.utime', ('/outside', None, None, -1)),
                 ('os.chown', ('/outside', 1, 1, -1)),
                 ('os.setxattr', ('/outside', 'user.test', b'x', 0)),
                 ('os.removexattr', ('/outside', 'user.test')),
                 ('os.truncate', ('/outside', 0)),
                 ('os.remove', ('/outside', -1)),
                 ('os.symlink', ('/owned/profile/a', '/owned/profile/b', -1)))
        for event, arguments in cases:
            with self.subTest(event=event), self.assertRaises(seed.SeedRejected):
                self.boundary()(event, arguments)

    def test_native_agent_and_dispatch_calls_are_blocked_but_store_constructor_is_not(self):
        boundary = self.boundary()
        for name, qualified in (('run_api_turn', 'run_api_turn'), ('__init__', 'AIAgent.__init__')):
            frame = types.SimpleNamespace(f_code=types.SimpleNamespace(
                co_filename=str(seed.INSTALLATION / 'native/run_agent.py'),
                co_name=name, co_qualname=qualified))
            with self.assertRaises(seed.SeedRejected):
                boundary.profile(frame, 'call', None)
        safe = types.SimpleNamespace(f_code=types.SimpleNamespace(
            co_filename=str(seed.INSTALLATION / 'native/hermes_state.py'),
            co_name='__init__', co_qualname='SessionDB.__init__'))
        boundary.profile(safe, 'call', None)


class DeniedCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.module = types.ModuleType('urllib3.util.connection')
        self.module.__file__ = seed.IPV6_PATH
        self.module.HAS_IPV6 = False
        code = compile('def candidate(): pass\n', seed.IPV6_PATH, 'exec')
        scope = {}
        exec(code, scope)
        function_code = scope['candidate'].__code__.replace(
            co_name='_has_ipv6', co_filename=seed.IPV6_PATH, co_firstlineno=114)
        self.module._has_ipv6 = types.FunctionType(
            function_code, vars(self.module), '_has_ipv6')
        self.module._has_ipv6.__module__ = 'urllib3.util.connection'
        self.stack.enter_context(patch.dict(seed.sys.modules, {'urllib3.util.connection': self.module}))
        class FakeSocket:
            family, type, proto = seed.socket.AF_INET6, seed.socket.SOCK_STREAM, 0
            descriptor = 17
            def fileno(self):
                return self.descriptor
        self.stack.enter_context(patch.object(seed.socket, 'socket', FakeSocket))
        self.socket = FakeSocket()
        parent = types.SimpleNamespace(f_globals=vars(self.module),
            f_code=types.SimpleNamespace(co_filename=seed.IPV6_PATH, co_name='<module>'), f_lineno=137)
        self.frame = types.SimpleNamespace(f_code=function_code, f_lineno=127,
            f_globals=vars(self.module), f_back=parent,
            f_locals={'host': '::1', 'has_ipv6': False, 'sock': self.socket})
        self.boundary = seed.OfflineBoundary(Path('/owned/profile'), {'phase': 'PREPARE_CONSUMER'})

    def test_exact_capability_probe_is_denied_and_only_closed_socket_qualifies(self):
        self.assertTrue(self.boundary.ipv6_probe((self.socket, ('::1', 0)), self.frame))
        with patch.object(seed.sys, '_getframe', return_value=self.frame):
            with self.assertRaises(PermissionError):
                self.boundary('socket.bind', (self.socket, ('::1', 0)))
        self.assertFalse(self.boundary.progress['blockedCapabilityProbes'][0]['bindPerformed'])
        with self.assertRaises(seed.SeedRejected):
            self.boundary.ipv6_closed()
        self.socket.descriptor = -1
        result = self.boundary.ipv6_closed()
        self.assertTrue(result['socketClosed'])
        self.assertFalse(result['hasIPv6AfterImports'])

    def test_matching_only_function_name_or_address_does_not_qualify(self):
        self.assertFalse(self.boundary.ipv6_probe((self.socket, ('::1', False)), self.frame))
        self.assertFalse(self.boundary.ipv6_probe((self.socket, ('127.0.0.1', 0)), self.frame))
        for field, invalid in (('f_lineno', 128), ('f_globals', {}),
                               ('f_code', self.frame.f_code.replace(co_firstlineno=115))):
            with self.subTest(field=field), patch.object(self.frame, field, invalid):
                self.assertFalse(self.boundary.ipv6_probe((self.socket, ('::1', 0)), self.frame))
        with patch.dict(self.frame.f_locals, {'has_ipv6': True}):
            self.assertFalse(self.boundary.ipv6_probe((self.socket, ('::1', 0)), self.frame))
        self.boundary.progress['phase'] = 'COMPLETE'
        self.assertFalse(self.boundary.ipv6_probe((self.socket, ('::1', 0)), self.frame))

    def test_second_bind_or_changed_module_result_is_not_suppressed(self):
        with patch.object(seed.sys, '_getframe', return_value=self.frame):
            with self.assertRaises(PermissionError):
                self.boundary('socket.bind', (self.socket, ('::1', 0)))
            with self.assertRaises(seed.SeedRejected):
                self.boundary('socket.bind', (self.socket, ('::1', 0)))
        self.assertEqual(self.boundary.denied[-1]['event'], 'socket.bind')
        self.socket.descriptor = -1
        self.module.HAS_IPV6 = True
        with self.assertRaises(seed.SeedRejected):
            self.boundary.ipv6_closed()


@unittest.skipUnless(os.name == 'posix', 'POSIX capture fixture identities')
class ServiceCaptureTests(unittest.TestCase):
    def setUp(self):
        PrivateFilesTests.setUp(self)
        with patch.object(sys, 'path', [str(ROOT / 'packages/claw-hermes'), *sys.path]):
            import gateway_service_handoff as handoff
            import gateway_service_profile as profile
            import gateway_service_sources as sources
            import gateway_store_startup as startup
            import gateway_prepared_consumer as prepared
        self.handoff, self.profile, self.prepared = handoff, profile, prepared
        identities = []
        for name in ('state.db', 'runs_idempotency.db', 'response_store.db'):
            path = self.home / name
            path.write_bytes(b'explicit fake database bytes')
            path.chmod(0o600)
            identities.append((path.stat().st_dev, path.stat().st_ino))
        self.connections = [sqlite3.connect(':memory:') for _ in range(3)]
        for connection in self.connections:
            connection.close()
        self.attempt = attempt = seed.Attempt()
        attempt.home, attempt.config_raw = self.home, self.raw
        attempt.connections = tuple(self.connections)
        attempt.selection = sources.load_selection()
        attempt.held = held = types.SimpleNamespace(
            _finished=False, finish=Mock(), check=Mock(), _owner=types.SimpleNamespace())
        owner = object.__new__(startup.NativeStoreStartup)
        consumer = object.__new__(prepared.PreparedRuntimeConsumer)
        owner._stage, owner._held, owner._owned = 'CLOSED', held, Mock()
        owner._expected = handoff.preopen.live.PreparedStoreExpectation(
            handoff.preopen.live.NATIVE_PIN, 'a' * 64, 'b' * 64,
            '12345678-1234-4234-8234-123456789012', 1, identities[0], identities[1],
            1, self.args.instance_id)
        owner._response_expected = handoff.response.PreparedResponseExpectation(
            handoff.response.NATIVE_FEATURE, handoff.response.SCHEMA_SHA256, identities[2])
        consumer._owner, consumer._held, consumer._stage = owner, held, 'DETACHED'
        consumer._borrowed_service, consumer._selected_feature = True, seed.NATIVE
        consumer._service_source = attempt.selection
        consumer._binding = types.SimpleNamespace(_stage='DETACHED')
        consumer._bundle = types.SimpleNamespace(_stage='DETACHED')
        consumer._source_proof = ('declared native source port', {})
        owner._prepared_consumer = consumer
        attempt.owner, attempt.consumer = owner, consumer
        self.auxiliary = {'sourceDerivedCacheSha256': 'd' * 64}
        self.imports = self.stack.enter_context(patch.object(prepared, 'verify_imports'))
        self.inspector = self.stack.enter_context(patch.object(profile, 'inspect_profile'))

    def test_actual_service_codec_binds_captured_file_ids_while_original_lease_remains_held(self):
        result = seed.capture_service(self.attempt, self.args, self.auxiliary)
        wire = result['handoff'].encode('ascii')
        decoded = self.handoff.decode(wire, expected_home=str(self.home))
        self.assertEqual(result['handoffSha256'], seed.sha(wire))
        self.assertEqual(decoded.service.selection.native_feature, seed.NATIVE)
        self.assertEqual(decoded.service.epoch, 1)
        self.assertEqual(decoded.service.instance_id, self.args.instance_id)
        self.assertEqual(decoded.service.config_sha256, seed.sha(self.raw))
        self.assertEqual(decoded.service.config_identity[1], (self.home / 'config.yaml').stat().st_ino)
        self.assertIs(self.attempt.record.service.__class__, self.profile.ServiceProfileExpectation)
        self.attempt.held.finish.assert_not_called()
        self.assertEqual(self.attempt.owner._owned.call_count, 2)
        self.assertEqual(self.imports.call_count, 2)
        self.inspector.assert_called_once()
        self.assertTrue(result['serviceCapturedWhileLeaseHeld'])
        self.assertNotIn('fixture', seed.canonical(result).decode())

    def test_unclosed_owner_wrong_consumer_or_released_lease_cannot_write_config(self):
        cases = ((self.attempt.owner, '_stage', 'VERIFIED'),
                 (self.attempt.consumer, '_stage', 'ATTACHED'),
                 (self.attempt.consumer, '_borrowed_service', False),
                 (self.attempt.consumer, '_selected_feature', '0' * 40),
                 (self.attempt.consumer, '_held', object()),
                 (self.attempt.held, '_finished', True))
        for obj, field, value in cases:
            with self.subTest(field=field), patch.object(obj, field, value):
                with self.assertRaises(seed.SeedRejected):
                    seed.capture_service(self.attempt, self.args, self.auxiliary)
                self.assertFalse((self.home / 'config.yaml').exists())
        self.attempt.held.finish.assert_not_called()

    def test_failed_real_inspection_port_preserves_partial_profile_and_lease(self):
        self.inspector.side_effect = ValueError('declared inspection failure')
        with self.assertRaises(ValueError):
            seed.capture_service(self.attempt, self.args, self.auxiliary)
        self.assertEqual((self.home / 'config.yaml').read_bytes(), self.raw)
        self.assertIsNone(self.attempt.record)
        self.attempt.held.finish.assert_not_called()


class FailureCustodyTests(unittest.TestCase):
    def test_foreign_exception_text_never_enters_failure_receipt(self):
        attempt = seed.Attempt()
        value = seed.failure_report(attempt, ValueError('credential=owned-test-secret'), time.monotonic())
        self.assertEqual(value['state'], 'REFUSED')
        self.assertNotIn('owned-test-secret', seed.canonical(value).decode())
        self.assertFalse(value['processRetained'])

    def test_verifier_failure_prevents_environment_hooks_and_native_work(self):
        args, attempt = args_for(), seed.Attempt()
        with patch.object(seed, 'validate_actor'), patch.object(seed, 'source_identity',
                return_value={'path': '/reviewed/seed.py', 'sha256': 'a' * 64}), \
                patch.object(seed, 'home_identity'), patch.object(seed.os, 'umask'), \
                patch.object(seed, 'verify_installation', side_effect=seed.SeedRejected('seed_bad_install')), \
                patch.object(seed, 'configure_environment') as environment, \
                patch.object(seed.sys, 'addaudithook') as audit, \
                patch.object(seed, 'native_lifecycle') as lifecycle:
            with self.assertRaises(seed.SeedRejected):
                seed.bootstrap(args, attempt)
        environment.assert_not_called()
        audit.assert_not_called()
        lifecycle.assert_not_called()
        self.assertFalse(attempt.progress['nativeEffectsAttempted'])

    def test_unknown_effect_emits_one_diagnosis_and_retains_original_references(self):
        original = {}
        def fail(args, attempt):
            attempt.progress.update(phase='CAPTURE_SERVICE', nativeEffectsAttempted=True)
            attempt.held = types.SimpleNamespace(finish=Mock())
            attempt.owner = types.SimpleNamespace(close=Mock())
            attempt.consumer = types.SimpleNamespace(detach=Mock())
            original['attempt'] = attempt
            raise seed.SeedRejected('seed_owned_failure')
        out, err = BinaryOutput(), BinaryOutput()
        with patch.object(seed, '_attempt', None), patch.object(seed, 'arguments', return_value=args_for()), \
                patch.object(seed, 'bootstrap', side_effect=fail), \
                patch.object(seed, 'retain_unknown', return_value=91) as retain, \
                patch.object(seed.sys, 'stdout', out), patch.object(seed.sys, 'stderr', err):
            self.assertEqual(seed.main([]), 91)  # Declared stand-in for the indefinite owned wait.
        attempt = original['attempt']
        retain.assert_called_once_with(attempt)
        attempt.held.finish.assert_not_called()
        attempt.owner.close.assert_not_called()
        attempt.consumer.detach.assert_not_called()
        self.assertEqual(out.buffer.getvalue(), b'')
        value = json.loads(err.buffer.getvalue())
        self.assertEqual(value['state'], 'SEED_OUTCOME_UNKNOWN')
        self.assertTrue(value['processRetained'])
        self.assertFalse(value['automaticCleanup'])
        self.assertFalse(value['automaticRetry'])

    def test_preflight_refusal_exits_without_starting_retention(self):
        out, err = BinaryOutput(), BinaryOutput()
        with patch.object(seed, '_attempt', None), patch.object(seed, 'arguments', return_value=args_for()), \
                patch.object(seed, 'bootstrap', side_effect=seed.SeedRejected('seed_preflight_refused')), \
                patch.object(seed, 'retain_unknown') as retain, \
                patch.object(seed.sys, 'stdout', out), patch.object(seed.sys, 'stderr', err):
            self.assertEqual(seed.main([]), 2)
        retain.assert_not_called()
        self.assertEqual(json.loads(err.buffer.getvalue())['state'], 'REFUSED')

    def test_physical_connection_check_requires_three_distinct_closed_handles(self):
        connections = [sqlite3.connect(':memory:') for _ in range(3)]
        self.addCleanup(lambda: [connection.close() for connection in connections])
        connections[0].close()
        connections[1].close()
        with self.assertRaisesRegex(seed.SeedRejected, 'not_physically_closed'):
            seed.physically_closed(tuple(connections))
        connections[2].close()
        seed.physically_closed(tuple(connections))
        with self.assertRaisesRegex(seed.SeedRejected, 'three_original'):
            seed.physically_closed((connections[0],) * 3)


if __name__ == '__main__':
    unittest.main()
