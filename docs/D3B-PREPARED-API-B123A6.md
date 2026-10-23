# B123A6 - prepared-only native runner and three-store API join

One existing CallerOwnedRunnerState and one existing BorrowedAPIStores now share
an explicitly prepared native GatewayRunner and the exact caller state/replay/
response objects. The optional prepared_runner= keyword selects this path; the
real APIServerAdapter constructor finishes its attachment internally. Default
bundles still reject any arbitrary gateway_runner through borrowed_runner_conflict.
No second owner, scheduler, native registry or connection is introduced.

## Qualified boundary

Prepared runner creation supplies the exact native SessionStore local epoch scalar
and path-keyed map once. Every prepared selection checks their original object and
values against the accepted epoch. No epoch increment, database write, recovery
or backfill is performed by this attachment. The runner/authority remain draining/
retiring, with no capabilities or served profiles. Actual work admission is closed.

The join checks original owner/authority/descriptor, profile, canonical response
binding, three native connection identities, paths, file inode/application IDs,
native locks, and absence of active transactions. No new SQLite or raw database
open occurs in the observed construction/selection/detach boundary. Existing caller
preflight/schema validation and mount protection are NOT conferred by this join.
Identity checks are cooperative momentary observations, not cross-database atomic
snapshots or a capability against arbitrary same-process mutation.

API must detach before runner. Pending tasks/work counters, open transactions and
changed owners refuse without cancellation, rollback, native repair or store close.
After awaited API resource cleanup the same prepared state and three connections
are checked again. An incomplete cleanup becomes CLOSE_UNKNOWN and cannot be
silently retried; runner ownership stays retained. Normal detach leaves all three
SQLite handles and the profile owned by the caller. Only caller code closes them.
No abandoned-construction recovery is claimed: the one-shot pair is retained.

## Regression discovered beyond initial success

Initial native20/20 passed but missed service-state drift after construction.
Two additional native methods failed5 assertions on _running, app/site/HTTP-runner
objects and pending work. The single helper now validates closed-service fields
and the existing native quiescence checks on EVERY selection and after cleanup.
The same assertions, unchanged, pass in current22/22. The initial results, failing
result and old helper/QA bytes remain historical. Independent A123C6 reproduced
broader counters/real-task cases; its exact final acceptance is merged separately.

## Actual execution and limitations

Current native00222/22 PASS with real GatewayRunner, SessionAuthority, SessionDB,
replay, ResponseStore and APIServerAdapter. Native methods/classes are not replaced.
One deliberately substituted empty memory-cleanup object is an explicit failure
fixture, not the normal path. Real asyncio tasks/locks/SQLite fault data exercise
retention. All22 temporary profiles are removed and ownership/registry/tasks
cleared by fixture cleanup. Watched success/refusal queries are SELECT/PRAGMA only,
with zero new connection/raw database open/row changes. Caller construction of
initial fixture stores happens before the watched boundary and is not zero-I/O.

Existing unchanged R122 native28/28 compatibility also passes this source. It
checks prepared runner behavior, not28 additional three-store scenarios. Seven
offline harness receipts bind source, results and scopes, not additional native
executions.501 actual join imports and467 compatibility imports were independently
matched against immutable native commit. Neither package calls model/provider,
opens a listener, proves full agent execution or Linux isolation.

The native optional version probes attempted7 Git subprocesses and one IPv6bind;
test audit denied all and records callers. Do not claim zero attempted operations.
Windows event loop was initialized before audit. Existing SQLite DELETE fallback
warnings remain; no dependency/interpreter upgrade was performed.

## Artifact and operational provenance

Native feature1e97dd617b81120255304e472ce322befcdb9ccd extends6b8124ab in4 files.
Patch/config are STAGED_NOT_INSTALLED; vendor/source locks remain unchanged. Fresh
patch application with the ORIGINAL base .gitattributes produces the tested bytes,
and duplicate application is refused. The first isolated patch fixture omitted
that file, inherited Windows CRLF conversion and failed byte equality; it is
retained. Product/patch bytes did not change to correct the fixture.

Own new native checkout initially timed out leaving an empty unopened index lock;
its owner verified exclusive OS access, preserved the stale file and restored only
that new baseline tree. No reset-hard/clean, existing user-file overwrite or change
to parallel worktree. Original failed setup receipts remain described in status.

New full combined harness regression follows immutable implementation/independent
QA union. Focused/native/static results alone do not claim that gate. No installed
feature, main/push/CIqueue/production/account/root/WSL change. Earlier tool blocks
were not replayed; C120P9 remains HOLD outside executable selection.

Next: integrate this prepared graph with existing NativeStoreStartup and profile/
mount lifecycle, qualify current-source actual work/observer transition, and only
then explicitly qualify active HTTP/admission. Complete runtime, broker accounting,
fullD3B, cross-store recovery and power-loss safety remain open. Borrowed listeners
and ordinary service guards are still closed, not bypassed by this attachment.
