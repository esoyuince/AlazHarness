# L106E — read-only gate for live native Hermes store connections

Base: 7f17594b73c825d8e04873ab2db2a28fe49ab688.
Branch: alaz/d3b-native-layout-l106e.
Scope: one complementary live-connection gate; concurrent L106R owns finite
native profile layout and opt-in canonical projection. No second layout/runtime.
The initial unexecuted local layout draft is retained as an evidence snapshot,
not installed or shipped as product code.

## Product behavior

`gateway_live_store_gate.verify_live_stores` runs under the exact held native
ProfileLease, final ordinary UID and main thread. It accepts ONLY pinned native
SessionDB / RunIdempotencyStore objects and their real SQLite connection types.
Trusted per-run expectations carry separately prepared schema fingerprints,
store-instance UUID, state application generation, file identities and exact
runtime epoch/instance. They must not be learned from the same untrusted live
candidate; the schema_digest helper is for an independent provisioning phase.
They are not network/model fields or serialized launch capabilities.

The verifier acquires the native state/replay mutexes without waiting. A busy
mutex causes rejection, and cleanup releases ONLY locks acquired by this call.
It refuses active transactions, shared/native-readonly state, background token
writers, volatile replay fallback, foreign connection paths, extra attached
schemas, query-only connection policy, weak synchronous settings, unexpected
journal mode, schema/generation drift and unresolved work. Application-table
queries are qualified to main; native temp storage cannot substitute evidence.
Replay state must be bounded unambiguous JSON, not duplicate keys or nonobjects.
No statuses, SQL pragmas, epochs, records, schema, native source or files are
repaired or changed by this verifier.

Observations use existing SQLite connections and filesystem metadata. There is
NO raw open/close of database or sidecar files and NO new sqlite3.connect call.
This preserves native connection tracking and avoids cancelling process-owned
SQLite locks by independently closing another descriptor on the same file.
Before/after native profile, file and mount snapshots and SQLite data_version /
total_changes checks reject observed changes. The scope is cooperative startup;
malicious same-UID/same-process code and every possible ABA race are not solved.

A successful result is `NATIVE_STORE_CONNECTIONS_VERIFIED`, NOT permission to
start a Gateway listener or run work. It explicitly does not prove VFS handle-
to-inode association, write-capability of a substituted native handle, physical
media durability, pre-constructor validation, paired recovery or full D3B.
query_only=0 is checked but is not a claim about sqlite3_open's original flags.
A shared startup implementation must retain the exact trusted constructors and
connection identities; this snapshot is not an enduring capability.

## Genuine native experiment

Ordinary UID23001/GID23003 in approved P71C; fresh owned /tmp code/profile only.
No root, mount/namespace/account/service alteration, broker request, real model
or production state. Native Python sources match immutable Hermes
`eb75627faf532fa6ffbdae59a0d14b0b385fc780`; existing pure ruamel sources are pinned
separately, with no package installation/update or vendor edits.

A separate fresh provisioning process creates native schemas and expectations,
then CLOSES both stores and the native profile lock. A new process applies the
existing explicit own-mountinfo Landlock policy and execs the fixed QA target.
The target reacquires real ProfileLease and opens real native stores. The gate
executes BEFORE any epoch/admission mutation. Subsequent deliberate fixture
mutations exercise refusals, never native method doubles or rewritten SQL code.

Positive tests compare prepared schema/UUID/application/file pins. Negative
checks cover wrong expected schema and epoch, native memory fallback, weak
sync, query-only policy, active transaction, running replay, duplicate status
keys, pending admission and temporary-table shadowing. Rejection leaves native
profile ownership and caller transactions/records intact. Fixture cleanup is
explicit QA work; the gate never deletes or completes the rejected work.

For lock preservation, the native state connection holds SQLite EXCLUSIVE mode
through a COMMIT while in_transaction is false. A separate process gets actual
SQLITE_BUSY before the gate AND after it. Only after the native state/replay
connections and profile are closed can a new competitor BEGIN IMMEDIATE and
roll back. That is a real interprocess lock test, not a mocked file lock.
Audit hooks observe zero raw database opens/new SQLite connections inside the
gate. SQL traces contain only observation statements; total_changes is stable.

