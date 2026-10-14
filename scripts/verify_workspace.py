"""Offline preparation checks. Does not import or execute upstream agent code."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

EXPECTED = {
    "openclaw": ("vendor/openclaw", "https://github.com/esoyuince/openclaw.git", "https://github.com/openclaw/openclaw.git"),
    "hermes-agent": ("vendor/hermes-agent", "https://github.com/esoyuince/hermes-agent.git", "https://github.com/NousResearch/hermes-agent.git"),
}
REQUIRED = [
    "README.md", "AGENTS.md", "CURRENT-STATE.md", "sources.lock.json", ".gitmodules",
    "docs/MVP-v0.1.md", "docs/WORKSPACE-RULES.md", "docs/BACKLOG.md",
    "docs/COMPONENT-MAP.md", "docs/BOOTSTRAP.md", "docs/THIRD-PARTY.md",
    "docs/adr/0001-hybrid-first.md", "config/development.example.json",
    "scripts/restore_sources.py", "tests/test_workspace_helpers.py",
    "evidence/bootstrap/forks.json", "evidence/bootstrap/environment.json",
]


def confined_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Expected a nonempty POSIX relative path")
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or ".git" in p.parts or ":" in relative:
        raise ValueError("Unsafe workspace path")
    candidate = (root / relative).resolve()
    if candidate == root.resolve() or not candidate.is_relative_to(root.resolve()):
        raise ValueError("Path escapes workspace")
    return candidate


def parse_gitlink(text: str) -> str | None:
    lines = text.splitlines()
    if len(lines) != 1:
        return None
    m = re.fullmatch(r"160000 ([0-9a-f]{40}) 0\t.+", lines[0])
    return m.group(1) if m else None


def git(cwd: Path, *args: str, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout, shell=False,
    )
    if check and result.returncode:
        raise RuntimeError(f"git {args[0]} failed ({result.returncode}): {result.stderr[:800]}")
    return result


def inspect(root: Path, deep: bool = False) -> dict:
    rows: list[dict] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        rows.append({"check": name, "passed": bool(ok), "detail": detail})

    try:
        top = Path(git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
        record("root.is_independent_git_repository", top == root.resolve())
        for relative in REQUIRED:
            record("file." + relative, confined_path(root, relative).is_file())
        manifest = json.loads((root / "sources.lock.json").read_text(encoding="utf-8-sig"))
        repos = manifest.get("repositories", [])
        names = [r.get("name") for r in repos]
        record("manifest.schema", manifest.get("schema_version") == 1)
        record("manifest.exact_sources", len(repos) == 2 and set(names) == set(EXPECTED))
        forks = json.loads((root / "evidence/bootstrap/forks.json").read_text(encoding="utf-8-sig"))
        by_name = {r["full_name"]: r for r in forks["repositories"]}
        for source in repos:
            name = source["name"]
            if name not in EXPECTED:
                record("unexpected_source", False, str(name))
                continue
            relative, origin, upstream = EXPECTED[name]
            repo = confined_path(root, relative)
            prefix = name + "."
            record(prefix + "path", source["path"] == relative)
            head = git(repo, "rev-parse", "HEAD").stdout.strip()
            record(prefix + "head_matches_lock", head == source["commit"], head)
            record(prefix + "origin", git(repo, "remote", "get-url", "origin").stdout.strip() == origin)
            record(prefix + "upstream", git(repo, "remote", "get-url", "upstream").stdout.strip() == upstream)
            record(prefix + "lock_remotes", source["origin"] == origin and source["upstream"] == upstream)
            link = parse_gitlink(git(root, "ls-files", "--stage", "--", relative).stdout)
            record(prefix + "gitlink_matches_lock", link == head)
            url = git(root, "config", "--file", ".gitmodules", "--get", f"submodule.{source.get('submodule_name', name)}.url").stdout.strip()
            record(prefix + "gitmodules_url", url == origin)
            dirty = git(repo, "status", "--porcelain", "--untracked-files=normal").stdout
            record(prefix + "worktree_clean", not dirty.strip(), dirty[:1000])
            missing = git(repo, "ls-files", "--deleted").stdout
            record(prefix + "tracked_worktree_files_present", not missing.strip(), missing[:500])
            nested = git(repo, "submodule", "status", "--recursive").stdout
            record(prefix + "nested_submodules_pinned", not any(x.startswith(("-", "+", "U")) for x in nested.splitlines()), nested[:500])
            fork = by_name.get("esoyuince/" + name, {})
            parent_name = upstream.removeprefix("https://github.com/").removesuffix(".git")
            record(prefix + "fork_parent_receipt", fork.get("fork") is True and fork.get("parent", {}).get("full_name") == parent_name)
            for relative_file, expected_hash in source["file_sha256"].items():
                file = confined_path(repo, relative_file)
                actual = hashlib.sha256(file.read_bytes()).hexdigest()
                record(prefix + "sha256." + relative_file, actual == expected_hash)
            if deep:
                fsck = git(repo, "fsck", "--connectivity-only", "--no-reflogs", check=False, timeout=180)
                record(prefix + "git_object_connectivity", fsck.returncode == 0, (fsck.stdout + fsck.stderr)[-1500:])
        ignored = ["runtime/probe.txt", "artifacts/probe.txt", "scratch/probe.txt", ".env", ".env.local", "config/private.key"]
        for relative in ignored:
            result = git(root, "check-ignore", "--no-index", "--quiet", "--", relative, check=False)
            record("ignore." + relative, result.returncode == 0)
        example = json.loads((root / "config/development.example.json").read_text(encoding="utf-8"))
        record("config.explicitly_non_runtime", example["status"] == "DESIGN_EXAMPLE_NOT_LOADED_BY_A_RUNTIME")
        record("config.no_automatic_agent_or_spend", example["mode"] == "mock" and example["autonomy_enabled"] is False and example["scheduler_enabled"] is False and example["real_model_budget_usd"] == 0)
        tracked = git(root, "ls-files", "-z").stdout.split("\0")
        tracked = [p for p in tracked if p]
        record("root.has_staged_or_tracked_content", len(tracked) > 0)
        forbidden = [p for p in tracked if p.startswith(("runtime/", "artifacts/", "scratch/")) or p == ".env" or p.endswith((".key", ".pem"))]
        record("root.no_tracked_runtime_or_secret_filenames", not forbidden, ", ".join(forbidden))
        secret_hits = []
        patterns = [re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")]
        for relative in tracked:
            path = confined_path(root, relative)
            if not path.is_file() or path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if any(p.search(text) for p in patterns):
                secret_hits.append(relative)
        record("root.limited_secret_pattern_scan", not secret_hits, ", ".join(secret_hits))
        whitespace = git(root, "diff", "--cached", "--check", check=False)
        record("root.staged_whitespace", whitespace.returncode == 0, whitespace.stdout[:1000])
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        record("verification_exception", False, str(error))
    failed = sum(not row["passed"] for row in rows)
    return {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "scope": "workspace_preparation_only", "result": "PASS" if rows and not failed else "FAIL",
        "checks": len(rows), "passed": len(rows) - failed, "failed": failed,
        "product_runtime_tested": False, "real_model_called": False,
        "secret_scan_scope": "tracked root text <=1MB; private-key headers and GitHub token patterns only; not a complete secret audit",
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--deep", action="store_true", help="Also check local Git object connectivity")
    parser.add_argument("--report", help="Optional report path relative to evidence/")
    args = parser.parse_args()
    root = args.root.resolve()
    result = inspect(root, args.deep)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        destination = confined_path(root, "evidence/" + args.report)
        if not destination.is_relative_to((root / "evidence").resolve()):
            parser.error("Report must remain under evidence/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
