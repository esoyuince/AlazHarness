# Integration workflow

Main holds reviewed development increments. It does not imply M1, M2, production
readiness or permission to launch autonomous work. Releases are separate decisions.

Start from live status.md plus git status/log/remote refs. Do not work on the old
dirty root tree as though it were the current main. Use a clean worktree under
scratch/worktrees, retain unrelated work, and keep one writer per implementation.

Use a focused feature branch from current main. Run the complete standard suite,
source/provenance gates and the feature's separately scoped native tests. Review
evidence against exact code hashes. Commit only selected files and check same-SHA
CI after push. Once the increment is accepted, use fast-forward where possible;
never squash away evidence links or force-push to solve divergence. Reconcile a
diverged main explicitly before merging. No branch/worktree deletion is implicit.

Update status.md with actual merge/CI result and exact next action. Retain prior
logs under docs/history. The root convenience status copy must match only after
checking for concurrent edits. Native tests are distinct from default server CI.
