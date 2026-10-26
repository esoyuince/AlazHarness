# AlazHarness - status

## R155A1 - NATIVE/STATIC PASS: same-image seed/readiness; exact-commit publication gate

Base main: 27eb7571211ba0b685d7893d149438d612f6e2cd.
Branch: alaz/m1-seed-readiness-r155a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-seed-readiness-r155a1.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Installed runtime: e03f7fd4e47fea6a58b749564ab350aeb4237a26 at /opt/alaz-r154a1.
Dedicated lab: AlazHarness-D3B-P71C.
Installation receipt: 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2.

### Completed runtime acceptance

same-image001 PASS, terminal exit 0. Request e2a42e11-d56e-4bc9-9f72-bc28d2c76155
was applied once and completed; no operation remains pending.
The original supervisor owned one fresh 64 MiB ext4 image through
ordinary-UID native seed (epoch 1), original projected readiness (epoch 2),
original stop and normal finish.

- Seed PID 11/start ticks 3076, UID 23001/GID 23003, supplementary groups [].
  Original six startup checks; profile [1792,12], databases
  [1792,26], [1792,30], [1792,31]. Handoff captured under held profile lease,
  three database connections physically closed and normal lease release.
  Verification 1188 ms + native 21936 ms = 23125 ms.
- Readiness PID 16/start ticks 5507, epoch 2 and all six original checks;
  PROJECTED_RETAINED_OWNER_CLOSED / SUPERVISED_PROJECTED_OWNER_CLOSED.
  Same image, same original supervisor, original worker mount namespace
  mnt:[4026532224], /dev/loop0. No rewritten profile/database identities.
- Original stop UNMOUNTED worker PID 10. Normal finish CLOSED:
  owned users gone, loop attachment gone, volume fence removed after cleanup,
  image lease released last. All owned children terminal.
  Host mount namespace and mount table unchanged. No retained original volumes.
- Controller PID 7/start ticks 2465 and Windows carrier PID 83144 exited 0.
  Whole communication completed within its 240-second deadline.
- Task/model calls 0; metadata socket fixture only. Service, API admission,
  finite work, real broker exchange, full D3B, M1 and production NOT ACCEPTED.
  No automatic retry or post-failure cleanup. The unmounted image and evidence
  remain; normal closure does not mean all R155 paths were deleted.

### Source and focused verification

ordinary007 PASS established the task-free native producer first:
epoch 1, ordinary UID, three physical database closes, capture under held
lease, normal lease release and async shutdown, 27227 ms total.
It is separate ordinary-rootfs evidence, not the same-image acceptance.

Primary Windows focused-windows002 PASS, exit 0: 120 cases processed,
113 passed and 7 Linux-only skips. Includes a real finite Windows Python
three-pipe child. Owned fixtures otherwise; no WSL/native application/root/model
acceptance comes from this suite. Source hashes are in its result.json.
The corrected Windows metadata comparison preserves before/after change
checks within each observation view and all cross-view comparable identities.
The source-specific original IPv6 capability probe remains BLOCKED before bind;
the actual socket must close and the original capability result must be false.

Earlier ordinary001..006 and focused-windows001 failures remain in evidence,
including unresolved finite diagnostics where the old wrapper lost a reason.
No later result retroactively changes those failures. ordinary006's exact
UTF-16LE startup-error bytes are preserved in stdout-capture.json and ignored
scratch; no binary is submitted as a tracked text artifact.

### Frozen same-image input

Intent SHA: 2b1d4f7eae5ac979a8f3449e230e8be8156d1335bae41b07a91f55b0ad4836a5.
Manifest SHA: 2b97bdf8ddd2f3b776311aba16cffce50918c4446989f544aa2668c80238f793.
Raw ZIP SHA: 7242482096d7a5f80677b94207b36dc66c30bfe244b5fcc2b93a0d35e9225268.
Ordinary proof-set SHA: cb79324e986166d606fcdf345da01a6dcff73c55a477e3db7ea27a6512b70abf.
Execution-start SHA: 22b370c932bec332ae64363e046581e953504d423a8e1693900ab0089b08a39f.
Saved result SHA: 6fb481f97a70d949f3ab080102e1511d8d44d09349aa74906f2219611f10b010.

### Publication and remaining product work

Implementation, selected verification, ordinary native proof, same-image
readiness/ordered-close acceptance and repository static gate PASS.
Static command: python -B scripts/ci_check.py, exit 0, 161142 ms.
6464 repository files, 2 gitlinks and 10 selected components checked;
3865 unittest cases discovered. Discovery is not full-suite execution.
See evidence/m1-seed-readiness-r155a1/static001/result.json.

Protected-state comparison PASS: original root HEAD/branch/status and all 33
existing changed/untracked file hashes/sizes unchanged; native d151673 and R154
worktrees clean. Main/local origin/live remote remained clean at base 27eb757.
This status was not mirrored over the independently changed original root copy.

The scoped evidence attributes preserve exact captured/frozen bytes across
checkouts. All 11 current source/test hashes match accepted focused002.
Final closure metadata is checked after the static scan.

This tracked snapshot is written before its own final commit. Publication
requires exact pushed-SHA alaz/local-ci success, then ordinary fast-forward main.
The post-commit receipts in this worktree's scratch/r155a1-publication/ record
the actual final SHA, accepted-ci-before-main.json and final-publication.json.
Live Git refs and that exact SHA's GitHub status are authoritative; no CI success
or push is inferred from this pre-commit snapshot. Read them before continuing.

P1 remains IN PROGRESS. Next product step: connect bounded real native work
through the same accepted product entry, then accept normal/error, replay/new
work and ordered close on one installation. P2-P5 and M1/prod remain OPEN.
Real-provider work needs a selected model and explicit budget.

Evidence: [R155A1](evidence/m1-seed-readiness-r155a1/).
Report: [R155A1](docs/M1-SEED-READINESS-R155A1.md).
Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
Prior report: [R154A1](docs/M1-INSTALL-READINESS-R154A1.md).
History: parent, initial, source-checkpoint, ordinary-investigation,
transport-checkpoint, pre-root, root-pending, runtime-passed and pre-publication
snapshots in docs/status-history/.

### Work log

- Entry and reviewed source snapshots retained.
- Ordinary failures diagnosed against exact source; no receipt/identity bypass.
- ordinary007 accepted the original task-free lifecycle under ordinary UID.
- Windows focused tests corrected and passed; independent source review complete.
- same-image001 inputs frozen and independently read back before one application.
- same-image001 completed PASS: seed epoch 1, projected readiness epoch 2,
  original stop/finish and unchanged host mounts; all owned children terminal.
- Report and roadmap updated; protected-state comparison PASS.
- Exact evidence bytes preserved; explicit source/test/evidence staging verified.
- Repository static gate PASS; final exact-SHA CI and main publication are
  recorded afterward in the publication journal without a self-referential commit.
