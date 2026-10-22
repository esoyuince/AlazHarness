# L106R — finite native-store profile and confined native restart

Base:7f17594b73c825d8e04873ab2db2a28fe49ab688.
Feature branch:alaz/d3b-native-layout-l106r. No main publication or push.
This implements the cold native-store profile slice, not full Gateway admission.
The complementary live-connection gate belongs to L106E and is not silently
counted as part of this feature's native execution.

## Explicit finite layout

New gateway_native_layout.py defines hermes-native-stores-cold-v1 for the
immutable Hermes source eb75627faf532fa6ffbdae59a0d14b0b385fc780. It includes
exactly the two SQLite databases, gateway.lock, the native quarantine/FTS locks,
SQLite sidecars when present, the pinned default SOUL.md, and the exact native
schema-cache data. The known home directories are explicitly named, including
logs/curator and cache. All leaf directories are EMPTY; cache may contain only
schema_columns.json. Arbitrary hooks/skills/cron/session payloads, plugin dirs,
config.yaml, auth.json, .env and unknown files are rejected. This deliberately
is NOT a general persistent Hermes home or an enablement of learned skills.

Directories must be0700, regular singleton files0600, with the expected UID,
GID and device. Symlinks/junctions, hard links, special files, changed metadata,
unknown entries and oversized data are rejected. Directory iteration rejects
unknown names before accumulating/sorting them; it cannot recursively walk an
arbitrary unbounded tree. Fixed shape bounds the number and depth of entries.

SOUL is667 bytes, SHA25636c1f5a2e92cd1d018311eaf4c8f1e8886672eae78212e033c681d0e3d5d506f.
The native schema-cache canonical JSON is SHA2568f4094e34ba4c09f2109fd04376c5f4a75597f31a8f9b7a75e527ce1ab87e114.
Both were derived from actual pinned native source/bootstrap, not guessed.
JSON whitespace/key order may differ; duplicate keys, nonfinite values and a
changed schema/tables mapping are refused. This checks the complete cached
reference rather than trusting a candidate's schema_hash field alone.

Only SOUL/cache content is read. No DB, SQLite sidecar or lock descriptor is
opened/closed, and no file is repaired, removed, chmodded or provisioned by
the layout observer. Auxiliary inode aliases of DB/lock/sidecar files refuse.
The inspector repeats metadata snapshots and checks opened auxiliary inodes.
It is still a snapshot under the trusted native lease/supervisor contract,
not protection against malicious host root or a concurrently mutable same-UID
profile. Existing mount/cgroup/nested-mount checks remain in the projection.

## Canonical opt-in; old defaults unchanged

gateway_state_projection.enter adds keyword-only profile_layout, defaulting to
minimal-v1. The old REQUIRED/ALLOWED set is not enlarged. Only the explicit
native-layout value switches the inventory check, and the selected mode is
rechecked before bind/pivot. Unknown/boolean modes refuse before kernel work.
The existing G84E UID/capability/seccomp/Landlock and S101 ownership/loop/cgroup
checks are unchanged. No additional /proc grant, host writable directory or
broker sibling socket becomes accessible. Legacy ipc_view v2 remains CLOSED.
The metadata permission is still the already qualified explicit own-mountinfo
opt-in; default false was separately rejected in this fresh native trial.

## Actual native002 acceptance

Only approved disposable AlazHarness-D3B-P71C, new owned /opt/alaz-l106r and
/srv/alaz-l106r resources were used. A new64MiB regular-file ext4 image was
prepared, not an existing disk. Root provisioning drops to Gateway UID23001 /
GID23003 for native profile bootstrap. Actual pinned ProfileOwnership,
SessionDB and RunIdempotencyStore create the legitimate schema/scaffold.
No dummy SQLite tables are used in this trial.

Two separate final-exec confined targets then ran with native ProfileLease:

1. Empty native state opened through actual native constructors. Native epoch1,
   session/admission queued->started and replay reservation committed.
2. After profile close, target reap, worker unmount and COMPLETE loop detach,
   another volume worker and isolated target reopen the same image. Epoch2,
   prior started admission->unknown, native duplicate request and replay keys
   reuse their ORIGINAL IDs; unknown claim and epoch1 write are refused.

Both DB row identities and inodes survive detach/remount. This is a normal
process shutdown with an intentionally unresolved admission, not a power-cut
or a new abrupt-crash trial. Existing H105E/N105D separately cover process
crash timing. No cross-database atomicity or automatic repair is inferred.

