# E118R1 - real queued-cancellation regression and independent worker lifetime tests

## Reproduced behavior, not a hypothetical bug

The original d0028f6 native _submit_api_worker increments _API_WORKER_LIVE before
submitting to the existing executor, but decrements only when its callable exits
or submission raises. Cancelling the asyncio Future can cancel a queued executor
job BEFORE that callable ever runs, so neither decrement path executes.

A real one-worker ThreadPoolExecutor held by another function reproduces:
initial0 -> native queued1 -> cancel -> drain ALL threads -> STILL1, with actual
work calls0. queued-cancel-before.json records this exact result. The same probe
against narrow source24165690 returns final0/calls0. The diagnostic count matters
for existing shutdown gates; it is not merely cosmetic or a model assertion.

The fix uses the EXISTING native lock to arbitrate queued/running/cancelled state.
Only cancellation that wins before callable entry releases queued ownership. If
_counted races behind that cancellation, it sees cancelled and never invokes the
business callable. After running starts, cancellation cannot decrement the count;
only the worker finally does so. Submission failure and completed-Future cancel
are tested; no underflow, second scheduling or replacement executor is introduced.
This fixes pre-start cancellation at the actual callable-entry boundary, not a
claim that Python can forcibly kill an already-running thread.

## One selected product, original native ancestry preserved

Counter-only native commit24165690b15f479f90f4bb7ac8751ae65c6f21fe is preserved as
an ancestor of selected943210584828ccfcfd6adc8eb966ecaa8ca18429. E118W2 owns the
source-level worker book and harness NativeWorkerObserver. This branch adds the
counter fix and independent real-native tests, not another book or scheduler.
The selected full patch includes the counter correction; the historical narrow
patch must NOT be applied as an extra activation step on top of it.

The selected native book binds submission and actual thread entry/exit to the
original immutable request binding. A source-owned ticket and actual thread IDs
are used; neither pending database records nor an observer's callback claims
prove a worker exists. Carrier DONE clears only its retained Task reference;
unfinished worker identity survives. The record disappears only after both source
worker exit and carrier release. Native worker thread callbacks do not invoke
arbitrary observer code. The bounded diagnostic book does not cancel or close work.

NativeWorkerObserver validates its native channel/book/provenance/process/store
owner and brackets the snapshot with source revision and global counter reads.
Transitions/races/contended locks yield unavailable, not a false idle observation.
Other unbound native workers are reported as unattributed; the public result
explicitly refuses all-agent completeness, canonical execution, service health,
admission/retry and store-release authority. Canonical SessionAuthority and
external-owner paths are NOT transformed into locally owned workers.

## Actually executed independent evidence

The exact selected native94321058 passed12 actual executor cancellation methods:
queued cancel, running cancel, real carrier cancellation, batch cancellation,
submission rejection, ordinary/exception/BaseException completion, duplicate
cancel and subsequent reuse. No worker function replacement or global count reset.
Every method ended with zero native worker count after its own executor drained.

The same selected source passed10 independent real native request/worker cases:
immutable ingress binding + real Python/native thread IDs; cancelled carrier with
surviving worker; queued carrier cancellation with zero computation; replay without
second worker; unbound other ingress; lock contention; PID/start identity change;
explicit observer fault without business-work cancellation; dummy compute failure;
and public data/authority limits. Native auth-decorated handler/task maps/submission/
worker finally/carrier release generate the records. QA never inserts/advances a
native worker ticket or task registry. Computation itself is a deterministic dummy.
Snapshot calls are watched for no new connections/raw DB opens or row changes.

Original E118W2 passed34 native methods (20 prior producer regressions +14 worker
cases). The independent12/10 overlap those and are NOT54 or56 unique scenarios.
The original counter-only12 run and old20 compatibility are historical precursor
proofs, not additional selected-current coverage. Seven offline receipts bind
these raw results and source bytes; they are not additional native executions.

All498 modules imported across the independent selected trials match immutable
native Git blobs, including the three changed native files. Current companion
and QA hashes are in selected-native-001-intent and selected-source-custody.json.
No environment/library upgrade or personal state access was performed. Native
SQLite DELETE-mode warnings remain in stderr rather than hidden or suppressed.

## Failure retained, not silently repaired

The first old-producer compatibility run on the narrow fix had19PASS/1ERROR: its
first handler hit the existing five-second test timeout. The native function,
old QA file and import hashes were left identical for ONE fresh retry;20/20 passed.
Both logs remain and this compatibility check is explicitly timing-flaky. The
first result is NOT rewritten as PASS or counted as a different test scenario.
Selected independent worker QA uses event handoffs and a15second bound; those
runs passed first time on the combined source without product relaxation.

## Runtime scope still closed

This qualifies real LOCAL worker lifetime/provenance, NOT canonical SessionAuthority
execution health, full active-work storage/profile/mount verification, Linux
isolation of the new source, healthy/busy HTTP or live provider dispatch. The
strict previous TaskObserver remains unchanged, rather than accepting a carrier
as a canonical owner. No invented canonical admissions or borrowed-runner bypass.

No native listener, model/provider, WSL/root/mount/defaultUbuntu, production,
account, CIqueue, main update or push. Installed native and source locks remain
unchanged. Earlier blocked cleanup/refinement operations were not reissued.

The source-qualified original E118W2 harness commit and this QA history will be
combined before ONE fresh complete standard suite. Scoped native/receipt success
is not reported as that future full regression or a running product acceptance.

## Original source integration

Original harness commit `15498974b6bd97074d11c07fd43e0b44ade980f4` was fast-forwarded before the independent QA commit; all executed companion/native bytes match. Selected27methods=14companion units+13offline receipts PASS, not a full-suite result. Next one combined full regression includes all current independent QA.
