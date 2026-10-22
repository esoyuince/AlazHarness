# J112X9 — tested native API store ownership, staged not activated

The native feature is cc16c10b16a0ca8d80b23fd9be3f0e59ee605075, built on response
borrowing parent e19a945342c94138c685ac919b208d558ddcc53a and original Hermes pin
eb75627faf532fa6ffbdae59a0d14b0b385fc780. There is ONE optional adapter constructor
seam and ONE complementary response-state view. Both are native fork changes,
not monkeypatched runtime factories or another gateway implementation.

The harness stores two exact patch artifacts/manifests and their acceptance
records. The installed vendor main, gitlink, sources.lock.json and running
H110E/A109 diagnostic path are UNCHANGED. This is an implemented/tested opt-in
feature staged for later explicit activation, not a deployed native agent API.

## Adapter ownership

APIServerAdapter can accept a single local BorrowedAPIStores bundle containing
actual SessionDB, RunIdempotencyStore and ResponseStore. It validates exact native
types, connection/path/process/thread/canonical-state identity, binds once to one
adapter/home and reuses the handles through native selectors. Constructor and
selection create no new SQLite connection. A foreign profile, runner conflict,
closed/replaced store or detached bundle is rejected rather than lazily reopened.

Borrowed disconnect refuses active transactions/work/tasks and unknown or invalid
work counters. It drains owned HTTP resources before detaching but NEVER closes
any caller DB, rolls back caller work or releases the profile/image lease. A
cancelled/failed cleanup is terminal UNKNOWN; blind retry is forbidden. Detached
idempotence does not require the caller to keep already-released stores open.
The default runtime-status writer is not scheduled by the borrowed teardown;
the unborrowed default path is retained and separately tested.

This bundle is not a lease, preconstructor validation, persisted schema certificate,
network permission or protection from malicious same-process code. Its caller
must own and qualify all three stores. Borrowed connect() explicitly refuses
before native HTTP setup. No work/model route has been enabled.

## ResponseStore canonical reads

The complementary optional canonical_state argument binds the existing live
SessionDB before opening response storage. Canonical response settlement uses
the same connection, not an additional read-only SQLite connection or native
pooled-reader helper. Busy, in-transaction, changed/foreign/closed state rejects;
main-qualified SQL prevents TEMP table shadowing. Read observations do not close
or mutate the caller's canonical store. Borrowed-mode response disk-open failure
must not silently fall back to memory. Default unborrowed behavior is preserved.

In real ordinary-user Linux comparison, the original extra SQLite read does NOT
corrupt the owner's EXCLUSIVE lock. Both original and patched cases keep other
processes BUSY before/after settlement and after ResponseStore close; competitors
acquire only after the canonical owner closes. The improvement is eliminating
the extra open and permitting committed terminal settlement under the retained
owner lock. Uncommitted terminal status is not accepted as durable; its caller's
transaction remains intact. A fake terminal row in TEMP cannot replace main.
No general POSIX-lock corruption claim is inferred from this experiment.

## Actual test boundaries

B112X9:27 actual native adapter/three-store Windows methods PASS,309 imported
native source files matched to the combined native Git commit. Cleanup failure
and HTTP-await ordering use explicit fixture awaitables; SQLite and native stores
are real. No API listener or provider run. The complete Linux API adapter/new
third-store/full-confinement combination is NOT tested by this result.

A112X7D:24 genuine native response-state methods PASS on Windows and the same24
on ordinary P71C Linux. Those platform repetitions are24 methods, not48 distinct
scenarios. It covers terminal/tombstone settlement, queued/started/unknown state,
foreign/stale/transaction/busy rejection and ownership-preserving close. Its
source hashes match the exact complementary files used in our adapter run.

A separate two-case Linux baseline/borrowed comparison uses real competing SQLite
processes and records source identities and cleanup. It is not27 additional
adapter methods or a native HTTP/full-isolation trial.15 offline receipt tests
(8+7) are standard-suite members; they don't rerun native scenarios. The full
upstream Hermes test suite was not run. One NEW complete combined harness run
with executable/config/test AND patch artifacts frozen is recorded here.

## Exact artifacts and history

Both patches were reapplied in order to three original source blobs, reconstructed
all five changed native files byte-exact, compiled, and reversed to the original
three files with both additions absent. The disposable reconstruction was removed.
This supplements the actual native run rather than claiming it as runtime proof.
74 original parent evidence blobs are preserved byte-for-byte in Git. Only
status.md conflicted; both prior handoffs are archived. All427 preexisting harness
sources are unchanged. Native main and current source pin never moved.

Original failures remain: explicit-BEGIN omission in a native-autocommit QA case;
Windows unittest socketpair blocked by the fixture; teardown None/async-status
cleanup errors; a27-method success aggregate rejected due optional IPv6 import
probe accounting. The optional probe remains denied; no network permission was
broadened to make tests pass. The borrowed status-writer side effect was removed
and all27 methods rerun. The final run has zero new network attempts in tested
adapter operations and zero new SQLite opens in borrowed constructor/selection.
Native default tests may create their own stores as intended. No old result is
rewritten as new success. Missing native commit identity was resolved with the
already configured harness identity per command, not a global config change.

## Activation gate / next work

response_store.db is a THIRD persistent store with its own schema, identity and
constructor side effects. It still needs finite layout, explicit trusted
preparation, read-only preopen and live validation integrated into A109's one
owner before this native feature can be selected. Then define readiness for
legitimate in-flight work instead of the currently quiescent-only diagnostics,
and qualify real native agent HTTP under full isolation. Only afterward test
broker live-ledger/dummy-provider accounting. No paired atomic recovery, power-
loss or automatic unknown-work retry is accepted here; legacyIPCv2 CLOSED and
fullD3B OPEN. No source pin upgrade or listener activation is hidden in this union.

No provider/model, root/mount, production/account/service/defaultUbuntu/CIqueue
change, main update or push. Only owned temporary profiles/code were touched;
source trees intentionally remain in ignored scratch/native feature worktrees.
Final summary/delivery identify the tested harness merge and next canonical step.

## Terminal union verification

Fresh complete harnessWindows2813=2790PASS/23SKIP/0ERROR/0FAIL, exit0.437 source,
config, test and native patch artifacts are byte-identical before/after. All427
preexisting source files unchanged.15 offline receipt tests are part of this
total, not15 native launches. The23 old platform/opt-in skips were not rerun.
Native adapter27 Windows methods, response24 methods per platform, and separate
Linux lock comparison remain distinct actual scopes. Full upstream native suite
NOT RUN. No artifact merge activates the native pin or work/listener routes.
74 original parent evidence blobs preserved; final local static follows.
