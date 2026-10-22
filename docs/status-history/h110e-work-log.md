# AlazHarness — status

## D3B-HTTP-READINESS-H110E — IN PROGRESS

Branch alaz/d3b-http-readiness-h110e; worktree scratch/worktrees/d3b-http-readiness-h110e.
Base82a8c3e, canonical A109 NativeStoreStartup only. Preserve414 existing source
files, main/remote/CI, root user edits and any concurrent feature. Prior full
handoff byte-preserved in docs/status-history/h110e-parent.md.

Scope: a small readiness-only HTTP lifecycle using existing aiohttp, no hand-
rolled HTTP parser or second native datastore owner. The pinned Hermes API
adapter constructor creates separate replay/response stores; do NOT instantiate
it as though it reused the verified A109 pair. Only explicitly authenticated
loopback liveness/readiness routes here; NO task/model/provider/agent routes.
No listener before A109 storage verification; readiness revoked on observed
ownership/identity/epoch failure and before shutdown. Drain owned HTTP requests
before closing native handles, retain caller ProfileLease on unknown cleanup.
This is NOT full Hermes Gateway HTTP admission or broker dispatch acceptance.

First inspect available dependencies, implement with real HTTP tests plus
explicit lifecycle doubles, then actual pinned native sequence on fresh owned
profiles in approved P71C where feasible. Use unique H110E files only. No new
root/mount/account/service/defaultUbuntu/config/push operation planned.
Baseline/evidence: evidence/d3b-http-readiness-h110e/. No native job pending.

### Actual native001 started
Request e110f0a1-19cd-4d37-b283-005100000010 pending. Current product source includes ASCII-only bearer validation; no modifications while this run executes. Actual aiohttp3.14.3 source reuse verified against installed RECORD; lab has no system aiohttp so pure sources in fresh temporary code tree only. Tests cover preopen failure/no bind, occupied port/known epoch effect and real readiness/revocation/transaction-close. No alternate runtime; concurrent R110X6C2 is independent QA only.

### Independent auth finding corroboration
Parallel R110X6C2 found invalid-UTF8 Authorization500 in its earlier c8d8ff1 snapshot. This branch already added ASCII-only+nonempty validation before native001; added explicit Unicode/surrogate unit regression,27methodsPASS. Product bytes unchanged throughout native001; fixed current source must be independently retested, not attribute old snapshot success. No parallel source overwritten.

### Native001 refused optional MIME dependency
Native001 finishedFAIL with unchanged sources and tempcleanup: wrong-schema case passed, aiohttp import tried /etc/mime.types under Landlock before occupied-port check. Knownfiles public configuration now temporarily empty during stdlib MIME seed; restored afterward. No new file grants or dependency/native functions changed. Initial runtime/receipt and direct Python3.12 empty-files API mismatch retained. Fresh native002 required; unit30 current methods pass if terminal receipt confirms.

### Native003 PASS / full regression started
Native003 terminal0:55 overlapping checks across fresh prepare/preopen-refusal/bind-conflict/normal nativeHTTP lifecycle. Wrong schema no parent nativeopen/port; epoch drift200->503 stays503 after restoration; HTTP closes before transaction settlement/lease release. Native sources unchanged, temporaryroot removed. Current product real-wire independent29PASS, unit30PASS, receipts5PASS. Earlier MIME and QA parser failures retained. Full e110f0a1-19cd-4d37-b283-005100000021 now IN PROGRESS;418 source freeze,414 baseline unchanged. No source/test edits until terminal.
