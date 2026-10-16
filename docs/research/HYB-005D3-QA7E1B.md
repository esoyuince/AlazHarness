# HYB-005D3 — separate QA7e1b

Status: fixed offline QA checks complete; final native/package publication is separately pending.
Existing247a implementation and publication ownership is preserved. QA7e1b
writes only separately named QA tests, reports and evidence. No second provider
engine, product branch, queue or budget writer. Historical D2 success is not D3 proof.

## Review gates

The externally usable provider credential must be distinct from the SDK/host
credential and absent from tool capsules, model messages, output, errors and
published receipts. Caller data may not select destination, forwarding headers,
credential source, proxies, redirects or fallback. The real budget reservation
must precede any forwarded request. Unknown outcomes retain exposure and do not
permit blind replay. Missing policy/credential/IPC/native proof must fail closed.

Distinguish a local credential-routing contract from OS isolation of the entire
Gateway. Same-UID arbitrary Python can read host files unless an actual OS boundary
prevents it. Test only new synthetic secrets/profile data. Do not modify personal
profiles, firewall, daemon settings or upstream source pins. No real inference.

Fixture/router shape must follow the implemented API, not invented methods.
Retained source/runtime reports are read-only; earlier runs are not new executions.

## Source-review questions (not reproduced runtime findings)

The current provider_broker.py source bf605724... checks the upstream account
credential only as a raw UTF-8 substring of the response body (line159 in the
first reviewed version). JSON and JSON-bearing SSE consumers decode escaped
strings. A raw substring check alone does not establish non-disclosure in the
decoded message. Review semantic response validation/redaction, and preserve
separate tests for legitimate replies versus protected information. No network
reproduction of this question was completed by QA7e1b.

PermitVerifier.check_authority reads a transaction but does not recheck database
identity, data_version or current epoch after rollback in the first reviewed
version. The checked state may change during the observation. This is a source
review question, not a proven network race or authorization bypass. A snapshot
cannot be claimed as an enduring execution lease; use explicit bounded semantics.

An attempted additional HTTP test-file write was blocked by the tool; the path
scripts/qa/provider_upstream_qa7e1b.py was confirmed absent. Its code and hypothetical
results are NOT part of the repository or the test count. No alternate tool or
encoding was used to repeat that blocked write. Existing product tests are read
and run separately below; the original source questions remain unverified.

## Existing targeted suite, first independent execution

72 primary-authored provider tests executed;71 passed and one test setup errored.
No source drift was observed. The error is not a runtime escape: Windows Python
has no asyncio.open_unix_connection attribute, so a patch of that missing symbol
without create=True fails before the test can exercise the refusal path. The
fixture should supply its explicitly synthetic port on Windows while keeping
its assertion that it is NOT called after missing socket validation.

Evidence: evidence/hyb-005d3-qa7e1b/existing-targeted-first.json/.txt.
These72 tests are reused existing cases, not72 newly written independent tests.
No Unix broker, Gateway, Docker process or provider request was started here.

## QA-G01 / QA-G02 — confirmed in synthetic read contracts

Nine new QA-owned tests ran with4 PASS /5 FAIL, no source drift, no network or
native broker execution. Test SHA a704d597f5574077a360c0bf798fde40e6f78510a8440620974ab2e686fd7bee.
Source provider_egress.py60ed089c...; fixtures reuse real production ledger with
the existing synthetic SQLite owner. Initial output is preserved unchanged in
snapshot-initial.json/.txt. These tests are not the blocked outbound HTTP file.

QA-G01(two cases): consume() can validate the short-lived grant, but the queued
check_authority() step never checks its expiry again. Advancing the test clock
past expiry or exactly to expiresAtMs does not reject. Check expiry at the final
authority stage as well; a queued observer cannot extend the permission lifetime.

QA-G02(three cases): after the SQLite snapshot's rollback and before return,
changing epoch, changing instance, or removing the grant in a separate real
connection does not invalidate the read. This is a controlled check of a change
DURING the reader, not proof of a race through the real network. Guard snapshot
identity/data_version and current owner again before returning. Even that does
not make the returned snapshot an enduring lease against future privileged writes.

The same five failing assertions must be preserved; primary247a owns product
correction. Four positive tests confirm source bytes unchanged, closed query-only
connections, no native writer invocation, and no restored budget on missing grant.

## Eleven in-memory IPC identity checks passed

The actual ProviderBrokerClient._exchange, framing and signature verifier ran
against explicitly synthetic in-memory reader/writer ports. All11 passed with
stable source hashes: wrong lifetime/nonce/domain/type are rejected; peer failure
and socket replacement occur before sending bytes; bounded refusal text is kept,
untrusted free-text diagnostics are not echoed; cancellation closes the stream
without retry. These are protocol unit contracts, not real Unix-socket or OS tests.

The9 snapshot tests and11 identity tests are20 new QA-authored offline cases.
The existing72-case primary suite is separately recorded, not another72 new tests.
No additional outbound HTTP test was created after the blocked tool write.
Evidence: identity-first.json/.txt. The first five snapshot failures remain open
until the product source is corrected and those exact test files pass unchanged.

## QA-G01 / QA-G02 correction verified

