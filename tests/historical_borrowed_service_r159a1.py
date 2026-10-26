"""Exact parent bytes for old receipts, never current R159 acceptance.

These nine files changed in R159. Their archives were exported from the pinned
parent Git commit, not reconstructed from old expected hashes. Only an exact
name and historical digest pair can select an archive; every other generation
continues through the existing live-source or older-archive resolver.
"""

import hashlib
import json


BASE = "37620d5c14afee895b16e3441f7a7ed14b77e7d7"
FOLDER = "evidence/p2-borrowed-service-r159a1"
SOURCES = {
    "packages/claw-hermes/execution_boundary.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__execution_boundary.py.txt",
        "sha256": "be363cf01e46380e9cb1aabf719fddd18299fd98428a9784fe9457a6b032372b",
        "size": 21689
    },
    "packages/claw-hermes/gateway_consumer_admission.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_consumer_admission.py.txt",
        "sha256": "7f42c035f641c22f85b5c7fe04b5bd8011b1d529f61720ee88281722affd06da",
        "size": 3550
    },
    "packages/claw-hermes/gateway_consumer_api.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_consumer_api.py.txt",
        "sha256": "e686828344d4c554416348730a226cc586ffaa635d451ff55d3b1734c6ad7168",
        "size": 4905
    },
    "packages/claw-hermes/gateway_prepared_consumer.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_prepared_consumer.py.txt",
        "sha256": "d5ce29480570d140363deda7fe8740ad7ddb1f5e579d0befbd790ca68a0f5cc6",
        "size": 21021
    },
    "packages/claw-hermes/gateway_store_startup.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__gateway_store_startup.py.txt",
        "sha256": "fdf7d7d84fd7538f829568c7a38db1e4b9302b1fb5643620a5a0dc2a78b4b50b",
        "size": 15646
    },
    "packages/claw-hermes/host_gate.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__host_gate.py.txt",
        "sha256": "3d598cb6aa0bab7be87849ea8585b5123e8cfcf42a54593349966f34c340378d",
        "size": 18380
    },
    "packages/claw-hermes/host_gate_plugin.py": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__host_gate_plugin.py.txt",
        "sha256": "7170317c68bb1b8a896d87f667dfcde494b6b02625b877654af0fe7ed387bfc6",
        "size": 16758
    },
    "packages/claw-hermes/local-control.mjs": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__local-control.mjs.txt",
        "sha256": "2037499a06c7baf29f90e1dc54c55d2d8f73b99c4eb665f7f6bcbc8cceacaf49",
        "size": 11607
    },
    "packages/claw-hermes/run-recovery.mjs": {
        "path": "evidence/p2-borrowed-service-r159a1/base-packages__claw-hermes__run-recovery.mjs.txt",
        "sha256": "48f2a3743aac3eb9b6c293258895d22fcb36839c230b6ee15498692427bec191",
        "size": 2528
    }
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
        raise AssertionError("unexpected pre-R159 historical source bindings")

    path = root / item["path"]
    payload = path.read_bytes()
    if len(payload) != item["size"] or hashlib.sha256(payload).hexdigest() != item["sha256"]:
        raise AssertionError("pre-R159 archived source bytes changed")
    return path
