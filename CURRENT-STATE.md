# AlazHarness — current checkpoint

Date: 2026-10-15. Default workspace remains C:\Antigravity\AlazHarness.
Branch for this package: alaz/hyb-001-reviewed.
Isolated worktree: scratch/worktrees/hyb-001-reviewed under the default workspace.
Always confirm git status and HEAD before resuming; other work may have advanced.

## Current scope

M0 bootstrap/publication is accepted at historical main 58b210a (37/37 tests).
The repository is public / MIT; existing alaz-server Local CI posts alaz/local-ci.
GitHub Actions remains disabled. No server policy or credentials changed here.

HYB-001 selected-component map and actual code copies are implemented.
HYB-002 has a bounded first protocol/mock slice. HYB-003 full runtime is NOT RUN.
No claim of M1 or M2 acceptance. The fixture is explicitly scripted, not AIAgent.

## Source custody

- OpenClaw submodule pin: 2dcbb6138d57dccfcd54f2f908ef9f38268b1229.
- Hermes submodule pin: eb75627faf532fa6ffbdae59a0d14b0b385fc780.
- Both original vendor worktrees are unchanged. This isolated worktree does not
  initialize them; six source modules + two licenses are tracked under packages/upstream.
- components.lock.json records original/target hashes and one import relocation.
- Original full-byte provenance was checked against the pinned local vendor tree.

## Implemented boundary

Node uses actual copied OpenClaw cancellation and execution/settlement deadlines.
A fixed Python test child uses actual Hermes StdioTransport and IterationBudget.
Our adapter handles correlation, one active run per instance, process-local
idempotency, bounded frames, deny-only peer requests, cancellation, uncertain
outcomes and verified direct-child closure. Resume is explicitly unsupported.

No full Gateway, real AIAgent, persistent identity/session/memory, general shell,
model inference, autonomous agenda, scheduler or OS sandbox was started.
Initial mock config remains a design example, not an enforced production policy.

## Parallel-work preservation

A second component implementation and modified CI gate appeared in the original
checkout while this package was being tested. They were not authored in this lane.
Those files were preserved, not merged, reset, deleted or bundled into this branch.
The aggregate original-worktree test count is not this package's acceptance.
This branch is based on 58b210a plus only the explicitly owned component slice.
Do not switch/merge the shared root checkout while another writer may use it.

## Reproduce this package

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_component_slices.py
python -B scripts/demo_hybrid.py
```

Node 24+ and Python 3.11+ are required. No package installation or model key.
Record exact commit CI evidence independently after push. Read docs/CI.md,
docs/COMPONENT-MAP.md, ADR-0002 and docs/HYB-001-COMPONENT-SLICE.md for scope.

## Next work

First reconcile the two implementation branches without overwriting shared work.
Then HYB-003: provision isolated Hermes runtime, use the real AIAgent public entry
and replace only model I/O with a mock. Qualify a real tool round, native ownership,
profile isolation and settlement. Do not call the scripted peer a completed agent.
M2 autonomy follows complete M1 acceptance, not helper/protocol test counts.

## This branch's local acceptance

- Clean isolated package on Windows: 83/83 tests PASS, zero skipped/errors.
- Original pinned source-byte comparison: 8/8 copied files PASS (six modules + two licenses).
- One scripted demo: completed; real model calls 0; direct child reaped with exit 0.
- Evidence: evidence/hyb-001/windows-component-tests.json, component-provenance.json,
  scripted-demo.json. These are pre-commit local receipts; GitHub exact-SHA status
  is checked independently after push. A live CI success does not imply full M1.

## Linux gate repair

Initial feature commit ed674068922445d2345bd09f251eb8b8a9e90828 had 82/83 parent
tests pass on Linux; the one syntax test had four failing .ts subcases because
native --check treated the files as JavaScript. Behavior tests were not excluded.
The portable gate explicitly strips types with Node's parser, then checks ESM.
The same four source files passed in the immutable Linux CI image; Windows full
suite remains 83/83. Failed and corrected preflight receipts are preserved under
evidence/hyb-001/. Exact repaired-commit live CI must be read independently.
