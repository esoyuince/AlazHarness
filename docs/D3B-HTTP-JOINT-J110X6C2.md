# J110X6C2 — storage-readiness HTTP and independent wire QA

This union keeps ONE H110E StorageReadinessHttp and ONE canonical A109 storage
startup. Exact parent commits are in inputs.json. No native Hermes API adapter,
second store owner, custom HTTP parser, model/task/provider route or fallback.

## Selected runtime

Authenticated GET /health/live and GET /health/ready listen on127.0.0.1 only.
A109 native startup and fresh live-store verification happen BEFORE any bind.
Readiness probes recheck identity, ownership, epoch and backing; observed failure
irreversibly revokes readiness. Liveness is explicitly process-only. Shutdown
withdraws readiness before awaiting HTTP drain and closes stores only after
successful aiohttp cleanup. Uncertain/cancelled HTTP cleanup retains stores;
active native transactions prevent storage close without reopening HTTP.

Strict auth/Host/origin/path/method/body parsing and no-store responses define
local diagnostics, not a public auth provider or full agent API. Caller tokens
must be independently random; shape alone is not entropy or launch authority.

## Bugs and environment, original failures preserved

Independent real-wire testing reproduced old c8d8ff1 invalid-UTF8 Authorization
returning500 rather than401. No auth bypass occurred. An ASCII guard in an OWN
scratch copy passed; concurrent H110E incorporated ASCII/nonempty checking and
was retested separately. The MIME-qualified selected hash is
7fde274d143e6bf4707a8318b00c942a308e61bdebbbf02eb3558337ae8f0cd1.

Native001 failed because aiohttp imported optional MIME data denied by Landlock.
The runtime now seeds builtin MIME data with temporarily empty knownfiles and
restores configuration, rather than granting broader file access. Native002
exposed QA parsing of a non-JSON parser refusal; original output and fixture
correction remain. Native003 passed on current source. No library/native method
or filesystem/proc grant was rewritten. Two independent QA cleanup cases first
failed due to slotted AppRunner method assignment; class-level test injection
fixed the harness, not the product. Every first outcome remains inspectable.

## Evidence scopes

H110E native003:55 overlapping checks in actual A109/Hermes/aiohttp final-exec
Landlock cases. Wrong schema has no parent native open/port; occupied port leaves
known epoch effect and refuses restart; real readiness200 becomes503 on epoch
drift and remains503 after restoration. HTTP closes before native transaction
settlement/profile release. This is NOT the full P102 mount/network/cgroup HTTP
path and NOT native APIServerAdapter. The union matches sources/receipts and
performs no new native execution.

Independent R110X6C2 runs29 real TCP/aiohttp methods on each of Windows/Linux.
Storage/profile/identity checks are explicitly doubled in those wire tests.
Auth/body/framing/header bounds, closed work/model routes, revoked readiness,
handle/epoch drift, port conflicts, slow headers, cancellation and cleanup order
are covered.29 repeated platform methods are not58 scenarios.108 Linux pure
sources independently match installed RECORD hash+size; no dependency install
or compiled-extension transport. Latest MIME-qualified code passed both runs.

H110E30 unit methods and5 native receipts plus independent6 offline wire/source
receipts are standard suite subsets. Wire executions/native predicates are not
added to the full count. A NEW complete combined suite runs on420 frozen source
files; parent successes are not substituted.23 old platform/opt-in skips are
not newly executed. All414 original source files are unchanged.

Both histories, source snapshots, original failed logs and evidence Git blobs
are preserved; only status.md conflicted. Prior handoffs live in separate
status-history files, not recursively appended. One union launch command had a
local literal syntax error before effects, and one custody check conservatively
rejected a canonical ancestor because it assumed a documentation descendant.
Both tooling stops are recorded; source/tests/evidence were not rewritten.

Own temporary code/profile/test processes were cleaned, sharedP71C not stopped.
No root/mount/account/service/defaultUbuntu/CIqueue/main/remote/provider action.
Canonical ancestry must be rechecked before fast-forward and any later docs
preserved. Never reset it to this feature or overwrite concurrent source.

## Remaining boundary

This readiness gate is intentionally quiescent. Real in-flight agent work needs
a separately reviewed healthy/busy policy and a borrowed-store contract,
including native response state. Then qualify the same fixed path under full
canonical mount/network isolation and broker live-ledger/dummy-provider dispatch.
Do not expose work routes now or infer paired atomic recovery/power-loss safety.
LegacyIPCv2 remains CLOSED/fullD3B OPEN; old R91F/G82C denied work not retried.

Terminal new full/static results and exact merge/canonical delivery are recorded
in summary.json, delivery.json and status.md, not inferred from separate suites.

## Final combined result

NEW full Windows2735 =2712 PASS /23 SKIP /0 errors /0 failures, exit0.
All420 source/config/test/script hashes are unchanged before/after. All414
baseline sources remain exact.105 original evidence Git blobs are preserved.
This is the complete union regression, not addition of parent test counts.
Independent29 wire methods repeat across Windows/Linux with explicit storage
doubles; H110E55 native predicates remain a separate current-source genuine
storage/HTTP experiment. The union does not rerun native/full isolation.

Local static follows in static-final.txt; remote CI/release is not inferred.
Canonical clean ancestry and source hash checks must precede local delivery.
