# R1A — Read-only retained-evidence view

Status: implementation and targeted acceptance complete; full-suite/publication
status is recorded in `status.md` and the evidence receipts. This is the FIRST
narrow R1 slice, not the complete source-capture/context-dispatch roadmap.
Base: `214f1dcd7ba7a83a0d13afdb7adfb221bfa21fa8` (D3A provider broker).

## What it does

`EvidenceViewInspector` extends the existing host-report reader. After the
original bearer, profile, replay-retention, admission, generation and terminal
checks, it describes text retained in that native terminal record. It performs
no task, provider, tool, memory, refund, or state-writing operation. The default
`HostReportInspector` and CLI output remain unchanged without opt-in.

The new projection runs INSIDE the same read-only transaction and is discarded
with the old report if the final epoch, SQLite data-version or file-identity
recheck fails. A fresh internal reader owns each optional selection; concurrent
callers do not share mutable selection state. No second store, scheduler,
transcript owner or budget accounting engine was introduced.

## Three different things

1. **Retained content:** which text bytes are currently present in the verified
   native terminal record, their exact UTF-8 size and SHA-256.
2. **Original source:** whether a complete original file was captured, which
   ranges were read, whether it still exists and its original byte digest.
3. **Provider-visible context:** which content/ranges reached a particular model
   request after normalization, redaction, compaction and transport.

Only the FIRST is positively described in this slice. The latter two remain
`unknown`. A retained tool result may already be truncated/redacted and need not
be a complete source file. A tool-call/result pair in saved history establishes
structure, not current-run execution attribution. Suffix flags and model-created
proof fields cannot promote it to independent effect evidence.

## Public interface

`packages/claw-hermes/evidence_view.py` provides:

- `EvidenceViewInspector(context, policy, clock=...)`, with `inspect` accepting
  the same original `body`, `idempotency_key`, `observed` as the host report.
- Optional frozen `EvidenceSelection(evidence_id, content_sha256, start_byte,
  end_byte)`. It selects only within existing retained text. Bounds are UTF-8
  byte offsets, end exclusive. It is neither a capability nor a provider request.
- `inspect_scope()` retains the original profile-only report and explicitly
  indicates that no task evidence was selected.
- `render_evidence_text(report)` renders metadata without raw content or paths.

The report's new `evidenceView.references` includes stored tool text records and
the saved final response. It does not enumerate all historical/user/system text.
The list is limited to256 references and history inspection to1024 message rows;
invalid/oversized inventories are unavailable, not silently reported complete.
Unsupported non-text content has null size/digest. A retained EMPTY string has
zero bytes and its actual digest; these cases are not interchangeable.

Reference IDs bind the selected profile/scope, run/session/admission/generation,
current terminal-record digest, content digest, kind and message position. They
are not stable source-file IDs across different runs. The whole-record digest
is canonical JSON SHA-256, independent of stored JSON whitespace. Its basis is
explicit: `canonical_current_terminal_record_json`. The legacy `task.resultDigest`
still means final output plus usage only; it was not redefined.

Optional selection output is `computed_locally_not_dispatched` and contains only
a range, size and selected-byte digest, never the selected payload. Its
`coverageOfStoredContent` can be complete/partial while `originalSourceCoverage`
and `modelVisibility` remain unknown. Multibyte splits, wrong digests, stale IDs,
invalid types (including bool-as-int), empty slices of nonempty text and
out-of-bounds ranges fail without returning a partial reference inventory.

## CLI

```text
python -B scripts/inspect_host_report.py --context <private-context.json> --policy <trusted-policy.json> --request <original-request.json> --include-evidence
python -B scripts/inspect_host_report.py --context <private-context.json> --policy <trusted-policy.json> --request <original-request.json> --include-evidence --evidence-selection <local-selection.json> --format text
```

The selection object has EXACTLY the four dataclass fields listed above. Obtain
its ID and content digest from a current opt-in report, not by guessing them.
The input files contain private host credentials/request metadata and must stay
outside Git and public evidence. Selection requires both `--include-evidence`
and `--request`; it cannot be used with `--scope-only`.

Exit0 indicates a validated report snapshot, not task or goal success. Unverified
or partial snapshots exit2. Expired task retention remains a refusal; reading a
report never renews that retention or reissues the task.

## No elevation from text

