"""Explicit self-metadata and code-snapshot contracts; no kernel changes here."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/claw-hermes'))
import credential_guard as guard
spec=importlib.util.spec_from_file_location('alaz_credential_snapshot',ROOT/'scripts/qa/native_credential_ext4.py')
snapshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot)


class MetadataContracts(unittest.TestCase):
    def policy(self):
        return {'version':1,'enabled':True,'readonly':['/usr'],
                'writable':['/owned/work'],'protected':['/owned/private/secret']}

    def test_legacy_shape_and_digest_stay_unchanged(self):
        p=self.policy();out=guard.validate_policy(p)
        self.assertNotIn('self_process_metadata',out)
        self.assertEqual(guard.policy_digest(p),guard.policy_digest(out))

    def test_explicit_metadata_true_only(self):
        p=self.policy()|{'self_process_metadata':True}
        self.assertIs(guard.validate_policy(p)['self_process_metadata'],True)

    def test_explicit_metadata_false_supported(self):
        p=self.policy()|{'self_process_metadata':False}
        self.assertIs(guard.validate_policy(p)['self_process_metadata'],False)

    def test_metadata_non_boolean_refused(self):
        for value in (1,0,'true',None,[],{}):
            with self.subTest(value=value),self.assertRaises(guard.GuardRejected):
                guard.validate_policy(self.policy()|{'self_process_metadata':value})

    def test_metadata_mode_cannot_grant_proc_tree(self):
        for path in ('/proc','/proc/self','/proc/123','/proc/123/environ'):
            with self.subTest(path=path),self.assertRaisesRegex(guard.GuardRejected,'broad_grant'):
                guard.validate_policy(self.policy()|{'self_process_metadata':True,'readonly':[path]})

    def test_metadata_mode_cannot_choose_other_pid(self):
        with self.assertRaises(guard.GuardRejected):
            guard.validate_policy(self.policy()|{'self_process_metadata':True,'metadata_pid':4})

    def test_fixed_read_file_list_no_memory_or_fd(self):
        self.assertEqual(guard.self_metadata_paths(42),
            ('/proc/42/stat','/proc/42/status','/proc/42/statm','/proc/42/cmdline','/proc/stat'))
        self.assertFalse(any(p.endswith(('/mem','/environ','/fd','/exe')) for p in guard.self_metadata_paths(42)))

    def test_invalid_pid_refused(self):
        for pid in (True,False,0,-1,'42',None,1.0):
            with self.subTest(pid=pid),self.assertRaises(guard.GuardRejected):
                guard.self_metadata_paths(pid)

    def test_old_protected_tree_rule_still_refuses(self):
        with self.assertRaisesRegex(guard.GuardRejected,'secret_in_granted_tree'):
            guard.validate_policy(self.policy()|{'self_process_metadata':True,'readonly':['/owned']})


class SnapshotContracts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'source';self.root.mkdir()
        for name in snapshot.ROOTS:
            (self.root/name).mkdir();(self.root/name/'fixture.txt').write_bytes(b'exact source bytes\n')
        (self.root/'sources.lock.json').write_text('{"source":"pinned"}')
        self.dest=Path(self.tmp.name)/'copy'

    def test_copy_matches_every_byte(self):
        expected=snapshot.source_files(self.root)
        snapshot.copy_verified(self.root,self.dest,expected)
        self.assertEqual(snapshot.source_files(self.dest),expected)
        self.assertEqual(len(expected),4)

    def test_runtime_credentials_excluded(self):
        (self.root/'runtime').mkdir();(self.root/'runtime/secret.json').write_text('private')
        (self.root/'.env').write_text('secret')
        expected=snapshot.source_files(self.root)
        self.assertFalse(any(p.startswith('runtime') or p=='.env' for p in expected))
        snapshot.copy_verified(self.root,self.dest,expected)
        self.assertFalse((self.dest/'runtime').exists())

    def test_source_modified_after_inventory_refuses(self):
        expected=snapshot.source_files(self.root)
        (self.root/'packages/fixture.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'source_changed'):
            snapshot.copy_verified(self.root,self.dest,expected)

    def test_source_added_after_inventory_refuses(self):
        expected=snapshot.source_files(self.root)
        (self.root/'scripts/added.py').write_text('x=1')
        with self.assertRaisesRegex(ValueError,'inventory_changed'):
            snapshot.copy_verified(self.root,self.dest,expected)

    def test_existing_destination_refused(self):
        self.dest.mkdir();(self.dest/'sentinel').write_text('preserved')
        with self.assertRaisesRegex(ValueError,'destination_exists'):
            snapshot.copy_verified(self.root,self.dest,snapshot.source_files(self.root))
        self.assertEqual((self.dest/'sentinel').read_text(),'preserved')

    def test_missing_root_refused(self):
        (self.root/'config/fixture.txt').unlink();(self.root/'config').rmdir()
        with self.assertRaisesRegex(ValueError,'source_root_invalid'):
            snapshot.source_files(self.root)

    def test_untrusted_symlink_root_refused_before_read(self):
        with patch.object(Path,'is_symlink',side_effect=lambda:True):
            with self.assertRaisesRegex(ValueError,'source_root_invalid'):
                snapshot.source_files(self.root)

    def test_cache_files_not_in_source_manifest(self):
        (self.root/'scripts/__pycache__').mkdir()
        (self.root/'scripts/__pycache__/x.pyc').write_bytes(b'ignore')
        (self.root/'scripts/x.pyc').write_bytes(b'ignore')
        self.assertEqual(len(snapshot.source_files(self.root)),4)

    def test_oversize_source_refused(self):
        with (self.root/'config/large').open('wb') as f:f.truncate(4_194_305)
        with self.assertRaisesRegex(ValueError,'file_size'):
            snapshot.source_files(self.root)


if __name__=='__main__':
    unittest.main(verbosity=2)
