# HYB-004C — independent QAbe46

Primary4cff owns implementation. Status: independent local tests PASS in the exact scopes recorded below.
Package exact-commit delivery is checked separately. No production method or second writer is
added by this reviewer. Default source Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780.

## Source-derived guardrails

Native gateway/runtime_ownership.py:215-243 exclusive_maintenance acquires the
same actual lock as Gateway ownership, retains it through the operation and
rejects a live owner even in the calling process. Reuse that boundary, not a
caller-supplied stopped flag. The lock inode may never be deleted/restored by
our maintenance code. Maintenance is allowed only after managed writers stop.

Frozen approval must bind action, exact key/request fingerprint and private
profile/principal scope, run identity, expected epoch/instance and snapshot.
It is not an inspector JSON turned into a writable capability. After acquiring
ownership and before commit, re-read the authoritative tables under transaction.
Completed/unknown/retired/malformed/ambiguous work must refuse orphan handling.
Missing or expired keys are not never-executed proof. Preserve a durable receipt
and make repeating the SAME operator command idempotent, but a different action
or request using its ID a conflict. Do not automatically POST another job.

Process-failure atomicity, confirmation expiry, an active Gateway, concurrent
maintenance and unacknowledged commit all need explicit acceptance. Prefer one
store write transaction plus a read-locked canonical store, or demonstrate the
exact multi-database rollback-journal restrictions; do not call a split-write
receipt atomic without crash tests. Real power loss and dishonest writers stay
outside a process-kill test. Existing status/docs are history, not permission.

## Native ownership evidence (completed)

The independent final probe used the unmodified public Gateway lifecycle and
native exclusive_maintenance. Thirteen checks passed: live Gateway refused
maintenance, stopped Gateway allowed it, nested same-thread canonical alias was
allowed, an independent same-process owner and another maintenance process were
refused. While a live maintenance lock was held, actual public Gateway startup
failed before ready; its native and launcher exits were proven. After hard-killing
only the held maintenance process via an owned OS handle and reaping it, maintenance
could reacquire. The same Gateway then started and cleanly stopped with a new epoch.
The lock inode persisted and the managed DB bytes did not change during lock-only
work. No admissions or model HTTP requests occurred. This is native primitive
coverage, not an operator apply transaction, irreversible effect or general fencing
proof. The first12-check run is preserved separately; the final13 checks add owned
failed-start and successful-after-release evidence, not25 identical-code cases.

Final receipt: evidence/hyb-004c-qa/ownership-final.json. Raw data remains under
runtime/hyb004c-qa-be46/ownership-final; one actual maintenance hard kill in this
run. The earlier initial run had its own kill. Fourteen offline receipt tests
are distinct from the thirteen native assertions and are not fourteen executions.

Reproduction (new output, existing prepared environment):
python -B scripts/run_maintenance_ownership_qa.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\fresh-maintenance-qa

## Initial operator regression (OPEN at first observation)

39 independent synthetic SQLite prepare/apply/receipt cases ran:38PASS/1FAIL,
no measured source drift. Native source-loader/maintenance were explicit test
substitutions only; real SQLite transaction and production operator code ran.
The failure retains a terminal_admission archive row for the run while deleting
its terminal_identity pointer. prepare still allows abandon_unadmitted because
only the pointer is checked. An incomplete/corrupt historical index must not be
interpreted as no old work. Reject or coherently validate relevant tombstones;
do not silently discard this fixture. This does not claim normal native runtime
creates the inconsistency, or establish a remote exploit. No actual old native
profile was changed. Hash and trace: operator-initial-findings.json and
operator-first-tests.txt. Primary4cff owns product fix.

The other tests include stale epoch/changed snapshot, wrong confirmation, related
work, missing DB/expired retention, read-only repeat, second-insert rollback and
commit-acknowledgement loss. Injected SQLite exceptions are synthetic failure
proof, not physical power loss or process-kill proof.

## Expanded receipt replay regression (OPEN at initial45)

