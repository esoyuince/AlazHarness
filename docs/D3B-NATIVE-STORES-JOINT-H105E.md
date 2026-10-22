# Native-store recovery QA union — H105E / N105D

Qualified parents are recorded in evidence/d3b-store-joint-h105e/inputs.json.
This union changes NO existing product implementation, storage policy, native
Hermes file or model/provider path. It joins complementary actual-source QA
and preserves both independent commit histories and their original evidence.
The only merge conflict was status.md; both prior histories remain intact.

## What the two proofs establish

Both use immutable Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780, real SessionDB,
RunIdempotencyStore, native runtime epoch/admission transactions and native
profile ownership. They deliberately terminate OWNED subprocesses with exit73
without finalizers and reopen their temporary databases in new processes.
Unknown work is not automatically rerun. A failed disk open may fall back to
memory in native replay storage; such a store cannot be admitted as persistent.
This demonstrates a necessary admission guard, not its production wiring.

N105D supplies eight checkpoint scenarios on Windows and ordinary-user Linux,
including before reserve/COMMIT, queued input, started input, partial terminal
state, synchronized terminal state and old running replay records. The platform
repeat is not eight additional scenarios. H105E supplies six Linux crash/reopen
pairs with raw rows and exact source custody, including the complementary
replay-completed/state-started case and explicit volatile-state loss. Their
scenarios overlap: do not sum them into fourteen independent scenarios.

Actual native recovery advances the epoch and marks previous started admission
unknown, rather than synthesizing completion. Existing request IDs/keys retain
identity, conflicting payload/fingerprint is rejected, and stale-epoch writes
are fenced. A crash before native reservation COMMIT rolls back that INSERT.
Individually valid stores can still disagree across an interruption; neither
receipt grants authority to resend or claims two-store atomic recovery.

## Fresh file-policy compatibility, not full Gateway acceptance

H105E also ran a positive control and an ordinary-user final-exec process with
the unchanged canonical Landlock metadata policy. Both acquired the real native
ProfileLease, opened actual native stores and reached epoch1. The explicit own
mountinfo READ_FILE opt-in was sufficient for that fresh-open path; no broader
proc permission was added. The first QA canary overlap correctly failed and is
preserved; the corrected fixture NARROWED code grants and used new profiles.
These cases do not include the complete P102 mount/network/cgroup projection.

The native bootstrap creates additional profile directories, SOUL.md and native
state.db auxiliary lock files. That observed layout exceeds canonical30604df's
strict cold-projection file list. The mismatch is pinned as a historical
observation, not a test demanding that future code preserve it. No files were
silently removed or hidden and no permission/allowlist was broadened to force
acceptance. A single explicit prepared-native-profile and constructor-side-
effect contract remains the next actual implementation gate.

## Verification boundaries

H105E's32 and N105D's22 offline receipt/tamper test methods are part of the new
combined standard suite, not54 new native trials. Both raw native source pins
and per-process imports remain distinguishable from system dependencies.
Unchanged code snapshots are not relabelled as newly executed native proofs.
A NEW complete combined Windows run is required and recorded separately in
this directory. Separate parent full counts are not reused as a union PASS.

All382 baseline source/config/test/script files remain unchanged. Parent QA
source manifests match in the union. Original evidence blobs were compared
against both immutable parent Git trees and the merge index. No alternate
P102X runtime, old R91F provenance patch or G82C denied operation was replayed.

Linux work was restricted to the previously authorized disposable P71C lab,
ordinary UID23001/GID23003 and owned temporary files. No root, mount, account,
service, production, CI configuration, defaultUbuntu, provider or model action.
Own temporary code/profiles and subprocesses were audited absent. The shared
lab was not terminated by this task. This union performs no further native run.

## Exact next work

Prepare one reviewed native profile layout and fail-closed opening sequence:
existing files/schema/ownership and final native lease first; actual live SQLite
connections on the intended persistent mount next; reject memory fallback and
unknown/partial pairs before epoch/admission. Avoid running repairing native
constructors against unidentified existing state. Preserve legitimate SQLite
locks when observing files. Requalify actual detach/reopen under full canonical
confinement, then fixed Gateway HTTP admission and the broker's live-ledger
read/send path. Neither power loss nor paired atomic recovery is accepted here.

Main remains the published cc7ceba unless a later explicit publication task
changes it. No push in this QA integration. Legacy IPCv2 CLOSED/fullD3B OPEN.
Read status.md and delivery.json for the active canonical worktree and exact
local merge/receipt commits after successful full/static gates.

## Final joint regression

NEW fullWindows2517=2494PASS/23SKIP/0ERROR/0FAIL, exit0;389 source hashes identical before/after. The54 parent receipt methods are subsets, not extra native cases. All382 baseline sources unchanged.76 original parent evidence blobs exactly preserved in merge index. Final static output follows in static-final.txt; no native rerun was performed by the merge. Full run elapsedSeconds=165.377.
