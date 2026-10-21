# Gateway profile mount observation - M96Q

Status: focused observer tests PASS; runtime integration NOT RUN.
Branch: `alaz/d3b-storage-mounts-m96q`.
Base: `80d85488b02b3b8cb4023f41d666b043b356e9a6`.

## Narrow implementation

`packages/claw-hermes/gateway_storage_mounts.py` adds a read-only Linux mount
observer for an existing profile. Both `state.db` and `runs_idempotency.db`
are mandatory; existing -wal, -shm and -journal sidecars are included. It
never opens database contents or SQLite connections, creates a database,
changes a journal/permission/mount/namespace/identity, or runs a subprocess.
Existing launch, projection and replay backing implementations are unchanged.

The observer matches an explicit per-run trusted expectation: mount ID,
major/minor device, mount root, mountpoint and filesystem type. It corroborates
mount devices with lstat, distinguishes path components, and rejects stacked
relevant mounts rather than guessing visibility. Both per-mount and superblock
read-only flags are checked. Unexpected per-file or sidecar binds are refused
even on the same device. Missing stores, links, special files, changing paths,
sidecars, mount table or namespace refuse rather than authorize a retry.

The parser is bounded, handles the four documented path escapes once, and
ignores unknown optional mountinfo tags. Existing tree-inspection code checks
special files and mount traversal but provides no filesystem-medium record;
that code is left intact, not reimplemented or made less strict here.

Actual tmpfs/ramfs/rootfs are refused. Only configured ext4/xfs/btrfs labels
are currently in scope; overlay/network/other types are UNQUALIFIED, not
claimed universally volatile. Read-only checks do not establish write access.

## What a successful result does NOT mean

`CONFIGURED_MOUNT_OBSERVED` is a snapshot, NOT durability or launch authority.
A filesystem label may itself have RAM, loop, VM or unflushed storage beneath
it. A reused mount ID, an ABA race, the open SQLite connection's inode,
exclusive-writer ownership, paired-store consistency and power-loss semantics
are NOT proved. The result explicitly leaves these stronger claims false.
Do not accept arbitrary model/network JSON as an ExpectedMount. The trusted
supervisor's backing-medium validation and recovery lifecycle remain separate.

The helper is NOT connected to Gateway startup. It does not make G84E's
private tmpfs persistent, bind a writable host directory, open IPC v2, or
repair/replace R91F's blocked collector. Full D3B remains open.

## Executed checks

- Windows:30/30 focused unit methods PASS, no skips; Linux mountinfo/namespace
  and device observations are synthetic while file metadata uses real fresh
  temporary files. Source SHA values match the Linux copies exactly.
- ChatGPT ANALYSIS CONTAINER, NOT user WSL: the same30 methods PASS under
  ordinary UID1000, no skips. These remain fixture tests, not30 actual mounts.
- In that same analysis container, two additional actual mount observations
  used freshly created dummy regular files. Actual tmpfs produced
  storage_volatile_filesystem; actual overlay produced
  storage_filesystem_unqualified. Both fixture directories were removed,
  their bytes unchanged, mount table/namespace and user identity unchanged.
  No mount/provisioning/privilege operation or real SQLite/Gateway run occurred.
- No positive real ext4/xfs/btrfs observer run is claimed. A user Linux lab run
  and Gateway admission integration remain NOT RUN. These observations cannot
  be substituted for the user's P71C or G84E acceptance.
- Full standard Windows regression was NOT run by this slice. The base's
  previous2273-test result is historical and not a synthetic combined result.
  The new30 cases are ordinary test discovery members, not an additional claim
  that all2303 tests executed. Local static result is recorded separately.

Evidence `evidence/d3b-storage-mounts-m96q/`: exact source hashes, Windows log,
analysis-container JSON/raw log and initial baseline. Imported container files
were matched byte-for-byte to their original SHA256 before writing here.
All345 preexisting package/script/test/config sources remain unchanged.

## Concurrent work and continuation

Primary I95P independently integrated the exporter fix while this slice ran;
we only observed that work, not its author/test runner. R91F remains85f7470
with its failed full suite and blocked provenance correction. R92S's separate
reviewer is also concurrent and untouched. No reclassification, deleted test,
substitute native proof or rerouting of a denied operation occurred here.

Next integration gate: obtain the trusted persistent-medium contract and
observe both live stores/sidecars in the intended Linux runtime; then join
that observation to verified database backing, exclusive lifecycle and the
actual fixed Gateway entrypoint BEFORE exposing admission. Do not loosen the
current mount/projection policies just to make an observed label match.
This independent source commit requires combined regression before promotion.
No main update, push, model/provider call, user WSL start or production action.

## Mechanism references (not test evidence)

Linux man-pages proc_pid_mountinfo(5):
https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html
Linux kernel tmpfs documentation:
https://docs.kernel.org/filesystems/tmpfs.html

## Final local gate

Local static PASS,2303 discovered, runtime_tested=false. This is not2303 executed tests. Final347 source hashes retained;345 existing sources unchanged. Container probe source is preserved verbatim in analysis-container-check.py.txt, SHA2565bf7bf2ec704951a2cea485cc52b66648d328635ca73a396b4531d8b7556022b. The fixture cleanup is confined to its own TemporaryDirectory instances. No pending own commands or user lab actions. Read Git HEAD for the local scoped implementation checkpoint.
