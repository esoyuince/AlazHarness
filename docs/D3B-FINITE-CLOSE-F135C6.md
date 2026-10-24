# F135C6 - Finite computed work and original-owner clean close

## Accepted local scope

A real programmatic API request reaches the native canonical adapter, authority,
finite dispatch, TurnRunner and physical worker thread. The explicit bounded
model double computes SUM:17,25,8 -> 50; native code persists the result and marks
one admission terminal/completed. Exact retry returns the original result without
a second computation; changed payload with the same key is rejected. There is no
fixture-written terminal row. A second scenario raises a controlled computation
exception and validates native failed-result persistence/retry and normal closure.
Neither scenario is an authenticated HTTP or real LLM/tool integration test.

Native and harness lifecycle now close normally after that real work. The original
owner closes all three original SQLite connections, not fixture teardown. Before
fixture cleanup registry references are already zero. Agent.close is called;
executor/cache/session resources retire before API withdrawal and runner detach.
Caller still owns and releases its own profile lease. SQL row counts do not change
during retirement/detach. Results/history are preserved and not fabricated to make
an idle-state check succeed. Both successful and failed-computation paths pass.

## Goals uses the existing caller connection

The goals helper formerly acquired a registry-managed state.db during a physical
turn. Native execution now composes its original profile scope with a revocable,
context-local borrow of the already-owned state. Real goals, loop and heartbeat
operations see the same caller SessionDB. No cache/registry ownership is acquired
or released in that selected path. Expired copied context or foreign authority/
profile/state fails instead of silently opening another DB. Ordinary unbound CLI
and gateway callers keep the registry path unchanged. Actual full-turn audit shows
zero new state.db opens; the explicit default compatibility control still covers
its intentional ordinary acquisition behavior.

## One-way native resource retirement

After begin_drain seals new acceptance, await retire_idle_runtime() verifies live
native dispatchers, physical threads, tracked writes, observers, open transactions
and durable obligations. An idle exact native executor, only the identified API
session state and exact cached agents are eligible. It shuts the native executor,
awaits the declared agent close method, then rechecks identity and obligations.
No queued work is cancelled or discarded to pass. A cancelled await does not imply
the close thread stopped; the task/plan remains owned and uncertainty blocks release.
Partial or unexpected effects retain UNKNOWN, not a retry ticket. Agent memory
manager/provider cleanup is not qualified by this bounded test and remains refused.

Native session retirement follows. The legitimate native fast-save cache is a
receipt for a completed per-entry UPSERT, not necessarily an unsaved write. Every
eligible receipt must exactly match the durable row in SessionStore._routing_scope
(the resolved sessions directory) and the current native entry, with verified
routing generation bounds. Empty authority scope remains separately checked for
API identity. Only proven memory receipts are removed; full-save counters, SQL
rows and history are not rewritten. Corruption, changed entries, foreign routes
and unresolved generations remain refusals. Final close checks are current, not
based on a stale DRAINED status.

## Failures and compatibility retained

Early normal computations correctly produced50 with no extra DB opens but failed
retirement on the fast-save cache. The initial receipt query used empty authority
scope, while native SessionStore writes its receipt to its own sessions scope.
Actual001-004 failures, cached/durable diagnostic and source snapshots are retained.
The scope fix used the correct native namespace; it did not weaken equality or
rewrite a row. Actual005 then closed normally. Final-normal/final-compute-failure
add physical connection, model-close, zero-row-write and original-owner assertions.

Independent Q135D8 reproduced the same old refusal and passed unchanged hint
expectations on the corrected source. Its final native checks cover16goals,
15resource retirement and6persisted-hint cases. Those original raw results remain in its
separate branch. Exact copies of the final results, original failures and driver
bytes are preserved in independent-q135d8-readback with explicit provenance. This
is readback evidence, not a merged QA history or another execution. Source hashes
are bound in source-custody-r136c6.json. Independent normal/
failure actual-close runs overlap the two original scenarios and are not four
new feature classes. Current native publication compatibility53/53 passes. The old
canonical owner selection39/39 also passes on current harness with old native5ff;
its earlier160-second timeout and unchanged subsequent300-second completion are
preserved. No remote CI timeout or product policy was changed by this work.

## Verification identities and reproducibility

Optional native feature d1516731308de8e87130dc68124e69aad35d6911 extends5ff88189 in
8files. Patch0011 reproduces those exact files and duplicate application is refused.
The selected finite manifest contains755pinned files; older prepared, admission and
canonical manifests/defaults remain unchanged. Finite is explicit and implies
canonical_api=True and local_admission=True, never activated by default.

The current original/independent/compatibility observations span756native files;
all bytes match immutable native Git. The normal finite run itself loaded/executed
748files; its failure scenario745. These are source counts, not test counts.
The11focused standard checks include3selection contracts and8offline result/source
receipts. Their thread assertion was strengthened during resume: compare observed
API loop thread set against actual run_sync worker set, not an absent metadata
field with a default value. Runtime code and executed native tests did not change.

The new complete standard result, exact frozen source/patch manifests and skip
comparison live in resume-r136c6. Completion is only claimed once its terminal
result exists; no native experiment was repeated merely to resume an interrupted
chat. Earlier failures remain failures. Any historical helper resolves only the
exact archived execution generation; it is not new-source runtime acceptance.

## Remaining acceptance

Windows actor/lease metadata, mount/layout and cold helpers are explicitly doubled.
Native API, scheduler, tasks, SQL, physical threads, persistence and owner cleanup
are real. The AIAgent factory/computation/close is an explicit bounded fixture.
No root/WSL/provider call, HTTP listener, real LLM or paid model, current native
Linux isolation, power-loss recovery or full M1/M2 claim. Current code still needs
active Linux isolation/HTTP tests and broader worker cancellation/restart/budget
acceptance. A successful error-result replay is not a general recovery proof.

Main publication4d37687 is already complete. This new finite feature remains on
its development branch until the exact new commit has passed remote CI. Installed
vendor/source locks stayeb75627; no main update or runtime activation is implied.
Original user changes and independent worktrees must remain untouched. The exact
next source/test/commit state is in status.md and resume-r136c6 records.

## Terminal complete standard regression

Current fullWindows3448=3425PASS/23SKIP/0ERROR/0FAIL, actual command136cc601...000006 exit0.602 source/config/test and11patch hashes stable throughout. Same23skip IDs/reasons, no skip relabelling. Existing597files:591unchanged,4runtime+2historical-test files changed,5newconfig/test/QA files. Test fixtures11/11 are included subsets. Independent raw evidence readback copies add no executed tests or product changes. No new native/Linux/provider/HTTP run was needed to recover the interrupted checkpoint. Local static and Git delivery follow on the same source.
