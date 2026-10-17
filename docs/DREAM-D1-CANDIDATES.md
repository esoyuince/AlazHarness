# DREAM-D1 — Manual, evidence-linked candidate memory review

Date: 17 October 2026. Implementation: E458, independent QA: 61A9.
98F0 resumed interrupted publication without changing product/test source.
Base commit: f23079dc7c3312da93b00139f15ef89717cccf16.
Status: scoped implementation and prior final native QA qualified; resumed
standard/opt-in verification and exact-commit publication are recorded separately.

## What exists now

A configured local Gateway can explicitly review selected TERMINAL jobs, pass
bounded historical excerpts through the existing budgeted provider broker, and
persist suggested observations, lessons or cautions as CANDIDATES. It is not
just a packet builder: DreamService.run performs one synthesis request and
validates its returned note structure and exact citations before persistence.
The synthesis provider in acceptance tests is SCRIPTED, not real inference.
This qualifies the running pipeline, not the quality of autonomous reflection.

New product module: packages/claw-hermes/dream.py. Existing host_gate_plugin.py
registers the optional HTTP routes; scripts/dream_once.py is a manual client.
The same Hermes native state owner, recovery/evidence reader, ExecutionLedger,
private broker and normalized request-view records are reused. No second DB,
agent engine, scheduler, skill writer or tool execution loop is introduced.
The Dream maintenance request itself is not a new Hermes agent task.

## Input and scope

The operator supplies the original body/idempotency_key/observed triples for
selected jobs in the same configured profile. Caller-provided proof text is not
authority. Existing authenticated terminal identity, generation, retention,
SQLite-version and file-identity checks must pass; active/missing/expired or
changed sources do not silently become lessons. A verified failed terminal job
may supply a failure observation, not proof of successful learning.

For each retained final answer/tool result, at most 2048 UTF-8 bytes of its
redacted prefix are offered. Truncation, redaction, native execution attribution
and original-source coverage remain explicit. This is NOT original-file range
coverage and does not reopen a path named by historical text. At most 32 excerpts
and 64 KiB of source context are selected across up to 8 jobs (default 4).
Known host/SDK/broker credentials are removed or rejected; this is not a universal
secret detector, privacy anonymizer or malicious-provider encoding defense.
The quoted content and candidate notes may be sensitive and are private output.

## Candidate review, not active memory

The synthesis request has no tools and asks for bounded JSON notes with kind,
statement, condition, citations and relatedCandidateIds. Each note must cite an
existing supplied evidenceId and an exact nonempty quote from the SHOWN excerpt.
The quote byte range and view hash are stored with deterministic candidate ID.
Unknown references, invented quotes, malformed/extra fields and duplicate notes
are rejected. A valid quote proves quotation membership, NOT logical entailment,
truth, generalization, model comprehension or goal achievement.

Every accepted note remains status=candidate, usableAsMemory=false,
conclusionVerified=false, skillTransferVerified=false and
grantsExecutionPermission=false. Nothing is injected as agent instructions.
Existing MEMORY.md, memory-provider contents, skills and rules are not edited.
Prior-note comparison covers up to 16 PREVIOUS DREAM CANDIDATES, not a complete
reconciliation of the existing trusted-memory store. Exact duplicates can be
marked duplicateOf; related notes stay candidates, never independent evidence.

## Persistence, cost and interruption

A batch identity derives from selected source excerpts, Dream policy and prompt
version. A native transaction reserves the new batch before the one provider
attempt. Same-batch calls return the retained result instead of a new synthesis
when the source read is still eligible. Unresolved prepared/running/unknown
batches block different batches; there is no blind retry or row deletion.
The completed result can be read through GET with its batch ID.

Provider calls use the existing profile-wide budget; Dream does not get a second
budget. Its configured output ceiling must fit that policy. Reservation, egress
and request-view phases remain distinct. Lost acknowledgement, cancellation,
provider failure or storage uncertainty are not refunded or upgraded to success.
Sources and configuration are rechecked before accepting candidates. A valid
response is settled even if its proposed notes are rejected. Unknown results
contain no accepted candidates. No recovery/abandon action for unresolved Dream
batches is added here; this remains a later explicit operator workflow.

History is bounded to 128 batches/4 MiB; the limit refuses rather than discarding
old notes. No automatic compaction, garbage collector or candidate promotion is
implemented. Current credentials are checked again on returned candidate data.
As with existing storage, record digests are consistency checks, not signatures
against a privileged database editor. Read-only status does not promise zero
SQLite WAL/SHM filesystem effects (existing G01 remains open).

## Configure and run manually

Dream is OFF by default. On an already-qualified configured Linux broker Gateway,
add the following to plugins.entries.alaz-host-gate.settings alongside the
existing policy/execution configuration. This fragment alone is not a complete
Gateway configuration and was not applied to personal or production profiles:

```json
"dream": {
  "enabled": true,
  "max_sources": 4,
  "max_notes": 6,
  "output_tokens": 2048
}
```

Local authenticated routes: POST /alaz/host/v1/dream with {"sources": [...]};
GET /alaz/host/v1/dream/{batch_id}. Absent/disabled configuration registers no
Dream routes. Capabilities say dreamMode=manual_candidates_only. Current bearer,
profile restrictions, request-size/encoding checks and runtime ownership apply.
There is no remotely exposed service or automatic wake-up.

