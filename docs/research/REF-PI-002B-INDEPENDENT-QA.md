# REF-PI-002B Independent QA (ea51)

Current status: owner P1 FIXED AND INDEPENDENTLY VERIFIED; SQLite reader connection
lifetime FIXED AND VERIFIED. Final independent root rerun: 248/248 PASS with no skips or code drift.
Exact-commit server CI is a separate publication gate.

Historical first observation: P1 REPRODUCED. This report belongs to an independent reviewer, not a
second implementation lane. Initial strict-admission.mjs hash:
04803e7af88a7f89e5fda4c5aae7c55199e5d8832e5d0e3af08d5d5513d20a84.

## Owner-bound transaction and acknowledgement

A configured Harness A adapter accepts a Conversation handle from Harness B.
It runs B's transaction, then returns A.submission(id). Two independent SQLite
stores can have matching numeric IDs. The real native reproduction returned
A's preexisting submission12 while B gained a new record. See ignored runtime
ref-pi-002b-ea51/trial-01/foreign-handle-observation.json and qa-results.json.
No external service, model inference or personal profile was used.

A proposed minimal correction accepts only a numeric conversationId and resolves
the handle from the configured Harness before entering its transaction. Objects
(including a foreign native handle) are rejected before accessing their methods.
IDs are local to that owner; authorization still belongs to the host. Invalid
or unknown IDs must produce no write. At that initial checkpoint the proposal was not installed; the live verification
section below records the implemented correction.
Patch and complete source: runtime/ref-pi-002b-ea51/owner-binding.patch and
proposed-strict-admission.mjs. Migrate valid call sites to submit(root.id,...).

## Independent evidence

Original: 5 PASS / 1 FAIL. Proposed snapshot b30d71f508af8ab0e9b3af023a6356450cf319b6afad3c3cd8cdeb03a28adf3e:
12 native checks PASS in proposal-trial-01 plus proposal-atomic-01, and6 pure
unit cases PASS (owner-unit-proposal.json). Native checks use real Pi/SQLite,
no fake admission, with provider inference disabled. Fault tests wrap the
storage boundary and perform graceful close/reopen; not a powerloss claim.

Do not transplant these counts to the live candidate without rerunning. Do not
change the assertion to permit foreign-store mutation. Tests and original
receipts remain under the dedicated runtime directory; final committed evidence
will identify the actual accepted module hash, not this temporary proposal.

## Live owner fix verification

The implementation lane adopted owner resolution from the configured Harness.
Actual candidate47c8aaed0d2c8ab3603aa5ecd3a1861b06a0ebda31139af80c454d211f19bf11
passes the independent owner six and atomic six scenarios. The API now takes
only a numeric conversationId; raw handles are refused before a store write.
Unknown numeric IDs use invalid_conversation rather than the proposal's
unknown_conversation; the test accepts these explicit refusal codes while still
requiring zero writes. This is not weakening the foreign-owner rejection.

Tracked evidence is under evidence/ref-pi-002b-qa, preserving the original failure.
Reproduce the12 local cases from this worktree using a fresh output:

```powershell
python -B scripts/run_independent_admission_qa.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\pi-ref001-ac97 --output C:\Antigravity\AlazHarness\runtime\independent-admission-new
```

A separate standard-suite recheck ran248 tests and found1 resource-lifetime error
in the SQLite fixture cleanup. Deterministic inspection of the snapshot reader
also found1 connection still open after return. Both connections created by the
test and the reader need explicit close. That failed run is preserved. The implementation now closes its connections
explicitly: the deterministic after-test found zero left open. See
snapshot-lifecycle-before.json and snapshot-lifecycle-after.json.

## Independent final native rerun

The current core, native worker and runner were hashed before and after the
full12 scenarios x2; no drift occurred. All24 passed with6 verified child-process
kill/reopen boundaries. This rerun is not added to the12 supplementary checks
or the standard root count to create a misleading total. Summary and raw receipt
hash: evidence/ref-pi-002b-qa/full-native-recheck.json. The raw isolated stores
are retained at runtime/ref-pi-002b-ea51/native-recheck-01.

The separate12 supplementary checks are in packaged-validation.json; their
passive native writes use zero model calls. The primary24 scenarios use Pi's
scripted faux provider, never paid inference. No additional engine, source
update, shared database or operating-system service was created by this QA.
The prepared dependency receipt and lock are verified by the packaged launcher.

This closes only the two reproduced findings and exercises the scoped atomic
admission contract. Authorization, selecting a trusted execution scope,
cross-process owner fencing, all native entrypoints, complete external-effect
idempotency and production adoption remain separate open gates.

## Final standard rerun and integration handoff

After the explicit SQLite-close correction, the independent full root suite
passed248/248 with exit0, no skipped tests, and unchanged measured core/test
hashes. root-final-validation.json and root-final-unittest.txt preserve that
actual run. The earlier248/1ERROR run remains under the private QA runtime;
none of its results were silently replaced by a false historical success.

All QA source and sanitized evidence are integration-ready on the single active
admission branch. This independent supplement does not alter the upstream source
or add another runtime owner. Publication and CI must be read for the actual
resulting commit; this local result is not a statement that any future commit
was tested. The next component review remains OpenCode REF-OC-001. External
effect uncertainty, host permissions, budgets and single-process owner fencing
are not closed by the admission tests.
