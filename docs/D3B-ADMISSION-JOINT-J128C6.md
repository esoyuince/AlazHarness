# J128C6 - explicit native local admission / retained drain qualification

One A128C6 native feature and independent Q128C6 acceptance; both original
histories/evidence preserved. Native feature1b7b31e1 extends1e97dd61 in5files.
This union stages an optional patch, NOT a live source-lock or installed runtime
promotion. Every prior557 harness source/config/test file stays unchanged.

## Explicit local lifecycle, no second owner

The existing BorrowedAPIStores object exposes activate_admission(), begin_drain(),
finish_drain(). Its existing CallerOwnedRunnerState moves PREPARED -> ACTIVE ->
DRAINING -> DRAINED, never back to ACTIVE. Default prepared behavior stays closed.
No fourth connection, new epoch, alternate scheduler, registry, ledger or profile
lease. Actual native SessionAuthority validates the phase at its entry and original
SQL callback before new admission or claim. Two forged flags do not authorize work.

The guard also verifies current profile/configuration/connection/registry identity
without taking a SQL lock or querying while the native transaction owns its mutex.
Native durable epoch checks remain authoritative. Standard GatewayRunner.start(),
API connect/listener and provider/model permissions remain refused. ACTIVE here
means a qualified LOCAL admission gate, not a running HTTP service or whole agent.

## Commit linearization and retained obligations

A new writer still waiting before the native transactional guard is refused when
drain starts. A writer already authorized inside that transaction may commit
AFTER the phase switches to DRAINING. Ownership is retained until its actual
commit/refusal result; an asyncio caller cancellation does not stop the thread.
The independent suite exercises real native tracked_write shielding: cancelled
carrier, retained mutation task/commit, accepted queued row, and refused finish.
No observer creates substitute rows or claims that cancellation undid a write.

Drain is nonblocking with respect to the held state SQL mutex. It stops new
admissions AND subsequent queued claims. Previously CLAIMED work can settle with
its original epoch/generation. QUEUED and UNKNOWN records remain unresolved and
block finish; they are not auto-executed, rolled back, cancelled, discarded or
replayed. Exact leaf replay retains the same ID, not permission for a new request.
This is deliberately not yet a fully integrated graceful FIFO drain/restart path.
Native retained idle sessions/caches must also retire through their owner later.

finish_drain is a fresh observation, not a permanent release ticket. Current
native tasks/worker records/SQL/replay/response obligations must be settled. API
then runner can detach, caller stores/lease remain open. Late obligations are
checked before API detach, after awaited cleanup, and before runner detach.
Unknown/cancelled cleanup retains CLOSE_UNKNOWN and refuses blind retry. There
is no fake counter reset, registry pruning, automatic rollback or epoch change.

## Evidence: baseline, failures, actual current native scopes

Unchanged1e97 baseline9 nested predicates establish native transaction semantics;
its ordinary runner flags are a declared fixture. Current original46/46 native
methods and independent28/28 PASS on exact same5native hashes. They overlap and
are NOT74distinct scenarios. Original46 contains22prepared compatibility+24new
admission methods; independent28 includes two transaction linearization races,
actual tracked cancellation, physical-thread lifetime fault records, wrong actor/
loop/config/profile, unknown/queued rows and late release obligations.

Native constructors/authority/API/stores/guards and SQL are real. Tests use guarded
native leaf ledger/claim/settlement operations, NOT complete public API requests,
full AIAgent/TurnRunner execution or the original harness NativeStoreStartup path.
Actual threads/tasks, paused callback and substituted memory-cleanup object are
explicit fixture barriers. No native method replacements. Transition observations
have no new SQLite connections/raw database opens/row changes. All successful
fresh fixtures removed profiles and released ownership/registry; forced cleanup
of fixture-retained rows is never called product drain success.

First original38/39 fixture-envelope error is retained (native source unchanged
for correction). Original5 and independent4 extra failures on candidate001 are
preserved; identical failing assertions pass fixedcandidate002. Two final original
awaited-cleanup cases pass unchanged native source, including a new replay while
cleanup awaits and cancelled await with native thread still running. First patch
application CRLF-only fixture mismatch and missing native commit identity also
remain in evidence; expected native attributes and per-call existing identity
fixed tooling only, not native tested bytes or global settings.

Original508 and independent514 actual native imports match immutable native
feature exactly. Staged config+patch reproduce all5testedfiles; duplicate apply
refuses. The old installed source/513-source prepared envelope, current observers,
previous runtime code and raw results are untouched.16 offline new receipts are
standard-suite subsets, not additional native runs. Full/selected/static terminal
counts belong to this union's evidence, never inferred from prior success.

## Remaining runtime acceptance

The read-only reviewer completed and was archived. Its baseline review confirms
that old clean-only storage/consumer gates cannot simply be reused as ACTIVE
health checks; retained sessions and queued-before-drain require an explicit
native finalization/reconciliation contract. Its route-reservation race concern
is source reasoning, not a reproduced current product failure.

Next integrate the selected native generation with the SAME original harness
owner, phase-appropriate source/lease/mount/storage validation, exact accepted
request/physical-worker observations and native session retirement. Then run
that exact active path inside the existing Linux confinement and through HTTP.
Do not repin the old prepared-only manifest or flip private flags to claim success.
Current tests do not accept all-agent liveness, cross-store atomic recovery,
powerloss durability, real model budget/accounting, or production activation.

Installed vendor eb75627 and maincc7ceba unchanged. No root/WSL/kernel test, provider,
model, listener, production/account change or remote CI/push performed. Prior
blocked root/refinement/C120P9 operations remain blocked/unexecuted. Read status.md
and final delivery.json for exact canonical commit and remaining scope.

## Terminal complete standard run

New full standard3343=3320PASS/23SKIP/0ERROR/0FAIL. Original command requesta128c601...000031 completed with exit0; old skip structures were normalized by explicit ID/reason before execution.563 source/config/test hashes and8patches unchanged, all557prior files unchanged.16offline receipts are included subsets. This complete run did not repeat native/WSL experiments or activate the native patch. Local static is separate from remoteCI.

## Canonical staged-artifact delivery

Tested union `53ddfd108759b32c71a7b9f1857bb044710b9a1c` fast-forwarded from `39a1be3a8786f52bc792d20ca20ee53e92c993a6` into canonical development. All563 source/config/test hashes and8patches still match full3343; current16offline receipts PASS. Native feature1b7b31e1 remains optional/uninstalled; old prepared source envelope and current harness runtime unchanged. Final handoff changes only documentation/evidence. No native/full replay, main merge, push or activation.
