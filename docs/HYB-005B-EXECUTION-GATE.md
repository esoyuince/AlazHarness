# HYB-005B — physical provider and guarded file execution

Status: local scoped verification complete; publication/CI pending; continuation3156. Base30b205f.
Prior0d37/3723 receipts keep their historical scopes; no acceptance is inherited.

## First implemented slice (not general all-provider M1 acceptance)

One native default profile; a dedicated provider URL on the SAME native aiohttp
application and SessionDB owner. Model credentials are distinct from host bearer.
Only operator-configured literal-loopback OpenAI-compatible chat-completions is
qualified in this slice. Production HTTPS providers and network/process fencing
remain separate; no remote model or paid request is used during acceptance.

The provider route reserves one PHYSICAL HTTP attempt, full configured maximum
input+output token exposure and integer micro-USD price exposure in native
state_meta BEFORE calling the provider. It never retries, follows redirects or
refunds unknown usage. SDK retry / auxiliary / summary requests hitting that
route consume separate reservations. Usage is observed, not a refund authority.
A token ceiling is a declared trusted provider bound; we do not pretend that
UTF8 bytes are exact tokenization or that fixture prices are actual invoices.
Unknown prices, changed policy, stale owner, missing history, oversized or
unsupported requests refuse. Actual tariff/model capability qualification is OPEN.

Implemented module execution_budget.py: ExecutionPolicy, ExecutionLedger with
claim(kind, fingerprint), settle(ticket, usage, outcome), snapshot(). Every claim
is retained with totals; constructor needs existing native db + LocalRecoveryContext.
Kinds provider/read_file. Limits count all physical attempts even failures; no
second task queue, provider scheduler or transcript writer. NO claim that commit
and network delivery are one atomic operation. Restart retains spent exposure.

GuardedFileTools calls the ORIGINAL native file handler after exact allowed-file,
plain-text size/path, native-owner and tool-attempt checks. The plugin uses native
explicit override registration, not observer exceptions. File write/patch/search
are denied. Allowed paths are operator-supplied, not model supplied grants. This
first read-only subset is not a malicious-same-process/OS-user sandbox; TOCTOU
and arbitrary tool family/side channel coverage remain OPEN. The host path must
require initialized execution policy and live guard identities before dispatch.

No new plugin alone is called a universal perimeter. Unextended Hermes with raw
credentials remains outside this dedicated host contract. Exact evidence scopes
will be recorded at completion in status.md and evidence/hyb-005b/.

## Execution-required client mode

HostGateClient({requireExecution:true}) requires version1 capabilities before every
prepare/dispatch and sends X-Alaz-Execution-Version:1. The updated server rejects
that header when execution is not installed; old host-only mode remains explicit
backward compatibility. There is no fallback from execution-required to host-only.
This is a trusted local operator profile; registry and model credentials are not
safe against an attacker who can run arbitrary code in the same OS process.

Source validation: config/execution-gate/source-lock.json. Response handling
buffers SSE up to4MiB and30seconds; it is NOT low-latency streamed delivery. All
frames and response model identities are checked; contradictory usage quarantines
the profile budget without refund. Transparent stream/cancellation and remote
provider credentials/egress fencing remain separate acceptance work.

## Live configuration boundary

The normalized, immutable startup execution-settings digest must still match the
native PluginContext configuration at readiness and ledger access. Missing, changed
or unreadable settings refuse; a changed budget is not silently reset, a revoked
file is not retained as a new permission, and another provider is not auto-adopted.
The comparison reuses the native current-config loader and its caching behavior;
no claim of instantaneous disk-change notification or atomic config+network I/O
is made. The original source is left untouched; this check is Alaz integration.

## Qualification state

Final native scenarios use an explicit180-second readiness allowance (legacy70
remains the launcher default), preload the already installed SDK class during
measured startup, and run serially. No SDK client/inference is created by preload.
The initial70-second failures, cold-SDK observation timeout and native Windows
reopen fault are retained and not relabeled successful performance acceptance.
Native normal includes clean reopen, no budget refund, plus live allowlist
revocation rejection in the completed isolated test profile before restoring
that test configuration for restart. All real-provider tariff, exact tokenization,
global egress/credential isolation, cancellation latency and M1/M2 gates stay open.

## Final native measurements — 16 October 2026

