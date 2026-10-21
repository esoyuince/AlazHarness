# State-volume supervisor — S101

Base: `0e170951b25de89dceae64b837997435b393243a`.
Feature: `alaz/d3b-volume-supervisor-s101`.
Status: actual mounted-volume and orphan-refusal slices PASS; complete standard
regression and final static gate are recorded separately after terminal results.
NOT a fixed Hermes Gateway entrypoint or complete D3B acceptance.

## New implementation, existing primitives preserved

New `packages/claw-hermes/state_volume_supervisor.py` controls an EXISTING,
preformatted ext4 image. It reuses ImagePin/acquire_image_lease unchanged.
No image creation/formatting occurs in the product API. Formatting belongs
only to the separately guarded QA fixture described below. The new fixed
`scripts/run_state_volume_worker.py` has no arbitrary argv/workload interface.
It mounts/holds/unmounts the selected filesystem, and never starts a Gateway.

The trusted caller must be Linux x86_64 host root, in the initial user-ID maps,
on its main controller thread. Installation, interpreter, image parent,
mountpoint and dedicated cgroup parent must be root-controlled. Rootless use,
user namespace remapping, alternate privileged helpers and fallbacks are absent.
The supervisor is not a security boundary against malicious host root or code
in its own trusted process. Its arguments are not network/model capabilities.

## Ordered lifecycle

1. Acquire the exact existing image inode's advisory lease. Inspect every
   present global loop device through LOOP_GET_STATUS64; device/inode identity,
   not backing-path text, determines an existing attachment. Unknown access or
   a changed inventory refuses. Only ENXIO means an unconfigured loop.
2. Before possible attach side effects, create a root-only, exclusive/no-follow
   `<image>.volume-owner.json` fence. Write and fsync the file AND parent directory.
   It records the exact image, controller PID, random scope and mountpoint.
   This is a locally held crash fence, not permission delivered to a workload.
   A stale fence is never auto-adopted, rewritten or deleted by begin().
3. Create a dedicated root-controlled cgroup-v2 scope. Confirm it is empty.
   Atomically configure one loop device using LOOP_CONFIGURE and AUTOCLEAR.
   Use a separately opened backing-file descriptor, NOT the flock-bearing
   descriptor: a kernel backing reference must not artificially keep the
   advisory controller flock alive after controller death. Validate the actual
   attached device/inode, flags, offset, size limit and sole matching loop.
4. Spawn only the fixed installed mount worker. It sets parent-death SIGKILL,
   rechecks its parent, joins the dedicated cgroup BEFORE mounting, and creates
   a private mount namespace with private propagation. It mounts ext4 with
   nosuid/nodev/noexec and errors=remount-ro. Readiness is bound to the actual
   Popen PID, token, live mount namespace, cgroup and configured loop number.
   The original parent namespace must NOT show the volume mount.
5. Normal stop refuses when any other live process or nested cgroup remains.
   Use ordinary umount only, never forced/lazy detach. An ambiguous stop/send
   result is not silently retried. A known BUSY response may be retried only
   explicitly after the owner has drained those users.
6. finish() first requires a reaped worker, empty recursive cgroup population,
   unchanged empty parent mountpoint and no unknown spawn effect. Close the
   controller's loop handle once; AUTOCLEAR may still be deferred by another
   namespace/user, so separately require the global image attachment to be gone.
   Recheck the cgroup and root fence, remove the empty scope, remove/fsync the
   fence, and release the IMAGE LEASE LAST. Failure never uses a generic finally
   unlock. Strong references keep uncertain objects/leases alive in-process.

There is no automatic crash recovery. A controller dying after preparation or
attachment leaves the fence. A freed flock alone does not permit reuse. An
operator must independently reconcile that exact generation's users/mounts/
attachments before authorizing recovery. A storage/fsync failure may require
manual inspection even after partial clean teardown. No retry/force-repair API
is provided. Fsync calls are checked, but power-loss durability was NOT tested.

All users must join the protected scope before receiving volume access. The
fixed mount worker has no production workload dispatch interface yet. A future
Gateway launch path must enforce membership, final UID and its full isolation;
the current QA's namespace join/drop is NOT that production admission path.

