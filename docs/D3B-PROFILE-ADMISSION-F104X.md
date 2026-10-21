# Native Hermes profile ownership inside canonical confinement — F104X

Base: `1207d37b5bb92bd107e5ec419cd3b4cac46d12f9`.
Feature: `alaz/d3b-profile-admission-f104x`.
Status: new actual native-profile slice qualified; final full/static outcomes
are recorded separately when terminal. Not full Hermes Gateway admission.

## One canonical projection path

This work keeps the qualified P102 gateway_state_projection implementation:
fixed `/run/alaz-state/profile`, strict profile inventory and S101 ownership,
root-controlled generation/cgroup checks, unchanged original G84E projection.
The P102X alternative is preserved, not merged as a second runtime. Its member
prototype is not silently substituted for canonical admission. No existing
image/profile ownership implementation, mount observer or upstream pin changed.

Only two product files change. credential_guard.apply has an explicit boolean
keyword `self_mount_metadata`, default False. It requires the existing true
self_process_metadata opt-in. The normal serialized policy rejects any new
permission field; callers cannot supply a metadata path or another PID.
When enabled, exactly one numeric `/proc/<launch-pid>/mountinfo` regular file
is opened O_PATH|O_CLOEXEC|O_NOFOLLOW and granted READ_FILE only using the same
existing Landlock metadata rule loop. The other five metadata files and all
filesystem handled bits stay unchanged. Metadata permits no WRITE_FILE,
EXECUTE, READ_DIR, foreign FD, memory or environment access. No broad /proc
allowance, fallback or kernel-policy disable was added. The digest explicitly
includes the extra option when enabled; the disabled path retains its old
digest. Descendants inherit the same policy; no new child-PID rule is granted.

Canonical gateway_state_projection.enter forwards this option only through
its new keyword observe_self_mount=True, after the existing projection, UID
drop, capability removal, seccomp and inherited-FD cleanup. Default invocation
still does not grant mountinfo. The existing legacy ipc_view v2 gate remains
closed. This is a trusted launch API, not permission derived from model JSON.

READ_FILE and READ_DIR are separate Landlock access types; mountinfo describes
the calling process's mount view. This narrow read removes the integration
blocker without authorizing changes to mounts or reading arbitrary host data.
References: official kernel userspace-api/landlock.html and filesystems/proc.html.
These references explain mechanisms, not native acceptance evidence.

## Real native-profile execution

Only the previously approved disposable AlazHarness-D3B-P71C was used. Owned
fixtures: /opt/alaz-f104x, /srv/alaz-f104x and /sys/fs/cgroup/alaz-f104x. A new
64MiB regular image was formatted, never a physical device or prior image.
The original broker private data and prior lab installations were preserved.

The new fixed final-exec target normally imports the pinned Hermes
`gateway.runtime_ownership.ProfileOwnership` and existing project ProfileLease.
No fake ownership class, native function patch or skip of the mount observer
is used in the actual run. Nine native source files came from no-replacement
Git blobs at eb75627faf532fa6ffbdae59a0d14b0b385fc780. Existing ruamel.yaml0.18.16
source files were hash-checked, copied only into the test installation, and
not installed/updated globally. Each final target records its own normal
module imports and exact hashes; executing children is not inferred from the
controller's module inventory.

Successful NEW native002: exit0,55/55 selected unit methods and41/41 parent
predicates. Two different final-exec target PIDs each passed38 overlapping
conditions. These counts are not117 independent Gateway runs.

- A disabled-option control cannot read mountinfo. The unchanged ProfileLease
  therefore refuses reservation without modifying the native lock record.
- Enabled targets run under actual UID23001/GID23003 with no supplementary
  groups/capabilities, no_new_privs/seccomp, distinct private namespaces and
  the original host user identity. They read only their own mountinfo, derive
  a constrained expected ext4/profile record tied to the projection's device,
  then call the unchanged mount observer and reserve native ownership AFTER
  exec and final descriptor cleanup. The resulting native PID record is the
  real final PID; its held lock descriptor is not inheritable.
- Before/after observation does not open or modify the two database contents.
  It verifies both stores/present sidecars on the selected bound profile.
- A real registered native writer thread is kept live. ProfileLease.finish
  refuses and retains ownership. The thread is a bounded Event waiter, not a
  claim that a full Hermes database writer was executed.
- A separate actual process, joined to the same image namespace as ordinary
  UID23001, attempts the real native lock. It exits77 with profile_already_owned
  and leaves the owner's record unchanged. After the target drains its thread
  and releases its profile, a new contender acquires/releases the same inode.
- The confined target deliberately stays alive after profile release. S101
  still refuses unmount and retains the image fence/lease until that process
  exits, the mount worker unmounts, the scope empties and the loop detaches.
