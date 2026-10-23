# C124L1 - independent original-owner and prepared-consumer acceptance

S124B1 owns the SINGLE gateway_store_startup integration and prepared-consumer
module. This work independently validates its original-close gap and corrected
native behavior, preserving the original implementation history. It does not
add a second startup/storage owner, native feature or consumer selector.

## Reproduced original boundary and current proof

A fresh fixture with the ORIGINAL startup source and real1e97 stores/runner/API
confirms that direct owner.close could close all three connections while API
remained ATTACHED and runner remained PREPARED. That old storage owner had no
consumer relation; it is an integration gap, not an upstream default bug. The
control has explicit Windows doubles for Linux actor/lease/layout/cold/live gate
boundaries. Old source bytes and actual native-import hashes remain recorded.

The current independent23-case suite uses the ORIGINAL selected implementation
and actual NativeStoreStartup construction, three native databases, epoch commit,
real live SQL validation, actual runner/authority/API preparation and native close.
Only Linux actor/lease/mount/layout/permission and cold-helper boundaries are
explicit fixture doubles. The prepared consumer source envelope is fixed to513
native files;501 actual imports independently match immutable1e97 Git bytes.
No new native source changes or installed-runtime promotion is involved.

Successful preparation retains exact three objects/connections and the accepted
epoch. Direct original owner close refuses before any database closes. Consumer
API detach must finish before runner detach; both complete before owner closes
response/replay/state. The external native profile reservation is still retained
until the caller separately releases it. Known pre-effect transaction/task
refusals are re-observable; the code does not roll back or cancel their owners.

Actual cancellation while native API cleanup is awaiting a fixture-controlled
empty memory cleanup leaves CLOSE_UNKNOWN. Cancellation after real authority
initialization but before preparation returns leaves FAILED_UNKNOWN. The source
owner still refuses close and no automatic retry happens. These two cases use
explicit pause/fault boundaries, not alternate normal constructors or a fake
positive native lifecycle. Dedicated fixture teardown is not product recovery.

## Independent before/after defect proof

Five negative cases on the old candidate all failed with clean fixture teardown:
committed epoch drift, new runner task, new authority mutation task, unsettled
response identity, and changed response application id after detach. The same
QA file (byte-identical) passes all five in the current23-case suite. The sole
implementation owner fixed its final store-close guard by repeating existing SQL
checks and checking existing runner/authority inventories immediately before
close. This task did not weaken assertions or modify parallel product files.

The first23-method independent attempt also contained a fixture bug: it assumed
an optional _mutation_tasks attribute existed, created a Task before that access
failed, and an early teardown assertion skipped DB cleanup. Its10failure/1error
log and stderr are retained; it did NOT produce a JSON PASS or successful cleanup.
The fixture now reads the optional attribute before task creation and always
cleans its own dedicated resources even on assertions. After the failed child
terminated, only its exact owned temporary root was removed; no user profile or
unrelated path was touched. A clean five-failure reproduction separates the
actual product issue from that test harness failure. Current23/23 cleanup passed.

## Nonclaims and remaining work

Seven offline receipt tests bind the current QA/product/raw observations and
preserved failures. They are not seven new native executions. Original20 and
independent23 native suites overlap and cannot be summed as43unique scenarios.
Full combined harness regression is separately recorded in joint J124L1 evidence.
Previous native/Linux source-pinned receipts remain historical; they are not
relabeled proof of this changed startup path. Static checks are not remote CI.

This is prepared-only ownership under Windows test boundary doubles. Real Linux
cold helpers, metadata permissions, mounts, confinement and active-work readiness
are NOT accepted by these tests. Current-source task observers/admission remain
open. Ordinary native API listener and runner-service guards stay closed; no
provider/model/production/root/WSL/main/push/CIqueue action. Earlier blocked actions
and C120P9 HOLD remain unchanged. The513 file envelope covers this known prepared
native Python path, not future dynamic agents/plugins, third-party dependencies
or hostile in-process source/handle replacement. No cross-store atomicity or
power-loss guarantee is claimed.

## Historical baseline receipt migration

The first complete combined3212-method run retained one failing C119 baseline assertion: it assumed all483 historical source/test files would stay current forever. Four already-saved pre-consumer files are now checked against those exact executed snapshots; all other baseline bytes remain checked. Only that receipt test changed, no product/native source or raw old evidence. Focused28 methods then passed. A NEW complete final run is required and recorded separately; the first full failure is never overwritten or aggregated into PASS. There are now four historical receipt-file adaptations in total, plus the one modified runtime owner.
