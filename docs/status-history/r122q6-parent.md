# AlazHarness - status

## D3B-SESSION-BORROW-JOINT-J121S1 - DEVELOPMENT-INTEGRATED; NATIVE PATCH STAGED / SHARED BOOTSTRAP OPEN

Canonical branch alaz/d3b-principal-launch-21oct.
Worktree C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct.
Tested merge6a01e1a89b0017153dc1710e16446e22e24f0f80 fast-forwarded, both original
S121R4 implementation and S121S1 independent QA histories intact. Native feature
2bc50496bebe21f948dd2e86f553ef1e22904ed2 on94321058 changes only3 native files;
installed vendor/source locks remaineb75627, NOT ACTIVATED. Read GitHEAD for final
documentation handoff; exact delivery refs in matching joint delivery.json.

### One new ownership seam, no guard removal

Optional SessionStore(...,session_db=caller_state) validates native state/profile/
file/handle/application identity and explicit single-home/SQLite-only mode BEFORE
eager default registry acquisition. Selects same caller connection across active/
routing/key paths; no new SQLite/registry acquire, foreign profile fallback or
closed-handle reopen. Default multiplexed constructor remains unchanged and still
uses registry-owned connection. No private-field replacement after constructor.

Detach disables only facade, never closes caller DB or releases profile. Native
mutex/open transaction/inflight/dirty state refuses without waiting/rollback/
discard. Borrowed routing JSON import/fallback disabled. Scope/config/owner-handle
changes refused. Full shared concurrent writer/drain coordination stays caller's
obligation; per-call guard is not atomic all-work ownership. Existing native write
methods may read DB header; zero-raw-open acceptance is construction/selection/
readonly-load/detach, not every mutation. Native profile/mount trust not minted.

### Current verified counts

NEW combined fullWindows3162=3139PASS/23SKIP/0ERROR/0FAIL exit0.496 source/config/
test hashes +5 native patch hashes stable. ALL490 prior harness files unchanged.
50 original parent evidence blobs preserved. Original23/23 and independent24/24
genuine native Windows methods PASS on same3 product hashes; suites overlap,
not47unique cases.14offline receipts are subsets of standard suite; re-run14/14
PASS on delivered source.23old platform/opt-in skips NOT reexecuted. Native full
upstream pytest and Linux isolation NOT RUN.

Original registry behavior control confirmed1 extra connection, not called bug.
Independent250 and original261 imported native files match immutable943Git or
explicit patch. Fresh patch apply reproduces exact bytes, second apply refused.
Fresh profiles removed, caller leases released after test teardown, registry0.
First failed fixture outcomes preserved (original21/23 and independent21/24):
sessions directory was already created by native imports, not borrowed facade.
Before/after comparison correction left product unchanged. Mutation failure test
allows existing native header validation but never JSON fallback/new connection.
Native journal fallback warning retained; no dependency/runtime upgrade.

### Next exact acceptance boundary

SessionStore caller-owned constructor is ready as staged optional patch. Now
construct one REAL canonical runner/SessionAuthority with the existing caller
state/accepted epoch and same three-store owner; no duplicate connection or epoch,
no ad-hoc private assignment. Native borrowed_runner_conflict remains BYTE-EXACT
and MUST stay until the shared contract is explicitly tested. Native listener/
work/model routes not activated. Then same-path profile/mount/three-store lifetime
and activeHTTP/full-isolation acceptance. FullD3B/cross-store recovery/powerloss,
broker live-ledger/dummy-provider accounting remain OPEN. LegacyIPCv2 CLOSED.
C120P9 extra physical probe remains HOLD; prior blocked operations NOT retried.
No root/WSL/provider/model/main/push/CIqueue/production/account changes. Maincc7ceba.

### Records

Joint report docs/D3B-SESSION-BORROW-JOINT-J121S1.md; detailed original and independent
reports D3B-SESSION-BORROW-S121R4.md / D3B-SESSION-BORROW-QA-S121S1.md.
Staged config/hermes-session-borrow-s121r4.json; patch under patches/hermes/s121r4/.
Joint evidence evidence/d3b-session-borrow-joint-j121s1/: summary.json,delivery.json,
full-windows-result.json,full-source/patch manifests,source-custody.json,
selected-delivery-result.json,static-primary-final.txt. Original raw native/results
remain in s121r4/s121s1 evidence. Status history docs/status-history/j121s1-*.md.
All native/full/merge jobs terminal; final static/docs commit only, no runtime replay.
