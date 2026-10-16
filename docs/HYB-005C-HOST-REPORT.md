# HYB-005C — read-only host usage and outcome report

Status: implemented; targeted/retained-record checks passed. Full root suite and
exact-commit publication are recorded in status.md when actually completed.
Base: aaf29d46b6496942c01a38f7373a9d56931c7cd0. Native contract remains pinned to
Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780. No existing runtime, provider,
recovery, host dispatch or ledger writer code is changed by this package.

## Delivered interface

`packages/claw-hermes/host_report.py` implements `HostReportInspector` and a plain
console renderer. `scripts/inspect_host_report.py` exposes JSON/text output. This
is the co-located LOCAL host reporting surface, not a new HTTP endpoint, web UI,
a live streaming dashboard, or a public/multi-tenant service.

The request mode reuses `LocalRecoveryInspector` for identity, scope, request
fingerprint, retention, native result and epoch checks. It subclasses only the
classification step and reads the execution ledger within the same existing
read transaction. It uses the production `ExecutionLedger._state/_row` validators
for seals, policy, scope, retained-claim consistency and counters. The path-only
adapter deliberately raises on all write execution; it is not a fake native writer.
No new accounting algorithm or duplicated canonical task owner is introduced.

Both existing SQLite stores are opened with mode=ro/query_only, and connections
are explicitly closed. The base inspector checks versions, epoch and store
identities after its transaction; any detected concurrent change discards the
report rather than returning a mixture of task and usage data. This is a snapshot,
not a lease or a promise that no writer can change state after the check returns.

An explicit `--scope-only` mode supports an auxiliary SDK call without inventing
a run/admission. It reads the existing state.db, validates the trusted context and
policy, and returns `task.classification=not_selected`. A missing ledger stays
unverified; the report never initializes a database or a budget. This mode does
not require a replay-store/task entry and does not claim that no tasks exist.

## The four separate facts

| Section | Evidence and limit |
|---|---|
| `task` | Native terminal classification via the existing recovery inspector. `taskSucceeded` is the native contract outcome, NOT independent achievement of the intended goal. |
| `nativeReportedUsage` | Only a verified terminal RESULT/HTTP aggregate. Nonterminal/unknown task usage is withheld; missing fields are not inferred. |
| `execution.observedUsage` | Provider-reported values in retained claims for the whole profile/principal scope. Missing/unsettled observations remain unknown, with explicit known/unknown denominators. |
| `execution.reservedExposure` | Full configured maximum exposure committed before each attempt, retained after errors. It is NOT a measured invoice or automatic refund balance. |

V1 provider claims carry no trusted run association. Therefore the report always
sets `attributedToThisRun=false`, comparison `comparable=false`, and numerical
run/scope difference to null. Even one visible admission is not evidence that
all scope usage belongs to it. Per-run accounting requires a separately reviewed
binding at the actual call boundary; this package does not retrofit guessed IDs.

A reservation does not prove packet delivery. `wireDeliveryCount` stays null.
Likewise `toolAttempts.handlerReturns` is not an independently verified successful
external effect. The historical fixture observer can count its own actual HTTP
requests, but that separate evidence must not be inferred from a production ledger.
Known token observations have `tokenizerVerified=false`; tariff verification and
billed amount remain unknown. A zero-provider initialized ledger is labelled
`no_reserved_attempts`, not a claim of zero calls through all possible clients.

## Safety and information boundaries

The report performs no claim, settlement, permit issue, dispatch, cancellation,
retry, repair, or refund. All authority fields remain false. Remaining capacity is
informational and explicitly does not grant permission. Quarantined spend remains
visible without unquarantining or replenishing the ledger.

Only trusted local operator context and policy are accepted. API tokens belong in
private runtime input files, not CLI argument values, evidence or Git. The report
omits prompts, outputs, raw request keys, credentials and local filesystem paths.
Status/outcome text uses bounded known enums; arbitrary stored diagnostics are
not echoed. Only a small known completion-reason set is rendered. The pinned
`sourceCommit` names the validation contract; it is not remote runtime attestation.

If scoped request/reservation identity fails, no execution totals are exposed.
A valid scoped reservation without an admission may still show the independently
validated PROFILE budget in a partial snapshot; task canonicalVerified stays false.
A verified task with an unavailable/corrupt/mismatched budget receives a partial
snapshot, not invented zeros. Nonterminal identity verification alone does not
make an observer-supplied usage value canonical. No underlying recovery behavior
was loosened to manufacture a successful report.

