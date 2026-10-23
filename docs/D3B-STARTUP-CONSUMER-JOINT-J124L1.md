# J124L1 - original storage owner with a prepared runtime consumer

The existing NativeStoreStartup is still the ONE owner of state/replay/response
connections. Its new explicit prepare_runtime(config,api_config) reserves one
consumer slot BEFORE imports, constructors or awaited effects. It never creates
a second store owner, learns a replacement epoch from candidate data, or enables
service. The native prepared runner/API borrows precisely those verified objects.

The original owner's close() itself now enforces the consumer guard. A convenience
wrapper cannot bypass it. RESERVED/CONSTRUCTING/ATTACHED/FAILED_UNKNOWN and
CLOSE_UNKNOWN consumers prevent all store-close effects. Preparation is one-shot.
Unknown outcomes cannot be retried or inferred clean from a cancelled coroutine.

The normal lifecycle is API detach -> runner detach -> original owner closes
response/replay/state -> external caller releases the profile. The consumer
never closes a caller store or releases that lease. Detachment revalidates after
awaited API cleanup and runner cleanup. Before the original owner closes, it
again checks real live SQL/epoch/storage and existing API/runner/authority work
inventories; a late task or new unsettled row cannot reuse an old detach receipt.
No forced cancellation, transaction rollback, recovery or replay is performed.

## What the experiments establish

Original S124B1 native20 and independent C124L1 native23 methods passed exact
same current product bytes. Both use real native constructors, epoch commit,
live SQL gates, runner/authority/API and three SQLite handles. Linux actor,
profile-lock metadata, permissions, mount/layout and isolated cold helper behavior
are EXPLICIT WINDOWS TEST DOUBLES. Therefore this is not Linux startup/confinement
acceptance and cannot activate a listener. Model/provider calls are absent.
The suites overlap and are not43 distinct scenarios. C124 original-gap control
uses additional live gate doubles and is explicitly labeled a baseline only.

The initial original20methods18PASS/2FAIL and independent clean5/5FAIL demonstrate
post-detach epoch/task/state gaps. Same QA assertions pass current helper. The
independent first run also had a separate optional-field/cleanup test-fixture
error, retained with logs and exact source; it is never counted as a product PASS.
All current temporary fixture profiles/tasks/ownership/registry cleanup passed.
Failing product consumers retain their failed state until dedicated fixture
teardown; fixture teardown is not a successful product detach/reconciliation.

A fixed513-native-file source envelope is checked before prepared constructors,
with loaded native imports verified within it.501 actual native import hashes
match immutable feature1e97. Installed native/source locks remaineb75627; storage
origin pins stay unchanged and are not re-labeled to this feature. Third-party
package trust and future agent/plugin imports are not proven by the envelope.

One existing runtime file changes; three historical receipt tests now verify
saved actual pre-consumer bytes. Old two-store/Linux proof is explicitly old
proof. New consumer, manifest, fixture and focused tests are additive. Original
S124B1 commit history and all original evidence Git blobs are preserved. Joint
full-source and patch manifests bind the freshly executed standard suite.

## Remaining acceptance boundary

The new Windows path confirms the original owner cannot close before safe
prepared detach. It does NOT complete actual Linux profile/mount/preopen/current
source integration, updated task observers, active-work admission or HTTP health.
Those must be tested on the SAME native feature/path before activating service.
Native API listener and ordinary runner guards remain closed. Full D3B, broker
live-ledger/dummy-provider dispatch and cross-store atomic/power-loss recovery
remain open; no separate scheduler/store/owner is added to address them.

C120P9 optional frame probe stays HOLD; previously blocked operations were not
retried by changing route/tool. No root/WSL/provider/model/main/push/remote CI or
production/account action. This joint handoff's summary/delivery records exact
terminal full/static counts, source hashes and canonical continuation.

## Historical baseline receipt migration

The first complete combined3212-method run retained one failing C119 baseline assertion: it assumed all483 historical source/test files would stay current forever. Four already-saved pre-consumer files are now checked against those exact executed snapshots; all other baseline bytes remain checked. Only that receipt test changed, no product/native source or raw old evidence. Focused28 methods then passed. A NEW complete final run is required and recorded separately; the first full failure is never overwritten or aggregated into PASS. There are now four historical receipt-file adaptations in total, plus the one modified runtime owner.

## Terminal complete regression

NEW final full3212=3189PASS/23SKIP/0ERROR/0FAIL exit0.522 source/config/test hashes and7 existing patch hashes remained exact. Same23 skipped test identities AND reasons as prior completed run; they were not executed as native acceptance. Of512 prior files,507 are unchanged,1runtime owner and4historical receipt bindings differ;10 source/test/config additions. Original20 and independent23 native scopes overlap, and8 owner contract tests/14offline receipts are standard subsets.36 original evidence Git blobs preserved. First full one-failure result and native pre-fix failures remain untouched. Local static is recorded separately; no installed/native/Linux/service activation.
