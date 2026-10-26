# AlazHarness - status

## R154A1 - COMPLETE: VERIFIED_CURRENT_SOURCE_INSTALLATION

P1: IN PROGRESS. Current source/dependency installation sub-gate: PASS.
Projected readiness / finite work / full D3B / M1 / prod: NOT ACCEPTED.
Base main: 16830bd56e8c9b6a23e1bd60435ffb4b04793a9d.
Packaged runtime source: e03f7fd4e47fea6a58b749564ab350aeb4237a26.
Native source: d1516731308de8e87130dc68124e69aad35d6911, unchanged.
Branch: alaz/m1-install-readiness-r154a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-install-readiness-r154a1.

Continuation after gated publication: main in
C:\Antigravity\AlazHarness\scratch\worktrees\main-published-21oct-a37c.
Live Git HEAD/ref state and exact-SHA CI are authoritative. The original root
remains on 58b210a with all 33 existing changed/untracked file contents preserved.
Its status copy was not overwritten.

### Delivered and accepted

- Added scripts/install_projected_candidate.py and tests/test_projected_install.py:
  exact candidate/dependency/interpreter preflight, source-only exclusive
  installation, atomic no-replace publication, receipt and read-only verification.
- Added scripts/qa/r154a1_install_candidate.py and
  tests/test_projected_install_runner.py: fixed one-shot laboratory invocation,
  frozen inputs, explicit permissions and conservative UNKNOWN propagation.
- Actual source-only installation002 PASS, exit 0, in AlazHarness-D3B-P71C.
  Destination /opt/alaz-r154a1, device 2096, inode 27339.
  834 package files (77 harness + 756 native + one dependency inventory) and
  1,162 dependency files copied and read back. Provisioning inputs remain at
  /opt/alaz-r154a1-input.
- Python /usr/bin/python3.12, CPython 3.12.3:
  e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f.
- Archive: e036fba503130b3b259ec727439089c8fa3d88408359618fa5c7df77a6b5513b.
  Receipt: 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2.
- Root installer PID 7 and host carrier PID 74292 both terminal, exit 0.
  Request 3d5848d2-aae5-4a82-bd76-904504df6154 completed; no replay.
- Separate ordinary-user installed verification PASS, exit 0:
  all bytes, modes, ancestry, interpreter, receipt and destination identity.
  Request bbd6950b-72ad-4c56-a98e-f71d48a16154 completed.
- No native startup, finite task, service, model/provider, image, mount or cgroup
  was started or created. Real model calls: zero.

### Tests, reviews and preserved corrections

- Linux installer: 36 PASS / 0 SKIP, exit 0, owned synthetic fixtures.
- Windows installer: 16 PASS / 20 Linux-only SKIP, raw unittest exit 0.
  First CRLF skip-count wrapper exited 1; raw output and erroneous summary
  preserved, reporting corrected from the same output without a test replay.
- Linux operator: 11 PASS / 0 SKIP, exit 0.
- Windows operator: 10 PASS / 1 Linux-only SKIP, exit 0.
- Actual ordinary-user environment and real-candidate preflight both PASS.
  These focused/platform results overlap and are not a full-regression total.
- Independent exact-byte installer and operator reviews found no blocker.
  Initial operator uncertainty/umask findings fixed before root application;
  original attempt001 is SUPERSEDED_NOT_APPLIED. All four candidate payloads
  equal the accepted preflight. Incomplete native review is not corroboration.
- All 77 packaged HEAD Git blobs match the archive. A closure check initially
  compared Windows checkout bytes; the sole LICENSE CRLF difference is qualified
  in checkout-qualification.json. Failed assertion retained; no content rewrite.
- Final pre-publication root33/native/main custody check PASS in protected-state.json.

### Publication gate

Implementation, installation and evidence are complete locally. Staged repository
static gate PASS, exit 0: 6,348 files, two gitlinks, 3,745 tests discovered (not
executed). Initial 120-second timeout is preserved and qualified; the accepted
standalone scanner completed in 198.379 seconds. Final closure metadata receives
changed-file/whitespace checks before commit. The exact final commit must pass
alaz/local-ci before ordinary fast-forward main publication. No new full Windows
suite or remote numeric test count is inferred here.
Live final local/origin/remote main equality and exact-SHA CI are checked before
closure; the ignored scratch publication journal records the final observations.
Git publication does not start a runtime service. No force, squash, reset or
earlier denied operation retry.

### Exact next product gate

Use the verified current installation for the original supervised ext4 image and
live caller context. Produce retained seed/receipt through the original native
owner/finite lifecycle on that same image after normal close while lease is held.
Copied QA state or rewritten device/inode/owner records are invalid.
Derive live supervisor/fence/cgroup/namespace/loop/principal bindings, then accept
fixed projected readiness and ordered close within the original worker deadline.
After that accept normal/error, replay/new-work and a real finite job through the
same product path. P2's selected real provider/budget follows P1 acceptance.

Report: docs/M1-INSTALL-READINESS-R154A1.md.
Roadmap: docs/PRODUCT-ROADMAP.md.
Evidence: evidence/m1-install-readiness-r154a1/.
History: docs/status-history/r154a1-parent.md, r154a1-initial.md,
r154a1-pre-install.md, r154a1-install-pending.md, r154a1-prepublication.md
and r154a1-work-log.md.
