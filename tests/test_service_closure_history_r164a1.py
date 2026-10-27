"""Historical source/test custody only; no product or native execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import historical_service_closure_r164a1 as history


ROOT = Path(__file__).resolve().parents[1]
LIVE_BYTES = b'# independent current-generation fixture, not old authority\n'
LIVE_SHA = hashlib.sha256(LIVE_BYTES).hexdigest()


class ServiceClosureHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        names = {history.BINDING, *history.PRESERVED_R163,
                 *history.PRESERVED_RESOLVERS, *history.PRESERVED_R160,
                 *(row['path'] for row in history.PARENTS.values())}
        for name in sorted(names):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        for name in history.PARENTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(LIVE_BYTES)

    def test_exact_parent_product_and_test_generations_select_named_archives(self):
        self.assertEqual(history.BASE, '28a12e1b18a839a9489a0c463d904b8e9a46db03')
        self.assertEqual(len(history.PARENT_SOURCES), 3)
        self.assertEqual(len(history.PARENT_TESTS), 6)
        for name, row in history.PARENTS.items():
            with self.subTest(name=name):
                archive = history.archived_source(self.root, name, row['sha256'])
                self.assertEqual(archive, self.root / row['path'])
                self.assertNotEqual(archive, self.root / name)
                self.assertEqual(len(archive.read_bytes()), row['size'])
                self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), row['sha256'])

    def test_current_unknown_older_alias_and_nonexact_inputs_do_not_read_archive(self):
        class Text(str):
            pass
        cases = []
        for name, row in history.PARENTS.items():
            cases.extend(((name, LIVE_SHA), (name, 'f' * 64),
                          ('other.py', row['sha256']), (Text(name), row['sha256']),
                          (name, Text(row['sha256'])), (None, row['sha256']),
                          (name, None), ('./' + name, row['sha256']),
                          (name.replace('/', '\\'), row['sha256'])))
        cases.extend((history.VOLUME, old) for old in
                     (history.EARLIER_R160_SHA, history.FINAL_R160_SHA))
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected archive I/O')):
            for name, digest in cases:
                with self.subTest(name=name, digest=digest):
                    self.assertIsNone(history.archived_source(self.root, name, digest))

    def test_path_and_digest_cannot_be_crossed_between_parent_generations(self):
        for name, row in history.PARENTS.items():
            for other, different in history.PARENTS.items():
                if name == other:
                    continue
                with self.subTest(name=name, other=other), patch.object(
                        Path, 'open', side_effect=AssertionError('unexpected archive I/O')):
                    self.assertIsNone(history.archived_source(self.root, name, different['sha256']))

    def test_binding_refuses_changed_base_scope_types_paths_hashes_and_evidence_sets(self):
        original = json.loads(history.binding_bytes())
        mutations = []
        for key, value in (('version', True), ('version', 1.0), ('base', '0' * 40),
                           ('scope', 'current_source_acceptance'), ('currentSourceAcceptance', True),
                           ('nativeRerun', True), ('sources', {}), ('testSources', {}),
                           ('preservedR163Evidence', {}), ('preservedResolvers', {}),
                           ('preservedR160Evidence', {}), ('r160RecordSourceGenerations', {})):
            value_copy = copy.deepcopy(original)
            value_copy[key] = value
            mutations.append((key, value_copy))
        for group in ('sources', 'testSources'):
            name = next(iter(original[group]))
            for key, value in (('path', name), ('path', '../outside.py'),
                               ('sha256', LIVE_SHA), ('size', 0)):
                value_copy = copy.deepcopy(original)
                value_copy[group][name][key] = value
                mutations.append((group + '/' + key, value_copy))
        source, row = next(iter(history.PARENTS.items()))
        for label, value in mutations:
            (self.root / history.BINDING).write_bytes(
                (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
            with self.subTest(label=label), self.assertRaisesRegex(AssertionError, 'source binding'):
                history.archived_source(self.root, source, row['sha256'])

    def test_binding_format_and_length_are_byte_exact(self):
        name, row = next(iter(history.PARENTS.items()))
        binding = self.root / history.BINDING
        for raw in (history.binding_bytes() + b' ', history.binding_bytes()[:-1],
                    json.dumps(json.loads(history.binding_bytes())).encode()):
            binding.write_bytes(raw)
            with self.subTest(size=len(raw)), self.assertRaisesRegex(AssertionError, 'source binding'):
                history.archived_source(self.root, name, row['sha256'])

    def test_every_archive_rejects_truncation_append_or_changed_same_length_bytes(self):
        for name, row in history.PARENTS.items():
            path = self.root / row['path']
            original = path.read_bytes()
            for raw in (original[:-1], original + b'\n', bytes([original[0] ^ 1]) + original[1:]):
                path.write_bytes(raw)
                with self.subTest(name=name, size=len(raw)), \
                        self.assertRaisesRegex(AssertionError, 'historical bytes'):
                    history.archived_source(self.root, name, row['sha256'])
            path.write_bytes(original)

    def test_known_parent_missing_binding_or_archive_fails_closed(self):
        name, row = next(iter(history.PARENTS.items()))
        binding = self.root / history.BINDING
        binding.unlink()
        with self.assertRaises(FileNotFoundError):
            history.archived_source(self.root, name, row['sha256'])
        binding.write_bytes(history.binding_bytes())
        (self.root / row['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            history.archived_source(self.root, name, row['sha256'])

    def test_aliases_cannot_replace_binding_archive_or_preserved_files(self):
        source, row = next(iter(history.PARENTS.items()))
        aliases = (history.BINDING, row['path'], next(iter(history.PRESERVED_R163)),
                   next(iter(history.PRESERVED_RESOLVERS)), next(iter(history.PRESERVED_R160)))
        for name in aliases:
            with self.subTest(name=name), patch.object(
                    Path, 'is_symlink', lambda path: path == self.root / name):
                with self.assertRaisesRegex(AssertionError, 'path changed'):
                    if name in (history.BINDING, row['path']):
                        history.archived_source(self.root, source, row['sha256'])
                    else:
                        history.assert_preserved_evidence(self.root)

    def test_current_bytes_are_not_historical_or_current_acceptance_authority(self):
        for name, row in history.PARENTS.items():
            live = self.root / name
            live.write_bytes(b'# changed current source or test\n')
            self.assertIsNotNone(history.archived_source(self.root, name, row['sha256']))
            self.assertIsNone(history.archived_source(
                self.root, name, hashlib.sha256(live.read_bytes()).hexdigest()))
        binding = json.loads(history.binding_bytes())
        self.assertIs(binding['currentSourceAcceptance'], False)
        self.assertIs(binding['nativeRerun'], False)

    def test_each_original_r163_evidence_file_rejects_changed_bytes(self):
        self.assertEqual(len(history.PRESERVED_R163), 13)
        for name in history.PRESERVED_R163:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(name=name), self.assertRaisesRegex(AssertionError, 'historical bytes'):
                history.assert_preserved_evidence(self.root)
            path.write_bytes(original)

    def test_each_old_resolver_and_r160_record_or_log_rejects_changed_bytes(self):
        self.assertEqual(len(history.PRESERVED_RESOLVERS), 7)
        self.assertEqual(len(history.PRESERVED_R160), 6)
        for name in (*history.PRESERVED_RESOLVERS, *history.PRESERVED_R160):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(name=name), self.assertRaisesRegex(AssertionError, 'historical bytes'):
                history.assert_preserved_evidence(self.root)
            path.write_bytes(original)

    def test_old_r160_generations_stay_distinct_from_r163_parent(self):
        history.assert_preserved_evidence(self.root)
        generations = {history.EARLIER_R160_SHA, history.FINAL_R160_SHA,
                       history.PARENT_SOURCES[history.VOLUME]['sha256']}
        self.assertEqual(len(generations), 3)
        for name, expected in history.R160_GENERATIONS.items():
            record = json.loads((self.root / name).read_bytes())
            self.assertEqual(record['sourceHashes'][history.VOLUME], expected)
            self.assertIsNone(history.archived_source(self.root, history.VOLUME, expected))

    def test_old_721_test_receipts_keep_their_original_product_test_and_log_selection(self):
        history.assert_preserved_evidence(self.root)
        for platform, passed, skipped in (('linux', 721, 0), ('windows', 608, 113)):
            record = json.loads((self.root / (history.R163 + 'focused-' + platform + '.json')).read_bytes())
            self.assertEqual((record['testsRun'], record['passed'], record['skipped']), (721, passed, skipped))
            for field, mapping in (('sourceHashes', history.PARENT_SOURCES),
                                   ('testHashes', history.PARENT_TESTS)):
                for name, row in mapping.items():
                    self.assertEqual(record[field][name], row['sha256'])
                    self.assertIsNotNone(history.archived_source(self.root, name, record[field][name]))
            self.assertIs(record['kernelConfinementTested'], False)
            self.assertIs(record['nativeServiceStarted'], False)
        check = json.loads((self.root / (history.R163 + 'source-check.json')).read_bytes())
        self.assertIs(check['volumeClosureIntegrated'], False)
        self.assertIs(check['installedServiceAccepted'], False)

    def test_tracked_archives_and_original_evidence_are_byte_exact(self):
        history.assert_preserved_evidence(ROOT)
        for name, row in history.PARENTS.items():
            self.assertIsNotNone(history.archived_source(ROOT, name, row['sha256']))


if __name__ == '__main__':
    unittest.main()
