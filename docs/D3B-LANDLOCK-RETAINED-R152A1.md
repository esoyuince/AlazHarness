# R152A1 - current Landlock and retained native lifecycle

## Result and scope

SCOPED_KERNEL_AND_RETAINED_LIFECYCLE_PASS. The immutable native003 candidate
completed on 25 October 2026 at 21:55:38 Europe/Istanbul. Normal computation and
controlled computation failure both passed with exit 0. Each scenario exercised
the original native retained owner, API resolver, finite runner, physical worker
thread, settlement, result persistence, three stores and lease lifecycle.

The first lifecycle ran unconfined. After normal owner closure and caller lease
release, a fixed QA exec entered a fresh interpreter. The unchanged current
credential guard then installed Landlock ABI3, and a second fixed QA exec
reopened the retained profile. The second owner and its cold helpers operated
under inherited filesystem confinement. Both execs preserved PID and start time.

This is filesystem-component and retained-lifecycle acceptance. It does not run
gateway_retained_launch.launch/receive/target_main, the product projected target
or the privileged volume supervisor. It does not establish namespace isolation,
separate UID, network isolation, zero capability bounding set, HTTP readiness,
real-provider/model cost, crash recovery or full D3B acceptance.

## What was changed

Only four QA scripts and their documentation/evidence were added. No product or
native source, configuration, source pin, installed dependency or supervisor was
changed. The starting harness commit is
8aae47fb7efa94fbfb45b22018747d4bb3178c2a. The native source remains
d1516731308de8e87130dc68124e69aad35d6911.

- r152a1_windows_accept.py freezes immutable Git sources and exact QA bytes,
  creates an exclusive attempt record, and checks complete terminal/source custody.
- r152a1_linux_transport.py verifies the bundle and installed dependencies,
  owns two bounded disposable process groups, qualifies results/audit events,
  and removes only its successful fresh trees after complete acceptance.
- r152a1_landlock_bootstrap.py starts with a fresh standard-library interpreter,
  validates the prior owner handoff, applies the unchanged guard, and performs
  the second fixed QA exec before native imports.
- r152a1_landlock_native.py extends the existing T143 actual native lifecycle
  driver with Landlock proof, retained replay/new-result checks and hash-bound
  pre-exec/bootstrap records.

The only double remains the declared AIAgent factory/computation/close fixture.
The input is SUM:17,25,8; normal computation yields 50. The error scenario raises
the declared controlled computation exception. API admission, finite execution,
physical thread scheduling, persistence and native owner methods are original.
There is no manual SQL settlement, forced native close, registry reset or forced
lease release on failure.

## Immutable attempt history

| Attempt | Result | Observed boundary and correction |
|---|---|---|
| native001 | FAIL, exit 1 | Original inherited-FD guard rejected the warm interpreter before Landlock installation. The completed first owner had physically closed three stores and released its lease. A new candidate introduced ordinary exec into a fresh QA bootstrap; the guard was unchanged. |
| native002 | FAIL, exit 1 | Fresh bootstrap, actual Landlock and both same-PID exec transitions succeeded. Native prepare_runtime imported aiohttp/stdlib mimetypes and received EACCES on /etc/mime.types. The next candidate added only this canonical nonsymlink file to the QA readonly list. |
| native003 | PASS, exit 0 | Normal and controlled-error scenarios completed all retained lifecycle and kernel checks. |

No attempt was replayed. Both failed runs terminated without timeout or signal,
their owned process groups were empty, and their failed temporary trees were recorded as
retained at terminal inspection. Their original raw results, frozen QA snapshots, terminal receipts and
diagnoses remain in the evidence directory. Candidate001's unconditional
landlockFilesystemComponentTested field was a reporting defect: null proof and
the original rejection show Landlock was not installed in that run. Later
candidates derive that field from recorded proof.

The accepted cases observed a non-inheritable regular FD7 before the bootstrap
exec and only FDs0/1/2 in the fresh bootstrap before the guard. These are type and
inheritability observations; descriptor contents/targets were not inspected.
No arbitrary descriptor closing or guard weakening was used.

