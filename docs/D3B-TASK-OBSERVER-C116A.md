# C116A - actual Task metadata observation and safe observation retirement

One additive gateway_work_observer module uses the existing B115 policy data
model and W115 native reader. It is not a new scheduler, executor, storage owner,
HTTP endpoint or source-patch activation. All461 prior executable/config files
are unchanged. Native source investigation used immutable featurecc16c10.

## What now comes from actual runtime objects

NativeTaskObserver attaches to an actual borrowed APIServerAdapter and exact
NativeWorkReader on a single process/thread/event loop while its task registries
are quiescent. It pins the borrowed bundle, three native objects, run-task map,
background set, aliases, scope and status map. PID/start identity is obtained
from the native OS-backed process-start query, not a fixture77 or caller flag.

Trusted in-process publish takes an actual asyncio.Task and immutable request
binding. The task must already be present in the native run map/background set,
belong to the same loop, and have neither completed nor received cancellation.
No complete/task_alive/healthy flag is accepted from a caller. Phase progression
QUEUED->RUNNING->SETTLING can only be published by that exact current Task.
The observer never schedules, awaits, cancels or transfers task execution.

capture samples the actual task registries before and after the existing read.
It rejects missing/unregistered/replaced tasks, extra background/session work,
unknown pending counters, active native executor threads and unqualified ingress.
The native worker counter is checked even when its wrapping asyncio Task has
already finished or been cancelled. A live carrier task is not automatically
proof that a different thread or external BotChat executor is healthy.

Expected run scope/key/fingerprint and optional response fingerprint are fixed
by trusted producer publication, independently of candidate rows. The returned
metadata must match those exact identities. Producer revision, task state,
status and alias/scope/handle identity are rechecked without yielding the loop.
Observation failure is sticky when ownership/binding is uncertain. Native mutex
or transaction unavailability is retryable with fresh evidence and no rollback.
This is cooperative synchronization, not a hostile same-process/ABA defense or
an atomic transaction across three files.

## Successful retirement is not automatic forgetting

retire_completed only deletes an observer's own entry. The real Task must have
succeeded, not been cancelled, and reached SETTLING. The native producer must
already have removed its task and background entries; the observer never does
that for it. It then selects the referenced terminal rows via the SAME reader
and confirms exact admission/session generation/epoch, terminal run/process
identity, matching fingerprints and a settled response, with no unresolved
workers. Native terminal status and remaining task inventory are rechecked.

An incomplete response, failed/cancelled task, wrong fingerprint or late owner
change prevents retirement. A currently open transaction is left untouched and
may be observed again after its owner explicitly settles it. Successful
retirement leaves drain latched and does not release stores or profile ownership.
It does not assert that all other system work is done; other rows remain visible
to the existing policy/next collector layer.

## Explicit remaining boundary

TaskBoundRows carries actual Task metadata and committed rows. Its public output
explicitly states storageIntegrityVerifiedHere=False,
nativeProducerHooksVerifiedHere=False and serviceReadinessVerified=False; all
admission/retry/store-release authority stays False. The collector does NOT
manufacture the storage_verified flag required by the pure policy.

Native borrowed connect is still refused. Native current run producers do not
yet publish these register/advance/retire hooks. In particular borrowed mode has
no gateway_runner/session authority, so simply running the native HTTP handler
would NOT establish the canonical admission/owner path. The Task may also be an
authority/BotChat watcher rather than the actual executor. Hook placement and
covered execution families require explicit integration, not optimistic inference.
The next stage must bind producer publication to trusted ingress and qualified
canonical execution, then bracket it with real profile/mount/storage verification
and test that same path under isolation before active-work HTTP wiring.

## Tests actually executed

34 focused standard methods use real asyncio Tasks, including cancellation before
the next tick, current-task phase updates, cross-thread rejection, changed read
revision, fingerprint mismatch, retained drain and normal/error retirement.
Their native adapter/storage boundaries are EXPLICITLY DOUBLED; these are not
native-service proof. Five additional offline receipt checks bind actual logs
and sources, not another native run.

Eight Windows native completion methods use the actual APIServerAdapter,
BorrowedAPIStores, three native SQLite stores, OS process-start query, real Tasks
and native admit/claim/settle/status APIs. The normal task moves QUEUED->RUNNING->
SETTLING, its producer finishes data/native task retirement, and the observer
returns to empty Task inventory without releasing the profile. Negative cases
cover partial settlement, open response transaction, task exception/cancellation,
changed fingerprint, latched drain and missing native producer retirement.

SQL tracing/connection and raw DB-open audit verify no observer writes/opens;
owned total_changes remain unchanged. Native classes/functions are not replaced.
312 actually imported native modules were reread from immutable no-replacement
Git and matched to reported hashes. All owned temporary profiles are closed and
released by the fixture. One optional urllib3 IPv6 feature bind is DENIED during
import; Windows event-loop wakeup sockets are allowed only for framework setup.
Zero additional network attempts or provider/model requests occur in cases.

Crucially, publishing the Task into native registries and immutable request data
is an EXPLICIT TEST PRODUCER SEAM. Task liveness/cancellation and OS start are
real now, but this does not prove production native ingress hook coverage,
profile/mount identity, Linux isolation or a functioning agent/model call.

C116A4 independently tests the same observer, including actual native executor
thread survival after a carrier Task is cancelled. Its original22-pass proof
on a2d49ec is historical after the retirement refinement; only its source-matched
current rerun may qualify80ac827. Preserve the original branch evidence/history.
The full standard regression remains pending until the combined tree is qualified.
Do not add overlapping native suite counts as independent scenarios.

## Change and safety boundaries

Only one additive observer and own QA/tests are selected. Existing cold startup,
quiescent HTTP, policy, reader, source locks and native patches remain unchanged.
No WSL/root/mount or previously blocked cleanup/refinement is retried. No agent
listener, provider/model, user profile, account, production, CIqueue, main merge
or remote push. Vendor main remains eb75627; featurecc16 is test-only.

Records live in evidence/d3b-task-observer-c116a/. Original a2d49ec source remains
in observer-before-completed-retirement.py.txt; it is not relabelled as current.
All future source changes need new relevant native/standard acceptance. FullD3B,
real native hook coverage, active-work HTTP and cross-store recovery stay OPEN.
