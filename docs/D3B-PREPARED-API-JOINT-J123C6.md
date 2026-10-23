# J123C6 - one prepared runner/API join with shared caller-owned stores

The original B123A6 native patch and independent A123C6 tests qualify one narrow
explicit construction/selection/detachment contract. They do not open a service.
Exact original commit and QA parents are recorded in inputs.json; complete
standard-suite results are recorded only once that new union run is terminal.
The immutable native feature is1e97dd617b81120255304e472ce322befcdb9ccd on6b8124ab.

## Explicit join, not a guard bypass

The already prepared real GatewayRunner uses the caller's exact native SessionDB,
instance and epoch. BorrowedAPIStores(home,state,replay,response,
prepared_runner=runner) validates that same runner/token/home/state and pins the
existing three native connections. APIServerAdapter's constructor completes the
attachment only after its native fields have been initialized. Positive tests
never set gateway_runner or install a private state handle after construction.
Default bundles still reject direct runner injection with borrowed_runner_conflict.
The listener connect guard and ordinary runner-service guard remain unchanged.

Preparation installs the exact local SessionStore authority epoch and original
single-path map. Selection rechecks the actual prepared authority/descriptor,
map identity and values, profile ownership, all three connection/path/file/
application identities and existing native locks. A wrong scope, equal-but-new
map, bool epoch, added foreign entry, replaced connection or changed generation is
not accepted. No extra SQLite open or registry acquisition, epoch bump, recovery,
maintenance, model call or worker is introduced by this contract.

The new join reuses BorrowedAPIStores and CallerOwnedRunnerState. It adds no
second scheduler, worker registry, storage owner or model/API dispatcher. Existing
native response canonical binding still points to the exact same state handle.
This is cooperative in-process object identity and lock validation, not an
adversarial capability system or atomic multi-file snapshot. Caller still owns
schema/cold preflight, shared-reader/writer coordination and mount validation.

## Ownership-preserving retirement

API must detach FIRST. A bound-but-unclaimed API bundle, attached adapter,
uncertain construction or CLOSE_UNKNOWN prevents runner retirement. Pending or
malformed work counters, an unfinished real task, active transaction in any of
the three stores or lock contention are refused without cancellation, rollback,
repair or caller close. The API rechecks the same prepared contract after its
awaited empty-memory cleanup. A deliberately injected cleanup failure retains
CLOSE_UNKNOWN and cannot be retried as if the first operation had no effect.

After successful API detach, runner detach retires only its facade/authority;
all three caller connections and the profile reservation remain usable. Closing
those databases and releasing the profile are still explicit caller obligations.
Idempotent facade detach does not imply safe repeated native work/admission.
No native HTTP app/site/server is started; no task admission is enabled.

## Genuine current evidence and corrected regression

Original native join22/22 and independent30/30 methods pass on exactly the same
four native files. A separate unchanged existing runner compatibility package
passes28/28 on that new native feature. These scopes overlap; do not sum them as
80 independent end-to-end scenarios. Original smoke1 and earlier successful20/27
runs belong to their exact historical source and are not extra current evidence.

The additional prepared-service checks found a real missing invariant after
construction. Original2 methods failed5 assertions; independent3 parent methods
failed11 assertions. A running flag/service object or new pending work could be
accepted by selection. The sole helper correction now requires the API to remain
closed and uses the existing native quiescence check every time, including after
awaited cleanup. The SAME independent QA bytes then pass30/30. All original
failure logs and before-source snapshots remain intact.

Tests use actual native GatewayRunner, SessionAuthority, APIServerAdapter,
SessionDB, RunIdempotencyStore, ResponseStore, locks, profile ownership and asyncio
tasks in fresh Windows temporary homes. Native product methods are not replaced.
One independent test replaces an empty memory-cleanup object solely to inject a
failure; it is not genuine HTTP resource teardown. Explicit malformed fields and
transactions are fixture faults, restored/rolled back by test teardown only,
never by the observer/product to manufacture success. No model/agent computation.

Watched construction/selection/detachment executes only SELECT/PRAGMA and observes
zero new SQLite/raw DB opens or row changes. All test homes, pending tasks,
profile ownership and registry counts are clean after fixture teardown. Exact
imported native Python source hashes are tied to immutable native Git plus the
four changed sources. Third-party/runtime versions were not upgraded. Optional
native version Git subprocess probes and urllib3 IPv6 feature bind were DENIED
and retained; zero attempted diagnostic activity is not claimed. Windows event
loop self-wakeup setup occurs before audit, not as a native listener permission.

Original default control at6b8124ab confirms the unqualified runner conflict with
same caller state and no epoch/row effects. Its missing local epoch map is
recorded, not fabricated. The independent index-only clean patch application
produces the ENTIRE exact native commit tree and refuses duplicate application;
its private index is removed afterward. Original patch fixture initially inherited
CRLF because native .gitattributes was omitted; failed custody proof remains
recorded, and the corrected fixture applies the unchanged patch exactly.

## Union/full-suite and runtime boundaries

One new complete harness standard run must cover the immutable implementation and
independent QA union; offline receipts are subsets, not additional native trials.
Full source/patch manifests before and after bind the result to exact files.
All505 prior harness sources remain unchanged. Existing23 platform/opt-in skips
remain skips; full native upstream pytest is not performed. Local static checks
are not remote CI. Final summary/delivery carry terminal counts and canonical head.

This feature is STAGED_NOT_INSTALLED. Existing installed vendor/source locks and
main remain unchanged. No native listener, live provider/model or production
account is touched. NativeStoreStartup's actual profile/mount source-pinned owner,
new-source task observers, active work/HTTP, complete agent runtime and Linux
isolation are NOT accepted by this prepared construction. The next stage must
qualify that same real path before service/admission, not remove guards or fake
private field/epoch ownership. Broker live-ledger/dummy-provider accounting,
fullD3B and cross-store power-loss/recovery remain open. Legacy IPCv2 stays closed.

Prior tool-blocked cleanup/refinement and the C120P9 optional physical probe remain
BLOCKED/HOLD and were not replayed. No main merge, remote push, root/WSL/mount,
production/CIqueue or dependency change is part of this delivery. Both original
histories and raw evidence must be preserved through ancestry-safe integration.

## Terminal new combined regression

NEW complete harnessWindows3190=3167PASS/23SKIP/0ERROR/0FAIL exit0.512 source/
config/test hashes and7patch hashes stayed exact; all505 prior source files
unchanged. The same23 prior skipped method names AND reasons match the previous
complete log.86 original evidence Git blobs retained.14 offline receipts are
standard-suite subsets. This is the single new complete union run, not summing
old full/native packages. Local static result is recorded separately; no remote
CI, native feature installation or active service acceptance is inferred.
