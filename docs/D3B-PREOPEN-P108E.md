# P108E — cold read-only native store preflight

Base: d24f8d2654c4a866445bf0b3d1e31f085ca34de7.
Branch: alaz/d3b-preopen-p108e.
The existing P107A constructor metadata prerequisite is reused unchanged.
This task adds one fixed separate-process preflight and its parent wrapper.
It does not replace native Hermes stores, their ownership implementation or
SQLite. Original P107E has no product implementation and remains untouched.
Parallel S108E is a separate in-progress alternative, not silently adopted or
merged into this path. Canonical promotion must first check concurrent state.

## API and trust boundary

`gateway_store_preopen.verify_preopen(held, expected_mount, expected)` requires
an actual held ProfileLease, exact ExpectedMount and independently prepared
PreparedStoreExpectation. Expected schema digests, UUID/application generation,
file identities and runtime epoch are trusted local startup configuration,
never learned from the same unidentified candidate or model-provided fields.

The parent launches only the installed scripts/run_store_preopen.py in a fresh
isolated Python interpreter (-I -B). It passes no inherited descriptors, keys,
PYTHONPATH or user configuration, and no caller-selected command. The exact
bounded stdin request and response are bound by SHA-256 plus parent/child PID
and final UID. Worker timeout kills and reaps only the owned helper. A refusal
leaves the native profile reservation and caller resources intact.

Parent operations observe lease, identity and mount; parent never opens a raw
DB descriptor or a new SQLite connection. This matters because the inspection
helper closes its files in a separate process, rather than disturbing the
parent's process-owned SQLite advisory locks. Actual interprocess verification
of that boundary is recorded below, not inferred from a code comment.

## Worker policy

The fixed worker never imports SessionDB or RunIdempotencyStore constructors.
It accepts only the two exact existing files under the private canonical home,
with the expected owner, inode/device, single link and0600 mode. Files have a
512-byte minimum and256MiB maximum. It reads the SQLite header and bounded full
content hash before and after. No symbolic path ancestors or links are adopted.
The parent requires the final ordinary Linux identity and still-held native
profile. Worker requires matching real/effective/saved UID/GID and parent PID.

Only cold DELETE-mode databases with SQLite read/write header versions1 are
supported. ANY declared journal/WAL/SHM sidecar, even empty or a dangling link,
refuses with explicit-recovery-required. No sidecar is deleted or replayed.
The SQLite connection uses mode=ro with NORMAL locks and timeout0; never
immutable or nolock. A busy or recovery-required DB fails rather than bypassing
locking. query_only and trusted_schema restrictions, disabled extension loading,
finite SQL/field limits, a VM/time progress budget and a read-only authorizer
restrict queries. Additional file-size/time bounds prevent unbounded inspection.
The trusted installed worker itself is in the local runtime trust boundary.

The helper checks the independent main.sqlite_schema digest BEFORE querying
application tables. It then checks quick_check, schema31, app ID, persistent
store UUID and exact epoch/instance; all application tables are main-qualified.
On that SAME query-only state connection it invokes the unchanged P107A marker
prerequisite: backfill complete and no known constructor-repair flags. No SQL
write, migration, epoch advance, native constructor or listener is invoked.
Before/after file hashes, metadata, directory snapshot and parent identity must
match. Atime is intentionally not a frozen field because a read may update it.

The return value is a cooperative cold snapshot, NOT enduring launch authority.
It cannot detect every ABA race or defend against a malicious same-UID/host-root
writer that ignores the lifecycle. Finite native layout and external image
ownership remain caller responsibilities. Known repair flags being absent is
not proof that every constructor side effect is absent; native clean opens may
still write. WAL/recovery/large profiles need their own explicit acceptance.

## Actual Linux sequence

The approved disposable P71C laboratory, ordinary UID23001/GID23003 only, used
fresh /tmp/alaz-p108e-* profiles and pinned native sources. Separate preparation
created real native schemas and trusted expectations, then closed the stores
and native profile lock. A new target applied the CURRENT unchanged Landlock
metadata policy, exec'd, and acquired actual native ProfileLease.

That target called the fixed preflight BEFORE opening the real native stores.
The successful helper exited and was reaped; the target then constructed actual
SessionDB and RunIdempotencyStore and ran the existing live-connection gate.
Both preflight and live checks observed epoch0; no admission/epoch was advanced.
This is a genuine preflight -> native open -> live check in the QA entrypoint,
not yet a product HTTP startup entrypoint or the full P102 namespace lifecycle.

