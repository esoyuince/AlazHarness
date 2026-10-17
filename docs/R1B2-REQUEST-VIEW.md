# R1B2 — Normalized provider request views

17 Ekim 2026. Scoped local/native acceptance PASS. Exact commit publication and
CI are tracked separately; local success is not automatically remote CI success.
Base e2a5b300568425358e181954cffb697ace2d032b.

## What changed

The existing execution boundary accepts `record_request_view: true` as a strict
boolean. It requires the already-qualified Linux Unix credential broker path.
Default false preserves legacy behavior; direct provider routes cannot silently
implement or bypass this option. No new endpoint, scheduler, database, provider,
credential or tool permission is introduced. Only the trusted native state owner
writes the new `alaz.evidence.request.v1.*` records.

The existing provider handler authenticates, validates, and normalizes its payload
(including a declared output ceiling if absent), then reserves the physical-call
budget. Its normalized payload goes to the existing broker client. Request-view
preparation and irrevocable egress authorization are committed in the SAME native
transaction. A capture failure rolls back both the grant and view; the earlier
physical budget reservation is not refunded. No extra LLM call is used.

## Three recorded phases, not three success claims

- `prepared`: canonical JSON UTF-8 request digest/size and bounded tool-message
  metadata were persisted with the egress grant. No IPC or physical-send proof.
- `handoff_armed`: a write-ahead intent was confirmed before the client attempts
  its private socket exchange. Lost commit acknowledgement can leave this state
  even when no socket was contacted. It is NOT an actual-send receipt.
- `broker_response_observed`: the trusted client verified the existing signed
  broker reply and bounded its body/status/content type before recording their
  hash/size. The broker emits this successful transport reply only after its
  fixed-route upstream operation returns an HTTP response. It may be an HTTP
  error; it is not a model-success, SDK-delivery, or comprehension guarantee.

The provider handler's subsequent response validation and ledger settlement are
separate. `providerResponseValidated` requires a recorded HTTP200 response plus
the matching existing claim settled as response/unknown_usage. A wrong-model or
otherwise invalid response can be observed yet not validated. Missing usage is
not zero usage. A record/ACK failure does not grant another attempt or refund.
Unknown transport/cancellation leaves the earlier recorded phase intact.

This protocol does not persist an independent broker-side pre-send journal. On a
lost/error reply the product cannot prove whether the upstream received bytes.
In controlled acceptance tests the origin can observe reception while the product
honestly retains handoff_armed/unknown. The fixture's additional knowledge is not
promoted into production state.

## Exact content inclusion, not inferred task ownership

The HTTP provider route is PROFILE scoped and carries no independently verified
initiating task identity. Neither body.user, arbitrary model text, a tool ID, nor
there being only one current task creates that identity. Request reports keep
initiatingRunId=null and initiatingRunVerified=false. A source's task provenance
must not be used to allocate the entire request's cost to that task.

At preparation time, a tool message can link to an existing source capture only
if its preceding read_file call/result pairing is unambiguous, the actual tool
ID hash and returned-content hash/byte count match uniquely, and the native
source record has returned with its read claim settled as tool_return. Ambiguous
source matches abort authorization. The reader revalidates the selected source
against its canonical admission and this same proof; later source records cannot
be retroactively joined to old requests. Different IDs, changed or summarized
content, duplicate IDs, missing text, and unpaired outputs are not fuzzy-matched.

The recorded range covers UTF-8 bytes of the exact RETURNED TOOL TEXT contained
in the prepared JSON request. It is not an offset range in the serialized JSON,
a tokenizer range, or a range of the original raw source file. Complete returned
text can still represent only20 of250 source lines. A local EvidenceSelection is
not an outbound operation and does not become a provider view.

## Metadata and reader behavior

The new row contains canonical request digest/byte count, message count, selected
tool-message index, hashed tool IDs/content digests/byte counts and preparation-
time source-capture digests, plus broker route identity/egress/claim binding and
response observation metadata. Raw request content, tool text, source paths,
credentials and raw tool IDs are NOT duplicated into these rows.

The same existing EvidenceViewInspector transaction now exposes profile-scoped
providerRequestViews and source-bound refs.providerRequestInclusions. Existing
retention, generation, owner, data-version and database-identity checks still
apply. Results are published only after all selected metadata passes validation.
A missing old request record stays UNKNOWN, not reconstructed from model output.
All modelProcessingVerified/understandingVerified/permission flags remain false;
the broad modelVisibility field remains unknown. Metadata are not signatures or
independent factual proofs against a malicious privileged database editor.

Bounds: at most1024 messages/256 tool messages per request,131072 bytes per view,
1000 rows/8MiB of history scanned per profile and bounded source-capture matching.
Source candidates are indexed once for read-side matching, not rescanned per tool.
No source files are reopened. There is no new retention cleanup/garbage collector
in this slice. Digests/sizes are potentially sensitive metadata; live reports are
not automatically public. Only explicit synthetic experiment outputs are shared.

G01 remains explicit: no application state/SQL mutations during reporting does
not guarantee filesystem silence. SQLite may create WAL/SHM sidecars. No immutable
flag is added to a live database, and clocks/retention are never rewritten.

