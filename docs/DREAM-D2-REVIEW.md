# Dream D2A — Manual candidate review and deterministic deltas

Date: 17 October 2026. Base commit: d3df140f38e15a34f7962c3338391413dd64514b.
Branch: alaz/dream-d2-4b83. Status: initial implementation and focused checks
complete; full standard, Git publication and CI tracked independently.

## Implemented behavior

This is the first **D2A** slice, NOT all of Dream D2. D1 creates untrusted
candidate lessons and verifies exact quote membership. D2A lets an explicitly
authorized local operator mark each candidate `accept_for_testing`, `reject`, or
`defer`; it saves an append-only decision *event list* and current decision
projection in the existing native SQLite owner. A deterministic revision acts
as an optimistic compare-and-swap token across concurrent decision writers.
Stale revisions must be refreshed, never automatically replayed. Idempotent
same-decision requests with the CURRENT revision create no new event. The
structured `reasonCode` is an operator classification, not proof of semantics.

`accept_for_testing` means **eligible for a future independent benchmark**, not
true/understood/learned/promoted. Every returned D2A report keeps:

- `evaluationStatus: not_run`, `independentOutcomeVerified: false`
- `modelInferenceQualityVerified: false`, `conclusionVerified: false`
- `activeMemoryChanged: false`, `skillTransferVerified: false`
- `grantsExecutionPermission: false`, `automaticTrigger: false`
- `additionalModelCalls: 0`

D2A NEVER calls a model, executes a tool, writes MEMORY.md/SKILL.md, injects an
agent instruction, edits the D1 source batch, grants network/file permission,
creates a scheduler, creates a new DB, or triggers new agent work. The review
row references a D1 `batchDigest` and candidate IDs; it does not duplicate
candidate statements, source text, paths, quoted secrets or tool contents.
Its SHA-256 digest is a local consistency checksum, not an external signature.

Before every read or write, D2A revalidates the *persisted* D1 candidate
batch through its `_history` validator in the same native transaction: D1
terminal status, provider claim, episode/owner scope, candidate identities,
source-reference metadata and non-authoritative flags. This **does not reopen
or revalidate expired original source text/terminal retention**. It annotates
the frozen D1 evidence only; no fresh source-read credit is granted. The
review uses D1's existing ExecutionLedger owner: no second writer or budget.

## Diff and no-change behavior

`diff(batchId, baseRevision)` accepts ONLY the batch seed revision or a previously
stored exact event revision. A malformed or invented baseline is rejected.
For a valid base, it reports newly decided, changed, unchanged and withdrawn
`accept_for_testing` entries. It marks independent testing required only when
a candidate is newly accepted in this **net diff**. Repeated or reversed
changes that restore the same projection report no net changes and zero extra
model calls. This is **not** Codex's automatic Phase2 global memory consolidation:
no memory workspace or global summary is modified.

## Config and local endpoints

D2A is OFF by default, and requires D1 to be enabled on the already-qualified
Linux separate-provider-broker path. In the same configured host-gate plugin
settings as D1, add:

```json
"dream_review": {"enabled": true, "max_events": 32}
```

This is only a plugin-settings fragment, NOT a complete Gateway configuration.
Nothing in personal/production profiles was changed or started by this work.
Only the existing local host bearer is accepted (no profile/room tokens,
extra JSON fields, redirects, remote listener or permission escalation):

```text
GET  /alaz/host/v1/dream/review/{batch_id}
POST /alaz/host/v1/dream/review
     {"batchId":"<64hex>","candidateId":"dc_<64hex>",
      "decision":"accept_for_testing|reject|defer",
      "reasonCode":"evidence_sufficient_to_test|duplicate|conflict|insufficient_evidence|out_of_scope|needs_benchmark|operator_deferred",
      "expectedRevision":"rv_<64hex>"}
POST /alaz/host/v1/dream/review/diff
     {"batchId":"<64hex>","baseRevision":"rv_<64hex>"}
```

