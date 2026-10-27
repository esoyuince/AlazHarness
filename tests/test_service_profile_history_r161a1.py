"""R161 historical/current source custody; no new native or kernel acceptance."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import historical_service_profile_r161a1 as history
from historical_self_identity_r150a1 import saved_generation_hash, source_hash, source_path


ROOT = Path(__file__).resolve().parents[1]
PROJECTION = 'packages/claw-hermes/gateway_state_projection.py'
LIVE_BYTES = b'# independent current-generation fixture; no runtime proof\n'
LIVE_SHA = hashlib.sha256(LIVE_BYTES).hexdigest()


class ServiceProfileHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding_path = self.root / history.BINDING
        self.binding_path.parent.mkdir(parents=True)
        self.binding_path.write_bytes((ROOT / history.BINDING).read_bytes())
        self.binding = json.loads(self.binding_path.read_bytes())
        for name, row in history.SOURCES.items():
            shutil.copyfile(ROOT / row['path'], self.root / row['path'])
            live = self.root / name
            live.parent.mkdir(parents=True, exist_ok=True)
            live.write_bytes(LIVE_BYTES)
        # The existing R150 resolver checks its immutable baseline metadata for
        # unknown projection generations, then deliberately returns the live path.
        for name in ('baseline.json', 'historical-source-bindings.json'):
            relative = 'evidence/d3b-self-identity-r150a1/' + name
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def fixture_pins(self):
        # The expected hash comes from a constant byte fixture, never a file read.
        return mock.patch.object(history, 'CURRENT_SOURCES', {
            name: LIVE_SHA for name in history.CURRENT_NAMES
        })

    def test_exact_parent_paths_and_digests_resolve_in_existing_chain(self):
        for name, row in history.SOURCES.items():
            with self.subTest(name=name):
                selected = self.root / row['path']
                self.assertEqual(history.archived_source(self.root, name, row['sha256']), selected)
                self.assertEqual(source_path(self.root, name, row['sha256']), selected)
                self.assertEqual(source_hash(self.root, name, row['sha256']), row['sha256'])
                self.assertEqual(saved_generation_hash(self.root, name, row['sha256']), row['sha256'])
                self.assertNotEqual(LIVE_SHA, row['sha256'])

    def test_unknown_name_or_digest_does_not_open_new_archive_metadata(self):
        with mock.patch.object(Path, 'open', side_effect=AssertionError('unexpected file read')):
            self.assertIsNone(history.archived_source(self.root, 'unlisted.py', '0' * 64))
            for name, row in history.SOURCES.items():
                self.assertIsNone(history.archived_source(self.root, name, LIVE_SHA))
                self.assertIsNone(history.archived_source(self.root, name, 'f' * 64))
                self.assertIsNone(history.archived_source(self.root, name + '.other', row['sha256']))

    def test_unknown_and_current_generations_stay_live_in_existing_chain(self):
        self.binding_path.unlink()
        for name in history.SOURCES:
            for expected in (LIVE_SHA, 'f' * 64):
                with self.subTest(name=name, expected=expected):
                    self.assertEqual(source_path(self.root, name, expected), self.root / name)
                    self.assertEqual(source_hash(self.root, name, expected), LIVE_SHA)
                    self.assertIsNone(saved_generation_hash(self.root, name, expected))

    def test_known_generation_requires_the_complete_exact_binding_record(self):
        expected = history.SOURCES[PROJECTION]['sha256']
        self.binding_path.unlink()
        with self.assertRaises(FileNotFoundError):
            history.archived_source(self.root, PROJECTION, expected)
        for raw in (b'{broken', b'x' * 131072):
            self.binding_path.write_bytes(raw)
            with self.assertRaisesRegex(AssertionError, 'historical source bindings'):
                history.archived_source(self.root, PROJECTION, expected)

    def test_binding_cannot_relabel_sources_types_outcomes_or_paths(self):
        mutations = []
        for key, value in (('version', True), ('version', 1.0), ('base', '0' * 40),
                           ('scope', 'current_runtime_acceptance'),
                           ('currentSourceAcceptance', True), ('nativeRerun', True)):
            changed = copy.deepcopy(self.binding)
            changed[key] = value
            mutations.append((key + '=' + repr(value), changed))
        for key, value in (('path', '../outside.py'), ('path', PROJECTION),
                           ('sha256', LIVE_SHA), ('size', 0)):
            changed = copy.deepcopy(self.binding)
            changed['sources'][PROJECTION][key] = value
            mutations.append((key + '=' + repr(value), changed))
        changed = copy.deepcopy(self.binding)
        changed['sources'].pop(PROJECTION)
        mutations.append(('missing source', changed))
        changed = copy.deepcopy(self.binding)
        changed['sources']['unlisted.py'] = changed['sources'][PROJECTION].copy()
        mutations.append(('additional source', changed))
        for label, changed in mutations:
            with self.subTest(label=label):
                self.binding_path.write_text(json.dumps(changed, indent=2, sort_keys=True) + '\n',
                                             encoding='utf-8')
                with self.assertRaisesRegex(AssertionError, 'historical source bindings'):
                    history.archived_source(self.root, PROJECTION,
                                            history.SOURCES[PROJECTION]['sha256'])

    def test_missing_truncated_or_equal_length_altered_archive_is_rejected(self):
        for name, row in history.SOURCES.items():
            path = self.root / row['path']
            original = path.read_bytes()
            with self.subTest(name=name, corruption='missing'):
                path.unlink()
                with self.assertRaises(FileNotFoundError):
                    history.archived_source(self.root, name, row['sha256'])
            for label, altered in (('truncated', original[:-1]),
                                    ('equal length', bytes([original[0] ^ 1]) + original[1:]),
                                    ('appended', original + b'!')):
                with self.subTest(name=name, corruption=label):
                    path.write_bytes(altered)
                    with self.assertRaisesRegex(AssertionError, 'archived source bytes changed'):
                        history.archived_source(self.root, name, row['sha256'])
            path.write_bytes(original)

    def test_archive_symlink_is_not_a_named_parent_file(self):
        row = history.SOURCES[PROJECTION]
        archived = self.root / row['path']
        other = self.root / 'other-parent-bytes.txt'
        other.write_bytes(archived.read_bytes())
        archived.unlink()
        try:
            archived.symlink_to(other)
        except OSError as error:
            self.skipTest('symlink fixture unavailable: ' + type(error).__name__)
        with self.assertRaisesRegex(AssertionError, 'archived source path changed'):
            history.archived_source(self.root, PROJECTION, row['sha256'])

    def test_tampered_live_projection_is_not_hidden_by_intact_parent_archive(self):
        with self.fixture_pins():
            history.assert_current_sources(self.root)
            (self.root / PROJECTION).write_bytes(b'# tampered live projection\n')
            self.assertEqual(source_hash(self.root, PROJECTION,
                                         history.SOURCES[PROJECTION]['sha256']),
                             history.SOURCES[PROJECTION]['sha256'])
            self.assertEqual(source_path(self.root, PROJECTION, LIVE_SHA), self.root / PROJECTION)
            with self.assertRaisesRegex(AssertionError, 'current product bytes changed'):
                history.assert_current_sources(self.root)

    def test_tampered_parent_archive_is_not_hidden_by_intact_live_projection(self):
        with self.fixture_pins():
            (self.root / history.SOURCES[PROJECTION]['path']).write_bytes(b'changed archive\n')
            history.assert_current_sources(self.root)
            with self.assertRaisesRegex(AssertionError, 'archived source bytes changed'):
                history.archived_source(self.root, PROJECTION,
                                        history.SOURCES[PROJECTION]['sha256'])

    def test_current_pin_must_be_fixed_valid_and_a_distinct_generation(self):
        for value in (None, True, '0' * 64, 'UNFROZEN'):
            with self.subTest(value=value), self.fixture_pins():
                history.CURRENT_SOURCES[PROJECTION] = value
                with self.assertRaisesRegex(AssertionError, 'current-source pins not frozen'):
                    history.assert_current_sources(self.root)
        with self.fixture_pins():
            history.CURRENT_SOURCES[PROJECTION] = history.SOURCES[PROJECTION]['sha256']
            with self.assertRaisesRegex(AssertionError, 'source generation did not advance'):
                history.assert_current_sources(self.root)
        with self.fixture_pins():
            with self.assertRaisesRegex(AssertionError, 'unlisted R161 current source'):
                history.assert_current_sources(self.root, names=('unlisted.py',))

    def test_original_history_test_and_resolver_are_preserved_byte_exact(self):
        for name in ('tests/test_self_identity_history_r150a1.py',
                     'tests/historical_borrowed_service_r159a1.py'):
            row = history.SOURCES[name]
            archive = history.archived_source(ROOT, name, row['sha256'])
            self.assertEqual(len(archive.read_bytes()), row['size'])
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), row['sha256'])
            self.assertNotEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), row['sha256'])

    def test_current_product_sources_match_reviewed_r161_generation(self):
        # These fixed pins are set after source review. No hash is learned from
        # the live files at runtime, and old archives cannot satisfy this check.
        history.assert_current_sources(ROOT)
        for name, expected in history.CURRENT_SOURCES.items():
            self.assertIsNone(history.archived_source(ROOT, name, expected))
            self.assertEqual(source_path(ROOT, name, expected), ROOT / name)
            self.assertIsNone(saved_generation_hash(ROOT, name, expected))


if __name__ == '__main__':
    unittest.main()
