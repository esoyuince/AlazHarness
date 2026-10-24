# I133P1 - canonical API publication in the original startup owner

## Published base and explicit selection

Previous publication is complete: remote/local main94f509d has exact-SHA
alaz/local-ci success. This focused branch starts at94f509d plus e073fc0
source-boundary checkpoint. Original/native source and ten staged patches are not
modified or installed. The dirty legacy root remains on its existing old branch.

NativeStoreStartup.prepare_runtime now has explicit canonical_api=False alongside
local_admission=False. Only local_admission=True,canonical_api=True selects native
5ff88189 with a separate fixed522-source manifest. Old1e97 prepared and1b7 local
admission envelopes stay byte-identical and exact; no fallback/upgrading/relabeling.
Invalid or unpaired options fail before reserving a consumer slot. Source and
import checks occur before native effects. The consumer slot remains reserved
before imports/constructors/await, preserving the original unknown-state rule.

This still uses ONE PreparedRuntimeConsumer, same original NativeStoreStartup,
three caller handles, original native authority and existing epoch. No alternate
scheduler, adapter resolver, session ledger or storage manager is introduced.

## Native publication and phase ownership

Preparation alone leaves native canonical publication NEW and admission PREPARED.
Explicit consumer.publish_api_adapter() delegates to the exact source-qualified
native bundle publication; it does not insert an adapter from harness code. The
native original registry contains only its exact enum-key/adapter entry. Consumers
track their own publication receipt, so direct native publication cannot silently
advance the owner's phase or authorize cleanup. Source, event loop, map object,
profile/config and exact native pair are checked; equal replacement maps are not
accepted. New-source admission requires the explicitly published registration.

Only this selected generation permits the exact owned API entry in idle work
checks. Old default behavior continues to require empty adapter registries. All
other tasks, queues, live worker records and obligations keep their existing
checks. ACTIVE identity observations do not grant health or store release.

API withdrawal occurs through its native successful cleanup. The consumer verifies
NEW or WITHDRAWN as appropriate before runner cleanup; post-detach checks retain
exact registry objects, native pair, accepted epoch and closed-wrapper identities.
Cancellation/late cleanup faults retain CLOSE_UNKNOWN and caller handles, not a
stale cleanup ticket. Direct owner close is refused until known final detachment.
No listener, automatic recovery, provider call or default status writer is started.

## Explicit native session retirement and one corrected uncertainty bug

consumer.retire_idle_api_sessions() is available only on selected canonical mode,
PUBLISHED registration and DRAINING admission. It first requires clean original
SQL gates, then invokes the existing native memory-only retirement operation.
It does not terminalize queued requests, clear worker obligations, erase history
or close stores. Active/queued/unknown work is retained and blocks retirement.

Initial complete native39 run had38PASS/1FAIL/0ERROR with cleanup completed. In the
failing case native retirement completed and returned its phase to DRAINING, then
an explicit unexpected post-effect exception was injected. The wrapper originally
looked only at phase change and left ATTACHED. Corrected wrapper treats unexpected
or post-return failures as ADMISSION_UNKNOWN even when phase appears unchanged;
only a native typed refusal before a receipt with unchanged phase is considered a
known refusal. Same39 test bodies then passed on corrected source. Original
helper bytes, failure log, source intents and results remain immutable.

## Actual acceptance and declared limits

Current native integration:39/39PASS, including23 inherited real-owner admission
contracts plus16 new source-selection/publication/API/retirement/fault cases.
Old local-admission1b7 selection:23/23PASS on CURRENT harness. Old prepared1e97
selection:20/20PASS on CURRENT harness. These overlap, not82 unique scenarios.
Twelve current standard tests comprise4 explicit selection contracts with declared
native preparation doubles and8 offline source/outcome receipts.

Native API calls are real admit_api_turn_async operations. The exact adapter and
authority resolve, an accepted queued request is recorded, exact retry retains
one row, changed payload refuses. Actual tasks/threads/SQLite and original startup
owner/consumer are used. The Windows fixture still explicitly doubles Linux
actor/lease metadata/mount/cold helper boundaries. Post-effect native-method and
memory-cleanup faults are named fixtures, not claimed unmodified full execution.

One end-to-end cleanup test uses real API admission but explicitly invokes native
leaf claim/settlement as a fixture, then native memory retirement, API withdrawal,
runner detach, caller store close and profile release. It proves cleanup and
history retention, NOT actual finite payload/TurnRunner/physical agent execution.
New watched observation/transition scopes perform0newSQL/rawDBopen/rowchanges;
API request writes occur outside them. No fake zero-write claim for API admission.

Loaded native514files in new39 match immutable5ff; compatibility514files match
1b7 and501match1e97. Manifest522files are verified from immutable Git blobs before
selection. Current executed harness bytes are bound in current-source-custody.
Native source files, installedvendor, tenpatches and global source locks unchanged.
Existing old runtime evidence is bound to exact saved pre-I133 bytes, not updated
expected hashes or relabelled as current acceptance. No earlier kernel run was
replayed. Raw logs preserve SQLite compatibility warnings and the original failure.

## Remaining work

Full standard/native/local/remote results are recorded separately in status and
summary. Full finite job execution, worker observation contract, current-source
Linux confinement and authenticated HTTP remain OPEN. Next drive a real accepted
request through native finite turn and physical worker with bounded compute and
native result/session/cache release; no test-settled row may substitute for that.
No new abstraction layer or private field assignment is required. Model budgeting,
recovery and M1/M2/product readiness remain separate gates. Prior blocked work was
not retried. Do not merge unverified source or equate old main's CI with this branch.

## Complete current standard regression

New full Windows3414=3391PASS/23SKIP/0ERROR/0FAIL, original command exit0.591source/config/test files and10patches identical before/after; same23skip IDs/reasons. Prior586files:581unchanged,3runtime and2historical receipt adapters changed;5new files. This full run includes12new standard contracts/receipts, not extra native or Linux executions. Native39/23/20 acceptance is separately recorded. RemoteCI not inferred from local result.
