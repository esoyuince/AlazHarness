# S124B1 - prepared runtime as consumer of original store startup

The ONE NativeStoreStartup remains the sole owner of all three native databases.
This integration adds an explicit prepare_runtime(config,api_config) consumer,
not another storage manager, scheduler or automatic recovery path. Original
startup construction/cold gates/accepted epoch order and native source pins stay
unchanged; a fixed separate source envelope qualifies the optional1e97 prepared
consumer. Installed vendor/source locks and ordinary service guards are unchanged.

## Original close gap and implemented invariant

A real-native Windows comparison showed original startup.close closed all three
connections while its manually attached prepared API remained ATTACHED and runner
PREPARED. That previous integration seam was not close-aware. The native functions
were real; Linux actor/lease/preopen/mount/permission evidence was explicitly
doubled. This is not a claim about a deployed active service or full Linux path.

New prepare_runtime reserves its consumer on the ORIGINAL owner before native
consumer imports/constructors/awaits can affect anything. The original close()
checks exact consumer type/state and refuses while it is reserved, constructing,
attached, partially detached or has unknown outcome. A convenience wrapper alone
could not enforce this; the guard sits in original NativeStoreStartup.close.

The consumer pins original state/replay/response objects/connections, accepted
epoch expectation object, caller lease/mount and one event loop. Real GatewayRunner,
SessionAuthority and API constructors use those handles and the accepted epoch.
No fourth SQLite connection, second epoch, recovery or private post-eager rewiring.
It reuses native prepared bundle/runner guards and existing SQL/schema/live gates.

Explicit detach orders API -> runner and revalidates after awaited API cleanup.
Only then can ORIGINAL owner close response/replay/state; external caller finally
releases the lease. Consumer never closes a store or releases a profile. Known
pre-effect transaction/busy refusals leave it attached and may be reobserved after
caller resolution. Constructor failure or an exception after cleanup begins is
terminal FAILED_UNKNOWN/CLOSE_UNKNOWN and cannot be silently retried or repaired.

Two deliberately added regressions caught post-detach drift: persisted epoch
change and a real newly pending runner Task. Initial20cases18PASS/2FAIL are retained.
Final close now reruns current live SQL checks plus native runner/authority work
inventories and retired identity, not merely a cached DETACHED label. The SAME20
QA methods/bytes then passed. It does not cancel the task, rollback a transaction,
reset a row or discard a native registry to manufacture safe close.

## Source and lifecycle scope

Fixed config/prepared-consumer-s124b1-sources.json has513 native Python source hashes
independently matched to immutable feature1e97. A hardcoded digest protects the
manifest bytes. Those files are read before consumer constructors; the loaded
native module set is checked afterward as well. All501 native imports in this
actual run match the fixed envelope and immutable Git. This covers the tested
prepared constructor envelope, not all optional modules/external packages, runtime
code-object attestation or hostile same-process mutation. No old storage/task
hash is relabelled as new-feature active-work acceptance.

Storage validation still expects the original epoch/schema/profile evidence.
Windows NativeFixture replaces only Linux actor/lease/layout/cold/mount/permission
boundaries; actual startup constructors/epoch advance/native state/replay/response,
SQL live gates, prepared runner/authority/API and final store close are real.
Schema expectations are fixture provisioned before reopening. No Linux cold
helper, real mount or confinement acceptance is claimed by this Windows run.

## Executed checks

20/20 current actual-native Windows consumer cases PASS. Same3handles/epoch and
reverse ownership teardown, slot before effects, duplicate prepare, constructor
and source failure, actual pending tasks, all3transactions, loop identity, source
envelope, unknown cleanup, manual detach without acknowledgement, awaited drift
and final epoch/work retirement refusal are tested. Positive watched preparation/
detach performs SELECT/PRAGMA only with zero new SQLite/raw database opens/row
writes. Explicit fault tests replace a constructor boundary, an empty cleanup
object or an awaited test boundary; they are NOT normal-path native substitutes.

8 unit methods cover owner reservation/default-pair/actor/type/failure behavior
with explicit dependency doubles.7 offline receipt methods preserve exact source,
failed-first-result and cleanup scope.83 focused methods include these15 plus
45 original startup lifecycle doubles and23 historical native receipt checks;
they are not83 genuine native runs or additional full-suite successes.

All fixture homes/profile ownership/registry counts were cleaned. Product UNKNOWN
states are recorded before isolated test teardown; fixture close is not presented
as successful product recovery. Optional native versionGit/IPv6 import diagnostics
were DENIED and retained, not zero attempted diagnostics. Existing SQLite DELETE
warnings remain. No dependency or interpreter upgrade, provider/model call or
service/listener activation. Windows framework loops were created before audit.

Three old native/Linux receipt tests now hash their exact saved pre-consumer
startup bytes, with strict base/hash matching; all other source checks remain.
Old raw receipts were not edited. They prove their HISTORICAL executed source,
not the new close-aware runtime. The current20 native cases are separate evidence.

## Remaining acceptance

This is source-qualified prepared integration under explicit Windows boundaries,
not active service. Updated-source task observers, actual admission/task semantics,
real cold preflight/profile/mount and same-path Linux isolation must be accepted
before any active-work HTTP/native agent listener. Cooperative caller serialization
is required; no cross-store atomicity, process-hostile capability or universal
writer inventory is claimed. FullD3B/broker live-ledger/dummy-provider accounting
and power-loss recovery remain OPEN. LegacyIPCv2 CLOSED; C120P9 extra probe HOLD.

Parallel C124L1 owns independent QA, not another implementation. Original mutual
scope-cede notes are retained and final S124B1 ownership is explicit. No other
worktree is changed. No main/push/installed native/CIqueue/production/accounts or
root/WSL changes; previous blocked actions are not retried. One fresh combined
full harness suite and canonical delivery follow only after exact QA union.
