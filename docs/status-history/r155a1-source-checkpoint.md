# AlazHarness - status

## R155A1 - IN PROGRESS: same-image retained seed and readiness

Goal: qualify task-free original native retained seeding, then connect it to
the existing supervised image and fixed projected readiness/ordered close.
Base main: 27eb7571211ba0b685d7893d149438d612f6e2cd.
Branch: alaz/m1-seed-readiness-r155a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-seed-readiness-r155a1.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Accepted installation: /opt/alaz-r154a1 in AlazHarness-D3B-P71C.
Runtime candidate: e03f7fd4e47fea6a58b749564ab350aeb4237a26.
Installation receipt: 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2.

### Current checkpoint: source seams implemented, runtime acceptance NOT RUN

- Original root58b210a and all33 existing changed/untracked file bytes match
  the R154 baseline. Main/native clean at entry; no root status overwrite.
- Ordinary-user read-only lab probe completed exit0. Original installation
  verifies all834 source-package and1162 dependency files; receipt unchanged.
  New R155 rootinput/state/cgroup/anchor paths were absent.
- Task-free original producer implemented and source-reviewed at113139e0.
  Owned local producer tests:21 PASS. No actual native producer invocation yet.
- Fixed original-worker namespace/cgroup seed child implemented.
  Owned local child tests:24 PASS. Its three original helper hashes match the
  accepted candidate manifest182b9d01.
- Fixed caller implemented and independently reviewed at69553f5f.
  Owned local caller tests:23 PASS (including failed diagnostic retaining custody).
  Tests use owned doubles, not mount/UID/native execution acceptance.
- Review found and fixed a post-effect custody issue before runtime: unknown
  effects must retain the SAME live root controller/lease/Popen objects.
  A diagnostic in try/finally enters a retain-alive wait; only known stdio closes.
  No fork, stop/finish, kill, retry, cleanup or lease release follows uncertainty.
- Host prepare/apply transport remains in implementation/review. It must observe
  EOF and verify live root PID/startticks without terminating a retained caller.
- Seed/child transfers are being observed by their owning agents.
  Caller two-file transfer request b37c9975-0790-4ab1-9813-83c0d2356155 is
  terminal, both files applied and readback hashes verified.

### Next exact work

Observe source transfer completion, finish host transport review and focused
tests, then execute one frozen ordinary-user native seed proof in a fresh home.
Only after terminal ordinary acceptance may the new dedicated P71C same-image
root acceptance be considered: seed -> original projected readiness -> normal
stop/finish, actual image/fence/cgroup identities and exact original supervisors.
No copied QA profile, edited retained identity or old denied root replay.
Keep seed35s + readiness60s + stop15s inside original worker120s.
Preserve all partial/unknown state and live custody, inspect terminal receipts.

R155 actual native seed / same-image root acceptance: NOT RUN.
No R155 privileged invocation, image/mount/cgroup or native process started.
P1 IN PROGRESS; installation sub-gate PASS; readiness, finite work, M1/prod open.

Evidence: evidence/m1-seed-readiness-r155a1/.
Roadmap: docs/PRODUCT-ROADMAP.md.
Previous report: docs/M1-INSTALL-READINESS-R154A1.md.
History: docs/status-history/r155a1-parent.md and r155a1-initial.md.

### Work log

- Entry: isolated branch from27eb757; preserved R154 final and R155 initial status.
- Source checkpoint: original verifier readback PASS; three fixed seams prepared,
  independent source review, owned local68 tests PASS. Runtime still NOT RUN.
