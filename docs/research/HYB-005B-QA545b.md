# HYB-005B — independent continuation QA545b

Date:16 October2026. Product/native/Git publication owner:3156. QA545b modifies
only its explicitly named tests/report/evidence; no second native batch or product
implementation was started. A status-hash conflict blocked the initial write
before any file was changed, and concurrent3156 ownership was then observed.

## C01 product closure confirmed on disk

The actual execution_boundary.py hash6c3551297676635764cd464dc1159b12a8ba34799faa8bd96a7106cd909a348f
now binds the startup settings digest to the live PluginContext.get_config result.
It also rechecks the current profile before providing the ledger used by the file
handler. It does not silently adopt a new budget or newly configured upstream.
The original22 QA3156 cases ran22/22 PASS with their previous assertions unchanged.
This includes the8 profile checks and14 retained-evidence tests, not22 new native
executions. Previous4 failures remain preserved in QA3156 evidence.

## Twelve additional checkpoint contracts

The production boundary is real; config loader, tool registry verifier and native
owner access are explicit synthetic ports. No Gateway, SDK or file handler runs.
Tests confirm revoked read permission reaches denial before tool ledger/owner
lookup; lowered call budget and changed provider key also refuse; missing context,
loader exception, non-serializable/null settings fail closed; bool is not an int
configuration alias; readiness refusal does not initialize/reset a budget; rejected
changes do not mutate or rebind the running policy; reordered identical JSON settings
remain equivalent.12/12 PASS, exit0, measured code/test drift0.

Reproducer: python -B -m unittest discover -s tests -p test_execution_policy_checkpoint_qa545b.py -v
Original checks: python -B -m unittest discover -s tests -p test_execution_*qa3156.py -v

A first QA launcher bookkeeping mistake used a relative file with relative_to of
an absolute root. It stopped before any tests ran; rerun normalized the bookkeeping
paths without changing the tests or product. It is not a failed product test or a
passing run. The twelve tests are part of the future full standard suite, not a
separate native execution total and not added twice to its count.

## Remaining evidence gates

A unit/component PASS does not qualify the live native loader, all provider paths,
actual tokenization, pricing, irreversible tool effects or OS isolation. Current
model/endpoint/file-family limits remain as in the HYB-005B implementation report.
Any native result from before this source hash must retain its historical scope.
Post-run verification must compare current measured source, OS-owned exit identities,
native SQLite records, wire count and consumed budget; a transport terminal flag
alone is insufficient. Clean-network acceptance cannot be inferred when the probe
reports blocked non-loopback attempts. Such counts and attribution limits remain
explicit, rather than being silently suppressed.

Full-suite, final native and exact-SHA CI are NOT yet claimed by this report.

## First final-source native corroboration: normal + reopen

The primary final-normal run was re-read independently from its retained receipt,
native state.db and OS-owned shutdown records. All17 measured product/probe files
match the current source. One exact admission/run/session, one native read_file
result, two actual loopback-provider requests and the stored final response agree.
The same profile was opened under epoch2 and a new native runtime instance; all
reserved exposure remained327680 configured token units /393216 microUSD fixture
exposure. No model call was added by that restart. Both generations shut down
normally with native/launcher exits confirmed and zero blocked non-loopback
Python network attempts. State-file SHA256 was unchanged by this read-only QA.

This is corroboration of ONE existing normal scenario with a second process, not
an additional Gateway run. Evidence: normal-native-corroboration.json. Startup was
78.221seconds under the explicitly declared180-second test bound, including SDK
class preloading; the old70-second cold-start performance criterion is NOT passed.
The primary also recorded capabilities/models refusals after revoking its TEST
profile allowlist, with no added reservations or provider requests. That checks
live configuration gates after completed work, not cancellation of an in-flight
provider or file operation. Direct tool-ledger revocation is separately covered
by the synthetic checkpoint tests above.

## Acceptance wording and next-stage boundaries

These gates support a NARROW dedicated-profile execution acceptance, not universal
budget enforcement. Every HTTP attempt that crosses the configured Alaz provider
route consumes a durable reservation, including SDK retry or summary traffic that
uses that route. It does not prove an unconfigured client cannot bypass the route,
that arbitrary providers/credentials are isolated, or that a declared input token
ceiling is a measured tokenizer count. The configured integer rates are fixtures;
real pricing and actual charge qualification require a separate provider gate.

C01 rechecks native configuration at readiness/ledger access; it does not atomically
join filesystem policy edits, provider delivery, and ledger settlement. A request
already sent or a native read already entered is not magically undone by revocation.
This is a fail-closed mismatch rule at the checked boundary, not instantaneous
in-flight cancellation or same-process adversary isolation. The native read wrapper
continues to rely on the explicitly documented file/path and trusted-process scope.

