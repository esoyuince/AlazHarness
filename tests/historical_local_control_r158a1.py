"""Exact parent bytes for old receipts, never current R158 acceptance.

These four files changed in R158. Their archives were exported from the pinned
parent Git commit, not reconstructed from old expected hashes. Only an exact
name and historical digest pair can select an archive; every other generation
continues through the existing live-source or older-archive resolver.
"""

import hashlib
import json


BASE = "aba1e6af9242e7b4006bbd9f6244022549a52c61"
FOLDER = "evidence/p2-local-control-r158a1"
SOURCES = {
    "packages/claw-hermes/host_gate.py": {
        "path": FOLDER + "/base-packages__claw-hermes__host_gate.py.txt",
        "sha256": "c2f95f09fbaa0b39dea57aaf488cbfaac204b61771adffeb8ef182bd5c81b1ff",
        "size": 12593,
    },
    "packages/claw-hermes/host_gate_plugin.py": {
        "path": FOLDER + "/base-packages__claw-hermes__host_gate_plugin.py.txt",
        "sha256": "a472af8f7869114dd2217caea671c89132d3ca287efd545c164558877fb749b3",
        "size": 16236,
    },
    "packages/claw-hermes/hermes-runs.mjs": {
        "path": FOLDER + "/base-packages__claw-hermes__hermes-runs.mjs.txt",
        "sha256": "070d27ba51fc6f4594e378d1564e42c0255b5779811f4cd2e7a6e5df95c1d7d7",
        "size": 11670,
    },
    "packages/claw-hermes/host-gate-client.mjs": {
        "path": FOLDER + "/base-packages__claw-hermes__host-gate-client.mjs.txt",
        "sha256": "19a15618966532b8f2828292f0bff85825cb9f86295f9df452e193228675d7c0",
        "size": 8609,
    },
}


def archived_source(root, name, expected):
    item = SOURCES.get(name)
    if item is None or expected != item["sha256"]:
        return None

    record = json.loads(
        (root / FOLDER / "historical-source-bindings.json").read_text(encoding="utf-8")
    )
    if record != {
        "version": 1,
        "base": BASE,
        "scope": "historical_receipt_source_identity_only",
        "currentSourceAcceptance": False,
        "nativeRerun": False,
        "sources": SOURCES,
    }:
        raise AssertionError("unexpected pre-R158 historical source bindings")

    path = root / item["path"]
    payload = path.read_bytes()
    if len(payload) != item["size"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
        raise AssertionError("pre-R158 archived source bytes changed")
    return path
