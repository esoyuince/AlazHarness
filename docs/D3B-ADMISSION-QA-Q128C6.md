# Q128C6 - independent native admission and drain acceptance

One native product implementation belongs to A128C6 in d3b-admission-lifecycle-a128c6.
This separate d3b-active-lifecycle-a128c6 branch owns independent QA and immutable
source evidence only. It neither edits that native owner nor promotes installed
vendor, the prepared harness source manifest, default observers or any service.

## Accepted local state transition

The tested optional native candidate extends existing BorrowedAPIStores and
CallerOwnedRunnerState, not another scheduler/ledger/connection owner. Explicit
activate_admission(), begin_drain(), finish_drain() transition PREPARED -> ACTIVE
-> DRAINING -> DRAINED. Ordinary service/start/listener paths remain refused.
Transitions keep exact three caller connections and existing epoch. Admission is
checked by the real SessionAuthority guard, including its existing callback inside
the real SQLite write transaction. Default prepared flags alone cannot authorize
new work. DRAINING/DRAINED cannot be reactivated; status is not provider permission.

Native finish requires current task/worker/receipt/response/replay ledgers to be
settled, not merely a cached DRAINED label. Caller still owns all stores and the
profile. API detaches first, runner next; neither closes caller connections or
leases. New unresolved records after finish must refuse before the next cleanup
effect, with another check after awaited API cleanup and before runner closure.

This is a narrow local admission contract, not a running agent. Real fixture
admissions call native ledger functions with the actual authority guard; no API
request driver, native finite-agent execution or physical model call is inferred.
Retained sessions/caches require their existing native owners to retire them.
The fixture does not erase them to manufacture a finish verdict. Existing harness
PreparedRuntimeConsumer and its513-file source envelope are NOT modified here.

## Real transaction boundary, including cancellation

An unchanged1e97 native baseline established nine nested predicates using real
SessionDB, SessionAuthority and SQLite; only the ordinary runner flags were an
explicit fixture. Drain-before-guard refuses the new row without row changes.
A callback already past the guard may still commit after drain starts. The caller
must retain its ownership, not promise that the phase switch synchronously stopped
all writes. Both existing accepted rows remain queued, epoch unchanged.

The same two cases run on the candidate's actual native GatewayRunner/authority/
API/three-store objects. begin_drain does not wait for the held SQL mutex and the
blocked writer rechecks the original transaction gate. A guard-authorized writer
in flight is retained; finish refuses both while it runs and after its accepted
row remains queued. A third actual native tracked_write case cancels the asyncio
carrier while its protected thread commit continues. The native mutation task
remains owned, commits the accepted row, and retires its own task record. The
cancelled caller never becomes permission to close or retry the accepted write.

DRAINING closes NEW acceptance AND subsequent queued claims. It does not execute
all queued successors. Queued and unknown rows remain unresolved and block finish.
A previously claimed native leaf can settle under the same epoch while draining.
Exact native leaf replay returns the same identity, not a new admission. Public
HTTP retry behavior was not exercised. Caller-controlled serialization remains a
precondition; these checks are not a hostile same-process concurrency boundary.

## Four reproduced failures and fixed-source qualification

Independent candidate001 first passed22 then24 methods. Four extra native tests
failed on the same frozen001 source: late unsettled response before API detach,
late real bot-receipt task after API detach before runner close, foreign profile
context in the admission guard, and changed JSON configuration in that guard.
The producer independently found related five cases and corrected the native
implementation. This branch copied only the exact fixed five files into its own
native worktree, never edited the producer. SAME failing QA bytes then ran with
all previous cases:28/28PASS,0errors,0failures,0skips. Initial successful subsets
and four failures retain their historical native/QA hashes; not relabelled current.

The independent final run includes real asyncio tasks, real threads, native worker
records, DB transactions and ContextVars. Deliberate registry faults and the paused
native authorization callback are fixture inputs, not replacement native methods.
No native classes or methods were monkeypatched. No Linux actor/mount/cold helper
is claimed here; this suite constructs native objects in fresh Windows profiles,
not through NativeStoreStartup. All28 fixture profiles, ownership and native registry
references were cleaned; recorded cleanup of retained rows is fixture cleanup,
not a successful product drain. Actual ordinary pending rows were never dropped
by the transition under test. In watched transition boundaries new SQLite opens,
raw DB opens and SQL row changes were all zero.

514 imported native sources in the final run match immutable1e97 Git or the exact
five candidate002 file hashes. Baseline247 native imports match immutable1e97.
Eight offline receipt tests verify those bytes, outcomes, old failures and scope;
they are standard-suite tests, not eight additional native executions. The SQLite
DELETE-mode compatibility warning remains in raw stderr, no runtime upgrade.

## Integration and remaining acceptance

All557 prior harness source/config/test files unchanged in this branch. New QA
and receipts only; full standard regression is pending a SINGLE immutable union
with the original implementation/config/native patch. Do not start duplicate full
or replay finished native work merely to read the evidence. Source commit/patch
custody must match the final optional native artifact before canonical delivery.

Native local admission is not harness active service permission. Next extend the
same original NativeStoreStartup/consumer lifetime with explicit active-mode source
qualification, same current request/physical-worker observation, native session
retirement and preserved unknown outcomes. Then qualify that exact combined path
under existing isolation and active HTTP. No default manifest widening or ad-hoc
retiring/start flag changes. FullAIAgent, model budget/accounting, cross-store
recovery and power-loss acceptance stay open. Prior blocked operations/C120P9
remain unexecuted. No root/WSL/provider/model/listener/production/main/push action.

## Immutable native artifact and completed review

Original native feature `1b7b31e14451baf1d56c3edbfa2cea69a8f7940c` on1e97 is byte-identical to all five independently tested candidate002 files. Patch SHA256 `c5cf4433b66ba57bd9659c7877f83e0ae152501de6fd9e3e02f801c1542c6f12` matches original artifact. Own native QA worktree adopted original history by fast-forward with no code change or test replay. Original native46 and independent28 remain overlapping scopes. The independent read-only review is completed and archived; it tested nothing. Its queued-before-drain and clean-only integration concerns are intentionally still open for the full runtime, not hidden by the local lifecycle PASS. Exact commit/patch/review checkpoint is original-feature-and-review-handoff.json.
