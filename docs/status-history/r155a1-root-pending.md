# AlazHarness - status

## R155A1 - IN PROGRESS: ordinary native seed PASS; same-image apply pending

Base main: 27eb7571211ba0b685d7893d149438d612f6e2cd.
Branch: alaz/m1-seed-readiness-r155a1.
Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\m1-seed-readiness-r155a1.
Native source: d1516731308de8e87130dc68124e69aad35d6911.
Installed runtime: e03f7fd4e47fea6a58b749564ab350aeb4237a26 at /opt/alaz-r154a1.
Dedicated lab: AlazHarness-D3B-P71C.
Receipt: 137cbe59427813b50f8c8581a7dbc3b81db9e514e2e57784cee91baa4cc17ae2.

### Live operation

Apply request e2a42e11-d56e-4bc9-9f72-bc28d2c76155 dispatched once;
Bridge process328a911d-bdb2-4960-9b9a-c7581b9b68f7. Terminal receipt PENDING.
Expected intent2b1d4f7eae5ac979a8f3449e230e8be8156d1335bae41b07a91f55b0ad4836a5.
No replay. Observe this same request; do not infer actual root effects, caller
liveness, native seed, readiness or normal close until its evidence is available.

### Accepted checkpoint

- ordinary007 actual native task-free seed PASS, terminal exit0.
  Producer2c004f6a7154d95af216517c867f1e3cafd63a05e05838f65752eca1b89c5f01.
  PID7/startTicks6259 under ordinary UID23001/GID23003, parent6.
  Profile [2096,29648]; DB identities [2096,29662], [2096,29666], [2096,29667].
  Epoch1, six original checks, original PREPARED consumer then detach/ownerclose,
  three connections physically closed, retained capture while lease held,
  original handoff roundtrip and normal lease release/async loop shutdown.
  Verification3376ms + native23851ms = total27227ms.
  755 qualified native files,130 source-derived cache entries.
  One original IPv6 capability probe remained BLOCKED; actual socket closed.
  Tasks/model/listeners/admission0. This is ordinary rootfs only, NOT same-image.
- Current producer/child/caller/transport/host sources independently reviewed.
  Exact hashes are in focused-windows002/result.json and frozen intent.
- Primary focused-windows002 PASS exit0:120 cases,113 pass,7 Linux-only skips;
  includes actual finite Windows Python three-pipe fixture. No native/WSL/root
  test action in that suite. Earlier focused001 failure is preserved; fixed
  Windows metadata-view comparison and a missing constant in an owned fixture.
  This is selected verification, not a new full-regression count.
- Ordinary001..005 failures, original reasons and exact sources preserved.
  ordinary003's old generic diagnostic lost its finite verifier reason;
  independent/embedded later full verifications PASS, no guard/receipt bypass.
- ordinary006 CreateVm/HCS_E_CONNECTION_TIMEOUT occurred before Linux carrier
  startup. Subsequent read-only P71C probe found its home absent and all four
  R155 root paths absent. No VM/service restart or old-state cleanup.
  Exact322-byte UTF-16LE output retained as base64 text and ignored raw binary.
- Original root58b210a/all33 existing file bytes preserved at entry; no original
  status overwrite. Final root/native/main preservation check remains due.

### Concrete same-image001 input - prepared, not yet applied

Original ordinary proof result SHA:
49afc18aca1d4393925cef39e00a3a0195a0333ca3a7d510b2af0c172256541c.
Proof-set binding SHA:
cb79324e986166d606fcdf345da01a6dcff73c55a477e3db7ea27a6512b70abf.
Intent SHA:
2b1d4f7eae5ac979a8f3449e230e8be8156d1335bae41b07a91f55b0ad4836a5.
Manifest SHA:
2b97bdf8ddd2f3b776311aba16cffce50918c4446989f544aa2668c80238f793.
Raw ZIP104123bytes SHA:
7242482096d7a5f80677b94207b36dc66c30bfe244b5fcc2b93a0d35e9225268.
Host113ec74d, callercc80c882, childfe598ba4, transporta08345f8, producer2c004f6a.

Preparation1fb72a81-2d6a-4ab9-a3af-7216be396155 completed exit0.
Separate frozen input readback7adc5ca2-5c48-402d-8c81-9233a2fd6155 completed
exit0 and confirmed no execution-start marker. Apply must revalidate everything
against this external intent SHA and exclusively mark its one invocation.

Fixed new input /opt/alaz-r155a1-input; fresh state /srv/alaz-r155a1;
image /srv/alaz-r155a1/images/state.ext4 (64MiB), original supervised mount.
Next: one original worker seed35s -> retained projected readiness60s ->
normal stop/finish inside original worker120s. Metadata socket fixture only.
Post-effect UNKNOWN retains SAME live root caller/lease/child references;
no forced close, kill, retry, remount, cleanup or original-runtime modification.

R155 privileged apply dispatched; same-image outcome PENDING, not accepted.
P1 IN PROGRESS; installation and ordinary native seed sub-gates PASS.
Projected readiness, finite work, full D3B, M1 and prod NOT ACCEPTED.
Real model calls0. No R155 commit/push/CI yet.

Evidence: evidence/m1-seed-readiness-r155a1/.
Roadmap: docs/PRODUCT-ROADMAP.md.
Prior report: docs/M1-INSTALL-READINESS-R154A1.md.
History: parent, initial, source-checkpoint, ordinary-investigation,
transport-checkpoint and this pre-root snapshot under docs/status-history/.

### Work log

- Entry and source review snapshots retained.
- Ordinary failures diagnosed from exact sources; no identity/receipt edits.
- ordinary007 accepted the original task-free lifecycle under ordinary UID.
- Windows focused tests corrected and passed; independent review complete.
- same-image001 prepared and exact inputs read back before privileged execution.

- Root application pending: e2a42e11 dispatched once after native/test/frozen gates;
  result observation continues, with no second application or cleanup.
