# B112X9 — opt-in native API borrowed-store lifecycle

This change is an explicit native fork patch, not a replacement gateway/storage
engine and NOT installed into the pinned production/runtime submodule. The
original Hermes pin eb75627faf532fa6ffbdae59a0d14b0b385fc780 stays selected.
Native feature commit and complementary parent are in native-commit.json;
config/hermes-api-borrow-b112x9.json carries exact before/after file hashes.
The A112X7D ResponseStore canonical-state patch is a prerequisite. Both patches
operate on disjoint native files and are applied/tested together in owned copies.

## One adapter, three caller-owned stores

APIServerAdapter accepts an explicit BorrowedAPIStores object instead of opening
its default response/replay stores. It reuses native run-state initialization
with the existing replay handle and selects the supplied SessionDB and response
object without lazy construction. No native factories are replaced globally.
Exact class/path/connection/canonical-state identity is checked at binding. Each
bundle is process/thread-bound, exact-home and single-claim. Different profile,
changed handle, foreign cache, closed connection or runner-authority conflict
rejects instead of silently reopening. Existing default constructor behavior
continues on the no-argument path and is tested separately.

The bundle is NOT a profile/image lock or a trusted prepared-schema proof. It
assumes the caller already owns/qualifies the three stores. It cannot protect
against malicious same-process mutation or a caller constructing duplicate
bundles. The current harness still qualifies only two persistent stores; this
new native seam cannot be activated until response_store.db is included in an
explicit third-store preparation/layout/preopen/live-validation contract.

## Shutdown without stealing ownership

Borrowed disconnect refuses active transactions, work counters or unfinished
tasks before making lifecycle changes. It does NOT trust the native convenience
work counter's exception-to-zero fallback. HTTP resources are stopped/drained
before detaching, then in-memory parked sessions are closed using the existing
native cleanup. None of the three supplied DB connections are closed, reset or
rolled back. Cancellation/failure makes cleanup state UNKNOWN and refuses blind
retry. Idempotent disconnect after successful detach remains valid even when
the real owner subsequently closes its stores. Detached selection never falls
back to opening a database.

Review exposed that the default _mark_disconnected helper schedules a runtime
status writer. The borrowed-only branch now updates its running flag without
that unqualified asynchronous profile write. The default unborrowed path remains
unchanged; its status writer is explicitly flushed by test cleanup. Work routes
have not been started, so this is not yet a general draining/in-flight-work policy.

Borrowed connect() explicitly refuses BEFORE the native listener or routes can
start. This guard is intentional until prepared third-store ownership, fixed
request admission and healthy/busy semantics are accepted. It is not permission
to invoke the native work API or a claim that every direct internal method is
blocked against hostile in-process callers.

## Genuine native checks and comparison

27 Windows methods use the actual patched native APIServerAdapter and actual
SessionDB, RunIdempotencyStore, ResponseStore in fresh owned profiles. Constructor
and selection/close paths are observed with SQLite-connect audit hooks. The
borrowed paths open ZERO additional connections. Real caller transactions remain
active on refusal; caller handles survive successful detach. Cancellation and
unknown cleanup use clearly labelled fake HTTP-resource awaitables, not fake
SQLite/native storage classes. No HTTP listener/model/provider starts.

All309 native Python modules actually imported in the successful run were matched
byte-for-byte to the combined native Git commit. Five modified source files are
explicit patches, not mislabeled as unchanged upstream. Third-party/native
Windows dependencies are from the existing prepared interpreter; a full clean
Linux APIServerAdapter dependency/confinement run is NOT claimed here.

A separate ordinary-user P71C Linux experiment compares original ResponseStore
with A112X7D canonical-state borrowing. Both paths keep the owner EXCLUSIVE SQLite
lock: competitors get SQLITE_BUSY before/after settlement and after response
close, and acquire only after canonical owner close. No upstream lock-corruption
bug was observed. The original creates an extra canonical read connection and
cannot settle under the owner's exclusive lock; the borrowed version uses the
same connection and settles the committed record without an extra open. An
uncommitted terminal row is explicitly refused without rolling back its caller,
and TEMP shadow tables cannot replace main-table evidence. Only fresh temporary
profiles, no root/mount/provider or production state.

## Failures preserved, not disguised

The initial response fixture forgot explicit BEGIN on native autocommit SQLite;
it failed before the uncommitted-state assertion. The fixture was corrected and
two new complete baseline/borrowed runs performed. The first Windows adapter
run was stopped before test setup by the audit denying the stdlib event loop's
local socketpair. That is now allowed only while unittest constructs its loop,
not for native API effects. A known optional urllib3 IPv6 import probe remains
DENIED; it is accounted separately from zero new network attempts in tests.

A subsequent run had two teardown failures (native closed connection becomes
None; default native status writer raced temporary cleanup). The borrowed status
side effect was removed, default test status is flushed, and current all27 tests
were rerun. Another result had27 passing methods but failed aggregate accounting
for the denied optional import probe; it remains a failed receipt. The final
run explicitly separates that denial without widening network permission.
An exact owned leftover status file was removed only after its originating
process ended and its filename/hash were verified. Final owned temporary profile
scan is empty. No original failed result is overwritten.

Initial own draft was archived when concurrent responsibility overlapped; the
other task then selected ONLY response-state borrowing, so this branch retained
the adapter seam as its complement. No alternate adapter is shipped. Initial
native commit failed for missing author configuration; the confirmed existing
harness identity was supplied per-command, without global/repo config changes.

## Acceptance boundary

Eight offline receipt/custody tests are standard-suite members, not eight new
native executions. The27 native methods and24 complementary response methods
are separately scoped; Windows/Linux repetitions must not be added as scenarios.
The complete upstream native suite is NOT RUN. One fresh combined harness
regression follows the union; selected proof does not substitute for it.

Installed vendor main, sources.lock.json, all427 existing harness sources,
production, CI queues/configuration, accounts/defaultUbuntu and published main
remain unchanged. No push or paid call. Next compose the single tested native
feature with a trusted persistent third-store lifecycle and healthy/busy policy
before updating any runtime pin or enabling work HTTP, then test broker ledger
and dummy-provider accounting. Full D3B/paired recovery/power loss remain open.
