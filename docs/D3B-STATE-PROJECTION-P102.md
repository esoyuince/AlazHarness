# Persistent profile inside G84E confinement — P102

Base: b0b673111b3cb793e70c2f2cb1f0951652a10fb0 (qualified S101).
Feature: alaz/d3b-state-projection-p102.
Status: actual scoped native projection PASS; full/static outcomes below are
reported only after their terminal receipts. NOT full D3B or Hermes admission.

## What is implemented

New gateway_state_projection.py composes the existing S101 volume authority
with G84E filesystem/network/IPC confinement. None of the367 prior source,
configuration, test or script files is modified. The original projection
still creates empty private tmpfs workspaces. The new explicit opt-in path
adds exactly one persistent subtree at /run/alaz-state/profile, not the whole
image and not an ambient host-writable directory.

VolumeBinding is a frozen trusted-supervisor input, never a network/model
capability. It pins the root-owned image identity, per-run crash-fence digest
and random token, cgroup device/inode, controller and mount-worker PID/start
pairs, live worker mount-namespace inode, loop number and profile inode.
Canonical paths, bounded integer types, root image ownership and overlap
rules are enforced before projection. The installed code and root supervisor
remain trusted; these checks are not a sandbox against malicious host root.

Read-only admission observes the actual root controller/worker, source
namespace, exactly worker plus current child in the protected cgroup, full
fence schema/hash, global sole matching loop device/inode/AUTOCLEAR, native
ext4 mount, rw/nosuid/nodev/noexec flags and private0700 Gateway-owned profile.
The prepared profile must contain exactly the two existing SQLite stores,
gateway.lock and optional known SQLite sidecars. Each is a same-device,
single-link0600 regular file. Nested source mounts or unrelated contents are
refused. This narrow current inventory is not yet the full Hermes profile
layout; future extensions require explicit qualification rather than a broad
recursive writable export.

A narrow Mounts subclass changes only the pre-pivot step: revalidate volume
and file metadata after namespace separation, bind only the profile subtree,
apply the restrictive per-mount flags, check inode/device/flags, then invoke
the existing pivot routine. The original network, broker socket selection,
UID/GID/capability drop, seccomp and ambient-FD cleanup mechanisms are reused.
Landlock receives one additional exact writable-profile rule; scratch remains
tmpfs, installed code stays read-only, and protected canaries remain denied.

The generic product callable expects an already registered/joined dedicated
root child. It is NOT a full production child-spawner or arbitrary dispatcher.
This task's fixed lab-only p102_projection_child.py demonstrates registration
BEFORE namespace access and a fixed isolated-Python exec after confinement.
Every failure terminates that child; no fallback or continued workload exists.
No mount/user/identity/IPC setting is activated just by adding this module.

## New native trial in the approved disposable lab

Only AlazHarness-D3B-P71C was used. New root-controlled code at /opt/alaz-p102,
new64MiB image/state under /srv/alaz-p102 and a new dedicated cgroup parent
/sys/fs/cgroup/alaz-p102. The initial lab marker, host IDs and absent Windows
mount exposure were checked. Existing accounts, services, original broker
config/budget and S101/G84E installations were not changed. No dependency was
installed. The three fixed broker scripts and their complete local Python
component import closure were copied with exact source hashes.

Native003 executed22/22 selected unit methods, then actual kernel operations.
The units use explicit privileged-boundary doubles; the following proof does
not mock mounts, final IDs, filters, SQLite, broker transport or process exit.
It is PASS_SCOPED_PERSISTENT_PROJECTION:32 parent predicates and26 conditions
in each of two real post-exec processes. These overlap; do not sum them as84
independent tests or Gateway launches.

1. A new root-supervised image is mounted privately. A separately registered
   seed process creates two synthetic SQLite stores and gateway.lock as the
   existing UID23001/GID23003. These are NOT native Hermes schemas.
2. Wrong profile inode is rejected by the product before projection. Wrong
   loop number is rejected even earlier by the fixed child's exact source-device
   guard. Its distinct error and empty anchor are recorded; this is not claimed
   as a separate product-inspector branch execution.
3. First confined post-exec process writes/commits the same synthetic key and
   value in both real databases. The process has four UID23001 and GID23003
   slots, empty supplemental groups, five zero capability sets, no_new_privs
   and inherited seccomp. Its network/mount/IPC namespaces are private and the
   initial host user namespace is preserved. Interpreter isolated mode is on.
4. Present protected canary read/write attempts get EACCES/EPERM. Host TCP,
   abstract socket, unrelated path socket and broker-sibling socket are denied;
   ordinary Gateway-UID positive controls connected BEFORE confinement, so dead
   listeners are not used as denial proof. Only the selected broker socket works.
   The actual native broker client completes a signed ping. No provider send.
5. Original volume source path, other image-root files, old host root, broker
   private files, foreign proc entries and cgroup control are hidden. A deliberately
   inherited high FD is closed. Private scratch writes and a local runtime
   socket work. Mountinfo remains denied by the UNCHANGED metadata policy.
6. While the confined child deliberately remains alive, S101 stop returns BUSY
   and retains its fence/image lease. After explicit child exit and reap, ordinary
   unmount, group/loop removal and lease-last teardown succeed.
