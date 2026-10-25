# R154A1 work log

## Baseline and continuation

Parent accepted main: 16830bd56e8c9b6a23e1bd60435ffb4b04793a9d.
Original R153 status is preserved in r154a1-parent.md. The initial, reviewed
pre-install and dispatched-install checkpoints remain in sibling history files.
r154a1-prepublication.md preserves the closure before static acceptance.
Work is isolated on alaz/m1-install-readiness-r154a1. Original root33 file bytes,
native d151673 and accepted main remained unchanged at the closure custody check.

## Implementation and validation

Added the exact-candidate source installer, ordinary read-only modes, fixed lab
operator and their focused suites. Independent source reviews bind final hashes.
Operator uncertainty propagation and explicit permissions were corrected before
root application; original attempt001 is SUPERSEDED_NOT_APPLIED.
Installer Linux: 36 PASS; Windows: 16 PASS / 20 Linux-only SKIP.
Operator Linux: 11 PASS; Windows: 10 PASS / 1 Linux-only SKIP.
All raw test exits were 0. The first Windows wrapper's CRLF skip-count error
(exit 1) and corrected summary are both preserved without replaying tests.

## Actual installation and verification

Ordinary environment and real-candidate preflight passed. Final attempt002
installed the unchanged R153 source and exact dependencies at /opt/alaz-r154a1
in P71C, exit 0. Installer and carrier were observed terminal. A separate ordinary
--verify-installed passed without writes: 834 package files and 1,162 dependencies.
Receipt: 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2.
No readiness, retained seed, native task, model, image, mount or cgroup was run.

## Closure qualification

A raw Windows checkout/archive comparison failed solely for LICENSE CRLF
conversion. The completed diagnostic verified all 77 immutable HEAD Git blobs
against the manifest; the conversion and failed assertion remain as evidence.
No code, archive or attributes were changed for this qualification.
Final pre-publication protected-state check passed for root33, native and main.

The first staged static invocation reached its 120-second tool deadline. A later
read-only inspection confirmed all 57 selected files staged, no unstaged diff,
and no matching original wrapper/scanner process. No PASS was inferred.
Standalone static002 completed in 198.379 seconds, exit 0: 6,348 files, two
gitlinks and 3,745 discovered tests. Discovery is not test execution.
static001-timeout.json and static002.json preserve these distinct outcomes.
Only final closure metadata follows that complete staged scan; changed-file
syntax/JSON/pattern/whitespace checks precede commit.

## Publication and continuation

Exact final-SHA alaz/local-ci gates ordinary fast-forward publication to main.
Final live refs and CI are recorded in the ignored scratch publication journal
and user-facing closure; no remote numeric test count is inferred.
P1 installation sub-gate is accepted; P1 overall remains IN PROGRESS.
Next: original native retained seed on the same supervised image, then supervised
readiness/ordered close and normal/error, replay/new-work, finite task acceptance.
