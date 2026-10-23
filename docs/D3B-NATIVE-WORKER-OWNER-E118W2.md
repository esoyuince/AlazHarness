# E118W2 - request-bound actual native worker lifetime

One source-owned native worker book extends the existing RunLifecycleChannel.
The existing executor still runs the function. No scheduler, store owner, Task
map or canonical admission is created by observation. Source base d0028f6,
selected native feature94321058; exact refs and patch in native-patch-custody.json.
Independent counter fix24165690 is preserved as an ancestor, with the final
merge tree identical to the actual tested combined implementation.

## Actual worker, not just its carrier

The native submission creates a ticket bound to the original immutable run
binding and exact carrier Task. Native counted-function entry records actual
thread ID/native thread ID and start time. Its own finally records return/raise
only after native count release. This is FUNCTION invocation lifetime, not the
lifetime of the reusable thread-pool thread. Function return is not business
success, canonical settlement or permission to release storage.

WorkerBook is bounded at256 records with monotonic submission IDs and revisions.
Snapshots are immutable. The original native DONE callback removes the carrier
Task reference but retains the worker record while its function is still active.
Only BOTH carrier release and actual terminal execution remove the record. A
cancelled carrier cannot make a surviving thread disappear. The book retains no
request body, result or exception text and calls no observer callback on the
worker thread. A diagnostic failure latches a gap without unwinding business work.

The harness companion NativeWorkerObserver pins the existing provenance/channel,
process ID/start, loop/thread and borrowed store handles. It brackets source book
reads by native count/revision checks. Contention/races are unavailable evidence,
not a fabricated empty/idle answer. It reports unattributed native workers rather
than claiming every worker belongs to its request inventory. Capture does not
open databases, write/commit/rollback rows, settle work, cancel Tasks or close
handles. Every public service/canonical/admission/retry/store-release grant is
false. The old strict NativeTaskObserver remains unchanged and still refuses
thread execution as canonical in-loop Task ownership.

## Real cancellation defect and correction

E118R1 reproduced native d002's count leak with a real saturated single-thread
executor: cancelling queued work before its callable starts leaves count1 even
after all threads drain, while actual callable calls remain0. Native ownership
had only been released in the callable finally, which never ran.

The correction uses the EXISTING native worker lock for the queued-to-running
versus confirmed-cancelled handoff. A cancellation callback releases only a
still-queued submission and the same locked state forbids later callable entry.
After entry only the actual worker finally releases ownership. A finished future
cannot release twice, and submission failure releases its unstarted reservation.
No counter reset, new executor, worker kill or assumption that Task cancellation
stops a thread. Worker lifecycle markers are composed after these native state
transitions. The independent original fix's Git history is retained.

## What was executed

Native001 on Windows PASS34/34:20 unchanged original native producer compatibility
methods plus14 new request/worker methods. Real auth-decorated /v1/runs entry,
Task/map lifecycle, native executor and actual thread IDs are used. There is NO
QA publication of worker records/tickets/counters/native Task maps. Computation
is deliberately dummy; inherited authority/external delivery edges and one
submission-error boundary are explicit doubles. No provider/model/listener.

The new cases include running worker after cancelled carrier and dropped Task
reference, saturated-queue cancellation with0calls/count0, two distinct concurrent
request/thread identities, replay without another worker, source fingerprints
unchanged by candidate DB tamper, source/sequence/process/book replacement,
transient lock contention, foreign thread refusal, JSON non-enablement, submit
failure, and retention of the old strict observer's refusal. The code does not
claim DB integrity merely because an immutable source fingerprint is retained.

14 companion unit contracts use explicit native/process boundary doubles.
Six offline receipt checks bind actual states, unchanged sources, native committed
imports, exact patch application and no-activation scope. These20 methods are
standard-suite subsets, not additional native executions. Native001 cleans its
owned temporary bootstrap and releases profiles. One optional IPv6 import probe
is denied; zero new network attempts occur during cases. Raw expected injected
failure logs remain preserved, not mistaken for suite failures.

E118R1 independently ran12 native counter-race and10 native request-worker methods
on this same selected94321058 feature. These overlap our34 and are NOT added as
56 unique end-to-end scenarios. Their original counter-only producer compatibility
had19PASS/1first-handler timeout, followed by20PASS on one fresh unchanged retry;
that timing-flaky failure remains retained, not relabelled. Original independent
harness commit/evidence will be preserved before the one combined full run.

474 native modules actually imported by our native001 were matched byte-for-byte
to immutable no-replacement Git blobs. Fresh patch apply to d002 originals yields
exact tested hashes; repeated apply is refused. A first Git merge stopped before
effects because the native repository had no author identity. Subsequent merge
used the EXISTING harness identity only per-command; no global/repo config edit.
The tested native tree is unchanged by the ancestry-preserving merge.

## Installation and remaining authority boundary

The patch is OPTIONAL and NOT_INSTALLED. It includes the counter correction;
do NOT apply the separate counter-only historical patch before this full patch.
Its prerequisite is the H117 native producer feature. Installed vendor/gitlinks/
sources.lock remain eb75627. Native borrowed connect/gateway_runner restrictions
are unchanged. Existing474 harness source/config files remain identical.

This establishes actual LOCAL worker/request lifetime, not a canonical
SessionAuthority claim or external owner health. Those roles remain distinct;
no synthetic admission is fed into publish/advance/retire. Active-work storage/
profile/mount validation, Linux isolation for this feature and healthy/busy HTTP
remain unaccepted. No native upstream full suite, cross-store atomic recovery or
power-loss guarantee. No main/push/production/CI/account/root/WSL/model changes.
Prior blocked cleanup/refinement remains blocked and was not retried.

Next preserve original counter/independent QA histories, run ONE source-frozen
combined standard suite, then canonical delivery. After this slice, connect the
real canonical execution/adoption boundary and verify active storage/HTTP under
the existing isolation policy; local worker presence alone grants nothing.
