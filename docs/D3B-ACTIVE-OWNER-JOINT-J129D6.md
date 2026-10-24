# J129D6 - local admission on the original harness store owner

## Integrated boundary

The existing NativeStoreStartup owns the same three native connections and accepted
epoch. prepare_runtime(..., local_admission=True) reserves its same existing
PreparedRuntimeConsumer, choosing a fixed517-file native1b7 source generation.
The default prepared1e97 generation and old513-file manifest remain unchanged.
No automatic selection, mixed native generations, extra store owner or scheduler.
The consumer forwards explicit activate_admission/begin_drain/finish_drain to the
existing native bundle while retaining matching harness and native phases.

The new small helper separates phase-specific operations; it does not own state,
connections, tasks or timers. Forged flags/native phase advancement do not become
successful harness activation. A changed or unknown partial native transition
retains ADMISSION_UNKNOWN and the original consumer slot; no blind retry/close.
This is tested integration of LOCAL admission, not live service activation.

## Observe identity while work exists, require clean state for release

ACTIVE/DRAINING observations may contain pending queued/unknown/replay/response
records. Two existing read-only validators have an explicit strict boolean
require_idle=False mode with DIFFERENT NATIVE_*_IDENTITY_OBSERVED states. It keeps
schema/header/epoch/actor/lease/path/inode/mount/connection/journal/retention checks.
It does not evaluate task health, capacity or release authority. A transaction or
held mutex can still make observation unavailable rather than falsely healthy.

All constructor/startup/default/finish/detach/store-close paths remain clean-only.
Response constructor mode cannot opt out of cleanliness. Original owner close
still requires current detached consumer, absent real native work and clean SQL.
The normal order is API -> runner -> original stores -> external caller lease.
No row is deleted, worker cancelled, registry pruned or connection reopened.

Withdrawal itself does NOT require SQL/writer idleness: identity checks precede
the native gate seal without taking the held writer mutex. A pre-guard blocked
writer is refused after drain. An already-authorized native tracked writer can
commit after its caller was cancelled; its accepted queued row and original owner
remain retained. finish fails until native obligations are resolved. Queued/unknown
work is not automatically run/recovered/discarded by this integration, and native
FIFO/session retirement remains a separate acceptance boundary.

## Actual test scopes, compatibility and evidence

Current original-owner native23/23, independent frozen-source native24/24, and
unchanged original20 prepared compatibility cases PASS on CURRENT harness code.
Current23/24 use immutable native1b7; compatibility20 uses old1e97 through the
unchanged default. Counts overlap and must not be summed as67unique scenarios.
Actual NativeStoreStartup/consumer, native constructors/profile ownership,
authority/API/three SQLite handles and SQL guards are used. Windows Linux actor/
lease metadata/layout/mount/cold helpers are explicit doubles. Named callback or
memory-cleanup faults are test barriers, not unstated production replacements.

Real mutex/cancelled tracked-write tests preserve commits and ownership. Independent
awaited-cleanup/cancellation tests retain CLOSE_UNKNOWN and all handles. Current
native imports514/514 and default501 match distinct immutable native manifests;
12 independent loaded harness modules match the exact current product/baseline.
Watched transitions read no raw DB files, create no SQLite handles or row changes.
All successful fresh fixture profiles and ownership/registry references are cleaned;
fixture cleanup of retained obligations is not product drain completion.

7pure/doubled contracts and15offline receipt methods(7+8) are standard-suite subsets,
not extra native runs. Historical426receipt checks initially produced18 source
assertion failures after code changed. Exactly11 named old runtime/test files were
archived against baselineffa0d36 and original expected hashes; same426 nowPASS.
No original raw result/expected hash or old kernel execution was rewritten/replayed.
The fresh complete standard result belongs to this union only, recorded separately.

## Remaining acceptance / delivery

No current-source Linux confinement, complete API/TurnRunner/agent task, HTTP listener,
provider/model or production activation. runtimeAdmissionAuthorized remainsFalse
for full runtime readiness; localAdmissionOpen reports only the explicit local gate.
The normal native service/start paths remain refused. Native feature1b7/source
locks/vendor installation are unchanged; new generation is selected only by the
explicit owner option in these tests. Full accepted-FIFO/session retirement,
request/physical-worker correlation, cross-store recovery/model budgets/powerloss
remain open. Old Linux isolation pertains to its historical tested source.

Both immutable implementation and independent QA histories are preserved. The only
merge conflict is status.md, with parent histories archived. Initial merge guard
stopped before effects when peer made a docs-only checkpoint; refreshed source
identities verified unchanged before the actual merge. No peer index or root user
changes were overwritten. One exact-source full regression owner only. No root/
WSL/install/main/push/remoteCI or historical blocked-operation retries.

Next exercise native accepted FIFO/session ownership to completion with actual
request/physical-worker correlation, then qualify that exact combined path under
existing Linux isolation and active HTTP before service activation. See status.md,
summary.json and final delivery.json for terminal counts and canonical commit.

## Complete regression and test-fixture correction

First complete standard3365 ended3341PASS/23SKIP/1ERROR, exit1. The old pure work
contract built PreparedRuntimeConsumer via __new__, bypassing its constructor and
omitting _local_admission. Isolated13cases reproduced the same AttributeError.
The fixture now explicitly initializes the real defaultFalse; all13test method
ASTs and expectations are unchanged. No product/native/source-manifest change.
Original fixture bytes, failed raw full output and diagnosis remain preserved.

A FRESH complete run after that single fixture setup change completed3365=
3342PASS/23SKIP/0ERROR/0FAIL, exit0. Current results are final-full-*; first failed
full-* records are not relabelled.572 current source/config/test hashes and8patches
stable, same23skip IDs/reasons. Prior563:551unchanged,12changed(4runtime,7historical
source receipt/helpers,1unitfixture),9new files.67original evidence Git blobs
preserved. This full does not replay native/kernel experiments. Local static
runs on this final source, not remoteCI or an upstream native full-suite claim.

## Canonical delivery

Tested union `001ca5e2e5b4fcf5929a44b964ad4eb7a1c1d300` fast-forwarded from `ffa0d366b505848718f4e10f044af19350a4d947` into the development continuation. All572source/config/test hashes and8unchanged native patches match final full3365. Delivered22checksPASS(7pure/doubled+15offline) are included standard subsets, no new native run. Native1b7/source locks are not installed or changed; default1e97 unchanged. Final handoff adds documentation/evidence only and validates those changed documents with bounded credential-pattern/JSON/Git checks. Whole local static was PASS on the tested merge; no remoteCI/fullnative claim.
