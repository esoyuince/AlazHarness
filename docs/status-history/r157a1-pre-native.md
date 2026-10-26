# AlazHarness - status

## R157A1 - IN PROGRESS: separate readiness on accepted current installation

Base main: cdc974728e69f590838b82421cd244e36554a74f.
Branch: alaz/m1-installed-readiness-r157a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-installed-readiness-r157a1.
Installed runtime source: e641a5000810efb2a453ae847f689b422f7d41a7.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Existing installation: /opt/alaz-r156a1 in AlazHarness-D3B-P71C.
Original receipt: a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845.

### Confirmed entry state

R156 final cdc9747 is published on main and the feature branch. Live exact-SHA
alaz/local-ci SUCCESS was rechecked before this work. Original R156 publication
proof records 3954 full-suite tests: 3948 passed, 6 skipped, no failures/errors;
static 6584 files PASS. Both R156/main worktrees are clean. Original root33
changed/untracked file bytes and all protected source worktrees are unchanged.

R156 ordinary001 and image001 finite normal/replay/new/error acceptance remain
accepted. The current installed runtime is unchanged. R155 readiness belongs
to an older installation and does not satisfy the current-installation gate.

### Current scope

Prepare a separate fixed readiness QA operation bound to the existing R156
installation, original receipt and accepted ordinary proof. Use a fresh image,
new R157 execution paths, native task-free seed epoch 1, one readiness child
epoch 2, and original normal stop/finish. Preserve all six startup checks,
physical connection closure, process/capture identities and unknown custody.

No new installer or runtime-code change is planned. The accepted finite attempt
will not be repeated, and no second child will be added to its supervisor.
Real provider/model calls remain outside this scope.

### Work in progress / next step

Source-only preparation and independent lifecycle/scope reviews passed.
Actual original candidate archive and manifest were revalidated; all four
generated QA files match the independently reviewed final hashes. Original
installation binding/receipt and all six ordinary proof files remain byte-exact.
Focused tests: Linux 22/22 PASS; Windows 22 run, 21 passed, one platform skip.
The actual three-source input is frozen at image001. No R157 native operation
has been submitted; native acceptance NOT RUN and no unknown effect is pending.

One planned native request: 53c00157-2ce9-4eea-9b9f-61beef0377f2.
Intent: 995225a4262b807450226ed252ed4bdc5a9e9cb8f40313ef6acd37aa26bbd72a.
Execution binding: 11fa244a48ff250115264428bb39d0f5dd5364c0fa5ca05e2ca8d05baf76e577.
Next: final frozen-input review, original host apply with this exact intent,
then poll the same request to a terminal outcome. No retry or cleanup on unknown.

P1 remains IN PROGRESS pending this acceptance and its joint source binding to
R156 finite proof. P2-P5, complete M1 and production acceptance remain OPEN.

Report: [R157A1](docs/M1-INSTALLED-READINESS-R157A1.md).
Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
Baseline: [entry](evidence/m1-installed-readiness-r157a1/baseline.json).
Prior runtime: [R156A1](docs/M1-FINITE-PRODUCT-R156A1.md).
Prior status remains in docs/status-history/r157a1-parent.md.

### Work log

- Read current status/rules and verified live R156/main/CI against final journal.
- Preserved original root33 and protected source states; created isolated R157 branch.
- Began source-only preparation and independent reviews; native operation NOT RUN.
- Actual preparation and frozen host input passed; one native image001 attempt pending.
