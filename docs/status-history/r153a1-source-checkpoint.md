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
Full001 completed exit 0: 3,690 tests run, 3,663 PASS, 27 SKIP, zero failures and
errors; 487.133 seconds on Windows Python 3.14.3. Original 23 skip IDs/reasons are
unchanged and exactly four Linux pipe tests are additional Windows skips.
The seven current source/test hashes match before and after the complete run.
Static/index gate completed exit 0: 6,259 tracked files checked, two gitlinks,
3,690 tests discovered; default staged whitespace check exit 0. This adds no
runtime test count. No effectful command is pending at this checkpoint.
Next: immutable source commit and actual source-only archive,
then one exact final-SHA alaz/local-ci gate before ordinary main fast-forward.
Report: docs/M1-PRODUCT-PATH-R153A1.md. Evidence: full001/summary.json.
No install, service, provider/model call, root/WSL/mount or cleanup action occurred.

### Remaining acceptance boundary

A retained receipt must be created by the original native owner on the same
supervised ext4 volume; old /tmp QA state or rewritten inode/device records are
not valid. Old prepared-only installations do not qualify current d151 bytes.
Historical denied actions must not be replayed or routed around. No new R153
installation has been attempted or rejected. Actual kernel readiness, finite
work, full D3B and M1 remain unaccepted.
