# B129D6 - local admission integrated into the original storage owner

## One owner, explicit selection, unchanged default

NativeStoreStartup.prepare_runtime(..., local_admission=True) reserves the SAME
PreparedRuntimeConsumer slot before native constructors or awaits. It selects a
separate fixed517-source manifest for native1b7b31e1. The old default remains the
exact1e97 prepared manifest, not a union that silently accepts mixed generations.
The new517 set is prior513 plus4 actually required native source dependencies,
all pinned to immutable Git blobs. This is source qualification, not a capability
for every future agent/HTTP path. Installed vendor/source locks stay unchanged.

Consumer.activate_admission(), begin_drain(), finish_drain() invoke the already
qualified native transitions on its existing bundle/binding. No new scheduler,
state owner, fourth connection, epoch or native patch. Both consumer-selected and
native phases must agree; calling native activation directly cannot masquerade as
a completed harness transition or authorize original-owner close. Consumer tracks
unknown partial native transitions and retains its original owner slot, never
retries construction/activation as if there had been no effects.

## Identity observation is not idle acceptance

Two existing live verifiers now accept explicit require_idle=False, with strict
boolean typing and DISTINCT NATIVE_*_IDENTITY_OBSERVED result states. All original
actor/lease/mount/schema/inode/header/connection/epoch/journal/retention checks
remain. Only pending-work cleanliness is not required for this identity snapshot.
The default and every constructor/startup/close path remain clean-only. A response
constructor cannot use identity-only mode. These snapshots grant neither work
health, ready capacity nor store release.

The selected consumer uses identity-only observation during ACTIVE/DRAINING so
normal queued/unknown/replay/response obligations do not masquerade as changed
connection identity. Transactions or concurrently held writer mutexes still make
snapshot inspection unavailable; no false healthy/busy claim is minted. The
withdrawal operation itself deliberately does not query/take the SQL writer lock
or require writers already idle. It rechecks actor/owner/source/native identity,
then seals native admission before the next write guard. Finish/detach/close
ALWAYS return to original clean gates and current native work checks.

A native tracked write whose caller was cancelled may still commit after drain.
The exact original owner stays retained throughout; accepted queued row remains
and finish refuses. A write waiting before its transaction guard loses to drain.
No rollback, prune, cancellation, automatic replay or FIFO execution is added.
QUEUED/UNKNOWN work still blocks finish; native session retirement and a complete
accepted-FIFO reconciliation contract are future work, not hidden by local PASS.

## Actual acceptance and explicit fixtures

Own23 real integration methods PASS with original NativeStoreStartup, original
consumer, native runner/authority/API and three actual SQLite connections. Cases
cover same handles/epoch, ordered API->runner->stores->caller profile release,
pending identity vs clean release, native bypass refusal, live transaction/mutex
withdrawal, native tracked-write cancellation, late obligation/epoch, wrong loop,
unknown native post-effect transition and service denial. Watched transition/
observation boundaries have0newconnections/0rawDBopens/0rowwrites.

Original20 prepared consumer methods also PASS with NEW harness modules and old
native1e97/default selection. Old scripts/test expectations were not weakened to
obtain compatibility. Source gate still refuses new1b7 under default selection.
Independent Q129C6 has a separate frozen snapshot/actual-native24method run; its
scope overlaps and counts are not summed as unique scenarios.

Windows Linux actor/lease metadata/layout/mount/cold-preopen helpers are explicit
fixture doubles. Native profile ownership, constructors, epoch and live SQL are
real. A designated post-native callback fault is deliberately doubled. Native
leaf admission/claim/settlement tests do NOT execute a complete API/TurnRunner/
agent task. All successful fixture profiles and native registry references were
cleaned; cleanup of unresolved fixture rows is not product drain completion.
Current native514 and compatibility501 imported sources match their distinct
immutable native commits. Native sources remain unchanged in this task.

Seven pure/doubled selection contracts and seven offline receipt methods PASS.
Historical receipt check initially had18failed source assertions across426methods,
because old results referred to previous runtime bytes. Those exact11named old
runtime/test files are archived against fixedffa0d36 baseline and expected hashes;
strict historical resolution now passes426/426. No raw result, expected digest,
old source or old kernel test is changed or rerun. New-source acceptance is the
new native runs, not old evidence. Historical helpers refuse unrecognized hashes.

## Remaining scope and integration record

No current-source Linux confinement, actual HTTP listener, full task observer,
full native FIFO/session retirement, cross-store recovery, power-loss or model
budget acceptance is claimed. Default runtimeAdmissionAuthorized remains False;
localAdmissionOpen is a narrower local-phase diagnostic, not provider permission.
The same source must pass those additional gates before a running service.

This task changes4 existing runtime modules and adds one narrow helper, one fixed
manifest, QA and receipts. Native patches/installed vendor/main unchanged. Prior
blocked actions/C120P9 were not retried. User root and peer worktree/index are
untouched. Final full-standard/static/delivery records belong to the exact union
and will be recorded by its SINGLE owner, not duplicated here. Continue from
status.md; raw new/native/default/old-failure evidence is in this directory.
