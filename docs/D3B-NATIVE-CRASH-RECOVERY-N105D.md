# N105D — Independent native-store crash/replay/epoch qualification

Base `30604dfcbb53d76b24bcf2a21996828d18afca49`.
Branch `alaz/d3b-native-stores-n105d`; ordinary-user QA only.
Native Hermes pin `eb75627faf532fa6ffbdae59a0d14b0b385fc780`.

## Result boundary

This work replaces dummy-table reasoning with actual unmodified Hermes
SessionDB, RunIdempotencyStore, runtime epoch/admission functions, and native
ProfileOwnership. It does NOT connect those stores to the final confined
Gateway startup path, implement a new admission adapter, or repair an old
R91F/G82C blocked operation. The concurrent H105E worktree is preserved.

Each platform executes eight independent crash/reopen scenarios and one real
unavailable-disk fallback case:17 child process lifetimes. Windows and Linux
repeat the SAME eight scenarios; these are not16 different scenarios. The
first child of each case exits73 with os._exit, deliberately skipping database,
profile-lock and Python finalizers. The next child uses the real native lock
and opens the original two files. No storage method or SQLite engine is mocked.

| Crash boundary | Native admission after restart | Replay reservation after restart |
|---|---|---|
| Before reservation | Absent | Absent |
| After INSERT, before COMMIT | Absent | Absent; original transaction rolled back |
| Reservation committed, before admission | Absent | Original running reservation retained |
| Native admission queued | Queued | Original running reservation retained |
| Native admission started | Unknown | Original running reservation retained |
| Admission settled, replay status not updated | Terminal | STILL running: actual two-store gap |
| Both terminal updates committed | Terminal | Completed |
| Running replay row with expired retention metadata | Absent | Running reservation NOT pruned |

The before-COMMIT case uses sqlite3's execution trace solely to terminate its
OWN child when the native COMMIT is about to execute. The INSERT and native
reserve method remain original. This timing injection is explicitly recorded;
it is not a separate mock storage implementation. The aged-running case
changes timestamps only on its own freshly created fixture row, then tests the
unchanged native retention path. No external run is executed in any case.

Every reopened native SessionDB advances epoch1 to epoch2. An attempted write
using epoch1 is refused as stale_epoch and no stale admission row appears.
Only an admission that was actually started becomes unknown; a second recovery
pass is idempotent. Claiming unknown work refuses with unknown_execution rather
than automatically executing it again. Retrying a committed request preserves
the original run ID and owner PID, a changed fingerprint conflicts, and a
lookup in a different scope is missing. Native schema tables and SQLite
integrity checks are verified using the already-open SQLite connections.

## Two explicit NO-GO interpretations

A terminal SessionDB admission plus a still-running idempotency record is a
REAL observed gap between separately committed databases. The QA passes only
because it detects the gap without concealing it. That is not proof of paired
atomic recovery. A future fixed admission/recovery path must interpret the
native state explicitly and must not resend or release the reservation merely
because the old process died.

A real connect failure to an owned missing-parent path makes the native replay
store use process memory. durable is False, PRAGMA database_list has no file,
and no reservation is issued in that case. This branch OBSERVES that fallback;
it does not claim a production readiness check has been installed. Diskless
storage must not be accepted as durable Gateway startup by the next adapter.

## Actual environments and journals

Windows used the already prepared Hermes interpreter, SQLite3.50.4. Linux
used /usr/bin/python3.12, SQLite3.45.1, as existing alazgateway UID23001/GID23003
in the approved AlazHarness-D3B-P71C lab. Both actual native stores selected
DELETE journal mode. The native safety selection was not patched or overridden.
No WAL-mode acceptance, sudden power loss, kernel crash, storage flush guarantee,
physical-medium durability, HTTP request ACK or live provider test is claimed.

The process audit denies Python socket connect/name resolution and subprocess
creation inside the store child. Some optional native environment probes try
subprocesses and catch the denial; the blocked-attempt count and stderr are
retained. This is diagnostic QA, not an OS sandbox attestation. No Gateway
listener, model inference or provider call was started.

## Provenance without alternate native modules

Native modules use normal original package imports. A finder checks each .py
file's immutable Git blob identity BEFORE handing its original import spec to
the standard loader. It does not alter source text, replace native classes,
construct a fake gateway.platforms package, or pre-populate invented modules.
After the run, imported source bytes are checked again. The source checkout was
clean at the exact pin before/after the Windows run. All measured native module
hashes were independently rechecked against no-replacement immutable Git blobs.

