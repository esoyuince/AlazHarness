"""R162 source custody and fixed R159 receipt preservation, not runtime proof."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import historical_service_receiver_r162a1 as history

ROOT = Path(__file__).resolve().parents[1]


class ServiceReceiverHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in (history.RUNTIME, history.BINDING, history.PARENT['path']):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())

    def test_exact_parent_and_current_generation_are_separate(self):
        parent = history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])
        self.assertEqual(parent, self.root / history.PARENT['path'])
        self.assertEqual(hashlib.sha256(parent.read_bytes()).hexdigest(), history.PARENT['sha256'])
        history.assert_current_source(self.root)
        self.assertIsNone(history.archived_source(self.root, history.RUNTIME, history.CURRENT_SHA))
        self.assertNotEqual(history.CURRENT_SHA, history.PARENT['sha256'])

    def test_unlisted_current_unknown_and_nonexact_types_do_not_read_archive(self):
        class Text(str):
            pass
        candidates = [('other.py', history.PARENT['sha256']),
            (history.RUNTIME, history.CURRENT_SHA), (history.RUNTIME, 'f' * 64),
            (Text(history.RUNTIME), history.PARENT['sha256']),
            (history.RUNTIME, Text(history.PARENT['sha256']))]
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected archive read')):
            for name, expected in candidates:
                with self.subTest(name=name, expected=expected):
                    self.assertIsNone(history.archived_source(self.root, name, expected))

    def test_changed_binding_cannot_relabel_redirect_or_requalify_parent(self):
        original = json.loads(history.binding_bytes())
        changes = [('base', '0' * 40), ('nativeRerun', True),
            ('currentSourceAcceptance', True), ('priorReceiptHashes', {}),
            ('sources', {history.RUNTIME: dict(history.PARENT, path=history.RUNTIME)})]
        for key, value in changes:
            modified = copy.deepcopy(original)
            modified[key] = value
            (self.root / history.BINDING).write_text(json.dumps(modified, indent=2, sort_keys=True) + '\n')
            with self.subTest(key=key), self.assertRaisesRegex(AssertionError, 'source binding'):
                history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])

    def test_binding_byte_format_is_fixed_and_archive_bounds_are_exact(self):
        path = self.root / history.BINDING
        path.write_bytes(history.binding_bytes() + b' ')
        with self.assertRaisesRegex(AssertionError, 'source binding'):
            history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])
        path.write_bytes(history.binding_bytes())
        archive = self.root / history.PARENT['path']
        original = archive.read_bytes()
        for raw in (original[:-1], original + b'\n', b'changed source\n'):
            archive.write_bytes(raw)
            with self.subTest(size=len(raw)), self.assertRaisesRegex(AssertionError, 'archived source bytes'):
                history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])

    def test_archive_path_alias_is_refused(self):
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(AssertionError, 'archive path changed'):
                history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])

    def test_parent_archive_cannot_mask_changed_current_runtime(self):
        (self.root / history.RUNTIME).write_bytes(b'# changed current runtime\n')
        self.assertIsNotNone(history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256']))
        with self.assertRaisesRegex(AssertionError, 'current R162 service runtime bytes'):
            history.assert_current_source(self.root)

    def test_current_runtime_cannot_mask_changed_parent_archive(self):
        (self.root / history.PARENT['path']).write_bytes(b'# changed parent runtime\n')
        history.assert_current_source(self.root)
        with self.assertRaisesRegex(AssertionError, 'archived source bytes'):
            history.archived_source(self.root, history.RUNTIME, history.PARENT['sha256'])

    def test_original_r159_receipts_remain_byte_exact(self):
        self.assertEqual(len(history.PRIOR_RECEIPTS), 9)
        history.assert_prior_receipts(ROOT)

    def test_changed_prior_receipt_is_not_accepted_as_original(self):
        for name in history.PRIOR_RECEIPTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        name = next(iter(history.PRIOR_RECEIPTS))
        path = self.root / name
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(AssertionError, 'original R159 receipt bytes'):
            history.assert_prior_receipts(self.root)


if __name__ == '__main__':
    unittest.main()