Prior startup failures, the earlier Windows reopen fault and historical blocked
network counts are retained. Final test improvement must be reported as current
observations, not removal or retroactive conversion of those failures. Standard
CI and the separately prepared native Gateway environment must stay separate.
No native setup command or dependency installation is added to default CI by QA.

## Final summary discrepancy — preserve original failed check

The first five final-source native cases were strictly corroborated. Summary then
failed the independent verifier's final-result check, even though the primary
runner's narrower count/marker assertions recorded PASS. That failed independent
receipt is retained in final-native-corroboration.json; it is not a final7/7 approval.

Direct retained evidence: the native stdout reports iteration budget1/1 and the
transcript contains the EXACT pinned MAX_ITERATIONS_SUMMARY_REQUEST constant.
The model returned the true file marker through two provider requests and both
requests retain full ledger reservations. However HTTP reports failed with usage
120 input/20 output/140 total, while the canonical admission is terminal/completed
and the two provider claims each report120/20 (aggregate240/40/280). The stored final
assistant output equals the HTTP output. No refund or missing provider reservation
is observed; execution/accounting and task-success projection are separate concerns.

Do NOT convert this to task success just because model text or canonical outcome
says completed. Do NOT infer a safe replay from HTTP failed. The summary budget-path
observation can be characterized separately, but HTTP/canonical terminal and usage
reconciliation needs an explicit next-gate decision. The source comments calling the
summary toolless are not behavioral proof: the actual pinned chat-summary builder
preserves tools, and the observed second request carries tool schemas.

Evidence: summary-result-discrepancy.json; the actual summary nudge and stdout show
this is the maximum-iteration summary path, not a second ordinary successful turn.
No upstream/product/native fixture was edited or rerun by QA to obtain this finding.

## Six strict cases and one separate summary accounting observation

The normal, provider-limit, tool-limit, denied-write, SDK-retry-limit and unknown-
price cases all pass strict retained-source/SQLite/lifetime verification, with
zero blocked non-loopback Python network attempts in their observed generations.
Their individual state database hashes did not change during independent reads.
See six-strict-native-corroboration.json. The SDK-retry case uses the real native
auxiliary client factory and installed SDK through the actual Gateway route, but
is not a full AIAgent task. Unknown-price is an explicit negative admission case.

Summary's reserved accounting is corroborated separately, but its contradictory
HTTP versus native completion/usage projection is OPEN. Seven runner count/marker
checks must not be described as seven successful user tasks or seven fully agreed
terminal outcomes. No source was changed to relabel the first strict rejection.
All observations are final-program-hash checks, not assumptions from prior PASS.

## Resolution of the apparent terminal conflict (current interpretation)

The earlier admission-versus-HTTP comparison was incomplete: an admission outcome
of completed only records that its native handling finished. It is NOT sufficient
proof that the agent completed the requested task. The canonical state_meta RESULT
record for this SAME summary contains completed=false, failed=false,
turn_exit_reason=max_iterations_reached(1/1), api_calls=1 and the preserved summary.
The pinned native terminal mapper derives failed from that result. The existing
LocalRecoveryInspector independently returned canonical_terminal_verified,
outcome=failed, taskSucceeded=false and retryAllowed=false. Both database hashes
were unchanged. Thus this is not established native state corruption or a failure
of the existing recovery inspector. The first strict verifier wrongly required a
completed task for the summary-budget scenario; its original rejection is retained
rather than hidden. See summary-terminal-semantics.json and
summary-inspector-observation.json.

The usage-scope difference is real: native terminal/API usage reflects120/20/140,
while both execution ledger provider claims retain120/20, for aggregate240/40/280.
The durable route counts/reserves BOTH physical requests, so no reservation is
lost or refunded. Public task-summary usage must not be used as the complete
provider budget total. Exact actual invoicing and unified usage reporting remain
separate gates. No code or assertion was changed by QA to make the earlier strict
summary expectation pass. Current acceptance: six strict cases plus a separately
qualified summary-accounting/iteration-limit observation, NOT seven completed tasks.

## Complete independent standard suite

881/881 tests passed, exit0, no skips.169 measured code/config files had no changes,
additions or removals during the run. Full-standard.json and full-standard.txt
contain the actual result and output. The twelve QA545b checkpoint tests are already
inside881; the22 rerun QA3156 cases, individual component checks and retrospective
native reads are not added again. This is a local standard run, not the native
Gateway suite or a same-commit server CI receipt. QA leaves publication to3156.
