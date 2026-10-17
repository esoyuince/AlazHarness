# DREAM-D2B2 — bounded paired trial and broker receipt attribution

Date: 18 October 2026. Base `5a5744d93a96c25b72aece441bdebded66f8b36a`.
Branch `alaz/dream-d2b2-wire-27af`. Product implementation: new
`packages/claw-hermes/dream_trial.py`, small guarded routes in existing
`packages/claw-hermes/host_gate_plugin.py`, and operator client
`scripts/dream_trial_once.py`. Sources follow existing MIT Alaz conventions;
no closed-source Codex/Claude code copied.

## What actually works

This is **D2B2 local-broker attribution pilot**, NOT a real external-model
learning acceptance. A local bearer-authenticated operator explicitly starts
a D2B1 SEALED plan already accepted for TESTING by Dream D2A. D2B2 revalidates
D1 candidate identity + latest D2A review revision in the real native SQLite
owner before the plan and again before each arm. If the candidate is withdrawn,
if the scorer source changed, or if a plan field changed, the trial refuses.

For each plan there is ONE durable batch identity. It selects cases from
D2B1 and composes TWO independent chat-completions requests:

- `baseline`: same cases and system prompt, WITHOUT the candidate lesson;
- `candidate`: identical cases, model/output ceiling/temperature, but with the
  source-cited **candidate statement and condition** embedded as UNTRUSTED DATA.

The gold labels, private HMAC oracle key, raw training examples, local personal
files and tool execution permissions are NOT sent in either request. There are
NO tool definitions, retrieval links, model file operations or general proxy.
The two model-request arms are NOT randomized or guaranteed statistically
independent; baseline always goes first. A complete JSON answer list with
exactly one case ID per plan case and a terminal stop reason is required.
Missing IDs, unknown keys, partial completion, extra tool calls, invalid model
identity, over-budget usage and leaked known credentials are refused.

Each arm claims its reservation through the EXISTING ExecutionLedger budget,
then sends once via the EXISTING `ProviderBrokerClient.send(record_view=True)`.
The broker client stores immutable request-view preparation, handoff intent,
and authenticated HTTP response metadata in the same native owner. A trial arm
becomes a validated local broker *observation* ONLY if source ticket,
request digest, broker ID/route, request-view row, HTTP response hash, content
type, native settled budget claim and final answer shape all match. Both arms'
response artifacts are stored in a bounded private native trial record;
no raw credentials, oracle key, or original D1 source file text is copied.
`GET status` repeats the native request-view and ledger consistency checks.

The local process may crash between DB reservation and physical socket write,
or receive the HTTP reply without later DB acknowledgment. Such uncertainty
cannot be reconstructed into a successful completed trial. **No blind replay,
second queue, automatic refund, background scheduling, provider fallback or
active MEMORY.md/SKILL.md write.** A duplicate submitted plan returns the
retained row without new provider reservations. If the second arm fails, the
first arm's evidence remains, but the PAIR is not called complete.

A complete trial status has `responseOrigin` =
`broker_process_http_response_observed`, `providerResponseValidated=true` and
TWO result items, each with `ticket`, `requestDigest`, `requestViewDigest`,
`responseSha256`, `usageOutcome` and the private answer artifact. This does
NOT establish the downstream provider actually ran a real model: local scripted
HTTP responses can produce the same transport evidence. The status ALWAYS
leaves `realModelExecutionVerified`, `physicalProviderInferenceVerified`,
`modelProcessingVerified`, `candidateLessonAppliedByModelVerified`,
`independentOutcomeVerified`, `skillTransferVerified`,
`activeMemoryChanged` and `grantsExecutionPermission` FALSE.

## Existing provider/broker limitations are important

The qualified broker code uses a **literal 127.0.0.1 upstream route**; this
pilot does not add external DNS/Internet access. Real billable inference cannot
be claimed by merely reconfiguring the UI. D3B entire-Gateway OS identity and
egress separation, a real provider/model/price/token budget contract, and a
real independent model task transfer remain OPEN. Only profiles explicitly
configured for the existing separate native broker may opt in. The broker
still trusts same-UID administration; full-OS multi-tenant confinement has
not been demonstrated. If a local synthetic provider responds, it is a
scripted HTTP reply, NOT machine learning.

## Manual configuration and routes

D1 `dream` and D2A `dream_review` must already be enabled. D2B2 is **OFF by
default**. An explicit additional plugin-settings fragment is:

