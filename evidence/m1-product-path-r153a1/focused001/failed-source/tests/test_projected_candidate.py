"""Real Git/source-candidate checks; no packaged code or native runtime executes."""
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_projected_candidate as candidate


def command(repo, *args, data=None):
    result = subprocess.run(['git', '-C', str(repo), *args], input=data,
                            capture_output=True, check=True, timeout=30)
    return result.stdout


def save(repo, path, data):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def commit(repo, message='owned fixture'):
    command(repo, 'add', '--all')
    command(repo, '-c', 'user.name=Owned Candidate Test',
            '-c', 'user.email=candidate-test@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '--quiet', '-m', message)
    return command(repo, 'rev-parse', 'HEAD').decode().strip()


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='alaz-projected-candidate-') as directory:
        base = Path(directory).resolve()
        repo = base / 'harness'; native = base / 'native'
        for root in (repo, native):
            root.mkdir(); command(root, 'init', '--quiet')
            command(root, 'config', 'core.autocrlf', 'false')
        # These sources would fail if the builder imported or executed them.
        source_bytes = b'raise RuntimeError("packaged source must not execute")\n'
        native_files = {}
        for number in range(candidate.NATIVE_COUNT):
            name = 'agent/module' + str(number).zfill(4) + '.py'
            value = source_bytes + ('# ' + str(number) + '\n').encode()
            save(native, name, value); native_files[name] = candidate.digest(value)
        native_sha = commit(native)
        save(repo, '.gitignore', b'scratch/\n')
        for name in candidate.EXACT | candidate.REQUIRED_MODULES:
            save(repo, name, b'{}\n' if name.endswith('.json') else source_bytes)
        envelope = {'schema': 1, 'nativeFeature': native_sha, 'sources': native_files}
        save(repo, candidate.NATIVE_MANIFEST, candidate.canonical(envelope))
        dependencies = {'dependencies/pkg/module' + str(i).zfill(4) + '.py':
                        candidate.digest(('dependency ' + str(i)).encode())
                        for i in range(candidate.DEPENDENCY_COUNT)}
        record = {'nativeExitCode': 0, 'sourceBytesUnchanged': True,
                  'installedBytesMatchPriorAcceptedTarget': True, 'sources': dependencies}
        save(repo, candidate.DEPENDENCY_RECORD, candidate.canonical(record))
        revision = commit(repo)
        with patch.object(candidate, 'NATIVE_FEATURE', native_sha):
            yield repo, native, revision, envelope, record


def output(repo, name='candidate'):
    return repo / 'scratch' / 'projected-candidates' / name


