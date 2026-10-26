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

- Native finite API/admission/publication/replay signatures: source review PASS for the bounded API fixture; projected execution remains NOT RUN.
- Fixed supervisor/projection/finite runtime: IMPLEMENTED in this worktree; independent source review PASS.
- Owned local supervisor tests: PASS 59 (29 unchanged readiness + 30 finite); native/process/kernel boundaries are explicit doubles.
- Owned local builder/installer tests: PASS 64; real Git/archive/filesystem fixtures, no runtime installation.
- Windows current-source focused tests: PASS, 351 run / 319 passed / 32 platform skips, exit 0.
- Windows preparation tests: initial 23 run / one fixture portability error; corrected 23/23 PASS, exit 0. Initial evidence preserved.
- Full pre-candidate static/discovery gate: PASS, 6498 root files / 2 source gitlinks / 3952 discovered tests, exit 0 in 71.743 seconds; discovery is not full test execution.
- New installed/native finite acceptance: NOT RUN at this checkpoint.
- Acceptance preparation utility/templates: IMPLEMENTED and independently reviewed; actual candidate and receipt pins must come from the verified build/install.
- New installation/kernel/root application: NOT RUN at entry.
- Immutable source commit: e641a5000810efb2a453ae847f689b422f7d41a7, local only; final push/exact-SHA CI remain NOT RUN.
- New candidate: 838 source files (756 pinned native), archive SHA-256 3c829db65670756abd531d146aa72c0dc5b3773cd750fc87d26567763f3caef8.
- Actual installation binding/operator/transport and 20,031,648-byte bundle: PREPARED and reviewed; apply has not started at this checkpoint.

The source snapshots are evidence for implementation, not execution authority.
No original installed receipt or accepted native source is rewritten to force
new code through an old inventory. Any changed runtime source needs its own
qualified candidate and independent verification before new native acceptance.

### Next step

Apply the reviewed source-only installation once in AlazHarness-D3B-P71C at /opt/alaz-r156a1, using attempt r156a1-install001. Planned bridge request adc60156-54c2-4148-92bf-b1566275fd94. Poll that request; pending is not completion and unknown effects must not be replayed. Retrieve the actual canonical receipt only after verified terminal installation, then render its bound ordinary producer and finite acceptance bundle.
P1 remains IN PROGRESS. P2-P5, full D3B, M1 and production remain OPEN.

Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
Current report: [R156A1](docs/M1-FINITE-PRODUCT-R156A1.md).
Prior report: [R155A1](docs/M1-SEED-READINESS-R155A1.md).

### Work log

- R155 publication and latest exact-SHA CI were checked against live refs.
- Protected original files and native/source worktrees passed entry comparison.
- Isolated R156 worktree created from accepted main; three source reviews split.

- Eleven owned source/test files were applied with exact before/after hashes.
- Original readiness behavior and one-child ownership remain; finite work has a separate fixed entry and receipt.
- Independent review found and fixed unbounded async preparation and pending-task checks after lease release. Both now retain ownership on uncertainty.
- The scripted API path does not set native CLI/unattended finite policy flags; no such policy acceptance is claimed.
- No R156 installation, WSL/root execution, real provider call, commit or push has occurred at this checkpoint.

- Current Windows source passed 351 focused tests (319 pass, 32 platform skips; exit 0; 228.640 seconds).
- Preparation fixture's Linux path spelling was corrected for Windows without weakening the generated Linux validator. Corrected 23/23 passed in 15.171 seconds; initial one-error result retained separately.
- Native, installation and acceptance source reviews found no remaining source-contract blocker. Actual projected execution remains a separate unrun gate.
- Source checkpoint now includes fixed candidate preparation and receipt-bound generation; old R154/R155 sources and accepted installed tree remain unchanged.

- Pre-candidate full static/discovery passed: 6498 indexed root files, 2 source gitlinks, 3952 discovered tests; no errors. The discovered suite was not executed by this gate.
- Source checkpoint is qualified for immutable candidate construction; no R156 install or native acceptance has run yet.

- Immutable source e641a5000810efb2a453ae847f689b422f7d41a7 committed (41 owned files); all 17 source/test hashes matched their tested bytes. Original 33-file root inventory and protected worktrees rechecked unchanged.
- The source exporter was first invoked with isolated Python, which prevented its sibling ci_check import; it exited before candidate creation. Normal -B invocation then exported the candidate successfully. No installer or native execution occurred in that failed host-only invocation.
- Actual installation operator, transport and frozen intent were read and checked. Intent SHA-256 8f51dd3cd2a6ff051a294ca9583f74bc43f6a7f0b58fc515e6c5081563cbaaf0; bundle SHA-256 c47f073b9270e114166ee0e4cef8138cb50ebc90c6512a401e8f82c9c3cec340. No old installation or receipt is replaced.
