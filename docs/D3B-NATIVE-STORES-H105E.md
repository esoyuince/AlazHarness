# H105E — real native store crash boundaries and file-policy compatibility

Scope: independent QA on canonical30604df. No replacement storage engine,
new projection implementation, vendor patch or blocked R91F/G82C action.
Native Hermes pin: eb75627faf532fa6ffbdae59a0d14b0b385fc780.

## What was actually executed

The existing prepared Windows interpreter first imported the real SessionDB,
RunIdempotencyStore and runtime transactions in a fresh temporary home. It
created an admission, advanced epoch1->2, recovered started work to unknown and
observed unknown_execution refusal. This initial import/API discovery is not a
profile-lock/confinement qualification. Vendor working sources were then checked
byte-for-byte against immutable no-replacement Git blobs before Linux transport.

The final Linux native002 run used the ordinary dedicated UID23001/GID23003 in
approved P71C. Six owned child processes exited via os._exit(73) with no database
close, rollback, profile release or atexit. Six NEW processes reopened the same
owned per-case profiles, reacquired the real native ProfileOwnership lock and
inspected/used unchanged native APIs. No method was mocked or rewritten. Only
the pre-COMMIT case installs a line-trace timing checkpoint, pinned to the last
commit in the immutable reserve() function; the actual native INSERT/transaction
runs and the process exits before that COMMIT. This is not a power-cut, an OS
crash or proof about physical-media flushing.

| Checkpoint | Actual observation after fresh process reopen |
|---|---|
| Replay committed, no state admission | Replay reused, state absent; no admission synthesized |
| Both stores running/started | New epoch exactly+1, state becomes unknown, claim blocked |
| State terminal, replay still running | Contradictory outcomes remain; no silent rewrite |
| Replay completed, state started | State becomes unknown; replay completed does not authorize replay |
| Native INSERT before native COMMIT | SQLite rolls it back; one subsequent explicit QA reservation creates one row |
| Replay path unopenable | Native fallback is memory; record disappears and QA never starts an epoch |

The last row demonstrates WHY a production admission gate must explicitly reject
memory backing; it does not claim that such a new production gate was wired in
this task. Classifications requiring reconciliation are evidence conclusions,
not an implemented automatic repair policy. No effectful work was dispatched.

Raw records include both stores' rows, epoch/instance IDs, distinct process IDs,
profile lock inode, journal/synchronous values, actual imports and hashes. The
same admission ID, generation and old owner epoch remain across recovery; stale
epoch writes and old-epoch settlement are refused. Reusing the same request or
idempotency key cannot mint a second accepted row; changed payload/fingerprint
conflicts. Native database integrity checks pass in the ordinary-user recovery
runs. The final six-case evidence is native-002-stdout.txt; native001 remains the
first successful execution, not rewritten to add later raw fields.

## A concrete profile-layout gap

Actual native bootstrap also creates SOUL.md, cache/skills/session directories,
state.db.quarantine.lock and state.db.fts_rebuild.lock. Canonical30604df's cold
projection permits only the two DBs, gateway.lock and declared SQLite sidecars.
The observed inventory therefore does NOT satisfy that existing allowlist.
`projection-inventory-comparison.json` pins this comparison to the old source
hash; its test does not demand that future implementations retain the gap.
No profile files were hidden/deleted to fabricate success and no allowlist was
widened. A reviewed separation of prepared native state, native auxiliary files
and scratch is still required before a full confined detach/remount acceptance.

## Exact current Landlock compatibility experiment

Separately, two fresh ordinary-user exec cases used valid empty SQLite files,
real native ProfileLease and the actual metadata guard. A positive unconfined
control and a Landlock-enforced case both reached native SessionDB plus durable
RunIdempotencyStore and epoch1. The enforced case used the existing explicit
self-mount read opt-in; the guard/profile lease/mount observer bytes were NOT
changed. This proves that this owned fresh-open path does not require a broader
/proc grant. It is NOT the full P102 network/mount/cgroup projection, and does
not solve the strict cold-profile inventory mismatch above.

The first compatibility attempt's protected canary overlapped its QA read-only
root, so validation correctly refused before enforcement. Only the QA grants
were NARROWED to code subdirectories and the manifest; first output preserved.
The final new control and Landlock cases both completed. A collector exit0 is
not substituted for per-case outcomes. No sensitive canary data was exposed.

The observed prepared Windows SQLite3.50.4 and Linux SQLite3.45.1 caused native
Hermes to choose DELETE rather than enable WAL. The Linux crash cases reported
synchronous=2. This task did not upgrade a runtime or override the native WAL
safety branch. Official background: SQLite Write-Ahead Logging, section WAL-reset
bug, and Atomic Commit In SQLite; those documents are not execution evidence.
No multi-database atomicity is inferred from independent successful commits.

## Source custody, test counts and limitations

276 native Python source files match immutable Git objects.31 ruamel.yaml0.18.16
pure-Python sources reuse the previously recorded package hashes; no dependency
was installed or updated and Windows native extensions were not transported.
The executed path's normally imported sources are mapped to that inventory.
This is not a complete Hermes SDK/provider runtime dependency qualification.
Source payload stays in ignored scratch, not a new tracked upstream code dump.

Final full Windows2495 =2472 PASS /23 SKIP /0 errors /0 failures, exit0. All385
source hashes match before/after; all382 original product/config/test/script
sources remain unchanged.32 new offline evidence/tamper tests pass in Windows
and Linux and are a SUBSET of the full Windows count. Those repetitions are not
new native crash executions. The23 old platform/opt-in skips were not rerun.

The verifier checks actual rows, checkpoint state, PIDs, epoch generations,
immutable imports, cleanup and bounded claims, not only all-true flags. It
rejects modified evidence such as unknown->queued, fabricated completion,
missing cases, wrong source hashes, changed inodes or a claimed safe retry.
A valid receipt still does not authorize runtime launch.

The twelve process lifetimes in native002 are six crash/recovery pairs. The
prior native001 is an earlier separate execution, not12 additional distinct
scenarios. Compatibility target pairs are separate fresh-open observations and
are not labelled full Gateway runs or repeated crash coverage.

## Cleanup and delivery boundary

All owned temporary code and profile directories were removed. A separate
ordinary-UID audit found no matching live process, remaining H105E temporary
path or unreadable same-UID process. No root, mount, namespace, account, service,
production, CI, main or push action was performed. P71C is shared with the
concurrent N105D work and was not terminated by this task. Default Ubuntu was
not started or commanded.

Only scripts/qa/h105e_store_crash_probe.py, scripts/qa/h105e_receipt.py and
 tests/test_h105e_native_crash_receipts.py are new executable/test sources.
Concurrent N105D remains untouched and must be source/result-verified before
any union. Do not treat its result or our unconfined crash proof as successful
actual full Gateway startup. Legacy IPCv2 CLOSED, fullD3B OPEN.

Evidence directory: evidence/d3b-native-stores-h105e/.
Next: retain these adversarial cases in the canonical QA baseline, then make
one explicit native prepared-schema/profile-layout/constructor-side-effect
contract and qualify it under canonical final UID/lease/projection, before
HTTP admission, live broker-ledger reading or dummy-provider sends. Unknown
cross-store state must remain non-retryable until an explicit reconciliation
rule is separately implemented and accepted.
