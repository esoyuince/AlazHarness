# HYB-004B — independent QA4cff

Status: TARGETED QA PASS; final whole-package and exact-commit delivery are recorded separately. Primary7c8b owns implementation. This document is a test
plan/source observation until individual repro receipts exist. No new native
Gateway loop, alternative scheduler, data repair or paid model call is authorized
by this document.

## Source-derived acceptance risks

Pinned Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780 has native tombstones:
hermes_state_terminal.py:12-14,58-86. A missing live session_admissions row is
not alone proof of no canonical admission. Exact terminal tombstone identity and
result must be considered, or fail closed as unverified.

A readonly recovery inspection must not call RunIdempotencyStore.lookup: native
lookup:157-167 prunes terminal rows and may extend retention in a write transaction.
status_for_run may also extend retention. Missing or pruned key cannot mean safe
new work. Explicitly read-only query+connection and immutable-profile binding
must be verified independently.

The HTTP run scope is SHA256(profile + NUL + configured API key), native
api_server_runs.py:375-386. The request fingerprint is SHA256 of exact sorted
JSON body and gateway_session_key (:644-651); an admission payload_digest is a
different identity and must not be compared as though interchangeable.

Runtime epoch (runtime_epoch singleton) must match the expected owner and remain
unchanged across the two-store snapshot. A caller-supplied epoch or stopped flag
is an expected value, not independent ownership proof. A gap seen while an old
writer remains alive may be transient; it cannot authorize a new POST.

## Planned negative tests

Wrong profile/scope/token, wrong input digest, wrong native run/session/admission,
stale epoch, retired/tombstoned terminal work, duplicate/contradictory records,
malformed persisted JSON, retention expiry and missing store. Verify no path, key,
body or private output leaks on refused queries. Ensure all read handles close
even when the second store/query fails. Mutation of returned evidence must not
turn an unverified state into executable permission. Automatic write/retry/delete
is never part of this gate.

## Initial classifier repro (fixes pending)

Pure classifyRunRecovery accepts completed+failed=true, whitespace session_id and
a run_id object coercible to a string as canonical_terminal_reported. These three
behaviors were reproduced on hash20dc8230 before any QA patch. HTTP snapshot already
rejects the contradictory flag, so this is an exported-classifier contract issue,
not a demonstrated remote exploit. Regressions are in
tests/test_reconciliation_transport_qa.py.7c8b owns the implementation fix.

Initial22 checks had5 failures:3 classifier issues and2 overstrict QA expectations.
The latter expected mayHaveBeenAccepted=false on local post-GET snapshot errors;
that field was absent, not true, and the request was read-only. Those2 QA predicates
now reject only a true write-uncertainty flag, while still requiring the exact
error code and no POST. Initial failed logs are preserved; they are not5 product bugs.

## Inspector defects reproduced (fixes pending)

Independent33 synthetic SQLite checks produced3 errors and1 failure. payload_json
that parses to a list, or api_turn_v1 as list/null, escapes inspect as AttributeError
rather than returning unverified. Exact traces are in inspector-initial-tests.txt.

Separately, an admission payload with a self-consistent native digest but a changed
settings.requested_model was reported canonical_terminal_verified although the
replay fingerprint still bound the other explicit body.model. This is an
inconsistent-record fixture, not a claim that normal upstream admission produces
that mismatch. Full request identity verification must either reconcile supported
model-selection fields or refuse an unsupported routing case. Tests live in
test_reconciliation_inspector_qa.py; primary7c8b owns fixes. Old failures retained.

## Actual retained native-record application

The new inspector was independently applied to ALL TEN retained HYB-004 profiles
using their own recorded epoch/instance/request body/key and local-only fixture
credentials. Four terminal results verified, four remained execution_unknown and
two remained reservation_without_admission_observed. All ten databases and their
sidecar bytes stayed unchanged; no Gateway/model process or POST was launched.
This is10 new inspections of prior runs, NOT10 new native recovery executions.
See evidence/hyb-004b-qa/native-records-first.json. The initial snapshot already
passed the normal historic records; it does not supersede the still-failing
malformed/model-mismatch tests. After fixes this recheck must be repeated on the
final inspector hash. The synthetic tombstone test passes, but actual native
retirement and live read/write race coverage are separate from that fixture.

