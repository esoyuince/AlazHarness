#!/usr/bin/env python3
"""Read-only verification of AlazHarness source checkouts. No dependency/model calls.

Usage: python scripts/verify-source-snapshot.py [--root PATH] [--output PATH]
An output path must be inside root/evidence. Existing reports are not overwritten.
This checks repository preparation, not product behavior or sandbox enforcement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

EXPECTED = {
    "openclaw": ("esoyuince/openclaw", "openclaw/openclaw"),
    "hermes-agent": ("esoyuince/hermes-agent", "NousResearch/hermes-agent"),
}


def repository_slug(url: str) -> str:
    """Accept credential-free official GitHub HTTPS or git SSH remote URLs."""
    value = url.strip()
    if value.startswith("git@github.com:"):
        path = value[len("git@github.com:"):]
    else:
        parsed = urlparse(value)
        if (parsed.scheme != "https" or parsed.hostname != "github.com"
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port is not None):
            raise ValueError("Not a credential-free GitHub remote URL")
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
        raise ValueError("Invalid owner/repository path")
    return path


def git(repo: Path, *args: str, timeout: int = 45) -> str:
    env = dict(os.environ)
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                            encoding="utf-8", errors="replace", env=env, timeout=timeout)
    if result.returncode:
        raise RuntimeError("git " + args[0] + " failed (exit " + str(result.returncode) + ")")
    return result.stdout.strip()


def verify_repo(root: Path, name: str, expected: tuple[str, str]) -> dict[str, Any]:
    repo = root / "vendor" / name
    out: dict[str, Any] = {"name": name, "path": "vendor/" + name, "checks": [], "errors": []}
    def check(label: str, ok: bool) -> None:
        out["checks"].append({"name": label, "passed": bool(ok)})
        if not ok:
            out["errors"].append(label)
    try:
        if not (repo / ".git").exists():
            raise RuntimeError("Missing independent repository/gitlink checkout")
        top = Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
        check("independent_repository_root", top == repo.resolve())
        before = git(repo, "rev-parse", "--verify", "HEAD")
        check("valid_head", bool(re.fullmatch(r"[0-9a-f]{40}", before)))
        out["commit"] = before
        out["commit_time"] = git(repo, "show", "-s", "--format=%cI", "HEAD")
        out["shallow"] = git(repo, "rev-parse", "--is-shallow-repository") == "true"
        out["branch"] = git(repo, "branch", "--show-current") or "(detached)"
        for remote, slug in zip(("origin", "upstream"), expected):
            actual = repository_slug(git(repo, "remote", "get-url", remote))
            out[remote] = actual
            check(remote + "_matches", actual.lower() == slug.lower())
        status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        check("clean_worktree", not status)
        check("no_deleted_tracked_files", not git(repo, "ls-files", "--deleted"))
        files = git(repo, "ls-files", "-z").split("\0")
        tracked = [p for p in files if p]
        out["tracked_files"] = len(tracked)
        check("nonempty_source_tree", len(tracked) > 0)
        missing = [p for p in tracked if not (repo / p).exists() and not (repo / p).is_symlink()]
        out["missing_tracked_count"] = len(missing)
        check("all_tracked_paths_present", not missing)
        license_path = repo / "LICENSE"
        data = license_path.read_bytes()
        out["license_sha256"] = hashlib.sha256(data).hexdigest()
        check("mit_license_text_present", b"MIT License" in data)
        tree = git(repo, "ls-files", "--stage")
        nested = [line.split("\t", 1)[-1] for line in tree.splitlines() if line.startswith("160000 ")]
        out["nested_gitlinks"] = nested
        check("no_unverified_nested_gitlinks", not nested)
        git(repo, "fsck", "--connectivity-only", "--no-reflogs", timeout=120)
        check("git_object_connectivity", True)
        after = git(repo, "rev-parse", "--verify", "HEAD")
        check("head_unchanged_during_check", before == after)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        out["errors"].append(type(exc).__name__ + ": " + str(exc))
    out["status"] = "PASS" if out["checks"] and not out["errors"] else "FAIL"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "read_only_source_preparation_not_product_acceptance",
        "repositories": [verify_repo(root, name, expected) for name, expected in EXPECTED.items()],
        "limits": ["No build or dependency installation", "No model or paid API call",
                   "No hybrid/autonomy acceptance", "Fork parent requires separate GitHub evidence",
                   "Root lock/gitlink consistency checked separately", "No LFS payload audit"],
    }
    report["status"] = "PASS" if all(r["status"] == "PASS" for r in report["repositories"]) else "FAIL"
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        path = (root / args.output).resolve()
        evidence = (root / "evidence").resolve()
        if not path.is_relative_to(evidence):
            parser.error("--output must be inside the workspace evidence directory")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    print(payload, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
