# Dedicated state-image controller lease — V98R

Status: actual Linux controller lease and fresh full Windows regression PASS.
Current controlling evidence: evidence/d3b-volume-lease-v98r/summary-final.json.
Branch: `alaz/d3b-volume-lease-v98r`.
Base: `bb30a99c7f6e02c5e054ba27451a55358c2348a1`.
This slice does not mount a volume or provide persistent Gateway admission.

## Persistence direction and why this primitive exists

Select a dedicated filesystem image as the next storage-domain candidate,
rather than exposing an ambient host-writable profile directory through G84E.
The two SQLite stores and their sidecars would reside together inside that
image. The existing G84E private tmpfs implementation is not modified or
pretended durable here; image attachment/projection remains unimplemented.

Before a trusted supervisor could attach an image, cooperating supervisors
need a single controller-side lease on the ORIGINAL image inode. The new
state_image_lease.py supplies only that missing ownership primitive. It reuses
Linux flock rather than inventing a database-backed lock or lockfile protocol.
The fixed pinned Hermes gateway/runtime_ownership.py already owns profile
writer exclusion through ProfileOwnership/gateway.lock. Do not replace or
hold a conflicting second profile lock around public Gateway startup.

## Implemented contract

ImagePin carries an explicit canonical image path, device/inode, aligned
bounded size, UID/GID and parent device/inode. It is local trusted supervisor
input, not a model/network capability. Linux-only acquisition requires the
current real/effective UID and GID to match the pin, a private0700 parent,
a private0600 regular single-link image and exact recorded identities.

The parent is opened once with O_DIRECTORY/O_NOFOLLOW/O_CLOEXEC; the image
is opened relative to that directory descriptor with O_RDWR/O_NOFOLLOW,
O_NONBLOCK and O_CLOEXEC. No O_CREAT, content read/write, truncation, chmod,
mount or repair happens. Missing or changed objects are rejected. Kernel
LOCK_EX|LOCK_NB gives immediate contention refusal. The same inode remains
on disk across acquisition, release and unexpected controller death.

Confirm rechecks both descriptors and path bindings, modes, owner, size,
controller identity and descriptor inheritance. A changed object is not
adopted or repaired. Close is idempotent and closes once, never unlinks the
image and never issues LOCK_UN. The module registers a child-only fork
cleanup: inherited copies close without unlocking the parent's shared open
file description. CLOEXEC prevents descriptors reaching a new executable.
The API is for one trusted controller thread; private descriptors must not
be manually closed or duplicated by callers.

## Deliberate limitations — do not convert these into stronger claims

flock is advisory on the tested local filesystem. It excludes cooperating
controllers using this same inode; it does not stop other permitted writers,
malicious same-UID code, host root, preexisting loop devices or other mounts.
Trusted ancestor control and current pinned identities remain prerequisites.
This module does NOT certify filesystem type, image format/content, storage
medium, exclusive profile writers, crash consistency or power-loss durability.
No fresh ext4 image was created: all test images are inert64KiB owned bytes.

A lease becoming available after controller death is NOT proof its old
Gateway/loop/mount is gone. Real integration must independently reconcile all
remaining volume users before reuse, and keep the outer supervisor lease
until users are stopped/reaped and attachment detached. Unknown effects
must refuse reattachment, not trigger blind retry. G84E closes ambient FDs;
therefore the lease belongs to the OUTER supervisor, never as an inherited
permission handed to the confined Gateway child.

## Actual execution

The26 selected test methods consist of8 cross-platform validation cases and
18 real Linux methods. Windows executes8 and explicitly skips18; those are
not reported as26 Windows successes. The approved disposable
AlazHarness-D3B-P71C distribution executed all26 with0 skips under existing
alazgateway UID23001/GID23003. No root, account, identity change, package,
format, mount, broker, Hermes Gateway or provider operation was performed.

The Linux tests exercise same-process independent opens and separate child
contention, successful acquisition after release, exception cleanup,
unexpected owner os._exit(73), actual os.fork and actual new-interpreter exec.
The forked child's close cannot release the parent lock. A child exec with
close_fds=False still cannot retain either pinned descriptor. Missing files,
wrong pins/modes, symlinks, hardlinks, replaced image/parent and changed size
are refused. Normal lease operations preserve original bytes and metadata;
negative mutations touch only the test-owned TemporaryDirectory fixtures.

Raw result linux-002-stdout.json includes every named test, direct unittest
result-object counts, before/after user/namespace observations, exact source
hashes, stable mount table, fixture/code cleanup and false stronger-acceptance
claims. Three separate offline receipt tests verify these records and current
source hashes; they do not rerun Linux or constitute three more live trials.

## Preserved harness errors and scoped cleanup

The first WSL invocation used -- rather than --exec. WSL invoked the test
account's intentionally nologin default shell and exited1 before Python/tests.
Original output and exit record remain linux-001*. The prior accepted N97K
command and local wsl --help confirmed the already-supported explicit process
form: --exec /usr/bin/python3.12. The new invocation uses that same user and
identical source, not a shell login, root, account/permission change or a tool
safety-denial reroute. This invocation succeeds; the original is not relabeled.