Windows measured218 distinct Hermes Python sources across the17 children.
Linux measured210 native Hermes sources and29 actual ruamel.yaml dependency
sources. The transport supplied a bounded234 native-file closure,31 verified
ruamel Python files and the identical probe,266 files total. Not every supplied
file is necessarily imported. Linux colocates the ruamel namespace directory
under the import root for ordinary import resolution; its entries retain
ruamel.yaml0.18.16 installed-RECORD provenance, NOT Hermes Git provenance.
linux-source-custody.json deliberately keeps nativeGitSources and
 dependencySources separate. No package was installed or updated.

No raw database content hashing/open-close occurs while native SQLite writers
are active. Queries use the live SQLite connections. Source .py hashes, native
rows/status projections and captured process outputs are the evidence. Child
JSON stdout is retained as text; child diagnostic stderr is decoded as UTF8
with replacement and is not claimed to be an exact binary diagnostic dump.
The parent/bridge stdout/stderr streams are preserved as captured bytes. No user
credentials or personal profile were loaded.

## Isolation from other development

Only this branch's new QA scripts/tests, report and evidence are changed.
All382 pre-existing source/config/test/script files remain byte-identical.
H105E owns the concurrent native-store integration attempt; its code/state and
records are read-only to this work. No duplicate product runtime is added.
The old root worktree, original source checkout, default Ubuntu, accounts,
services, production and CI configuration are not changed. Main stays cc7ceba.

The Linux bootstrap ran as ordinary alazgateway, created only its new
/tmp/alaz-n105d-code-* temporary tree and nested owned profiles, and removed
both normally after all children were reaped. A separate ordinary-user audit
found no owned temporary root or live matching process. The shared lab is not
terminated while H105E may be using it. No root/mount/namespace/account actions
were issued by N105D.

## Reproducibility and evidence

The immutable-source manifest is prepared from Git ls-tree, not mutable file
names alone. The ignored scratch manifest can be reconstructed at the recorded
pin. Run the fixed QA with a NEW output, pinned source and matching manifest:

```text
<prepared-python> -I -B scripts/qa/n105d_recovery_probe.py --source <verified-native-source> --manifest <pinned-manifest.json> --output <fresh-result.json>
```

This is not an instruction to open a personal profile. The probe constructs
new owned marked temporary profiles itself and refuses a supplied child home
outside that fixture structure. Linux must use the existing test UID. Actual
transport bootstrap and exact source inventory are preserved in evidence.

Evidence folder: `evidence/d3b-native-stores-n105d/`.
Windows native result: native-windows-001.json, terminal-result JSON and raw logs.
Linux native result: linux-001-stdout.txt (outer receipt containing full native
record), terminal-result JSON and raw stderr. Source custody has separate
Windows/native and Linux/native/dependency records. Twenty-two offline tests
check exact raw/parsed correspondence, source pins, transitions and deliberately
mutated invalid claims. They are not22 additional crash executions.

The NEW complete Windows standard suite is recorded separately only after its
terminal result. No historical full-suite counts substitute for this run.
Legacy IPCv2 remains closed; actual confined native-store admission, two-store
recovery policy, full Gateway and live ledger/provider dispatch remain open.

## Terminal standard regression

NEW complete Windows suite:2485 total =2462 PASS /23 SKIP /0 errors /0 failures,
exit0. Result comes from unittest's result object. All386 source/script/test/
configuration hashes remain unchanged during execution; ALL382 baseline files
are untouched. The22 new offline evidence methods are included in that total.
The23 existing platform/opt-in skips were not rerun as unit groups on Linux;
the actual Linux eight-case native experiment is a distinct, explicit scope.

No product patch is inferred from this QA success. In-memory fallback refusal
in a fixed production admission path, native profile layout qualification,
final confined database connection opening and cross-store reconciliation
remain unimplemented/unqualified by this slice. Preserve concurrent H105E;
combine only terminal reviewed commits and run a fresh combined gate.
Final local static output is recorded separately and is NOT GitHub CI.

## Local delivery

Tested independent QA/evidence commit: `59fde69e3a91fbff95ed8a58cb5350753f5f8d4d`. Canonical was observed at `30604dfcbb53d76b24bcf2a21996828d18afca49`; it was not updated by this task. ConcurrentH105E also currently contains native crash QA rather than a completed confined connection adapter. Preserve its work and do not attribute either independent proof to that missing implementation. No push/main action. A documentation-only follow-up records final static and exact-source identity.
