# J113Q8 - verified cold response state in the single native startup lifecycle

## Scope

R113Q8 supplies the cold response-file preflight; L113F6 supplies the live handle
check and opt-in extension to the existing A109 NativeStoreStartup. They are one
path, not two runtimes or competing store owners. Native feature cc16c10 remains
a separately tested source export: the installed vendor and source lock are not
promoted. No real agent HTTP listener or work/provider route is activated.

## Startup and ownership

The optional response expectation pins the exact native schema and feature,
response device/inode, and fixed constructor bounds. It must originate in trusted
provisioning. An old or unknown file is never used to teach the checker its own
expected schema. The finite layout admits the third database and its named
sidecars only when explicitly selected; the default two-store layout still
rejects that extra file. Cold preflight rejects every sidecar rather than trying
journal recovery.

Both ordinary state/replay preflight and the response preflight finish before
native writable constructors. The parent reads metadata only; separate bounded
interpreters use normal SQLite read locks, mode=ro, query-only, untrusted schema,
no extensions, limited authorizer and finite query budgets. Wrong file identity,
permissions, schema or version, unsettled response identity, malformed/orphan
records and constructor eviction pressure stop the start without repairing or
creating files. Before/after bytes and metadata must remain exact.

After the canonical state/replay constructors and their existing live check, the
selected response source is checked and the real ResponseStore receives the SAME
live canonical connection. Response live observations happen before and after
one clean epoch advance. They check native types, exact path/mount/schema, caller
binding, active transaction absence and zero response row changes at constructor
time. This remains cooperative ownership, not hostile same-process attestation.

On shutdown all returned connections are checked for active transactions before
any close. Response closes first, replay second and canonical state last. The
caller, not startup, releases the native profile/image lease after successful
close. Replaced handles, unconfirmed constructor effects and uncertain close
retain ownership and cannot be blindly retried. Open transactions are not silently
rolled back. No new independent profile manager is added.

## Actual execution and its limits

The standalone cold check has 44 real-SQLite/explicit-parent-double methods on
both Windows and ordinary Linux, plus 6 offline source/receipt methods. A separate
real native P71C run uses actual native stores and ProfileLease, fixed subprocesses
and a competing SQLite process: 47 overlapping checks, including 13 refusal cases.
It proves the helper does not discard the parent's exclusive SQLite lock and the
parent opens no raw database descriptor or SQLite connection during preflight.
Its populated response bytes survive a qualified actual native reopen unchanged.

The integrated L113F6 native002 run uses real native classes in new ordinary-UID
processes. Nine target cases cover clean three-store startup, a fresh-process
reopen, the unchanged two-store control, five early response-file refusals and
canonical pending work. The clean and reopen cases each have 16 checks; the
control has 8, each early response refusal 7, and canonical pending 8. Their 83
nested predicates are not 83 separate test runs. Clean/reopen retain all three
file inodes and response expectation and advance the epoch from 1 to 2.

Early response-file rejection occurs with zero parent SQLite opens and unchanged
bytes of all three databases. Canonical pending work is a DIFFERENT later case:
the existing canonical constructors have already run. Exact epoch/admission rows
and replay/response bytes remain unchanged, but state.db metadata bytes can change.
The first integrated run's broader byte-purity assertion failed and remains in
evidence. Native002 retains a narrower honest check and the raw before/after
observations. This is not a claim that all native constructors are side-effect-free.

The native response feature source check currently precedes only the response
constructor, not both canonical constructors. An optional refinement to move it
earlier was blocked by the tool; it was not retried through another tool or
encoding. The accepted source and native002 proof remain unchanged. No additional
native003 experiment is claimed or required for the documented existing scope.

## Evidence custody and regression

Actual integrated native files were independently reread from immutable feature
Git: 279 native Python sources, the transported current harness files and pinned
existing dependencies match. The cold helper and tests match their separately
qualified source hashes. Historical two-store mount/HTTP proofs bind exactly to
saved original versions of the three changed modules; they are explicitly
HISTORICAL, not falsely reused as current three-store confinement results.

The complete combined standard Windows suite runs on 446 frozen source/config/
test files and the two unchanged native patches. Relative to the 434-file base,
427 files remain exact; the intentional edits are three runtime integration
modules and four historical receipt bindings. Twelve new files implement the
cold/live checks, fixed worker, native probes and tests. Final count/result and
source equality are recorded only after the full run is terminal. Selected
methods, offline receipts and platform repeats are not added on top of that total.

## Remaining acceptance gates

Current two-store StorageReadinessHttp explicitly refuses a response-configured
startup; otherwise its old readiness predicate could misleadingly certify only
two of three stores. The native borrowed agent listener remains refused too.
Actual full namespace/mount/remount and HTTP acceptance of the NEW three-store
path is not tested in this ordinary-user trial. A legitimate in-flight healthy/
busy policy is not implemented by cold checks or busy-close refusal.

The next gate is that same three-store path under the canonical isolation and
readiness ownership contract, without granting extra directories or weakening
old defaults. Then qualify the native adapter, healthy/busy policy and broker
live-ledger/dummy-provider accounting before any installed-pin or work activation.
Cross-store outcome equivalence, atomic recovery, unknown-partial replay and
physical power-loss safety remain unaccepted. Legacy IPC v2 stays closed; full
D3B stays open. No main merge, push, production/account/CI configuration change,
package installation, root or mount operation is part of this integration.
