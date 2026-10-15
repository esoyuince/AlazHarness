# HYB-005A — independent QA890e

Status: scoped independent QA PASS; initial failures preserved. Primary9897 owns product files;
QA890e owns only tests/test_host_gate_qa.py, this report and evidence/hyb-005a-qa890e.
No upstream edits, second scheduler or personal profile changes are authorized here.

## Initial executed test result

The REAL HostGateLedger/HostGatePolicy code runs against synthetic SQLite stores
and a test substitute for native SessionDB._execute_write. This is not a Gateway
or full native-owner acceptance.36 cases executed:34PASS,2FAIL, exit1. Source
hash before/after was identical; exact hash is in initial-run.json. All temporary
connections are closed. Old state and initial output are retained.

## QA-01 — missing consumed intent can resurrect the same dispatch identity

1. issue(requestId A, body), consume(key, body).
2. Simulate partial state loss by removing only the intent row in TEMP state_meta.
   Config retains issued=1/spent=1. No native replay row is present (valid possible
   after pre-send crash, retention or an unavailable original send).
3. issue(A, same body) currently succeeds instead of refusing inconsistent history.

The deterministic namespace+requestId produces the same key again. Expected:
config counters must be corroborated against retained intents BEFORE issue or
consume. A missing row is not proof of a never-sent request. This is a partial
record-loss fixture, NOT a claim of physical SQLite corruption or an attacker
without database access deleting rows remotely.

## QA-02 — configuration count is trusted without retained-history consistency

Issue one request, then change config.issued to0 in the TEMP DB while retaining
its intent. A second issue succeeds. The guard must refuse internally contradictory
history rather than resetting/guessing counters. Every state transition should
check consistent bounded retained intent count and consumed count in the SAME
native-owner transaction. No automatic pruning or reinitialization over history.

The test names are test_deleted_consumed_intent_not_reissued and
 test_dishonest_counter_not_accepted. They deliberately expect rejection; do not
weaken them or classify their present failure as a product PASS. Missing-config
with retained intents already refused in the tested candidate.

## Successful scoped observations

Repeated keys, changed input, scope/model/epoch/expiry/clock rollback, closure,
legacy/unissued keys, missing replay DB, callback commit failure, lost commit ACK,
and twenty concurrent issuers/consumers were also exercised.20 concurrent consume
calls produced exactly one claim with spent=1. Lost commit ACK retained consumed
state and a retry was refused. These are36 offline cases, not36 native runs.

## Further native acceptance needed

The dedicated host POST endpoint must be absent/closed when plugin registration
fails. No fallback to raw /v1/runs from the new host client. Prove real native
SessionDB ownership, serialized consumption before native admission, authenticated
route deny behavior, connection/cancellation loss, closure and retention after a
native reopen. A literal API forwarding cap is not a total provider/token/currency
budget. Existing probes and closures must be read only unless a fresh TEST profile
is explicitly created. M1/M2 remain open.

## Ledger fixes independently rechecked

Primary9897 added a bounded retained-intent scan and count/namespace consistency
check inside the same _execute_write transaction. The SAME36 test functions now
pass36/36, exit0, code drift0. No weakening of the two failed assertions.
Product hash c2f95f09fbaa0b39dea57aaf488cbfaac204b61771adffeb8ef182bd5c81b1ff;
recheck-run.json and recheck-tests.txt record the observed closure of QA-01/02.
This does not make all-database rollback or hostile operator tampering detectable.

## QA-03/04 — client accepts contradictory admission responses (initial finding; corrected below)

The real new HostGateClient was exercised against a fixture fetch in Node24.
12 cases ran:10PASS/2FAIL, exit1, client source drift0. A202 response with
status=completed, completed=false and partial=true was returned without error.
A202 completed response whose output was an object rather than text was also
returned. Existing run observers reject such ambiguity; the new dispatch entry
must not deliver these as valid native admissions. Assert invalid_host_admission,
mayHaveBeenAccepted=true and retryAllowed=false WITHOUT refunding the permit.

Source hash: ddf1206517794907a7b02a7967cae4c0f28b512b262aea0790ce134c3e2ceabe.
Exact tests: tests/node/host_gate_qa.mjs, one case per unittest via
 tests/test_host_client_qa.py. Failed cases:
contradictory_completed_admission_refused, invalid_output_type_refused.
This is malformed HTTP-response handling, not a demonstrated remote native-server
exploit. Native successful completion should still be established by later GET
and canonical reconciliation, not admission response alone. Initial output retained
in client-initial-tests.txt and client-initial-run.json. Primary owns the fix.

## Component HTTP observations (not native Gateway)

