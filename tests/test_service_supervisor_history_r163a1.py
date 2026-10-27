"""Parent source/evidence custody only; no native/kernel/service execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import historical_service_supervisor_r163a1 as history


ROOT = Path(__file__).resolve().parents[1]
LIVE_BYTES = b'# independent R163 current-generation fixture\n'
LIVE_SHA = hashlib.sha256(LIVE_BYTES).hexdigest()


class ServiceSupervisorHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in (history.BINDING, history.PARENT['path'], *history.RECORDS, *history.LOGS):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        live = self.root / history.SOURCE
        live.parent.mkdir(parents=True, exist_ok=True)
        live.write_bytes(LIVE_BYTES)

    def test_exact_parent_generation_selects_only_named_archive(self):
        self.assertEqual(history.BASE, 'dc1ccb5ecf4e9741f6fd828a03e8ebed7f9497b7')
        path = history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])
        self.assertEqual(path, self.root / history.PARENT['path'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), history.PARENT['sha256'])
        self.assertEqual(len(path.read_bytes()), history.PARENT['size'])
        self.assertNotEqual(path, self.root / history.SOURCE)

    def test_current_unknown_earlier_and_nonexact_inputs_do_not_read_archive(self):
        class Text(str):
            pass
        cases = [(history.SOURCE, LIVE_SHA), (history.SOURCE, 'f' * 64),
                 (history.SOURCE, history.EARLIER_SHA), ('other.py', history.PARENT['sha256']),
                 (Text(history.SOURCE), history.PARENT['sha256']),
                 (history.SOURCE, Text(history.PARENT['sha256'])),
                 (None, history.PARENT['sha256']), (history.SOURCE, None)]
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected archive I/O')):
            for name, expected in cases:
                with self.subTest(name=name, expected=expected):
                    self.assertIsNone(history.archived_source(self.root, name, expected))

    def test_record_generations_do_not_relabel_initial_r160_source(self):
        history.assert_preserved_evidence(self.root)
        initial = json.loads((self.root / (history.R160 + 'initial-focused-linux.json')).read_bytes())
        self.assertEqual(initial['sourceHashes'][history.SOURCE], history.EARLIER_SHA)
        self.assertNotEqual(history.EARLIER_SHA, history.PARENT['sha256'])
        self.assertIsNone(history.archived_source(self.root, history.SOURCE, history.EARLIER_SHA))
        for name in ('focused-linux.json', 'focused-windows.json'):
            record = json.loads((self.root / (history.R160 + name)).read_bytes())
            self.assertEqual(record['sourceHashes'][history.SOURCE], history.PARENT['sha256'])
            self.assertIsNotNone(history.archived_source(self.root, history.SOURCE,
                                                        record['sourceHashes'][history.SOURCE]))

    def test_binding_cannot_change_types_generation_paths_or_acceptance_scope(self):
        original = json.loads(history.binding_bytes())
        mutations = []
        for key, value in (('version', True), ('version', 1.0), ('base', '0' * 40),
                           ('scope', 'current_service_acceptance'), ('nativeRerun', True),
                           ('currentSourceAcceptance', True), ('preservedRecords', {}),
                           ('preservedLogs', {}), ('recordSourceGenerations', {})):
            changed = copy.deepcopy(original)
            changed[key] = value
            mutations.append((key, changed))
        for key, value in (('path', history.SOURCE), ('path', '../outside.py'),
                           ('sha256', LIVE_SHA), ('size', 0)):
            changed = copy.deepcopy(original)
            changed['sources'][history.SOURCE][key] = value
            mutations.append((key, changed))
        for label, changed in mutations:
            (self.root / history.BINDING).write_bytes(
                (json.dumps(changed, indent=2, sort_keys=True) + '\n').encode())
            with self.subTest(label=label), self.assertRaisesRegex(AssertionError, 'source binding'):
                history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])

    def test_binding_format_and_parent_size_are_exact(self):
        binding = self.root / history.BINDING
        binding.write_bytes(history.binding_bytes() + b' ')
        with self.assertRaisesRegex(AssertionError, 'source binding'):
            history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])
        binding.write_bytes(history.binding_bytes())
        archive = self.root / history.PARENT['path']
        original = archive.read_bytes()
        for raw in (original[:-1], original + b'\n', bytes([original[0] ^ 1]) + original[1:]):
            archive.write_bytes(raw)
            with self.subTest(size=len(raw)), self.assertRaisesRegex(AssertionError, 'historical bytes'):
                history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])

    def test_known_parent_missing_binding_or_archive_fails_closed(self):
        binding = self.root / history.BINDING
        binding.unlink()
        with self.assertRaises(FileNotFoundError):
            history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])
        binding.write_bytes(history.binding_bytes())
        (self.root / history.PARENT['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])

    def test_aliases_cannot_replace_named_binding_archive_or_evidence(self):
        aliases = (history.BINDING, history.PARENT['path'], next(iter(history.RECORDS)),
                   next(iter(history.LOGS)))
        for name in aliases:
            with self.subTest(name=name), patch.object(Path, 'is_symlink',
                    lambda path: path == self.root / name):
                with self.assertRaisesRegex(AssertionError, 'path changed'):
                    if name in (history.BINDING, history.PARENT['path']):
                        history.archived_source(self.root, history.SOURCE, history.PARENT['sha256'])
                    else:
                        history.assert_preserved_evidence(self.root)

    def test_live_bytes_are_not_an_archive_or_current_acceptance_authority(self):
        live = self.root / history.SOURCE
        live.write_bytes(b'# changed live supervisor\n')
        self.assertIsNotNone(history.archived_source(self.root, history.SOURCE, history.PARENT['sha256']))
        self.assertIsNone(history.archived_source(self.root, history.SOURCE,
                                                 hashlib.sha256(live.read_bytes()).hexdigest()))
        binding = json.loads(history.binding_bytes())
        self.assertIs(binding['currentSourceAcceptance'], False)
        self.assertIs(binding['nativeRerun'], False)

    def test_each_frozen_json_and_raw_log_refuses_changed_bytes(self):
        for name in (*history.RECORDS, *history.LOGS):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(name=name), self.assertRaisesRegex(AssertionError, 'historical bytes'):
                history.assert_preserved_evidence(self.root)
            path.write_bytes(original)

    def test_tracked_original_r160_evidence_remains_byte_exact(self):
        self.assertEqual(len(history.RECORDS), 3)
        self.assertEqual(len(history.LOGS), 3)
        history.assert_preserved_evidence(ROOT)
        self.assertIsNotNone(history.archived_source(ROOT, history.SOURCE, history.PARENT['sha256']))


if __name__ == '__main__':
    unittest.main()
