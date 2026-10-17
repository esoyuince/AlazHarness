# R1-EVIDENCE independent QA E03E

Status: QA COMPLETE — 50/50 unchanged independent tests and 1374/1374 full standard suite PASS on stable source. Product/commit owner remains 724a; E03E made no product edits. New-commit Git/CI and positive in-retention native-report qualification remain separately tracked.

## Verified baseline

Existing 83 host-report tests pass (exit 0, no source drift). This is baseline coverage, not 83 new tests or a native run. Receipt: evidence/r1-evidence-qa-e03e/existing-reports-first.json.

## Read-source constraints for the new projection

1. LocalRecoveryInspector._classify verifies canonical identity/outcome and final response/usage. Its resultDigest covers output+usage, NOT all intermediate messages. The EvidenceRef source digest must describe exactly what was hashed, not retroactively claim an independent source-file hash.
2. NativeReadIsolation._snapshot_input obtains at most 64 KiB, but that full-byte snapshot is not the same thing as native read output or model visibility. Native invoke redacts the resulting text and the result can be a slice. Do not infer whole-file provenance from full-memory capture or a valid container binding.
3. An assistant can generate arbitrary message/tool names, JSON fields, source paths and apparent proof labels. The new view must not treat embedded boolean flags, model prose or key names as privileged evidence, nor echo them in the operator report.
4. A terminal canonical record can contain inherited historical messages. A tool id appearing in history does not by itself bind it to this admission/generation. Missing/duplicate/unpaired ids must not silently become successfully executed tools for this run.
5. Existing readonly transactions check epoch/data_version and file identity after reading. A new section must be built inside and discarded with that same snapshot, not reread later through a separate connection.
6. Unicode, bool-as-int, negative/overflow counts, duplicate JSON keys, shape errors and oversized inputs must not crash CLI or become complete coverage. No arbitrary path from JSON may be opened.
7. Changed evidence digest, a retargeted run/session and a mutated returned report must not resurrect execution, retry or budget capacity. These tests must check storage bytes/denied write calls as well as displayed status.

## Next

Read the actual product evidence_view API when written; add narrow tests in tests/*qa_e03e* and preserve initial failures without weakening assertions. Source fixtures are synthetic; no real model/native Gateway run is claimed. Optional manifest/full-file/wire support not implemented in R1 must remain UNKNOWN/unsupported, not advertised as tested.

## First actual new API qualification

42 new E03E tests executed on stable source: 32 EvidenceViewInspector/EvidenceSelection tests plus 10 legacy public-report invariants. Result **41 PASS / 1 FAIL**, exit 1. Evidence: projection-first.json/.txt. The earlier 10/10 and baseline 83 are not added again.

### E03E-01 — UTF-8 denial reason is erased (P2, diagnostic)

The invalid multibyte split IS refused. However unavailable_evidence validates codes using `[a-z_]{1,80}`, which removes the product's own `split_utf8_boundary` code because it contains digit 8. Returned reason becomes generic evidence_unavailable. No incorrect content acceptance or data leak was observed. Keep this test unchanged; fix the reason-code contract in the product (for example a closed known-code mapping, not reflection of arbitrary error text). Product writer remains724a.

The other cases verify exact stored UTF-8 hash/length, incomplete vs missing content, opaque embedded JSON, ambiguous/unpaired IDs, historical-only pairing, source identity change, different admission binding, expired/missing record rejection, wrong digest/range/type, all-or-nothing inventory limits, concurrent epoch invalidation and no write methods. They make no provider-wire, original-file-integrity or real-model-comprehension claim.

## CLI and test inventory

Eight additional independent CLI tests pass (exit0, stable measured source). They invoke the real CLI in separate Python processes with temporary synthetic profiles; no real Gateway/provider is started. Legacy default has no evidence section, explicit opt-in reports metadata only, local selection is NOT DISPATCHED, duplicate selection keys and incompatible scope/flags fail, missing source is not success. Receipt cli-first.json/.txt.

Total new QA test definitions: **50** (32 projection,10 existing-report invariants,8 CLI). Results so far:41/42 on projection+invariants,8/8 CLI; E03E-01 remains open until unchanged-test recheck. No full-suite or same-commit CI conclusion follows from these subsets. The research plan's28 scenarios include later features; these50 are not a claim that all28 have been implemented.

All three test files now have stable hashes; no new test additions planned for this QA slice before the product source freeze. Source/method alignment and original-data immutability have been checked. Product/native/Git publication remains724a.

## Historical native-profile boundary

A current-clock read of the five retained HYB005B profiles returned retention_expired for all five. The original positive-inventory attempt remains NOT_ACCEPTED in retained-first.json, never relabeled PASS. A separate expired-denial-corroboration.json confirms the five expected refusals, empty evidence references and unchanged DB/config/original-receipt bytes. No historical clock override, retention extension, database rewrite or new Gateway/model execution was used. Current positive inventory over these expired stores remains unqualified; use in-retention records for that separate acceptance.

## E03E-01 closed with unchanged tests

Product724a now permits the explicit internal `split_utf8_boundary` reason while retaining the prior bounded filtering for all other reasons. E03E did not edit product code. All **50/50** independent test definitions pass, exit0, no skips, no measured source change during the recheck. Test hashes match test-custody.json exactly. Evidence: unchanged-recheck.json/.txt. The original41/42 failure remains unchanged.

### Scope conclusion

The implemented R1 API qualifies metadata over a canonical terminal record, not actual original-source coverage or provider visibility. It correctly keeps both unknown, even for complete local selection of retained text. The reported record digest covers canonical JSON of the whole current terminal record; legacy final-output/usage digest is separate. Test-created messages are synthetic; no new paid provider or native Gateway execution was performed.

E03E's50 tests, explicit first failure, closure, prior83-test baseline and five expired-native-profile denials are ready for integration. Full standard suite and exact published-commit CI are still separate product-owner gates and have not been inferred. Source freeze before full-suite acceptance should include all new tests and scripts. No more E03E test changes are planned.

## Independent full standard result

At 2026-10-17 09:25:28 Europe/Istanbul, full discovery completed **1374/1374 PASS**, exit0, no skips. All216 measured code/config/test paths had identical before/after hashes and no files were added. Receipt full-standard-first.json; exact source manifest full-source-before.json; complete output full-standard-first.txt. The50 E03E cases are included in1374, not added again. These are local standard tests, not new native Gateway/provider runs and not remote CI.

## Handoff

All E03E test/source/provenance hashes are stable and ready for the product writer's single feature commit. Original failing diagnostic test and expired-profile positive attempt remain retained; the latter is NOT accepted as positive inventory. Source checks, CLI subset and full standard suite provide separate scopes. No product/runtime profile/pin/main changes or paid calls were made by E03E. Final public commit and CI must be checked by exact SHA, never inferred from base214f1dc or from these local results.