## Local use

```powershell
python -B -X utf8 scripts/inspect_host_report.py --context runtime/report-context.json --policy runtime/report-policy.json --request runtime/report-request.json --format json
python -B -X utf8 scripts/inspect_host_report.py --context runtime/report-context.json --policy runtime/report-policy.json --scope-only --format text
```

The paths above are caller-supplied private local files, not files automatically
created in the repository. Context fields are `profile_home`, `api_token`, `epoch`,
`instance_id`. Policy is the exact existing `ExecutionPolicy` object shape. Request
fields are `body`, `idempotency_key`, and the observed native run object `observed`.
Never copy credentials from an unrelated personal profile to populate these files.

Exit0 means a verified report/scope snapshot, NOT task success. A correctly
reported failed summary can exit0. Partial/unverified evidence exits2. An explicit
scope-only read does not require or fabricate a request key. Inputs and outputs
are bounded, and malformed private input produces a bounded diagnostic.

## Tests and historical-native replay of the reader

The initial primary39 checks passed. Independent QA9256 found two reporting
issues (four negative cases): nonterminal unverified usage was exposed as complete,
and arbitrary unused native status/outcome strings could leak. The product was
corrected and the SAME30 QA tests passed without relaxing their assertions.
Fourteen further scope-only tests cover SDK unknown usage, no invented task,
missing stores, table/view rejection, scope/policy/epoch mismatch, query-only
closure, WAL concurrency, quarantine and the actual console interface.
The83 focused tests belong inside the final root-suite count, not on top of it.

`scripts/verify_host_report_retained.py` executes the current module and CLI
against seven retained HYB005B test profiles. Five are admitted native tasks;
SDK retry is scope-only; missing-price deliberately returns an unverified exit2.
All seven expected observations passed with unchanged DB/config/receipt bytes and
unchanged measured source. These are seven NEW READER checks, NOT seven new
Gateway, agent, SDK-provider or paid-model executions. Real model calls remain0.

The actual iteration-summary report preserves native failed and
`max_iterations_reached(1/1)`, native usage120/20/140, profile-scope provider usage
240/40/280, and327680 tokens/393216 micro-USD RESERVED exposure. This accurately
shows a scope difference without claiming per-run cost equivalence or an invoice.
The SDK retry report shows one reservation, UNKNOWN observed usage and no selected
task. Example outputs and receipts are in `evidence/hyb-005c/retained-reports/`.

```powershell
python -B -m unittest discover -s tests -p test_host_report*.py -v
python -B -X utf8 scripts/verify_host_report_retained.py --source-workspace C:\Antigravity\AlazHarness --output C:\Antigravity\AlazHarness\runtime\fresh-report-verification
```

The retained-record experiment requires the original ignored test profiles and
unexpired native retention. Do not change the clock or repair an old record to
force it to pass after expiration. Standard CI uses fresh synthetic stores and
does not require these profiles, native Hermes installation, or network access.

## Remaining work

This closes the local read-only reporting slice, not complete HYB-005 or M1/M2.
Next is HYB-005D: explicit isolated credentials and mandatory egress authority,
followed by qualified real-provider model/token/tariff bounds. A future HTTP report
surface must authenticate, preserve these scopes and snapshot limits, and prove
that no retention/hydration side effect is hidden behind a GET. Do not add a
second writer to achieve it. Per-run provider binding, tool outcome/goal validation,
remote providers, general OS sandboxing and learning-transfer remain separate gates.

## Final local delivery checks

The full root suite executed964 tests, all passed, no skips or code/config drift
across177 measured files. The83 report-specific cases are included in964.
The independent QA9256 full run also executed964/964; repetition is not another
964 unique cases. The seven retained-profile report/CLI checks remain separate
from standard tests and are not new native runs. Source databases, profile
configs and historical receipts stayed unchanged.

Publication hygiene and staged-diff checks passed. Only the selected report,
CLI, test, documentation and sanitized evidence files are published. Exact native
host/provider credentials and request keys from the test profiles were checked
against the selected text and were absent. This bounded check is not a complete
security audit. Same-commit server CI is read only after push; no old CI result is
inherited. The existing runtime enforcement and source pins remain unchanged.
