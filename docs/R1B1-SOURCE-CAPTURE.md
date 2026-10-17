# R1B1 — Trusted isolated input capture

17 Ekim 2026. Status: scoped implementation and final local/native acceptance PASS.
Exact-commit CI and publication are recorded separately below. Base ee5580ded751c8fc22c9d09984b8f14cc72b58e5.

## Scope

The existing qualified Linux NativeReadIsolation route can opt in to metadata
capture with `record_source: true` inside its existing `isolated_read` settings.
Absent means false; strings/numbers/null are not boolean settings. No new tool,
endpoint, database, scheduler, provider key, scope or file permission is added.
The current 64 KiB plain regular .txt allowlist and existing native guards remain.
Direct/Windows non-isolated paths do not gain this capture feature.

The writer is called by the actual mandatory isolated-read path, not an optional
plugin observer. It reuses the existing native database owner's transaction and
ExecutionLedger validators. There is no new state.db writer or second budget
calculation. Internal source_capture APIs are trusted host-only interfaces, NOT
requests accepted from an agent, tool result, other process or network message.

## Two durable points and three distinct data objects

1. Before invoking the native file tool, the already obtained raw source snapshot
   is hashed and its exact byte count recorded in native state_meta. The current
   admission, epoch, generation, scope, policy, request digest and reserved read
   ticket are rechecked in that transaction. Actual native dispatcher tool-call
   identity is captured from the pinned approval context and stored only hashed.
2. After the real isolated operation, verified process exit/removal and native
   redaction, the exact returned UTF-8 result digest/size is bound to the earlier
   record. The same live ownership and unchanged earlier capture must still hold.

The record transitions captured -> returned; there is no resend, refund, delete
or implicit recovery action. Begin commit failure/acknowledgement loss prevents
original invocation. Finish failure after execution can retain captured or even
committed returned metadata while its acknowledgement is lost. It does NOT prove
that the downstream tool-result consumer or a model received that return.
The original physical reservation remains consumed. Existing settlement occurs
only after the isolated invocation returns through GuardedFileTools.

A complete RAW SOURCE SNAPSHOT, the possibly paginated/redacted FORMATTED TOOL
RETURN, and PROVIDER REQUEST CONTENT are three different objects. This slice
only records the first and second relationship. Requested offset/limit is not a
measurement of the actual source range that survived formatting/redaction.
It does not implement provider-visible byte ranges or semantic understanding.

## Read-side binding

The opt-in EvidenceViewInspector reads new metadata within the very same existing
recovery/report transaction; post-read epoch/data-version/path-identity checks
still invalidate the entire snapshot. A capture is bound to a retained terminal
reference only when canonical admission, generation, payload digest, policy,
physical read claim, native tool-call ID hash and exact returned text hash/size
all agree, and the physical claim is settled as tool_return. Duplicate matches
are rejected, not guessed; ambiguous history or changed/sanitized text is not
fuzzily matched. Unmatched captured records remain separate metadata observations.

`sourceCaptures` reports raw source SHA256/bytes/full captured range, requested
line bounds, returned-output SHA256/size, process outcome and exact matched
EvidenceRef where available. Bound references identify `captured_snapshot_complete`;
this does not mean the whole source was returned by the native file tool.
Current source availability, tool-output source coverage, model visibility,
comprehension, claim truth and independent goal success are not promoted.

No source path is opened by this report; it can read the historical capture after
the original file is gone without asserting the file still exists. No raw source
content, source path or raw tool ID is added to the new metadata row. Existing
native staging/transcripts have their previous private retention policy; this
change is not a new deletion or privacy-anonymization guarantee. Hashes and sizes
are sensitive metadata and reports are not automatically public.

Missing old records remain UNKNOWN. Old transcripts do not get reconstructed
capture evidence from content or model-generated proof JSON. Existing replay
retention still gates access. This slice does not implement capture garbage
collection or claim source-row presence against malicious privileged DB edits.
Ordinary source integrity hashes are not signatures or factual truth proofs.

## SQLite storage effects (G01)

`writesPerformed=false` and `applicationStateWrites=false` describe no application
SQL/state mutation while reporting, not zero filesystem side effects. SQLite may
create auxiliary WAL/SHM files even with a mode=ro connection. New capture sections
and text rendering state this limitation; strict filesystem-silent acceptance
remains open. No immutable flag is added to live databases, and no clock or
retention is changed to make a test pass.

## First failures preserved

The initial 40-test authoring run had one Windows fixture issue: write_text
translated 250 LF lines into 750 raw bytes while its fixed expectation was 500.
The product counted correctly. Fixture generation now uses write_bytes; the 500
expectation was not loosened. Before-source and failure receipts are retained.

The first actual Linux 250-line native run failed before container execution:
the native plugin loader removed its temporary import path after registration,
so the new lazy source_capture import was unavailable during invocation. The
old route refused rather than silently skipping capture or running on host.
A separate bootstrap regression reproduced ModuleNotFoundError before the fix.
The product now preloads its own source_capture dependency while registration's
path is active; no global path is left enabled. The unchanged regression passes.
The initial native FAIL and its spent reservations are preserved, not repaired.

## Tests and files