Primary247a modified provider_egress.py to recheck expiry before/after the
transaction, then compare the current owner and data_version after releasing
the snapshot and check the store identity. The broker also checks expiry again
near outbound forwarding. The SAME9 snapshot cases now pass; the SAME11 protocol
identity cases remain passing. Both test files have their original hashes,
including every initially failing assertion. Combined20/20, exit0, drift0.
Evidence unchanged-recheck.json/.txt. No native broker or network race acceptance
is inferred from these synthetic unit tests.

The semantic response-reflection source question is separate: raw-only scanning
still does not establish decoded-message secrecy. It was not network-reproduced
by QA7e1b. Do not label it fixed by the grant-snapshot correction. The Gateway
and broker also share a trusted OS user; separate processes do not establish
protection from arbitrary same-user host code.

## Response guard correction and full-suite qualification

The primary now added reject_sensitive_response for literal and decoded JSON,
JSON-bearing SSE and same-field stream fragments. It remains explicitly bounded
to supported representations, not every possible encoding by a hostile provider.
The source-only concern was addressed in product code and in primary-authored
synthetic transport tests, which this reviewer also ran. This does not claim the
blocked real-HTTP script was run or that arbitrary remote provider secrecy is proven.
See response-and-identity-recheck.json/.txt for the exact counted selection.

The first independent full suite executed1270 tests, exit0, no skipped tests.
However run_native_provider_broker.py changed during that run, so this package
snapshot is NOT_ACCEPTED as final evidence. All other209 monitored files remained
stable. Raw full-standard-first.json/.txt is preserved; a final same-source run
is still needed after the native experiment launcher is stable.

## QA handoff and second complete-suite observation

The second full-suite run executed1273 tests with exit0/no skips. It is STILL
NOT_ACCEPTED as a final whole-package snapshot: the native launcher changed and
verify_broker_socket_shutdown.py appeared during the run. This does not change
the previously proven20 fixed QA cases; it means final publication must use a
stable source set. Both full-run records and all initial failure records remain.

QA7e1b's own code is ready for integration:20 new offline tests, unchanged hashes,
five initial grant-reader failures corrected in product,11 in-memory IPC contracts
passing. The primary's15 decoded-response tests were separately rerun as part of
26 passing response/identity checks; those26 overlap the20 and are not an extra
26 unique cases. Existing provider selection81 also overlaps and must not be added.

Reproduction (no dependencies or model calls):
```
python -B -m unittest discover -s tests -p test_*qa7e1b.py -v
python -B -m unittest discover -s tests -p test_provider*.py -v
python -B -m unittest discover -s tests -p test_broker*.py -v
```

Primary247a retains product/native acceptance and Git publication ownership.
This QA handoff does not assert that the real five-case Gateway/broker experiment
has completed or that the feature commit/CI is green. The final source-set suite
and native receipts must be read when present. Current isolated tool and source
pins are preserved; no new budget writer, DB, scheduler or paid call was added.

## Final frozen-v4 verification

The third independent full suite completed1273/1273 PASS, exit0, no skips.
All211 measured code/config files were unchanged and no files were added during
that run. The20 new QA tests are INCLUDED in1273; repetitions and overlapping
selections are never added together. Earlier two source-set failures remain in
their original receipts. Final evidence: full-standard-final.json/.txt.

Five completed v4 native Gateway/broker scenarios were then independently read
from the server's retained original source, native JSON and actual SQLite stores.
Allfive agreed: normal2reservations/2grants/1tool/1admission; missing and stale
broker each0/0/0/0; provider-limit1/1/1/1; disconnect1/1/0/1 with unknown usage
and positive retained exposure. Original stores and receipts remained byte-
identical. These are retrospective corroborations, not five new executions.
See native-final-corroboration.json. Source v4 hashes, lifecycle exit records
and controlled-origin request counts are retained; no real model was called.

## Publication-only source normalization

A subsequent working-copy check found provider_egress.py lost one trailing blank
line: v4 hash0ef894c8... changed to fa1d568d... . A direct diff of the original
server source showed ONLY that final blank line, with identical parsed Python AST.
The native and standard v4 receipts are unchanged; their raw-byte hashes are not
silently relabeled. Exact published-byte test/CI qualification or restoration of
the qualified bytes remains the integration owner's step. This is not a product
logic change, but it must not be described as byte-identical to old receipts.

The independent local QA part is complete. Primary247a owns final publication
and same-commit CI. Full same-UID host isolation, arbitrary hostile provider
encodings, HTTPS pricing/tokenizer, restart takeover and general M1/M2 remain
outside this local trusted-process routing slice. No product code was modified
by QA7e1b; only these tests, reports and explicit sanitized evidence were staged.

## Exact publication-byte requalification observed

The integration owner reran the full standard suite after the trailing-blank-line
normalization: full-publication.json/.txt reports1273/1273 PASS, exit0, no skipped
tests or measured code additions/changes. Five additional publication-source
native cases and the Unix close check were recorded separately by that owner;
publication-native-corroboration.json keeps their distinct scope. The earlier v4
receipts and QA's v4 retrospective check remain unchanged historical evidence.
This closes the local byte-normalization handoff item. Exact-commit server CI
still must be checked after the forthcoming commit, not inferred from these runs.
