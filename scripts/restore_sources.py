"""Recreate pinned submodules. Prints a plan by default; --apply allows network/writes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from verify_workspace import EXPECTED, confined_path, git, parse_gitlink


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = json.loads((root / "sources.lock.json").read_text(encoding="utf-8"))["repositories"]
    if len(sources) != 2 or {s["name"] for s in sources} != set(EXPECTED):
        raise ValueError("Unexpected source set")
    for source in sources:
        name = source["name"]
        relative, origin, upstream = EXPECTED[name]
        if (source["path"], source["origin"], source["upstream"]) != (relative, origin, upstream):
            raise ValueError("Source identity mismatch")
        if parse_gitlink(git(root, "ls-files", "--stage", "--", relative).stdout) != source["commit"]:
            raise ValueError("Manifest disagrees with parent gitlink")
        repo = confined_path(root, relative)
        declared = git(root, "config", "--file", ".gitmodules", "--get", f"submodule.{source.get('submodule_name', name)}.url").stdout.strip()
        if declared != origin:
            raise ValueError("Unexpected submodule URL")
        existing = (repo / ".git").exists()
        if existing and git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip():
            raise RuntimeError(f"Refusing dirty source: {name}")
        print(f"{name}: initialize {relative} at {source['commit']} from {origin}")
        if args.apply:
            git(root, "submodule", "update", "--init", "--depth=1", "--", relative, timeout=600)
            remote = git(repo, "remote").stdout.splitlines()
            if "upstream" not in remote:
                git(repo, "remote", "add", "upstream", upstream)
            elif git(repo, "remote", "get-url", "upstream").stdout.strip() != upstream:
                raise RuntimeError("Unexpected upstream remote; no replacement performed")
            if git(repo, "rev-parse", "HEAD").stdout.strip() != source["commit"]:
                raise RuntimeError("Restored commit mismatch")
    print("Source restore complete; no dependencies or agent started." if args.apply else "PLAN ONLY. Re-run with --apply to clone/check out pinned sources. No package installation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
