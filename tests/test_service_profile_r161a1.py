"""Selected service-profile contracts; native loader/model/kernel not exercised."""
import builtins
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_service_profile as service
import gateway_native_layout as layout
import gateway_retained_profile as retained
from service_profile_fixtures_r161a1 import arguments, canonical, set_up_profile


def expectation():
    return service.ServiceProfileExpectation(1,
        service.sources.ServiceSourceSelection('a' * 40, 'b' * 64, 'c' * 64),
        '/alaz/state/profile', (77, 1), ((77, 2), (77, 3), (77, 4)),
        1, 'previous-instance', 'd' * 64, (77, 5), 2, 'e' * 64)


class ExpectationContracts(unittest.TestCase):
    def test_exact_typed_expectation_without_io(self):
        value = expectation()
        with patch.object(service.sources, 'load_selection', side_effect=AssertionError('source I/O')), \
             patch.object(Path, 'resolve', side_effect=AssertionError('filesystem I/O')):
            self.assertIs(service.validate_expectation(value), value)

    def test_plain_mapping_or_subclass_not_a_typed_expectation(self):
        class Other(service.ServiceProfileExpectation):
            pass
        values = (None, True, asdict(expectation()), Other(**expectation().__dict__))
        for value in values:
            with self.subTest(value_type=type(value).__name__), self.assertRaises(service.ServiceProfileRejected):
                service.validate_expectation(value)

    def test_schema_generation_and_config_fields_are_strict(self):
        changes = ({'schema': True}, {'schema': 2}, {'epoch': True}, {'epoch': 0},
                   {'epoch': 2**63}, {'instance_id': ''}, {'instance_id': 'bad/value'},
                   {'config_size': True}, {'config_size': 0},
                   {'config_size': service.MAX_CONFIG_BYTES + 1},
                   {'config_sha256': 'x' * 64}, {'discovery_sha256': 'A' * 64})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(service.ServiceProfileRejected):
                service.validate_expectation(replace(expectation(), **change))

    def test_identities_do_not_alias_or_cross_devices(self):
        changes = ({'home_identity': [77, 1]}, {'home_identity': (77, True)},
                   {'config_identity': (77, 1)}, {'config_identity': (78, 5)},
                   {'database_identities': [(77, 2), (77, 3), (77, 4)]},
                   {'database_identities': ((77, 2), (77, 2), (77, 4))},
                   {'database_identities': ((77, 2), (77, 3))},
                   {'config_identity': (77, 2**64)})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(service.ServiceProfileRejected):
                service.validate_expectation(replace(expectation(), **change))

    def test_selection_type_and_all_three_digests_bound(self):
        value = expectation()
        changes = (None, asdict(value.selection),
                   replace(value.selection, native_feature='a' * 39),
                   replace(value.selection, manifest_sha256='x' * 64),
                   replace(value.selection, selection_sha256='a' * 63))
        for selected in changes:
            with self.subTest(selected=selected), self.assertRaises(service.ServiceProfileRejected):
                service.validate_expectation(replace(value, selection=selected))

    def test_structural_home_is_canonical_and_posix_portable(self):
        service.validate_expectation(expectation())
        for home in ('relative', '/alaz/../profile', '/alaz/./profile', '/alaz//profile',
                     '//alaz/profile', '/alaz/profile/', '/alaz\\profile', '/alaz/\x00profile'):
            with self.subTest(home=repr(home)), self.assertRaises(service.ServiceProfileRejected):
                service.validate_expectation(replace(expectation(), home=home))


