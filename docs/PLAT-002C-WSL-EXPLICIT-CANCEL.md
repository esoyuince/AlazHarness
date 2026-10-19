# PLAT-002C — explicit test-owned Windows/WSL2 cancel handshake

Date: 2026-10-20.
Branch: alaz/plat-002c-cancel-20oct.
Base: 4be011b3224ae9b94b5b7f8d0c07583a8f133764
(previous PLAT-002B code + final docs CI SUCCESS).

**Scoped native explicit in-band cancellation: PASS.**
**Out-of-band Windows WSL-wrapper kill/disconnect recovery: NOT RUN.**
**Full PLAT-002, D3B, M1/M2: NOT ACCEPTED.**

## Why this gate exists

PLAT-002A established a strict fixed Windows->WSL2 identity query,
but encountered a native timeout and unknown Linux-process exit.
PLAT-002B subsequently proved on real Ubuntu that only test-owned
Linux subprocesses could be launched, terminated and reaped inside
a private Linux temporary directory, with their source bytes SHA
checked. Neither slice proved in-flight cancellation initiated
by the Windows control plane.

This PLAT-002C sub-slice implements a one-run, explicit
START -> READY -> CANCEL -> CANCELLED handshake. It is NOT a
general-purpose agent tool bridge, autonomous host executor or
safety certificate for Windows filesystem confinement.

## Implemented and protected contract

Fixed scripts:
- scripts/qa/wsl2_cancel_windows_once.py — Windows controller,
  explicit environment opt-in, exactly one fixed wsl.exe,
  one Ubuntu distribution, one /usr/bin/python3 -I -B guest script.
- scripts/qa/wsl2_cancel_guest.py — Linux-only nonroot UID1000
  fixed worker, exact request parsing, source SHA check, private
  /tmp source copy then exec of that copy. No shell, network,
  provider, arbitrary tool or agent-supplied subprocess arguments.
- tests/test_plat002c_cancel.py — 34 local Python contract tests.
- tests/test_plat002c_receipt.py — 9 independent fixed native
  proof/custody assertions; standard CI does not launch WSL.

Windows derives a cryptographically random per-run 24-hex run ID
and 64-hex nonce; input contains only version, explicit
start/cancel, run ID, nonce, and fixed cancellation reason.
The guest rejects unknown fields, altered nonce/run ID, duplicate
JSON keys, empty/NUL/non-UTF8, multi-line and overlong frames.
READY contains guest UID, source SHA and single test-owned
worker PID. Windows checks its exact response shape and that it
does not claim actual secure execution or Windows host-file isolation.

Only after READY verifies does Windows send CANCEL. The Linux
guest's fixed test child ignores SIGTERM; the guest confines
SIGTERM/SIGKILL to that child process group, validates it owns
the group, and waits for the child to exit and be reaped.
The guest removes only its own verified private /tmp script and
directory before sending CANCELLED. Windows checks run ID/nonce,
source SHA, same worker PID, killed/reaped flags, source/temp
cleanup flags, and WSL wrapper process exit0.

A missing/invalid READY or CANCELLED, timeout, nonzero exit or
ambiguous lifecycle produces an UNKNOWN/REFUSED result. No model
call, no automatic replay, and no fallback to an unguarded Windows
process is permitted. Native timeout does NOT mean Linux child
teardown is proven.

## Real one-shot native acceptance

A separate read-only preflight on Ubuntu read 72 process records
with zero inaccessible, zero old/current PLAT002B/PLAT002C
matches and zero matching private temporary directories.
Only after that preflight a single explicit test-owned run was
performed. Its result:

- Host fixed Windows -> Ubuntu WSL2 wrapper exit0.
- READY and CANCELLED run ID, nonce, source SHA matched.
- Guest UID1000; test-only worker PID matched across messages.
- Owned child ignored TERM, was killed with KILL and reaped.
- Own Linux source copy and temporary directory removed.
- No paid model or provider request.

**Native result: PASS_EXPLICIT_CANCEL_HANDSHAKE_TEST_OWNED**.
A separate later read-only Ubuntu snapshot read 72 process
records: zero unreadable, zero matching test processes,
zero matching private temporary roots.

Evidence under evidence/plat-002c-cancel-20oct:
- preflight-readonly.json
- native-cancel-handshake-01.json
- post-run-readonly.json
- summary.json (current source manifest, acceptance limits).

CI evidence SHAs represent only exact native source bytes
with a single recognized Windows CRLF -> tracked Git LF
canonicalization where necessary. Neither a false native
SUCCESS nor a changed historical receipt is allowed.

## Explicit limits and next gate

**Not tested:** forcing/stopping Windows wsl.exe while READY is
outstanding; surviving Linux child/grandchild/FD cleanup after host
loss; Linux parent reparenting and unknown-outcome replay;
different real host UID Gateway vs budget broker; host filesystem
confinement (WSL may still access Windows mounts); full D3B
Landlock/netns/IPC and bound durable provider budget; Hermes
real Gateway; real model/pricing; other macOS/ARM64 adapters.

PLAT-002D next: test-owned out-of-band wrapper interruption with
independent guest lease/watchdog/cleanup and authoritative
read-only post-run reconciliation. The result MUST stay UNKNOWN
until the independently observed process state is known.
Never infer a safe replay from host wrapper exit alone.
Any fully guarded agent execution additionally needs D3B UID,
mount, socket, budget and startup attestation accepted separately.

The combined Harness remains platform-neutral at control plane,
Linux-first for future secure execution; the current test is
narrow and does not enable production or M1/M2 agent autonomy.


## Local regression and evidence/source gate

Windows root full unittest: 2,229 discovered, 2,224 non-skipped,
5 Linux-only SKIP, exit0, 245.578 seconds. The full log remains in
ignored runtime/plat-002c-cancel-20oct/full-standard-windows.txt;
its SHA256 is recorded in the tracked evidence summary. Offline
PLAT-002C test contract: 34 parser/host refusals and 9 immutable
native receipt/source QA, all PASS. Root static check:
PASS, 2,229 tests discovered, 1,540 tracked files, two upstream
source gitlinks and zero errors. These are code-quality checks,
not a new model invocation or a complete Linux confinement pass.
Branch exact-code GitHub local-ci status still PENDING.


## GitHub exact-code CI observation

The code and native evidence were committed as
08bc69f61379e0f4c2e744954eeee1b3d872cd66 on
origin/alaz/plat-002c-cancel-20oct.
GitHub alaz/local-ci: **SUCCESS**, status ID 56740857051
at 2026-10-19T22:55:45Z. Three source files' tracked LF
Git blob SHA values matched their accepted test-source manifest;
the native Windows checkout source SHA matches the exact
LF->CRLF byte mapping. Worktree remained clean.
This CI success is for the explicit test-owned cancellation slice,
not Windows wrapper forced kill, unknown-outcome replay, paid-model
operation or full D3B confinement. A docs-only follow-up needs its
own independent CI result.
