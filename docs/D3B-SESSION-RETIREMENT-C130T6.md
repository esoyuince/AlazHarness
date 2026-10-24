# C130T6 - idle native API session retirement without durable deletion

## Actual boundary discovered, not full request execution

J129's original owner can select local native admission, but that is not a full
API turn. Eagerly importing the real API entry loads three modules outside its
fixed517-file source envelope: gateway/session_api.py, session_results.py and
session_api_turn.py. Actual same-owner preparation refuses BEFORE admission;
consumerFAILED_UNKNOWN retains original three handles and profile. The first
uncaught fixture result and later diagnostic-only result are both preserved.
No whitelist bypass or late import trick was used to call that a running request.
The independent peer also observed that direct native library API admission has
no published delivery adapter and retains a bound session on refusal. That is
an unqualified route, not a general upstream defect.

This milestone handles a narrower concrete leftover: after native leaf work is
terminal, SessionAuthority still retains its LiveSession and SessionStore route
cache. finish_drain correctly refuses those. Existing retire_live_sessions is for
committed DELETIONS; using it here would conflate release with deletion. This
optional native operation releases only explicitly idle ordinary API memory and
preserves the persistent session, transcript, routing and retry identities.
It does NOT implement queued-at-seal FIFO consumption, full agent execution or
the request/physical-worker publication seam. Those are still required next.

## Three-file optional native feature

Native13186a5f8a25949e05ffacddbaafd2461989eaac on1b7b31e1 adds the explicit
BorrowedAPIStores.retire_idle_api_sessions() method, its sibling implementation,
and a narrow internal idle-check option. Ordinary checks retain their original
defaultFalse option and still require no live sessions. No second owner, scheduler,
ledger, connection, epoch, service-start permission or native default change.

The operation requires DRAINING in the same owner thread/event loop. Current native
identity/config/profile, all original work registries, physical workers and clean
ledgers must pass. It then checks every actual LiveSession BEFORE any removal:
ordinary API identity, real completed non-cancelled/non-failed dispatcher or no
dispatcher, free mutation/claim locks, no subscribers, controls, observers,
settlements or fanout peers (including detached still-writing peers). Native
worker records must already have been retired by their own owners; task.done is
not used as physical-worker proof. Cached agents/executors remain refused.

Facade/event/fanout/state mutexes are taken without waiting. Dirty transcript,
unpersisted routing generation, inflight entry publication, foreign metadata,
changed source context or memory/durable active-turn markers retain all entries.
Both native API private binding and current persistent route/session identity are
checked. The caller remains responsible for unregistered same-process writers;
this is a cooperative operation, not protection from arbitrary in-process mutation.

Only the proven authority and facade memory entries are removed. No SQL write,
connection open/close, epoch advance, recovery, callback, cancellation or wait is
performed by retirement. All three logical SQLite dumps and total_changes remain
unchanged in the watched successful/refused cases. A returned retirement receipt
is NOT permission to close: existing finish_drain and ordered API/runner detach
still reobserve current state; the caller owns final store/profile release.
Rebinding memory after retirement causes the normal finish guard to reject again.

## Failures reproduced and fixed without weakening assertions

Candidate001 passed23 of24 native methods. A reply still owed to a native waiter
was missed because the registry name was wrong. Three added cases then failed on
the unchanged candidate: memory turn marker, durable turn marker and live profile
drift. Those four omissions were corrected only in the new sibling. The exact
same27 method bodies passed candidate002. All initial outcomes and source/QA
bytes remain in evidence, not relabelled final acceptance.

One further test injects a tracing exception AFTER the first real memory removal.
Native methods are not replaced; the artificial trace fault is explicit. The
operation retains ADMISSION_UNKNOWN, keeps all caller connections/profile and
all durable data, refuses retries and detach. The partial memory effect is not
undone or called a clean drain. Final current28/28PASS includes this check.
Unchanged prior local-admission28/28 also PASS on the same new native bytes.
These suites overlap and are not56 unique full-agent scenarios.

Current native tests call real API binding plus actual guarded native leaf
admission/claim/settlement; a completed leaf record is NOT described as executing
its agent payload. Native objects, SQLite, event streams, asyncio tasks and threads
are real. Explicit memory/SQL faults stay in fresh owned test profiles. Every
successful test fixture removed its profile and released registry references;
fixture disposal of retained/unknown state is NOT product shutdown acceptance.
The harness API baseline uses the prior explicitly doubled Windows Linux-boundary
fixture; current native retirement cases are direct native constructors, not
original NativeStoreStartup or a Linux confinement run. No model/provider/HTTP.

## Exact artifact and source custody

Current28 loads512native Python files and original28compat loads514; each exact
source matches immutable feature13186a5f. API refusal baseline448 imports match
immutable1b7. Prior candidate outcomes match their saved3file overrides and native
base. Eight offline receipt tests bind exact outcomes/scope/QA/Git blobs and are
standard-suite subsets, not eight native replays. Native journal warning and
DELETE fallback remain in raw logs; no interpreter/dependency upgrade happened.

Ninth patch patches/hermes/c130t6/0009-caller-owned-idle-api-retirement.patch and
config/hermes-session-retirement-c130t6.json are STAGED_NOT_INSTALLED. Fresh apply
in an isolated ignored Git staging tree reproduces all3tested hashes and second
apply is refused. The first apply fixture inherited its parent Git prefix and
skipped patch paths; exact byte assertions caught the no-op. That separate tooling
outcome and untouched first stage are preserved; native tested code did not change.
No installed vendor/source-lock/current source envelope was promoted.

All572prior harness source/config/test files unchanged. This branch adds optional
artifact, QA, evidence and documentation only. Independent peer qualification and
ONE complete standard union must precede canonical delivery. Do not duplicate full
or replay finished native tests just for status. Scope of real complete request,
queued completion, memory/agent-cache finalization, current physical-worker trace,
Linux confinement and HTTP remains OPEN. Maincc7ceba and installednativeeb75627
unchanged, no push/provider/root/WSL/production/account or previously blocked action.

## Exact next integration work

Qualify the actual API-entry source set and publish the SAME native adapter through
its existing canonical resolver/registry with an explicit lifetime; do not assign
private fields after eager construction or add another resolver. Then exercise a
real accepted request/TurnRunner/physical worker with an explicitly bounded dummy
model boundary, native result publication, cache release and session retirement.
Decide accepted queued-at-seal completion without replaying unknown outcomes.
Only then transfer exact source/runtime to the existing isolation/HTTP acceptance.
Current memory retirement does not substitute for any of those gates.
