# Reviewed development baseline publication — 21 October 2026

User approved publishing `alaz/d3b-joint-21oct-4c21` and advancing main only
following successful exact-SHA `alaz/local-ci`. This is not a release, a
production deployment, or completion of D3B, M1 or M2.

## Reviewed range

Old remote main: `b8ff44ff105965ba3f6f9fa9559ad96f2c084815`.
Qualified starting head: `b133627028b1b52e9feb90d358e091595d6f3580`.
61 commits; 1227 changed paths, of which 985 are evidence files. The range
includes previously qualified host admission, budgets, reporting, isolated
reads, manual Dream review/evaluation and guarded broker integration. It is
not presented as only the last IPC fix. `pending-commits.txt` and
`pending-files.txt` in `evidence/publication-21oct-a37c/` record the full range.

Pattern-based publication review scanned 1367 reachable new blob versions
and 61 commit objects, 20698582 bytes, including historical versions no longer
at the tip. Private-path inventory covers all 61 commit trees (1605 names).
No configured credential pattern hit, forbidden private path, unreviewed
binary/large blob or unsupported file mode was found. This is bounded
pattern-based review, not a guarantee every possible secret is absent.
No vendor gitlink target or root license change is in the pending range.
Ten copied upstream components were reproduced against their pinned vendor
source bytes, including retained licenses: PASS.

The 317 source/config/test files are identical to the full joint regression
snapshot: Windows 2125 total / 2120 passed / 5 skipped, and Linux selected
175 passed / 0 skipped, including those five native budget cases. Local
static inspection passed. These results are scoped and do not replace the
GitHub status for the actual pushed SHA. No runtime/source/test changes are
introduced by this publication preparation.

## Write discipline and continuation

First push only the reviewed branch. Check GitHub `alaz/local-ci` on the exact
published SHA. Then re-read remote main and require a history-preserving
fast-forward. Never force, squash, drop commits or delete old branches and
worktrees. Root worktree has unrelated user work and remains untouched.
No system identities, production services, CI permissions or model settings
are changed. IPC v2 stays fail-closed. A clean worktree from updated main is
the baseline for subsequent two-host-UID launcher/projection development.

At preparation time push and main update have NOT RUN. Their actual receipts
and final status must be recorded separately, not inferred from this plan.
