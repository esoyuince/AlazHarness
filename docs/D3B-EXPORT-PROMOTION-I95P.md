# D3B primary development-line exporter integration — I95P

Scope: integrate an independently completed source-export correction into the
clean primary DEVELOPMENT branch. This is not main publication, an R91F storage
repair, a new runtime feature, or a new Linux confinement acceptance.

Active branch: `alaz/d3b-principal-launch-21oct`.
Worktree: `scratch/worktrees/d3b-principal-launch-21oct`.
Before: `916f5290981f5cc4775c930fb4674d046cb3cc67`.
Integrated: `80d85488b02b3b8cb4023f41d666b043b356e9a6`.
Original code commit: `bfaa32b3d0d5df86178b5926343db5cf9b1fe8e2`.
Method: fast-forward, no squash/cherry-pick/rewrite/deletion. Two original
commits and all original before/after evidence are retained.

## Why this is a separate useful step

The R91F replay-storage branch remains at85f7470 with a genuine missing-source
receipt error and a previously blocked collector correction. That operation
has NOT been retried, re-expressed, delegated, patched, or replaced here. No
storage proof, acceptance assertion, original result, timeout or skipped-test
rule has been changed. We do not run the same triage again or label that branch
qualified. Its passing subsets are not mixed into this delivery.

The independent source-export branch was already complete at80d8548. Its entire
two-commit diff and tests were reviewed before integration. It changes one line
in scripts/qa/export_principal_source.py to ensure every Git object query names
the original object rather than following local replacement references. Four
real temporary-repository tests cover blob, whole-commit, custom-prefix and
empty-environment replacement cases. Only inert fixture comments are exported;
they are not installed or executed. All package runtime modules are unchanged.

The new primary test count is2273 = previous primary2269 +4 exporter tests.
The blocked storage branch independently has2295 = base2269 +26 storage tests.
These are DIFFERENT branch scopes, not26 tests deleted to make a failing suite
pass. No tests have been removed from either branch. R91F is NOT merged here.

## Verification sequence

The source branch's345-file manifest was matched to live bytes BEFORE merge.
After fast-forward, the primary source was matched to that manifest again.
A fresh complete standard Windows suite was executed on the primary tree;
its own stdout/log, result object and before/after hashes are recorded under
`evidence/d3b-export-promotion-i95p/`. Runtime tests and the local static checker
are serialized; the static checker does not run concurrently with this suite.
No result is declared before its command reaches a terminal receipt.

Source inspection confirms343 of344 old files unchanged, one helper modified,
one test file added. No old source was removed. Native G84E evidence remains
unchanged historical evidence; its verifier is part of the standard suite but
that does not mean a Linux namespace test was rerun. No WSL distribution, root
operation, model, network provider, production data or system configuration is
used. Main remainscc7ceba and no branch is pushed in this task.

## Exact continuation boundaries

Primary development-line integration is this task's deliverable. The next
runtime gate still requires a fixed trusted Hermes Gateway entrypoint and a
qualified persistent lifecycle for BOTH state.db and runs_idempotency.db.
The current Gateway private workspace is ephemeral, not durable state. Legacy
IPC v2 activation remains closed. A real Gateway/provider dispatch is not
inferred from broker pings or source packaging.

R91F can only be promoted after its blocked correction boundary is legitimately
resolved and a fresh whole-branch result passes; its85f7470 checkpoint and failure
records remain the explicit reference. This integration grants no permission
to bypass that block or to publish R91F. No repeated readiness/timeout triage is
needed merely to restate the known error.

## Terminal primary-branch regression

Fresh full Windows standard suite: **2273 total,2268 PASS,5 SKIP,0 failures,
0 errors**, command exit0,408.974 test seconds. Counts come from the unittest
result object; tests and their internal deadlines are unchanged. All345 frozen
package/script/test/config file hashes match before, after and final review.
The four replacement-ref regressions and existing host-report CLI test passed
inside this full run; no separate passing subset is added to the total.

This does not supersede the failing2295 R91F STORAGE run, which used another
branch and another scope. Its85f7470 HEAD, status, original collector, failing
receipt test, original receipt and blocked-operation record match the initial
snapshot. G82C e1bc877 and local maincc7ceba also remain unchanged and clean.
No blocked operation was retried, delegated or routed through a different tool.

The final local static checker runs separately after the terminal full suite.
Its exact output is static-final.txt and summary.json records the terminal exit.
It is not GitHub CI or a new native runtime test. This follow-up checkpoint
contains status/documentation/evidence only; code stays at originalbfaa32b,
with the complete source tested at80d8548. Read Git HEAD for the final local
integration handoff. Nothing is pushed and main is not merged.