## Accepted native behavior

| Check | Normal | Controlled error |
|---|---|---|
| First finite work | Once; terminal completed result 50 | Once; terminal failed result |
| Retained reopen | Epoch 1 to 2, same three database identities | Epoch 1 to 2, same three database identities |
| Exact saved request replay | Identical stored result and usage, zero new computation | Identical stored failure result and usage, zero new computation |
| Changed payload with same request ID | admission_conflict refused | admission_conflict refused |
| New request | Exactly one new physical-thread computation | Exactly one new physical-thread computation |
| New persisted admission | terminal completed, owner epoch 2, generation 2 | terminal failed, owner epoch 2, generation 2 |
| New result and usage | Equal to actual API return | Equal to actual API return |
| Prior admission/result | Unchanged | Unchanged |
| Ordered closure | All three native connections physically closed, trusted retained receipt captured while caller lease held, then lease released | Same |
| Cold helpers | Two before bootstrap and two under confinement | Two before bootstrap and two under confinement |

The code's assertions verify actual connection closure and persisted/API equality;
the report records successful completion of those assertions. Each scenario has
14 first-lifecycle checks and four resumed-lifecycle checks. There are four total
fixture computations across both scenarios, not computations on replay.
The four original retained helper files are kept unchanged at restarted startup.
Both owner startups complete the original six cold/live checks.

## Kernel and process observations

The existing ordinary lab account is UID 23001/GID 23003. Actual supplementary
group 23003 and CapBnd 2199023255551 remain present. CapEff, CapPrm, CapInh and CapAmb
are zero. The unchanged observer is equal before/after guard application except
no_new_privs changes from 0 to 1, and equals the post-exec observation. No namespace,
mount, UID or capability transition is claimed.

There are four primary before/after denial pairs across the two scenarios:
synthetic canary read-open and QA source write-open, each first permitted in the
same process and then rejected with EACCES13. The four corresponding post-exec
observations confirm inherited denial; they are not extra independent controls.
The probes open/close only: no canary contents are read by the denied probe and no
source write, truncation or creation is attempted. Both synthetic canaries and all
frozen source bytes remain unchanged.

The QA readonly exports are the frozen harness/native sources, pinned installed
dependencies, explicit Python/shared-library paths and specific runtime files,
including /etc/mime.types. Writable exports are only the new case's temporary
profile area, result directory, environment home and /dev/null. This laboratory
export set is not asserted to equal the full product projection policy.

The network audit hook denies every observed socket.connect, socket.bind and
getaddrinfo event. Four optional urllib3 IPv6 bind probes were denied: one in each
initial and resumed interpreter. Acceptance recognizes only the exact _has_ipv6
function, pinned dependency path and SHA256, with at most one per interpreter.
No network operation is allowed by this exception, and unexpected audit events
fail. This is not kernel network-isolation acceptance or a claim of zero attempted
network operations. No provider was called.

## Source custody and lifetime

The accepted bundle contains 823 source entries: 756 native files, 66 harness/QA
files and one accepted-dependency map. The installed 1162 dependency files match the
immutable accepted map before and after execution. Loaded native-module hashes,
transferred sources and final host source bytes match the frozen manifest.

Accepted bundle SHA256:
ff23ecb92b3c00de7244163ea8ef3b5fc62e6ca636d34314a4b9239b2980de60.

| QA file | SHA256 |
|---|---|
| r152a1_landlock_native.py | 0e239897cd1d52d1cff469b7cf94419ea5aa38390cd9d557d0937ede71779378 |
| r152a1_landlock_bootstrap.py | b1007b11f98d66fe3753d7225e3daf8eae22cf82e85dbffd81ce8b7f7be58b86 |
| r152a1_linux_transport.py | 91246de577096d588c265f6ef22d9bc09f170f376400b08ec0826219d9c8c035 |
| r152a1_windows_accept.py | f7e9bfc08c826b8b3e2104d6f8986278edd00346214840a9dcfe90a711883bd9 |

