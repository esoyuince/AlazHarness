#!/usr/bin/env python3
"""Characterize pinned Hermes execution middleware, not a production security gate.

Uses the actual upstream module bytes. Only its plugin registry and the terminal
provider/tool callback are fixtures. No Gateway, LLM, network, or installer runs.
Supply the already pinned vendor/hermes-agent/hermes_cli/middleware.py explicitly.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import types
from typing import Iterator

SOURCE_COMMIT = "eb75627faf532fa6ffbdae59a0d14b0b385fc780"
SOURCE_PATH = "hermes_cli/middleware.py"
SOURCE_GIT_BLOB = "753b6643ab2c6b2d7cfc38d1e65043286ceb0080"
SOURCE_SHA256 = "3745ad211f365554a3c070083dc39d3ff9b6cdc93965f13d8796918433ec2328"
MODULE_NAME = "_alaz_pinned_middleware_boundary_probe"


def verified_source(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular, explicitly selected upstream source file")
    if path.stat().st_size > 131072:
        raise ValueError("Source exceeds the bounded probe input")
    data = path.read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if git_blob != SOURCE_GIT_BLOB or hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Pinned source byte mismatch; no unverified code was executed")
    return data


class FixtureManager:
    """Only the registry API touched by the actual execution-chain function."""

    def __init__(self) -> None:
        self._middleware: dict[str, list] = {}
        self.failures: list[str] = []

    def _report_hook_failure(self, kind, callback, kwargs, error, *, surface):
        # Do not record arguments, request content, or exception messages.
        self.failures.append(type(error).__name__)


@contextmanager
def loaded_source(data: bytes, path: Path) -> Iterator[tuple[types.ModuleType, FixtureManager]]:
    """Execute exact checked source with a fixture registry, then remove all stubs."""
    names = ("hermes_cli", "hermes_cli.plugins", MODULE_NAME)
    if any(name in sys.modules for name in names):
        raise RuntimeError("Use a fresh standalone process; refuse an existing Hermes context")
    manager = FixtureManager()
    package = types.ModuleType("hermes_cli")
    package.__path__ = []
    registry = types.ModuleType("hermes_cli.plugins")
    registry._delivery_manager = lambda: manager
    package.plugins = registry
    module = types.ModuleType(MODULE_NAME)
    module.__file__ = str(path)
    for name, value in zip(names, (package, registry, module)):
        sys.modules[name] = value
    try:
        # Compile the already-verified bytes, not a second potentially changed read.
        exec(compile(data, str(path), "exec"), module.__dict__)
        yield module, manager
    finally:
        for name in reversed(names):
            sys.modules.pop(name, None)


CASES = (
    "no_middleware",
    "permission_error_before_next",
    "return_without_next",
    "error_after_success",
    "next_called_twice",
    "downstream_error",
    "wrong_callback_signature",
)


def observe(module: types.ModuleType, manager: FixtureManager, kind: str, case: str) -> dict:
    terminal_calls = 0
    accepted_result = {"fixture_result": "completed"}
    denied_result = {"fixture_result": "refused"}

    def terminal(payload):
        nonlocal terminal_calls
        terminal_calls += 1
        if case == "downstream_error":
            raise OSError("fixture downstream error")
        return accepted_result

    def callback(**kwargs):
        if case == "permission_error_before_next":
            raise PermissionError("fixture budget or authorization rejection")
        if case == "return_without_next":
            return denied_result
        result = kwargs["next_call"]()
        if case == "error_after_success":
            raise RuntimeError("fixture middleware post-call error")
        if case == "next_called_twice":
            return kwargs["next_call"]()
        return result

    def wrong_signature(required_missing_argument):
        raise AssertionError("This incorrectly declared callback must not be entered")

    manager.failures.clear()
    manager._middleware.clear()
    manager._middleware[kind] = [] if case == "no_middleware" else [
        wrong_signature if case == "wrong_callback_signature" else callback
    ]
    returned = None
    escaped = None
    try:
        if kind == "llm_execution":
            returned = module.run_llm_execution_middleware({"fixture_request": True}, terminal)
        else:
            returned = module.run_tool_execution_middleware("fixture_tool", {"fixture_argument": True}, terminal)
    except Exception as error:
        escaped = type(error).__name__

    channel = "exception" if escaped else "refused" if returned is denied_result else "completed" if returned is accepted_result else "other"
    actual = {
        "terminal_calls": terminal_calls,
        "reported_callback_failures": list(manager.failures),
        "escaped_exception": escaped,
        "result_channel": channel,
    }
    expected = {
        "terminal_calls": 0 if case == "return_without_next" else 1,
        "reported_callback_failures": {
            "permission_error_before_next": ["PermissionError"],
            "error_after_success": ["RuntimeError"],
            "next_called_twice": ["RuntimeError"],
            "wrong_callback_signature": ["TypeError"],
        }.get(case, []),
        "escaped_exception": "OSError" if case == "downstream_error" else None,
        "result_channel": "exception" if case == "downstream_error" else "refused" if case == "return_without_next" else "completed",
    }
    return {
        "kind": kind,
        "case": case,
        "observed": actual,
        "expected_characterization": expected,
        "matches_characterization": actual == expected,
        "demonstrates_fail_open_exception": case in ("permission_error_before_next", "wrong_callback_signature") and terminal_calls == 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_path = args.source_file.absolute()
    output = args.output.absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir():
        raise ValueError("Select an absent output file in an existing directory")
    started = time.monotonic()
    data = verified_source(source_path)
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with loaded_source(data, source_path) as (module, manager):
        cases = [observe(module, manager, kind, case) for kind in ("llm_execution", "tool_execution") for case in CASES]
    unchanged = source_path.read_bytes() == data and hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == script_hash
    matched = sum(case["matches_characterization"] for case in cases)
    success = unchanged and matched == len(cases) == 14
    report = {
        "schema_version": 1,
        "result": "CHARACTERIZATION_CONFIRMED" if success else "FAIL",
        "scope": "actual pinned Hermes middleware functions; fixture registry and terminal counters only",
        "source_commit": SOURCE_COMMIT,
        "source_path": SOURCE_PATH,
        "source_git_blob": SOURCE_GIT_BLOB,
        "source_sha256": SOURCE_SHA256,
        "source_bytes": len(data),
        "probe_sha256": script_hash,
        "observations": len(cases),
        "matching_observations": matched,
        "mismatches": len(cases) - matched,
        "source_and_probe_unchanged": unchanged,
        "findings": {
            "pre_next_permission_error_is_veto": False,
            "return_without_next_suppresses_fixture_terminal": True,
            "refusal_response_compatible_with_native_callers": "NOT TESTED",
            "production_host_gate_implemented": False,
            "strict_budget_enforcement_accepted": False,
        },
        "environment": {"system": platform.system(), "python": platform.python_version()},
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "native_gateway_started": False,
        "real_provider_calls": 0,
        "agent_tool_calls": 0,
        "network_requests": 0,
        "dependencies_installed": False,
        "cases": cases,
    }
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("result", "observations", "matching_observations", "mismatches", "source_and_probe_unchanged", "findings")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
