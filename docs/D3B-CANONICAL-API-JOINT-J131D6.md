# J131D6 - native canonical API publication and exact request admission

One native implementation C131D6 plus independent Q131P1 qualification, preserving
both original histories. Optional feature5ff88189 changes6native files atop13186a5f;
the tenth patch is STAGED_NOT_INSTALLED. Existing579 harness source/config/test
files, current source envelopes, installed vendor and main remain unchanged.

## Missing adapter registration now explicit

Prepared API and runner already shared the exact three caller-owned connections,
authority and epoch, but the native resolver's primary adapter registry was empty.
The new bundle.publish_api_adapter() delegates to the EXISTING runner publication
method with explicit caller_bundle. It adds one Platform.API_SERVER entry to the
original registry, not another resolver, scheduler, admission table or store owner.

This is permitted only in qualified idle PREPARED state. Publication itself leaves
admission closed and schedules no API recovery, voice callback, listener or model.
Explicit activate_admission remains a separate step; late ACTIVE publication is
refused. Own-entry-aware native idle checks accept ONLY the identity-matching
published adapter and reject other work or entries; unpublished/default behavior
still requires the original empty map. Ordinary non-caller publication is unchanged.

Identity includes primary/secondary map objects, exact enum key, adapter/config,
primary owner profile and owner event loop. Equal copied map/string key is not the
same registration. Pure profile/publication checks fit the native transactional
admission guard without SQL or recursive mutex acquisition. Owner-loop checks
happen before activation and before awaited cleanup effects.

## Actual API calls, not a running HTTP or agent service

Real native admit_api_turn_async now resolves the exact adapter and authority,
binds the native API source, and creates a queued request. Exact retries retain
one admission identity. A changed body or different target with the same request
is rejected. This is genuine programmatic API admission, not a fabricated row or
stubbed resolver. It does not exercise HTTP authentication/listening or complete
finite payload/TurnRunner/AIAgent execution.

One test admits via that real API, then explicitly calls the guarded native leaf
claim/settlement functions, retires idle sessions and detaches. SQL dumps remain
unchanged across retirement/detach. That leaf settlement is a declared fixture;
it must NOT be reported as payload/model execution. Queued or unknown requests
still block drain completion and retain their data. No history is erased to make
shutdown look clean.

Publication persists while admitted obligations or an awaited cleanup remain.
Only after successful current work/SQL checks does native cleanup remove its exact
owned entry; runner detaches later, caller still owns all connections/profile.
Cancelled cleanup keeps CLOSE_UNKNOWN and the registration while physical cleanup
may continue. Trace faults after actual insertion/removal retain UNKNOWN and
ADMISSION_UNKNOWN/CLOSE_UNKNOWN rather than rolling back unknown effects. A stale
removal cannot delete a replacement foreign adapter. Registry removal does not
claim that cached source references are physically destroyed; sealed gates remain
authoritative for admission and release.

## Product corrections established by native regression

Initial48methods reported42PASS/6ERROR: real request-admission mutation callbacks
started the ordinary gateway_state.json background writer and raced profile
teardown in5cases; one test expected a later RuntimeStoreError but an earlier
BorrowedStoreRejected had already correctly refused identity drift. That assertion
was changed to accept either refusal, never success.

Four dedicated producer tests and two independent tests reproduced missing status
writer/profile/loop checks before the product fix. Native trace showed
track_mutation.finished -> persist_work_count -> _persist_active_agents ->
publish_runtime_status. Caller-owned runner now skips only the unqualified default
status FILE persistence in two helpers; native task/commit ownership still updates.
The ordinary runner's status file behavior is proven with a real ordinary runner.
Primary adapter/config identity and pre-effect loop checks were added. Original
failing bodies pass unchanged on fixed code; first outcomes remain in evidence.

The new ordinary control initially omitted its separate SessionStore cache sweep.
One registry ref leaked within that test process, producing a53-method failed run
and an outer temporary-directory cleanup error. The native close documentation
requires store sweep then runner wrappers; corrected fixture calls both actual
owners. No product edit, registry reset or ignored cleanup error. This historical
failed process/temp-root result remains failed; only the final fresh53profiles are
recorded cleaned. Existing SQLite fallback warnings also remain unmodified.

## Final native scope and provenance

Product native00453/53 PASS includes28prior admission contracts and25publication/
default writer tests. Independent native00321/21 PASS overlaps those tests; not74
unique scenarios. Native classes/methods are unchanged by tests. Real tasks,
threads, SQLite, runner/authority/API are used; cleanup-memory objects and trace
faults are explicit controlled fixtures. Watched pure transition regions have no
new SQLite/rawDBopen/rowwrite. Real API admission writes outside those regions are
expected, not hidden by a zero-write claim.

Actual imported native files from both final executions and current QA/fixture
hashes match the immutable feature and final patch. Fresh patch application
reproduces exact6bytesets; duplicate application refuses. Original evidence Git
blobs are preserved. New offline receipt tests bind hashes, raw outcomes, failures
and scope; they are subsets of the standard suite, not additional native runs.
Full native upstream pytest, Linux isolation and real model/provider are not run.

The read-only source reviewer completed and was archived. It recommended the
existing resolver, no recovery, exact owner and retained cleanup lifetime. Its
suggested post-ACTIVE timing was not blindly copied: this native design tests
PREPARED publication with precise own-entry-aware checks. Current harness source
manifests and empty-registry predicates remain unchanged, so harness integration
is explicitly not qualified by this native-only artifact.

## Remaining acceptance

Next qualify this exact native source generation in the SAME NativeStoreStartup
consumer and replace only its relevant own-entry checks. Then drive real accepted
API work through the native finite/TurnRunner/physical-worker path with bounded
computation and proper cache/session retirement; no direct test-only terminalization
may stand in for that result. After that, qualify the exact active path in Linux
isolation and HTTP. Existing blocked copy-sync/root/refinement/C120P9 actions are
not retried. Model accounting, powerloss/cross-store recovery and fullD3B remain
open. No global runtime upgrade, installed vendor/source-lock/main/push/remoteCI,
production/account, root/WSL/provider/listener change occurred.

The final summary/status/delivery records the one new combined full standard run,
local static gate and exact canonical commit. A test or evidence review never
authorizes native service activation.

## Terminal combined standard regression

One new full standard3395=3372PASS/23SKIP/0ERROR/0FAIL, requestc131d601...000027 exit0.584source/config/test files and10patch hashes unchanged. All579prior harness files untouched; five additions include original and independent QA/config/tests. The15new offline receipts are full-suite subsets. Same23skipIDs/reasons verified against priorJ130, not a Linux rerun.116original evidence Git blobs retained. This result does not execute native full upstream suite or enable any installed runtime.

## Canonical staged-artifact delivery

Tested `717cea096358a0fbe227b1409fde24b27638f268` fast-forwarded from `3bbabdc6bfb44c3498113f375c54065ea0d61ad9` into canonical development, preserving both original histories. All584 source/config/test hashes and10patches match full3395; current15offline receipts PASS. Native5ff88189 remains uninstalled; current harness envelope/consumer predicates and installedvendor/main unchanged. Final handoff modifies docs/static evidence only, no new native/full replay, remoteCI, push or service activation.