Both successful process groups were already empty at normal completion; complete
stdout/stderr was captured. No timeout, signal or straggler termination occurred.
Cleanup was deferred until both cases, audit accounting, final dependency checks,
empty groups and fresh-root device/inode/UID custody passed. Both successful trees
were then removed. The two earlier failed trees were not cleaned. Timeout and
cleanup-error branches were statically reviewed, not fault-injected.

The original native stderr preserves its SQLite fallback and missing optional
secret-source module warnings. The accepted lifecycle uses the unchanged pinned
environment; no SQLite/package upgrade is part of this result. Outer stderr is
empty. Warnings do not substitute for successful persisted-result/close checks.

## Review and publication gate

Independent source review corrected result/epoch/generation coverage, late
pre-exec assertions, timeout nesting, unknown-result receipts, early profile
cleanup and unconditional Landlock-tested reporting before accepted execution.
The final one-file MIME export change was verified at the byte level.

Independent full-record corroboration passed all 115 recorded-data checks.
These are JSON/source/hash checks, not additional runtime tests. The reviewer
reconstructed the manifest and complete transport stdout digests, compared
standalone and embedded proof artifacts, and checked all four QA and imported
native source hashes. The exact-commit publication gate is recorded separately.

API return tuples, handoff bytes and kernel-hash environment values are not
separately exported. Their equality and binding are supported by hash-matched
executed assertions and receipts. Full dependency bytes and earlier failure
trees were not independently reread by the reviewer; original runtime
attestations/terminal records support those claims. The guard's internal policy
hash normalization was not independently recomputed; no mismatch is reported. The historical full suite (3615 PASS / 23 SKIP) is prior evidence;
it is not a new R152 local run. Static test discovery is not test execution, and
the CI status API does not establish a fresh test count.

## Evidence and continuation

- observed-summary.json: recomputed per-case evidence from immutable raw records.
- native001/ and native002/: preserved failures, diagnoses and reviewed source snapshots.
- native003/: intent, manifest, reviewed sources, raw stdout/stderr, all three
  per-case artifacts, terminal and redacted Bridge receipt.
- protected-state.json: root/main baseline equality, clean pinned native source,
  and empty product/config/source-lock diff.
- independent-review.json and local-gate.json: recorded review and publication checks.

Current-source full projected readiness remains NOT RUN. The existing privileged
installation was not qualified for this source, and no current trusted supervisor
invocation was available. The next product gate is the existing authorized volume
supervisor invoking the exact fixed projected launcher, with its full identity,
mount/export/namespace requirements and original native startup/close/lease path.
Earlier denied root/bootstrap/mount/cleanup operations were not retried or routed
through another tool. This package does not authorize such a retry.

## Local publication gate

Staged ci_check.py PASS, exit 0: 6221 tracked files scanned, two source gitlinks,
10 selected components and 3638 test methods discovered. Discovery is not test
execution. No syntax, JSON, bounded credential-pattern or tracked-path errors.

The default whitespace check reported only one extra blank line at EOF in the
three immutable driver snapshots and the byte-identical executed QA driver.
Those bytes were preserved. Strict whitespace checking passes for every other
path; the four exact frozen paths pass all checks with only blank-at-EOF excluded
for that command. The initial default result and exact scoped commands are in
local-gate.json. No global Git setting or product/source hash was changed.

## Publication

Code/evidence commit 870da7ae310ca20ab4392aa7b998531056ee8384 was pushed to
alaz/d3b-retained-acceptance-r152a1. Its exact alaz/local-ci status is SUCCESS,
observed 2026-10-25 19:08:07 UTC; see publication-code-ci.json. The status API
does not expose an exact fresh test count, so no remote count is inferred.

The closure changes only this report, status/work log, summary and publication
metadata. Its own exact HEAD must also pass alaz/local-ci before ordinary
fast-forward main publication. Live local/origin/remote main equality and exact
final-SHA CI are verified at completion; Git is authoritative for the final SHA.
No runtime service or installed native deployment is implied by the Git update.
