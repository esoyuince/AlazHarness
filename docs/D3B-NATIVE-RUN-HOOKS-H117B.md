# H117B - optional native run producer provenance

The installed Hermes/runtime pins remain unchanged. Native feature and patch
hashes are in config/hermes-run-hooks-h117b.json. This explicit two-file patch
extends featurecc16c10; it is NOT automatically installed by the earlier series.
One concrete harness consumer, gateway_native_run_provenance, accompanies the
existing actual Task observer. No second scheduler, executor, or store owner.

## What is now source-wired rather than supplied by a test producer

The actual decorated native /v1/runs entry computes its normal request scope and
fingerprint, reserves/replays its durable key, admits a canonical request where
available, creates its existing Task and registers that Task in its normal maps.
Only then does the optional notification channel publish CREATED. The native
execution functions publish STARTED, EXECUTION_RETURNED and RETIRED; DONE comes
from a real Task callback AFTER native background removal. Native request/body
validation and refusal/replay paths remain in place and produce no new acceptance
notification when no new run is created. Default no-channel behavior is retained.

The immutable binding captures the original scope/key/fingerprint and any original
canonical admission identifiers. Candidate database rows cannot redefine the
expected fingerprint. Neither request text nor bearer credentials are sent to
this diagnostic sink. It is explicitly installed in-process at quiescence, not
from user JSON, model output, environment settings or an HTTP endpoint.

The channel distinguishes executor_thread_carrier, canonical_authority_observer
and external_owner_observer. A native API Task often only watches execution
elsewhere. A carrier cancelled while its native executor thread still runs is
reported with task_done and worker_count separately. DONE is NOT a success or
executor-health statement; failure/cancel status remains visible.

Source/sequence/task/loop identity is preserved. Unknown eager/custom task factories,
pre-start cancellation without native retirement, replaced channels, reentrant
notifications and sink errors latch GAP. Notifications are synchronous and never
scheduled as new work. An async sink is rejected and its unstarted coroutine is
closed. Callback failure does NOT cancel, retry or undo the native business work.
This is deliberately a diagnostic channel, not an enforcement/admission gate.

The concrete consumer pins native binding/Task references, checks ordered events,
bounds active records to256 and completed diagnostics to32, and drops Task/request
references from completed diagnostic entries. Its public output always denies
canonical executor health, service readiness, runtime admission and store release.
It does NOT forge TaskRequest registrations or bypass the existing observer's
canonical execution requirements.

## Actual native execution and explicit doubles

20 Windows cases PASS against actual native APIServerAdapter, three native stores,
native decorated _handle_runs, replay reservation, actual Task creation/maps,
status publication, native retirement and done callbacks. No QA writes native
Task maps or manually emits producer events. Native bearer auth is exercised with
owned dummy credentials; invalid bearer is401 before any notification. The
network listener/middleware transport is NOT started or tested by these calls.

Model computation/agent construction and the authority/external-delivery boundaries
are explicit deterministic doubles. The original native _submit_api_worker still
creates a real executor thread. Thus worker-outliving-cancelled-carrier behavior
is real, but no agent/provider/model work or canonical SessionAuthority executor
health is claimed. Three execution-role labels are covered without treating
watchers as executors. The optional borrowed listener remains refused.

Cases include exact immutable ingress identity; original unobserved default;
replay without a second admission; conflict and malformed-key rejection;
unkeyed requests without invented fingerprint; callback exception/async sink;
duplicate/late attachment; channel replacement; cancellation before Task start;
actual worker survival after wrapper cancellation; native failure; role-specific
notifications; provenance consumer; and custom task-factory observation refusal.

12 consumer methods use real asyncio Tasks with explicitly doubled native publisher
boundaries. Six offline receipt methods bind the actual native logs/source hashes
and patch reproduction; they are not six new native trials. A fresh COMPLETE
standard run is pending the original-source union with P117 independent acceptance.
Focused/static/native success is not substituted for that full regression.

473 actually imported native source files were matched to immutable base Git blobs
except the two explicit patched files, whose hashes match the native execution.
The patch applies to a fresh immutable source export and reproduces those exact
bytes. A second application is rejected. Temporary export was removed. Only the
temporary Git apply command disables autocrlf; global configuration is untouched.
Native commit identity was supplied per-command from existing harness settings.

## Retained unsuccessful attempts and unchanged environment

First native001 ran17 cases and failed15 because the request fixture omitted its
owned dummy bearer and audit path fields. The actual native auth refusal was not
relaxed: the fixture was corrected, three explicit auth/cancellation/factory cases
were added, and all20 current cases passed with unchanged product sources. The
failed run and old QA source remain in evidence. Earlier source-edit guards and
one unit-source compile error stopped before existing source/test execution and
are recorded separately, not called tests. SQLite's existing DELETE fallback
warning and intentional dummy execution failure log remain in original stderr;
no environment/library upgrade was made.

P117N1 independently selected this EXACT native patch and consumer and supplies
separate QA rather than shipping its earlier duplicate draft. Preserve that
original history once terminal; overlapping scenarios must not be summed.
All467 previous harness source/config files are untouched. No WSL/root, prior
blocked-cleanup/refinement retry, provider/model, production/account, CIqueue,
main merge or remote push. Vendor main stays eb75627 and native borrowed feature
cc16 is used only as the source/test prerequisite, not the active installed pin.

## Remaining executor integration

This closes the native /v1/runs PROVENANCE NOTIFICATION subset only. Borrowed
adapter mode still rejects gateway_runner/SessionAuthority, and those actual
canonical executor hooks are NOT wired to NativeTaskObserver.publish/advance/
retire by this patch. No canonical admission is manufactured for a direct thread
carrier. The next gate must connect a real qualified canonical executor/worker
lifetime to these request bindings, verify active-work profile/mount/storage,
then test the same path under isolation before healthy/busy HTTP activation.
Existing cold/quiescent diagnostics, policy/reader/observer and listener refusal
remain unchanged. FullD3B, broker live-ledger/dummy-provider accounting and
cross-store atomic recovery/powerloss acceptance remain OPEN.
