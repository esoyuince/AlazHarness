"""Tests for our preparation helpers; not upstream or agent runtime tests."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_workspace import confined_path, parse_gitlink


class PathTests(unittest.TestCase):
    def test_valid_path(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.assertEqual(confined_path(root, "docs/test.md"), (root / "docs/test.md").resolve())

    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), "../outside")

    def test_rejects_absolute(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), "/outside")

    def test_rejects_drive(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), "C:/outside")

    def test_rejects_backslash(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), "docs\\file")

    def test_rejects_git_internals(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), ".git/config")

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), "")

    def test_rejects_root(self):
        with self.assertRaises(ValueError):
            confined_path(Path.cwd(), ".")


class GitlinkTests(unittest.TestCase):
    def test_accepts_gitlink(self):
        self.assertEqual(parse_gitlink("160000 " + "a" * 40 + " 0\tvendor/openclaw\n"), "a" * 40)

    def test_rejects_normal_file(self):
        self.assertIsNone(parse_gitlink("100644 " + "a" * 40 + " 0\tfile\n"))

    def test_rejects_multiple_entries(self):
        self.assertIsNone(parse_gitlink(("160000 " + "a" * 40 + " 0\tvendor/x\n") * 2))

    def test_rejects_conflict_stage(self):
        self.assertIsNone(parse_gitlink("160000 " + "a" * 40 + " 1\tvendor/x\n"))

    def test_rejects_empty(self):
        self.assertIsNone(parse_gitlink(""))


if __name__ == "__main__":
    unittest.main()
