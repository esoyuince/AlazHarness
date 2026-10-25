# P142C6 - Retained profile views across the existing projection boundary

## Scope and decision

Adds one explicit retained-layout option to the existing supervised volume
projection. It connects the saved retained-profile contract to a host-side mounted
profile and the fixed in-sandbox /run/alaz-state/profile without modifying the
original receipt, creating a second store owner, or broadening four old layouts.
The current package is a tested Python integration contract, NOT a new kernel
confinement, active finite-work, HTTP or real-model acceptance.

Main1321699 remains the prior CI-qualified baseline. Installed Hermes eb75627,
optional native d151, all source manifests and eleven native patches are unchanged.
No root, WSL runtime, mount, namespace, policy/permission, service, network provider
or main/push action was performed for this code change. Existing root user edits
must remain byte-exact. Source-in-code permission comments never authorize a run.

## Exact product path

Only existing gateway_state_projection.py changes, plus new
 gateway_retained_projection.py. Explicit NATIVE_RETAINED_LAYOUT and retained_profile
must be selected together. Old defaults still reject a receipt before probing
kernel state, while new selection without one also refuses. The original four
modes use their previous call paths and return shapes.

RetainedProjection requires the exact VolumeBinding class AND object reference,
its complete valid fields (image/controller/worker/cgroup/namespace/loop/fence),
original typed RetainedProfileExpectation and current principal. Full immutable
value snapshots detect later field changes even in the same object, and the
original/current principal dictionaries must agree. All three DB devices and
profile inode must belong to the bound loop volume. The receipt's home may be
only mountpoint/profile or the fixed target; no alternate path, traversal or
caller-supplied arbitrary alias is accepted.

This record is trusted caller data, NOT a signed token or launch capability, just
like the existing VolumeBinding and retained expectation. It does not protect
against arbitrary hostile Python code in the same process. Mapping validation
alone is not proof that any mount or kernel restriction happened. It is not an
automatic remount/migration contract: a different loop device, source deployment
or cross-process receipt trust requires separately qualified handling.

The helper derives a HOME-ONLY typed receipt view internally after validation.
Original receipt and DB/epoch/instance/source/cache fields remain unchanged. Both
host and target views run the unchanged strict gateway_native_layout reader:
private regular file metadata, exact three DB identities, bound discovery bytes,
empty active registry and no extra credentials/config. No SQLite handle opens,
epoch write, helper-file deletion or metadata repair are performed by the mapper.

inspect_volume still proves live root supervisor/controller/worker/cgroup/image
attachment/mount/fence and profile identity. The retained host view is checked
there, and the same original mapping is checked again in _ProfileMounts.pivot
before any bind. Original bind/remount flags/source-target inode checks remain.
After pivot, the entire target snapshot is compared before privilege drop. UID/
GID/capability drop, seccomp and Landlock retain their original sequence. A final
whole target check after those stages must succeed before returning retainedProfile.
The return still explicitly says no profile lease, native DB or agent admission
has been acquired. No old caller receives a retainedProfile field implicitly.

NativeStoreStartup itself is unchanged. It receives the typed target expectation
and still checks previous epoch/instance, all three identities, lease, mount, cold
schema and live state before any epoch acceptance. Unit handoff tests stop before
cold helpers/SQLite and verify failures cannot open them. JSON/exec serialization
of this typed result has NOT been implemented; historic F126 launcher only uses
old modes and remains untouched. A new launcher must explicitly reconstruct the
trusted typed record, not treat arbitrary JSON as launch authority.

## Tests and immutable evidence

Own36 focused contracts comprise mapping/projection/pivot/original-startup checks
plus two exact historical-source binding negatives. Kernel, user/mount syscall and
startup store boundaries are explicit test doubles. They cover changed binding,
receipt, principal, profile, each database, wrong views, selected/unselected modes,
late target change, failure after UID drop/filter/guard, and unchanged old modes.
Existing22projection,18prepared and18three-store test files also passed unchanged.

Independent C14221 checks use EXACT two current runtime hashes and a separately
written driver. It added six original-startup tests to its earlier15 with unchanged
bodies;15 and21 are historical subsets, not36 distinct tests. Current source21
result, old15 script/result and all raw logs are copied with source/provenance
hashes. Copying is not a new test execution. Our six offline receipts check these
records; own focused42=36contracts+6receipts, not42native/kernel executions. There
is semantic overlap between own and independent contracts; do not total as unique.

One original F126 receipt check failed when it compared its historic kernel run
against this changed projection source. Raw failure remains. A resolver for ONLY
this file and exact immutable1321699 pre-change bytes was added to the existing
history chain. Unknown names or hashes are not redirected; current changed source
never inherits old kernel acceptance. Original expected digests and original
native/kernel result records remain unchanged. The failing file passes again.

Candidate001 two runtime files remain unchanged through this stage. Final full
standard count/outcome/source hashes are separate and must be read from full001;
focused success is not promoted to a full-suite or current-kernel success.

## Remaining acceptance

Real current-source kernel acceptance is NOT RUN. It requires the reviewed
supervised-volume launcher to carry the typed retained expectation across the
host/target and exec boundary, pin current756native code+dependencies and run the
actual API/finite/worker/result/normal-close path under namespaces/seccomp/Landlock.
Perform old-request replay without recompute, new request once, normal and controlled
error, and host-file/socket/ambient-FD/reentry negative canaries. First profile
creation and retained reopen must use their respective explicit layouts.

Specific previous denied root/cleanup/bootstrap operations are not retried here.
No alternative tool or broad sudo/WSL command should be used to bypass a refusal.
Rootless permission checks, unit sequencing and old kernel receipts are not a
substitute for executing the new isolated lifecycle. Authenticated HTTP, separate-
process trusted receipt persistence, crash/power-loss durability and real
model/tool/memory/budget acceptance remain separate future gates.

## Complete standard terminal result

Fresh3534=3511PASS23SKIP0ERROR0FAIL, actual command0020exit0,217.486seconds.
620source/config/test files and11patches unchanged. Other614of616old files unchanged;
one oldruntime plus one oldhistoryhelper changed, four new source/test/helper files.
Same23skipIDs/reasons. Focused42 and independent21 remain overlapping unit/receipt
scopes, not kernel/native execution. Old targeted F126 hash failure retained and
corrected with exact immutable prior generation before this complete run.