class GitCandidate(unittest.TestCase):
    def test_exact_git_export_is_reproducible_without_running_source(self):
        with fixture() as (repo, native, revision, _, __):
            first = candidate.build(repo, revision, native, output(repo, 'a'))
            second = candidate.build(repo, revision, native, output(repo, 'b'))
            self.assertEqual(first, second)
            for name in (candidate.ARCHIVE, 'manifest.json', 'install-plan.json'):
                self.assertEqual((output(repo, 'a') / name).read_bytes(),
                                 (output(repo, 'b') / name).read_bytes())
            self.assertEqual(first['nativeSourceFileCount'], 756)
            self.assertEqual(first['dependencies']['fileCount'], 1162)
            self.assertIs(first['dependencies']['bytesIncluded'], False)
            self.assertIs(first['dependencies']['installedBytesVerifiedNow'], False)
            for key in ('installed', 'executionAuthorized', 'privilegedExecutionTested',
                        'positiveProjectedReadinessAccepted', 'finiteWorkExecuted'):
                self.assertIs(first[key], False)
            self.assertEqual(first['realModelCalls'], 0)
            plan = json.loads((output(repo, 'a') / 'install-plan.json').read_bytes())
            self.assertEqual(plan['archiveSha256'], first['archiveSha256'])
            self.assertIs(plan['executionAuthorized'], False)
            self.assertIs(plan['historicalDeniedOperationsMayBeRetried'], False)
            with tarfile.open(output(repo, 'a') / candidate.ARCHIVE) as archive:
                names = archive.getnames()
                self.assertFalse(any(n.startswith(candidate.PREFIX + 'dependencies/') for n in names))
                self.assertIn(candidate.PREFIX + 'accepted-dependencies.json', names)
                self.assertIn(candidate.PREFIX + 'scripts/run_supervised_retained.py', names)

    def test_dirty_files_and_autocrlf_do_not_change_immutable_candidate(self):
        with fixture() as (repo, native, revision, _, __):
            before = candidate.build(repo, revision, native, output(repo, 'before'))
            save(repo, 'packages/claw-hermes/gateway_retained_launch.py', b'dirty user bytes\r\n')
            save(native, 'agent/module0000.py', b'other uncommitted native bytes\n')
            save(repo, '.env', b'owned private test data\n')
            command(repo, 'config', 'core.autocrlf', 'true')
            after = candidate.build(repo, revision, native, output(repo, 'after'))
            self.assertEqual(before, after)
            self.assertEqual(command(repo, 'config', 'core.autocrlf').strip(), b'true')
            self.assertEqual((repo / '.env').read_bytes(), b'owned private test data\n')
            self.assertNotIn('.env', after['fileManifest'])

    def test_git_replacement_refs_cannot_substitute_exported_sources(self):
        with fixture() as (repo, native, revision, _, __):
            before = candidate.build(repo, revision, native, output(repo, 'before'))
            save(repo, 'packages/claw-hermes/gateway_retained_launch.py', b'replacement source\n')
            replaced = commit(repo, 'replacement fixture')
            command(repo, 'replace', revision, replaced)
            self.assertNotEqual(command(repo, 'show', revision + ':packages/claw-hermes/gateway_retained_launch.py'),
                                b'raise RuntimeError("packaged source must not execute")\n')
            after = candidate.build(repo, revision, native, output(repo, 'after'))
            self.assertEqual(before, after)

    def test_git_environment_cannot_redirect_explicit_repository(self):
        with fixture() as (repo, native, revision, _, __):
            with patch.dict(os.environ, {'GIT_DIR': str(native / '.git'),
                                         'GIT_WORK_TREE': str(native)}):
                result = candidate.build(repo, revision, native, output(repo))
            self.assertEqual(result['harnessCommit'], revision)

    def test_missing_fixed_entrypoint_refuses_before_creating_output(self):
        with fixture() as (repo, native, _, __, ___):
            (repo / 'scripts/run_supervised_retained.py').unlink()
            revision = commit(repo)
            with self.assertRaisesRegex(candidate.CandidateRejected, 'required_source_missing'):
                candidate.build(repo, revision, native, output(repo))
            self.assertFalse(output(repo).exists())

    def test_git_symlink_mode_is_rejected_without_following_worktree_file(self):
        with fixture() as (repo, native, _, __, ___):
            name = 'packages/claw-hermes/gateway_supervised_launch.py'
            oid = command(repo, 'hash-object', '-w', '--stdin', data=b'/not/followed').decode().strip()
            command(repo, 'update-index', '--cacheinfo', '120000,' + oid + ',' + name)
            command(repo, '-c', 'user.name=Owned Candidate Test',
                    '-c', 'user.email=candidate-test@example.invalid', '-c', 'commit.gpgsign=false',
                    'commit', '--quiet', '-m', 'link fixture')
            revision = command(repo, 'rev-parse', 'HEAD').decode().strip()
            with self.assertRaisesRegex(candidate.CandidateRejected, 'regular_source_only'):
                candidate.build(repo, revision, native, output(repo))
            self.assertFalse(output(repo).exists())

    def test_native_envelope_must_match_actual_git_blob(self):
        with fixture() as (repo, native, _, envelope, __):
            envelope['sources']['agent/module0000.py'] = '0' * 64
            save(repo, candidate.NATIVE_MANIFEST, candidate.canonical(envelope))
            revision = commit(repo)
            with self.assertRaisesRegex(candidate.CandidateRejected, 'native_source_changed'):
                candidate.build(repo, revision, native, output(repo))
            self.assertFalse(output(repo).exists())

    def test_native_count_and_feature_are_fixed(self):
        with fixture() as (repo, native, _, envelope, __):
            for change in ('feature', 'count', 'schema_type'):
                modified = json.loads(json.dumps(envelope))
                if change == 'feature': modified['nativeFeature'] = 'b' * 40
                elif change == 'count': modified['sources'].pop('agent/module0000.py')
                else: modified['schema'] = True
                save(repo, candidate.NATIVE_MANIFEST, candidate.canonical(modified))
                revision = commit(repo, change)
                with self.subTest(change=change), self.assertRaisesRegex(candidate.CandidateRejected, 'native_envelope'):
                    candidate.build(repo, revision, native, output(repo, change))
                self.assertFalse(output(repo, change).exists())

    def test_dependency_proof_refuses_failed_incomplete_and_malformed_records(self):
        with fixture() as (repo, native, _, __, record):
            for change in ('failed', 'exit_type', 'count', 'digest', 'path'):
                modified = json.loads(json.dumps(record))
                if change == 'failed': modified['nativeExitCode'] = 1
                elif change == 'exit_type': modified['nativeExitCode'] = False
                elif change == 'count': modified['sources'].pop('dependencies/pkg/module0000.py')
                elif change == 'digest': modified['sources']['dependencies/pkg/module0000.py'] = 'unknown'
                else: modified['sources']['dependencies/../outside.py'] = modified['sources'].pop('dependencies/pkg/module0000.py')
                save(repo, candidate.DEPENDENCY_RECORD, candidate.canonical(modified))
                revision = commit(repo, change)
                with self.subTest(change=change), self.assertRaises(candidate.CandidateRejected):
                    candidate.build(repo, revision, native, output(repo, change))
                self.assertFalse(output(repo, change).exists())

    def test_bounded_credential_scanner_rejects_source_before_output(self):
        with fixture() as (repo, native, _, __, ___):
            # Deliberately synthetic scanner fixture, no credential is used.
            value = b'# ' + b'sk-' + b'X' * 40 + b'\n'
            save(repo, 'packages/claw-hermes/gateway_supervised_launch.py', value)
            revision = commit(repo)
            with self.assertRaisesRegex(candidate.CandidateRejected, 'credential_pattern'):
                candidate.build(repo, revision, native, output(repo))
            self.assertFalse(output(repo).exists())


