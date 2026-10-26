# AlazHarness - status

## R156A1 - IN PROGRESS: native/static PASS; exact-commit CI failure under investigation

Base main: 4823ebbca5f039aee1e9a4a209e40a48c015044a.
Branch: alaz/m1-finite-product-r156a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-finite-product-r156a1.
Immutable runtime source: e641a5000810efb2a453ae847f689b422f7d41a7.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Installed runtime: /opt/alaz-r156a1 in AlazHarness-D3B-P71C.
Installation receipt: a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845.
Prior R155 accepted status: docs/status-history/r156a1-parent.md.

### Completed implementation and installation

A separate fixed finite operation now uses the original RetainedVolumeSupervisor,
projection, retained NativeStoreStartup, prepared consumer, canonical API,
authority, physical worker, persistence, drain/retirement/detach and normal close.
The readiness operation remains separate; both share one original child-attempt
slot. No second child is appended to a completed or uncertain attempt.

The immutable e641a50 source candidate contains 838 source files, including
756 exact d151 native sources. r156a1-install001 copied and read back all
838 source + 1162 dependency files with the pinned Python and root-controlled
ancestry. Original canonical receipt was fetched as ordinary UID 23001 and
verified. Installation root device/inode: 2096/29702. Previous installation
/opt/alaz-r154a1 and protected source worktrees were not overwritten.

Installation request adc60156-54c2-4148-92bf-b1566275fd94 completed once,
exit 0, installer terminal observed. It was source-only installation.

### Completed actual native acceptance

ordinary001 PASS, exit 0. Request 42d90156-3554-483d-8b59-1e275173d836.
The exact new producer completed original task-free native startup and close:
six checks, owner CLOSED, consumer DETACHED, all three physical connections
closed, profile lease normally released, no outstanding tasks/threads.
Observed elapsed 13124 ms; producer total 12704 ms, native lifecycle 10906 ms.
Tasks/models/listeners zero. This is ordinary-rootfs proof, separate from image001.

image001 PASS, state SAME_IMAGE_SEED_FINITE_ACCEPTED, exit 0.
Request 2edf0156-c0e9-469f-840d-470d55c7c90b completed once; no effectful R156
operation remains pending or unknown. The original supervisor owned a new
64 MiB ext4 image through seed epoch 1 -> one fixed finite child epoch 2 ->
original stop/finish. Seed total 10069 ms; entire host operation observed
by the bridge in 43597 ms (not a standalone finite-computation measurement).

- Normal A: completed, bounded answer 50 checked against original saved result.
- Exact replay A: same admission ID and both corresponding result digests;
  computation count stays 1.
- New B: distinct admission, completed, bounded answer 7, computation count 2.
- Controlled application error C: third admission, native terminal failed;
  computation count 3 and full original normal close still completed.
- Original API tuple equals the saved result/usage fields. Tuple and saved dict
  have distinct envelope hashes; replay equality is checked within each envelope.
- Finite PID 16/start ticks 9977; wrapper, owner frame and original capture agree.
  All six startup checks passed. Child exited 0; observedAfterUnknown=false.
- Same three physical connections, registry refcounts 0, model fixture instances
  closed and retirement row changes 0. Original drain/detach/owner close and
  caller lease finish accepted.
- Worker PID 10 and token match MOUNTED -> UNMOUNTED. Original finish CLOSED:
  owned users gone, loop attachment gone, fence removed after cleanup,
  image lease released last. All owned children terminal; no retained original
  volumes. Host mount namespace/table unchanged.
- Metadata broker fixture stopped normally only after volume close.
  No automatic retry, forced detach, signalling or uncertain-state cleanup.
  The unmounted image and evidence remain.

### Explicit scope and diagnostics

Model factory/computation/close is an explicit scripted fixture; three fixture
invocations, zero real model/provider calls. Native API/authority/worker/store
and close are original implementations. Native profile event counts include
coroutine resumes, not distinct task counts.

Finite child stderr is 4513 bytes and is preserved. It includes native SQLite
DELETE-mode warnings, a nonfatal missing agent.secret_sources.command
registration diagnostic and the expected controlled model failure traceback.
This does not accept that secret-source integration or general provider readiness.

No general runtime admission/service, real broker exchange, CLI/unattended
policy, restart replay, full D3B, full P1, M1 or production acceptance is claimed.

### Verification and evidence

- Windows exact-current-source focused suite: PASS, 351 processed /
  319 passed / 32 platform skips, exit 0, 228.640 seconds.
- Windows preparation: initial one fixture portability error preserved;
  corrected 23/23 PASS, exit 0, 15.171 seconds. Product validator unchanged.
- Pre-candidate full static/discovery: PASS, 6498 root files, 2 gitlinks,
  3952 discovered tests, exit 0, 71.743 seconds.
- Final full static/discovery after generated sources/evidence: PASS,
  6564 root files / 2 gitlinks / 3952 discovered tests, exit 0, 65.479 seconds.
  Static discovery is not full discovered-suite execution.
- Independent source, concrete installation/acceptance binding and actual
  native evidence reviews preserve the fixture/native/provider distinction.
- Original root 33-file changed/untracked byte inventory and protected Git
  states rechecked unchanged before final publication. 24 current source/test/QA
  hashes match; all 81 candidate harness files retain their canonical Git bytes.
  Existing Windows LICENSE CRLF presentation is explicitly recorded; its exact
  canonical Git blob matches the installed candidate. Runtime bytes unchanged.

