# A128C6 - explicit native caller-owned admission and draining

## Delivery scope

Native feature1b7b31e14451baf1d56c3edbfa2cea69a8f7940c extends optional1e97dd61
in exactly5files. It is an inactive patch/config artifact, NOT installed Hermes,
not a promoted harness consumer envelope, not complete API/TurnRunner work.
Existing557 harness source/config/test files are unchanged. Native constructor,
profile ownership, SQLite stores, authority admission/claim guards and adapter
cleanup remain original actual classes/methods, with an explicit new lifecycle.

## One binding, explicit transition

The existing BorrowedAPIStores exposes activate_admission(), begin_drain() and
finish_drain(). The existing CallerOwnedRunnerState remains the phase authority:
PREPARED -> ACTIVE -> DRAINING -> DRAINED -> ordinary ordered DETACHED. No new
scheduler, work registry, store owner, connection or epoch. Native default
prepared behavior and ordinary service/listener refusal stay unchanged. Every
transition uses the original owner thread and event loop; active/drained cannot
be reactivated or reset to a fresh prepared phase.

Activation requires the same single-profile config and pair, three source-owned
connections, no open transaction, no unresolved native state/replay/response
records and no retained native work. It makes one no-await memory transition;
unknown failures retain ADMISSION_UNKNOWN with admission flags closed. Native
SessionAuthority._require_admission_open now also checks this explicit binding
phase. Merely flipping retiring/draining booleans does not activate a prepared
borrower. The original non-borrowed guard and default construction are untouched.

The existing native off-loop transaction callback checks current admission,
config, context-home, connection and authority identities without recursively
acquiring its already-held SQL mutex or querying SQLite. Closed response/replay
handles or foreign scope cannot pass merely because object pointers are the same.
The native original write still performs durable epoch/generation checks.

## Drain semantics and retained work

DRAINING closes NEW admission and NEW queued claims before any await, without
waiting for a transaction lock, cancelling work, rolling back caller transactions
or advancing epoch. Work that already crossed the original transaction guard can
commit; its accepted row must remain accounted for. Previously claimed native
rows may settle. Queued/unknown rows are never silently marked terminal, deleted,
replayed or promised to execute during drain. Existing exact leaf replays may
return their original record without creating work, per upstream semantics.

finish_drain() requires actual current native work registries empty and all three
ledgers settled. A cancelled asyncio waiter does not prove a worker thread stopped.
Retained native worker/session/task records are NOT pruned by this seam, even if
a Task is done. Their existing owner must legitimately retire them before finish.
In particular, whole API turns create live session entries; their retirement is
still a subsequent integration task, not fabricated by clearing dictionaries.

DRAINED is not a reusable release ticket. Current work/ledgers/storage identity
are checked again before API detach, after its awaited cleanup and before runner
detach. Late replay/response/work stops closure. A new replay during actual awaited
API cleanup, or cancellation while cleanup continues in a physical thread, retains
CLOSE_UNKNOWN and all caller-owned DBs/profile; a blind cleanup retry is refused.
Normal sequence is API detach -> runner facade detach -> caller closes the three
stores -> caller releases profile. No profile/state is closed by the lifecycle.

These are cooperative in-process ownership checks, not an atomic transaction
across files or protection against arbitrary hostile same-process mutation. No
extra await-held SQL locks or second admission scheduler were introduced.

## Executed native acceptance and corrections

Final native00446/46 PASS on Windows:24new admission/drain/race/cleanup methods
plus22 unchanged original prepared API compatibility methods. Actual native
constructors/SQLite/guard/claim/settlement/profile lease are used, not native
method mocks. Lower-level guarded native ledger writes exercise admission and
claim semantics but are NOT a full admitted agent/TurnRunner/API request. Explicit
test fixtures include paused guard/cleanup callbacks and inserted task/registry
records. Watched transitions add0SQLiteconnections/0rawDBopens/0SQLrowchanges;
actual admission/settlement naturally write their native rows outside that watch.
All46 fresh profiles removed, native ownership released, registry counts zero.
508actually imported native sources match immutable feature Git blobs.

First native00138/39PASS had a test envelope error: ResponseStore.put received a
top-level id rather than its existing response object, so it correctly refused
an unsettled key. Fixture-only correction led to39/39 on identical product bytes.
Five additional real native regressions all failed on candidate001: stale DRAINED
replay before API detach, late response before runner detach, changed config,
foreign active profile and closed response at the admission write gate. Same
expectations passed on candidate002; old QA/product/results are retained. Final
extra two real awaited-cleanup tests passed without further product change.

Independent Q128C6 separately reproduced4candidate001 failures and qualified
28methods on these exact5candidate002 hashes, including the original native
tracked_write shielding/cancelled-carrier behavior. The two native suites overlap,
not74 distinct cases. Independent raw records live in its own branch/evidence.
Our8offline receipt methods bind current source/patch/scope and failures; these
are not8new native executions. Full standard regression awaits the exact union.

## Patch custody and setup diagnostics

Patch0008 applies to1e97dd61 and reproduces the exact5tested Git/file hashes;
a second application is refused. The first miniature patch-application fixture
omitted native .gitattributes and inherited Windows autocrlf, producing ONLY CRLF
mismatches. Original failed comparisons remain saved; repeating on a fresh fixture
with actual base attributes produces byte-exact files without modifying the patch
or product. Native commit initially lacked identity; HEAD remained unchanged,
then existing harness Git identity was supplied per invocation, not globally.
No hook or signature control was removed, no Git reset/clean or force action.

## Not yet accepted / next

PreparedRuntimeConsumer and its513-source envelope remain at1e97, as do current
observer gates. Do not silently repin them or represent this native optional
patch as an active harness. Next explicitly integrate same-owner ACTIVE/DRAINING
with live task/SQL observation and native session retirement, then execute a
current-source admitted TurnRunner/worker test and the same path in Linux
seccomp/Landlock/network/filesystem isolation before active HTTP acceptance.
A prepared attach diagnostic is never admission authority.

No HTTP listener, full AIAgent/worker run, provider/model, root/WSL, production,
main/push/remoteCI or installed runtime/source-lock change. Old confinement remains
its exact historical source proof. FullD3B, model accounting and powerloss/cross-
store recovery remain open. Old tool-blocked operations/C120P9 are not replayed.

Records: config/hermes-admission-lifecycle-a128c6.json, patch under
patches/hermes/a128c6/, this evidence folder native004/source-custody/patch-
application, historical failures, current receipt tests. Read status.md for the
exact combined qualification and canonical delivery state.