Create private local JSON files yourself for the intended configured profile:
connection.json has exactly base_url (http://127.0.0.1:PORT) and token;
sources.json is an array of exact prior {body,idempotency_key,observed} requests.
Keep credentials and outputs under ignored runtime/, never public evidence.
The parent output directory must exist and the output file must be NEW.

```text
python -B scripts/dream_once.py --connection runtime/dream/connection.json --sources runtime/dream/sources.json --output runtime/dream/candidates-new.json
python -B scripts/dream_once.py --connection runtime/dream/connection.json --batch-id <returned-64-hex-batch-id> --output runtime/dream/status-new.json
```

The CLI only connects to literal loopback, never follows redirects or retries a
POST. Exit0 means idle or a completed CANDIDATE batch, not learned skill. Other
states exit2. On a lost POST reply use a known batch ID for status rather than
assuming nothing happened. Recovering a batch ID when its reply was lost is not
provided by a dedicated list endpoint in this first slice.

## Final accepted tests and four real process scenarios

Prior independent final-source standard: 1657/1657 PASS, no skips; 243 measured
product/test/script/config files unchanged. Includes 40 Dream +12 CLI +10 new
input cases once (62 additions over 1595). 32 independent API and16 independent
HTTP tests are OPT-IN, separate from standard CI. 98F0 reruns the same standard
and48 opt-in tests; see evidence/dream-d1-e458/recovery-98f0 for fresh receipts.
Old1595/1605/1635 results retain their earlier scope, not this final total.

61A9's four FINAL fresh Linux profiles use dream.py SHA256
07283756339da89a420c40f9fe80fc4f8ffaef26b903c65129cfa135a66d415a:

| Scenario | Actual outcome |
|---|---|
| Valid synthesis | One persisted candidate; exact quote/source and request/claim binding |
| Invented citation | rejected, zero candidates; provider cost remains counted |
| Lost synthesis connection | unknown, zero candidates; reservation retained |
| Feature disabled | no Dream row or Dream provider request |

Total: 11 scripted origin requests, of which3Dream requests;4real isolated reads
for the source jobs;4Gateway+4broker lifetimes. Four exact Docker IDs and four
sockets were checked absent. Repeated identical Dream requests added no provider
call. Real CLI status GET matched all3enabled results. A stdlib-only independent
reader reconstructed the3110-byte Dream request and compared source/record/quote/
candidate IDs, actual origin-byte hash, ledger and request-view phases.

The native sample caution is deliberately scripted test data, not proof that a
real model invented a useful lesson. No real inference or paid call occurred.
The4early v1 scenarios are preserved separately and not counted as4more final
acceptance scenarios. 98F0 did NOT replay native experiments during publication.
Original native profiles/private credentials remain local and are not published.

## Preserved issues and fixes

D61-G01: a credential containing a JSON-escaped character bypassed checking only
serialized text. Fixed by recursively checking decoded strings/keys.
D61-G02: a nonexistent provider ticket could survive status validation after a
resealed row. Fixed by matching actual claim identity, epoch, instance and outcome.
D61-G03: changed note content with stale candidateId could survive status reading.
Fixed by recomputing the deterministic ID. Original failing assertions pass
without weakening them; this is not protection against privileged full-DB edits.

Initial test SQLite cleanup errors, a concurrent-snapshot test scheduling error,
and an independent reader's unrelated scalar-metadata parse issue are preserved
as TEST/HELPER issues, not falsely labeled fixed product defects. Full details:
docs/research/DREAM-QA-61A9.md and evidence/dream-qa-61a9/.

## Open next

DREAM-D2: qualify real-model synthesis on held-out good/bad lessons; add explicit
candidate inspection/acceptance/rejection before any active-memory use. Complete
trusted-memory reconciliation, idle/event triggers, unresolved-batch operator
recovery and independent skill transfer are NOT implemented. Existing D3B OS
identity/egress and real-provider/token/price gates remain open; no M1/M2 closure.
This slice changes agent maintenance behavior, but does not train model weights
or establish autonomous self-improvement. No Claude proprietary code/prompt is
copied into this implementation. Main and upstream source pins stay unchanged.

## Recovery qualification — 2026-10-17T15:48:30.022785+03:00

Same243-source product passed1657/1657 standard tests again;32API+16HTTP
opt-in passed separately, all exit0/no skips/no source drift. The existing
final4native receipts and independent source map match this exact version.
No native experiment was replayed. Main and44pre-existing tracked root files
were preserved. Final Git/CI result is recorded only after actual publication.

## Historical receipt byte preservation

Git normalizes some historical receipt line endings. The 25 affected raw
local files are additionally preserved losslessly as UTF-8 strings, original
lengths and SHA256 in recovery-98f0/verbatim-evidence-eol.json under the primary
evidence directory. Their normalized Git versions retain identical values;
source/test code, assertions and actual outcomes were not changed.

## Exact-code publication — 2026-10-17T15:59:53.686836+03:00

Product commit `0a12d3dc20fafcd0e5ea77c12ef9cd7184b13033` was published to `alaz/dream-d1-e458`.
GitHub alaz/local-ci is SUCCESS (status56593314782,2026-10-17T12:58:06Z).
The status API supplies no remote test count; local1657standard and48opt-in
results retain their measured scopes. All243accepted product/test/script/config
files match the published commit bytes. Same-source four final native scenarios
were qualified separately before this recovery, with no native replay here.

Evidence: code-ci-status.json and recovery-98f0 standard/API/HTTP/index receipts
under evidence/dream-d1-e458. This documentation-only follow-up preserves code,
original failure receipts and source pins; its own CI is checked after push.
Root status mirror remains equal; main stays unchanged. Next is DREAM-D2:
real-model synthesis quality and explicit candidate review/verification, not
an automatic scheduler or active-memory promotion disguised as a finished task.