## Reuse and implementation files

New: packages/claw-hermes/request_view.py.
Existing: provider_egress.py, provider_broker.py, execution_boundary.py,
evidence_view.py. Native owner, source_capture, budget calculations, admission,
broker framing/HMAC and upstream engine/pins are reused, not replaced.
The dependency is loaded while the plugin registration import path is active;
there is no new lazy-import failure after that temporary path is removed.

Probe: scripts/run_native_provider_broker.py --record-source --record-request-view.
Optional --read-limit20 and --fixture-lines250 test actual partial output.
The new after-tool-disconnect scenario drops the second upstream reply after
its request body is read. Origin request digests are calculated independently
from actual HTTP body bytes, not copied from the product's request metadata.
Reader: scripts/qa/verify_request_view_af13.py --fixture <closed-test-profile>
--receipt-sha256 <exact-native-receipt> --output <fresh-separate-output>.
The reader starts no Gateway/model/tool and never rewrites the original stores.
Its private CLI input files contain synthetic test credentials and stay ignored.

## Tests and evidence boundaries

68 primary new offline cases exercise real product code with synthetic owner/IPC
and native/Docker test ports.16 unchanged independent9B08 baseline cases are also
in standard discovery. Independent9B08 opt-in29 API and6 actual HTTP-handler cases
are run separately, not silently added to standard CI counts. The test sources
and their hashes are preserved. Native Gateway/SDK/broker/Docker runs are a third
scope; they use scripted authenticated loopback model responses only.

The first46 primary cases passed. Additional malformed-record/bounds/options
cases passed, and the existing81 provider regressions passed. Independent initial
API failures were a QA helper's fault flag ending BEFORE its enclosing COMMIT;
that helper was corrected with the29 test AST/assertions unchanged. Those first
records are retained by QA and are not presented as a fixed product defect.

## Open after this slice

This is not full raw-source range mapping, verified provider-request initiating
run attribution, tokenization/billing proof, comprehension, independently tested
goal success, or learned skill transfer. The existing loopback provider limit
is not expanded to remote HTTPS. D3B whole-Gateway OS identity/egress isolation,
real-model/provider price/token acceptance, HYB006 memory/skill transfer and full
M1/M2 remain open. R2 goal verification must use this evidence without treating
a model's success statement, JSON shape or HTTP response as a completed goal.
No main merge, production service change, real credential or paid call is part
of this work. Prior source/Claude research and all old worktrees remain intact.

## Final local/native acceptance — 2026-10-17T12:57:19.038201+03:00

1595/1595 standard tests passed, exit0, no skips,235 measured files unchanged.
84 new standard cases (68 primary,16 independent baseline) are included once.
35 unchanged independent opt-in cases (29 API,6 HTTP-handler) passed separately;
these are not35 extra CI tests. Existing81 provider regressions also passed and
are already in the standard total. No dependency/native install was added to CI.

Six final Linux cases all passed with147 measured program/config files. The
controlled origin received10 requests;5 isolated file reads ran. Six Gateway and
six broker lifetimes closed; all5 final container IDs and6 broker sockets were
independently checked absent. The earlier2 exploratory runs are retained, not
counted as two more final scenarios. Main source databases/configs/inputs stayed
byte-identical during reporting; SQLite sidecar changes remain explicitly noted.

Eight request manifests (recording disabled in the two-request optout case) match
origin HTTP body SHA256/byte counts and tool-message metadata. Three source-bound
inclusions exist: normal,partial,and after-tool-disconnect. The limit case has a
source capture but no second provider request/inclusion. The early disconnect
has one armed manifest and no file read. After-tool-disconnect preserves its
second armed manifest and source inclusion WITHOUT claiming a broker response.

The partial source is250lines/4166raw bytes. The returned20line text is594UTF-8
bytes and appears exactly in the11679byte second request, measured at the origin.
Line20 is present;21 and250 are absent in the tool text. The request's remaining
bytes contain other context/tool definitions: these sizes are not conflated.
Model processing/comprehension, goal success, physical-send proof for unknown
handoffs and initiating-run cost attribution are not established by this slice.

Evidence: evidence/r1b2-request-af13/full-publication.json,
native/publication-suite.json, native/publication-cleanup.json and the six
*-view/report.json and verification.json files. No live secrets/private CLI
inputs or databases are published; generated credential canaries were checked.

## Independent final corroboration — 2026-10-17T13:03:14.811539+03:00

The9B08 final read-only verifier corroborated all six SAME publication profiles,
using direct database/source/wire observations rather than the product proof
helper. Its remote original report SHA256 matches the preserved verbatim receipt;
each native receipt SHA256 also matches the primary copy. The independent check
started no new native work. Its own baseline1527 standard tests and35 opt-in
product tests are not additional counts on top of the primary1595 standard suite.
A local outer-wrapper NameError after the remote successful saved result and a
LF/CRLF transport copy mismatch are explicitly retained in the QA report. Original
remote bytes, JSON-equivalent local copy, and failure diagnostics remain separate.
Neither changes the actual native verdict nor constitutes a product bug fix.
