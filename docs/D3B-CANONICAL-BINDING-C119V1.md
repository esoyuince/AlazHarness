# C119V1 - named API request to canonical SessionAuthority correlation

This additive companion uses the existing native RunLifecycleChannel and existing
SessionAuthority state. It does not introduce another scheduler, admission writer,
worker registry or alternate native execution path. Native feature94321058 stays
immutable and optional; installed Hermes remains eb75627. All483 existing harness
sources are unchanged. No existing borrowed gateway_runner restriction is relaxed.

## Selected scope

NativeCanonicalBinding attaches explicitly to a quiescent ordinary (NON-borrowed)
APIServerAdapter/SessionAuthority pair, on its current process/thread/event loop.
Five critical native source seams must match committed hashes before attachment.
Preparation/schema pins are supplied by a separate trusted provisioner; candidate
schema is never adopted as its own expected value. Existing schema/connection
inspection is reused on state and run-replay connections. This does not qualify
third-store/lease/mount ownership for the standard runtime.

The native producer supplies immutable run/scope/key/fingerprint/admission/session
identity. The companion stores those source observations, never reconstructing
expected identity from the candidate replay row. All later reads are bounded,
main-qualified, parameterized SELECT/PRAGMA against existing connections. State
and replay locks plus the native session-stream lock are acquired nonblocking.
Open transactions or contention remain unavailable; no commit/rollback/close.

A named request can be QUEUED, CLAIMED, or SETTLED. CLAIMED requires the native
started admission, current epoch/session generation, actual native execution stamp,
executing map and the live authority drain Task to agree. The task's coroutine/code,
self and route must be the native SessionAuthority._drain, not an arbitrary live
Task or the API observer waiting for the result. An adopted agent tuple is checked
against the claim generation, but that reference alone is not physical-worker
liveness or a full verified AIAgent construction/adoption callsite.

Cancellation of the API watcher is not cancellation of its canonical executor.
Its DONE source event drops the watcher reference while the named claim remains
observable. Only committed terminal canonical/replay rows and native carrier
retirement allow release_settled to delete this companion's diagnostic references.
No native task/map/row is removed or cancelled. No release of stores is authorized.

Expected transient gaps between execute return and settlement are UNAVAILABLE,
not a fabricated live execution and not automatic permanent corruption. Confirmed
identity/source/claim mismatch latches refusal. Restoring bad identity bytes does
not clear that latch. There is no dispatch/retry/recovery path in this module.

## Explicit limitations

This is a named identity/claim snapshot, never an all-work inventory or service
ready/healthy result. Every output denies admission, retry, store-release and
service readiness. Profile/mount validation, physical worker health and original
canonical payload-digest equivalence are explicitly not verified by this snapshot.
No HTTP wiring or NativeTaskObserver publication/ownership takeover is added.

The real standard native SessionStore opens its registry-owned state; it is NOT
pretended to be the caller-owned state path accepted by the existing borrowed
API bundle. These paths cannot be conflated. A future shared canonical bootstrap
must qualify their ownership/lifetime contract instead of temporarily removing
borrowed_runner_conflict or reassigning native handle fields for a passing test.

## Genuine validation design

Native smoke001 used real SessionStore, APIServerAdapter, authentication handler,
run producer, canonical API preparation/admission, FIFO claim, asyncio Tasks and
settlement. The API watcher and native drain were distinct. The runner facade and
model/message-handling boundary were deliberate doubles. The real adopt_agent
method was called at that doubled boundary, not the complete TurnRunner callsite.
No test manually inserted a happy-path admission/claim/Task/stamp. Deliberate
negative fixtures change fields/rows only after genuine native acceptance.

The first24 native cases PASS are retained with their actual source snapshots.
A review then found JSON 1e9999 was parsed as infinity despite rejecting literal
NaN/Infinity. A new failing regression demonstrated it; parse_float now rejects
nonfinite values too. Actual native-drain coroutine/route validation was added.
The current27-case run and final9 pure contracts must be separately recorded;
historical24 PASS is not attributed to changed code.

Control schema preparation occurs on a distinct fresh source-qualified profile
and closes before every candidate suite. Temporary candidate homes, registry
refs and process profile ownership are cleaned by the fixture. Connections and
raw DB opens are forbidden during observation; traced SQL is read-only and row
change counters are checked. Native imports are later matched to immutable Git.

The offline audit blocked one network attempt in first native run before any
network effect. It is recorded rather than called zero attempts; the current
fixture also records the source/target of any denied probe. There is no provider,
model or HTTP listener activation. Standard-library event-loop wakeup sockets
are permitted only during explicitly marked loop construction.

Prior blocked root-cleanup/source-refinement operations remain BLOCKED and are
not retried through another tool or route. This task runs no WSL/root/mount action.
No production, account, CIqueue, main or remote push changes are authorized here.

## Next acceptance boundary

The exact current native/standard test results and delivery commit will be added
only when terminal. Next work is actual TurnRunner/physical worker adoption and
canonical-request provenance in the shared caller-owned startup contract, followed
by active profile/mount/three-store isolation acceptance before HTTP health wiring.
This named correlation does not confer fullD3B, cross-store atomicity, or powerloss
safety and is not evidence of an installed running harness.

## Current native terminal proof

Native002 completed27/27 PASS on exact current code. All501 imported native Python files match immutable943Git. The source hash and schema control are retained in source-custody.json and native002 records. The denied network event is an import-time _has_ipv6 capability probe attempting to bind (::1,0); it was rejected before bind. There was no provider call. Nine pure contracts and six offline receipt methods passed15/15. They are not fifteen additional native scenarios. Complete standard regression is still running; only its own terminal result may qualify the full package.

## Terminal full standard result

New fullWindows3134=3111PASS/23SKIP/0ERROR/0FAIL. All487 source hashes and4existing patch hashes stable; all483 previous source files unchanged. Native00227 methods and9pure+6offline standard methods have distinct scope; subsets are not added together. The complete runner finished exit0. Static verification is recorded separately; no installed activation, main merge or push. Actual TurnRunner adoption, shared borrowed canonical ownership, active-work profile/mount/third-store isolation and HTTP remain open.

## Canonical delivery

Tested commit `68f1b833d633766a2a3c958572bcc7281243337e` fast-forwarded into alaz/d3b-principal-launch-21oct. All487 source and4patch hashes match; final15 selected methods passed again. Final handoff changes only documentation/evidence. Installed native remains eb75627; maincc7ceba/no push.
