# J117B - source-wired native run notifications and independent acceptance

One original H117B implementation and the independently written P117N1 acceptance
are preserved through their original commits. The native feature and exact patch
are optional source artifacts, not a runtime/source-lock upgrade. The concrete
consumer is gateway_native_run_provenance; existing policy/reader/Task observer
and all467 previous harness sources remain unchanged.

## What this boundary now proves

The native decorated /v1/runs entry, not QA registry writes, creates the binding
and actual Task notifications. Ordinary auth/request validation, durable replay
selection, Task creation, status, native retirement and done callbacks execute.
Expected scope/key/fingerprint is captured from original ingress variables, not
read back from a candidate DB as its own expected truth. Retry/conflict/auth
refusal do not publish another admission. Default no-observer behavior remains.

Notifications explicitly distinguish a thread carrier from canonical-authority
and external-owner watchers. They do NOT prove that a separate executor is alive
or healthy. STARTED names the native carrier/watcher's Task tick, NOT a canonical
admission claim. EXECUTION_RETURNED is a return boundary, not success. DONE can
coexist with native failed/cancelled status or a still-live executor thread.

Same source/Task/loop identity and monotonic notification sequence are enforced.
A callback exception, callback-only CancelledError, async callback, replaced
channel, unqualified task factory or missing native retirement latches GAP.
The diagnostic callback never retries or unwinds native business work. This
failure isolation is not an execution safety/admission permission: a broken
observer must never be consumed as positive service health.

The existing-observer companion pins original binding/Task references, rejects
phase and identity gaps, bounds active records and completed diagnostics, and
removes Task/request references from completed diagnostic records. It does NOT
call NativeTaskObserver.publish/advance/retire_completed with manufactured
canonical ownership. Those producer-to-executor hooks remain a separate gate.

## Tests and their limits

Original native20/20 PASS and independent selected-source native20/20 PASS both
use actual native run handler/auth decorator/task-map lifecycle and real executor
threads. They overlap; do NOT sum as40 independent end-to-end cases. Agent/model
computation and authority/external delivery edges are explicit deterministic
doubles. No actual HTTP listener/middleware transport or network provider was
started. Native borrowed connect refusal is retained. Native callbacks and maps
were not published manually by these fixtures.

Independent cases additionally isolate callback CancelledError at acceptance and
retirement, missing bearer, JSON attempting activation, coroutine callback fault,
and native worker survival after the cancelled carrier Task has finished. All
current source imports were matched to committed native featured0028f6, including
both modified modules. The original patch applies to fresh immutable cc16 source
and yields exactly the tested raw bytes; repeated application is refused.

24 focused standard methods (12 consumer contracts with doubled native boundary,
12 offline receipts) pass on the combined tree. They are subsets of the ONE fresh
full standard run, not extra native executions. The terminal full result is added
below only after the ongoing source-frozen run finishes. No native upstream full
pytest suite or active-work Linux/isolation acceptance is inferred.

## Preserved failures and operating boundaries

Original H117 native001 failed on missing fixture bearer/audit fields. The native
auth implementation was not weakened; dummy request metadata was corrected and
the fresh run passed on unchanged product source. P117's earlier independent
draft, its cancellation regression and old native results remain historical
artifacts, not a second selected implementation or extra current coverage.
The first unit-source compile error and guarded source editing stops did not run
code under test. Windows CRLF receipt bytes are preserved exactly, not normalized
into different evidence; only that evidence directory declares their line endings.

The installed vendor remains eb75627 and the earlier borrowed featurecc16 is not
silently installed either. No source lock/gitlink, main, remote push, production,
account, CIqueue, WSL/root/mount or provider/model changes. Prior blocked independent
cleanup and early-source-check refinement remain BLOCKED, not retried by another
route. Native test-owned profiles/threads are cleaned by their own terminal QA.

## Exact next acceptance

Connect actual qualified canonical SessionAuthority executor/worker lifetime to
these native request bindings, including legitimate phase/retirement publication.
Borrowed mode's existing gateway_runner conflict is NOT bypassed here. Verify
active-work profile/mount/storage around capture and then real task lifecycle
under the same isolation boundary before active-work HTTP. Until then canonical
executor health, native listener/work routes, live-ledger/dummy-provider accounting,
fullD3B and cross-store atomic recovery/powerloss acceptance remain OPEN/CLOSED
as recorded in status.md. Notifications alone are not service readiness.

## Terminal full standard result

The ONE fresh combined Windows suite finished3092=3069PASS/23SKIP/0ERROR/0FAIL,
exit0, with474 source/config/test hashes and all3 staged patch hashes unchanged.
All467 prior sources remain identical.24 focused methods are12consumer contracts
plus12offline receipts, subsets of the full suite. Native20/20 and independent
native20/20 overlap and are not summed.80 original evidence Git blobs are intact.
Both native imports together cover504 source files with matching immutable-source
custody. Local static is recorded in static-final.txt, not remote CI. Runtime
activation and the canonical executor/active-work health boundary remain closed.

## Canonical delivery

Tested source `d0b150b3924da9dc7f103cb07fa438a93d3b83ca`, acceptance `7c4e5125920ec2548f536344c11974bd649a023f`; canonical `42b20e9956cff938976972ed1a7eddec6d47edff` fast-forwarded without history loss. All474 source files and3 patches match the full run.24/24 focused methods passed again at the canonical path. The accepted static check applies to identical executable sources; final delivery changes only documentation/evidence. Native featured0028f6 remains NOT INSTALLED, main/push unchanged. Canonical executor linkage, active-work storage/HTTP/isolation remain OPEN.