During an actual BEGIN IMMEDIATE native state transaction, the layout observer
opened only /run/alaz-state/profile/SOUL.md and cache/schema_columns.json. The
transaction remained active. This directly verifies no raw SQLite open/close
from this observer; it does not by itself prove all foreign writers are absent.
Native integrity checks passed, both constructors used file-backed connections,
then final inventory remained valid after close. Actual interpreter chose
DELETE journaling; its native warning was preserved, not hidden or overridden.

Real final UID/GID, empty groups/capabilities, inherited no_new_privs/seccomp,
private network/mount/IPC namespaces, preserved host user namespace and fixed
source/metadata boundaries are recorded. Two authenticated broker pings work;
physical provider attempts are zero. Unrelated live host endpoints and present
canary accesses fail, private config/budget and old host roots remain hidden.

Real native ownership contention fails while held, succeeds after native
release, but S101 still refuses to stop while the target PROCESS is alive.
Only after all users exit/reap and detach can the image lease release. Negative
wrong inode/loop, default minimal layout and default denied mountinfo were
also run. All42 parent predicates PASS; target write24/read27 conditions PASS.
These nested counts are not93 independent experiments.

## First failures and exact source custody

The first native run is retained as FAIL: detailed native-import provenance
exceeded the existing16KiB supervisor line bound. Cleanup terminated the owned
target and detached the volume; no success was claimed. Only QA framing changed:
max16 frames of max32 source pins, each<8KiB, with PID/index/count/digest checks.
The production supervisor limit and product module bytes were unchanged.
Native002 used a fresh image/source generation AFTER independently checking
old owned processes, loops, fence and socket were gone. The first image/source
were renamed to owned -first paths and retained byte-for-byte, not overwritten.

Windows tests uncovered two portability issues in auxiliary reads: DirEntry
stat's zero device/inode/nlink placeholders were replaced by full path lstat,
and optional O_BINARY preserves CRLF bytes under Windows CRT. Strict link,
owner, size and digest checks remain. Windows Path.stat/fstat ctime differ
following mutation; only Windows test fixtures simulate consistent POSIX ctime.
Linux fixtures execute real modes/UID/fstat without that shim. First failed
outputs and source-change explanations are retained.

The unfinished draft that preceded real scaffold discovery is archived but
never activated. L106E's initial alternate candidate is also only a historical
snapshot; final ownership is L106R layout/projection and L106E live-store gate.
No second runtime or denied R91F/G82C operation was introduced.

Historical F104X/Q104E projection receipts are explicitly bound to the original
7f17594 Git blob retained verbatim. Their guard source is still current. Old
native outcomes were not rewritten. NEW seven L106R receipt tests pin current
layout/projection/QA sources to native002, including actual imported native and
dependency hashes. Old success cannot stand in for changed-source acceptance.

## Tests and remaining boundary

Windows25 new layout tests and22 original projection methods PASS. Both groups
also passed in actual Linux as ordinary UID23001 (47 methods,0 skips). Seven
new offline receipt checks and the old historical-source proofs pass. These
are subsets of the new full suite, not extra native process lifetimes. The new
complete Windows/static result will be recorded only after terminal execution.

The lab transport consists of355 pinned files. The executed new source and
all package/native/dependency records remain unchanged during the native run.
Separate cleanup audit found no owned PID, loop, fence, cgroup, socket or mount
anchor. Both64MiB images remain unattached for inspection. Shared lab was not
terminated while complementary L106E worked; defaultUbuntu/accounts/services/
production/CI/main/remote were untouched. No paid model/provider send occurred.

IMPORTANT: finite layout does not establish database schema/identity before
native constructors, nor does it disable native automatic repair of unknown
existing files. This acceptance creates a fresh known profile and reopens it;
it does not authorize arbitrary candidate database adoption. The complementary
live gate operates AFTER constructors and must not be described as preflight.
A fixed complete startup still needs separately trusted prepared DB schema/
identity validation before constructors, then live-connection gate and explicit
partial-state reconciliation before HTTP acceptance. Actual full Hermes Gateway,
provider accounting, electric power loss and paired atomic recovery remain OPEN.

Evidence:evidence/d3b-native-layout-l106r/. Current continuation:status.md.

## Final full regression

New fullWindows2549=2526PASS/23SKIP/0ERROR/0FAIL exit0, 226.162s. All395 sources unchanged during execution. Of389 baseline files,386 unchanged; changed prior files are canonical projection and two historical-provenance tests. Six new code/test/QA files. New25 unit+7 receipt tests are subsets; Linux repeats25+22 methods without skips. The23 old platform/explicit-opt-in skips were not reexecuted in this task. Final local static gate is recorded separately; not GitHub CI.