class ServiceProfileContracts(unittest.TestCase):
    def setUp(self):
        set_up_profile(self)

    def inspect(self, value=None):
        return service.inspect_profile(self.home, **arguments(self, value))

    def check(self, value=None):
        return service.check_config(self.home, **arguments(self, value))

    def write(self, name, raw):
        path = self.home / name
        path.write_bytes(raw)
        path.chmod(0o600)

    def select_raw(self, raw):
        self.write(service.CONFIG_NAME, raw)
        self.expectation = replace(self.expectation, config_size=len(raw),
                                   config_sha256=hashlib.sha256(raw).hexdigest())

    def test_exact_profile_and_private_config_proof_do_not_write(self):
        before = {p.relative_to(self.home).as_posix(): p.read_bytes()
                  for p in self.home.rglob('*') if p.is_file()}
        snapshot = self.inspect()
        self.assertEqual(set(snapshot), service._REQUIRED | {'profile'})
        result = self.check()
        self.assertEqual(result['state'], 'SERVICE_CONFIG_BOUND')
        self.assertEqual(result['configSha256'], self.expectation.config_sha256)
        for flag in ('databaseOpened', 'nativeConfigLoaded', 'modelPolicyQualified',
                     'runtimeAdmissionAuthorized'):
            self.assertIs(result[flag], False)
        serialized = json.dumps(result)
        self.assertNotIn('fixture-model', serialized)
        self.assertNotIn(str(self.home), serialized)
        after = {p.relative_to(self.home).as_posix(): p.read_bytes()
                 for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_old_cold_prepared_and_retained_paths_still_reject_config(self):
        old = retained.RetainedProfileExpectation(retained.FEATURE, str(self.home),
            self.expectation.home_identity, self.expectation.database_identities,
            self.expectation.epoch, self.expectation.instance_id,
            self.expectation.discovery_sha256)
        for options in ({}, {'include_response': True, 'include_prepared': True},
                        {'include_response': True, 'include_prepared': True, 'retained': old}):
            with self.subTest(options=tuple(options)), self.assertRaises(layout.NativeLayoutRejected):
                layout.inspect_profile(self.home, uid=self.uid, gid=self.gid,
                                       device=self.device, **options)

    def test_source_mismatch_rejected_before_profile_access(self):
        bad = replace(self.selection, native_feature='a' * 40)
        for operation in (self.inspect, self.check):
            with patch.object(service.sources, 'load_selection', return_value=bad), \
                 patch.object(service, '_home') as home, self.assertRaisesRegex(
                     service.ServiceProfileRejected, 'source_changed'):
                operation()
            home.assert_not_called()

    def test_selected_manifest_must_match_before_profile_access(self):
        for operation in (self.inspect, self.check):
            with patch.object(service.sources, 'selected_manifest',
                              side_effect=service.sources.ServiceSourcesRejected('private-manifest-path')), \
                 patch.object(service, '_home') as home, self.assertRaisesRegex(
                     service.ServiceProfileRejected, '^service_profile_source_rejected$'):
                operation()
            home.assert_not_called()

    def test_invalid_expectation_has_no_source_or_profile_io(self):
        with patch.object(service.sources, 'load_selection') as selected, \
             patch.object(service, '_home') as home, self.assertRaises(service.ServiceProfileRejected):
            self.inspect(replace(self.expectation, schema=True))
        selected.assert_not_called()
        home.assert_not_called()

    def test_source_change_during_read_rejected(self):
        actual_read = service._read_config
        actual_selection = service.sources.load_selection
        changed = False
        def read(home, *args):
            nonlocal changed
            raw = actual_read(home, *args)
            changed = True
            return raw
        def selected():
            return replace(self.selection, native_feature='a' * 40) if changed else actual_selection()
        with patch.object(service, '_read_config', side_effect=read), \
             patch.object(service.sources, 'load_selection', side_effect=selected), \
             self.assertRaisesRegex(service.ServiceProfileRejected, 'source_changed'):
            self.inspect()

    def test_missing_config_or_retained_entry_rejected(self):
        for name in (service.CONFIG_NAME, 'runtime/active_sessions.json',
                     'cache/tool_discovery_cache.json', 'auth.lock'):
            raw = (self.home / name).read_bytes()
            (self.home / name).unlink()
            try:
                with self.subTest(name=name), self.assertRaises(service.ServiceProfileRejected):
                    self.inspect()
            finally:
                self.write(name, raw)

    def test_unexpected_profile_payload_rejected(self):
        for name in ('.env', 'auth.json', 'another.yaml', 'runtime/unrelated.json',
                     'hooks/payload.py', 'skills/payload.py', 'cache/documents/payload.txt'):
            self.write(name, b'fixture-only')
            try:
                with self.subTest(name=name), self.assertRaises(service.ServiceProfileRejected):
                    self.inspect()
            finally:
                (self.home / name).unlink()

    def test_all_three_database_identities_bound(self):
        for index in range(3):
            identities = list(self.expectation.database_identities)
            identities[index] = (self.device, 2**62 + index)
            with self.subTest(index=index), self.assertRaisesRegex(
                    service.ServiceProfileRejected, 'database_identity'):
                self.inspect(replace(self.expectation, database_identities=tuple(identities)))

    def test_profile_and_config_identity_bound(self):
        for value in (replace(self.expectation, home_identity=(self.device, 2**62)),
                      replace(self.expectation, config_identity=(self.device, 2**62))):
            for operation in (self.inspect, self.check):
                with self.subTest(operation=operation.__name__), self.assertRaises(service.ServiceProfileRejected):
                    operation(value)

    def test_home_and_device_mismatch_refused(self):
        for kwargs in ({**arguments(self), 'device': self.device + 1},
                       arguments(self, replace(self.expectation, home=str(self.home / 'other')))):
            with self.assertRaises(service.ServiceProfileRejected):
                service.inspect_profile(self.home, **kwargs)

    def test_same_size_changed_config_content_refused(self):
        raw = self.config_bytes.replace(b'fixture-model', b'changed-model')
        self.assertEqual(len(raw), len(self.config_bytes))
        self.write(service.CONFIG_NAME, raw)
        for operation in (self.inspect, self.check):
            with self.assertRaisesRegex(service.ServiceProfileRejected, 'config_changed'):
                operation()

    def test_same_bytes_replacement_inode_refused(self):
        path = self.home / service.CONFIG_NAME
        saved = self.home / 'old-config'
        path.rename(saved)
        self.write(service.CONFIG_NAME, self.config_bytes)
        saved.unlink()
        for operation in (self.inspect, self.check):
            with self.assertRaisesRegex(service.ServiceProfileRejected, 'identity_or_size'):
                operation()

    def test_config_size_bound_before_any_profile_file_open(self):
        self.write(service.CONFIG_NAME, b'x' * (service.MAX_CONFIG_BYTES + 1))
        for operation in (self.inspect, self.check):
            with patch.object(service, '_read_aux') as opened, \
                 patch.object(service, '_read_config') as config_opened, self.assertRaisesRegex(
                    service.ServiceProfileRejected, 'config_size'):
                operation()
            opened.assert_not_called()
            config_opened.assert_not_called()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX mode/owner contract; Windows fixture doubles metadata')
    def test_config_owner_and_mode_are_private(self):
        path = self.home / service.CONFIG_NAME
        path.chmod(0o644)
        for operation in (self.inspect, self.check):
            with self.assertRaises(service.ServiceProfileRejected):
                operation()
        path.chmod(0o600)
        with self.assertRaises(service.ServiceProfileRejected):
            service.check_config(self.home, **{**arguments(self), 'uid': self.uid + 1})

    @unittest.skipIf(sys.platform == 'win32', 'POSIX symlink contract')
    def test_config_symlink_refused_before_open(self):
        path = self.home / service.CONFIG_NAME
        path.unlink()
        path.symlink_to(self.home / 'SOUL.md')
        for operation in (self.inspect, self.check):
            with patch.object(service, '_read_aux') as opened, \
                 patch.object(service, '_read_config') as config_opened, self.assertRaises(service.ServiceProfileRejected):
                operation()
            opened.assert_not_called()
            config_opened.assert_not_called()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX symlink contract')
    def test_home_symlink_alias_refused(self):
        alias = self.home / 'alias'
        alias.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(service.ServiceProfileRejected, 'canonical_home'):
            service.check_config(alias, **arguments(self, replace(self.expectation, home=str(alias))))

    @unittest.skipIf(sys.platform == 'win32', 'POSIX hardlink contract')
    def test_config_hardlink_refused(self):
        path = self.home / service.CONFIG_NAME
        path.unlink()
        os.link(self.home / 'SOUL.md', path)
        for operation in (self.inspect, self.check):
            with self.assertRaises(service.ServiceProfileRejected):
                operation()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX FIFO contract')
    def test_config_fifo_refused_without_blocking_open(self):
        path = self.home / service.CONFIG_NAME
        path.unlink()
        os.mkfifo(path, 0o600)
        for operation in (self.inspect, self.check):
            with patch.object(service, '_read_aux') as opened, \
                 patch.object(service, '_read_config') as config_opened, self.assertRaises(service.ServiceProfileRejected):
                operation()
            opened.assert_not_called()
            config_opened.assert_not_called()

    def test_only_selected_auxiliary_files_opened_no_sqlite_or_locks(self):
        actual = layout.os.open
        opened = []
        def read(path, *args, **kwargs):
            opened.append(Path(path).relative_to(self.home).as_posix())
            return actual(path, *args, **kwargs)
        with patch.object(layout.os, 'open', side_effect=read):
            self.inspect()
        self.assertEqual(opened, ['SOUL.md', 'cache/schema_columns.json',
                                 'cache/tool_discovery_cache.json',
                                 'runtime/active_sessions.json', 'config.yaml'])
        opened.clear()
        with patch.object(layout.os, 'open', side_effect=read):
            self.check()
        self.assertEqual(opened, ['config.yaml'])

    def test_config_change_between_snapshot_and_open_refused(self):
        actual = service._read_config
        def read(home, *args):
            self.write(service.CONFIG_NAME, self.config_bytes.replace(b'fixture-model', b'changed-model'))
            return actual(home, *args)
        with patch.object(service, '_read_config', side_effect=read), \
             self.assertRaises(service.ServiceProfileRejected):
            self.inspect()

    def test_open_descriptor_metadata_change_refused(self):
        actual = layout.os.fstat
        def changed(fd):
            info = actual(fd)
            keys = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid',
                    'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            values = {key: getattr(info, key) for key in keys}
            values['st_ino'] += 1
            return SimpleNamespace(**values)
        with patch.object(layout.os, 'fstat', side_effect=changed), \
             self.assertRaises(service.ServiceProfileRejected):
            self.check()

    def test_config_replacement_after_read_refused(self):
        actual = service._read_config
        def read(home, *args):
            raw = actual(home, *args)
            path = self.home / service.CONFIG_NAME
            saved = self.home / 'old-config'
            path.rename(saved)
            self.write(service.CONFIG_NAME, raw)
            saved.unlink()
            return raw
        for operation in (self.inspect, self.check):
            # Each iteration starts with its explicitly supplied fixture identity.
            path = self.home / service.CONFIG_NAME
            self.expectation = replace(self.expectation,
                config_identity=(path.stat().st_dev, path.stat().st_ino))
            with patch.object(service, '_read_config', side_effect=read), \
                 self.assertRaises(service.ServiceProfileRejected):
                operation()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX nonblocking FIFO race contract')
    def test_fifo_swap_between_lstat_and_open_is_nonblocking_and_refused(self):
        actual = service.os.open
        def swapped(path, flags, *args, **kwargs):
            if Path(path).name == service.CONFIG_NAME:
                self.assertTrue(flags & os.O_NONBLOCK)
                Path(path).unlink()
                os.mkfifo(path, 0o600)
            return actual(path, flags, *args, **kwargs)
        with patch.object(service.os, 'open', side_effect=swapped), \
             self.assertRaisesRegex(service.ServiceProfileRejected, 'fd_changed'):
            self.check()

    @unittest.skipIf(sys.platform == 'win32', 'POSIX nonblocking FIFO race contract')
    def test_all_auxiliary_fifo_swaps_are_nonblocking_refused_and_closed(self):
        actual = service.os.open
        for name in ('SOUL.md', 'cache/schema_columns.json',
                     'cache/tool_discovery_cache.json', 'runtime/active_sessions.json'):
            path = self.home / name
            raw = path.read_bytes()
            descriptors = []
            def swapped(candidate, flags, *args, **kwargs):
                if Path(candidate) == path:
                    # A regressed blocking open fails before creating the FIFO,
                    # so this regression test itself cannot wait for a writer.
                    self.assertTrue(flags & os.O_NONBLOCK)
                    path.unlink()
                    os.mkfifo(path, 0o600)
                    fd = actual(candidate, flags, *args, **kwargs)
                    descriptors.append(fd)
                    return fd
                return actual(candidate, flags, *args, **kwargs)
            try:
                with self.subTest(name=name), \
                     patch.object(service.os, 'open', side_effect=swapped), \
                     self.assertRaisesRegex(service.ServiceProfileRejected, 'aux_fd_changed'):
                    self.inspect()
                self.assertEqual(len(descriptors), 1)
                with self.assertRaises(OSError):
                    os.fstat(descriptors[0])
            finally:
                path.unlink()
                self.write(name, raw)

    def test_whole_profile_snapshot_change_refused(self):
        actual = service._snapshot
        calls = 0
        def changed(*args):
            nonlocal calls
            result = actual(*args)
            calls += 1
            if calls == 2:
                result['state.db'] = (*result['state.db'][:-1], result['state.db'][-1] + 1)
            return result
        with patch.object(service, '_snapshot', side_effect=changed), \
             self.assertRaisesRegex(service.ServiceProfileRejected, 'profile_changed'):
            self.inspect()

    def test_config_check_tolerates_database_and_directory_runtime_changes(self):
        self.inspect()
        self.write('state.db', b'changed database bytes' * 100)
        backup = self.home / 'config_backups'
        backup.mkdir(mode=0o700)
        self.write('config_backups/native-generated.json', b'fixture backup')
        self.assertEqual(self.check()['state'], 'SERVICE_CONFIG_BOUND')
        with self.assertRaises(service.ServiceProfileRejected):
            self.inspect()

    def test_no_native_imports_or_loader_calls(self):
        actual = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name in ('hermes_state', 'hermes_state_runtime') or name.startswith(('gateway.', 'hermes_cli.', 'tools.')):
                raise AssertionError('native import attempted')
            return actual(name, *args, **kwargs)
        with patch.object(builtins, '__import__', side_effect=guarded):
            self.inspect()
            self.check()

    def test_soul_schema_discovery_and_active_state_remain_checked(self):
        names = ('SOUL.md', 'cache/schema_columns.json',
                 'cache/tool_discovery_cache.json', 'runtime/active_sessions.json')
        changed = (b'x' * layout.SOUL_BYTES, b'{}', b'{}', b'{"entries":[1]}')
        for name, raw in zip(names, changed):
            old = (self.home / name).read_bytes()
            self.write(name, raw)
            try:
                with self.subTest(name=name), self.assertRaises(service.ServiceProfileRejected):
                    self.inspect()
            finally:
                self.write(name, old)

    def test_canonical_unicode_finite_json_config_is_accepted(self):
        self.select_raw(canonical({'flags': [None, True, False],
                                   'name': 'Türkçe', 'values': [-7, 0, 3.5, 1e20]}))
        self.inspect()
        self.check()

    def test_duplicate_nonfinite_noncanonical_and_nonobject_configs_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"v":NaN}', b'{"v":Infinity}',
                    b'{"v":1e309}', b'[]', b'null', b'{ "a":1}',
                    b'{"b":1,"a":2}', b'{}\n', b'key: value', b'\xff'):
            self.select_raw(raw)
            with self.subTest(raw=repr(raw)), self.assertRaises(service.ServiceProfileRejected):
                self.check()

    def test_environment_references_are_refused_at_any_depth_or_key(self):
        for value in ({'model': '${MODEL}'}, {'x': [{'value': 'prefix-${TOKEN}-suffix'}]},
                      {'${DYNAMIC_KEY}': 'value'}):
            self.select_raw(canonical(value))
            with self.assertRaisesRegex(service.ServiceProfileRejected, 'environment_reference'):
                self.check()

    def test_config_depth_node_string_and_number_limits(self):
        deep = 0
        for _ in range(service.MAX_CONFIG_DEPTH + 1):
            deep = [deep]
        values = ({'x': deep}, {'x': [0] * service.MAX_CONFIG_NODES},
                  {'x': 'a' * (service.MAX_CONFIG_STRING + 1)}, {'x': 10**service.MAX_INTEGER_DIGITS},
                  {'x': '\x00'})
        for value in values:
            self.select_raw(canonical(value))
            with self.subTest(kind=type(value['x']).__name__), self.assertRaises(service.ServiceProfileRejected):
                self.check()

    def test_parser_diagnostic_never_exposes_config_content(self):
        self.select_raw(b'{"fixture-private-value":broken}')
        with self.assertRaises(service.ServiceProfileRejected) as caught:
            self.check()
        self.assertEqual(str(caught.exception), 'service_profile_unavailable')
        self.assertNotIn('fixture-private-value', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
