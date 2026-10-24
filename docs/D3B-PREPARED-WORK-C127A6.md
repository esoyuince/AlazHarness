# C127A6 - prepared-work refusal before detach and retired-store close

## Concrete regression, not a new admission path

PreparedRuntimeConsumer.check() previously checked SQL and native object identity
but not the full known prepared runner/authority work containers. A live task
could pass check; detach then disconnected the API BEFORE native runner detach
rejected work, unnecessarily leaving CLOSE_UNKNOWN. Some independent mailbox
operations were not checked even at final original-owner store close.

The exact unchanged product reproduced 12 cases:2PASS/10FAIL/0ERROR. The earlier
first attempt's2PASS/7FAIL/3ERROR remains recorded: QA imported a worker helper
outside the existing513 prepared-source envelope. Product correctly refused that
import expansion. QA was corrected to inject a native worker record explicitly,
not to relax the source manifest. Tests still use actual native owners, SQLite,
asyncio Tasks and a real waiting thread, but task/worker records are deliberate
fixture fault injection, NOT actual admitted jobs or model/TurnRunner execution.

## Minimal shared check

One read-only helper checks source-qualified existing native runner and authority
containers before check/detach effects, after API cleanup awaits, and before final
store close. It creates no registry/scheduler/worker, opens no DB, prunes nothing,
cancels nothing and treats even retained completed/cancelled work as unresolved
until the native owner retires it. A cancelled API carrier is not physical thread
completion. physical_workers() is not called because it mutates the registry.

Known busy refusal now leaves consumer ATTACHED/API ATTACHED/runner PREPARED,
connections open and tasks untouched. Caller may naturally settle its work and
then detach; the checker never performs that settlement. Work arriving during an
already awaited cleanup remains CLOSE_UNKNOWN, not automatically retried.

A separate read-only reviewer identified three further task/payload families and
two retired identity gaps. All5 extra native cases failed on the first fixed
version; identical assertions pass after adding native bot receipt tasks,
completion inflight and notification batches, plus exact detached descriptor and
singleton/non-multiplexed registry checks. Historical delivered_stops records are
NOT incorrectly treated as live work. Existing live SQL quiescence is reused;
no new SQL schema or ownership table, no locks held across awaits.

This remains a cooperative per-call observation. It cannot prove absence of
unregistered work or prevent arbitrary concurrent same-process mutation. No
active-service/admission claim is made. Native source1e97, source manifest and old
canonical/TurnRunner observer restrictions are unchanged by this task.

## Tests and source custody

Final genuine-native Windows suite40/40=17new task/refusal cases+23existing native
consumer compatibility cases.13 explicit object-double unit contracts and8
offline source/scope receipts PASS. These are different scopes, not61 unique
runtime tests.501 actually imported native files matched immutable1e97 Git and
the original513-source envelope. All watched selection/refusal boundaries have
zero new SQLite/raw database opens/row changes.40 fresh test profiles removed,
registry counts0, native ownership released and no pending asyncio tasks.

The native fixture explicitly doubles Linux actor/profile lease/mount/layout/cold
helper boundaries on Windows. No current Linux namespace/seccomp/Landlock rerun,
physical power-loss test, completeAIAgent, HTTP listener, model/provider or active
borrowed TurnRunner was executed. Previous F126 confinement PASS belongs to the
pre-C127 consumer bytes and is preserved as historical, NOT relabelled current.

388 old receipt methods initially had6 source mismatches. Three exact pre-C127
files were saved from immutablee496 Git. A named-generation resolver composes the
prior F126 resolver, returning only the requested known generation, never broadly
accepting mismatches. Raw old results and expected hashes are unchanged.388/388
historical checks then pass; that is evidence integrity, not native replay.

## Delivery boundary

Own product change is only gateway_prepared_consumer.py; two existing receipt
helpers adapt exact historical source binding. O127B6 independently owns current
canonical/TurnRunner source selection and prepared attachment. Combine immutable
changes only, qualify attachment against this current guard, then ONE fresh full
standard union regression. No alternate implementation or peer working-tree edit.

Root user work, installed vendor, main and sources.lock stay unchanged. No push,
root/WSL/native activation/production or prior blocked-operation retry. Current
native/focused jobs terminal. Exact final source/full/static/commit acceptance is
recorded in status.md and subsequent union evidence, not inferred from counts.
