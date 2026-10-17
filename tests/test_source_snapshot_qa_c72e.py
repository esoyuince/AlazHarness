"""Independent exact-byte snapshot QA; synthetic temporary inputs, no native agent.
Existing source snapshot primitive is exercised, not a reimplemented reader.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'packages/claw-hermes'))
import isolated_read as ir


class SourceSnapshotIndependentQA(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.path = self.root/'source.txt'
        self.path.write_bytes(b'alpha\nbeta\n')

    def test_actual_raw_bytes_not_newline_normalized(self):
        data = 'Işık😀\r\nβ\n'.encode('utf-8')
        self.path.write_bytes(data)
        self.assertEqual(ir._snapshot_input(str(self.path)), data)

    def test_bom_and_undecodable_bytes_are_capture_not_text_claim(self):
        data = b'\xef\xbb\xbfA\xff\x00\r\n'
        self.path.write_bytes(data)
        self.assertEqual(ir._snapshot_input(str(self.path)), data)

    def test_empty_source_is_captured_not_absent(self):
        self.path.write_bytes(b'')
        self.assertEqual(ir._snapshot_input(str(self.path)), b'')

    def test_exact_bound_is_not_truncated(self):
        data = b'q'*65536; self.path.write_bytes(data)
        self.assertEqual(ir._snapshot_input(str(self.path)), data)

    def test_over_bound_rejected_before_open(self):
        self.path.write_bytes(b'q'*65537)
        with patch.object(ir.os, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_relative_input_rejected(self):
        with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input('source.txt')

    def test_other_extension_rejected_before_open(self):
        p = self.root/'source.json'; p.write_text('{}')
        with patch.object(ir.os, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(p))

    def test_directory_named_txt_rejected(self):
        p = self.root/'directory.txt'; p.mkdir()
        with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(p))

    def test_hardlinked_input_rejected(self):
        p = self.root/'alias.txt'; os.link(self.path, p)
        with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_symlink_ancestor_refused_without_traversing(self):
        original = Path.is_symlink
        def seen(p): return True if p == self.root else original(p)
        with patch.object(Path, 'is_symlink', seen):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_input_mutation_between_stat_and_open_refused(self):
        original = ir.os.open
        def opened(p, flags):
            self.path.write_bytes(b'changed-length\n')
            return original(p, flags)
        with patch.object(ir.os, 'open', opened):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_changed_inode_from_open_descriptor_refused(self):
        original = ir.os.fstat
        def changed(fd):
            s = original(fd)
            return SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino+1,
                                   st_size=s.st_size, st_mtime_ns=s.st_mtime_ns)
        with patch.object(ir.os, 'fstat', changed):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_in_place_change_during_read_refused(self):
        original = ir.os.fstat; calls = []
        def changed(fd):
            s = original(fd); calls.append(1)
            return SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino,
                                   st_size=s.st_size, st_mtime_ns=s.st_mtime_ns+(1 if len(calls)>1 else 0))
        with patch.object(ir.os, 'fstat', changed):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))

    def test_descriptor_closed_when_read_is_rejected(self):
        original = ir.os.fstat; fds = []
        def changed(fd):
            s = original(fd); fds.append(fd)
            return SimpleNamespace(st_dev=s.st_dev, st_ino=s.st_ino,
                                   st_size=s.st_size+1, st_mtime_ns=s.st_mtime_ns)
        with patch.object(ir.os, 'fstat', changed):
            with self.assertRaises(ir.ExecutionDenied): ir._snapshot_input(str(self.path))
        self.assertEqual(len(fds), 1)
        with self.assertRaises(OSError): original(fds[0])

    def test_source_content_not_changed_by_capture(self):
        before = self.path.read_bytes(); meta = self.path.stat()
        ir._snapshot_input(str(self.path))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, meta.st_mtime_ns)

    def test_returned_bytes_do_not_track_later_file_changes(self):
        old = ir._snapshot_input(str(self.path)); self.path.write_bytes(b'replaced\n')
        self.assertEqual(old, b'alpha\nbeta\n')
        self.assertNotEqual(hashlib.sha256(old).digest(), hashlib.sha256(self.path.read_bytes()).digest())

    def test_uppercase_txt_uses_same_byte_contract(self):
        p = self.root/'UPPER.TXT'; p.write_bytes(b'U\r\n')
        self.assertEqual(ir._snapshot_input(str(p)), b'U\r\n')

    def test_missing_source_not_created(self):
        p = self.root/'absent.txt'
        with self.assertRaises(OSError): ir._snapshot_input(str(p))
        self.assertFalse(p.exists())
