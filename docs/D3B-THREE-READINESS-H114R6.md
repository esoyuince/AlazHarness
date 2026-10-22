# H114R6 - explicit three-store diagnostic HTTP readiness

One optional extension to the existing StorageReadinessHttp and existing
NativeStoreStartup; no second parser, listener implementation or store owner.
Base0be65aa. Installed native source lock/gitlink is unchanged. Native cc16c10
is exercised only in copied owned lab fixtures, not installed into production.

## Selected contract

StorageReadinessHttp(..., response_ready=True) requires a trusted response
expectation before any start. Default selection still rejects a three-store
startup; truthy strings/integers are not accepted. Construction captures the
exact expectation object and its live-check fields. Changes before startup
fail before storage effects. The constructor does not create/open any store.

After normal three-store startup, the service binds only when a read-only
pair -> response -> pair observation succeeds. All three native objects and
connection identities, the same response expectation, caller ownership and
writers are checked again after the observation. The response verifier is the
existing one, with constructor=False: legitimate prior response writes are
not confused with constructor migration. Pending response identity still
revokes readiness; this deliberately is NOT healthy/busy work-serving policy.
There is no multi-file atomic snapshot or hostile-same-process/ABA guarantee.

Status and responses label the optional mode
native_three_store_quiescent_readiness_only. False authority flags stay false;
only authenticated GET /health/live and /health/ready exist on127.0.0.1.
Liveness never inspects storage or claims it is ready. Any readiness failure
irreversibly revokes this service lifecycle, even after the fixture is repaired.
Shutdown remains the original single path: withdraw, drain HTTP, then native
startup closes response/replay/state. Unknown HTTP cleanup or active response
transaction retains the stores/profile; no rollback/reopen/automatic retry.

## Actual native acceptance

native001 is a NEW ordinary-UID23001/GID23003 P71C run after final exec with the
existing Landlock policy, genuine patched Hermes stores and actual aiohttp.
It uses no native class or HTTP factory replacements. A separate provisioner
closes each fresh profile before startup. Native feature and transported pure
dependency hashes are independently matched to their prior trusted inventories;
279 native files were reread against exact feature Git,108 HTTP dependency
sources match pinned installed-package records. No package install/download.

Four scenarios cover wrong response schema (0 parent writable SQLite connects,
no port or epoch), occupied requested port (3 opens and a reported epoch effect,
no blind retry), real three-store serving, and a fresh process reopening the same
profile. The two positive lifetimes keep all three inodes and response content;
epoch advances1->2. This is process restart, NOT a new mount/remount experiment.

While serving, explicit QA inserts an unresolved key ONLY into response_store.db.
Ready200 changes to503; deleting that QA row does not restore readiness. The
canonical pair stayed otherwise healthy: this proves the third store is actually
included. Wrong/missing/duplicate auth, Origin/Host/body/method/path checks retain
their earlier rejection behavior and agent routes stay404. An active response
transaction blocks native close AFTER the HTTP listener closes; only explicit
fixture rollback permits the second close and caller profile release.

Audit observes exactly3 parent native SQLite connections and0 new connects or
raw DB opens during HTTP probes. All child processes exit, no forced cleanup,
owned temporary code/data is removed and tokens are absent from captured logs.
94 nested assertions in4 scenarios are not94 independent end-to-end runs.
No root/mount, full network/IPC projection, model/provider or native agent API.
The existing optional early-source-check refinement was not reordered/replayed.

## Other verification and source history

21 new boundary-double lifecycle methods plus30 existing HTTP and18 existing
startup methods pass69/69. Default protocol behavior also passes the original29
real TCP/aiohttp methods on Windows, with explicit storage/profile DOUBLES.
Six new offline native-receipt methods check source identity and raw results;
they are standard-suite subsets and do not rerun native HTTP. Full current-source
regression is recorded separately after terminal completion, not inferred here.
23 old platform/opt-in Windows skips are not a new Linux acceptance.

One older L113 receipt compared its original HTTP bytes to the new implementation
and correctly failed. It now explicitly verifies the saved executed039bc source,
its baseline pin and all unchanged inputs. Original receipt bytes are untouched.
The NEW H114 receipt binds actual imported current code instead; no old success
is falsely claimed for the new implementation. The first mismatch is retained.

## Concurrent work and next boundary

T114R6A independently owns the finite third-file P102 selector and full-isolation
fixture. Its early duplicate HTTP draft was archived, and the agreed selected
HTTP is this exact frozen source7256a62. The earlier include_response draft is
also retained only as history; public keyword is response_ready, with no alias.
No change was written into the other task's worktree. Only a terminal current-
source full-isolation result plus fresh union regression can close that gate.
This ordinary-user HTTP success is not a substitute for mount/netns proof.

No installed native feature, work route, real agent listener, broker dispatch,
healthy/busy policy, cross-store recovery or power-loss safety is accepted by
this patch. Legacy IPCv2 remains closed. Production/root checkout changes,
CI queues, main and remote refs remain untouched. Complete regression/static,
scoped commit and exact continuation are recorded in status.md and summary.json.

## Terminal current-source regression and reviewed parallel limitation

Fresh complete Windows2945=2922PASS/23SKIP/0ERROR/0FAIL, exit0. All449 source
hashes and2 native patch hashes stayed fixed.444 of446 old sources unchanged;
only HTTP and one historical receipt binding changed, with3 new QA/test files.
This branch does not include the projection option or imply a combined suite.

The separate T114R6A native003 is terminal0 with45 parent and58/63 target
predicates. Independent read-only review matched473 transported sources,
including279 native Git files and identical HTTP7256a62; actual22 HTTP rows,
private200/hostECONNREFUSED, response-only503/restore503, three inodes/rows across
two full mount lifetimes and close ordering are consistent. No native rerun by
this review. Earlier two missing-transport failures remain failures, unmodified.

Its internal supervisor records no residual owned loops/fences/scopes and no
forced cleanup. A SEPARATE post-run root cleanup observation was tool-blocked.
That action was not reissued/bypassed, and independent cleanup remains unverified.
The accepted HTTP slice and recorded native experiment are not substitutes for
that independent check or a not-yet-run combined branch regression.

## Canonical HTTP-only local delivery

Tested code `e715c75aa7e6cf0680d3c3c13d7b88dbc9fc53d5` fast-forwarded from `0be65aaff452bb8a4416f4a684efa6818c76f04c` into the canonical development branch. All449 source files and two native patch hashes still equal the accepted full run. Final record is documentation/static only. The separately reviewed T114R6A projection implementation is not included by this delivery and its independently blocked cleanup observation stays unverified. Native source pins, main and remotes unchanged. Current status.md is the continuation.
