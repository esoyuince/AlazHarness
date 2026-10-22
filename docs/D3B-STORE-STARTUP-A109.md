# A109 — one-shot product store startup under full canonical confinement

Base78b41d0. New gateway_store_startup.NativeStoreStartup composes the EXISTING
finite native layout, ProfileLease, P108E separate read-only helper, pinned native
SessionDB/RunIdempotencyStore, live-store gate and native runtime epoch operation.
No alternative helper, lock, projection or database implementation is introduced.
The external launcher supplies the actual held final-UID ProfileLease and trusted
prepared expectation; this class does not adopt/release somebody else's profile.

## Fixed call sequence

Create an object under the final actor and held lease. start() checks a finite
profile and exact prepared file identities, then runs the fixed read-only preflight
BEFORE writable constructors. Only after successful preflight are native factories
imported/called. The actual live connections must pass the existing live gate,
which refuses all pending/unknown admissions, workers and replay work. With that
clean-only prerequisite the pinned native begin_runtime_epoch advances exactly
one generation, then the same live gate verifies that exact generation again.
Only VERIFIED state exposes native store handles. No arbitrary callback/factory
or caller-selected executable exists in this product path.

The object sets stage BEFORE each possible effect. A failed or interrupted start
cannot be retried on the same object; epochMayHaveAdvanced is set BEFORE invoking
the native write, so a lost result is never claimed to mean no epoch effect.
No recover_session_inputs, automatic resend or task/provider dispatch occurs.
The gate may accept individually terminal records but does not reconcile their
cross-store meaning. VERIFIED is storage readiness, NOT HTTP/runtime admission.

close() refuses registered live writers/token writer and ACTIVE caller SQLite
transactions rather than implicitly rolling them back. It closes only returned,
owned replay/state objects, checks their primary connection handles actually
closed, and leaves the caller's profile lease held. Unknown constructor/close
effects prevent an automatic release/retry: the dedicated process must exit
under the supervisor's normal lifecycle. No destructor or implicit context
manager claims successful cleanup. The caller must still drain ALL tasks and
unregistered readers/writers; this is a cooperative process-bound lifecycle,
not isolation against malicious same-process code or an inventory of all readers.

## Real native003 experiment

The existing approved P71C disposable installation ran a new64MiB owned ext4
image using unchanged canonical network/mount/IPC isolation, host-UID reduction,
seccomp, Landlock and exact own-mountinfo permission. Fixed trusted test code at
/opt/alaz-a109 invoked the SAME product NativeStoreStartup.start/close in two
fresh final-exec processes. Actual native Hermes code remained pinned at
 eb75627faf532fa6ffbdae59a0d14b0b385fc780, with no mocked native constructors.

A separate seed process created fresh native schemas and trusted expectations,
then closed its connections/profile. First confined startup passed the product
chain and advanced epoch0->1. Explicit owned test work was recorded and settled
terminal. Native stores closed, profile released, process reaped, image unmounted
and loop detached before the second mount lifetime. Second startup passed the
same chain, advanced1->2, retained native IDs/inodes and rejected duplicate keys.

The second target then deliberately created one unfinished native admission,
closed its owned stores and tried a NEW product startup object under the still
held profile. It failed at LIVE_BEFORE_EPOCH, never advanced to epoch3, retained
the started row and refused a same-object retry. This is refusal, not a claim
that the system automatically recovered or reconciled unknown work.

Actual close attempts with an open SQLite transaction were rejected and left the
transaction/native handle usable. Normal close worked only after explicit QA
rollback. Separate native profile contender and supervisor checks confirmed that
profile/image ownership stays until its respective owner releases/exits. Host
TCP/abstract/sibling sockets, canary and private broker files remained unavailable
to confined targets; only the selected broker endpoint worked. Two authenticated
pings, zero physical provider attempts. Default/minimal layout and default mount
metadata denial remained effective in explicit negative cases.

42 parent controls plus31/36 child predicates are nested observations of two
mount lifetimes and an additional refused startup, NOT109 separate executions.
27 unit methods use explicit native/mount doubles (real SQLite handles only for
closure behavior). Five receipt methods check recorded native sources/results;
they are not new kernel runs. Full Windows execution is recorded independently.

## Failures and refinements retained

Native001 stopped before Gateway/storage startup: QA source transport omitted
existing packages/upstream/hermes Python slices needed by broker imports. The
read-only diagnostic identifies the missing file. Complete existing package
sources were added to the transport; no product validation was weakened. After
confirming no process/loop/fence remained, the failed owned install/image was
archived as -first; native002 then passed without product source changes.

Review subsequently found that close() would otherwise discard active caller
transactions. Two regressions failed on the original module and passed with the
explicit refusal. That old module and original native002 proof were retained;
a fresh native003 complete run tests the corrected product, including real
transaction-preservation checks. Native002 image/install remain as -second.
Current and prior images are retained unattached, not reformatted or reused.

All task runtime objects were audited gone after native003: no owned processes,
loop attachment, fence, cgroup, endpoint or projection anchor. Existing private
broker config/budget unchanged, parent mount table unchanged. The shared lab
was not stopped because parallel C109E work may use it. Default Ubuntu, CI queue,
production services/accounts and user repository-root changes were not modified.

## Integration and next boundary

A parallel C109E branch has a same-named but different startup implementation
without epoch advancement. It is NOT silently unioned or overwritten. Canonical
promotion requires an unchanged compatible head and explicit one-path choice;
a successful feature is not permission for a force merge. Preserve both histories.

This qualifies the storage component's real preflight->native opening->live
verification->clean-only epoch sequence under full canonical confinement, not
the complete Hermes HTTP Gateway. Broker live-ledger reads/provider send, request
readiness, paired atomic recovery and power-loss durability remain open. Legacy
IPCv2 gates remain closed. No production deployment, model call, main merge or
push is part of this work. Existing blocked R91F/G82C changes are untouched.

Evidence: evidence/d3b-store-startup-a109/. Exact full/static/commit pointers are
recorded after terminal completion; status.md stays short and prior status is
preserved byte-for-byte in docs/status-history/a109-parent.md.

## Final complete regression

Current fullWindows2694=2671PASS/23SKIP/0ERROR/0FAIL, exit0. All414 source hashes stable; all408 baseline files unchanged. Linux32/32PASS contains27 lifecycle unit methods and5 offline receipts; these are standard-suite subsets/platform repeats.23 old platform/explicit-opt-in Windows skips were not rerun here. Final native003 (not earlier002) pins current product and open-transaction refusal. Scope remains storage component, not HTTP/provider/complete D3B. Static result follows in static-final.txt.

## Canonical local delivery

Qualified code `ecea1419fd64e41ea3621048fea110bf851a86a0` fast-forwarded from `78b41d0a90b7abd311ee1d1f992cc65b605f073e` into `alaz/d3b-principal-launch-21oct`. All414 sources exactly match complete/native003 qualification; this delivery is documentation-only. Feature and C109E alternate branches retained, latter not merged or edited. No new native test, main publication or push. Current short status.md is the active continuation; delivery.json records provenance.
