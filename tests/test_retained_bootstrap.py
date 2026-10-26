"""Owned provisioner contracts only; these tests never invoke native Hermes.

The source-scanner fixture, verifier fixture and failure injection below are
explicit doubles. Passing them is not retained-profile/native acceptance.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/bootstrap_retained_profile.py'
SPEC = importlib.util.spec_from_file_location('owned_retained_bootstrap', SOURCE)
seed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seed)


class BinaryOutput:
    def __init__(self):
        self.buffer = io.BytesIO()


class OwnedScanner:
    """Tiny AST fixture with the original scanner's return shape, not its code."""
    @staticmethod
    def _tool_module_candidates(root):
        return sorted(list(root.glob('*.py')) + list(root.glob('*/tool.py')))

    @staticmethod
    def _module_registers_tools(path):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == 'register' for node in ast.walk(tree))


class ArgumentAndProtocolTests(unittest.TestCase):
    def test_decimal_rejects_ambiguous_or_unbounded_actor_numbers(self):
        self.assertEqual(seed.decimal('23001'), 23001)
        self.assertEqual(seed.decimal(str(2**64 - 1)), 2**64 - 1)
        for value in ('0', '01', '+1', '-1', ' 1', '1.0', '1e3', str(2**64), True, 1):
            with self.subTest(value=value), self.assertRaises(seed.BootstrapRejected):
                seed.decimal(value)

    def test_home_requires_canonical_absolute_explicit_path(self):
        self.assertEqual(seed.canonical_home('/srv/owned/profile'), Path('/srv/owned/profile'))
        for value in ('relative', '/', '//srv/profile', '/srv//profile', '/srv/./profile',
                      '/srv/../profile', '/srv/profile/', '/srv/\x00profile', '/srv\\profile'):
            with self.subTest(value=value), self.assertRaises(seed.BootstrapRejected):
                seed.canonical_home(value)

    def test_json_is_one_ascii_canonical_frame_and_refuses_nan(self):
        raw = seed.canonical({'b': '\nİ', 'a': 3})
        self.assertEqual(raw, b'{"a":3,"b":"\\n\\u0130"}\n')
        self.assertEqual(raw.count(b'\n'), 1)
        self.assertEqual(json.loads(raw), {'a': 3, 'b': '\nİ'})
        with self.assertRaises(ValueError):
            seed.canonical({'value': float('nan')})

    def test_environment_is_credential_free_without_repurposing_home(self):
        home = Path('/srv/owned/profile')
        inherited = {'HOME': '/private', 'OPENAI_API_KEY': 'owned-test',
                     'PYTHONPATH': '/untrusted', 'HTTP_PROXY': 'http://unused'}
        with patch.object(seed.os, 'environ', inherited):
            seed.configure_environment(home)
            self.assertEqual(dict(os.environ), {
                'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
                'HERMES_HOME': str(home), 'TMPDIR': str(home)})

    def test_failed_verifier_prevents_environment_audit_or_native_lifecycle(self):
        progress = {'phase': 'ARGUMENTS', 'nativeEffectsAttempted': False}
        with patch.object(seed, 'validate_arguments', return_value=Path('/owned/profile')), \
                patch.object(seed, 'validate_actor'), patch.object(seed, 'home_identity'), \
                patch.object(seed.os, 'umask'), \
                patch.object(seed, 'verify_installation', side_effect=seed.BootstrapRejected('owned_bad_verifier')), \
                patch.object(seed, 'configure_environment') as environment, \
                patch.object(seed.sys, 'addaudithook') as audit, \
                patch.object(seed, 'native_lifecycle') as lifecycle:
            with self.assertRaisesRegex(seed.BootstrapRejected, 'owned_bad_verifier'):
                seed.bootstrap(argparse.Namespace(), progress)
        environment.assert_not_called()
        audit.assert_not_called()
        lifecycle.assert_not_called()
        self.assertEqual(progress, {'phase': 'VERIFY_INSTALLATION', 'nativeEffectsAttempted': False})

    def test_pinned_verifier_refusal_retains_only_a_finite_reason_code(self):
        # Owned verifier double; neither installation nor native code runs.
        for reason, expected in (
                ('installation_file_changed', seed.BootstrapRejected),
                ('owned-sensitive path detail', ValueError)):
            raw = ('class InstallationRejected(ValueError): pass\n'
                   'def verify_installed(*args, **kwargs):\n'
                   '    raise InstallationRejected(' + repr(reason) + ')\n').encode()
            with patch.object(seed, '_trusted_installer_bytes', return_value=raw), \
                    patch.dict(seed.sys.modules, dict(seed.sys.modules)):
                seed.sys.modules.pop('_alaz_r155_verified_installer', None)
                with self.assertRaises(expected) as caught:
                    seed.verify_installation()
                if expected is seed.BootstrapRejected:
                    self.assertEqual(str(caught.exception), 'bootstrap_installation_file_changed')
                else:
                    self.assertNotIsInstance(caught.exception, seed.BootstrapRejected)

    def test_native_failure_preserves_fresh_entry_checks_and_retires_observers(self):
        progress = {'phase': 'ARGUMENTS', 'nativeEffectsAttempted': False}
        async def fail(*args):
            raise seed.BootstrapRejected('owned_native_failure')
        with patch.object(seed, 'validate_arguments', return_value=Path('/owned/profile')), \
                patch.object(seed, 'validate_actor'), patch.object(seed, 'home_identity') as identity, \
                patch.object(seed.os, 'umask'), patch.object(seed, 'verify_installation', return_value={}), \
                patch.object(seed, 'configure_environment'), patch.object(seed.sys, 'addaudithook'), \
                patch.object(seed.sys, 'path', list(sys.path)), \
                patch.object(seed.sys, 'setprofile') as profile, \
                patch.object(seed.threading, 'setprofile') as threads, \
                patch.object(seed, 'native_lifecycle', side_effect=fail):
            with self.assertRaisesRegex(seed.BootstrapRejected, 'owned_native_failure'):
                seed.bootstrap(argparse.Namespace(), progress)
        self.assertEqual([call.kwargs for call in identity.call_args_list], [{'fresh': True}] * 2)
        self.assertIsNone(profile.call_args_list[-1].args[0])
        self.assertIsNone(threads.call_args_list[-1].args[0])
        self.assertTrue(progress['nativeEffectsAttempted'])

    def test_failure_protocol_preserves_partial_effects_and_has_no_success_stdout(self):
        argv = ['--home', '/owned/profile', '--instance-id', 'owned-seed',
                '--expected-profile-device', '123', '--expected-profile-inode', '456',
                '--gateway-uid', '23001', '--socket-group-gid', '23003', '--parent-pid', '1200']
        for attempted in (False, True):
            def fail(args, progress):
                progress.update(phase='NATIVE_IMPORTS' if attempted else 'VERIFY_INSTALLATION',
                                nativeEffectsAttempted=attempted)
                raise RuntimeError('owned-sensitive-text-must-not-escape')
            output, errors = BinaryOutput(), BinaryOutput()
            with patch.object(seed, 'bootstrap', side_effect=fail), \
                    patch.object(seed.sys, 'stdout', output), patch.object(seed.sys, 'stderr', errors):
                self.assertEqual(seed.main(argv), 2)
            self.assertEqual(output.buffer.getvalue(), b'')
            raw = errors.buffer.getvalue()
            self.assertLessEqual(len(raw), seed.MAX_RESULT)
            self.assertNotIn(b'owned-sensitive', raw)
            value = json.loads(raw)
            self.assertEqual(value['state'], 'SEED_OUTCOME_UNKNOWN' if attempted else 'REFUSED')
            self.assertTrue(value['partialStatePreserved'])
            self.assertFalse(value['automaticCleanup'])
            self.assertFalse(value['automaticRetry'])
            self.assertEqual(value['result'], 'NOT_ACCEPTED')
            self.assertGreaterEqual(value['totalMillis'], 0)


