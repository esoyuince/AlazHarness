# R156 actual acceptance: independent evidence review

**Verdict: PASS for the declared projected finite qualification scope.** The exact generated pure `validate_caller` accepted the original caller record. Independent byte, hash, canonical-frame and identity checks found no contradiction. This review started no native runtime and ran no new tests.

## Immutable inputs

- Harness: `e641a5000810efb2a453ae847f689b422f7d41a7`.
- Native: `d1516731308de8e87130dc68124e69aad35d6911`.
- Runtime SHA-256: `e710f75ebc6900e1d16807a5d0a691f1c2f10c2f066c5d8918a6c13317e78c95`.
- Original host result SHA-256: `6a67c078680fa4cb41ae29547c3c9e6e7048f7aeb49327384c37822ea0e88931`.
- Exact generated assertion SHA-256: `6d374e49ce37269422f14d11feaf5a93fbe6d9b961e3fc00c722834f164ce7e7`.
- Installation receipt SHA-256: `a4bcc0f27d29f27f08c55d3a65eaa102a503a7da12d4672253f0245fd5d4f845`.

## Native outcomes

| Case | Request | Admission | Outcome | Cumulative computations |
|---|---|---|---|---:|
| normal | r156a1-normal | 923779b4205044e48a3698ac70c32348 | completed | 1 |
| replay | r156a1-normal | 923779b4205044e48a3698ac70c32348 | completed | 1 |
| new | r156a1-new | 12e3b6a39a074a8dba96617abaf94ca2 | completed | 2 |
| error | r156a1-error | 6953c84c971a4bf2873569b0a7591d43 | failed | 3 |

Normal and replay share the admission ID, API result hash, stored result hash, outcome and computation count. New and controlled-error requests have distinct admissions. API and stored digests are different serializations and are not expected to equal one another; runtime lines 213–230 compare the underlying native values before hashing them.

The seed handoff is hash-bound at epoch 1; the finite owner completed epoch 2. The owner record reports DETACHED consumer, CLOSED owner, the same three connections physically closed, registry refcounts zero, all fixture models closed, zero retirement writes and caller lease released. The original supervisor then records UNMOUNTED worker and CLOSED volume, owned users gone, loop detached, fence removed after cleanup and lease released last. Captured events end in normal stop, normal finish, volume closed, closure verification and complete; the original retained-volume list is empty.

## Evidence binding

The 2,224-byte finite child stdout exactly equals the canonical owner record plus its newline, SHA-256 `aadb7bbbe821f35f55ac6f12dda233c1381c0eba0af8d981a3bb42f1c3693618`. PID 16 and start ticks 9977 match the observed completed child, exit code 0, with complete non-overflowing pipes and the expected input digest. All raw output layers bind through caller, transport and host records. The exact assertion is a byte-exact extension of the reviewed pure protocol. Intent, execution start, source hashes, fresh installation receipt and harness/manifest identifiers agree. Ordinary proof raw and producer streams verify and bind to the same installation and producer source.

The complete SHA-256 inventory and detailed checks are in `actual-acceptance-review.json` beside this note.

## Scope and diagnostics

- Three scripted model invocations, zero real model/provider calls; factory, computation and model close remain explicitly doubled.
- Metadata broker fixture only. Service start, runtime admission authorization, full D3B, M1 and production readiness are all false.
- Profile event counts are `run_api_turn=11`, `execute_finite_admission=56`, `run_sync=3`, `commit_and_publish=3`, `settle_session_input=3`. These are raw profiler call events, not unique logical calls or admissions. See runtime lines 127–131.
- Child stderr is 4,513 bytes. It records SQLite DELETE-mode fallback warnings, a nonfatal missing `agent.secret_sources.command` registration diagnostic, and the expected controlled model failure traceback. This is not evidence that stderr was clean or that the missing secret-source integration is supported.
- Native database contents were not independently reopened during review; terminal native readback is enforced by the pinned runtime and bound completion record.
- The original `image001/ordinary-proof.json` binding is independently hash-verified (`c44c6e0806b6cd60bd33f4d410268bcdbd4e06bfe4333b6e77502989e10dfa71`). Every original proof-file row now matches independently: result, stdout, stderr, execution start, producer source and embedded Linux runner, plus the ordinary-driver source. The subsequently fetched 363-byte ordinary execution start matches SHA-256 `49f960fc0727a550f263be79643d2aa54de4543b674e020d8b2a52257ce13108`; its producer/runner hashes, attempt identity, rootless actor and dedicated lab also agree. No ordinary-proof metadata gap remains.
