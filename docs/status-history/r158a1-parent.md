# AlazHarness - status

## R157A1 - DONE: native readiness and joint P1 acceptance

P1 is DONE for the same unchanged R156 installation. R156 finite and R157
readiness-only native acceptances use separate fresh image/supervisor lifecycles.
P2-P5, complete D3B, M1 and production acceptance remain OPEN.

Active branch: alaz/m1-installed-readiness-r157a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-installed-readiness-r157a1.
QA base main: cdc974728e69f590838b82421cd244e36554a74f.
Installed runtime: e641a5000810efb2a453ae847f689b422f7d41a7 at /opt/alaz-r156a1.
Native: d1516731308de8e87130dc68124e69aad35d6911.
Receipt: a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845.

### Completed and accepted

- Reviewed source-only renderer, four explicit QA sources and 22 focused tests.
- Original candidate/receipt and all six R156 ordinary proof files revalidated.
- One fresh image001: seed epoch 1, readiness epoch 2, six startup checks,
  original stop/finish, all owned children terminal, host mount state unchanged.
- Native request 53c00157-2ce9-4eea-9b9f-61beef0377f2 terminal exit 0/PASS.
  Intent 995225a4262b807450226ed252ed4bdc5a9e9cb8f40313ef6acd37aa26bbd72a.
  Result 5bd9879c71d3c2ee2e45762899892f51195068937cf1d30108d5c32127f33426.
- Joint P1 evidence/source verification PASS; both installation objects equal;
  81 packaged harness Git blobs unchanged from e641 and exact manifest bytes.
- Runtime and original receipt unchanged; no reinstall or repeated finite work.
  New real model/provider calls zero. No unresolved R157 native effect exists.

The initial joint verifier rejected LICENSE's Windows CRLF checkout bytes.
Committed LF blob and installed manifest always matched. Final verifier compares
exact Git blob bytes, records CRLF-only checkout differences and requires clean
packaged paths. First source-only diagnostic is preserved; native was not rerun.

### Validation and limits

Linux preparation unit tests: 22/22 PASS, 5.217 s.
Windows focused tests: 22 run, 21 passed, 1 platform skip, 0 failures/errors,
35.689 s, exit 0. Actual candidate preparation and host freeze: exit 0.
Native acceptance: exit 0; separate independent source/frozen/native/P1 reviews PASS.
Joint evidence and packaged-source verifier: exit 0/PASS.
Staged offline static gate: PASS, 6641 tracked files, 3976 tests discovered (not executed by this gate), exit 0.

Seed and readiness child stderr each contain 1265 bytes of SQLite DELETE-mode
warnings; outer stderr is empty. No SQLite upgrade occurred. Finite model
factory/computation/close remains scripted fixture; real broker, service,
general runtime admission, restart replay and product CLI are not accepted here.

### Git / CI publication handoff

This tracked status snapshot is finalized before its containing commit is made.
The exact resulting commit, push outcomes, latest required alaz/local-ci status,
normal main fast-forward and final protected-state verification are recorded in:

C:\Antigravity\AlazHarness\scratch\worktrees\m1-installed-readiness-r157a1\scratch\r157a1-publication\final-publication.json

Before resuming, verify that journal against live Git and the latest required
status for the actual commit. If no final journal exists, publication remains
unverified: finish that step before beginning P2. Main was cdc9747 at entry.
No force push/rebase/reset is part of this work. Git publication is not a
deployment or a service start. Root33 user changes are separately protected;
the original root status copy is not overwritten.

### Exact next work

P2 / R158A1: read the existing HostGateClient/HermesRunsClient and native
listener/stop sources, map the real control flow, then implement the thin daily
start/task/watch/result/usage/cancel/close path on the canonical native owner.
Resolve selected-model source/secret closure and explicit budget before a real
provider acceptance. No new task queue/result authority is needed.

Report: [R157](docs/M1-INSTALLED-READINESS-R157A1.md).
Joint evidence: [P1](evidence/m1-installed-readiness-r157a1/p1-acceptance.json).
Next packet: [P2/R158](docs/P2-LOCAL-PRODUCT-R158A1-PLAN.md).
Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
Detailed prior status: docs/status-history/r157a1-parent.md.
This task's initial and pre-native snapshots are retained beside it.

### Work log

- Read status/rules and verified live R156/main/CI against the final R156 journal.
- Preserved root33 and protected worktrees; created isolated R157 at cdc9747.
- Prepared/reviewed fixed QA, tested guards, verified actual candidate and froze intent.
- Executed one native image001, observed terminal PASS and original normal close.
- Independently reviewed all raw captures, identities and same-installation P1 scope.
- Verified 81 exact packaged Git blobs; corrected only source-verifier CRLF handling.
- Updated P1 roadmap/report and precise P2 entry packet; publication uses final journal.
