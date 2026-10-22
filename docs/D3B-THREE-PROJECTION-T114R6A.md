# T114R6A - full isolated three-store diagnostic readiness

This work reuses ONE NativeStoreStartup, ONE H114R6 StorageReadinessHttp and the
existing P102 projection. Default minimal and two-store selection is unchanged.
The new fixed profile selector is hermes-native-three-stores-cold-v1; it opts into
the existing finite response file inventory, not a broader writable host tree.
The HTTP extension belongs to H114R6. An early independent draft was discarded
from executable selection and retained as historical evidence, then the exact
H114R6 source7256a62 was used for every genuine trial. No duplicate listener.

## Current product boundary

response_ready=True explicitly selects three-store QUIESCENT diagnostics. The
configuration object, all three native handles and expectations are pinned;
response validation is bracketed by pair validation and followed by ownership/
handle checks. Any observed drift irreversibly revokes readiness. Process liveness
remains separate. HTTP drains before NativeStoreStartup attempts store close;
active response transactions retain all stores and the caller's profile lease.
Neither GET route authorizes agent work, retry or provider dispatch.

The new selector still exposes only /run/alaz-state/profile, with exact image,
profile and namespace ownership checks. Default layouts refuse the extra third
file. UID/GID/capability reduction, seccomp, Landlock and existing broker-only
socket projection remain the same. No new system-file or host-directory grants.

## Actual full-confinement execution

Native003 used one fresh64MiB ext4 image in the approved disposable P71C lab,
with a trusted root controller and final ordinary UID23001/GID23003. Two complete
mount/exec/unmount/loop-detach lifetimes run the SAME current three-store startup
and H114R6 HTTP after final exec. Nativefeaturecc16c10 is exported from immutable
Git for the fixture; the installed vendor/source lock is NOT changed.

Inside the private network, actual ready requests return200; while that same
process/port remains live the host connection gets ECONNREFUSED. Three native
store inodes and saved response content persist through detach/remount and the
clean epochs advance1->2. Profile exclusion, process lifetime and outer image
lease release are distinct and exercised in their existing order.

Only the RESPONSE database is changed by the deliberate fault fixture: an
application-id mismatch in the first lifetime, an unsettled key in the second.
Ready becomes503 even though the canonical epoch remains valid. Restoring each
fixture does not re-enable200. HTTP stops before the response transaction is
explicitly rolled back by the fixture, and all three connections close before
caller lease release. Native work remains closed; fixture data changes are not
an HTTP work route. Two authenticated broker pings and zero provider sends.

Native003 is terminal0 with45 parent predicates and58/63 target predicates,
22 HTTP observations in2 lifetimes. These nested counts are not166 independent
trials. All473 transported source files are
hash-locked in native-003-intent.json; exact counts come from that manifest.
279 native source files and139 installed pure dependency sources were verified.
Windows focused88 methods include18 independent third-store/projection cases;
10 offline native-receipt methods bind actual outcome fields, PID/port/event order,
source hashes and retention. These are not additional kernel trials.

## Failures and operational scope

Native001/002 failed before the target/volume path because the transported test
package omitted fixed launcher scripts, then immutable packages/upstream broker
helpers. Both are retained as FAIL, never attributed product success. Independent
post-failure observations were CLEAN and both images remain unattached. No product
or security rule changed to fix these fixture mistakes; native003 uses another
fresh path and complete original import closure, checked before new work.

Native003's own teardown records successful target/broker exits, loop/fence/
scopes absent, parent mount/private-file hashes unchanged and no forced cleanup.
The separately requested final Linux root cleanup query was BLOCKED by tool
safety. It was NOT reissued through another tool, encoding or path. Therefore
INDEPENDENT FINAL CLEANUP = BLOCKED, not CLEAN. Local receipt analysis and standard
regression may continue; no further root/native operation is attempted by this
work. This limitation stays explicit in status and the final handoff.

Earlier two-store/kernel proofs and L113 ordinary-user proof retain their own
executed snapshots. Their source-custody checks must not silently equate them
with newly changed projection/HTTP code. Native003 is the current-path evidence.
The earlier blocked L113 source-check relocation is untouched and not replayed.

## Remaining scope

No native Hermes APIServerAdapter listener or work/model route is activated.
Quiescent diagnostics does not define healthy/busy service for legitimate active
agent work. That ownership/observation policy and the broker live-ledger plus
dummy-provider accounting remain next. No automatic partial/unknown replay,
cross-store atomic recovery, physical power-loss guarantee or full D3B acceptance.
Legacy IPCv2 remains closed. Main/remote push/CI/production/defaultUbuntu unchanged.

The fresh full combined standard result, exact selected commit and canonical
continuation are recorded only after those gates finish. Prior source/evidence
histories are preserved; original installed Hermes remains pinned toeb75627.

## Raw receipt field scope clarification

The added response-store `duplicateRefused` field inherits the fixture marker from the genuine canonical/replay duplicate check. It is NOT an independently executed response-request deduplication check. Response evidence here is body/conversation/inode persistence, exact handle ownership, zero constructor row writes, fault revocation and safe close. No response request execution or cross-store atomicity is claimed from that marker; the raw historical result stays unchanged.

## Terminal combined standard regression

NEW fullWindows2973=2950PASS/23SKIP/0ERROR/0FAIL exit0.454 source/config/test hashes
and both native patch hashes stayed exact. The full run contains the independent
18 cases and10 current offline receipts as subsets, not extra native trials.
H114R6's source-identical current native experiment is retained through its
original commit;30 original evidence blobs remain unchanged. The installed
vendor/source lock was not promoted. Local static is recorded separately.

Acceptance is SCOPED BEHAVIOR+REGRESSION PASS with INDEPENDENT FINAL CLEANUP
BLOCKED. The native trial's own teardown checks passed, but the separate blocked
post-run query was not retried and has no CLEAN result. No ambiguity is hidden.

## Canonical delivery

Tested commit `6f1daf8c291b8deb59e557b3bebeb78e5ea62c90`, documentation-preserving merge `5d21b51f52cdf876faded6b08f0b67bba28d0a8b`, prior canonical `799e0220d19575f08c29716412e497a2231cbe6c` retained as ancestor and fast-forwarded. All454 source hashes and2 patches match the full run. Final handoff edits documentation/static receipt only; no additional native/root run, installed-feature activation, main merge or push. Independent final cleanup remains BLOCKED.
