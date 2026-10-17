# Dream D2B1 — Sealed held-out paired evaluation (offline scorer)

**17–18 October 2026 · alaz/dream-d2b-eval-8d20**

## Acceptance boundary

This is **D2B1**, the first measurable offline evaluation slice. It is **not
full Dream D2B learning/skill transfer**. Dream D1 creates bounded
source-cited CANDIDATES; Dream D2A can classify a candidate as
`accept_for_testing` via a currently revision-pinned review. D2B1 creates an
immutable-by-hash paired task **plan**, compares two externally supplied answer
files against an operator-private answer oracle, and reports counts. It does
not call a model, certify the authorship of model answers, write active memory,
write skills, grant tools, select goals, schedule itself, or promote a lesson.

The only Gateway interaction in the operator client is a GET of the current D2A
review, before sealing and again before scoring. This is an already-authenticated
loopback endpoint. A profile/runtime without an accepted D2A candidate cannot
start the manual plan. An outdated/rejected decision is a hard refusal.

### Data trust

Private training prompts, held-out prompts, gold labels and answer files stay
under **ignored `runtime/`**. The gold file is never sent to the local Gateway
by D2B1; a public task plan contains prompts and an HMAC-SHA256 commitment to
the gold file, but **not the labels**. A separate, cryptographically generated
256-bit oracle key remains in a private file and is not printed. The private key
must not appear in the plan, response files, versioned evidence, or chat.

The plan also locks the current evaluator Python file SHA-256, exact task IDs,
training prompt hashes, policy, candidate ID, D1 batch digest and D2A review
revision. Re-sealing after seeing model answers is NOT an honest held-out test.
The scorer checks the evaluator's own source file hash and HMAC commitment
before scoring. This defends routine accidental edits and low-entropy answer
key guessing **provided the oracle key remains secret**. It is not a signed
artifact or defense against a privileged operator rewriting all files.

Novelty checks reject *exact* duplicated training/held-out prompt hashes, but
cannot prove semantic novelty, absence from web/model pretraining or actual
concealment from a compromised inference process. These are measured limits,
not hidden assumptions.

## First supported evaluation family

The evaluator supports a deliberately small deterministic classification task:

- At least **4 unique training prompts**, at most 128.
- **12–48 distinct held-out prompts**. A question is at most 2 KiB UTF-8.
- A gold file with one unique case ID and one exact expected answer for each
  held-out case, with at least 3 distinct expected answer labels.
- A baseline arm and a candidate-lesson arm with exactly one answer per case.
  Missing/extra/repeated cases and wrong arm or plan identity are rejected.
- Grading is `exact_strip_v1`: surrounding whitespace is ignored; case,
  spelling, Unicode and semantic equivalence are not normalized.

The locked policy requires at least **3 previously wrong cases improved**, **0
previously correct cases regressed**, and a positive net change. These are
sample acceptance *signals*, not a statistical claim or independent proof.
The reported fields include `baselineCorrect`, `candidateCorrect`, `wins`,
`regressions`, `netGain` and `observedLocalGainAgainstLockedOracle`. The result
always declares `responseOrigin=unverified_external_artifacts`,
`realModelExecutionVerified=false`, `independentOutcomeVerified=false`,
`skillTransferVerified=false`, `promotableMemoryProposal=false`,
`usableAsMemory=false`, `activeMemoryChanged=false`,
`grantsExecutionPermission=false`, `automaticTrigger=false`, and
`additionalModelCalls=0`. **A positive local score must never be displayed as
"Alaz learned a skill".**

## Manual operator workflow

The D2A manual review feature must be enabled on an already-qualified local
Gateway. These D2B1 files are **not** a complete Gateway configuration and
nothing was applied to the user's production/personal profiles.

Prepare six PRIVATE files under `runtime/dream/` (the directory must exist).
The existing D1 `connection.json` includes `base_url` and `token` and must
remain private. Example *shapes only* (no actual answer key or credentials):

**training.json:** `{"version":1,"prompts":["training example 1", "... four or more distinct ..."]}`

**cases.json:** `{"version":1,"family":"synthetic_triage","cases":[{"caseId":"case_01","prompt":"..."}, ...]}`

**truth.json:** `{"version":1,"answers":[{"caseId":"case_01","answer":"GREEN"}, ...]}`

The plan generator never writes the answer labels to the plan and refuses
mismatched case coverage or distributions. All candidate and plan IDs shown
below are placeholders and must be taken from the current D1/D2A status:

```text
python -B scripts/dream_eval_once.py key --output runtime/dream/oracle-key-new.json
python -B scripts/dream_eval_once.py seal --connection runtime/dream/connection.json --batch-id <64hex> --candidate-id dc_<64hex> --training runtime/dream/training.json --cases runtime/dream/cases.json --truth runtime/dream/truth.json --key runtime/dream/oracle-key-new.json --output runtime/dream/plan-new.json
```