The real aiohttp/plugin/ledger were bound to a SYNTHETIC adapter and owner; native
adapter provenance validation was substituted ONLY at binding for this fixture.
17/17 loopback HTTP cases passed, including20 simultaneous dispatch requests with
one callback and19 refusals, authentication/duplicate-header/duplicate-JSON/query/
foreign-header rejection, committed consumption before callback and no refund on
callback exception. No Hermes Gateway or AIAgent was constructed; the callback is
only a counter and fake202. These17 are NOT17 native runs or part of the root suite.
The first receipt is historical: its all() assertion was subsequently strengthened
to require exactly one matching consumed row (avoiding vacuous empty success).
A fresh final run is required before treating the improved checker as exercised.

## QA-03/04 corrected and independently rechecked

The same12 real-client/fixture-fetch cases now pass12/12, exit0; malformed output
and contradictory completed flags are rejected as invalid_host_admission. The
per-client attempted set is populated before the request and is not cleared by
those refusals. The unchanged36 ledger tests were rerun36/36 as well. Source
hashes and zero in-run drift are in final-targeted-validation.json. Tests were
not weakened; initial red receipts remain. These48 cases belong to the standard
suite and must NOT be added again to its total.

The strengthened HTTP checker now also passed17/17 with exactly one matching
consumed intent required at callback entry. Final component receipt is
http-final-component.json. It remains a synthetic adapter/owner test with an
explicit bind-time provenance substitution, NOT full native Gateway evidence.

## Native evidence independently corroborated (four existing runs)

The four qualified primary reports were independently compared with their actual
closed-profile state.db files. No native worker was rerun and no production
record was changed. Every measured product/runner hash matches the current
checkout. First/second process identity, nonce, exit0, native+launcher reaping,
profile binding, native class names and no blocked non-loopback attempts were
checked. Four reports are corroborated, not four additional executions:

- missing-plugin: no intent, admission, transcript, tool or model request.
- invalid-policy: no intent, admission, transcript, tool or model request.
- normal: ten concurrent independent clients give one native acceptance and nine
  rejections; one real read_file tool result, two scripted model HTTP requests.
- lost-ack: the actual202 acknowledgement is dropped by the test relay; consumed
  state stops repeated dispatch. One native admission, one real read_file and two
  scripted model requests, not two agent runs.

Normal and lost-ack each cleanly reopen the same profile under a new native epoch.
Their persisted consumed intent/counters and completed native output are unchanged;
no further model request occurs. These are clean shutdown/reopen checks in this
package, NOT a new process-kill, disk-power-loss or atomic-network-delivery proof.
The generation count is six process lifetimes across these four scenarios.
No real model inference occurred; only the provider responses were scripted.

See native-retained-corroboration.json for exact primary receipt hashes. The
records in runtime/.../normal-trial-01 and final-missing-plugin are historical
pre-fix attempts and are excluded from the four qualified-run claim.

## Remaining boundary conditions

The dedicated host endpoint is required by HostGateClient. If plugin setup fails,
that endpoint is unavailable and the client never falls back to /v1/runs. This
DOES NOT establish that an unmodified upstream Gateway without the plugin has
its raw routes universally disabled, nor does it fence another channel or agent.
A trusted operator credential and dedicated profile remain assumptions.

Consumption is durable before handoff, not atomic with network delivery. A crash
between consumption and native execution can abandon a not-yet-delivered request;
there is deliberately no automatic refund/resend. Regenerating all state from an
old backup and malicious changes to both counters and rows are not detected by a
local consistency checksum. A newly minted unrelated requestId is not semantic
proof that an old business intention has never run. Currency/token/provider retry
budgets, tool permissions and OS sandboxing are still separate open increments.

## Final independent standard test run and handoff

Complete repository unittest discovery passed669/669, exit0, no skipped tests.
131 measured program/test/component files were unchanged during the run and no
new program file appeared. Full output and measured host product hashes:
full-standard-validation.json and full-standard-tests.txt. This669 includes the
36 ledger+12 client QA cases and all prior standard suites. Do not add48 to669.
The17 selected-component HTTP cases and four existing native scenarios remain
separate evidence scopes; the component guard substitution remains disclosed.

All four identified defects were reproduced before fixes, their failing receipts
preserved, and their original test expectations passed against final product
code. The scope is one-use host handoff and defensive response validation, not
complete M1, tool/model authorization, hard provider budgets or hostile-plugin
isolation. The existing32 root files and four source trees were preserved.

QA890e stages only its named tests, HTTP probe, report, this session's prior-status
archive and evidence. Primary9897 retains sole publication/branch ownership.
No green CI claim is made until the exact published SHA is queried separately.