7. A second independently created mount/confinement/exec cycle reopens the SAME
   image. Both rows and file inodes survive full detach/reattach. Primary-key
   duplicate inserts are refused, SQLite integrity_check says ok, and scratch
   has no previous-cycle marker. Again the live user blocks stop; cleanup follows
   its actual exit. The broker sees exactly two pings and zero physical attempts.

The kernel reused namespace IDs across sequential lifetimes. They were checked
against the live child each time; no cross-time namespace uniqueness is claimed.
Both database commits were separate SQLite transactions. Paired-store atomicity,
OS crash/power-cut durability, corruption/full-disk handling and real provider
accounting are NOT established by this trial.

## Preserved first failures and QA repairs

The first QA source authoring attempt failed compilation on a nested string
literal; no file was published and no native action ran from that attempt.
qa-authoring-correction.json records it. The snippet was rewritten without
nested newline escaping.

Native001 correctly refused before broker readiness: QA hashed a fixed command
for the new installation but invoked the old installed broker. Diagnosis
reported launch_command_mismatch. QA now computes and executes the command
from the SAME root-controlled install, with all three unchanged entry scripts.
No launcher hash check was weakened. Its cgroup audit also originally treated
kernel pseudo-files as nested scopes; the corrected audit checks child groups
AND the kernel populated flag independently.

Native002 then correctly failed on a missing local import helper under
packages/upstream/hermes/hermes_state_keys.py. The transport had copied only
packages/claw-hermes Python modules. It now includes the exact project component
helper closure and explicitly probes imports before creating an image. No
runtime fallback, fake module, old installation mutation or package install.

Both failed outputs and diagnostics remain native001/native002. Their code and
unmounted images were separately audited idle, then RENAMED to -attempt01 and
-attempt02, preserving original image hashes. Native003 used a NEW image and
installation. The new product projection module stayed unchanged throughout;
only QA setup/diagnostics were corrected. None of this edits/replays the blocked
R91F collector or the failed G82C branch.

## Cleanup and exact evidence

Current authoritative native records: native-003-result.json and
native-003-stdout.txt, with source manifest native-003-intent.json. The outer
receipt contains actual unit/native exit codes; nested nativeStdout contains
the32 observations, both26-condition child reports, IDs/inodes and bounded
claims. Four new offline receipt methods verify these records and five new
source hashes. They are included in the full suite, not four new native runs.

Independent final root READ-ONLY audit checked all three retained image
identities: no loop attachment, fence, live matching process, socket, cgroup,
nonempty parent mountpoint or anchor remained. Final installed source hashes
match the native manifest. Only the named P71C lab was terminated, exit0;
Ubuntu was only observed and never started/stopped by this task. UTF16 WSL
output is recorded reversibly with encoding, text, byte length and SHA256.
Three unattached64MiB images and code generations remain for inspection; no
previous image was reformatted or deleted. cleanup-final.json is authoritative.

## Still missing before Hermes admission

This is the first combined persistent-profile/confinement proof, NOT a complete
Hermes Gateway entrypoint. Native ProfileOwnership was not acquired and native
Hermes state/replay stores, recovery/epoch binding and provider dispatch were
not run. The test schemas and duplicate primary-key check are not Hermes
idempotency acceptance. Legacy IPCv2 remains closed and full D3B stays open.

The next concrete integration issue is already observed: existing
GatewayProfileLease calls the qualified mount observer, which reads
/proc/self/mountinfo, but final Landlock metadata rules intentionally deny that
file. Do not skip the observer or claim pre-exec JSON authorizes post-exec
admission. A narrow, explicitly reviewed self mount-metadata policy or a
properly bound alternative observation mechanism must be qualified, without
exposing foreign process metadata/FDs or broad /proc. Then reserve the real
native profile AFTER final exec/FD cleanup, verify actual native connections,
recovery/epoch and all required profile contents, and only then admit work.

The broker's live read-only Gateway ledger path is also not solved by ping:
this trial sends no provider request. Complete that path separately without
revealing broker-private credentials/budget or an ambient writable host tree.
A production fixed launcher must own cgroup registration/namespace access and
teardown, rather than expose this QA program as a general command interface.

Evidence directory: evidence/d3b-state-projection-p102/.
No push, main update, production service or paid model operation in this slice.

## Final current-source regression

Fresh complete Windows standard suite:2428 total /2405 PASS /23 SKIP /
0 failures /0 errors, actual command exit0. Direct unittest result objects,
not a text footer, provided these counts. All373 current source hashes are
identical before and after; all367 existing source files remain unchanged.
22 unit methods and4 offline receipt methods are subsets of this total.
The same22 unit methods separately passed in the actual P71C Linux trial.
The23 pre-existing skips are18 image-native and5 opt-in broker methods; this
task did not reexecute those groups and does not borrow old Linux counts.

Final45-file native transport exactly matches current source bytes. Both failed
native generations remain failed. The fresh third execution alone supports the
new32-predicate and two26-condition claims. Private original broker configuration
and budget remain unchanged; source/file/profile checks do not assert native
Hermes replay, physical media guarantees or production admission. The final
sequential local static result is in static-final.txt. No background test remains.

## Canonical local development delivery

Tested code commit `cef1cb20fcab605d7b97b8de944e3d96ba1071d9` was fast-forward promoted from b0b6731 to alaz/d3b-principal-launch-21oct. Canonical worktree: `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct`. Original feature branch and raw failed/successful generations are preserved. All373 tested source bytes match in primary. The subsequent delivery/static documentation commit does not change product or test source. No main update or push.