This test uses genuine native stores and final-exec Landlock, NOT the entire
P102 mount/network/cgroup projection or the full Hermes HTTP runtime. It does
not establish pre-constructor safety for unidentified existing state. The
external image/profile layout and cold preparation responsibilities are separate.

## Bugs found during qualification

1. A JSON document with repeated status keys could be classified using one key
   while the native parser sees another. The failing test is retained, along
   with the old module and native001 proof. The query now rejects duplicate
   keys anywhere in a bounded JSON tree, malformed/nontext/nonobject input and
   unknown states. A new complete native run followed this product change.
2. Temporary tables could shadow unqualified schema, epoch and work queries
   even though main.sqlite_schema matched the expected digest. A separate
   read-only review reproduced the false acceptance. Source edits waited until
   the preceding full run completed with unchanged source hashes. Five new
   regression cases reproduced the gap; all application-table reads now use
   explicit main qualification. Prior native/full successes remain historical;
   current-source native/full requalification is required and recorded separately.

The existing minimal projection policy, native files and historical receipts
are not weakened or rewritten. Product code changes belong to the new gate
only. The old blocked R91F/G82C operations were neither replayed nor bypassed.

## Unit versus native evidence

Unit methods exercise actual SQLite SQL against small owned fixtures, but the
native object identity, profile lease and Linux mount boundaries are explicit
doubles. They are not a genuine Hermes acceptance. Native receipts separately
prove exact upstream classes/connection types and existing metadata policy.
Offline receipt checks validate those raw outcomes and source hashes; they are
not additional Linux executions. Full Windows count and selected Linux repeats
must not be added together. Terminal counts will be recorded in summary.json.

## Remaining integration gate

Existing SessionDB constructors can create, repair or migrate database state.
This LIVE-only check executes after constructors and therefore cannot replace
read-only prepared-schema/ownership validation before opening unidentified
state. The next fixed startup path must compose the accepted finite native
profile layout, pre-constructor qualification, native ProfileLease, trusted
constructors, live connection gate and explicit epoch/recovery policy before
request readiness. Partial terminal pairs still require separate reconciliation;
this function must never be used as an automatic resend authorization.

The native layout is store-only, not arbitrary user skills/hooks/config. Future
profile extensions require explicit policy and fresh tests. Main remains the
published cc7ceba, and no push is part of this change. Legacy IPCv2 remains
closed; full D3B acceptance remains open.

Evidence: evidence/d3b-native-layout-l106e/.
Relevant external background, not execution evidence: official SQLite
howtocorrupt.html (POSIX advisory lock cancellation), pragma.html (database_list,
query_only, synchronous and data_version), and lang_naming.html (schema name
resolution). See those primary documents for general SQLite semantics.

## Final current-source acceptance

Native003 exits0 with8 parent conditions and37 overlapping child predicates,
including10 actual refusal cases. These are one controlled native scenario
with several negative subcases, not45 independent runs. The interprocess
SQLITE_BUSY/busy/then-success sequence is independently checked in receipts.
Only DELETE journaling was exercised with native Hermes in this lab; other
configured journal enum values do not imply additional native-mode acceptance.

Final full Windows2572=2549 PASS /23 SKIP /0 failures /0 errors, exit0. All393
source hashes stable before/after; ALL389 preexisting sources remain unchanged.
Current Linux selected55/55 PASS =50 SQLite/unit methods plus5 offline receipt
methods; all are subsets/platform repeats, not new native launches.23 existing
platform/opt-in tests remain skipped on Windows and were not rerun here.
The earlier full2567 was successful BEFORE main qualification and is retained
as historical, not substituted for current-source acceptance. Both newly found
bugs have retained failing regressions, original product snapshots and new
complete native/full runs. No old success receipt was edited.

Temporary code/data and owned processes were audited absent. P71C remains
available for the concurrent finite-layout work; this task did not terminate
it or change defaultUbuntu/CI/production services. Static outcome is recorded
separately in static-final.txt and is not a GitHub publication result.
