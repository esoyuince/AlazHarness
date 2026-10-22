# F111E274 — canonical storage-readiness HTTP under full isolation

Base:1e9c305afd3d02cbb56a74f9cce034c33a4609a9.
Feature:alaz/d3b-http-confined-f111e274.
Scope: close the previous full-confinement HTTP qualification gap using the
EXACT existing StorageReadinessHttp, NativeStoreStartup and state projection.
No new product module, HTTP parser, store engine, ingress grant or work route.

## What actually ran

The approved disposable AlazHarness-D3B-P71C lab was initially Stopped and the
named preflight started it; defaultUbuntu stayed untouched. Fresh fixed paths
/opt/alaz-f111e274, /srv/alaz-f111e274 and /sys/fs/cgroup/alaz-f111e274 were proven
absent BEFORE writes. A root controller created and formatted one new64MiB
regular image, not a physical device or an existing disk. It reused the fixed
reviewed supervisor and selected broker installation without changing either.
No operating-system account/service/CI configuration was provisioned.

Two NEW worker mount lifetimes and final-exec target processes used real ext4,
hostUID23001/GID23003, empty supplementary groups/capabilities, no_new_privs,
seccomp, private mount/network/IPC namespaces and the current Landlock policy.
Host user namespace is deliberately retained; this is not a hostile host-root
boundary. Only the dedicated finite native profile subtree is persistent;
scratch stays private/ephemeral and ambient host paths are not exported.

In EACH target, the real native ProfileLease is acquired after exec. A wrong
schema goes through the actual HTTP startup and refuses before a listener or
new epoch; closing that failed lifecycle retains caller profile ownership.
Then the real canonical HTTP.start calls the same native storage lifecycle:
finite layout -> separate read-only preflight -> immutable Hermes constructors
-> live verification -> clean-only new epoch -> live verification -> HTTP bind.
No production method, storage owner or live boundary was mocked in this run.

A real authenticated local TCP request reaches /health/ready with200. While
that listener is still alive, the controller in the HOST network namespace
tries the SAME reported port and receives ECONNREFUSED. PID/port are bound to
the child's earlier positive HTTP observation. The child then serves200 again.
The test does not expose a new host forwarding/proxy socket; external ingress
is still a future separately authorized integration responsibility.

Each lifecycle records11 raw response bodies/statuses:200 ready,401 wrong key,
401 invalid UTF8 bearer bytes,404 closed work route,404 query alias,405 mutation
method,200 after host probe,200 after explicit fixture settlement,503 after
intentional epoch drift,503 even after restoring the old value, and200 process-
only liveness. Tokens are synthetic random values and absent from logs. There
are22 responses over two lifetimes, not22 independent system acceptance runs.

Native fixture work uses unchanged SessionDB/RunIdempotencyStore/runtime APIs
and is explicitly settled by the QA, not dispatched to any provider. After
complete process exit/unmount/loop detach a new mount/exec retains DB inodes,
store UUID/schema pins and native record IDs. Startup epochs1->2 are observed;
the same native request/key is reused, not a second executed job. A deliberately
unfinished new record in the second lifetime blocks another storage startup
before epoch3 and remains started, not erased/replayed/reconciled.

HTTP.close stops its listener first but refuses native storage shutdown while
a real SQLite transaction is open. The transaction and caller lease stay held;
the closed port is independently probed inside the private namespace. Explicit
QA rollback then permits the SAME HTTP lifecycle to finish native close. The
native profile lock remains held until the outer caller releases it. A real
other process cannot acquire it earlier, but can after release. Even then a
still-alive confined process keeps the supervisor image lease retained. Only
reaping users, unmounting and detaching the loop releases that image lease.

Existing positive host controls and target refusals cover unrelated TCP,
abstract/path Unix sockets, broker siblings, protected canary access, inherited
descriptors, hidden broker private config/budget and absent host state paths.
The ONLY selected broker socket works:2 authenticated pings,0 physical provider
attempts. Existing broker private file hashes/inodes and the controller's mount
table remain unchanged. No firewall or credential policy was relaxed.