Native002 passed37 overlapping target predicates with9 explicit refusal cases:
wrong schema digest, wrong expected epoch, old native version, known repair
marker, missing backfill, present sidecar, nonprivate file, symbolic file, and
an actually locked candidate. Each applicable refusal compares full DB bytes
and metadata before/after and verifies the native lease remains held. Fixtures
are explicitly created/restored only by QA code; the gate never repairs them.

For the lock test, the native parent holds an EXCLUSIVE SQLite lock after
COMMIT. A separate competitor observes SQLITE_BUSY. The readonly helper then
refuses the locked database; after its raw reads/connections close, the same
kind of competitor STILL observes SQLITE_BUSY. Only after native connections
and the profile close does a competitor acquire and roll back. Parent audit
reports zero raw DB opens or new SQLite connections during preflight calls.
No raw parent snapshot is taken while its live SQLite lock is held.

Native source pin: eb75627faf532fa6ffbdae59a0d14b0b385fc780. The276 native Python
and31 pure dependency files reuse the independently verified source inventory;
no vendor method, package install, model, network service or provider is changed.
No privileged UID change, mount or image setup occurred in this task. The test
covers final-exec Landlock and true native storage, NOT complete network/mount/
cgroup projection, paired transactional recovery or physical power loss.

## Failures retained and accounting

Native001 correctly rejected a symbolic file in the existing PARENT mount
observer, before the worker. The QA expected the worker's later rejection code
and failed. Only that expected bounded code was corrected; product bytes are
identical across native001/002. The fresh complete second run passed. The first
stderr/exit1 and original QA source are retained. A separate offline receipt
fixture used a field named run, shadowing unittest.TestCase.run; the field was
renamed without weakening assertions or changing native records. Both failures
remain inspectable.

29 real-SQLite unit methods use explicit doubles for native lease/mount/process
boundaries. They are NOT genuine Hermes runs.5 offline native-receipt checks
bind the actual successful scenario to current source and immutable upstream.
These34 methods pass on Windows and ordinary-user Linux. Platform repetitions
and native predicates do not add to the full test count. The complete new
Windows result and408-source freeze are recorded after terminal completion.
All403 existing source/config/test/script files remain unchanged.

Cleanup audit found no owned temporary profile/code directory or matching live
process. Shared P71C is not terminated because another task is using it. No
CI queue/config, default Ubuntu, accounts, services, production, public main or
remote refs are touched. Old blocked R91F/G82C operations are not retried.

## Remaining integration

Compose this preflight with the accepted finite cold native layout and image
ownership in one fixed product startup path. Preserve the native lease across
preflight, trusted constructors, live verification and an explicit non-dispatching
recovery decision. No unknown/partial pair may authorize automatic resend.
Then qualify that SAME call path under full P102 isolation and real Gateway
readiness, followed by broker live-ledger reading and fake-provider dispatch.
Neither this snapshot nor a successful helper receipt is an HTTP launch grant.

The implementation is in gateway_store_preopen.py and run_store_preopen.py.
Current state: status.md. Evidence: evidence/d3b-preopen-p108e/. Original parent
status is retained in docs/status-history/p108e-parent-d24f8d2.md. Keep ongoing
status short; final summary records exact commits/tests/publication state.

## Final qualification

NEW complete Windows2662=2639 PASS /23 SKIP /0 ERROR /0 FAIL, exit0.
All408 source/config/test/script hashes are unchanged before/after; ALL403
existing files remain unchanged. Linux selected34/34 PASS (29 SQLite methods
with explicit native-boundary doubles plus5 offline receipts). These are
subsets/platform repeats, not additional native runs. The23 old platform/
explicit-opt-in skips were not reexecuted by this task.

Native002 is the current-source successful execution;37 nested predicates and9
refusal cases belong to one controlled scenario. Native001 remains a failed
QA expectation run, not relabelled successful. Product files stayed identical
across those two runs. All native temporary profiles/code/processes are clean.
Final local static follows in static-final.txt; it is not remote CI or release.

## Canonical local delivery

Tested code `382afe4bf48f2cc883b23b4249dd6c4ad887ba22` fast-forwarded from `d24f8d2654c4a866445bf0b3d1e31f085ca34de7` to the canonical development branch. The feature remains clean and retained. All408 sources match full/native evidence; this follow-up changes only documentation/static delivery. S108E alternate runtime is not merged or overwritten; canonical selects one helper pair. Maincc7ceba and remote refs unchanged. No full HTTP readiness or full-projection acceptance is implied by local promotion.