Reproduction (fresh output path, no installs):

```powershell
python -B scripts/qa/reconciliation_native_records.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\fresh-recovery-inspection
python -B -m unittest discover -s tests -p test_reconciliation_transport_qa.py -v
python -B -m unittest discover -s tests -p test_reconciliation_inspector_qa.py -v
```

A local inspection context is privileged host configuration, not network caller
input. Retrospective profiles prove an observation at their saved epoch; this
report does not establish an active process lease or authorize later mutation.
No returned JSON object can be used to delete an idempotency key or reissue work.

## Fixed-candidate targeted acceptance

All55 independent targeted checks now pass (22 classifier/real-loopback adapter
cases +33 synthetic SQLite cases), exit0 and no measured product-code drift.
run-recovery.mjs48f2a374 now rejects contradictory completion and coercible IDs,
and does not accept whitespace session identity. recovery_inspector.py8695b480
explicitly checks payload/API settings types, returns bounded unverified failures,
and binds a supported direct model request to its native selected-model field.
Unknown provider/alias/options routing is refused, not guessed equivalent.

All the original defective fixtures are still in the final test suite. The two
initial overly strict GET error-flag expectations were corrected independently;
no actual faulty case was removed to obtain PASS. The first full503-test run
also overlapped a primary code update and retained4fails/3errors. It is historical
FAIL with measured code drift, not final acceptance.

No old source bytes, existing profiles, API keys or native replay keys were
rewritten to make these tests pass. The final root suite and retained-native
recheck have distinct receipts; do not add55 tests a second time to the root count.

The semantics now distinguish transportTerminal/admissionReported from actual
local canonical verification. resume uses only GET even on observer timeout or
abort; reconcile makes one authenticated GET. The regular observe control path
remains intentionally allowed to request stop and is a different operation.
This change does not grant permission to repeat an effect or repair a database.

## Final independent local acceptance

The complete standard suite passed **506/506**, exit0, no skips and no measured
code drift. Product/QA hashes are in root-final-validation.json; the55 targeted
cases are already part of506. The first503 count was an earlier failing/drifting
revision, preserved rather than relabeled green.

The post-fix inspector was applied again to the ten original HYB-004 native
profiles: **10/10 PASS**, four exact terminal outcomes, four unknown executions,
two reservation-only observations, every database byte unchanged. See
native-records-final.json. Neither the first nor final ten-record inspection
creates new Gateway runs, kills or model calls. Any new primary native8-case
acceptance must be verified from its own final program hashes separately.

Original32 root file hashes and all four upstream pins/clean worktrees are
preserved (custody.json). No dependencies were installed by this reviewer; no
user profile or real provider credential was used. The initial failures and
precise fix boundaries stay in the evidence directory for auditability.

This closes only the bounded read-only classification/inspection and observer
behavior reviewed here. Automatic orphan repair, key deletion/reoffer, provider
cost limits, live process fencing, external effect exactly-once and full M1/M2
remain NOT ACCEPTED. The default-profile/direct-model local inspector is not a
public network authorization API, an atomic two-store transaction or a future
execution lease. Package publication is owned by primary7c8b; exact-SHA CI must
be read after its commit, not assumed from these local tests.

## Final four actual native-run corroboration

Primary reran all four native scenarios after the fixes, once each. Their four
public reconciliation records match the current adapter/classifier/inspector
hashes. This reviewer independently reopened each retained state.db read-only,
matched canonical admission/tool counts and real read nonce, checked first hard
kill and second native exit/epoch receipts, and reapplied the final actual local
inspector with the original private test identity. All four results matched.
Database bytes remained unchanged and no additional provider or Gateway process
was started by this corroboration. See final-four-native-corroboration.json.

The current native acceptance is FOUR post-fix executions, not the initial eight
plus four presented as twelve tests on identical code. Completed has one read and
two model HTTP requests; before-model has zero reads/one request; after-tool has
one read/two requests; orphan has zero reads/zero requests. No scenario adds a
model request after restart. All of those HTTP responses are scripted, not model
inference. Automatic mutation remains outside this acceptance.