For `accept_for_testing`, reason MUST be `evidence_sufficient_to_test`.
These are bounded enums; a model-generated sentence cannot become a decision
or authority. Review endpoints are registered only when opt-in review is on;
read/write routes check the native host bearer, supported scope and readiness.
Capabilities expose `dreamReviewMode=manual_for_testing_only`.
The bearer is operator authority but is NOT independently a proof that a human
physically reviewed the lesson. Do not claim human judgment where a scripted
client may hold this credential.

## Manual client

First obtain the D1 `batchId`, `candidateId` and D2A `revision` from the
local authenticated D1 status/read endpoints. Keep the same private D1 CLI
connection JSON file under ignored runtime/; output must be a NEW path.

```text
python -B scripts/dream_review_once.py --connection runtime/dream/connection.json --batch-id <64hex> --inspect --output runtime/dream/review-first.json
python -B scripts/dream_review_once.py --connection runtime/dream/connection.json --batch-id <64hex> --candidate-id dc_<64hex> --decision accept_for_testing --reason-code evidence_sufficient_to_test --expected-revision rv_<64hex> --output runtime/dream/review-decision.json
python -B scripts/dream_review_once.py --connection runtime/dream/connection.json --batch-id <64hex> --diff-from rv_<64hex> --output runtime/dream/review-delta.json
```

The manual client uses literal loopback, does not consult proxy settings or
follow redirects, never retries a POST after unknown delivery and never
overwrites an existing output file. Exit0 means a validated review response,
not successful learning. Exit2 means uncertain/invalid local response; read
status with a known batchId rather than blindly replaying. Private bearer,
review notes and source excerpts do NOT belong in Git.

## Explicit limits and D2B acceptance still OPEN

- **D2B independent held-out transfer and model-quality evaluation: NOT RUN.**
  Review `accept_for_testing` does not score a new job or confirm a useful lesson.
- **D2B active memory/skill adoption: NOT IMPLEMENTED.** A verifier must lock
  task set, evaluator hash and baseline first; test previously unseen cases
  with/without lesson before any controlled proposal for promotion.
- Trusted existing-memory conflict reconciliation beyond D1 candidates is not
  implemented. An operator `conflict` reason is not a semantic conflict proof.
- Automatic Dream idle/job-completion trigger and goal selection are disabled.
- D3B whole-Gateway OS identity/egress isolation, real model/tariff/token
  verification and full M1/M2 learning/skill transfer remain open.
- Review rows bind to the current native owner epoch and instance; cross-restart
  reattachment/migration of older review rows is NOT qualified and may be refused.
  A stored row is not a claim of unconditional cross-epoch readability.
- Review decisions are retained as immutable event history until explicit
  future housekeeping. There is no auto-prune and no automatic retry/recovery
  of D1 unknown batches; bounded review event count fails closed.
- Local record hashes are NOT protection from an adversary with privileged
  full database access. SQLite query-only semantics do not guarantee no WAL/SHM
  helper files (existing G01 remains open).

## Test evidence

Initial focused results: 25 native-owner service tests, 18 actual host HTTP
middleware-handler tests, 14 loopback/manual CLI tests = 57 PASS. All use
synthetic D1 provider replies, scoped temporary SQLite stores and/or local
loopback; they are not live production users, real model inference or a new
native Gateway/Docker qualification. Full standard exit/result, final source
hashes, Git/CI results and any failures are recorded under
`evidence/dream-d2-4b83/` and `status.md` only when independently observed.
A successful root static gate discovers tests; discovery is not the same as
executing all tests. No Codex or Claude proprietary code was copied.

## Full standard acceptance — 2026-10-17T22:31:03.819657+03:00

1714/1714 offline unittest PASS, exit0, no skips reported. 247 measured
code/test/config files byte-identical before/after the run; 57 D2A tests
are INCLUDED in 1714 once. No actual native Gateway/paid model inference,
no held-out new task and no independent learned-skill verification. Detailed
local log and source hashes are in evidence/dream-d2-4b83/.
