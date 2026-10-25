# R153A1 — Supervised readiness candidate

## Result and product scope

This package adds a fixed retained-readiness child to the existing volume
supervisor and a deterministic exporter for the current harness/native sources.
It advances P1 in [PRODUCT-ROADMAP.md](PRODUCT-ROADMAP.md). P1 and M1 remain
IN PROGRESS: a current installed kernel run, a qualified retained seed on the
same volume, and useful finite work through that complete path are still required.

Base harness: `7abdd57e408ec7972bddeaf267ea180b4cb3673b`.
Native source: `d1516731308de8e87130dc68124e69aad35d6911`, unchanged.
The publication closure will record the exact source commit and actual archive
digest. A source export does not establish installation or execution authority.

## Product changes

### Fixed supervisor composition

`RetainedVolumeSupervisor` extends the original `VolumeSupervisor`; its inherited
image lease, durable fence, worker and attachment remain the single owner. The
new method accepts only the existing typed retained startup record and original
IPC/filesystem contracts for an already RUNNING volume.

The controller checks the original live authority, obtains the known worker
mount-namespace descriptor, and starts one fixed isolated Python child with
explicit argv and environment. Only that descriptor is passed. The child checks
its direct parent and worker identities, joins the original cgroup before the
mount namespace, closes the known descriptor, and calls the unchanged
`gateway_retained_launch.launch`.

The original projection, source exports, UID/GID drop, namespace, seccomp,
Landlock and post-exec ownership checks still decide admission. There is no
new scheduler, owner implementation, arbitrary command or workload callback.
The original readiness target is unchanged.

The original worker has a 120-second idle lifetime. The controller conservatively
records that deadline before inherited start and requires the child timeout
(at most 60 seconds) plus a 15-second stop margin to fit before dispatch.
A fresh worker is an explicit prerequisite.

### Bounded output and uncertain outcomes

The fixed child uses pipes for stdin, stdout and stderr. A main-thread selector
handles partial writes and simultaneous output, with a 65,536-byte per-stream
bound and an explicit deadline. An attempt is never resent or automatically
restarted. Timeout, output overflow, spawn ambiguity and invalid receipts retain
the original child state and block inherited volume stop/finish.

Read-only observation can recognize a later successful exit from that same
child. Completion requires the exact result schema, original child PID, next
owner epoch, the six ordered native startup checks, explicit readiness-only
flags and an empty child portion of the original cgroup while the mount worker
remains alive. Only then may the caller use the original stop/finish path.

### Exact-source exporter

`scripts/build_projected_candidate.py` reads an explicit immutable harness
commit and 756 hash-bound native source files from the existing d151 repository.
Git replacement and ambient Git repository redirection cannot change those bytes.
The archive is deterministic and verified without extraction or execution.

The package includes the accepted 1,162 dependency hashes as a reference inventory.
It does not include or install those dependency bytes, Python, live state or
credentials. The actual installation must independently verify them.

Only a fresh ignored destination below `scratch/projected-candidates/` is used.
The exporter creates `projected-source.tar`, `manifest.json` and
`install-plan.json`. It rejects unsafe names/modes, links, case collisions,
mismatched or missing sources and trailing archive data. The existing bounded
credential scanner is reused; this is not a new complete security audit.

## Verification

| Check | Observed result | Scope |
|---|---|---|
| Windows full001 | 3,690 run: 3,663 PASS, 27 SKIP; zero failures/errors, exit 0 | Original 23 skip IDs/reasons unchanged, plus exactly four Linux pipe skips; source hashes unchanged |
| Windows focused002 | 48 PASS, 4 Linux-only SKIP; exit 0 | 29 supervisor contracts and 19 real-Git/archive checks; included in the full suite |
| Linux pipe transport | 4 PASS, zero skips; exit 0 | Actual owned subprocesses, Python 3.12.14; no native store or kernel projection |
| Independent source review | No remaining blocking finding in the recorded bytes | Source review, not installed/runtime acceptance |
| Local static/index gate | PASS, exit 0: 6,259 tracked files, two gitlinks, 3,690 tests discovered; whitespace exit 0 | Static discovery is not test execution; final commit CI remains required |
| Actual current-source archive | NEXT after immutable source commit | Not yet exported at this source checkpoint |
| Installed projected readiness / finite work / M1 | NOT RUN / NOT ACCEPTED | Remains the next product gate |

Full standard run: Windows Python 3.14.3, 487.133 seconds. Focused Windows run:
167.985 seconds. Focused results are a subset of the full standard run and are
not added to its total. The separate four Linux pipe results qualify transport
only. Default CI status will be checked on the exact final commit; no CI test
count is inferred from the local Windows count.

Independent source review found two blocking issues in the initial draft:
regular-file stdio was incompatible with the unchanged inherited-FD guard, and
completion verification accepted arbitrary check names. Both were corrected
before successful tests. The review also prompted the worker deadline bound.
The reviewed product file hashes are in `source-review.json`.

The first Windows focused run failed because its fixture supplied an incomplete
IPC contract and globally mocked `os.stat`, interfering with unittest traceback
rendering. `focused001/` preserves the failed receipt, diagnostic and source
snapshots. The corrected fixture uses the full original v2 policy and a
module-local OS double. No product validator was weakened.

The independent native-path audit did not reach the source and is recorded as
INCOMPLETE in `review-evidence-limits.json`; it is not counted as corroboration.
Historical specific denials were not replayed. No new R153 installation was
attempted or rejected.

## Next acceptance gate

1. Select the exact disposable current-source installation and verify its
   root-controlled ancestry, interpreter, source bytes and dependency bytes.
2. Produce the retained receipt through the original owner/finite lifecycle on
   the actual supervised ext4 image. A copied QA profile or rewritten inode,
   device or owner record is invalid. Prefer one mount lifetime.
3. Derive the live supervisor, fence, cgroup, namespace, loop and principal
   observations; run the fixed supervised readiness path with the original
   export/identity/confinement checks.
4. Preserve the same owner and evidence on uncertainty; qualify clean native
   readiness and close before enabling finite work.
5. Then implement and accept normal/error, saved-result replay and new work
   through the product path. Provider/model, user flow, durable memory and
   operational recovery remain later roadmap gates.

The candidate plan suggests fresh `/opt/alaz-r153a1`, `/srv/alaz-r153a1` and
`/sys/fs/cgroup/alaz-r153a1` paths. It is a review record, not an executable
installer or permission to retry any earlier denied privileged operation.

## Evidence and workspace custody

Evidence root: `evidence/m1-product-path-r153a1/`.
Baseline and protected-state checks preserve the root worktree's 33 original
changed/untracked files and the unchanged native source. All product changes
are additive; old launcher, native source envelopes and default readiness
semantics remain unchanged.

The status history contains the exact R152 parent, initial R153 handoff and
intermediate work log. The active `status.md` remains the continuation record.
Publication requires success of `alaz/local-ci` on the exact final commit before
an ordinary fast-forward to main. No forced Git operation or service deployment
is part of this package.