class OutputBoundaries(unittest.TestCase):
    def test_outside_and_existing_destination_never_reach_source_read(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            existing = output(repo); existing.mkdir(parents=True)
            sentinel = existing / 'keep'; sentinel.write_bytes(b'owned')
            with patch.object(candidate, 'source') as read:
                for path in (repo / 'outside', existing):
                    with self.subTest(path=path), self.assertRaises(candidate.CandidateRejected):
                        candidate.build(repo, 'a' * 40, repo, path)
                read.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b'owned')

    def test_unignored_scratch_destination_is_rejected(self):
        with fixture() as (repo, native, revision, _, __):
            (repo / '.gitignore').unlink()
            with patch.object(candidate, 'source') as read:
                with self.assertRaises(candidate.CandidateRejected):
                    candidate.build(repo, revision, native, output(repo))
                read.assert_not_called()
            self.assertFalse(output(repo).exists())

    def test_full_commit_required_before_git_is_called(self):
        with patch.object(candidate, 'git') as read:
            for value in ('HEAD', 'main', '123abc', 'A' * 40, '--all', None):
                with self.subTest(value=value), self.assertRaises(candidate.CandidateRejected):
                    candidate.commit(ROOT, value)
            read.assert_not_called()

    def test_source_selection_excludes_private_runtime_tests_and_qa(self):
        for name in ('runtime/state.db', '.env', 'vendor/hermes-agent/a.py',
                     'scripts/qa/f126c1_bootstrap.py', 'tests/test_anything.py', 'status.md'):
            self.assertFalse(candidate.selected(name))
        self.assertTrue(candidate.selected('packages/claw-hermes/gateway_supervised_launch.py'))
        self.assertTrue(candidate.selected('scripts/run_retained_projected.py'))


