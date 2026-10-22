# AlazHarness — status

## D3B-HTTP-QA-R110X6C2 — IN PROGRESS

Branch alaz/d3b-http-qa-r110x6c2; worktree scratch/worktrees/d3b-http-qa-r110x6c2; base82a8c3e. Independent adversarial HTTP lifecycle QA for concurrent H110E readiness-only layer. Do NOT create another HTTP or storage runtime. Never modify H110E uncommitted sources, native vendor, production services, existing CI, defaultUbuntu, main/remote. Earlier desired worktree name collided at assertion BEFORE any write; H110E belongs to another active task and is preserved.

Scope: actual loopback protocol tests (authentication, no model/work dispatch, stale storage readiness, cancellation/cleanup, port conflicts) plus explicit boundary doubles where needed. A109 remains only canonical NativeStoreStartup. Runtime source hashes before/after must match tested H110E snapshot. Do not count stub storage/HTTP as actual native or full isolation. Readiness-only endpoint is not a full Hermes API adapter; native constructor opens additional response/replay state and cannot be blindly adopted.

414 baseline sources frozen. Prior full status byte-preserved in docs/status-history/r110x6c2-parent.md. No pending operation. Next inspect current H110E API and dependencies, prepare independent tests without modifying its worktree; qualify sources before shared/canonical integration. No automatic merge of an alternative runtime.


### Independent real-HTTP finding

Initial25 network/lifecycle tests pass after QA-only slotted AppRunner mocking correction. Expanded29 found a REAL candidate bug: invalid UTF8 Authorization produces500/UnicodeEncodeError rather than401; source c8d8ff1 unchanged. No authentication bypass or native store use. Evidence windows-003/ and authorization-ascii.patch; one isascii guard before encode proposed in own scratch snapshot only. Concurrent H110E product untouched; canonical must not be labelled fixed until selected patch/tests integrated. Fixed snapshot full audit request017 now running; actual HTTP, explicit storage/profile doubles, NOT native Gateway acceptance.


### Current independent QA PASS; complete regression started

Current H110E source9612d3c includes ASCII+emptyauth protection. Own fixed snapshot and current candidate29/29 realHTTP tests PASS Windows; same current29/29 PASS ordinary Linux purePython aiohttp, source hashes exact, temp removed. Storage/profile boundaries explicitly doubled, no native storage or full isolation claim. Prior invalidUTF8->500 failure and QA mocking errors retained.6 offline receipts PASS. Full regression request023 now IN PROGRESS,416 source freeze,414 old sources unchanged. Do not edit executable/test sources while pending. Concurrent H110E remains untouched; no product promotion yet.
