# W115B6 - one work-state policy and committed native metadata reader

This continuation is additive on canonical9717704. Original B115 policy history
is integrated unchanged; W115 supplies the complementary native reader and an
independent real-native test fixture. No existing startup, quiescent HTTP, profile
or confinement implementation is changed. The installed vendor, source locks and
two optional native patches remain unchanged. No listener or task is activated.

## Decision contract

The single gateway_work_health policy classifies explicitly supplied evidence as
IDLE, BUSY, DRAINING, UNOBSERVABLE or RECONCILE_REQUIRED. A pending count alone is
never evidence of valid work. Current admission/session generation/epoch must
match a complete trusted live-owner inventory. Referenced run ownership uses PID
plus process-start identity; response identity must link to the same admission.

The first supported scope is at most one executing/settling owner globally plus
bounded queued work. Native delegated-worker rows are explicitly NOT qualified:
nonterminal worker state causes reconciliation, not a fictitious IDLE/BUSY pass.
A legitimate SETTLING task keeps its already-terminal admission and linked
run/response records visible until the same owner finishes. This avoids calling
partially settled cross-file work idle or silently replayable.

Known owner loss, stale generation/epoch or unknown work latches reconciliation.
Temporary missing/stale/contended observations remain UNOBSERVABLE and may be
observed again. Drain latches and never implies that stores can be released.
Every public decision denies runtime admission, retry and store-release authority.
This module is a pure local classifier, NOT a worker scheduler or recovery engine.

## Existing-handle reader

NativeWorkReader requires actual SessionDB, RunIdempotencyStore, ResponseStore,
three existing distinct native handles, the expected runtime identity and three
independently prepared schema hashes. It keeps the supplied native canonical
response binding, native mutexes, process/thread and declared paths pinned.
It does not use a lazy API that could reopen or borrow a new canonical connection.

The reader takes the existing state/replay locks without waiting, rejects any
active transaction or live native token writer, and performs only SELECT/PRAGMA
observations. It verifies the expected runtime epoch/instance/store UUID and the
supplied schemas through the existing live-connection helper. Main-qualified SQL
prevents temporary tables from hiding real pending state. Native connection
changes and observed total_changes/data_version drift cause refusal, not repair.

Active admissions/runs/unsettled responses are collected, along with terminal
records explicitly selected by the owner inventory. Selections use SQL parameters,
not embedded identity strings. At most256 rows per category are returned; one
extra row detects overflow and produces unavailable evidence. Replay JSON is
bounded to65536 bytes before transfer and checked for invalid/duplicate keys so
a forged terminal status cannot hide a running record.

The row bound limits returned data, NOT a hard upper bound on SQL scan time over
historical terminal records. Production latency/large-history behavior is not
qualified here. No transaction across all three files is opened; the sample is
cooperative, not a cross-file atomic snapshot or protection against malicious
code running in the same process.

CommittedWorkRows deliberately has NO storage_verified, complete, task_alive,
healthy, admission or release field. It carries rows, runtime/sample identity and
raw request fingerprints for a future trusted collector. The pure policy does
not yet compare those fingerprints against independently observed live request
payloads. A future adapter-owned collector must do that binding and bracket the
read with actual owner revision/task observations and profile/mount verification.

## Genuine Windows/native tests

The selected policy is verified by37 pure unit methods and the original B115
16-case native-data fixture. The independent W115 reader/policy integration runs
28 real-native methods against fresh, owned temporary profiles from immutable
featurecc16c10. Actual SessionDB, replay, ResponseStore, runtime admission,
claim/settle and worker-registry APIs are used; native factories/classes are not
replaced. The native source export is hash-locked and never installed.

The28-case probe verifies queued/started ownership, all-three mapping, terminal
owner settlement, drainage, stale epoch/generation/PID-start, unknown work,
orphan identities, duplicate/malformed/oversized JSON, TEMP-table shadowing,
wrong response linkage, inventory overflow and parameterized identity selection.
The native worker-registry case explicitly expects refusal of delegated workers;
no actual worker process is started. Existing transactions/mutexes remain owned,
caller connections stay open, and observed SQL is read-only with zero extra
SQLite connects, raw database opens or row modifications during observation.

Crucial limitation: live-owner task inventory, process-start value and the storage
verification flag in BOTH native fixtures are explicit TEST FIXTURES. They are
not proof of a working adapter-owned live collector, live-worker monitoring,
HTTP integration or full kernel isolation. Real databases do not make fixture
liveness flags real. The current quiescent HTTP behavior is intentionally unchanged.

## Preserved first outcome and one selected engine

An early independent policy draft and its43 passing pure methods are retained
only as historical evidence; it is not a second installed classifier. Its first
native run had22 passes and1 error: the QA invoked a private response settlement
helper without committing its transaction. The reader correctly refused an active
transaction. The updated fixture asserts that refusal and explicitly commits its
OWN change before asking for an idle observation. It does not weaken the reader,
add auto-commit/rollback or rewrite the original failure as success.

The source-identical final policy comes from original B115 commit3fae30d. Its17
original evidence Git blobs remain exact. Seven new offline receipt/selection
checks validate W115 source custody and actual outcomes; together with the original
five receipt methods these are standard-suite members, not new native executions.
Native16/28 scenarios have overlapping semantics and are not a single44-case run.

## Regression and environment boundaries

The new combined complete standard regression freezes461 source/config/test files
and two patch hashes. All454 preexisting executable/config files remain exact.
The old23 platform/opt-in skips are not newly executed in the Windows suite.
Native upstream full pytest and Linux/full-isolation work-health are not run.
Final counts are recorded only in the terminal full-windows-result.json.

No WSL, root, mount, provider/model call, existing user profile, runtime package
installation or native source-pin promotion is performed by this continuation.
Temporary native profiles are removed and their native profile ownership released.
The exported source fixture is retained under ignored scratch for reproducibility.
Earlier T114 independent cleanup remains BLOCKED; no blocked action was retried.
Main/remote push/CI queues/production/account configuration stay unchanged.

## Exact next acceptance boundary

Build the actual native adapter-owned producer snapshot: obtain complete live
Task/process/phase and independent request identity under an observation barrier,
read these same existing native handles, recheck the revision and profile/mount
identity, and reject stale, incomplete or concurrent observations. Do not derive
live ownership from the same database rows being judged or from caller booleans.

Then qualify the combined collector/policy with real task lifecycle transitions
and one active owner, using the existing confinement/startup path. Only after
that should a separately reviewed active-work HTTP status surface be wired in.
The existing cold/quiescent checks and native borrowed connect refusal remain.
No automatic unknown/partial retry, cross-store atomic recovery, power-loss claim,
actual native agent listener or fullD3B acceptance is granted by this phase.

## Terminal combined regression

Fresh fullWindows3022=2999PASS/23SKIP/0ERROR/0FAIL, exit0.461 source/config hashes and2 native patches stayed exact; all454 preexisting source files are unchanged.37 pure policy and12 offline receipt/selection methods are members of this total, not extra native runs. The28 reader and16 policy native-data cases remain separate Windows-only fixtures, with explicit live-owner/storage flags rather than live collector proof. Original17 policy evidence blobs remain exact. Local static output is separately recorded; remote CI/activation is not inferred.
