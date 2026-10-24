# AlazHarness - status

## D3B-ADMISSION-JOINT-J128C6 - DEVELOPMENT-INTEGRATED OPTIONAL PATCH / FULL ACTIVE HARNESS STILL OPEN

Canonical branch alaz/d3b-principal-launch-21oct.
Worktree C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct.
Tested union53ddfd108759b32c71a7b9f1857bb044710b9a1c fast-forwarded from39a1be3.
Original implementationdad8011 and independentQAfc3bbbd histories retained.
Read GitHEAD for final docs-only checkpoint; exact promotion in joint delivery.json.
Native feature1b7b31e14451baf1d56c3edbfa2cea69a8f7940c on1e97dd61 STAGED_NOT_INSTALLED.
Installed native/source locks remaineb75627,maincc7ceba; no push/remoteCI.

### Native local admission and retained drain

Existing BorrowedAPIStores activate_admission/begin_drain/finish_drain uses same
CallerOwnedRunnerState PREPARED->ACTIVE->DRAINING->DRAINED, one-way, no new
scheduler/ledger/store owner or fourth connection/epoch. Native SessionAuthority
entry and SQL transactional guard check phase/profile/config/identity; two flags
alone cannot activate. Pure guard does not recursively acquire state SQL lock.
Ordinary GatewayRunner.start/API.connect/listener/provider remain unqualified.

Drain before native write guard refuses new row; guard-passed inflight write may
commit after DRAINING begins. Native tracked_write survives cancelled caller;
writer ownership retained until actual outcome. Claimed leaf can settle sameepoch.
DRAINING stops new admissions AND queued claims. QUEUED/UNKNOWN/retained sessions
block finish and remain preserved, not automatically executed/cancelled/pruned/
replayed. This is NOT a complete graceful FIFO or restart/reconciliation contract.

Current release barriers recheck work/stores/ledgers before API detach, after its
await and before runner detach. Late obligations reject; cancelled/failed cleanup
retains CLOSE_UNKNOWN, all3caller handles/profile and no blind retry. API->runner
only detach; caller closes original stores and lease. No health/capacity/store
release inferred from a status flag or cancelled waiter.

### Exact acceptance

Original native46/46PASS=24new+22prepared compatibility; independent28/28PASS on
same5product files. Scopes overlap, not74unique. Real native objects, SQL guard/
ledger/claim/settlement, actual tasks/threads and explicit registry/callback/memory
cleanup fault barriers. NOT full API request/TurnRunner/agent execution or original
NativeStoreStartup ACTIVE integration. Final original508/independent514native
imports match immutable feature; no native method replacements. Watched
transitions0newSQL/rawDBopen/rowwrite; successful fresh fixture profiles/ownership/
registry clean. Fixture retained-row cleanup is not product drain completion.

First fixture-envelope error, original5/independent4 additional before-fix failures,
patch-application CRLF fixture, missing per-invocation commit identity retained.
Same4failing independent QA bytes pass final28; native source unchanged when2late
await/cancel checks extended original44to46. Source trust does not authorize use.

NEW fullWindows3343=3320PASS/23SKIP/0ERROR/0FAIL, command00031 exit0.563source/
config/test hashes+8patches unchanged through delivery, all557prior files unchanged,
6newsource/config/test files. Same23skip IDs/reasons retained, not run asLinux.
16offline receipt tests (8+8) passed again on delivered exact source; standard
subset, no native/full replay.101original evidence Git blobs unchanged. Full
wrapper reporting succeeded; separate commit-path assertion diagnostic retained
for one identical shared parent history file, no source/test changes needed.
Local staticPASS on tested source; final canonical static evidence recorded below.

### Exact remaining work

Current harness prepared513source manifest and observers stay1e97; this new native
feature is not silently repinned or installed. Existing clean-only owner gates
cannot be used as ACTIVE health. NEXT integrate the selected native feature with
SAME NativeStoreStartup owner and phase-specific source/lease/mount/storage checks;
resolve accepted FIFO/session retirement through native owners and correlate
actual request/physical-worker lifetime. Then test THAT exact active path under
existing Linux isolation and HTTP. Old isolation is historical source, not
new-feature acceptance. FullAIAgent/model budget/cross-store recovery/powerloss open.

Read-only reviewer completed/archived; no delegated work pending. No root/WSL,
model/provider/listener/production/account/main/push/CIqueue changes. Prior blocked
root/refinement/C120P9 work stays blocked/not rerun. User root and vendor changes
preserved. Current native/full/merge jobs terminal, only final docs/static commit.

### Records

Docs/D3B-ADMISSION-JOINT-J128C6.md, D3B-ADMISSION-LIFECYCLE-A128C6.md,
D3B-ADMISSION-QA-Q128C6.md. Config/hermes-admission-lifecycle-a128c6.json.
Patch patches/hermes/a128c6/0008-caller-owned-admission-lifecycle.patch.
Evidence/d3b-admission-joint-j128c6/: inputs,summary,joint-source-custody,
full-windows-result/rawlog,source/patch manifests,skip-custody,delivery,
selected-delivery-result,static-final,static-primary-final,merge-finalization-diagnostic.
Original raw evidence and before-fix failures preserved in A128C6/Q128C6 folders;
status history docs/status-history/j128c6-*.md retains checkpoints.
