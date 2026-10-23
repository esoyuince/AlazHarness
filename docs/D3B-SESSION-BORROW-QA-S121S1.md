# S121S1 - independent caller-owned SessionStore acceptance

Original C120A exact clean full3148=3125PASS/23SKIP and canonical delivery9418bf0
were verified before starting this work. No C120 test or blocked C120P9 physical
probe was replayed. The optional SessionStore implementation is owned by S121R4;
this branch supplies an independent default control, native behavior checks and
source custody, NOT a duplicate product, native hook or bootstrap.

## Default versus explicit caller ownership

A fresh real-native baseline at optional feature94321058 confirms the normal
SessionStore constructor opens one additional registry-managed connection even
when the caller already holds a separate SessionDB for that path. It intentionally
serves multiplexed profiles; this is not called an upstream bug. Its default
close releases its registry entry and leaves the independent caller DB usable.

The reviewed optional SessionStore(...,session_db=caller_state) instead borrows
the exact already-open non-registry native state for one fixed profile. The source
is copied byte-exact into an independent native worktree for tests; original
S121R4 files and installed vendor are not edited by this task. Configuration must
explicitly disable multiplexing and legacy JSON mirrors. No private _db assignment
after an eager constructor or deletion of borrowed_runner_conflict is accepted.

The candidate validates native state/path/file/application identity, live profile
handle, configuration and native mutex. Existing routes retain the same caller
connection without register/open/recovery. Foreign active scopes, explicit paths,
profile keys or changed state/configuration are refused. Closed state is not
reopened. Detach disables the facade, not the caller connection/profile; dirty
transcripts, in-flight entries and active DB transactions block detach without
rolling back or discarding them. Caller retains close/quiescence responsibility.

Legacy routing JSON import/write is refused in explicit borrowed mode. A real
query-only database fault exercises the original routing writer failure and
confirms no JSON fallback file is created. That MUTATION attempt uses the native
header validation read; it is not falsely counted as a zero-raw-open observation.
Normal constructor/selection/read-only routing-load/detach boundaries were watched
with zero SQLite connections, raw DB/JSON opens and SQL row changes.

## What ran

24 independent real-native cases PASS on Windows. Native SessionDB, SessionStore,
ProfileOwnership, locks, registry and SQLite are not replaced. Cases include
actual scope ContextVar switching, same-profile cross-thread selection, schema/
application-id changes, original locks/open transactions, absent schema/JSON
fallback, original profile release/reacquisition, configuration change and default
behavior. Explicit corruption occurs only in fresh fixture data and is restored
for fixture cleanup; it is not product repair or retry.

All24 profiles were removed and ownership released; registry generations/refcounts
returned to zero.250 actually imported native Python sources match immutable
94321058 Git or the exact three reviewed native file hashes. Seven offline receipt
checks verify these original results, current QA/source identities and scope;
they do not execute more native cases. The full harness standard suite remains
pending the source-identical original implementation and this QA union.

## First failures retained and corrected test scope

The first independent24-case run had21 PASS,2 FAIL,1 ERROR. It assumed that
sessions/ did not exist before SessionStore construction. A separate fresh-profile
experiment proves the native import itself prepares sessions/ before ownership
or state construction. Tests now compare exact entry inventory before/after the
facade and respect that preexisting folder. Product bytes did NOT change. The
original failing log, original QA and correction are retained, not relabelled.
The query-only write fixture separately permits the existing native read-only
header validation, while still forbidding new SQLite handles and any JSON open.

Native DELETE-mode fallback warnings remain in stderr. No interpreter/library
upgrade, package install or environment mutation was performed. These results
are not a claim of zero I/O in all native SessionDB mutation methods, malicious
same-process resistance, cross-file atomicity or universal quiescence under racing
external code. Selection is not a prepared-schema/mount/security capability.

## Remaining boundary

Only the SessionStore caller-owned state seam is under test. The complete
GatewayRunner/SessionAuthority/API three-store shared bootstrap is NOT accepted.
The existing borrowed_runner_conflict and disabled borrowed listener MUST remain.
No native source lock, installed feature, provider/model/listener/WSL/root/mount,
production/account/CIqueue/main/remote push action occurred. Earlier blocked cleanup
and requalification remain blocked and were not retried via another route.

Next preserve the original S121R4 commit/patch and verify exact hashes, then run
one complete combined standard suite. Subsequent work must define one real
caller-owned canonical bootstrap with existing readiness/profile/mount lifecycle,
not manually replace private state after opening or enable HTTP by bypassing a guard.