class OwnedFiles(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='alaz-owned-bootstrap-test-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name).resolve()
        self.home = self.root / 'profile'
        self.home.mkdir(mode=0o700)


class OwnedFilesystemTests(OwnedFiles):
    @unittest.skipUnless(sys.platform == 'linux', 'Linux fd and permission contract')
    def test_fresh_home_is_observed_not_created_or_reused(self):
        info = self.home.stat()
        args = argparse.Namespace(gateway_uid=info.st_uid, socket_group_gid=info.st_gid,
                                  expected_profile_device=info.st_dev, expected_profile_inode=info.st_ino)
        self.assertEqual(seed.home_identity(self.home, args, fresh=True), (info.st_dev, info.st_ino))
        retained = self.home / 'owned-partial-state'
        retained.write_bytes(b'preserve')
        with self.assertRaisesRegex(seed.BootstrapRejected, 'home_not_empty'):
            seed.home_identity(self.home, args, fresh=True)
        self.assertEqual(retained.read_bytes(), b'preserve')
        self.assertEqual(seed.home_identity(self.home, args, fresh=False), (info.st_dev, info.st_ino))
        args.expected_profile_inode += 1
        with self.assertRaisesRegex(seed.BootstrapRejected, 'home_identity'):
            seed.home_identity(self.home, args, fresh=False)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux fd and permission contract')
    def test_home_wrong_mode_or_symlink_is_refused(self):
        info = self.home.stat()
        args = argparse.Namespace(gateway_uid=info.st_uid, socket_group_gid=info.st_gid,
                                  expected_profile_device=info.st_dev, expected_profile_inode=info.st_ino)
        self.home.chmod(0o755)
        with self.assertRaisesRegex(seed.BootstrapRejected, 'home_identity'):
            seed.home_identity(self.home, args, fresh=True)
        self.home.chmod(0o700)
        linked = self.root / 'linked'
        linked.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(seed.BootstrapRejected, 'home_alias'):
            seed.home_identity(linked, args, fresh=True)

    def fixture_tree(self):
        native = self.root / 'native'
        contents = {
            'tools/alpha.py': 'registry.register(name="owned")\n',
            'tools/plain.py': 'VALUE = 1\n',
            'tools/__init__.py': '', 'tools/registry.py': '', 'tools/mcp_tool.py': '',
            'tools/nested/__init__.py': '', 'tools/nested/tool.py': 'registry.register(name="nested")\n',
        }
        hashes = {}
        for name, content in contents.items():
            path = native / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = content.encode('utf-8')
            path.write_bytes(raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
        return native, hashes

    def test_discovery_rows_use_real_qualified_source_stats_and_scanner(self):
        native, hashes = self.fixture_tree()
        rows = seed.source_discovery_rows((native, hashes), OwnedScanner)
        self.assertEqual(set(rows), {str(native / n) for n in (
            'tools/alpha.py', 'tools/plain.py', 'tools/nested/tool.py')})
        for path, row in rows.items():
            info = Path(path).stat()
            self.assertEqual(row[:2], [info.st_mtime_ns, info.st_size])
            self.assertIs(row[2], not path.endswith('plain.py'))

    def test_changed_tool_bytes_are_refused_without_rewriting_them(self):
        native, hashes = self.fixture_tree()
        changed = native / 'tools/alpha.py'
        changed.write_bytes(b'changed = True\n')
        with self.assertRaisesRegex(seed.BootstrapRejected, 'source_changed'):
            seed.source_discovery_rows((native, hashes), OwnedScanner)
        self.assertEqual(changed.read_bytes(), b'changed = True\n')

    def test_unqualified_or_missing_candidate_is_refused(self):
        native, hashes = self.fixture_tree()
        extra = native / 'tools/unqualified.py'
        extra.write_text('VALUE = 2', encoding='utf-8')
        with self.assertRaisesRegex(seed.BootstrapRejected, 'candidates_changed'):
            seed.source_discovery_rows((native, hashes), OwnedScanner)
        extra.unlink()  # Owned fixture teardown only; producer never repairs a profile.
        (native / 'tools/alpha.py').unlink()
        with self.assertRaisesRegex(seed.BootstrapRejected, 'candidates_changed'):
            seed.source_discovery_rows((native, hashes), OwnedScanner)

    def test_duplicate_candidate_or_nonbool_scanner_result_is_refused(self):
        native, hashes = self.fixture_tree()
        candidates = OwnedScanner._tool_module_candidates(native / 'tools')
        duplicate = types.SimpleNamespace(_tool_module_candidates=lambda _: candidates + [native / 'tools/alpha.py'])
        with self.assertRaisesRegex(seed.BootstrapRejected, 'candidates_changed'):
            seed.source_discovery_rows((native, hashes), duplicate)
        wrong_type = types.SimpleNamespace(_tool_module_candidates=lambda _: candidates,
                                           _module_registers_tools=lambda _: 1)
        with self.assertRaisesRegex(seed.BootstrapRejected, 'source_changed'):
            seed.source_discovery_rows((native, hashes), wrong_type)

    def test_scanner_time_source_change_is_refused(self):
        native, hashes = self.fixture_tree()
        def mutating(path):
            path.write_bytes(path.read_bytes() + b'# fixture change\n')
            return False
        scanner = types.SimpleNamespace(_tool_module_candidates=OwnedScanner._tool_module_candidates,
                                        _module_registers_tools=mutating)
        with self.assertRaisesRegex(seed.BootstrapRejected, 'source_changed'):
            seed.source_discovery_rows((native, hashes), scanner)

    @unittest.skipUnless(sys.platform == 'linux', 'Owned POSIX symlink fixture')
    def test_discovery_symlink_is_refused_even_with_matching_content(self):
        native, hashes = self.fixture_tree()
        target = native / 'tools/alpha.py'
        outside = self.root / 'outside.py'
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaisesRegex(seed.BootstrapRejected, 'source_file'):
            seed.source_discovery_rows((native, hashes), OwnedScanner)

    def test_closed_connections_are_physically_probed(self):
        connection = sqlite3.connect(':memory:')
        with self.assertRaisesRegex(seed.BootstrapRejected, 'not_physically_closed'):
            seed.physically_closed([connection])
        connection.close()
        seed.physically_closed([connection])


class AuditContractTests(OwnedFiles):
    # No global audit hook is installed in the test process. All calls below
    # exercise the same decision function with owned event data before effects.
    def boundary(self, phase='START_OWNER'):
        return seed.OfflineBoundary(self.home, {'phase': phase})

    def test_caught_audit_refusal_keeps_finite_evidence_without_argument_data(self):
        progress = {'phase': 'NATIVE_IMPORTS'}
        boundary = seed.OfflineBoundary(self.home, progress)
        with self.assertRaises(seed.BootstrapRejected):
            boundary('socket.connect', ('owned-sensitive-argument',))
        self.assertIs(progress['boundaryRejections'], boundary.denied)
        self.assertIs(progress['nativeWorkAttempts'], boundary.native_work_attempts)
        self.assertEqual(boundary.denied[0], {
            'phase': 'NATIVE_IMPORTS', 'reason': 'bootstrap_network_or_process_forbidden',
            'event': 'socket.connect', 'sources': []})
        self.assertNotIn('owned-sensitive', json.dumps(progress))

    def owned_ipv6_probe(self, boundary, host='::1', *, close=True, source=None):
        # Pure Python socket double; this test creates no OS socket or bind.
        class OwnedSocket:
            def __init__(self, family):
                self.family = family
                self.type = seed.socket.SOCK_STREAM
                self.proto = 0
                self.fd = 42
            def fileno(self):
                return self.fd
            def close(self):
                if close:
                    self.fd = -1
        module = types.ModuleType('urllib3.util.connection')
        module.__file__ = source or boundary.ipv6_source
        module.boundary, module.socket = boundary, seed.socket
        code = '''def _has_ipv6(host):
    sock = socket.socket(socket.AF_INET6)
    try:
        boundary('socket.bind', (sock, (host, 0)))
        raise AssertionError('The owned bind must always be refused')
    except (PermissionError, ValueError):
        pass
    if sock:
        sock.close()
    return False
'''
        exec(compile(code, module.__file__, 'exec'), vars(module))
        return module, OwnedSocket

    def test_original_ipv6_probe_remains_blocked_and_its_socket_close_is_observed(self):
        boundary = self.boundary('PREPARE_CONSUMER')
        module, owned_socket = self.owned_ipv6_probe(boundary)
        with patch.dict(sys.modules, {'urllib3.util.connection': module}), \
                patch.object(seed.socket, 'socket', owned_socket):
            module.HAS_IPV6 = module._has_ipv6('::1')
            self.assertEqual(boundary.ipv6_probe_closed(), {
                'count': 1, 'socketClosed': True, 'bindPerformed': False})
            self.assertEqual(boundary.denied, [])
            self.assertEqual(len(boundary.blocked_ipv6_sockets), 1)
            module._has_ipv6('::1')  # A second probe is an unexpected denial.
            self.assertEqual(len(boundary.blocked_ipv6_sockets), 1)
            self.assertEqual(len(boundary.denied), 1)

    def test_unqualified_ipv6_phase_source_host_or_caller_never_gets_probe_exemption(self):
        for fault in ('phase', 'source', 'host', 'caller'):
            boundary = self.boundary('NATIVE_IMPORTS' if fault == 'phase' else 'PREPARE_CONSUMER')
            module, owned_socket = self.owned_ipv6_probe(boundary,
                source='/owned/other.py' if fault == 'source' else None)
            with patch.dict(sys.modules, {'urllib3.util.connection': module}), \
                    patch.object(seed.socket, 'socket', owned_socket):
                if fault == 'caller':
                    with self.assertRaises(seed.BootstrapRejected):
                        boundary('socket.bind', (owned_socket(seed.socket.AF_INET6), ('::1', 0)))
                else:
                    module._has_ipv6('::2' if fault == 'host' else '::1')
            self.assertEqual(boundary.blocked_ipv6_sockets, [])
            self.assertEqual(len(boundary.denied), 1)

    def test_missing_physical_ipv6_socket_close_is_not_accepted(self):
        boundary = self.boundary('PREPARE_CONSUMER')
        module, owned_socket = self.owned_ipv6_probe(boundary, close=False)
        with patch.dict(sys.modules, {'urllib3.util.connection': module}), \
                patch.object(seed.socket, 'socket', owned_socket):
            module.HAS_IPV6 = module._has_ipv6('::1')
            with self.assertRaisesRegex(seed.BootstrapRejected, 'ipv6_probe_not_closed'):
                boundary.ipv6_probe_closed()

    def owned_schema_double(self, boundary):
        module = types.ModuleType('hermes_state_schema')
        module.__file__ = str(seed.INSTALLATION / 'native/hermes_state_schema.py')
        module.SCHEMA_SQL = 'CREATE TABLE owned_reference (value TEXT)'
        module.boundary = boundary
        code = '''class SessionSchemaMixin:
    @staticmethod
    def _parse_schema_columns(schema_sql):
        boundary('sqlite3.connect', (':memory:',))
'''
        exec(compile(code, module.__file__, 'exec'), vars(module))
        return module

    def test_only_original_schema_reference_can_open_memory_once_and_is_closed(self):
        boundary = self.boundary('CREATE_COLD_STORES')
        module = self.owned_schema_double(boundary)
        with patch.dict(sys.modules, {'hermes_state_schema': module}):
            module.SessionSchemaMixin._parse_schema_columns(module.SCHEMA_SQL)
            with self.assertRaisesRegex(seed.BootstrapRejected, 'database_path_forbidden'):
                module.SessionSchemaMixin._parse_schema_columns(module.SCHEMA_SQL)
        self.assertEqual(boundary.reference_schema_opens, 1)
        connection = sqlite3.connect(':memory:')  # Owned test connection; no global hook.
        connection.close()
        boundary('sqlite3.connect/handle', (connection,))
        self.assertFalse(boundary.reference_handle_pending)
        self.assertEqual(boundary.reference_connections, [connection])
        seed.physically_closed(boundary.reference_connections)

    def test_schema_memory_exception_rejects_other_phase_sql_source_and_caller(self):
        for fault in ('phase', 'sql', 'source', 'caller'):
            boundary = self.boundary('START_OWNER' if fault == 'phase' else 'CREATE_COLD_STORES')
            module = self.owned_schema_double(boundary)
            sql = module.SCHEMA_SQL.encode().decode() if fault == 'sql' else module.SCHEMA_SQL
            if fault == 'sql':
                self.assertIsNot(sql, module.SCHEMA_SQL)
            if fault == 'source':
                module.__file__ = '/owned/unqualified.py'
            with patch.dict(sys.modules, {'hermes_state_schema': module}), \
                    self.assertRaisesRegex(seed.BootstrapRejected, 'database_path_forbidden'):
                if fault == 'caller':
                    boundary('sqlite3.connect', (':memory:',))
                else:
                    module.SessionSchemaMixin._parse_schema_columns(sql)
            self.assertEqual(boundary.reference_schema_opens, 0)

    def helper_event(self, script, **overrides):
        event = {'executable': seed.PYTHON,
                 'argv': [seed.PYTHON, '-I', '-B', str(seed.INSTALLATION / 'scripts' / script)],
                 'cwd': str(seed.INSTALLATION),
                 'env': {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/'}}
        event.update(overrides)
        return event['executable'], event['argv'], event['cwd'], event['env']

    def test_only_original_two_helpers_in_original_order_are_allowed(self):
        boundary = self.boundary()
        for script in seed.HELPERS:
            boundary('subprocess.Popen', self.helper_event(script))
        self.assertEqual([x['script'] for x in boundary.helpers], list(seed.HELPERS))
        with self.assertRaisesRegex(seed.BootstrapRejected, 'process_forbidden'):
            boundary('subprocess.Popen', self.helper_event(seed.HELPERS[0]))

    def test_helper_environment_argv_phase_and_order_cannot_expand(self):
        cases = [self.helper_event(seed.HELPERS[1]),
                 self.helper_event(seed.HELPERS[0], env={'PATH': '/usr/bin:/bin'}),
                 self.helper_event(seed.HELPERS[0], argv=[seed.PYTHON, '-c', 'pass']),
                 self.helper_event(seed.HELPERS[0], cwd=str(self.home))]
        for event in cases:
            with self.subTest(event=event), self.assertRaises(seed.BootstrapRejected):
                self.boundary()('subprocess.Popen', event)
        with self.assertRaises(seed.BootstrapRejected):
            self.boundary('PREPARE_CONSUMER')('subprocess.Popen', self.helper_event(seed.HELPERS[0]))

    def test_network_and_unqualified_process_events_are_denied(self):
        for event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'socket.gethostbyname',
                      'socket.getnameinfo', 'socket.sendto', 'os.system', 'os.exec', 'os.fork',
                      'os.posix_spawn'):
            with self.subTest(event=event), self.assertRaises(seed.BootstrapRejected):
                self.boundary()(event, ())

    def test_database_paths_are_fixed_and_not_taken_from_a_uri(self):
        boundary = self.boundary('CREATE_COLD_STORES')
        for name in ('state.db', 'runs_idempotency.db', 'response_store.db'):
            boundary('sqlite3.connect', (str(self.home / name),))
        self.assertEqual(len(boundary.sqlite_opens), 3)
        for name in (':memory:', str(self.root / 'elsewhere.db'), 'file:' + str(self.home / 'state.db')):
            with self.subTest(name=name), self.assertRaises(seed.BootstrapRejected):
                boundary('sqlite3.connect', (name,))

    def test_profile_mutations_refuse_parent_escape_or_relative_paths(self):
        boundary = self.boundary()
        boundary('open', (str(self.home / 'owned'), None, os.O_WRONLY | os.O_CREAT))
        for path in (str(self.root / 'outside'), str(self.home / '..' / 'escape'), 'relative'):
            with self.subTest(path=path), self.assertRaises(seed.BootstrapRejected):
                boundary('open', (path, None, os.O_WRONLY))
        with self.assertRaises(seed.BootstrapRejected):
            boundary('os.rename', (str(self.home / 'owned'), str(self.root / 'outside'), -1, -1))

    @unittest.skipUnless(sys.platform == 'linux', 'Owned POSIX symlink fixture')
    def test_profile_mutation_refuses_symlink_escape(self):
        outside = self.root / 'outside'
        outside.mkdir()
        alias = self.home / 'alias'
        alias.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(seed.BootstrapRejected):
            self.boundary()('open', (str(alias / 'new'), None, os.O_CREAT | os.O_WRONLY))


if __name__ == '__main__':
    unittest.main()