## Source custody

All420 original project source/config/test/script files stay byte-identical.
The three new QA entrypoints adapt the already-reviewed A109 QA, with distinct
fixed fixture paths and added actual HTTP checks. Native payload includes276
immutable Hermes Python sources matched to no-replacement Git objects at
 eb75627faf532fa6ffbdae59a0d14b0b385fc780. Existing ruamel sources and108 pure
HTTP dependency sources retain recorded hashes; HTTP package RECORD hash/size
checks were independently repeated. No package download/install or upstream
modification. Actual imported-module hashes and chunk digests are captured.

The primitive projection receipt truthfully describes its EARLIER phase: its
own native-store-opened/HTTP fields remain false, as it executes before native
startup. The NEW final-exec target and parent records prove subsequent stages.
Likewise the Landlock subreceipt does not independently certify network
isolation; real namespace comparison and TCP positive/negative controls do.
These historical/phase-specific fields are not rewritten to widen old claims.

The original scoped result enum PASS_SCOPED_NATIVE_STORE_LAYOUT is retained in
the adapted QA protocol. Acceptance additionally requires the NEW explicit
readinessHttpUnderFullIsolation flag and actual HTTP/identity/order/source
observations. A PASS string alone is insufficient. The offline verifier checks
these raw facts and mutated copies, and never grants runtime launch authority.

## Validation and counts

Actual native001 exit0:44 parent controls; first target49/49 and second54/54
predicates. These overlap and are NOT147 separate trials. Both fresh mounts
and22 HTTP responses completed in that one two-lifetime experiment.
Existing selected Linux startup contracts27/27 PASS; those tests have their
original explicit boundary doubles and are distinct from the native run.
New12 offline receipt/mutation methods pass on Windows and Linux. They check
source matching, native provenance, cleanup, HTTP revocation, host refusal,
PID/UID binding, persistence and scope. Corrupted receipts are refused. Platform
repeat and selected methods must not be added to the complete Windows total.
A NEW complete suite is required, with425 source hashes frozen until terminal;
its terminal count is recorded below and in full-windows-result.json.

Independent cleanup observes no own process, socket, anchor, cgroup, fence or
loop attachment, and empty unmounted mount directories. Image and installation
remain for evidence. The shared lab is not terminated (parallel F111X84 review
exists); all OUR owned processes have exited. That independent branch was read
for coordination only; its uncommitted work was not overwritten or merged.

## Limits and next gate

This accepts the existing DIAGNOSTIC readiness HTTP lifecycle inside the full
canonical isolation. It does NOT start Hermes APIServerAdapter or native agent
HTTP listeners, route work, send a model request, establish healthy/busy semantics
or reconcile partial store pairs. The direct native fixture records do not
constitute a model/task execution. Physical power-loss and paired atomic
recovery are not tested. LegacyIPCv2 remains CLOSED; fullD3B remains OPEN.

Next review one borrowed-native-store/ResponseStore lifecycle and healthy/busy
readiness policy before enabling actual work routes. Preserve the validated
startup/close ordering and namespace boundary. Then qualify the broker live-
ledger/dummy-provider send/accounting path. Do not redispatch unknown work or
pretend the local-only diagnostic port is host-accessible production ingress.
No main merge, remote push, production settings or existing CI queue changes.

Evidence: evidence/d3b-http-confined-f111e274/.
Continuation: status.md; previous handoff in docs/status-history/f111e274-parent.md.

## Terminal complete regression

NEW fullWindows2747=2724PASS/23SKIP/0ERROR/0FAIL, exit0;425 source hashes unchanged before/after. All420 baseline sources remain exact.12 new offline receipt methods are included in the full total and repeat onLinux;27 existing startup contracts also ran onLinux. These are not new native trials or additional full-suite counts.23 old Windows platform/opt-in skips were not rerun as a group. Native001 completed on its first full execution with44 parent and49/54 child predicates. Static outcome follows in static-final.txt, not remote CI publication.
