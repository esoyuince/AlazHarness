"""Synthetic Linux mount records + real owned files. No mount/UID/DB operations."""
from contextlib import ExitStack
from pathlib import Path
import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_storage_mounts as mounts


def table(filesystem='ext4', options='rw,relatime', super_options='rw', extra=''):
    return ('1 99 8:1 / / rw - ext4 /dev/root rw\n'
            f'2 1 8:3 / /owned {options} shared:1 future-tag:value - '
            f'{filesystem} /dev/fixture {super_options}\n' + extra).encode()


class ParserTests(unittest.TestCase):
    def test_kernel_fields_and_unknown_optional_tags(self):
        record = mounts.parse_mountinfo(table())[1]
        self.assertEqual(record.device, (8, 3))
        self.assertEqual(record.mount_point, '/owned')
        self.assertEqual(record.root, '/')
        self.assertEqual(record.parent_id, 1)
        self.assertEqual(record.filesystem, 'ext4')

    def test_escape_sequences_are_decoded_once(self):
        raw = b'1 9 8:3 / /a\\040b\\011c\\012d\\134e rw - ext4 none rw\n'
        self.assertEqual(mounts.parse_mountinfo(raw)[0].mount_point, '/a b\tc\nd\\e')
        raw = b'1 9 8:3 / /a\\134040 rw - ext4 none rw\n'
        self.assertEqual(mounts.parse_mountinfo(raw)[0].mount_point, '/a\\040')

    def test_invalid_escape_and_noncanonical_paths_refused(self):
        for path in (r'/a\099', r'/a\000', r'/a\x', '/a/../b', '/a//b', '//a', '/a/./b'):
            with self.subTest(path=path), self.assertRaises(mounts.StorageMountRejected):
                mounts.parse_mountinfo(f'1 9 8:3 / {path} rw - ext4 none rw\n'.encode())

    def test_empty_truncated_or_oversize_input_refused(self):
        for raw in (b'', table()[:-1], b'x' * (mounts.MAX_MOUNTINFO_BYTES + 1), table() + b'\0\n'):
            with self.subTest(size=len(raw)), self.assertRaises(mounts.StorageMountRejected):
                mounts.parse_mountinfo(raw)

    def test_malformed_fields_and_identifiers_refused(self):
        for raw in (b'no separator\n', b'1 2 8:3 / / rw - ext4 x\n',
                    b'0 1 8:3 / / rw - ext4 x rw\n', b'1 2 8:a / / rw - ext4 x rw\n',
                    b'1 2 8:3 / / rw,ro - ext4 x rw\n', b'1 2 8:3 / / rw - ext4 x rw,ro\n',
                    b'1 2 8:3 / / rw,,x - ext4 x rw\n', b'1 2 8:3 / / rw - ext4 x rw\n'*2):
            with self.subTest(raw=raw), self.assertRaises(mounts.StorageMountRejected):
                mounts.parse_mountinfo(raw)

    def test_longest_component_prefix_not_text_prefix(self):
        records = mounts.parse_mountinfo(table(extra='3 1 8:4 / /owned-more rw - xfs none rw\n'))
        self.assertEqual(mounts.select_mount(records, '/owned-more/a').mount_id, 3)
        self.assertEqual(mounts.select_mount(records, '/owned/a').mount_id, 2)
        self.assertEqual(mounts.select_mount(records, '/owned-extra/a').mount_id, 1)

    def test_stacked_ancestor_and_file_mount_ambiguity_refused(self):
        for extra in ('3 1 8:5 / / rw - ext4 none rw\n',
                      '3 1 8:5 / /owned rw - ext4 none rw\n'):
            with self.subTest(extra=extra), self.assertRaisesRegex(mounts.StorageMountRejected, 'stack_ambiguous'):
                mounts.select_mount(mounts.parse_mountinfo(table(extra=extra)), '/owned/a')

    def test_missing_ancestor_refused(self):
        records = mounts.parse_mountinfo(b'2 1 8:3 / /other rw - ext4 none rw\n')
        with self.assertRaisesRegex(mounts.StorageMountRejected, 'mount_not_found'):
            mounts.select_mount(records, '/owned/a')

    def test_mount_count_and_line_limits(self):
        with patch.object(mounts, 'MAX_MOUNTS', 1), self.assertRaisesRegex(mounts.StorageMountRejected, 'limit'):
            mounts.parse_mountinfo(table())
        with patch.object(mounts, 'MAX_LINE_BYTES', 8), self.assertRaisesRegex(mounts.StorageMountRejected, 'malformed'):
            mounts.parse_mountinfo(table())

    def test_expectation_does_not_accept_bool_ids_or_volatile_filesystems(self):
        for values in ((True, (8, 3), '/', '/owned', 'ext4'),
                       (2, (True, 3), '/', '/owned', 'ext4'),
                       (2, [8, 3], '/', '/owned', 'ext4'),
                       (2, (8, 3), '/', '/owned', 'tmpfs'),
                       (2, (8, 3), '/', '/owned', 'overlay')):
            with self.subTest(values=values), self.assertRaises(mounts.StorageMountRejected):
                mounts.ExpectedMount(*values)


class ProfileObservationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='alaz-mount-observer-')
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name).resolve()
        for name in mounts.DATABASE_NAMES:
            (self.home / name).write_bytes(b'owned dummy bytes, not an actual SQLite database')
        self.expected = mounts.ExpectedMount(2, (8, 3), '/', '/owned', 'ext4')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(mounts, '_is_linux', return_value=True))
        self.reader = self.stack.enter_context(patch.object(mounts, '_read_mountinfo', return_value=table()))
        self.namespace = self.stack.enter_context(patch.object(mounts, '_mount_namespace', return_value='mnt:[123]'))
        self.device = self.stack.enter_context(patch.object(mounts, '_device', return_value=(8, 3)))
        self.stack.enter_context(patch.object(mounts, '_mount_path', side_effect=lambda p:
            '/owned/profile' + ('' if p == self.home else '/' + p.name)))

    def observe(self):
        return mounts.observe_profile_mounts(self.home, self.expected)

    def reject(self, reason):
        with self.assertRaisesRegex(mounts.StorageMountRejected, reason):
            self.observe()

    def test_success_remains_snapshot_not_durability_or_authority(self):
        result = self.observe()
        self.assertEqual(result['state'], 'CONFIGURED_MOUNT_OBSERVED')
        self.assertEqual(result['presentFiles'], 2)
        self.assertEqual(result['sidecarsObserved'], 0)
        self.assertIs(result['snapshotOnly'], True)
        for key in ('writesPerformed', 'databaseContentsOpened', 'sqliteOpenInodeVerified',
                    'physicalMediumDurabilityVerified', 'exclusiveWriterVerified',
                    'pairedStoreConsistencyVerified', 'fullGatewayPersistenceAccepted', 'launchAuthorized'):
            self.assertIs(result[key], False, key)
        self.assertNotIn(str(self.home), str(result))

    def test_existing_sqlite_sidecars_observed_not_opened(self):
        for name in mounts.SIDECAR_NAMES:
            (self.home / name).write_bytes(b'owned sidecar')
        self.assertEqual(self.observe()['sidecarsObserved'], 6)

    def test_tmpfs_ramfs_rootfs_rejected_despite_regular_files(self):
        for fs in ('tmpfs', 'ramfs', 'rootfs'):
            self.reader.return_value = table(filesystem=fs)
            with self.subTest(filesystem=fs):
                self.reject('storage_volatile_filesystem')

    def test_unqualified_filesystems_refused_not_assumed_volatile(self):
        for fs in ('overlay', 'nfs', '9p', 'fuse.sshfs'):
            self.reader.return_value = table(filesystem=fs)
            with self.subTest(filesystem=fs):
                self.reject('storage_filesystem_unqualified')

    def test_readonly_mount_or_superblock_refused(self):
        for raw in (table(options='ro'), table(super_options='ro')):
            self.reader.return_value = raw
            with self.subTest(raw=raw):
                self.reject('storage_readonly_mount')

    def test_each_expected_identity_field_is_checked(self):
        for expected in (mounts.ExpectedMount(9, (8, 3), '/', '/owned', 'ext4'),
                         mounts.ExpectedMount(2, (8, 4), '/', '/owned', 'ext4'),
                         mounts.ExpectedMount(2, (8, 3), '/subvolume', '/owned', 'ext4'),
                         mounts.ExpectedMount(2, (8, 3), '/', '/other', 'ext4'),
                         mounts.ExpectedMount(2, (8, 3), '/', '/owned', 'xfs')):
            self.expected = expected
            with self.subTest(expected=expected):
                self.reject('storage_mount_binding_mismatch')

    def test_same_device_file_bind_of_one_store_refused(self):
        self.reader.return_value = table(extra='3 2 8:3 /other/state /owned/profile/state.db rw - ext4 none rw\n')
        self.reject('storage_mount_binding_mismatch')

    def test_present_sidecar_on_different_mount_refused(self):
        (self.home / 'state.db-wal').write_bytes(b'owned')
        self.reader.return_value = table(extra='3 2 8:3 /other/wal /owned/profile/state.db-wal rw - ext4 none rw\n')
        self.reject('storage_mount_binding_mismatch')

    def test_real_stat_device_must_match_mount_record(self):
        self.device.side_effect = [(8, 3), (8, 8)]
        self.reject('storage_device_mismatch')

    def test_missing_required_store_is_not_created(self):
        path = self.home / 'runs_idempotency.db'
        path.unlink()
        self.reject('storage_required_database_missing')
        self.assertFalse(path.exists())

    def test_directory_cannot_stand_in_for_database(self):
        path = self.home / 'state.db'
        path.unlink(); path.mkdir()
        self.reject('storage_regular_single_file_required')

    def test_hardlinked_database_refused(self):
        link = self.home / 'alias'
        try:
            os.link(self.home / 'state.db', link)
        except OSError as exc:
            self.skipTest('no hardlink support: ' + type(exc).__name__)
        self.reject('storage_regular_single_file_required')

    def test_changed_table_or_namespace_refused_without_retry(self):
        for which in ('table', 'namespace'):
            self.reader.side_effect = None; self.namespace.side_effect = None
            if which == 'table':
                self.reader.side_effect = [table(), table(extra='3 1 8:4 / /else rw - xfs none rw\n')]
            else:
                self.namespace.side_effect = ['mnt:[123]', 'mnt:[124]']
            with self.subTest(which=which):
                self.reject('storage_observation_changed')

    def test_changed_metadata_refused(self):
        original = mounts._snapshot
        calls = []
        def changed(*args):
            first, present = original(*args)
            calls.append(1)
            if len(calls) == 2:
                first['state.db'] = (*first['state.db'][:-1], first['state.db'][-1] + 1)
            return first, present
        with patch.object(mounts, '_snapshot', side_effect=changed):
            self.reject('storage_observation_changed')
        self.assertEqual(len(calls), 2)

    def test_sidecar_appearance_or_disappearance_invalidates_observation(self):
        for appearance in (True, False):
            sidecar = self.home / 'state.db-wal'
            if sidecar.exists():
                sidecar.unlink()
            if not appearance:
                sidecar.write_bytes(b'owned old sidecar')
            original = mounts._snapshot
            calls = []
            def changed(*args):
                result = original(*args)
                calls.append(1)
                if len(calls) == 1:
                    if appearance:
                        sidecar.write_bytes(b'owned new sidecar')
                    else:
                        sidecar.unlink()
                return result
            with self.subTest(appearance=appearance), patch.object(mounts, '_snapshot', side_effect=changed):
                self.reject('storage_observation_changed')

    def test_sidecar_permission_failure_is_not_treated_as_absence(self):
        original = Path.lstat
        def denied(path, *args, **kwargs):
            if path == self.home / 'state.db-wal':
                raise PermissionError('owned access failure')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'lstat', denied):
            self.reject('storage_mount_observation_unavailable')

    def test_database_bytes_and_owner_files_remain_untouched(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.home.iterdir()}
        with patch('builtins.open', side_effect=AssertionError('no data open')), \
             patch.object(Path, 'open', side_effect=AssertionError('no data open')):
            self.observe()
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.home.iterdir()}
        self.assertEqual(before, after)

    def test_read_failure_is_bounded_and_no_private_path_leaks(self):
        self.reader.side_effect = PermissionError(str(self.home))
        self.reject('storage_mount_observation_unavailable')

    def test_non_linux_or_untrusted_expectation_refused_before_path_access(self):
        with patch.object(mounts, '_is_linux', return_value=False), \
             patch.object(mounts, '_canonical_profile', side_effect=AssertionError('no path work')):
            self.reject('storage_linux_required')
        with patch.object(mounts, '_canonical_profile', side_effect=AssertionError('no path work')), \
             self.assertRaisesRegex(mounts.StorageMountRejected, 'storage_trusted_expectation_required'):
            mounts.observe_profile_mounts(self.home, {})

    def test_relative_profile_refused(self):
        with self.assertRaisesRegex(mounts.StorageMountRejected, 'not_canonical'):
            mounts.observe_profile_mounts(Path('.'), self.expected)


if __name__ == '__main__':
    unittest.main()