## Actual mounted-image acceptance in P71C

Only the previously approved disposable `AlazHarness-D3B-P71C` was started.
Guarded exact marker, distro, initial identity and absent Windows drive exposure.
New installation: `/opt/alaz-s101`; new fixture tree: `/srv/alaz-s101`.
New temporary cgroup parent: `/sys/fs/cgroup/alaz-s101`. No controller settings,
existing cgroups, accounts, packages, services, default Ubuntu or old P71C/G84E
state were modified. Code was copied from seven explicitly named/hash-verified
project files (six initially, one supplemental). No network/provider call.

The QA creates exactly one new private 64MiB regular file and formats that file
using existing trusted mke2fs. It does not format a physical device, a preexisting
image or any filesystem from earlier work. The image is deliberately retained
unattached for inspection. This is real ext4, not the old inert-byte fixtures.

First native run:27/27 unit methods in the lab and33/33 native predicates, exit0.
Privileged unit boundaries are doubles; the subsequent mounted proof is real.
The native proof performs three worker lifetimes:

- Mount once, write/commit two actual SQLite databases as UID23001/GID23003,
  using dummy owned tables, synchronous FULL and PERSIST journals. A separate
  live reader makes normal stop refuse; image lease and fence remain held.
- Drain that reader, ordinary unmount, reap helper, empty/remove scope, detach
  loop and release. Reopen the SAME image through a new helper/mount lifetime.
  Both rows and database inodes remain, SQLite integrity_check is ok, and
  duplicate primary-key inserts in both dummy stores are refused.
- Start a third helper and independent reader. Intentionally SIGKILL only
  that owned helper. Its surviving cgroup reader keeps the namespace/loop
  alive. finish() refuses, preserving lease/fence. After the reader exits and
  is reaped, finish verifies all users/attachment gone before release.
- A separate owner deliberately exits73 AFTER fsynced preparation but BEFORE
  attachment. The flock is available, but the retained fence refuses restart.
  The test then cleans only this proven-exited fixture through explicit QA,
  not an automatic product recovery path.

Second, separate supplemental run:19/19 native predicates, exit0. A real outer
controller starts the mount helper; the independent QA parent places a reader
in that scope and namespace as UID23001. The controller deliberately exits74.
PDEATHSIG ends its helper, but the reader stays live and the actual loop remains.
The advisory flock is now available; begin() still refuses the surviving loop.
After the final reader exits and the kernel clears the loop, begin() STILL
refuses the unchanged crash fence. Only then does explicit exact-fixture QA
cleanup remove the empty group and fence. No product auto-recovery was enabled.

These33 and19 predicates overlap and are not52 independent Gateway runs. The
controller and worker death scenarios are deliberate fixture crashes, not
power cuts or unclean OS shutdown. The image and SQLite schemas are synthetic;
no native Hermes store/epoch/replay engine, paired-transaction atomicity, live
provider request or durable actual Gateway admission was tested.

Mount namespace inode numbers were reused by the kernel between sequential
lifetimes. We verify each live helper against its actual current namespace and
parent; these numbers are not persistent identities and uniqueness across time
is not claimed. Controller generations use different fsynced random tokens.

## Evidence, cleanup and next work

Evidence directory: `evidence/d3b-volume-supervisor-s101/`.
Main trial: native-001-result.json + native-001-stdout.txt.
Supplement: orphan-001-result.json + orphan-001-stdout.txt.
Both contain exact child outcomes and source hashes; raw outputs are retained.
Four new offline receipt tests verify current sources, actual rows/inodes,
separate crash observations and terminal cleanup. They do not rerun Linux.

Final root read-only audit found no matching owned processes, image loops,
crash fence, cgroup parent or host-visible mount. Owned mountpoint directories
were empty. Installed source hashes were unchanged. Only the named P71C lab
was terminated afterward. Default Ubuntu was only observed; no start/stop was
issued to it. The unmounted64MiB image, root-controlled code and acceptance JSON
remain in the stopped disposable lab for inspection. No global WSL shutdown.