```json
"dream_trial": {"enabled": true, "max_cases": 12, "output_tokens": 256}
```

This is NOT a complete Gateway configuration and was NOT applied to any
private/personal/production profile. Each full two-arm request consumes up
to TWO new provider budget reservations, in addition to the earlier D1 Dream
synthesis. If budget is insufficient, no partial response is upgraded to
success; the reserved cost exposure stays consumed as before.

Local bearer-authenticated, loopback HostGate routes:

```text
POST /alaz/host/v1/dream/trial
  {"plan": { ... exact D2B1 sealed plan ... }}
GET /alaz/host/v1/dream/trial/{plan_id}
```

`POST` never authorizes agent execution; it is explicit model evaluation only.
Feature-disabled installations register neither route. Existing listener
scope, JSON limit, authorization checks and native owner lifecycle apply.

Manual CLI with existing private connection and plan files under ignored
`runtime/dream/`:

```text
python -B scripts/dream_trial_once.py run --connection runtime/dream/connection.json --plan runtime/dream/plan-new.json --output runtime/dream/trial-run-new.json
python -B scripts/dream_trial_once.py status --connection runtime/dream/connection.json --plan-id ev_<64hex> --output runtime/dream/trial-status-new.json
python -B scripts/dream_trial_once.py score --connection runtime/dream/connection.json --plan runtime/dream/plan-new.json --truth runtime/dream/truth.json --key runtime/dream/oracle-key.json --output runtime/dream/trial-score-new.json
```

`score` queries trial status by the authenticated local HostGate, then D2A
review status AGAIN. D2B1 grades the two server-stored answer artifacts
using the local PRIVATE oracle and scorer source hash. Its output reports
`brokerReceiptChainReportedByHost=true` and
`brokerReceiptIndependentlyVerified=false`: this client trusts the local host
status contract; it does NOT independently verify the broker's signature or
attest a physical real-model inference. `observedLocalGainAgainstLockedOracle`
is merely a score on received answers, not certification of real skill transfer.
Neither the HMAC key nor the answer key is POSTed to the Gateway or printed.
Outputs must be NEW private files; no blind POST retry on lost acknowledgment.

## Tests and acceptance scope

Initial 27 synthetic service tests: **FAIL** 2 assertions + 1 error, retained
with complete source SHA/log in `evidence/dream-d2b2-wire-27af/initial-red.*`.
The in-flight D2A revocation path was corrected to mark the trial UNKNOWN
without accepting a result; two test harness assumptions around token limit
and frame signature checks were corrected WITHOUT weakening product gates.
The corrected 65 focused tests (34 native-owner service, 17 HostGate handler,
14 CLI, with one real loopback subprocess) are PASS, no skips. They use the
existing SQL owner/ExecutionLedger and broker client with SCRIPTED `_exchange`;
not a real Linux broker socket/process, actual external HTTP provider, or
paid model. Source hash/test log: `focused-fixed.*`. All previous D1/D2A
acceptance remains scoped to its own exact code commits. Full standard suite
and exact new SHA Git/CI are recorded separately in evidence/status once
observed; do not infer PASS from test discovery alone.

Windows WSL Ubuntu is present, but no `aiohttp` and no Docker command were
available in that isolated Linux runtime at this checkpoint. Native Linux
broker+Gateway end-to-end qualification was **NOT RUN** here. No user runtime,
credentials or provider environment were altered to install dependencies.

## Open work after this slice

D2B2-native: a real Linux broker server + Gateway configured only for a
scripted localhost provider, with the two arms and signed socket/HTTP receipts,
process cleanup and restart/uncertain-ack cases rechecked independently.
Then D3B OS egress; limited REAL MODEL test with pinned model, tariff,
request/response provenance, response author attribution and paired controls.
D2B3: independently run unseen tasks across sessions with and without the
candidate note, prelocked independent evaluator and no oracle leakage. Only
**then** consider a separately authorized/promotable memory proposal. The
current pilot gives NO new autonomy/permission/learning authority.

## Final offline baseline — 2026-10-18T01:12:59.117592+03:00

Full1836/1836 Python unittest PASS, exit0, no skip reports. 256 frozen
source/test/config files byte-identical before/after. The 65 new trial tests
are included in the1836 once. Root static check PASS:1185 checked root
files, 2 source gitlinks,1836 tests DISCOVERED (not extra execution).
Initial 27-test red retained independently. No real Linux broker socket/native
Gateway, external/paid model, learned skill or active memory was run.
Exact code and CI status are appended only after actual Git publication.
