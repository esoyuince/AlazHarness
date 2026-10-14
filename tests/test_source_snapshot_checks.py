"""Unit tests for the bootstrap verifier helpers; not harness product tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_snapshot", ROOT / "scripts/verify-source-snapshot.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RemoteChecks(unittest.TestCase):
    def test_https_remote(self):
        self.assertEqual(MODULE.repository_slug("https://github.com/esoyuince/openclaw.git"), "esoyuince/openclaw")

    def test_https_without_suffix(self):
        self.assertEqual(MODULE.repository_slug("https://github.com/NousResearch/hermes-agent"), "NousResearch/hermes-agent")

    def test_ssh_remote(self):
        self.assertEqual(MODULE.repository_slug("git@github.com:esoyuince/hermes-agent.git"), "esoyuince/hermes-agent")

    def test_credentials_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.repository_slug("https://token@github.com/a/b.git")

    def test_foreign_host_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.repository_slug("https://github.com.example.org/a/b.git")

    def test_query_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.repository_slug("https://github.com/a/b.git?token=example")

    def test_extra_path_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.repository_slug("https://github.com/a/b/tree/main")

    def test_absent_repo_fails_closed(self):
        scratch = ROOT / "scratch"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-check-", dir=scratch) as tmp:
            result = MODULE.verify_repo(Path(tmp), "openclaw", MODULE.EXPECTED["openclaw"])
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
