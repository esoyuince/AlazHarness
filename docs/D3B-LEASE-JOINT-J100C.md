# Image/profile lease integration — J100C

Status: integration source and native experiment qualified separately; final
full/static outcomes below are authoritative only after terminal results.
Branch: alaz/d3b-lease-joint-j100c.
Inputs: f7f12edcbda7e3876aaf0e98fb3d91d9ea99af86 (L99D profile lifecycle)
and681ddd9fe94a81d25e75edcd9dea8df9fb59c6d4 (V98R image lease).
Common baseline: bb30a99. Both histories and original evidence are preserved.

## Integration, not a new lock implementation

The two product implementations coexist unchanged. ImageLease is held by
an outer cooperating controller; pinned native Hermes ProfileOwnership is
held by the final ordinary profile process. No extra database or profile lock
engine is introduced. The merge conflict was limited to status.md; both
relevant histories remain below the new continuation. The unqualified R91F
and failed G82C branches are NOT merged or changed. Their original failures
remain failures, independently of this different qualified test selection.

## New actual Linux cross-process experiment

New QA only: scripts/qa/j100c_joint_lease_probe.py. It reuses the existing L99D
setup/source verification and exact original native ownership implementation.
The approved disposable P71C lab runs as alazgateway UID23001/GID23003.
The parent and profile children are different PIDs but the SAME ordinary UID;
this is not a new host-identity or confined-Gateway acceptance.

The controller leases a new inert64KiB image file. The two dummy SQLite files
are in a SEPARATE ordinary temporary profile, NOT inside the image. No image
is formatted, attached or mounted. No root, account, package, namespace,
service, live database, provider or real Gateway operation is used.

The successful fresh trial checks28 overlapping conditions across two child
owner lifetimes and11 contender processes:

- Acquire image in parent before starting the child that acquires native profile.
- With a registered real writer alive, native finish refuses and retains the
  profile lock. Both image and profile rivals remain excluded.
- Drain writer and release profile while that child deliberately remains alive.
  A profile rival can now acquire, but an image rival is STILL refused.
  Therefore profile lock availability is NOT evidence that its process exited.
- Reap the normal child; parent still holds image. Start a second profile owner,
  verify contention, and intentionally exit that owned child with73 without
  finalizers. Reap it, then confirm profile available but image still excluded.
- Only after explicit parent close can the image rival acquire. Both original
  dummy databases, image bytes and lock inode remain unchanged. No forced
  cleanup is needed; all fixtures/code are removed. Identity, user/mount
  namespaces and mount table remain unchanged.

The ordering above is implemented by this QA experiment, NOT by a production
volume supervisor. The ImageLease API itself still permits a trusted caller
to close early; no new enforcing teardown guard is claimed. This trial cannot
prove no other volume attachment, descendant writer, mount or device reference
exists. It does not justify enabling persistent admission or legacy IPC v2.

## Process-bound evidence correction

First trial79/79 Linux unit methods passed, but the joint experiment exited1
with27/28 checks. The parent expected gateway.status in its own module list;
only the children actually reserve a profile and lazily import that module.
The failure is preserved in native-001-* and the original QA source snapshot.
Product code was NOT modified. The corrected QA records source inventories
inside each owner child in its PID-bound ready message; each exact native
source hash must match the transport manifest. Parent imports are recorded
separately. No child execution is inferred from parent imports.

Fresh native002 ran79/79 selected methods again and passed28/28 joint checks,
actual subprocess exit0, no skipped Linux methods. Both owner inventories
contain42 verified Python sources. This is a NEW execution, not an edited
old receipt or retrospective relabeling of native001. This correction concerns
only the new J100C probe; the separate blocked R91F collector is untouched.

## Source custody and interpretation

Transferred native bytes came from no-replacement Git objects at Hermes pin
 eb75627faf532fa6ffbdae59a0d14b0b385fc780. Existing ruamel.yaml0.18.16 sources
match the previously qualified installed-package hashes. No dependency was
installed/updated and no upstream code was committed into this tree. The
48-file temporary transport manifest and the per-process inventories are
stored with raw output. Product sources from both inputs are unchanged.

The selected79 methods are30 mount observer +23 native-profile sequencing +26
image-lease methods. Repeating them on Linux does not create79 extra unique
cases. The28 native observations overlap and are not28 Gateway runs.
Four new offline receipt checks pin current code, per-process provenance,
ordered outcomes, limited claims, first failure preservation and cleanup.
The full standard run includes those four; it is not reconstructed from
old passing subsets. Windows skips the18 Linux image methods plus five prior
explicit-opt-in broker methods; the18 image cases ran in the new Linux79.
No fresh execution of the five optional broker methods is claimed here.

## Cleanup and next boundary

Only our named P71C lab was stopped after an ordinary-user audit found no
matching code/profile/image fixtures or probe processes. Both distributions
were observed stopped in the final list; no Ubuntu stop/start was issued.
UTF16 WSL text is recorded reversibly with original byte counts and hashes.
No global shutdown, main advancement, push, provider or model call occurred.

Next: a bounded outer-supervisor lifecycle must verify no old attachment/users,
attach the image privately, keep the lease outside child exec/FD cleanup,
reap all users and detach before releasing it. Then qualify the actual native
stores/epoch/recovery and fixed Hermes entrypoint before admission. Existing
profile validation and advisory image locking do not supply those guarantees.
The separately blocked R91F evidence repair remains unresolved. Full D3B OPEN;
legacy IPC v2 CLOSED; no physical/power-loss durability assertion.

Evidence: evidence/d3b-lease-joint-j100c/.
Current status: status.md. Final tested merge commit is recorded on delivery.

## Independent full result and concurrent primary

Current complete Windows execution2365 total=2342PASS/23SKIP/0FAIL/0ERROR, exit0;358 sources unchanged. The previous native79 and28-condition records apply to exact current product/QA bytes, not a reconstructed result. Primary separately completed the same product merge plus J01C QA at0e89518. Its code/evidence are not overwritten or counted as this trial. Independent merge is checkpointed first; a fresh final regression is required when joining both QA contributions.

## Final union qualification

Independent merge836a29a (our qualified2365 suite) is joined with concurrently
completed primary0e89518 (J01C). Products are byte-identical; incoming new source
consists only of the other QA runner and its four receipt methods. The J01C
controller-death counterexample and our ordered child-teardown proof complement
each other. Preserve both raw first failures and separately executed successes;
never sum native predicates into a fictitious larger single trial.

NEW final full execution:2369 total =2346 PASS /23 SKIP /0 errors /0 failures,
exit0,203.615s, all360 source hashes stable. Both sets of receipt tests are in
that total. Eight offline receipt methods are not eight new Linux executions.
The final48 copied native sources for our Linux trial still match this union.
No further native run was performed after the evidence-only union, and no old
Windows result was relabeled as its regression. All34 incoming J01C and27 prior
J100C evidence blobs match their input commits; the earlier73 L99D/V98R files
remain preserved. The final sequential local static gate is recorded separately.

Once that gate passes, this exact commit may be fast-forwarded to the still
clean primary at0e89518. A documentation-only delivery records canonical paths
and the tested merge. No main/push action or additional runtime activation.

## Canonical delivery

Tested consolidated merge `58d5b4cf669661b111ffb5980a822c2a698906aa` was fast-forwarded from0e89518 into `alaz/d3b-principal-launch-21oct`. Canonical worktree is `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-principal-launch-21oct`. Original integration branch remains clean at that tested merge. The following documentation/delivery commit keeps all360 source hashes exact and changes no runtime setting. No push/main update; current status is the newest top entry in status.md.
