"""Owned byte/filesystem fixtures; never privileged installation acceptance."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import install_projected_candidate as installer


def source_fixture():
    b = installer._builder()
    source = {name: b'raise RuntimeError("candidate code must never execute")\n'
              for name in b.EXACT | b.REQUIRED_MODULES}
    number = 0
    while len(source) < 77:
        source['packages/claw-hermes/fixture_' + str(number).zfill(4) + '.py'] = b'# source\n'
        number += 1
    native = {'agent/fixture_' + str(i).zfill(4) + '.py':
              ('raise RuntimeError("native fixture ' + str(i) + ' must never execute")\n').encode()
              for i in range(b.NATIVE_COUNT)}
    source.update({'native/' + name: data for name, data in native.items()})
    source[b.NATIVE_MANIFEST] = b.canonical({'schema': 1, 'nativeFeature': b.NATIVE_FEATURE,
                                           'sources': {n: b.digest(v) for n, v in native.items()}})
    dependencies = {'pkg/fixture_' + str(i).zfill(4) + '.py':
                    ('raise RuntimeError("dependency fixture ' + str(i) + ' must never execute")\n').encode()
                    for i in range(b.DEPENDENCY_COUNT)}
    source['accepted-dependencies.json'] = b.canonical({n: b.digest(v) for n, v in dependencies.items()})
    return source, dependencies


def seal(source):
    b = installer._builder()
    revision = 'a' * 40
    metadata = {}
    for name, data in source.items():
        generated = name == 'accepted-dependencies.json'
        metadata[name] = {'gitBlob': None if generated else hashlib.sha1(
            ('blob ' + str(len(data)) + '\0').encode() + data).hexdigest(),
            'mode': 0o755 if name.startswith('scripts/') else 0o644,
            'bytes': len(data), 'sha256': b.digest(data),
            'repository': 'generated-reference' if generated else
                          'native' if name.startswith('native/') else 'harness'}
    archive = b.archive_bytes(source, metadata, revision)
    checked = b.verify_archive(archive, metadata, revision)
    manifest = {'schemaVersion': 1, 'kind': 'PROJECTED_STARTUP_SOURCE_CANDIDATE_NOT_INSTALLED',
        'harnessCommit': revision, 'nativeFeature': b.NATIVE_FEATURE, 'archive': b.ARCHIVE,
        'prefix': b.PREFIX, **checked, 'nativeSourceFileCount': b.NATIVE_COUNT,
        'harnessSourceFileCount': 77, 'fileManifest': metadata,
        'dependencies': {'sourceRecord': b.DEPENDENCY_RECORD, 'recordGitBlob': 'b' * 40,
            'recordSha256': 'c' * 64, 'inventoryFile': 'accepted-dependencies.json',
            'inventorySha256': b.digest(source['accepted-dependencies.json']),
            'fileCount': b.DEPENDENCY_COUNT, 'bytesIncluded': False,
            'installedBytesVerifiedNow': False, 'target': 'Linux x86_64 CPython 3.12'},
        'installed': False, 'executionAuthorized': False, 'privilegedExecutionTested': False,
        'positiveProjectedReadinessAccepted': False, 'finiteWorkExecuted': False,
        'pythonIncluded': False, 'realModelCalls': 0}
    return manifest, archive


def prepared(manifest, archive, **overrides):
    raw = installer.canonical(manifest)
    pins = {'expected_manifest_sha256': installer.digest(raw),
            'expected_archive_sha256': installer.digest(archive),
            'expected_harness_commit': 'a' * 40}
    pins.update(overrides)
    return installer.prepare_bytes(raw, archive, **pins)


class CandidateInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.dependencies = source_fixture()
        cls.manifest, cls.archive = seal(cls.source)

    def test_exact_candidate_prepares_all_bytes_without_executing_them(self):
        result = prepared(self.manifest, self.archive)
        self.assertEqual(dict(result.source), self.source)
        self.assertEqual(len(result.source), 834)
        self.assertEqual(len(result.dependencies), 1162)
        self.assertFalse(hasattr(result, 'installed'))
        with self.assertRaises(TypeError):
            result.source['new.py'] = b'changed'

    def test_changed_manifest_external_pin_refuses(self):
        with self.assertRaisesRegex(ValueError, 'manifest_digest'):
            prepared(self.manifest, self.archive, expected_manifest_sha256='0' * 64)

    def test_changed_archive_external_pin_refuses(self):
        with self.assertRaisesRegex(ValueError, 'archive_digest'):
            prepared(self.manifest, self.archive, expected_archive_sha256='0' * 64)

    def test_changed_harness_pin_refuses(self):
        with self.assertRaisesRegex(ValueError, 'manifest_schema'):
            prepared(self.manifest, self.archive, expected_harness_commit='d' * 40)

    def test_native_revision_refuses(self):
        manifest = deepcopy(self.manifest)
        manifest['nativeFeature'] = 'd' * 40
        with self.assertRaisesRegex(ValueError, 'manifest_schema'):
            prepared(manifest, self.archive)

    def test_manifest_cannot_claim_execution_authority(self):
        for key in ('installed', 'executionAuthorized', 'positiveProjectedReadinessAccepted'):
            with self.subTest(key=key):
                manifest = deepcopy(self.manifest)
                manifest[key] = True
                with self.assertRaisesRegex(ValueError, 'manifest_claims'):
                    prepared(manifest, self.archive)

    def test_boolean_zero_is_not_a_model_call_count(self):
        manifest = deepcopy(self.manifest)
        manifest['realModelCalls'] = False
        with self.assertRaisesRegex(ValueError, 'manifest_claims'):
            prepared(manifest, self.archive)

    def test_traversal_metadata_refuses_even_with_matching_manifest_pin(self):
        manifest = deepcopy(self.manifest)
        manifest['fileManifest']['../escape.py'] = next(iter(manifest['fileManifest'].values()))
        with self.assertRaisesRegex(ValueError, 'path_not_canonical'):
            prepared(manifest, self.archive)

    def test_source_case_collision_refuses(self):
        manifest = deepcopy(self.manifest)
        manifest['fileManifest']['license'] = manifest['fileManifest']['LICENSE']
        with self.assertRaisesRegex(ValueError, 'source_collision'):
            prepared(manifest, self.archive)

    def test_archive_symbolic_link_refuses(self):
        b = installer._builder()
        output = io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(self.archive), mode='r:') as original, \
                tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT,
                             pax_headers={'comment': b.stamp('a' * 40)}) as changed:
            for index, member in enumerate(original):
                data = original.extractfile(member).read()
                if index == 0:
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/owned-fixture-target'
                    member.size = 0
                    changed.addfile(member)
                else:
                    changed.addfile(member, io.BytesIO(data))
        archive = output.getvalue()
        manifest = deepcopy(self.manifest)
        manifest['archiveSha256'] = installer.digest(archive)
        manifest['archiveBytes'] = len(archive)
        with self.assertRaisesRegex(ValueError, 'archive_regular_only'):
            prepared(manifest, archive)

    def test_archive_trailing_data_refuses_after_resealed_digest(self):
        archive = self.archive + b'not-approved-tar-data'
        manifest = deepcopy(self.manifest)
        manifest['archiveSha256'] = installer.digest(archive)
        manifest['archiveBytes'] = len(archive)
        with self.assertRaisesRegex(ValueError, 'trailing_payload'):
            prepared(manifest, archive)

    def test_native_envelope_disagreement_refuses(self):
        source = dict(self.source)
        b = installer._builder()
        envelope = b.unique_json(source[b.NATIVE_MANIFEST])
        envelope['sources'][next(iter(envelope['sources']))] = '0' * 64
        source[b.NATIVE_MANIFEST] = b.canonical(envelope)
        manifest, archive = seal(source)
        with self.assertRaisesRegex(ValueError, 'native_envelope'):
            prepared(manifest, archive)

    def test_dependency_map_traversal_refuses(self):
        source = dict(self.source)
        b = installer._builder()
        dependencies = b.unique_json(source['accepted-dependencies.json'])
        value = dependencies.pop(next(iter(dependencies)))
        dependencies['../escape.py'] = value
        source['accepted-dependencies.json'] = b.canonical(dependencies)
        manifest, archive = seal(source)
        with self.assertRaisesRegex(ValueError, 'path_not_canonical'):
            prepared(manifest, archive)

    def test_dependency_proof_digest_mismatch_refuses(self):
        manifest = deepcopy(self.manifest)
        manifest['dependencies']['inventorySha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'dependency_proof'):
            prepared(manifest, self.archive)

    def test_duplicate_manifest_json_key_refuses(self):
        raw = installer.canonical(self.manifest)
        raw = b'{"schemaVersion": 1,' + raw[1:]
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            installer.prepare_bytes(raw, self.archive,
                expected_manifest_sha256=installer.digest(raw),
                expected_archive_sha256=installer.digest(self.archive),
                expected_harness_commit='a' * 40)

    def test_receipt_requires_exact_identity_flags_and_types(self):
        expected = {'rootInode': 123, 'destination': '/opt/owned-fixture',
                    'installed': True, 'executionAuthorized': False, 'realModelCalls': 0}
        installer._verify_receipt(installer.canonical(expected), expected)
        for name, value in (('rootInode', 456), ('destination', '/opt/wrong-fixture'),
                            ('executionAuthorized', True), ('realModelCalls', False)):
            with self.subTest(name=name):
                wrong = dict(expected, **{name: value})
                with self.assertRaisesRegex(ValueError, 'receipt_identity'):
                    installer._verify_receipt(installer.canonical(wrong), expected)


@unittest.skipUnless(sys.platform == 'linux', 'descriptor and atomic-publication fixtures require Linux')
class OwnedFilesystemTests(unittest.TestCase):
    def setUp(self):
        # Retain owned fixtures as test artifacts. No production tree is touched.
        artifacts = ROOT / 'scratch/owned-install-tests'
        artifacts.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='fixture-', dir=artifacts))
        self.fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        self.addCleanup(os.close, self.fd)

    def test_all_actual_candidate_fixture_bytes_materialize_and_read_back(self):
        source, dependencies = source_fixture()
        manifest, archive = seal(source)
        candidate = prepared(manifest, archive)
        files = dict(candidate.source)
        files.update({'dependencies/' + n: data for n, data in dependencies.items()})
        modes = dict(candidate.source_modes)
        modes.update({'dependencies/' + n: 0o644 for n in dependencies})
        installer._materialize(self.fd, files, modes)
        actual = installer._tree(self.fd, {n: installer.digest(v) for n, v in files.items()},
                                 trusted=False, modes=modes)
        self.assertEqual(actual, files)
        self.assertEqual(len(actual), 1996)
        self.assertFalse((self.root / installer.RECEIPT).exists())

    def test_materialization_refuses_nonempty_directory_and_preserves_existing_file(self):
        (self.root / 'existing').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'stage_not_empty'):
            installer._materialize(self.fd, {'new.py': b'new'}, {'new.py': 0o644})
        self.assertEqual((self.root / 'existing').read_bytes(), b'keep')
        self.assertFalse((self.root / 'new.py').exists())

    def test_materialization_traversal_fails_before_writes(self):
        with self.assertRaisesRegex(ValueError, 'path_not_canonical'):
            installer._materialize(self.fd, {'../escape': b'bad'}, {'../escape': 0o644})
        self.assertEqual(os.listdir(self.fd), [])

    def test_materialization_file_directory_collision_fails_before_writes(self):
        files = {'module': b'file', 'module/child.py': b'child'}
        with self.assertRaisesRegex(ValueError, 'file_directory_collision'):
            installer._materialize(self.fd, files, {n: 0o644 for n in files})
        self.assertEqual(os.listdir(self.fd), [])

    def test_materialization_directory_case_collision_fails_before_writes(self):
        files = {'pkg/first.py': b'first', 'Pkg/second.py': b'second'}
        with self.assertRaisesRegex(ValueError, 'path_case_collision'):
            installer._materialize(self.fd, files, {n: 0o644 for n in files})
        self.assertEqual(os.listdir(self.fd), [])

    def test_input_symbolic_link_refuses(self):
        (self.root / 'real').write_bytes(b'bytes')
        (self.root / 'link').symlink_to('real')
        with self.assertRaises(OSError):
            installer._read_at(self.fd, 'link', 100)

    def test_input_hardlink_refuses(self):
        (self.root / 'real').write_bytes(b'bytes')
        os.link(self.root / 'real', self.root / 'link')
        with self.assertRaisesRegex(ValueError, 'single_link_required'):
            installer._read_at(self.fd, 'link', 100)

    def test_fifo_refuses_without_waiting_for_writer(self):
        os.mkfifo(self.root / 'pipe')
        with self.assertRaisesRegex(ValueError, 'single_link_required'):
            installer._read_at(self.fd, 'pipe', 100)

    def test_parent_symbolic_link_refuses(self):
        (self.root / 'directory').mkdir()
        (self.root / 'link').symlink_to('directory', target_is_directory=True)
        with self.assertRaises(OSError):
            installer._directory(self.root / 'link', trusted=False)

    def test_world_writable_ancestry_refuses(self):
        self.root.chmod(0o777)
        with self.assertRaisesRegex(ValueError, 'untrusted_ancestry'):
            installer._trusted(self.root.stat(), True)

    def test_dependency_changed_bytes_refuse(self):
        (self.root / 'module.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'file_digest'):
            installer._tree(self.fd, {'module.py': installer.digest(b'expected')}, trusted=False)

    def test_extra_dependency_file_refuses(self):
        (self.root / 'module.py').write_bytes(b'expected')
        (self.root / 'extra.py').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'extra_file|extra_entry_limit'):
            installer._tree(self.fd, {'module.py': installer.digest(b'expected')}, trusted=False)

    def test_extra_empty_dependency_directory_refuses(self):
        (self.root / 'module.py').write_bytes(b'expected')
        (self.root / 'extra').mkdir()
        with self.assertRaisesRegex(ValueError, 'extra_directory|extra_entry_limit'):
            installer._tree(self.fd, {'module.py': installer.digest(b'expected')}, trusted=False)

    def test_missing_dependency_refuses(self):
        with self.assertRaisesRegex(ValueError, 'missing_file'):
            installer._tree(self.fd, {'module.py': installer.digest(b'expected')}, trusted=False)

    def test_dependency_mode_mismatch_refuses(self):
        (self.root / 'module.py').write_bytes(b'expected')
        (self.root / 'module.py').chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'file_mode'):
            installer._tree(self.fd, {'module.py': installer.digest(b'expected')},
                            trusted=False, modes={'module.py': 0o644})

    def test_changed_python_hash_refuses_using_declared_reader_fixture(self):
        # A byte-reader double tests pin refusal only; no actor or trust guard is
        # patched and no installation is attempted or claimed.
        path = self.root / 'python-fixture'
        path.write_bytes(b'owned-interpreter-fixture')
        path.chmod(0o755)
        with patch.object(installer, '_read_path', return_value=(path.read_bytes(), path.stat())):
            with self.assertRaisesRegex(ValueError, 'interpreter_digest'):
                installer._python('0' * 64)

    def test_partial_write_is_preserved_without_success_receipt(self):
        original = installer._write_at
        calls = []
        def interrupted(parent, name, data, mode):
            if calls:
                raise OSError('owned fixture interruption')
            calls.append(name)
            original(parent, name, data, mode)
        with patch.object(installer, '_write_at', side_effect=interrupted):
            with self.assertRaises(OSError):
                installer._materialize(self.fd, {'first': b'one', 'second': b'two'},
                                       {'first': 0o644, 'second': 0o644})
        self.assertEqual((self.root / 'first').read_bytes(), b'one')
        self.assertFalse((self.root / 'second').exists())
        self.assertFalse((self.root / installer.RECEIPT).exists())
        with self.assertRaisesRegex(ValueError, 'stage_not_empty'):
            installer._materialize(self.fd, {'first': b'one'}, {'first': 0o644})

    def test_atomic_publication_never_replaces_existing_directory(self):
        (self.root / 'stage').mkdir()
        (self.root / 'destination').mkdir()
        (self.root / 'stage/source').write_bytes(b'new')
        (self.root / 'destination/existing').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, 'destination_exists'):
            installer._rename_noreplace(self.fd, 'stage', 'destination')
        self.assertEqual((self.root / 'destination/existing').read_bytes(), b'keep')
        self.assertEqual((self.root / 'stage/source').read_bytes(), b'new')

    def test_atomic_publication_success_preserves_directory_identity(self):
        (self.root / 'stage').mkdir()
        before = (self.root / 'stage').stat()
        installer._rename_noreplace(self.fd, 'stage', 'destination')
        after = (self.root / 'destination').stat()
        self.assertEqual((before.st_dev, before.st_ino), (after.st_dev, after.st_ino))
        self.assertFalse((self.root / 'stage').exists())

    def test_destination_existence_including_dangling_symlink_refuses(self):
        (self.root / 'destination').symlink_to('absent')
        with self.assertRaisesRegex(ValueError, 'destination_exists'):
            installer._absent(self.fd, 'destination')


if __name__ == '__main__':
    unittest.main()
