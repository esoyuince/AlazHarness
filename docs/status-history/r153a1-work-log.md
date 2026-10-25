# R153A1 work log

The exact R152 parent status is r153a1-parent.md. The initial R153 status is
r153a1-initial.md. Current status.md remains the single active handoff.

## Implementation and first focused-run checkpoint

# AlazHarness - status

## R153A1 / P1 - IN PROGRESS: supervised readiness candidate

Roadmap decision: 2026-10-25, Europe/Istanbul.
Active branch: alaz/m1-product-path-r153a1.
Active worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-product-path-r153a1.
Base: 7abdd57e408ec7972bddeaf267ea180b4cb3673b (published main).
Native source: d1516731308de8e87130dc68124e69aad35d6911, unchanged.
Protected root remains on 58b210a with its original 33 changed/untracked files.

### Product path and scope

The adopted five-package roadmap is docs/PRODUCT-ROADMAP.md. This package adds
the missing fixed supervisor child composition and a reproducible exact-source
candidate exporter. The original retained target remains readiness-only. Full
P1 still requires current installation, a retained receipt from the actual
supervised ext4 volume, positive native readiness and then finite useful work.

### Completed at this checkpoint

- Isolated worktree and baseline of main, native source and protected root.
- Roadmap persisted; prior status preserved in docs/status-history/r153a1-parent.md.
- Additive RetainedVolumeSupervisor and fixed child entrypoint. Same inherited
  image lease/fence, cgroup/namespace identity checks and original launcher.
- Bounded nonblocking pipe transport, exact completion protocol and conservative
  worker deadline. Unknown child state prevents stop/finish; no signal or retry.
- Independent source review found no remaining blocker in the reviewed bytes.
  Initial stdio/check-list findings were corrected without weakening old guards.
- Real owned Linux subprocess/pipe checks: 4 PASS, zero skips, Python 3.12.14.
  This is transport validation only, not native store or kernel projection.
- First Windows focused run failed: incomplete synthetic IPC policy plus a
  shared os.stat mock that also broke unittest traceback rendering. Raw receipt,
  source snapshots and diagnostic were preserved in focused001. The fixture now
  supplies the original complete v2 policy and mocks only this module's OS seam.
  Product validators remain unchanged.

### Active verification

The corrected focused run is pending under request
ff82a6b2-7332-44d8-bb6a-65c531ba1531 (focused002). Poll to terminal; do not replay.
Next: full regression/static gate, exact-source commit and actual source-only
archive export, then exact final-SHA alaz/local-ci before normal main fast-forward.
No install, service, provider/model call, root/WSL/mount or cleanup action occurred.

### Remaining acceptance boundary

A retained receipt must be created by the original native owner on the same
supervised ext4 volume; old /tmp QA state or rewritten inode/device records are
not valid. Old prepared-only installations do not qualify current d151 bytes.
Historical denied actions must not be replayed or routed around. No new R153
installation has been attempted or rejected. Actual kernel readiness, finite
work, full D3B and M1 remain unaccepted.

## Corrected focused run and full regression checkpoint

# AlazHarness - status

## R153A1 / P1 - IN PROGRESS: supervised readiness candidate

Roadmap decision: 2026-10-25, Europe/Istanbul.
Active branch: alaz/m1-product-path-r153a1.
Active worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-product-path-r153a1.
Base: 7abdd57e408ec7972bddeaf267ea180b4cb3673b (published main).
Native source: d1516731308de8e87130dc68124e69aad35d6911, unchanged.
Protected root remains on 58b210a with its original 33 changed/untracked files.

### Product path and scope

The adopted five-package roadmap is docs/PRODUCT-ROADMAP.md. This package adds
the missing fixed supervisor child composition and a reproducible exact-source
candidate exporter. The original retained target remains readiness-only. Full
P1 still requires current installation, a retained receipt from the actual
supervised ext4 volume, positive native readiness and then finite useful work.

### Completed at this checkpoint

- Isolated worktree and baseline of main, native source and protected root.
- Roadmap persisted; prior status preserved in docs/status-history/r153a1-parent.md.
- Additive RetainedVolumeSupervisor and fixed child entrypoint. Same inherited
  image lease/fence, cgroup/namespace identity checks and original launcher.
- Bounded nonblocking pipe transport, exact completion protocol and conservative
  worker deadline. Unknown child state prevents stop/finish; no signal or retry.
- Independent source review found no remaining blocker in the reviewed bytes.
  Initial stdio/check-list findings were corrected without weakening old guards.
- Real owned Linux subprocess/pipe checks: 4 PASS, zero skips, Python 3.12.14.
  This is transport validation only, not native store or kernel projection.
- First Windows focused run failed: incomplete synthetic IPC policy plus a
  shared os.stat mock that also broke unittest traceback rendering. Raw receipt,
  source snapshots and diagnostic were preserved in focused001. The fixture now
  supplies the original complete v2 policy and mocks only this module's OS seam.
  Product validators remain unchanged.

### Active verification

Corrected Windows focused002 completed exit 0: 52 tests, 48 PASS and exactly four
Linux pipe SKIP; the same four pipe tests passed on Linux. All 29 supervisor
contracts and all 19 real-Git/archive candidate checks passed.
The full standard regression is RUNNING under request
3442d44a-8756-4593-af56-ef95173a1531 (full001). Poll to terminal; do not replay.
Next: static gate, exact-source commit and actual source-only archive export,
then exact final-SHA alaz/local-ci before normal main fast-forward.
No install, service, provider/model call, root/WSL/mount or cleanup action occurred.

### Remaining acceptance boundary

A retained receipt must be created by the original native owner on the same
supervised ext4 volume; old /tmp QA state or rewritten inode/device records are
not valid. Old prepared-only installations do not qualify current d151 bytes.
Historical denied actions must not be replayed or routed around. No new R153
installation has been attempted or rejected. Actual kernel readiness, finite
work, full D3B and M1 remain unaccepted.

## Full regression result

Full001 request 3442d44a-8756-4593-af56-ef95173a1531 completed exit 0.
3,690 tests run; 3,663 PASS, 27 SKIP, zero failures/errors. Original 23 skips
unchanged plus four Linux-only pipe skips; those four passed separately on Linux.
Source hashes unchanged before/after. Local static/index gate and source export
are next. Only final closure SHA will need the remote publication gate; no
separate code-commit CI is required for a source-only archive build.

## Local static/index gate

Request 1076690d-0dfc-4b60-94b4-0252ea721531 completed exit 0.
6,259 tracked files and two gitlinks checked, 3,690 tests discovered; zero
static errors and default staged whitespace exit 0. Full test execution remains
full001. Raw .log files are locally retained; explicit public transcript copies
will be hash-checked and scanned before the source commit.

## Real-source refusal and narrow marker refinement

Source checkpoint652d881 committed locally with tested source Git bytes and exact
public transcript archives. candidate001 refused one credential-url pattern,
with no archive or installation. Git/AST classified native base.py line337 as a
conventional placeholder in resolve_proxy_url's docstring. Native bytes/scanner
were not changed. Exact native marker review requires all eight identity fields,
every occurrence and the entire declared inventory; changed pin/clean bytes
cannot silently drop it. Independent review passed final97be4be/015a43c bytes.
Linux packaging27 PASS, Windows new-marker8 PASS. Full001/static001 remain the
pre-marker complete-repo receipts; runtime source files are unchanged. The first
Windows marker preflight was NOT STARTED due solely to a local helper's extra
EOF LF; actual primary scanner was verified byte-equal to its committed source.
Next: refined source commit, candidate002 actual export and exact-final-SHA CI.
