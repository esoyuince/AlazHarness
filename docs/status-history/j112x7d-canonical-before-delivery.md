# AlazHarness - status

## D3B-API-BORROW-JOINT-J112X9 - DEVELOPMENT-RECORDED; NATIVE PATCH NOT ACTIVATED

Canonical branch alaz/d3b-principal-launch-21oct.
Worktree C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct.
Tested harness merge c4ff1211305055c29258a846a6faea8b7724fc17 fast-forwarded.
Native feature cc16c10b16a0ca8d80b23fd9be3f0e59ee605075 includes complementary
response parent e19a945342c94138c685ac919b208d558ddcc53a. Both native feature
histories/patches are retained. Installed native pin eb75627 and all gitlinks/
sources.lock remain UNCHANGED. Current H110E/A109/P102 diagnostics still selected.

### Implemented optional native seam

One BorrowedAPIStores bundle passes real SessionDB, replay and ResponseStore to
native APIServerAdapter without new database opens. Exact home/process/thread/
connection/canonical-state checks; no lazy fallback for other homes, closed or
replaced handles. Single claim; caller retains three-store and profile ownership.
Borrowed disconnect refuses active/unknown work and active transactions; drains
resources, never closes caller DBs or rolls back caller work. Cancellation/error
keeps terminal UNKNOWN ownership; no blind retry. No default async status writer
scheduled by borrowed teardown. Existing unborrowed native path retained/tested.
Borrowed connect explicitly REFUSES: no new agent/work/model listener activated.

Complementary ResponseStore canonical_state reuses caller SessionDB for terminal
and tombstone reads. Main-qualified SQL, foreign/stale/busy/transaction refusal;
no fallback to in-memory response store on borrowed disk-open failure. Not a
trusted third-store schema/preconstructor or full readiness qualification yet.

### Verified counts and limits

NEW complete harnessWindows2813=2790PASS/23SKIP/0ERROR/0FAIL, exit0.437 source,
config/test/patch artifacts stable;427 prior harness sources unchanged.74 original
evidence blobs preserved.15 offline receipts are included in standard total.
23 prior platform/opt-in skips not rerun. Full upstream Hermes suite NOT RUN.

Actual native adapter27/27 Windows with real three stores,309 imported native
files byte-matched to combined Git commit. HTTP cleanup fault awaitables doubled;
no actual listener/model/provider. Complementary response24/24 Windows and24/24
ordinary Linux (24 distinct methods). Separate original/borrowed Linux competitor
comparison: canonical EXCLUSIVE lock staysBUSY both paths, releases on owner close;
NO upstream lock-corruption observed. Borrowed response settles committed state
with0 extra canonical connections; uncommitted/TEMP false terminal rejected.
No full Linux confinement trial of new native adapter/third-store combination.

Both native patches applied to immutable base, five native files reconstructed
exactly/compiled, then reversed to original three files; temporary copy removed.
First failed fixtures/accounting retained. Windows asyncio socketpair is allowed
only for unittest loop setup; optional IPv6 import probe remains DENIED; zero new
network attempts during successful native operations. Owned temp profiles empty.

### Exact next step

Integrate response_store.db as a THIRD persistent store: trusted explicit
preparation, finite layout, schema/identity, read-only preopen and live validation
under sole A109 lifecycle. Then define healthy/busy policy for legitimate work,
qualify native agent HTTP under full isolation, and only then consider explicit
runtime-pin activation and broker live-ledger/dummy-provider accounting. No
partial-pair replay, paired atomic recovery or physical power-loss claim.
LegacyIPCv2 CLOSED; fullD3B OPEN. Main remainscc7ceba, no push, model/provider,
root/mount/account/production/defaultUbuntu/CIqueue or service changes.

### Records

Report docs/D3B-API-BORROW-JOINT-J112X9.md.
Evidence evidence/d3b-api-borrow-joint-j112x9/{summary,delivery,patch-roundtrip,
source-custody,full-windows-result,full-sources-before,full-sources-after}.json.
Native patches patches/hermes/{a112x7d-response-canonical-state,
b112x9-borrowed-api-stores}.patch; adapter manifest config/hermes-api-borrow-b112x9.json.
Original native/QA proofs evidence/d3b-api-borrow-b112x9/ and d3b-api-storage-a112x7d/.
Prior handoffs docs/status-history/j112x9-*.md. All own native/full/merge jobs
terminal. Final local static/doc commit below; current Git HEAD is continuation.