All360 preexisting source/config/test/script files are unchanged. New modules,
fixed worker and QA add no dependency. Historical failed R91F/G82C code/actions
are neither modified nor replayed. IPCv2 remains CLOSED and fullD3B OPEN.

Next: review/publish the bounded supervisor slice, then compose its actual
image namespace and root-controlled user registration with G84E confinement,
final-UID native profile ownership, qualified native database/epoch/recovery
and a fixed Hermes entrypoint BEFORE admitting requests. The present worker
alone has the host root view; private mounting is NOT full Gateway isolation.
Do not start real Hermes under this worker and call it the completed sandbox.

Kernel mechanism references (not acceptance evidence):
https://man7.org/linux/man-pages/man4/loop.4.html
https://docs.kernel.org/admin-guide/cgroup-v2.html

## STOP transport failure found and repaired before delivery

Review found that STOPPING was recorded after pipe write/flush. Either call
can fail after a partial transport effect, leaving RUNNING and allowing a
blind resend. Two new regression cases reproduced this (2 FAIL). The product
now records STOPPING BEFORE the first pipe effect. Both cases pass, assert
one write only, retain the lease/fence, and refuse another stop attempt.
No privileged policy, existing primitive, assertion or deadline was relaxed.

The initial27-case native unit run,33/19 native proofs and fullWindows2400
PASS remain immutable historical evidence for the pre-fix version. Native
current-source acceptance was run AGAIN after the fix: native-002 and
orphan-002 each exit0,29/29 units,33 main predicates and19 supplemental
predicates, all source hashes unchanged. These repeated predicates are not
additional unique scenarios. The final offline receipt now references these
new runs; it never rewrites an old PASS to describe changed code.

Before repeating, a read-only audit proved the original owned source/image
had no users, mounts, loops, scopes or fences. It was RENAMED, not deleted or
reformatted, to /opt/alaz-s101-original and /srv/alaz-s101-original. The first
image bytes/hash were preserved. A fresh /opt/alaz-s101 installation and NEW
/srv/alaz-s10164MiB image were created for the final tests. Both unattached
images and both code generations remain in the stopped test distro. Final
cleanup is cleanup-final.json, with no matching processes/loop/scope/fence
and unchanged final-source hashes. Default Ubuntu was not started/stopped.

The fixed worker's protocol currently bounds idle command waiting at120s.
It is a bounded prototype, not an indefinitely available service. This timeout
and error exits never authorize lease release: the parent still checks actual
worker termination, cgroup population, attachment identity and the fence.
A production supervisor/watchdog and actual Gateway command protocol remain
separate work; do not silently remove this bound to activate an agent.

Final current-source full regression is collected in full-final-windows-result.json
and full-final-sources-before/after.json. The original full2400 outcome remains
full-windows-result.json. A new complete run follows the source correction;
no composition of old subset results substitutes for that run.

## Final current-source regression

New full Windows standard execution:2402 total /2379 PASS /23 SKIP /0 failures /
0 errors, exit0. All367 source/config/test/script hashes are identical before
and after; all360 prior sources remain unchanged.29 focused methods and4 offline
receipt methods are subsets of the full total. Same29 methods ran on Linux.
The23 existing Windows skips were not reexecuted by this task; do not substitute
historical Linux79 for a fresh run. The actual33/19 mounted/orphan conditions
are separate overlapping observations, not52 standalone process lifetimes.

Final product/native sources match native002, orphan002 and cleanup-final.
The first2400 standard PASS, the two reproduced new STOP failure cases and all
first native results remain preserved. This final result follows the correction,
not an edited/reinterpreted earlier receipt. Native stop-pipe failure is tested
through an explicit transport double; the mounted tests exercise real kernel
state. Local static runs after the complete standard execution, independently.

## Canonical development delivery

Tested source/evidence commit `d9296de5e7180363c1487fcc627c51fbd09740d8` was fast-forwarded from0e17095 into `alaz/d3b-principal-launch-21oct`. Canonical path is `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct`. Feature branch/tree remains clean at that commit. All367 sources match final full/native proof. Local static feature PASS2402; following primary static verifies documentation-only delivery. No main/push or new runtime activation; R101 stays a separate feature.
