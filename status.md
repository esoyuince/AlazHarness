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
- Nine source/test files, report, roadmap and a concrete R159 service entry plan.

### Validation and reviewed scope

New Linux tests: 25 SQLite/HTTP handler + 31 CLI/HTTP fixture, 56/56 PASS.
Earlier ledger 36 and host-client 17 regressions PASS.
Primary Windows request: 70010158-83e7-4f2f-ae8e-bb0508f43794, terminal exit 0:
109 run, 104 passed, 5 skipped, 0 failures/errors, 27.248 seconds.
Four skips are unavailable aiohttp in that Python; one is POSIX SIGINT. All
five passed in Linux. Nine primary source hashes matched before/after the suite.
checks/windows-focused.json and .txt preserve the exact combined-source run.

Independent request/lifecycle/final-source-docs reviews PASS. Source compatibility:
old host lock rejects two d151 files; execution 5/5, retained 756/756 and finite
755/755 primary file hashes match. Command secret-source exists natively but is
missing from both product manifests. Existing locks and native source unchanged.

Staged static/discovery gate: PASS, 6662 files checked, 4032 tests discovered,
119.567 seconds, exit 0. Discovery does not execute the full suite.
Exact-commit CI and main publication are recorded in the final journal below.

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