Seven fresh serial final-code scenarios met their narrow execution/budget
expectations. Six pass the strict post-run outcome/denial verifier. The iteration-
limited summary is explicitly NOT a successfully completed task: its separate
strict task-success assertion failed and is preserved unchanged.

| Scenario | Physical upstream POSTs | Successful native reads | Measured outcome |
|---|---:|---:|---|
| normal | 2 | 1 | Completed output retained through a clean new Gateway generation; no refund or repeat. |
| provider-limit | 1 | 1 | Next call refused with provider_attempt_limit; no second upstream POST. |
| tool-limit | 2 | 0 | Actual tool result reports tool_attempt_limit. |
| denied-write | 2 | 0 | Actual tool result reports tool_not_allowed; independent target file remains absent. |
| sdk-retry-limit | 1 | 0 | One actual auxiliary-SDK invocation with retries enabled; retry stopped by native provider budget route. No job admission. |
| summary | 2 | 1 | Iteration-limit summary text retained and both calls charged; task status remains failed. |
| unknown-price | 0 | 0 | Missing/invalid price refuses initialization; guarded host path404, no job or reservation. |

All eight final Gateway process lifetimes (normal opens twice) closed cleanly.
No final source drift, fixture errors, paid inference, or blocked non-loopback
attempts were observed. The test observer is not an OS sandbox and this does not
prove unconfigured clients cannot use another egress path. All earlier failed,
drifted, unqualified and blocked-network receipts remain preserved as historical
evidence; the current zero-count result does not explain their unknown targets.

The normal case additionally revoked the completed TEST profile's read allowlist.
Real capabilities503 and provider metadata403 followed without another model call
or budget mutation. That test config alone was restored before reopening.

## Summary scope correction and usage projection follow-up

The strict verifier expected the summary task to be completed and rejected it.
The unmodified native API explicitly classifies iteration-limited/incomplete
results as failed (api_server_runs.py:185-200). The native finalizer still obtains
a final summary (turn_finalizer.py:130-163; chat_completion_helpers.py:2309-2363).
A returned summary is thus not proof the requested task completed. We retain the
failed strict assertion rather than weakening it or rewriting native status.

Observed summary ledger usage totals240 input/40 output tokens across two physical
requests, while the Gateway run reports120/20. Both full conservative reservations
remain held; the budget gate does not rely on the smaller run aggregate. Any host
reporting must distinguish physical-attempt usage, reserved exposure and task
outcome. This remaining projection work is HYB-005C; it is not silently fixed here.

Receipts: evidence/hyb-005b-close-3156/final-native-suite.json,
summary-strict-outcome.json and native-<scenario>.json. The rechecks are read-only
comparisons to the actual retained SessionDB, not additional native executions.
The current suite supports the local text-only execution slice, not complete
M1/M2, all-provider budgeting, verified tariffs, egress isolation or actual learning.

## Standard and component closure

Current root discovery881/881 PASS, exit0/skip0/drift0 across169 measured code/config
files. Actual opt-in aiohttp component matrix27/27 PASS on the same product sources;
its synthetic profile/owner/registry ports remain disclosed. See full-validation.json
and http-final-matrix.json under evidence/hyb-005b-close-3156. Exact-commit server CI
is recorded after publication, not inferred from this local run.

## Independent QA545b and summary semantic resolution

The separately staged QA545b package was read before integration. Its twelve
checkpoint tests are included (not added again) in the same881-test measured
suite, and its independent881/881 run also passed. Six strict native cases and
normal live-revocation/reopen records were corroborated without a new native run.

The full native terminal RESULT, not merely the admission outcome, resolves the
summary status: completed=false and max_iterations_reached(1/1). The existing
LocalRecoveryInspector returns canonical_terminal_verified, outcome=failed,
taskSucceeded=false, retryAllowed=false. Therefore no native corruption or current
recovery-inspector bug was established by the earlier admission-only comparison.
The original strict task-completed assertion remains failed because it was not
the proper success expectation for an iteration-limited job. The summary budget
path is qualified separately, never converted to successful task completion.

The remaining usage distinction is substantive: two provider claims total240/40
while the native run aggregate reports120/20. HYB-005C should expose these scopes
separately and reuse the already correct inspector's task outcome. Evidence:
docs/research/HYB-005B-QA545b.md and evidence/hyb-005b-qa545b/summary-terminal-semantics.json,
summary-inspector-observation.json, full-standard.json. No primary product or
upstream file was changed by that independent reviewer.