45 own tests (40 storage/invoke/report, one bootstrap and four pagination tests) and 63
independently authored C72E cases (18 raw snapshots, 40 capture API, two bootstrap
and three pagination tests) are
separate case sets; counts are included once in full discovery. Native runs are
separate from those synthetic SQLite/native-port tests. Final count/result/exit,
source freeze and exact-commit CI are recorded only when actually completed.
No real model inference, billed call or new dependency is required for this slice.

Product: packages/claw-hermes/source_capture.py; existing isolated_read.py and
evidence_view.py. Probe: run_native_provider_broker.py --record-source with
--fixture-lines 2..500; without opt-in the legacy no-capture path is preserved.
Reader QA: scripts/qa/verify_source_capture_af13.py --fixture <closed-profile>
--receipt-sha256 <exact-receipt> --output <fresh-separate-directory>.
It does not start a task or model. CLI inputs written under output/private contain
synthetic fixture credentials; keep them out of Git. Only sanitized reports and
receipts go under evidence/r1b1-source-af13/; independent evidence is in
r1b1-qa-c72e/ with its own review report.

## Open and next

R1B2 must bind actual normalized/redacted provider request content to the physical
provider attempt. Neither a capture nor a returned tool result proves delivery.
Context compaction and memory/skill transfer must preserve this distinction.
D3B whole-Gateway OS identity/egress, real provider pricing/tokenizer/model,
HYB006 learning transfer and full M1/M2 remain open. Main is not merged here.

## G03: omitted pagination was incorrectly inferred in the first candidate

An additional check of the actual 250-line file showed that the native default
returned all 250 lines, while the candidate capture had substituted a requested
limit of 200. The earlier v2/v3 fixture checks passed only their narrower metadata
assertions; they do NOT qualify actual partial-read behavior. Initial receipts
and the later semantic rejection are retained, not rewritten.

Only explicitly present offset/limit arguments are now recorded. Missing values
are null; explicit null/invalid values still fail. The strict paginationBasis
field distinguishes explicit-arguments-only metadata; earlier unpublished
guessed-bound candidate rows without this field are rejected, never upgraded.
The new probe supplies an explicit limit20 to a250-line input and checks actual
last-visible/first-excluded lines as well as the independent input hash.
The same omitted-bound regression is retained before and after the fix.

## Final publication-source qualification — 2026-10-17T11:57:50.871397+03:00

Full standard:1511/1511 PASS, exit0, no skips. All227 measured code/test/config
files unchanged; no additions. The108 new tests (45 primary and63 independent)
are included once. Evidence: full-publication.json and publication-source-freeze-v4.json.
Historical1504 PASS was pre-G03, not this acceptance.

Five final Linux cases passed on the same143 transferred program/config files:
normal, actual partial20-of250, provider limit, upstream disconnect and opt-out.
Four isolated reads and eight scripted provider requests; five Gateway and five
broker lifetimes closed cleanly. Four exact container IDs were inspected absent;
all five broker sockets absent. No new run in corroboration, inference or paid call.

The partial input is4166 raw bytes; formatted tool result594 UTF-8 bytes. Actual
terminal text contains line20 but neither21 nor250. Metadata records requested
limit20 and binds source to that return, not full-return or model visibility.
Two-line captures are54raw/174output bytes. Missing pagination is null; native
defaults and request identity unchanged. Limit-case taskfailed retains capture;
disconnect has no capture; opt-out preserves UNKNOWN. JSON/text CLI matched.

First fixture newline error, bootstrap ModuleNotFoundError, G03 guessed-pagination,
QA contract-draft failures and source-drift runs remain preserved. Strict
explicit_arguments_only field rejects unpublished guessed-bound candidate rows.
Model visibility, comprehension, goal success and filesystem-silence remain open.
See native/publication-suite.json and native/publication-corroboration-af13.json.
Code/CI publication pending at this checkpoint; local PASS is not CI PASS.

## Verbatim QA evidence packaging

Two raw QA files (native-pagination-observation.txt and pagination-contract-alignment.diff)
are published losslessly as UTF-8 strings plus original length/SHA256 in
evidence/r1b1-source-af13/verbatim-qa-publication-texts.json. Their exact raw local
originals remain under ignored runtime/r1b1-publication-verbatim. This preserves
unified-diff context whitespace and original terminal EOF rather than silently
normalizing them. Test sources, assertions and recorded outcomes are unchanged.

## Exact-code publication and continuation — 2026-10-17T12:06:45.708443+03:00

Code commit `15eca31e3522ee4c2215b3a3d4f8df9b217e7559` is published on
`alaz/r1b1-source-capture-af13`. GitHub `alaz/local-ci` is SUCCESS,
status56587531642 at2026-10-17T09:03:38Z, observed by both status tools. The API
reports status, not remote test counts. Local1511/1511 and independent1511/1511
remain separately measured standard runs; native five-case acceptance is separate.
All227 frozen source files match published Git index bytes, with no exceptions.
Evidence: evidence/r1b1-source-af13/code-ci-status.json.

This documentation/summary/status-only commit does not modify runtime code,
tests, original failure receipts or source pins. Its own CI is checked only
after publication. Main remains b8ff44ff105965ba3f6f9fa9559ad96f2c084815.
Next: R1B2 actual normalized provider request-view binding. R1B1 captures source
and exact redacted tool return, NOT provider delivery, understanding or goal
success. D3B OS perimeter, real models/tariffs/token bounds, HYB006 and M1/M2
remain open. No independent source database, scheduler or extra tool permission.
