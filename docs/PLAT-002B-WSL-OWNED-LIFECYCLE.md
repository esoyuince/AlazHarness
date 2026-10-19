# PLAT-002B — Windows/WSL2 test-owned Linux subprocess lifecycle

Date: 19 October 2026
Branch: alaz/plat-002b-lifecycle-19oct
Base: bac4d1b2730e7f97ac630a45372a898a1b905d21
Status: **SCOPED NATIVE OWNED-CHILD PASS**; full PLAT-002/D3B **NOT ACCEPTED**.

## Purpose and prior blocker

PLAT-002A fixed read-only Windows/WSL handshake had a native five-case
FAIL when its positive guest query timed out. Guest process closure
remained UNKNOWN; auto retry and WSL restart were intentionally prohibited.

This phase began with separate read-only inspection. Native Windows
process enumeration found 0 wsl.exe, wslhost.exe and VmmemWSL and one
WslService at that instant. WSL --list --running independently reported
Ubuntu RUNNING, demonstrating that no visible Windows wsl.exe does not
mean a stopped Linux guest. A fixed read-only Ubuntu /proc scan read
72 command lines with 0 inaccessible and found 0 old guest probe
processes. This resolves only their state at the inspected snapshot,
not the historical reason for the previous timeout.
Initial Linux /tmp filesystem probe returned stat type ext2/ext3.

Evidence: evidence/plat-002b-lifecycle-19oct/read-only-recovery-preflight.json

## Implemented, explicitly test-only

- scripts/qa/wsl2_owned_lifecycle.py: exact-SHA verified fixed Linux
  Python source, no arbitrary executable/command input, nonroot UID.
  Source copied into an owned private /tmp directory and checked again
  before running test-owned subprocesses.
- scripts/qa/run_plat002b_windows_once.py: Windows-only fixed WSL binary,
  fixed Ubuntu distribution, fixed script and script SHA, explicit
  environment opt-in, one native execution and immutable receipt. No
  shell/paid model/system account changes.
- tests/test_plat002b_lifecycle.py: 19 offline guard/policy tests.
- tests/test_plat002b_receipt.py: 8 independent source/native-receipt
  custody tests; CI never runs a live WSL process.

The Linux native filesystem was reported by GNU stat as ext2/ext3.
This is a filesystem-family name; it is not an independent on-disk
ext4-format assertion.

## Actual native acceptance: deliberately narrow

One Windows -> Ubuntu one-shot pilot returned exit 0. An inner
unprivileged Linux copy of the guest script exercised the following
eight checks, all **PASS**:

1. Owned child returned exit code 0.
2. The normal child was reaped.
3. A dedicated owned process group terminated with SIGTERM.
4. The SIGTERM child was reaped.
5. A child ignoring SIGTERM required stronger termination.
6. That child exited with SIGKILL.
7. The SIGKILL child was reaped.
8. All three test-owned children were reaped.

The exact source copy SHA matched before/after copying into /tmp.
The copied source and owned temporary root were removed. A separate
read-only Ubuntu snapshot inspected 72 processes, found 0 matching
PLAT-002B process command lines and 0 matching temporary roots.
The run was neither a real Hermes Gateway nor a provider invocation.

Receipts:
- evidence/plat-002b-lifecycle-19oct/native-owned-lifecycle-01.json
- evidence/plat-002b-lifecycle-19oct/post-run-readonly.json
- evidence/plat-002b-lifecycle-19oct/summary.json

## Not established — keep FAIL/UNKNOWN separate from PASS

- Cancelling/killing the **Windows WSL wrapper mid-flight** and proving
  its Linux descendant tree is reaped was **NOT TESTED**.
- Linux process UID1000 is not a separate host broker UID. The native
  probe did not activate D3B Landlock/netns/IPC, independent broker
  ledger/budget, or a host filesystem confinement policy.
- A Windows mounted filesystem was visible for initial source
  loading; hostFilesystemIsolated remains false. This is not a
  secure general WSL execution adapter or authentication boundary.
- No real model/provider, scheduler/autonomy, account changes,
  WSL reset, unrelated PID termination or production daemon.
- The old PLAT-002A native five-case FAIL and its reason remain
  unchanged as separate historical evidence.

## Exact next gate

PLAT-002C: bounded Windows wrapper cancellation, guest owned-PID/
lease fencing, child-grandchild tree and unknown-outcome reconciliation,
using independently inspectable test-owned processes. Then join
with D3B host principal, mounted IPC, broker budget and actual
scripted Hermes Gateway before wider security acceptance. Model
tariffs and autonomy remain separate.

Full Windows unittest: 2,186 discovered, 2,181 executed and 5
Linux-only skipped, exit0, 238.704s. The complete log remains in the
own ignored runtime/plat-002b-lifecycle-19oct directory, with its
SHA-256 in the evidence summary. Root static check PASS: 2,186
discovered, 1,530 tracked files and two pinned upstream links.
Exact-code GitHub CI is pending and is distinct from these local tests. Do not call scoped native PASS full D3B PASS.


## Exact PLAT-002B code CI status

The native evidence/source code commit
242a92dbec2adfd606e99cbe9065aed866666fd4 on the isolated
alaz/plat-002b-lifecycle-19oct branch has GitHub alaz/local-ci
**SUCCESS**, status ID 56730161201 at 2026-10-19T20:33:08Z.
The exact original Git source hashes match the one-shot native
Windows->WSL2 scope and saved evidence. Native 8/8 owned subprocess
checks, Windows full 2186 exit0 skipped5, and source static
2186 discovered/1530 tracked text files/2 gitlinks PASS.

This CI does NOT qualify Windows-wrapper mid-flight cancel, full D3B,
Windows host filesystem confinement, a separate broker host UID,
or real agent/model execution. The following docs/evidence-only
commit will need its own independent CI observation.
