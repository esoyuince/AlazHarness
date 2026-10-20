# PLAT-002D — unexpected Windows WSL-wrapper loss

Date: 20 October 2026
Status: **OFFLINE POLICY/EVIDENCE QA PASS; NATIVE WRAPPER-LOSS NO-GO**
Branch: alaz/plat-002d-wrapper-loss-20oct
Base: 03717f73fa57e9722a39f5180f6198794fce4ec9
Production agent / full PLAT-002, D3B, M1/M2: **NOT ACCEPTED**

## Purpose

A *test-owned* Windows wsl.exe wrapper can disappear while a
fixed Linux child and grandchild remain active. Unlike ordinary
START/READY/CANCEL/CANCELLED (PLAT-002C PASS), this out-of-band
interruption must never imply tool success or automatic effect
replay.

This is an opt-in QA fixture: not a general command launcher,
not a production model loop, and not an attestation of WSL host
filesystem confinement. No privileged accounts, network,
host service restarts or unrelated process termination.

## Implemented QA-only design (not a security certificate)

- scripts/qa/wsl2_wrapperloss_guest.py: WSL2 x64 UID1000,
  source SHA-frozen native /tmp 0700 copy, detached guardian
  and one fixed worker/grandchild process group. Fixed
  seven-second nonrenewable lease, Linux subreaper and
  PID/birth-tick checks; a twelve-second worker self-cleanup
  fallback. Exclusive 0600 ready/result records scoped to
  the exact test-owned root. No arbitrary shell or model.
- scripts/qa/wsl2_wrapperloss_observe.py: independent guest
  observer checking run ID, nonce hash, source SHA, UID,
  PID birth time, lease terminal record and current processes.
  Cleanup is allowed only for the three exact, verified files
  after authoritative closed/unknown evidence. No recursive
  deletion.
- scripts/qa/run_plat002d_windows_once.py: original immutable
  seven-second READY test, receipt native-wrapperloss-01.json.
- scripts/qa/run_plat002d_windows_once_v2.py: second independent
  fresh-run, 20-second bounded READY test, receipt
  native-wrapperloss-02.json. Its console print mistakenly
  named the first receipt; the fixed RECEIPT path and bytes
  of the second file are independently verified.
- tests/test_plat002d_wrapperloss.py,
  tests/test_plat002d_second_pilot.py and
  tests/test_plat002d_receipt.py: offline policy and immutable
  evidence QA, no WSL or other OS process launched by default CI.

The code describes a bounded test watchdog, but its actual
survival of WSL-wrapper termination was not proven. Do not
turn nominal TTL values into a guarantee of cleanup.

## Native experiment 01: initial READY timeout

Independent preflight in Ubuntu read 73 /proc entries with zero
unreadable, no old PLAT002D processes and no test roots.
One explicit first invocation returned
FAIL_OR_UNKNOWN_GUEST_LEASE, READY_TIMEOUT_UNKNOWN after 7s.
No READY was received, and therefore there was no verified
Windows-wrapper interruption *after* READY. The independent
source-bound observer found NO_OWNED_ROOT. A subsequent
read-only global Ubuntu scan read 72 /proc entries with zero
unreadable, zero matching test processes and zero roots.
This first FAIL was preserved with exact source hashes.

## Native experiment 02: READY, test-owned Windows wrapper stopped

After a separate clean postfail snapshot, a different host
controller used a new random run ID, a new receipt filename
and a bounded 20s readiness deadline. It **received and
validated READY**, then terminated only its own Popen Windows
wsl.exe wrapper; observed wrapper exit code 1.

The independent WSL observer reported NO_OWNED_ROOT and did
not find the required durable Linux lease/cleanup record.
Thus this native result is also **FAIL_OR_UNKNOWN_GUEST_LEASE**
and the external effect is **UNKNOWN_DO_NOT_REPLAY**.
A separate later read-only Linux /proc query did not respond
within 22 seconds. Full guest process disposition and actual
lease expiry/reaping remain UNKNOWN.

A Windows-only native process snapshot later found zero
Windows wsl.exe and wslhost.exe but one WSL service. This
does NOT prove that the Linux guardian, worker and grandchild
were correctly reaped or why the native directory disappeared.
No WSL restart or third native effectful attempt occurred.

## Frozen evidence and acceptance separation

evidence/plat-002d-wrapperloss-20oct contains:
- preflight-readonly.json
- native-wrapperloss-01.json (FAIL)
- postfail-readonly.json (first clean snapshot)
- native01-failure-custody.json (original source SHAs)
- native-wrapperloss-02.json (FAIL)
- native-no-go-summary.json (both independent attempts,
  source SHA manifest, WSL postquery timeout, Windows process
  snapshot and explicit NO-GO).

Original raw Windows CRLF and Git LF source representations
are compared by a strictly bounded exact single transformation
in tests. Historical native FAIL files are never relabelled,
rewritten as a new run or implicitly retried.

**Native readiness for attempt 02: PASS.**
**Deliberate termination of the owned Windows wrapper: OBSERVED.**
**Independent Linux lease terminal record and cleanup: NOT PROVEN.**
**Native PLAT-002D acceptance: NO-GO.**
**M1/M2, D3B host principal/IPC/budget and production agent: NO-GO.**

## Next gate: PLAT-002D-RECOVERY

1. Reestablish independent WSL guest query health. Read guest
   boot identity/uptime and process/mount identity using only
   authorized read-only checks. Do not restart WSL or issue
   another wrapper-loss pilot while Linux process state is
   unknown. Any disruptive recovery requires operator approval.
2. Specify a narrowly scoped, test-owned, persistent Linux
   ledger *outside volatile /tmp* with owner UID/mode, exclusive
   create, run/nonce/source SHA, process birth-ticks, boot ID
   and fsynced terminal evidence. Never touch personal or
   production agent state without separate authorization.
3. Test host loss before READY, after READY, before/after
   terminal fsync, guest boot changes, and descendant
   reparenting separately. Independent auditor must prove
   closure or explicitly preserve UNKNOWN; never replay
   the original external effect automatically.
4. Only after the guest/wrapper lease gate passes, integrate
   real D3B broker vs Gateway host UIDs, selected IPC socket,
   network/filesystem confinement, durable budget and real
   local scripted Hermes Gateway before full platform acceptance.

Green unit/static/GitHub CI validates **only source contracts
and preserved evidence**, not the failed native safety gate.


## Windows root and scoped CI evidence

Default-discovered Windows Python root unittest: 2,286 tests,
2,281 non-skipped, five Linux-only skips, exit0, 368.720s.
All 57 new PLAT-002D policy/source/native-negative-receipt
tests PASS. Complete Windows log (ignored, not published):
runtime/plat-002d-wrapperloss-20oct/full-standard-windows.txt
with SHA-256 in local-qa-summary.json. Source static checker
PASS: 2,286 discovered, 1,555 tracked text files,
two upstream gitlinks and zero errors.

These code checks never restart WSL, replay either native pilot,
execute a real model or provide the missing native lease receipt.
Exact GitHub branch code CI must be checked separately.
