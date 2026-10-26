"""Provenance guards for the four exact pre-R158 source archives."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from historical_self_identity_r150a1 import saved_generation_hash, source_hash, source_path


ROOT = Path(__file__).resolve().parents[1]
FOLDER = Path("evidence/p2-local-control-r158a1")
OLD = {
    "packages/claw-hermes/host_gate.py": "c2f95f09fbaa0b39dea57aaf488cbfaac204b61771adffeb8ef182bd5c81b1ff",
    "packages/claw-hermes/host_gate_plugin.py": "a472af8f7869114dd2217caea671c89132d3ca287efd545c164558877fb749b3",
    "packages/claw-hermes/hermes-runs.mjs": "070d27ba51fc6f4594e378d1564e42c0255b5779811f4cd2e7a6e5df95c1d7d7",
    "packages/claw-hermes/host-gate-client.mjs": "19a15618966532b8f2828292f0bff85825cb9f86295f9df452e193228675d7c0",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HistoricalLocalControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / FOLDER
        self.folder.mkdir(parents=True)
        self.binding_path = self.folder / "historical-source-bindings.json"
        shutil.copyfile(ROOT / FOLDER / self.binding_path.name, self.binding_path)
        self.binding = json.loads(self.binding_path.read_text(encoding="utf-8"))
        for name, row in self.binding["sources"].items():
            shutil.copyfile(ROOT / row["path"], self.root / row["path"])
            live = self.root / name
            live.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, live)

    def test_known_parent_generations_use_exact_archived_bytes(self):
        for name, expected in OLD.items():
            with self.subTest(name=name):
                fixed = self.folder / ("base-" + name.replace("/", "__") + ".txt")
                self.assertNotEqual(digest(self.root / name), expected)
                self.assertEqual(source_path(self.root, name, expected), fixed)
                self.assertEqual(digest(fixed), expected)
                self.assertEqual(source_hash(self.root, name, expected), expected)
                self.assertEqual(saved_generation_hash(self.root, name, expected), expected)

    def test_current_and_unknown_generations_use_live_bytes_without_archive_access(self):
        shutil.rmtree(self.folder)
        for name, old_digest in OLD.items():
            live = self.root / name
            current = digest(live)
            self.assertNotEqual(current, old_digest)
            for expected in (current, "f" * 64):
                with self.subTest(name=name, expected=expected):
                    self.assertEqual(source_path(self.root, name, expected), live)
                    self.assertEqual(source_hash(self.root, name, expected), current)
                    self.assertIsNone(saved_generation_hash(self.root, name, expected))
                    if expected != current:
                        self.assertNotEqual(source_hash(self.root, name, expected), expected)

    def test_unlisted_name_cannot_borrow_a_known_digest(self):
        shutil.rmtree(self.folder)
        name = "packages/claw-hermes/unlisted.py"
        live = self.root / name
        live.write_bytes(b"unlisted live fixture\n")
        expected = OLD["packages/claw-hermes/host_gate.py"]
        self.assertEqual(source_path(self.root, name, expected), live)
        self.assertEqual(source_hash(self.root, name, expected), digest(live))
        self.assertNotEqual(source_hash(self.root, name, expected), expected)
        self.assertIsNone(saved_generation_hash(self.root, name, expected))

    def test_missing_or_unreadable_binding_fails_for_a_known_generation(self):
        name = "packages/claw-hermes/host_gate.py"
        expected = OLD[name]
        self.binding_path.unlink()
        with self.assertRaises(FileNotFoundError):
            source_path(self.root, name, expected)
        self.binding_path.write_text("{incomplete", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            source_path(self.root, name, expected)

    def test_altered_binding_identity_cannot_redirect_or_relabel_an_archive(self):
        name = "packages/claw-hermes/host_gate.py"
        mutations = []
        for field, value in (("base", "0" * 40), ("nativeRerun", True),
                             ("currentSourceAcceptance", True)):
            changed = copy.deepcopy(self.binding)
            changed[field] = value
            mutations.append((field, changed))
        for field, value in (("path", name), ("path", "../outside.py"),
                             ("sha256", digest(self.root / name)), ("size", 0)):
            changed = copy.deepcopy(self.binding)
            changed["sources"][name][field] = value
            mutations.append((field + "=" + str(value), changed))
        changed = copy.deepcopy(self.binding)
        changed["sources"].pop("packages/claw-hermes/hermes-runs.mjs")
        mutations.append(("source removed", changed))
        changed = copy.deepcopy(self.binding)
        changed["sources"]["packages/claw-hermes/extra.py"] = changed["sources"][name].copy()
        mutations.append(("source added", changed))
        for label, changed in mutations:
            with self.subTest(label=label):
                self.binding_path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(AssertionError, "historical source bindings"):
                    source_path(self.root, name, OLD[name])

    def test_missing_truncated_or_same_length_altered_archive_fails_closed(self):
        for name, expected in OLD.items():
            path = self.root / self.binding["sources"][name]["path"]
            original = path.read_bytes()
            with self.subTest(name=name, corruption="missing"):
                path.unlink()
                with self.assertRaises(FileNotFoundError):
                    source_path(self.root, name, expected)
            for label, changed in (("truncated", original[:-1]),
                                   ("same length", bytes([original[0] ^ 1]) + original[1:])):
                with self.subTest(name=name, corruption=label):
                    path.write_bytes(changed)
                    with self.assertRaisesRegex(AssertionError, "archived source bytes changed"):
                        source_path(self.root, name, expected)
            path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
