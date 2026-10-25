# R151A1 - actual self-identity map acceptance

## Purpose and current scope

The R150/665330a change adds only the current numeric process UID/GID map
READ_FILE grants when explicitly selected by the retained launcher. The previous
19 controls used declared file/syscall adapters. This package qualifies that
component against the actual Linux kernel with the original guard and observer.

The test executes as the existing ordinary alazgateway account in the dedicated
AlazHarness-D3B-P71C lab. The read-only environment probe confirmed UID23001,
GID23003, Python3.12.3, Linux6.6.87.2 and Landlock ABI3. A first WSL diagnostic
reported a missing default home directory but the probe exited0; the executable
test explicitly selects / as its working directory.

## Evidence design

The exact five product modules plus one QA driver are hash-checked before transfer,
after load, after execution and in the host source tree. No product functions are
patched. All irreversible confinement is confined to fresh child processes.
Four cases are prepared: default maps denied; selected maps readable by the
unchanged observer; fixed QA Python exec preserving PID; descendant with a new
PID receiving no new self-map grant. The descendant may still read its parent's
explicitly granted files while that parent is alive; that inheritance is recorded.

Each of the42primary denial checks is first shown to be permitted in the same
process before confinement. The4additional descendant checks start already
confined; they are inherited-denial observations without an unconfined same-child
baseline. Sensitive proc tests only open and close descriptors; they never read
environ/mem contents or write/truncate/create proc files. The protected file is a
new synthetic canary. No real credentials or profiles are used.

## Execution control

Use scripts/qa/r151a1_windows_accept.py --attempt NAME --prepare to freeze the
bundle, then --execute to run exactly that candidate. Each attempt has an
exclusive execution-start record. Existing or unknown attempts cannot rerun.
The complete stdout/stderr and terminal result are retained, including failures.
Timeout is UNKNOWN, never PASS or confirmed child termination.

## Limits

This is component evidence, not successful gateway_retained_launch.launch,
projected receive, native store startup/close, separate-UID isolation or network
isolation. QA exec uses the fixed test driver, not the product readiness target.
No root/bootstrap/mount/namespace/service/provider action is performed.
No previously denied operation is retried or routed through another tool.

The complete product gate remains the existing trusted supervisor invoking the
exact current fixed projected launcher in its authorized dedicated volume child.
Current-source exports, original ownership guards, mount checks and ordered
startup/close must all pass there before that gate can be accepted.

## Results

SCOPED KERNEL PASS. native002 completed on 25 October 2026 at 19:16 Europe/Istanbul.
All four cases exited0 and passed, with zero failures/skips. native001 was prepared
but never executed; independent review fixes superseded it before the first run.

| Case | Actual result |
|---|---|
| default, PID8 | Original observer denied at /proc/self/uid_map; six metadata grants |
| selected, PID9 | Original observer reads exact identity; eight metadata grants |
| same-PID QA exec, PID10 | Full identity unchanged except no_new_privs0-to1 |
| descendant, parent11/child12 | New own maps/status denied; original parent maps remain read-openable |

All42 before/after open pairs were permitted before policy and rejected with
EACCES13 after policy. This covers foreign UID/GID maps and status, own environ/mem,
own proc/fd directory opens, map write-opens, and the controlled canary. The default
case includes two extra own-map read denials. Four additional descendant read-open
denials are nested in the fourth case, not four extra product acceptance cases.
No sensitive proc contents were read and no proc write/truncate was performed.

The complete after-observation equals before with only nnp changed0-to1. Actual
supplementary group23003 and nonzero CapBnd2199023255551 were preserved and reported.
This does not meet the full product launcher's zero-group/zero-capability-bound
identity requirement and is not reported as doing so.

The five product modules plus QA driver matched all loaded, transferred and host
before/after SHA256 values. The reviewed QA driver SHA256 is
06dd33bcd1aefa6ad0e6f7cf18a157476844cbbf6545ddc2995334fa2f60b36c.
Bundle SHA256: ce8750367c47cfcff9864aa1dae436799320bd984df85f8d01fb5d822242598b.
The owning process group was already empty at normal completion. No timeout or
termination signal occurred. The exact owned temporary tree was removed; all
four synthetic canaries were unchanged. The timeout handling was statically
reviewed, not fault-injected in this run.

Independent review found two pre-run QA issues: a second unverified transport
source read and insufficient descendant accounting on an inner timeout. Both
were corrected before the only actual kernel execution. The reviewer then
recomputed denials, full observer equality, loaded hashes and lifetime evidence
from the recorded full result; it did not perform another execution.
The earlier R150 full suite (3615PASS23SKIP) and main665330a CI SUCCESS are prior
evidence and are not counted as new runs in this package.

## Technical reference

Linux kernel Landlock userspace documentation:
https://docs.kernel.org/userspace-api/landlock.html
The reference describes ordinary processes restricting themselves, no_new_privs,
and inheritance by future children. Actual local results remain authoritative
for the selected ABI3 environment.


## Records and continuation

- evidence/d3b-self-identity-kernel-r151a1/summary.json: exact accepted scope.
- native002/intent.json, result.json, terminal.json and bridge-terminal.json:
  candidate hashes and terminal command evidence; execution-session ID omitted.
- native002/stdout.txt and stderr.txt: original raw output, empty stderr.
- independent-review.json: pre-run corrections and independent result corroboration.
- protected-state.json: root/main HEAD and Git-status observations matched baseline;
  product/config diff is empty and selected product/lock hashes are unchanged.
- native001/not-run.json: superseded preparation, never counted as a test.

No new full standard suite was requested locally because product code did not
change. The publication gate is checked separately for the exact final commit.
The next product gate is still current-source fixed projected readiness, original
native open/close and caller lease release in the existing authorized supervisor
context. This component acceptance does not authorize a root/bootstrap/mount retry.

## Local publication gate

Staged-source ci_check.py PASS, exit0:6151tracked files scanned,2source gitlinks,
10selected components,3638test methods discovered. Discovery is not test execution.
No syntax/JSON/bounded credential-pattern or tracked-path errors. Cached whitespace
check also passed. Source and current product/config/lock diff remain unchanged.

## Publication

Code/evidence commit ec3182bebfe2768a41fdb3bc1e3b50df00e71f6d was pushed to
alaz/d3b-self-identity-kernel-r151a1. Its exact alaz/local-ci status is SUCCESS
(2026-10-25T16:26:52Z), recorded in publication-code-ci.json. The status API does
not expose an exact fresh test count, so no remote count is inferred. This
closure changes only documentation/status/publication metadata. Its own HEAD CI
is checked separately before ordinary fast-forward main publication.
No runtime service or installed native deployment is implied by the Git update.