- A second full image mount/exec repeats this lifecycle. Dummy SQLite rows and
  inode numbers persist; duplicate dummy primary-key writes are refused.
- Six explicit prohibited metadata opens return EACCES: mountinfo write,
  environment, memory, FD directory, mounts and limits reads. The controller's
  proc path is absent. Host sockets/TCP/abstract namespace, source image tree,
  private budget/config and inherited host FD remain inaccessible. Protected
  canary read/write is denied; allowed private runtime sockets still work.
- Two authenticated broker pings, zero physical provider attempts. The broker
  private config/budget hashes and parent mount table are unchanged.

The entry projection receipt correctly still says profileOwnershipAcquired=False:
that receipt precedes final exec. The NEW target observation separately says
nativeProfileLease=True after actual reserve. No old receipt was edited to
claim this later acquisition. The actual Hermes Gateway server, native Hermes
state/idempotency database schemas, epoch/recovery and provider ledger dispatch
are NOT tested. SQLite files here still contain the earlier owned dummy schema.

## First failure and source custody

Native001 failed before mount/target admission with broker_not_ready. A
read-only import diagnostic identified one missing transport dependency:
packages/upstream/hermes/hermes_state_keys.py. The root install checks passed,
but the broker's imported execution/recovery module needed that helper.
The QA transport was expanded to the existing reviewed Hermes helper files;
NO product source, permission or assertion changed to make the trial pass.

A read-only audit proved the first owned installation/image had no users,
loop, scope, fence, socket or mounted targets. They were renamed, not deleted
or reformatted, to /opt/alaz-f104x-first and /srv/alaz-f104x-first. Image hashes
were checked across the rename. Native002 uses a NEW image and full install.
Both original failed output and later successful output remain immutable.

The prior P102 receipt is explicitly historical for its changed projection
module. Original source bytes are retained and matched to the exact1207d37
Git blob. Its original receipt and assertions remain; its stale-current-source
failure is saved. The new F104X receipt separately checks current guard,
projection, adapters, QA and per-process native/dependency hashes.

New contract10 and receipt7 methods are part of the complete Windows suite.
The Linux55 selection is10 new contracts +22 existing projection contracts +23
existing ProfileLease methods. Privileged unit boundaries use doubles; actual
native lifecycle observations above are separate. Independent Q104E's12
syscall-rule/failure tests were read-only executed against its immutable
snapshot matching our exact guard hash. They verify READ_FILE=4, no permission
smuggling, protected-file collision, descriptor cleanup, failed opens/rules/
restrict calls, and distinct policy digests. That branch/test file was NOT
modified and these12 are not part of this feature's standard discovery count.

## Cleanup and remaining gate

A separate root read-only audit found no owned processes, loops, fences,
scopes, broker sockets or anchors for either image generation; mount targets
were empty. Both64MiB images and source generations remain unattached for
inspection. Default Ubuntu, existing accounts, packages, services, production,
other checkouts and CI configuration were not changed. Shared-lab disposition
is recorded separately after checking concurrent work; no global WSL shutdown.

This qualifies native profile ownership inside the final confined persistent
profile, NOT a complete fixed production admission orchestrator. It does not
open actual native stores, prove paired-store atomic recovery/power loss,
exercise real provider dispatch, or automatically recover stale crash fences.
The final production child admission path, native database connections/epoch/
recovery, broker read-only live Gateway ledger access and provider accounting
still need an end-to-end acceptance before real requests are admitted.
R91F/G82C blocked historical actions were untouched. Main/push not changed.
Legacy IPCv2 CLOSED, fullD3B OPEN.

Evidence: evidence/d3b-profile-admission-f104x/. Latest active pointer: status.md.
Full result and final exact source/commit/static delivery are appended only
after terminal confirmation, not reconstructed from passing subsets.

## Final complete regression

NEW full Windows run:2445 total =2422 PASS /23 SKIP /0 errors /0 failures,
exit0,270.270 seconds. Counts come from the unittest result object, not a text
footer parser. All378 source/config/script/test hashes are unchanged before
and after;370 old source files remain untouched. Prior changes are the two
explicit product opt-ins and one historical receipt test. Five new QA/test
sources added. Contract10 and offline receipt7 are subsets of full discovery.
The55 selected Linux methods passed; the23 old Windows skipped methods were
NOT reexecuted in this task. Native41/38 conditions overlap and are not a new
sum of standalone trials. Independent12 rule audits are separately selected,
not added to this branch's standard count. Its exact source hash matches ours.

No product source changed after successful native002. The first native broker
setup failure, first missing-keyword contract failures and old source-custody
assertion are retained. New actual receipts, not edited old results, support
the scoped claims. The staged static gate runs after this complete regression.
Main/push remain unchanged. Canonical development promotion, if still clean
and exactly at1207d37, is fast-forward only and recorded separately.