class ArchiveBoundaries(unittest.TestCase):
    revision = 'a' * 40
    payload = {'LICENSE': b'owned fixture\n', 'scripts/fixed.py': b'raise RuntimeError("not executed")\n'}

    def setUp(self):
        self.metadata = {name: {'mode': 0o644, 'bytes': len(data), 'sha256': candidate.digest(data)}
                         for name, data in self.payload.items()}

    def tar(self, entries=None, comment=None):
        if entries is None:
            entries = [(name, data, tarfile.REGTYPE, 0o644, '') for name, data in self.payload.items()]
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT,
                          pax_headers={'comment': comment or candidate.stamp(self.revision)}) as archive:
            for name, data, kind, mode, link in entries:
                info = tarfile.TarInfo(candidate.PREFIX + name)
                info.type = kind; info.mode = mode; info.linkname = link
                info.size = len(data) if kind == tarfile.REGTYPE else 0
                archive.addfile(info, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
        return stream.getvalue()

    def test_exact_archive_verified_without_extraction(self):
        with patch.object(tarfile.TarFile, 'extractall', side_effect=AssertionError('no extraction')):
            result = candidate.verify_archive(self.tar(), self.metadata, self.revision)
        self.assertEqual(result['sourceFileCount'], 2)

    def test_changed_payload_and_revision_are_rejected(self):
        changed = [(name, b'changed data' if name == 'LICENSE' else data, tarfile.REGTYPE, 0o644, '')
                   for name, data in self.payload.items()]
        for raw in (self.tar(changed), self.tar(comment='foreign source')):
            with self.subTest(rawLength=len(raw)), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(raw, self.metadata, self.revision)

    def test_missing_extra_duplicate_and_case_collision_are_rejected(self):
        rows = [(name, data, tarfile.REGTYPE, 0o644, '') for name, data in self.payload.items()]
        for entries in (rows[:1], rows + [('foreign.py', b'x', tarfile.REGTYPE, 0o644, '')],
                        rows + [rows[0]], rows + [('license', b'x', tarfile.REGTYPE, 0o644, '')]):
            with self.subTest(entries=len(entries)), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(self.tar(entries), self.metadata, self.revision)

    def test_links_special_files_and_unsafe_modes_are_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(self.tar([('LICENSE', b'', kind, 0o644, '/not/followed')]),
                                         self.metadata, self.revision)
        for mode in (0o666, 0o777, 0o4644):
            with self.subTest(mode=mode), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(self.tar([('LICENSE', self.payload['LICENSE'], tarfile.REGTYPE, mode, '')]),
                                         self.metadata, self.revision)

    def test_noncanonical_names_and_trailing_payload_are_rejected(self):
        for name in ('../LICENSE', './LICENSE', 'scripts//fixed.py', 'scripts\\fixed.py', 'LICENSE/'):
            with self.subTest(name=name), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(self.tar([(name, b'x', tarfile.REGTYPE, 0o644, '')]),
                                         self.metadata, self.revision)
        for raw in (self.tar() + b'foreign data', b'', b'not a tar'):
            with self.subTest(length=len(raw)), self.assertRaises(candidate.CandidateRejected):
                candidate.verify_archive(raw, self.metadata, self.revision)


if __name__ == '__main__':
    unittest.main()
