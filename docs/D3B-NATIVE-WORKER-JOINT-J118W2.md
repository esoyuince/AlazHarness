# J118W2 - actual local worker ownership and cancellation accounting

This union contains the original E118W2 worker source and the independent E118R1
counter/correlation tests, with both histories preserved. Exact refs are in
inputs.json. There is one native worker book, one existing executor, one harness
companion. The feature is an optional native patch, not an installed upgrade.

## Concrete result

A native /v1/runs request now has source-generated immutable provenance linked
to the actual submitted callable, actual thread entry and function exit. The
carrier Task's DONE does not mean the callable stopped. While a cancelled
carrier's worker keeps running, its source-bound record and global native count
remain visible; the Task reference is dropped. The record is removed only after
both worker termination and native carrier release. Thread-pool threads can live
longer than invocations: these records name invocation lifetime, not pool shutdown.

The companion verifies the channel/provenance/process-start/loop/handle identity
and brackets book observations with source revision and native count. Changed or
contended observations are not a positive empty answer. Native workers outside
this request book are explicitly unattributed, never assumed absent or owned.
Metadata reads do not open databases, mutate rows, commit/rollback, cancel or
close. All service/canonical/admission/retry/store-release grants remain false.

## Fixed native bug

Original d002 queued cancellation leaked worker count: a real single-thread
executor was occupied, the second queued Future was cancelled, then all threads
finished. The callable ran zero times but the native count stayed at1.

The narrow fix guards queued/running/cancelled ownership transfer with the
existing native lock. A pre-entry cancellation can release only if the same
locked state prevents the callable entering afterward. Once running, only the
worker finally releases. Completed cancellation cannot release twice; submission
failure releases only its own still-queued reservation. No manual counter reset,
new executor, native Task-map mutation or assumption that cancel stops threads.
The independent original counter commit24165690 is an ancestor of native94321058.
The ancestry merge preserved the exact source tree used by the combined tests.

## Genuine test evidence and limits

E118W2 native34/34 passed:20 unchanged producer compatibility methods plus14 new
worker correlation cases. Native handler/auth decorator, scheduling, Tasks,
worker-count path, thread identities and three stores are real. The model
calculation is deterministic dummy work. Inherited authority/external delivery
boundaries and the dedicated submission-failure boundary are explicit doubles.
No manual worker record/ticket/counter/native Task-map publication by QA.

Independent E118R1 ran12 real counter-race tests and10 real request/worker tests
on EXACT same94321058 feature and companion. Coverage includes queued cancellation,
running cancellation, multiple cancellation races, repeated cancellation, actual
thread ID/request correlation, replay, unrelated global work and contention.
These packages overlap; they are not a single56-case execution. Native imports
from all three results were independently matched to committed Git blobs; exact
union count is in source-custody.json. Temporary native homes/ownership cleaned.
No native upstream full suite, new HTTP listener or Linux isolation trial here.

Current focused27 standard methods are14 boundary-doubled companion unit cases
and13 offline evidence checks. They are subsets of the complete standard suite,
not extra native cases. The complete selected-union suite is running with483
source/config/test files and4 patches frozen; its terminal result is recorded
separately, never inferred from focused PASS. All474 prior source files unchanged.

A counter-only compatibility run first had19PASS/1timeout on its first handler;
one unchanged fresh retry passed20/20. Both original records remain, explicitly
timing-flaky. The successful combined current34 did not require that retry.
An initial full-run command had a quoting SyntaxError BEFORE any command body
or tests ran; corrected command is the first actual complete run. Native Git
merge initially stopped on missing identity before effects; existing harness
identity supplied per-command only. No global/native Git user configuration edits.

## Source selection / no activation

config/hermes-worker-owner-e118w2.json selects native94321058 after prerequisite
d0028f6. The new patch ALREADY includes the queued-cancellation correction; do not
apply its historical counter-only patch as an extra prerequisite. Fresh patch
application reproduces the actual native bytes, a repeated apply is refused.
Installed vendor/gitlinks/source lock remain eb75627. Original source evidence
blobs and failure logs remain unchanged; root user work is untouched.

## Open boundary

Local worker/request invocation is now observed, but it is NOT a canonical
SessionAuthority claim, remote worker health or complete service readiness.
Existing NativeTaskObserver is not relaxed: canonical admissions are not invented
for thread carriers. Actual canonical claim/adoption must be linked separately,
then active-work profile/mount/storage validated and the same path tested under
isolation before active-work HTTP. The borrowed runner conflict stays enforced.

All work/listener/model activation, live-ledger/dummy-provider accounting and
fullD3B remain open/disabled as recorded in status.md. No cross-store atomicity or
power-loss claim. No main merge, push, CIqueue/production/account/provider/WSL/root
change. Historic blocked cleanup and source refinement are not retried or cleared.

## Terminal combined full standard result

ONE NEW full Windows3119=3096PASS/23SKIP/0ERROR/0FAIL, exit0.483 source/config/test
hashes and4 staged patch hashes stayed exact; ALL474 prior source files unchanged.
27 focused methods are14 unit contracts +13 offline receipts, subsets of full.
Native34 includes20 inherited+14 new; independent12/10 overlap and are not added.
505 actual native imports across current trials match943Git.62 original evidence
blobs are preserved. Local static-final.txt follows, not remote CI/runtime approval.
Canonical authority/active storage/HTTP/isolation and installed-feature gates remain
unchanged/open. Prior blocked cleanup remains BLOCKED and not retried.

## Canonical delivery

Tested source `c6b0fe66acc45aed06e88ff7924849685af26b35`, acceptance `09d2669b70225e9630b8e6f2e3fe49bec826df87`; canonical `250e218fe12883db320dbed02763d4fea8d6bce8` fast-forwarded preserving original histories. All483 source hashes and4patches match full run.27 selected methods passed again at canonical location. Accepted static applies to identical executable source; final edits docs/evidence only. Installed vendor remains `eb75627faf532fa6ffbdae59a0d14b0b385fc780`; native943 feature NOT installed, main/push unchanged. Canonical executor/storage/isolation/active-work HTTP remain open.
