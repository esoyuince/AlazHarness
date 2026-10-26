# AlazHarness - status

## R156A1 - IN PROGRESS: fixed supervised native finite work

Base/main: 4823ebbca5f039aee1e9a4a209e40a48c015044a.
Branch: alaz/m1-finite-product-r156a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-finite-product-r156a1.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Prior accepted laboratory installation: /opt/alaz-r154a1 in AlazHarness-D3B-P71C.
Entry baseline: evidence/m1-finite-product-r156a1/baseline.json.

### Confirmed entry

R155A1 was published at the base above after exact-SHA alaz/local-ci success.
Live local/origin/remote main and the R155 feature remain at that SHA and clean.
The original root remains at 58b210ac9d400b84b028a2b57dcf1a4a396f089e;
its 33 existing changed/untracked file bytes match R155's final record.
Native d151673 and the R154 worktree remain clean. Original root status is not
overwritten. The R155 status is preserved in docs/status-history/r156a1-parent.md.

R155 accepted a fresh same-image seed epoch 1, original projected readiness
epoch 2 and normal supervisor stop/finish. It did not accept finite work,
API/service admission, a real broker exchange, real model calls, full D3B,
M1 or production.

### Current scope and contracts

Implement a separate fixed finite product operation using the original
supervisor, projection, retained native owner and prepared consumer.
The existing readiness operation and its readiness-only receipt stay exact.
Both operations must share the original one-child attempt ownership; no second
child may be appended after readiness and the old epoch-1 handoff must not be
represented as an updated epoch-2 handoff.

First acceptance targets: one normal bounded native task, exact-identity replay
and a new task identity, then one source-defined terminal application error,
within one original consumer/owner lifecycle. Use original replay/publication/
drain/retirement/physical-close contracts. Uncertain effects keep original
ownership; no automatic retry, forced close, lease release or cleanup.
Real external model/provider calls remain zero for this P1 slice. Scripted model
responses, if used, must be recorded separately and do not establish real-model
acceptance. P2 provider work requires an explicit selected model and budget.

### Active work and verification

- Native finite API/admission/publication/replay signatures: source review IN PROGRESS.
- Supervisor and fixed entry connection: source review IN PROGRESS.
- Acceptance design: source review IN PROGRESS.
- Implementation, focused tests and new native acceptance: NOT RUN at entry.
- New installation/kernel/root application: NOT RUN at entry.
- Commit/push/exact-SHA CI for R156: NOT RUN.

The source snapshots are evidence for implementation, not execution authority.
No original installed receipt or accepted native source is rewritten to force
new code through an old inventory. Any changed runtime source needs its own
qualified candidate and independent verification before new native acceptance.

### Next step

Read the exact current retained launcher, prepared consumer, finite API and
original native runner/authority sources. Reuse their actual call sequence,
then implement and independently review the fixed finite path and its tests.
P1 remains IN PROGRESS. P2-P5, full D3B, M1 and production remain OPEN.

Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
Prior report: [R155A1](docs/M1-SEED-READINESS-R155A1.md).

### Work log

- R155 publication and latest exact-SHA CI were checked against live refs.
- Protected original files and native/source worktrees passed entry comparison.
- Isolated R156 worktree created from accepted main; three source reviews split.
