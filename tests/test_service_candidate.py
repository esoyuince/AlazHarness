"""Owned Git/byte fixtures; no service, dependency or model acceptance.

Only the NEW service generation and verifier accessor are substituted for the
synthetic Git fixture. Historical finite builder/installer globals are untouched.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import MappingProxyType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_service_candidate as candidate
import verify_service_candidate as verifier

SERVICE_NATIVE = '5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d'
SERVICE_MANIFEST = '05dee55dede392d10af65fc123969b8f317cf417d1af669b655d2115a2757bd2'
SERVICE_SUPPORT = frozenset((
    'packages/upstream/hermes/hermes_state_keys.py',
    'packages/upstream/hermes/terminal_status.py',
    'config/execution-gate/source-lock.json',
))
LEGACY_HASHES = {
    'build_projected_candidate.py':
        '7b26916aec3c806ef2debf77e9e9c728ec473d8c8d2689bbbdcfc4cd7223a64b',
    'install_projected_candidate.py':
        'f261fd22c641a1ffdd6fb9694fec0c7d3cb0c8dba788cb7549c142fd1e4dcef6',
}


def command(repo, *args, data=None):
    result = subprocess.run(['git', '-C', str(repo), *args], input=data,
                            capture_output=True, check=True, timeout=30)
    return result.stdout


def save(repo, name, data):
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def commit(repo):
    command(repo, 'add', '--all')
    command(repo, '-c', 'user.name=Owned Service Candidate Test',
            '-c', 'user.email=service-candidate@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', 'owned fixture')
    return command(repo, 'rev-parse', 'HEAD').decode('ascii').strip()


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='alaz-service-candidate-') as directory:
        root = Path(directory).resolve()
        repo = root / 'harness'; native = root / 'native'
        for path in (repo, native):
            path.mkdir(); command(path, 'init', '--quiet')
            command(path, 'config', 'core.autocrlf', 'false')
        original = json.loads((ROOT / candidate.NATIVE_MANIFEST).read_bytes())
        native_hashes = {}
        for name in original['sources']:
            raw = ('raise RuntimeError("native fixture must never execute")\n'
                   '# ' + name + '\n').encode('ascii')
            save(native, name, raw)
            native_hashes[name] = candidate.digest(raw)
        native_commit = commit(native)
        save(repo, '.gitignore', b'scratch/\n')
        for name in candidate.EXACT | candidate.REQUIRED_MODULES:
            raw = ((ROOT / name).read_bytes() if (ROOT / name).is_file() else
                   b'raise RuntimeError("harness fixture must never execute")\n')
            save(repo, name, raw)
        for name in candidate.CLI_FILES:
            save(repo, name, (ROOT / name).read_bytes())
        save(repo, 'packages/claw-hermes/must_not_execute.py',
             b'raise RuntimeError("packaged source must never execute")\n')
        envelope = dict(original, nativeFeature=native_commit, sources=native_hashes)
        envelope_raw = candidate.canonical(envelope)
        manifest_sha = candidate.digest(envelope_raw)
        save(repo, candidate.NATIVE_MANIFEST, envelope_raw)
        selection = json.loads((ROOT / candidate.SELECTION).read_bytes())
        selection.update(nativeFeature=native_commit, sourceManifestSha256=manifest_sha)
        save(repo, candidate.SELECTION, candidate.canonical(selection))
        host_lock = json.loads((ROOT / candidate.HOST_LOCK).read_bytes())
        host_lock['native_commit'] = native_commit
        for row in host_lock['files']:
            row['sha256'] = native_hashes[row['path']]
        save(repo, candidate.HOST_LOCK, candidate.canonical(host_lock))
        support_lock_name = 'config/execution-gate/source-lock.json'
        support_lock = json.loads((ROOT / support_lock_name).read_bytes())
        for row in support_lock['files']:
            row['sha256'] = native_hashes[row['path']]
        support_lock_raw = candidate.canonical(support_lock)
        save(repo, support_lock_name, support_lock_raw)
        support_pins = dict(candidate.SUPPORT_FILES)
        support_pins[support_lock_name] = candidate.digest(support_lock_raw)
        dependencies = {'dependencies/pkg/fixture_' + str(i).zfill(4) + '.py':
                        candidate.digest(('dependency fixture ' + str(i)).encode())
                        for i in range(candidate.DEPENDENCY_COUNT)}
        record = {'nativeExitCode': 0, 'sourceBytesUnchanged': True,
                  'installedBytesMatchPriorAcceptedTarget': True, 'sources': dependencies}
        save(repo, candidate.DEPENDENCY_RECORD, candidate.canonical(record))
        revision = commit(repo)
        with patch.object(candidate, 'NATIVE_FEATURE', native_commit), \
                patch.object(candidate, 'MANIFEST_SHA256', manifest_sha), \
                patch.object(candidate, 'REVIEWED_NATIVE_MARKERS', ()), \
                patch.object(candidate, 'SUPPORT_FILES', MappingProxyType(support_pins)), \
                patch.object(verifier, '_builder', return_value=candidate):
            yield repo, native, revision


class FixedServiceGenerationTests(unittest.TestCase):
    def test_real_generation_and_historical_tools_remain_exact(self):
        self.assertEqual(candidate.NATIVE_FEATURE, SERVICE_NATIVE)
        self.assertEqual(candidate.NATIVE_COUNT, 760)
        self.assertEqual(candidate.MANIFEST_SHA256, SERVICE_MANIFEST)
        for name, expected in LEGACY_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest(),
                                 expected)

    def test_complete_cli_closure_is_pinned_to_actual_sources(self):
        self.assertIn('scripts/alaz_local.mjs', candidate.CLI_FILES)
        self.assertIn('packages/upstream/openclaw/string-coerce.ts', candidate.CLI_FILES)
        self.assertIn('packages/claw-hermes/package.json', candidate.CLI_FILES)
        self.assertEqual(len(candidate.CLI_FILES), 12)
        for name, expected in candidate.CLI_FILES.items():
            with self.subTest(name=name):
                self.assertEqual(candidate.digest((ROOT / name).read_bytes()), expected)

    def test_execution_and_recovery_support_files_are_explicit_and_pinned(self):
        self.assertEqual(set(candidate.SUPPORT_FILES), SERVICE_SUPPORT)
        self.assertLessEqual(SERVICE_SUPPORT, candidate.EXACT)
        for name, expected in candidate.SUPPORT_FILES.items():
            with self.subTest(name=name):
                self.assertEqual(candidate.digest((ROOT / name).read_bytes()), expected)

    def test_real_verifier_requires_all_four_external_identity_pins(self):
        with self.assertRaises(ValueError):
            verifier.prepare_bytes(b'{}\n', b'not an archive',
                expected_manifest_sha256='0' * 64,
                expected_archive_sha256='0' * 64,
                expected_harness_commit='0' * 40,
                expected_native_feature='d1516731308de8e87130dc68124e69aad35d6911')

    def test_verifier_loads_exact_pinned_builder_and_refuses_other_hash(self):
        loaded = verifier._builder()
        self.assertEqual(loaded.NATIVE_FEATURE, SERVICE_NATIVE)
        self.assertEqual(candidate.digest((ROOT / 'scripts/build_service_candidate.py').read_bytes()),
                         verifier.BUILDER_SHA256)
        with patch.object(verifier, 'BUILDER_SHA256', '0' * 64):
            with self.assertRaisesRegex(verifier.VerificationRejected, 'service_builder_changed'):
                verifier._builder.__wrapped__()


class OwnedServiceCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.repo, cls.native, cls.revision = cls.stack.enter_context(fixture())
        cls.destination = cls.repo / 'scratch/service-candidates/accepted-fixture'
        cls.manifest = candidate.build(cls.repo, cls.revision, cls.native, cls.destination)
        cls.archive = (cls.destination / candidate.ARCHIVE).read_bytes()
        cls.source, cls.metadata, _, _ = candidate.source(cls.repo, cls.revision, cls.native)

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def prepare(self, manifest=None, archive=None, **overrides):
        manifest = self.manifest if manifest is None else manifest
        archive = self.archive if archive is None else archive
        raw = candidate.canonical(manifest)
        pins = {'expected_manifest_sha256': candidate.digest(raw),
                'expected_archive_sha256': candidate.digest(archive),
                'expected_harness_commit': self.revision,
                'expected_native_feature': candidate.NATIVE_FEATURE}
        pins.update(overrides)
        return verifier.prepare_bytes(raw, archive, **pins)

    def variant(self, changes=None, *, remove=()):
        command(self.repo, 'checkout', '--quiet', self.revision)
        for name in remove:
            (self.repo / name).unlink()
        for name, raw in (changes or {}).items():
            save(self.repo, name, raw)
        return commit(self.repo)

    def reseal(self, source):
        metadata = {}
        for name, raw in source.items():
            generated = name == 'accepted-dependencies.json'
            row = dict(self.metadata.get(name, {'mode': 0o644}))
            row.update(bytes=len(raw), sha256=candidate.digest(raw),
                gitBlob=None if generated else hashlib.sha1(
                    ('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest(),
                repository='generated-reference' if generated else
                           'native' if name.startswith('native/') else 'harness')
            metadata[name] = row
        archive = candidate.archive_bytes(source, metadata, self.revision)
        manifest = deepcopy(self.manifest)
        manifest.update(candidate.verify_archive(archive, metadata, self.revision))
        manifest['fileManifest'] = metadata
        manifest['harnessSourceFileCount'] = len(source) - candidate.NATIVE_COUNT - 1
        if 'accepted-dependencies.json' in source:
            manifest['dependencies']['inventorySha256'] = candidate.digest(
                source['accepted-dependencies.json'])
        return manifest, archive

    def test_exact_source_only_round_trip_and_immutable_preparation(self):
        prepared = self.prepare()
        self.assertEqual(dict(prepared.source), self.source)
        self.assertEqual(len(prepared.dependencies), 1162)
        self.assertEqual(sum(name.startswith('native/') for name in prepared.source), 760)
        self.assertEqual(set(path.name for path in self.destination.iterdir()),
                         {candidate.ARCHIVE, 'manifest.json', 'install-plan.json'})
        with self.assertRaises(TypeError):
            prepared.source['new.py'] = b'not mutable'
        for key in ('installed', 'executionAuthorized', 'dependenciesAcceptedForService',
                    'serviceReadinessAccepted', 'kernelAcceptance', 'realModelAcceptance',
                    'pythonIncluded', 'nodeIncluded'):
            self.assertIs(self.manifest[key], False)
        self.assertEqual(self.manifest['realModelCalls'], 0)

    def test_build_is_deterministic_and_cannot_overwrite_output(self):
        other = self.repo / 'scratch/service-candidates/repeat-fixture'
        candidate.build(self.repo, self.revision, self.native, other)
        for name in (candidate.ARCHIVE, 'manifest.json', 'install-plan.json'):
            self.assertEqual((other / name).read_bytes(), (self.destination / name).read_bytes())
        with self.assertRaises(ValueError):
            candidate.build(self.repo, self.revision, self.native, self.destination)

    def test_destination_outside_ignored_service_candidates_refuses(self):
        with self.assertRaises(ValueError):
            candidate.build(self.repo, self.revision, self.native, self.repo / 'export')
        self.assertFalse((self.repo / 'export').exists())

    def test_missing_service_entrypoint_or_transitive_ts_refuses(self):
        for name in ('scripts/run_supervised_service.py', 'scripts/run_service_projected.py',
                     'scripts/run_service_volume_worker.py', candidate.HOST_LOCK,
                     'packages/upstream/openclaw/string-coerce.ts'):
            with self.subTest(name=name):
                revision = self.variant(remove=(name,))
                with self.assertRaises(ValueError):
                    candidate.source(self.repo, revision, self.native)

    def test_modified_cli_import_closure_refuses_even_at_new_harness_commit(self):
        name = 'packages/upstream/openclaw/number-coercion.ts'
        revision = self.variant({name: self.source[name] + b'\nimport "./unselected.ts";\n'})
        with self.assertRaises(ValueError):
            candidate.source(self.repo, revision, self.native)

    def test_missing_or_changed_execution_and_recovery_support_refuses(self):
        for name in SERVICE_SUPPORT:
            with self.subTest(name=name, mutation='missing'):
                revision = self.variant(remove=(name,))
                with self.assertRaises(ValueError):
                    candidate.source(self.repo, revision, self.native)
            with self.subTest(name=name, mutation='changed'):
                revision = self.variant({name: self.source[name] + b'\n'})
                with self.assertRaises(ValueError):
                    candidate.source(self.repo, revision, self.native)

    def test_changed_support_cannot_pass_by_resealing_archive_and_manifest(self):
        for name in SERVICE_SUPPORT:
            with self.subTest(name=name):
                source = dict(self.source); source[name] += b'\n'
                manifest, archive = self.reseal(source)
                with self.assertRaises(ValueError):
                    self.prepare(manifest, archive)

    def test_selected_source_case_collision_refuses(self):
        # Construct immutable tree entries, not worktree files: Windows may
        # collapse these names even though Git objects preserve both exactly.
        rows = command(self.repo, 'ls-tree', '-z',
                       self.revision + ':packages/claw-hermes').split(b'\0')[:-1]
        for name, raw in ((b'Fixture.py', b'# first\n'), (b'fixture.py', b'# second\n')):
            self.assertNotIn(name, [row.split(b'\t', 1)[1] for row in rows])
            blob = command(self.repo, 'hash-object', '-w', '--stdin', data=raw).strip()
            rows.append(b'100644 blob ' + blob + b'\t' + name)
        tree = command(self.repo, 'mktree', '-z', data=b'\0'.join(rows) + b'\0').strip()
        for parent, child in ((self.revision + ':packages', b'claw-hermes'),
                              (self.revision, b'packages')):
            rows = command(self.repo, 'ls-tree', '-z', parent).split(b'\0')[:-1]
            self.assertEqual(sum(row.split(b'\t', 1)[1] == child for row in rows), 1)
            rows = [b'040000 tree ' + tree + b'\t' + child
                    if row.split(b'\t', 1)[1] == child else row for row in rows]
            tree = command(self.repo, 'mktree', '-z', data=b'\0'.join(rows) + b'\0').strip()
        revision = command(self.repo, '-c', 'user.name=Owned Service Candidate Test',
            '-c', 'user.email=service-candidate@example.invalid', '-c', 'commit.gpgsign=false',
            'commit-tree', tree.decode('ascii'), '-p', self.revision,
            '-m', 'owned immutable case collision').decode('ascii').strip()
        names = command(self.repo, 'ls-tree', '-r', '--name-only', '-z', revision).split(b'\0')
        self.assertIn(b'packages/claw-hermes/Fixture.py', names)
        self.assertIn(b'packages/claw-hermes/fixture.py', names)
        with self.assertRaisesRegex(candidate.CandidateRejected, 'candidate_case_collision'):
            candidate.source(self.repo, revision, self.native)

    def test_host_lock_native_or_file_hash_disagreement_refuses(self):
        for field in ('native_commit', 'sha256'):
            with self.subTest(field=field):
                lock = json.loads(self.source[candidate.HOST_LOCK])
                if field == 'native_commit':
                    lock[field] = '0' * 40
                else:
                    lock['files'][0][field] = '0' * 64
                revision = self.variant({candidate.HOST_LOCK: candidate.canonical(lock)})
                with self.assertRaises(ValueError):
                    candidate.source(self.repo, revision, self.native)

    def test_native_manifest_external_hash_cannot_be_replaced(self):
        envelope = json.loads(self.source[candidate.NATIVE_MANIFEST])
        envelope['purpose'] += ' changed'
        revision = self.variant({candidate.NATIVE_MANIFEST: candidate.canonical(envelope)})
        with self.assertRaises(ValueError):
            candidate.source(self.repo, revision, self.native)

    def test_native_hash_and_count_remain_bound_after_archive_resealing(self):
        name = next(name for name in self.source if name.startswith('native/'))
        changed = dict(self.source); changed[name] = b'# altered native fixture\n'
        missing = dict(self.source); del missing[name]
        for label, source in (('hash', changed), ('missing', missing)):
            with self.subTest(case=label):
                manifest, archive = self.reseal(source)
                with self.assertRaises(ValueError):
                    self.prepare(manifest, archive)

    def test_git_replacement_and_ambient_repository_redirection_are_ignored(self):
        revision = self.variant(remove=('scripts/run_supervised_service.py',))
        command(self.repo, 'replace', self.revision, revision)
        try:
            with patch.dict(os.environ, {'GIT_DIR': str(self.native / '.git'),
                                         'GIT_WORK_TREE': str(self.native)}):
                payload, _, _, _ = candidate.source(self.repo, self.revision, self.native)
            self.assertEqual(payload, self.source)
        finally:
            command(self.repo, 'replace', '-d', self.revision)

    def test_each_external_identity_pin_is_mandatory(self):
        for key, value in (('expected_manifest_sha256', '0' * 64),
                           ('expected_archive_sha256', '0' * 64),
                           ('expected_harness_commit', '0' * 40),
                           ('expected_native_feature', SERVICE_NATIVE)):
            with self.subTest(pin=key), self.assertRaises(ValueError):
                self.prepare(**{key: value})

    def test_old_candidate_kind_and_native_generation_refuse(self):
        for key, value in (('kind', 'PROJECTED_STARTUP_SOURCE_CANDIDATE_NOT_INSTALLED'),
                           ('nativeFeature', 'd1516731308de8e87130dc68124e69aad35d6911'),
                           ('nativeSourceFileCount', 756)):
            manifest = deepcopy(self.manifest); manifest[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.prepare(manifest)

    def test_acceptance_claims_and_noninteger_model_count_refuse(self):
        fields = ('installed', 'executionAuthorized', 'dependenciesAcceptedForService',
                  'serviceReadinessAccepted', 'kernelAcceptance', 'realModelAcceptance',
                  'pythonIncluded', 'nodeIncluded')
        for key in fields + ('realModelCalls',):
            manifest = deepcopy(self.manifest)
            manifest[key] = False if key == 'realModelCalls' else True
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.prepare(manifest)

    def test_runtime_selection_and_readback_cannot_be_invented(self):
        requirements = self.manifest['runtimeRequirements']
        self.assertEqual((requirements['selection'], requirements['readback']),
                         ('NOT_RUN', 'NOT_RUN'))
        for runtime, version in (('python', '3.12'), ('node', '>=24 <25')):
            self.assertEqual(requirements[runtime], {'version': version, 'path': None,
                             'sha256': None, 'observedVersion': None})
            for key, value in (('path', '/owned/unobserved-binary'),
                               ('sha256', '0' * 64), ('observedVersion', version)):
                manifest = deepcopy(self.manifest)
                manifest['runtimeRequirements'][runtime][key] = value
                with self.subTest(runtime=runtime, field=key), self.assertRaises(ValueError):
                    self.prepare(manifest)

    def test_extra_source_or_missing_required_source_refuses_after_resealing(self):
        missing = dict(self.source); del missing['packages/upstream/openclaw/string-coerce.ts']
        extra = dict(self.source, **{'unexpected.txt': b'not selected\n'})
        for label, source in (('missing', missing), ('extra', extra)):
            with self.subTest(case=label):
                manifest, archive = self.reseal(source)
                with self.assertRaises(ValueError):
                    self.prepare(manifest, archive)

    def test_changed_payload_digest_refuses(self):
        manifest = deepcopy(self.manifest)
        manifest['fileManifest']['LICENSE']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.prepare(manifest)

    def test_git_blob_metadata_must_match_actual_payload_bytes(self):
        manifest = deepcopy(self.manifest)
        manifest['fileManifest']['LICENSE']['gitBlob'] = '0' * 40
        with self.assertRaises(ValueError):
            self.prepare(manifest)

    def test_duplicate_json_field_refuses_with_matching_external_pin(self):
        raw = b'{"schemaVersion": 1,' + candidate.canonical(self.manifest)[1:]
        with self.assertRaises(ValueError):
            verifier.prepare_bytes(raw, self.archive,
                expected_manifest_sha256=candidate.digest(raw),
                expected_archive_sha256=candidate.digest(self.archive),
                expected_harness_commit=self.revision,
                expected_native_feature=candidate.NATIVE_FEATURE)

    def test_resealed_dependency_reference_cannot_claim_service_acceptance(self):
        manifest = deepcopy(self.manifest)
        manifest['dependencies']['installedBytesVerifiedNow'] = True
        with self.assertRaises(ValueError):
            self.prepare(manifest)

    def test_dependency_map_path_traversal_refuses_after_resealing(self):
        source = dict(self.source)
        dependencies = json.loads(source['accepted-dependencies.json'])
        name = next(iter(dependencies))
        dependencies['../escape.py'] = dependencies.pop(name)
        source['accepted-dependencies.json'] = candidate.canonical(dependencies)
        manifest, archive = self.reseal(source)
        with self.assertRaises(ValueError):
            self.prepare(manifest, archive)

    def test_archive_link_and_trailing_payload_refuse_after_resealing(self):
        changed = io.BytesIO()
        with tarfile.open(fileobj=io.BytesIO(self.archive), mode='r:') as original, \
                tarfile.open(fileobj=changed, mode='w', format=tarfile.PAX_FORMAT,
                             pax_headers=original.pax_headers) as archive:
            for index, member in enumerate(original):
                stream = original.extractfile(member)
                with stream:
                    raw = stream.read()
                if index == 0:
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/owned-fixture-target'; member.size = 0
                    archive.addfile(member)
                else:
                    archive.addfile(member, io.BytesIO(raw))
        for label, raw in (('link', changed.getvalue()),
                           ('trailing', self.archive + b'unapproved trailing payload')):
            with self.subTest(case=label):
                manifest = deepcopy(self.manifest)
                manifest['archiveSha256'] = candidate.digest(raw)
                manifest['archiveBytes'] = len(raw)
                with self.assertRaises(ValueError):
                    self.prepare(manifest, raw)

    def test_nonzero_member_padding_refuses_with_matching_external_pins(self):
        with tarfile.open(fileobj=io.BytesIO(self.archive), mode='r:') as archive:
            member = next(member for member in archive if member.size % 512)
            offset = member.offset_data + member.size
        changed = bytearray(self.archive)
        self.assertEqual(changed[offset], 0)
        changed[offset] = 1
        raw = bytes(changed); manifest = deepcopy(self.manifest)
        manifest['archiveSha256'] = candidate.digest(raw)
        manifest['archiveBytes'] = len(raw)
        with self.assertRaisesRegex(ValueError, 'service_archive_noncanonical'):
            self.prepare(manifest, raw)

    def test_archive_missing_extra_or_duplicate_member_refuses(self):
        for mutation in ('missing', 'extra', 'duplicate'):
            changed = io.BytesIO()
            with tarfile.open(fileobj=io.BytesIO(self.archive), mode='r:') as original, \
                    tarfile.open(fileobj=changed, mode='w', format=tarfile.PAX_FORMAT,
                                 pax_headers=original.pax_headers) as archive:
                for index, member in enumerate(original):
                    stream = original.extractfile(member)
                    with stream:
                        raw = stream.read()
                    if mutation == 'missing' and index == 0:
                        continue
                    archive.addfile(member, io.BytesIO(raw))
                    if mutation == 'duplicate' and index == 0:
                        archive.addfile(member, io.BytesIO(raw))
                if mutation == 'extra':
                    member = tarfile.TarInfo(candidate.PREFIX + 'unselected.txt')
                    member.size = 5; member.mode = 0o644
                    archive.addfile(member, io.BytesIO(b'extra'))
            raw = changed.getvalue(); manifest = deepcopy(self.manifest)
            manifest['archiveSha256'] = candidate.digest(raw)
            manifest['archiveBytes'] = len(raw)
            with self.subTest(case=mutation), self.assertRaises(ValueError):
                self.prepare(manifest, raw)


if __name__ == '__main__':
    unittest.main()