Owned temporary entries were absent in the final ordinary-user audit.
Only the named P71C distribution was terminated, exit0, and it was observed
Stopped. The final list independently showed default Ubuntu Running. This
task issued no Ubuntu launch/stop and does not know why its state changed.
The first cleanup wrapper wrongly asserted that unrelated Ubuntu stayed
Stopped; that assertion failed AFTER successful owned cleanup and P71C stop.
The unchanged raw list and separate cleanup-scope-review.json preserve this
fact. Never stop unrelated work merely to make a broad cleanup assertion pass.
No additional native execution was needed to resolve the scope mistake.
UTF16 list/termination output is retained reversibly as decoded text, encoding,
byte length and exact SHA256; no binary scan exemption is introduced.

## Sources, regression and protected work

All349 pre-existing package/script/test/config files are frozen. Only three
new source/test files are added: state_image_lease.py, its26-method test module,
and a3-method offline receipt module. Full Windows discovery therefore totals
2335. The full run includes18 added Linux-only skips plus the prior5 platform
skips; actual Linux26 execution is separate and must not be added to the full
Windows total as more unique methods. Counts come from unittest result objects.
Final source manifests and results are published only after the process exits.

Primary developmentbb30a99, maincc7ceba, vendor pin and unqualified R91F85f7470
are not modified. No blocked R91F collector/provenance correction or G82C edit
is replayed, merged or replaced. Prior failures remain on those branches.
No push, production activation or full D3B acceptance occurs in V98R.

## Exact next integration gate

1. Implement a bounded outer-supervisor volume lifecycle that excludes
   preexisting attachments/users, holds this lease outside the confined child,
   attaches the selected image exactly once to a private mount context and
   retains real persistent contents across fresh contexts. Never expose an
   unrelated host-writable tree. Failure or orphaned-users state must refuse.
2. Integrate native ProfileOwnership rather than reimplement its profile lock;
   prove the profile's actual open databases, expected mount and epoch/recovery
   before admission. R91F source-coverage correction remains separately blocked.
3. Only then qualify actual Hermes startup, acknowledged duplicate recovery,
   abrupt restart, storage-loss/full/permission behavior, paired-state recovery,
   broker-private data boundaries and a local dummy-provider send.

The present tests satisfy the controller lease primitive only. Neither a
filesystem label nor a successful exclusive flock makes steps1–3 complete.

Mechanism references (not substitutes for local evidence):
https://man7.org/linux/man-pages/man2/flock.2.html
https://docs.python.org/3/library/os.html
https://learn.microsoft.com/en-us/windows/wsl/basic-commands

## Terminal regression result

Fresh full Windows selection:2335 total /2312 PASS /23 SKIP /0 failures /0 errors,
actual command exit0. Of those skips,18 are the new Linux-native methods already
executed successfully in P71C, and5 are prior optional Linux broker IPC/HTTP
methods not rerun by this task. No test timeout or assertion was relaxed.
Linux selected26/26 PASS includes the same8 validation cases and18 native cases;
it is not another26 unique tests. Offline receipt3 is part of the full total.
All352 source hashes match before/after;349 preexisting sources are unchanged.
Final staged static scan follows this completed execution and is retained in
static-final.txt with its exact result; it does not replace the full suite.

The code remains a controller lease primitive, not a mounted-image supervisor.
No unpublished R91F code/test is included in this different passing selection.
Read local HEAD for the implementation/evidence commit. Main is not advanced.

## Final corrected-artifact qualification and concurrent work

First full execution PASS2335 with23 skips is retained. The following static
scan failed JSONDecodeError because initial WSL shell output was plain text
incorrectly named linux-001-stdout.json. It is now linux-001-stdout.txt with
identical raw bytes/hash. Only the offline receipt filename reference changed;
no assertion, native source or scanner rule was weakened. Original first
full/statics remain immutable, including the misleadingly named static-final.txt
which is the FIRST failure, not the final gate. static-after-format.txt PASS.

A NEW complete current-source execution after that filename correction passed:
2335 total /2312 PASS /23 SKIP /0 errors /0 failures, exit0,210.087s.
Authoritative current files are full-final-windows-result.json and its own
raw log/352-source before-after manifests. Linux product/test hashes remain
exactly those of the actual26/26 P71C trial. No additional native run is claimed.
The original summary.json is historical; summary-final.json controls delivery.
Final documentation-stage static outcome is static-qualified.txt.

During finalization the primary development branch independently advanced from
bb30a99 to f7f12ed (native profile lifecycle adapter L99D). A stale-ref guard
stopped BEFORE any commit/summary write. This task did not reset, merge or
modify that primary; its tests are not added to this branch's results.
The V98R implementation remains independently based on bb30a99. Compose the two
complementary leases only after separate review and a fresh combined regression.
Maincc7ceba and unresolved R91F85f7470 remain unchanged.

## Local commit

Tested implementation/evidence commit: `16946567c2e7d1a890c541637caa1b1c7a73f4e3`. Following documentation checkpoint retains identical352 source files. No push, main or concurrent-primary update.