A separate authorized model runner must then generate two independent answer
files for the SAME sealed cases, same model/version/settings/budget, with the
candidate lesson included ONLY in the candidate arm. The runner must not see
the gold file or the oracle key. The D2B1 scorer does NOT implement that
runner because the real-model/D3B broker authority/egress gates remain OPEN.

Each private response file schema is:

```json
{"version":1,"planId":"ev_<64hex>","arm":"baseline","answers":[{"caseId":"case_01","answer":"GREEN"}]}
```

The candidate response file uses `"arm":"candidate"`, same planId and exact
case IDs. Each answer is an externally supplied raw string, not a verified
model output. To calculate the score:

```text
python -B scripts/dream_eval_once.py score --connection runtime/dream/connection.json --plan runtime/dream/plan-new.json --truth runtime/dream/truth.json --key runtime/dream/oracle-key-new.json --baseline runtime/dream/baseline.json --candidate runtime/dream/candidate.json --output runtime/dream/score-new.json
```

All output files MUST be new and under ignored `runtime/`; a repeated invocation
cannot overwrite the first plan or score. A failed/unknown read does not retry
a POST or mark success, and errors do not disclose the oracle key or token.
No D2B1 endpoint, DB table, scheduler, executable runner or second budget was
added to the Gateway.

## Synthetic end-to-end score and negative controls

The local tests use a synthetic triage family with 12 questions, 3 gold labels
and fictional prior/trial answers. The **scripted** prior responses score 8/12,
scripted candidate responses score 12/12 (4 net wins, no regressions).
`evidence/dream-d2b-eval-8d20/synthetic-demonstration.json` records this
**synthetic numerical result only** and explicitly states
`independentOutcomeVerified=false`. This demo proves that the deterministic
scorer works; it does NOT show a model improved by reading a Dream note.

Negative tests include forged model permission claims, stale/rejected review,
changed gold or private oracle key, changed scorer code, duplicate/overlapping
prompts, missing or substituted trial cases, regressions, tiny samples and
malformed/tampered plan IDs. There is a real synthetic loopback GET+subprocess
key→seal→score test with no model call and no HTTP POST.

## Next acceptance gates — NOT RUN

**D2B2 real-model trial:** First close D3B isolated Gateway/OS identity/egress,
model tariff/token and broker attribution. Pin one task family, model/version,
source candidate/batch, hash of grading code and unseen held-out corpus BEFORE
calling the provider. Generate baseline/treated answers through the existing
budget ledger and isolated provider process. Bind every trial answer to a
verified provider request/response receipt (not an operator-supplied JSON
claim). Duplicate/failing/unknown provider states do not get success credit or
a blind replay/refund. Rechecking D2A revision immediately before any output
is used is mandatory.

**D2B3 genuine transfer:** Run held-out cases from a separate independent
harness, use enough paired controls to distinguish variance from benefit,
measure outcome on a fresh task across sessions with the lesson and without,
prevent answer-key leakage, and record adverse effects. Only then create a
*proposable* memory/skill improvement. Real active-memory adoption would be a
separate explicit privileged operation and approval boundary, not part of D2B1.

No licensed Codex or Claude Desktop code was copied into our public MIT repo.
All changes in this slice are new original Python, tests and documentation.

## Exact local acceptance — 2026-10-18T00:27:40.158885+03:00

Full project offline unittest 1771/1771 PASS, exit0, skipped0, 251 measured
code/test/config files unchanged. Includes D2B1 39 scorer + 18 CLI tests once.
Static `ci_check.py` PASS discovered1771, checked1169 tracked root files and
2 source gitlinks; **static test discovery is not 1771 additional executions**.
The 12-example 8→12 local demo uses scripted answer files. Real-model trials,
native D2B Gateway, provider attribution and held-out real skill verification
remain NOT RUN. See evidence/dream-d2b-eval-8d20/full-standard.json,
root-static.json, source-freeze-before-full.json and synthetic-demonstration.json.

## Publication and CI — 2026-10-18T00:32:57.331505+03:00

Code commit `d421e75e58c0a6e2db4cf0b8ca8f304fe677337d` pushed to `alaz/dream-d2b-eval-8d20`.
GitHub `alaz/local-ci` **SUCCESS** (status 56608074524,
2026-10-17T21:32:01Z). The status API does not expose the remote test count.
The independently observed local full1771/1771 result,251 source SHA values
and scripted trial are bound to the published code commit; doc-only follow-up
CI will be checked as a SEPARATE commit. This does not close D3B or certify
real model learning. `main` unchanged; user worktrees preserved.