Report: [R156A1](docs/M1-FINITE-PRODUCT-R156A1.md).
Acceptance summary: [summary](evidence/m1-finite-product-r156a1/acceptance-summary.json).
Native evidence: [image001](evidence/m1-native-finite-r156a1/image001/result.json).
Ordinary evidence: [ordinary001](evidence/m1-native-finite-r156a1/ordinary001/result.json).
Installation: [receipt](evidence/m1-finite-product-r156a1/installation/installation-receipt.json).
Roadmap: [product roadmap](docs/PRODUCT-ROADMAP.md).
All earlier R156 checkpoints remain under docs/status-history/r156a1-*.md.

### Publication and exact next step

This tracked snapshot is written before its own final commit. Publication
requires exact pushed-SHA alaz/local-ci success, then ordinary fast-forward main.
The post-commit journal in this worktree's scratch/r156a1-publication/ records
the actual final SHA, accepted-ci-before-main.json and final-publication.json.
Live Git refs and that exact SHA's latest status are authoritative; no push
or CI success is inferred from this pre-commit snapshot. Read them on resume.
Final docs/evidence commit must preserve all candidate-selected runtime bytes
from e641a50; generated QA is outside the runtime source candidate.

P1 remains IN PROGRESS, with current-installation finite acceptance complete.
The next narrow P1 gate is the separate readiness/no-work operation on the same
838-source installation using a fresh image and original lifecycle. R155's
readiness PASS belongs to its older installation and is not silently reused.
Do not repeat the accepted R156 finite attempt or append another child to it.
No runtime-code change is needed for that remaining qualification.

P2 source work may proceed in parallel: daily local start/task/status/result/
usage/cancel/close; selected provider's necessary source/dependency coverage.
Real-provider acceptance needs P1 closure plus a chosen model and explicit
budget. P3 persistence/memory reuse, P4 fault/operation flows and P5 same-release
M1-01..M1-07/pilot remain OPEN.

### Work log

- Entry live refs and exact R155 CI checked; original root33 and native/source
  worktrees compared against prior final publication.
- Fixed finite supervisor, projection, strict work/result and native lifecycle
  implemented. Independent review fixed preparation deadline, pre-release task
  checks, exact three-connection identity and post-wait elapsed deadline.
- Windows focused and corrected preparation suites passed; first portability
  error retained. Pre-candidate static/discovery passed.
- 41 owned files frozen at e641a50; 17 source/test hashes matched tested bytes.
  Initial isolated-Python exporter import failure happened before output;
  ordinary -B invocation exported the complete candidate successfully.
- Actual install binding/operator/transport/bundle reviewed, installed once,
  exact original receipt read back, and seven bound QA sources generated.
- ordinary001 accepted the exact task-free producer; host prepare revalidated
  all six evidence files and froze image001's four-source bundle.
- image001 completed PASS with normal/replay/new/error and original normal close.
- Actual diagnostic output and remaining current-installation readiness gate
  recorded without broadening scope. Evidence and prior checkpoints retained.

- Final full static/discovery PASS: 6564 files / 2 gitlinks / 3952 tests discovered, exit 0 in 65.479 seconds. Final closure metadata is checked separately after this scan.
- Independent actual acceptance and original ownership reviews PASS; all ordinary proof rows are bound and the three native operation receipts are terminal exit 0.
- Exact pushed-SHA CI and normal main publication are recorded afterward in scratch/r156a1-publication/ without a self-referential tracked commit.

### Current publication interruption

Feature commit 0451203566f25459e48b13a2c96756597f9ed460 was pushed normally.
Its latest exact-SHA alaz/local-ci FAILED rc=1, status 57240625611,
created 2026-10-26T07:54:36Z. Main remains at accepted base 4823ebbca5f039aee1e9a4a209e40a48c015044a; no main merge/push was attempted.
Native installation/ordinary/finite acceptance remains PASS and no runtime operation is pending. Investigate the actual failed CI job/test, preserve its failure, fix only the demonstrated issue, validate and obtain a new exact-SHA success before main publication. Do not rerun the already accepted native finite attempt or change CI policy to bypass a test failure.

### CI failure diagnosed; narrow history-test correction in progress

Read-only CI log inspection bound the failure to exact SHA 0451203566f25459e48b13a2c96756597f9ed460.
Actual full suite: 3952 run, 3944 passed, 2 failures, 6 skips, 245.919 seconds.
Both failures are R150 source-history assertions comparing the current R156
launcher to the original R147 integration digest. No timeout/OOM; container
removed normally; static step was not reached after the failing test command.
The same two failures reproduce in the Windows eight-test history selection.

Keep original R147/R150 evidence and the exact historical resolver unchanged.
Preserve the previous launcher from immutable main 4823 as an exact-byte archive;
check current source directly against the accepted e641 R156 digest. Add focused
rejection cases for altered live and archived bytes. No product/runtime changes,
native acceptance repetition or CI policy adjustment. Main remains at 4823.
Next: corrected focused history tests, static gate and new exact-SHA CI.

Evidence: ci045120-failure.json, ci045120-test-failures.txt,
ci-repair-red.json and ci-repair-source-provenance.json in the R156 product folder.
