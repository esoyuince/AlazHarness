# AlazHarness - status

## R158A1 - DONE: local control and read-only request recovery

P1 remains DONE. P2 is IN PROGRESS. P3-P5, full D3B, M1 and production are OPEN.
This packet implements the thin local control client and request-to-run locator;
native daily service start/close and real-model acceptance are NOT RUN.

Active branch: alaz/p2-local-control-r158a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\p2-local-control-r158a1.
Base main: aba1e6af9242e7b4006bbd9f6244022549a52c61.
Reviewed native source (unchanged): d1516731308de8e87130dc68124e69aad35d6911.

### Implemented

- HostGateLedger.observe plus authenticated GET /alaz/host/v1/requests/{request_id}:
  read-only state/replay snapshot, existing scope/key/fingerprint/epoch/inventory
  checks, no issue/consume, native pruning/status repair or execution readiness.
- HostGateClient.observeRequest: strict response/identity/flag validation.
- LocalControlClient and scripts/alaz_local.mjs: task/request/status/watch/result/
  usage/cancel over existing clients. Execution boundary and provider broker are
  mandatory for submission. No raw-start fallback, new queue or result store.
- Watch interruption only stops observation. Cancel sends once and observes
  separately; malformed successful stop ACK preserves possible acceptance.
- start/close return unsupported. Native run usage is not verified physical-call
  accounting; absent cost remains unknown. Null-generation queued cancellation
  stays terminal_unverified/unresolved under the existing strict classifier.
- Local control source/tests, exact historical source archives and provenance
  tests, report, roadmap and a concrete R159 service entry plan.

### Validation and reviewed scope

New Linux tests: 25 SQLite/HTTP handler + 31 CLI/HTTP fixture, 56/56 PASS.
Earlier ledger 36 and host-client 17 regressions PASS.
Initial primary Windows request: 70010158-83e7-4f2f-ae8e-bb0508f43794, terminal exit 0:
109 run, 104 passed, 5 skipped, 0 failures/errors, 27.248 seconds.
Four skips are unavailable aiohttp in that Python; one is POSIX SIGINT. All
five passed in Linux. Nine primary source hashes matched before/after the suite.
checks/windows-focused.json and .txt preserve the exact combined-source run.

Independent request/lifecycle/final-source-docs reviews PASS. Source compatibility:
old host lock rejects two d151 files; execution 5/5, retained 756/756 and finite
755/755 primary file hashes match. Command secret-source exists natively but is
missing from both product manifests. Existing locks and native source unchanged.

Initial staged static/discovery gate before the CI correction: PASS, 6662 files
checked, 4032 tests discovered, 119.567 seconds, exit 0. This did not execute tests.
The corrected staged gate, exact-commit CI and main publication are recorded in
the final journal below.

### Exact-commit CI correction

Initial commit cd596387f9f4fc03f02eeaf540e24a921792820e ran 4032 tests in CI:
FAILED, 17 failure records, 10 skips, 263.358 seconds; status 57253341117.
Main was not advanced. Raw log/metadata and summary remain in checks/ci-first-attempt*.
Sixteen failure records concerned historical source identities; one timeout
fixture assumed a GET reaches the peer before a whole-observation deadline.

Archived the four changed existing product files exactly from parent aba1e6a.
Only an exact historical path/digest pair selects its fixed, hash-checked archive;
current/unknown generations still use live bytes, and corrupted archives fail.
The 11 receipt modules and expected outcomes remain unchanged. One existing
helper delegates to the new resolver; six focused provenance tests were added.
The timeout fixture retains 40 ms, explicit execution_timeout and no-stop checks.
No product source, native pin or runtime changed in this correction.

First primary correction: 118 run, 114 pass, 3 failures, 1 skip; three loops
advanced and exposed the fourth old source, host-gate-client.mjs. Preserved in
checks/windows-ci-repair-001.*. Final primary request:
9c010158-5840-4aa2-bc23-4318f539ce58, terminal exit 0, 118 run, 117 passed,
1 POSIX skip, 0 failures/errors, 22.299 seconds; checks/windows-ci-repair-002.*.
All final checked source hashes matched before/after. Independent archive and
fixture source review PASS: ci-repair-review.json. Corrected commit CI remains
a required publication gate; source review and historical receipts are not
new native service/model acceptance.

### Publication handoff

This tracked status is finalized before its containing commit. Exact commit,
feature push, latest required alaz/local-ci, ordinary main fast-forward/push,
post-main CI and final protected-state checks are recorded in:

C:\Antigravity\AlazHarness\scratch\worktrees\p2-local-control-r158a1\scratch\r158a1-publication\final-publication.json

If that final journal is missing or not PASS, finish publication before R159.
Verify it against live Git and the latest required status. Git publication does
not deploy a service. No native runtime/provider attempt or unknown native effect
exists for R158; the R156 installation and receipt remain untouched.
Original root33 user changes and R154-R157/native protected trees are preserved.

### Exact next work

R159: explicitly qualify a borrowed loopback transport on the SAME native
runner/authority/three-store owner. Preserve the default P1 listener-free path.
Bind a reviewed route subset; make ready/draining observation/control explicit;
retain active/unknown work ownership until terminal, retire transport/handlers,
then native runtime/API, drain/detach, stores and original leases.
Review the HTTP-only metrics writer, update native/host compatibility together,
build a fresh P2 source/Node/Python closure, and qualify daily start/close.
Real model task follows selected route/model and visible call/token/cost budget.

Report: docs/P2-LOCAL-CONTROL-R158A1.md.
Next plan: docs/P2-BORROWED-SERVICE-R159A1-PLAN.md.
Roadmap: docs/PRODUCT-ROADMAP.md.
Evidence: evidence/p2-local-control-r158a1/.
Prior status: docs/status-history/r158a1-parent.md; initial R158 snapshot beside it.

### Work log

- Verified R157 final journal/live Git/required CI and protected root33; read rules,
  MVP and active plans, then created isolated R158 from accepted main.
- Read pinned clients/native service/stop sources; recorded exact listener and
  source-lock barriers without changing their guards.
- Implemented and independently reviewed read-only request recovery and local CLI.
- Preserved at-most-once handoff, observer/stop separation, unknown usage and
  native result authority; fixed malformed stop-ACK ambiguity.
- New Linux tests 56/56 PASS; primary final-source 109/104/5 PASS.
- Updated report/roadmap and exact R159 boundary; staged whitespace and static
  checks passed. Final commit/CI/main publication is handed off to the journal.

- First exact-commit CI failed and its artifacts were retained; main stayed at
  aba1e6a. Added four exact parent source archives without changing old results.
- Fixed the scheduling assumption in the watch-timeout fixture. Primary final
  correction suite 118/117/1 passed; source/provenance review PASS. New exact-commit
  CI and ordinary publication must complete before the R159 handoff.