45 tests ran43PASS/2FAIL on unchanged71094532 operator code. The archive-pointer
issue remains. A second fixture first records a legitimate operator closure, then
adds a conflicting canonical unknown admission. The same apply command returns
already_recorded/requestClosed=true without rechecking the now-conflicting state.
The inspector already refuses that contradiction, so the operator receipt replay
should also distinguish historical receipt retrieval from CURRENT closure. It
currently claims the latter through requestClosed=true. No mutation happens on
replay, but the returned current-state assertion is not supported. Revalidate
absence in the receipt replay path or explicitly cease asserting current closure.
Regression: test_canonical_appears_after_closure_replay_refused. These are
artificially inconsistent temporary records, not a claim of normal native race.
Code remains primary4cff-owned; initial failures preserved unchanged.

## Fixed operator targeted acceptance

After the two independent findings, operator00613968 now calls the bounded
assert_no_recorded_work scan and repeats that check when replaying an old command.
The helper e355372c rejects matching unindexed terminal archives and malformed or
excessively large archive scans. Both failing fixtures remain unchanged. All45
independent SQLite prepare/apply/receipt tests pass, exit0, no measured drift.
Prior39/45 failed observations stay in evidence, never relabeled successful.

## Actual transaction process crashes

The genuine OperatorResolution and pinned native exclusive_maintenance executed
against fabricated SQLite tables in a NEW test profile. No native Gateway or
model was involved. A test-only AST/line checkpoint paused actual apply between
the first and second receipt INSERT, or after real COMMIT before the reply. It
did not replace methods, query results or local state. Parent verified OS process
ownership and killed only the owned interpreter; both native and launcher exits
were awaited. Before-commit cut left0 audit rows. After-commit cut left2rows.
Repeating the exact operator command produced recorded or already_recorded as
appropriate, never duplicate receipt or replay-table changes. Both cases passed.
The first actual process result is transaction-crash.json. This is real process
crash/SQLite recovery evidence on synthetic stores, not two new Gateway recovery
scenarios, powerloss, WAL or an actual external side effect. A final run pins all
program hashes as well as the operator module before/after its two scenarios.

## Final independent acceptance

The unchanged corrected product passed the complete604-test standard suite,
exit0/no skips/no measured drift. Our45 operator tests and14 ownership-receipt
tests are included in604, not59 additional tests beyond it. Root actual output
and hashes are root-first-validation.json/root-first-tests.txt (the name marks
our first full run in this task, which passed). No old failed39/45 result was
rewritten or treated as final acceptance.

Final transaction-crash-final.json pins all relevant runner/worker/operator/helper
hashes and has two actual owned process kills on synthetic SQLite, both PASS.
These repeat transaction-crash.json with wider program fingerprinting; do not
add the earlier two runs to the final two as identical-harness acceptance.
Native primitive ownership13 assertions in ownership-final.json are another
scope, involving one held-maintenance process kill and real Gateway lifecycle.
None of these numbers is a count of model inference calls; all are zero inference.

Primary's THREE final native profiles (orphan, completed, unknown) were independently
read from both actual SQLite files after verifying recorded owned process exits.
All current product hashes matched. Orphan had exactly one operator receipt and
one pointer, no admission/tool and retained replay identity. Completed kept its
real read_file marker and original outcome with no closure rows. Unknown remained
unknown with no tools or closure rows. Original receipt, repeated command and
new-epoch replay match byte-for-byte as values; the new inspector agrees. No
profile file changed during this review. See native-final-corroboration.json and
scripts/qa/operator_native_corroboration.py. This is three retrospective
corroborations, NOT three additional Gateway runs or applied closures.

## Scope and remaining limitations

The operation writes an explicit LOCAL audit closure, never changes the native
interrupted status and never re-admits work. Native raw API clients do not become
aware of this receipt automatically. The proposed future host coordinator must
consume verified closure records and must handle replay-key expiry separately;
this does not yet enforce perpetual no-reoffer against bypass clients. Local
plan confirmation is an explicit action boundary, not a cryptographic signature
of an operator or an OS access-control implementation. Read-only inspection is
not proof of a future mutation lease. Native source/lock, bound context, immutable
plan and fresh transactional rechecks jointly protect this narrow mutation.

Physical power loss, hardware faults, hostile writers bypassing native ownership,
production WAL, irreversible external effects, global money/token budgets, model
quality and M1/M2 are not accepted. QA files are staged explicitly; primary4cff
owns the single package commit. A green prior commit never proves this new one.
