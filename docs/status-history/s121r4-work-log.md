# AlazHarness - status

## D3B-SESSION-BORROW-S121R4 - IN PROGRESS

Harness branch alaz/d3b-session-borrow-s121r4; worktree scratch/worktrees/d3b-session-borrow-s121r4; base9418bf0. C120A clean full3148=3125PASS/23SKIP already terminal and delivered; do not replay. C120P9 extension stays HOLD/outside executable paths.

Selected next narrow feature: explicit optional caller-owned SessionDB in native SessionStore construction. Reuse one already-open state handle, reject wrong home/profile/changed handle/closed state without opening a replacement or silently falling back. Closing the SessionStore must not close caller state or release profile. Default constructor remains unchanged. Native separate worktree on feature94321058, not vendor main or installed runtime.

Do NOT remove borrowed_runner_conflict or activate shared API listener. Full canonical runner bootstrap, all-three lifecycle, profile/mount and active HTTP acceptance remain separate. No blocked probe or root cleanup reissued. No WSL/root/provider/production/main/push/CIqueue changes. Native patch/source tests and exact receipts required before staged delivery. Status changes scoped to own worktree; existing490 source baseline retained.


### Implementation ownership and current candidate

S121R4 owns ONE native SessionStore(session_db=...) option; S121S1 independently reviews/tests it, no duplicate product. Three native files changed, API borrowed_runner_conflict untouched. Candidate validates caller-owned live exact-home native state before default constructor priming, rejects foreign scope/handle/owner changes, no reopen; explicit borrowed mode forbids JSON routing fallback/import. Default path unchanged. Candidate not frozen/tested yet; native suites follow. No claims of full runner bootstrap or active HTTP.


### Native test candidate frozen

Request d121f74b...00013 starts23 actual-native cases, explicit session_db constructor + no-opens/owner/config/transaction/JSON fallback controls. Three candidate native files and QA hash frozen in native001-intent. No changes to candidate until terminal. Independent S121S1 reviews same native source, no duplicate implementation.


### Native23 acceptance and immutable patch terminal

Native00223/23PASS on exact3-file candidate, registryrefs0/profile released/temp data removed. First21/23 failed only preexisting-directory assumptions; original source and failed logs retained. Stage snapshots proved native scaffolding existed before facade. Product unchanged001->002. Native patch committed 2bc50496bebe21f948dd2e86f553ef1e22904ed2 in own fork; exact fresh apply and duplicate refusal verified. Imported unchanged native bytes matched base943Git; API borrowed_runner_conflict bytes unchanged. Current patch remains STAGED/NOT INSTALLED. Next independent QA alignment, offline receipts and one new combined full suite.
