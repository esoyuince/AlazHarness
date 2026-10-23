# J115W6 - one work-health policy with existing-handle native reader

The original combined reader commit and the independent policy review are
recorded in inputs.json. There is ONE gateway_work_health decision core and ONE
gateway_work_health_reader; neither is a new scheduler/store owner or recovery
engine. No existing startup/quiescent HTTP or isolation implementation is changed.

## Scoped behavior

Complete fresh storage-verified snapshots may classify no active work as IDLE,
matching separately observed live owners as BUSY, and latched normal drain as
DRAINING. Ownerless/unknown/stale work, wrong generations/runtime identity or
uncertain shutdown require RECONCILE_REQUIRED. Stale, incomplete, malformed or
contended evidence is UNOBSERVABLE; an active transaction is not silently rolled
back to obtain a healthy answer. Reconciliation and drain latch in the policy
session. Transient unobservability can be reconsidered using fresh evidence.

The same live SETTLING owner may retain terminal admission/run/response records
until it finishes. If that owner disappears before linked records settle, the
system does not call the partially finished work idle or replayable. One active
executing/settling owner is supported; delegated workers are explicitly rejected
until their live adoption contract is qualified. Queued native generation is NULL.
Every public decision denies admission, retry and store-release authority.

The reader uses already-open genuine state/replay/response handles and their
native mutexes. It bounds returned inventories, parameterizes identity queries,
uses main-qualified SQL, checks schema/runtime/handle and observed version
stability, and keeps terminal rows referenced by the supplied owner inventory.
It performs SELECT/PRAGMA only, without new SQLite connections, raw database opens,
writes, commits, rollbacks, retries or closes. Row-count limits are not a hard
latency bound on scanning historical records; no cross-file atomicity is implied.

## The live trust boundary is still OPEN

The native reader returns committed metadata, not proof of task liveness or
verified profile ownership. It deliberately cannot mint complete/storage_verified/
task_alive/healthy flags. Run scope/key/fingerprint and response fingerprints are
metadata, not independently verified request identities. A future adapter-owned
collector must obtain actual Task/process/phase/request identity under an owner
revision barrier, verify profile/mount/storage, call this reader, and recheck the
revision/handles. Supplying caller booleans or reconstructing live tasks from
pending database rows is NOT accepted. No HTTP endpoint was wired to this policy.

## Actual tests and preserved source provenance

The original W115B6 NEW complete standard run executed3022 methods:
2999 PASS,23 SKIP,0 errors,0 failures. Its461 before/after source hashes and both
existing patch hashes match this merge exactly. All454 prior sources remain
unchanged; the seven source additions are two modules plus focused QA/tests.
This review only adds source-custody and documentation. It re-ran49 selected
methods (37 pure +12 offline receipts); it did NOT repeat or sum full suites.

The B115 native-data fixture executed16 methods with real native stores and API
transitions. The W115 native reader executed28 methods, including native data
mapping, active transaction/mutex refusal, no extra opens/writes, safe terminal
selection, JSON bounds/duplicates, parameterized IDs, TEMP shadowing and wrong
ownership/generation. These fixtures overlap and are NOT a single44-case run.
Native source imports from both experiments were independently matched to
immutable Git blobs at featurecc16c10. No native classes were replaced.

Crucially, both native fixtures supplied live-owner/task/process-start/storage
verification as EXPLICIT TEST DATA. They do not prove actual agent task capture,
HTTP readiness or full-isolation active-work health. Temporary profiles were
removed and native ownership released. No native upstream full pytest was run.
The original23 platform/opt-in standard skips remain skips, not fresh acceptance.

The early independent reader policy draft and43 tests remain historical, not a
second implementation. Its first native22/23 result is preserved: an uncommitted
fixture settlement was rightly refused. The corrected fixture explicitly commits
its own change; the reader never auto-commits. The policy test-source surrogate
write failure also remains recorded. Neither first outcome is rewritten as PASS.

## Delivery boundaries

Original parent evidence Git blobs, native results, source snapshots and both
histories are preserved. Only status.md conflicted and both previous handoffs are
archived. Local static validation follows in static-final.txt; it is not a remote
CI or live-runtime result. Installed vendor/source locks/native patch activation,
main and remote push remain unchanged. No WSL/root/mount/provider/model/account/
production/CIqueue action occurred. Prior cleanup/refinement blocks remain OPEN
and were not retried via another tool or route.

Next: the real adapter-owned producer collector and independent request binding,
then genuine task-lifecycle/isolation acceptance before active-work HTTP wiring.
Existing strict cold and quiescent gates stay selected. Full D3B, actual native
agent listener, broker live-ledger/dummy-provider dispatch and cross-store
atomic recovery/power-loss safety are not accepted by this foundation.
