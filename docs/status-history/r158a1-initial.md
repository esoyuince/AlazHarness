# AlazHarness - status

## R158A1 - IN PROGRESS: P2 daily local control

Goal: reuse HostGateClient/HermesRunsClient and the canonical native owner for
the daily local task/observation/result/usage/cancel path, with explicit listener
and close ownership. No second task queue or persisted result authority.

Active branch: alaz/p2-local-control-r158a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\p2-local-control-r158a1.
Base main: aba1e6af9242e7b4006bbd9f6244022549a52c61.
Native source under review: d1516731308de8e87130dc68124e69aad35d6911.

### Verified entry and current work

R157 final-publication journal sha256:
9776eefcde208f17da7f0dee9cecdb8c6a0c3d2921f96a41f382e88bb43d37a5.
Live R157/main/remote refs match aba1e6a; latest required alaz/local-ci status
57248416850 is success (verified same-commit reuse). All 59 R157 files and all
33 original-root changed files match their recorded bytes. Protected trees match.

P1 remains DONE. P2-P5, full D3B, M1 and production remain OPEN.
Source inspection is in progress. No native runtime attempt, provider call,
new installation or service start has been made for R158.

### Current operation / exact next step

Read current pinned JS clients, native listener/stop/physical-worker sources,
and cross-check the host/execution source locks against the prepared owner.
Then implement and test the supported thin control path and document the exact
remaining listener/model acceptance work. A real provider call requires the
selected model and explicit call/token/cost budget; do useful source work first.

New isolated worktree creation completed exit 0. Read-only source export request
e0010158-607e-46dc-a368-aa51a3913ce4 is in progress; poll its same receipt.
No unresolved mutating native operation exists.

### Records

Baseline: evidence/p2-local-control-r158a1/baseline.json.
Parent status preserved exactly: docs/status-history/r158a1-parent.md.
Plan: docs/P2-LOCAL-PRODUCT-R158A1-PLAN.md.
Publication journal for this task will be scratch/r158a1-publication/final-publication.json.
Original root user content remains protected; its status copy is not overwritten.

### Work log

- Verified prior publication, live Git and latest required CI; read status,
  AGENTS.md, workspace rules, MVP and R157 report.
- Created isolated R158 worktree from accepted main.
- Began pinned source mapping and independent lifecycle review.
