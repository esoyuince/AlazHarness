# HYB-004 — independent QA5016

Primary208f owns implementation. No second product runtime or admission store added.

## Confirmed independent two-store gap (two owned crash/reopen runs)

A rollback-only BEGIN IMMEDIATE lock held by an external SQLite connection stops
canonical state.db writes without modifying any native function. The unmodified
public Gateway still reserves a key in runs_idempotency.db. With one reservation
and ZERO canonical admissions proved under the held lock, the OS-owned native
process was killed. Parent and native handles exited, then the lock was rolled
back and released. The same profile/config/key was reopened by the native public
lifecycle, epoch1 ->2, new native PID and instance ID.

OBSERVED: zero native admissions/messages before and after restart, exactly one
retained reservation, no model requests. Actual HermesRunsClient.status reports
interrupted. An explicit identical POST returns the same run_id with replayed=true;
changed input returns409. The client resume result has backendConfirmed=true and
requiresOperator=false even though no canonical admission exists.

This is not successful input recovery and not a completed user task. The observed
terminal classification comes from the fallback reservation store; the adapter's
backendConfirmed means a terminal HTTP status, NOT canonical execution proof.
No automatic retry/replay or operator resolution was added by QA. No lost accepted
202 is claimed: first TCP request reset before the client received acceptance.

Raw evidence: runtime/hyb004-qa-5016/gap-trial-01/gap-observation.json.
The independent technique uses no settrace/method replacement; it can corroborate
primary's line-checkpoint gap using a distinct mechanism. It delays existing
writes but never injects/commits an admission row. Still no power-loss/WAL proof.

## Acceptance implication

HYB-004 must remain bounded characterization until orphan-reservation handling is
explicit. Add a host-level orphan/unknown classification or repair path with exact
native ownership proof. Do not treat an absent canonical record as success; do
not delete a replay key and submit automatically based only on a missing response.
Production repair and retention expiry behavior are not implemented in this QA.

## Qualified repetition and scope

The experiment was repeated in another fresh profile with the same existing
prepared interpreter. Both runs show the same gap: one durable replay reservation,
zero canonical admissions, zero transcript entries, zero model HTTP requests.
Each run has one OS-handle-verified nonzero process kill followed by a new native
runtime epoch and a cleanly shut-down replacement. Repeated raw profiles are
retained at runtime/hyb004-qa-5016/gap-trial-01 and gap-qualified-02.

The first run was independently accepted by the stricter observation validator
once it was packaged. The second ran that validator before writing its final
OBSERVATION_CONFIRMED receipt. Neither receipt is product_recovery_accepted.
New code is test/QA only; the existing native Gateway worker, real Hermes sources
and production HermesRunsClient were not modified by this reviewer.

Twenty-seven offline tests cover malformed/forged observation receipts, duplicate
or missing records, wrong generations, misleading success, unexpected inference,
non-exited processes and reader resource custody. Missing databases are not
created by read_state; both SQLite read connections are explicitly closed.
These27 tests are not27 native recovery scenarios and are part of the standard
suite, not an additional count to add to it.

## Reproduce the independent timing technique

```powershell
python -B scripts/run_gateway_gap_qa.py --source-workspace C:\Antigravity\AlazHarness --python C:\Antigravity\AlazHarness\runtime\hyb-gateway-5a5c\prepared\env\Scripts\python.exe --output C:\Antigravity\AlazHarness\runtime\fresh-gap-review
python -B -m unittest discover -s tests -p test_gateway_gap_qa.py -v
```

Output must be fresh; the runner installs nothing and reads no personal profile.
The rollback-only lock is deliberately injected contention on a TEST database,
not a production repair. No SQL rows are manually inserted or changed. Retention
expiration, operator repair, multiple writers, WAL and physical power loss remain
unqualified. Primary208f's normal/unknown/completed cases and its AST checkpoints
are separate evidence, not inferred from these two reproductions.

## Preserved files

- scripts/run_gateway_gap_qa.py: independent bounded fault/reopen experiment.
- scripts/qa/gateway_gap_client.mjs: existing adapter operations against real HTTP.
- scripts/gateway_gap_contract.py: strict observation-only validator.
- tests/test_gateway_gap_qa.py: offline evidence and reader contracts.
- evidence/hyb-004-qa/gap-initial-observation.json and gap-qualified-observation.json.
- evidence/hyb-004-qa/root-validation.json and root-unittest.txt: actual offline
  full-suite output; interpret only the exact recorded tests/exit/drift fields.

A backend-confirmed interrupted HTTP status is not a successfully executed task.
This important semantic difference must be preserved in the next host recovery
contract. The orphan gap is still OPEN, not repaired by green characterization.

## Offline suite and retained primary-store review

The independent complete offline suite ran386/386 with exit0 and no skips.
Measured scripts/tests/component hashes did not change during that run. The27
new QA evidence/reader cases are included in386. This does not run native Hermes
inside CI and is not a count of386 crash tests.

Eight then-complete primary acceptance runs were independently re-read from the
retained SQLite databases after their recorded native/launcher exits: completed,
first-provider-wait, after-real-read and before-reservation, each twice. Final
admission IDs, status, counts and real read nonce agree with the HTTP/exit records.
Completed output is byte-identical; uncertain executions stay unknown with no new
model call. The pre-reservation case is an explicit fresh reoffer, not an automatic
retry and not recovery of a previously accepted job. These eight checks are
retrospective corroboration, NOT eight new process runs. The initial snapshot
is preserved separately; a later complete ten-case corroboration may supersede
its coverage without adding to the native-execution count.

The tested native tool was read_file. This package does not establish exactly-once
external writes, payments, network effects or another irreversible action.
QA5016 stages only its listed files; primary208f owns final Git publication.
Exact-commit CI must be checked after that publication, never inherited from e6f596c.

## Complete primary-set corroboration

After all five scenarios had two accepted runs each, all TEN retained records
were independently checked against both actual SQLite stores and their recorded
first-kill/second-shutdown identities. Every check corroborated its stated result.
See primary-store-final-corroboration.json. This supersedes the eight-run coverage
above; neither file contributes additional native executions. The two after-reserve
runs also show no canonical admission despite a retained interrupted replay key.
The primary trace checkpoint and our independent database-lock technique agree.

## Proposed HYB-004B exit criteria (NOT IMPLEMENTED by this QA)

Transport terminal, canonical admission existence, execution outcome and permission
to repeat are distinct facts. A missing admission_id in a response is insufficient
on its own to prove an orphan: an authenticated native lookup must corroborate it.
Until that proof exists the host can say unverified/orphan-candidate, never success.
The interrupted reservation's transport flag must not imply safe automatic repeat.

An orphan-reconciliation decision must bind the exact request fingerprint, native
profile/principal scope, run identity and current ownership epoch. Completed work
must retain its previous result; unknown claimed work must keep its execution
barrier. A safe input reoffer before ANY reservation is a separate case from a
reservation without admission. Key deletion/expiry alone is not a recovery decision.

Acceptance needs separate tests for pure reservation, genuinely unknown execution,
retained completion, unauthorized or foreign scope, same-key/different-payload,
stale epoch, retention expiration, and database read failure. This is a proposed
next-gate checklist, not proof of an implemented host policy or tested safe repair.