Content is treated as opaque text. JSON saying `complete`, `modelSeen`, `verified`
or naming a file is not parsed as authority. Paths embedded in content are never
opened. User prompts, retained content, tool names and raw call identifiers are
not copied into report strings. Hashes and sizes are still metadata, not an
anonymization guarantee; operator reports should not automatically be published.
A malicious privileged process that can alter the stores is outside this local
snapshot trust model. Content-addressing is not a signature or truth check.

All execution/retry/repair flags remain false. Original ledger rows, reservations
and result stores are unchanged. `goalAchievementVerified`, `claimTruthVerified`
and `understandingVerified` remain false. The existing native task classification
is displayed separately, not interpreted as proof that a real-world goal succeeded.

## Tests and preserved first failures

Own51 new tests exercise the actual metadata reader and CLI using explicitly
synthetic SQLite profiles. Independent E03E contributes50 new tests:32 projection,
10 old-report invariants and8 CLI subprocess cases. The independently authored
files and their unchanged hashes were read before integration. Subset totals and
the old83-test baseline must NOT be added again to full-suite totals.

Both test authors found the same P2 diagnostic problem: a split UTF-8 byte range
was already refused, but its `split_utf8_boundary` reason was erased by a
letter-only reason filter. The product now accepts that exact internal code.
The original test files and failure receipts remain unchanged; all51 own and50
independent cases passed after this code-only fix. This was not an unauthorized
range acceptance, file access or credential leak.

The tests additionally verify output-only vs whole-record digest differences,
history pairing ambiguity, metadata nonreflection, current identity binding,
Unicode/empty/missing/rich-content distinctions, all-or-nothing limits, same
connection use, read-only SQL, missing-store noncreation, post-read epoch changes,
no ledger writes/refunds, object mutation isolation and JSON/text CLI behavior.

Full standard discovery, root/static gates and exact-commit CI are separate
acceptance records. Test/script/config source hashes are frozen before the full
run. No proprietary code or prompt from the Claude static study is used in this
implementation, and no new dependency was installed.

## Retained-native experiment: important negative result

Five historical HYB005B fixture profiles (normal, provider-limit, tool-limit,
denied-write, summary) were read with the CURRENT clock. They were approximately
30hours old and exceeded the existing24-hour fallback retention. The initial
attempt expecting positive evidence remains FAIL/NOT_ACCEPTED. No timestamp,
clock, retention rule or database was changed to make that test pass.

A separate explicit `--expect-expired` qualification passed for all FIVE: current
reader and real CLI refused with `retention_expired`, returned zero references,
kept all action flags false and left original DB/config/receipt bytes unchanged.
These are five negative read checks, NOT five successful current inventories and
NOT five new Gateway/model executions. Independent E03E corroborated the same
boundary in its separate receipts.

`verify_evidence_view_retained.py` is a repeatable fixture-specific verifier with
an explicit positive/expired expectation. It accepts only a fresh output under
the research workspace's runtime, outside the source profiles. Its private CLI
inputs stay there; only sanitized aggregate reports are copied to Git evidence.

Positive inventory against an in-retention real native profile is STILL OPEN.
Synthetic reader/CLI coverage does not close that acceptance. The product will
not claim original-file coverage or model dispatch even when that next check
passes, because the corresponding trusted capture records are not yet produced.

## Files and next step

Product: `packages/claw-hermes/evidence_view.py`; opt-in existing CLI:
`scripts/inspect_host_report.py`; fixture verifier:
`scripts/verify_evidence_view_retained.py`.
Evidence: `evidence/r1-evidence-724a/` and `evidence/r1-evidence-qa-e03e/`.
Independent report: `docs/research/R1-EVIDENCE-QA-E03E.md`.

Next R1B: bind actual source capture and normalized provider-request ranges to
trusted runtime records, with an in-retention native end-to-end acceptance. This
must reuse the existing writer and physical provider budget, not a model-authored
manifest or another queue. Only after that should context selection/compaction
and independent goal-assessment work build on the stronger evidence.

D3B OS identity/egress separation, real model/tariff/token bounds, HYB006 skill
transfer and full M1/M2 remain open. R1A does not add a goal chooser or more tool
permissions. `main` is not modified by this delivery.

## Local final source checkpoint

1374/1374 standard tests passed, exit0/no skips. The101 new tests (51 own and
50 independent) are INCLUDED in that total. All229 measured source/config/test
files stayed unchanged and no new files entered that set. The ordinary root
gate and published commit status are recorded separately; a local pass does
not imply remote CI success. The initial UTF-8 diagnostic failure and all five
expired positive-profile attempts remain preserved.
