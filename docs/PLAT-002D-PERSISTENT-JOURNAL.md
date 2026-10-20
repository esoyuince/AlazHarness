# PLAT-002D-RECOVERY — Persistent test-owned WSL lease evidence

Date: 20 October 2026.
Branch: alaz/plat-002d-persistent-20oct.
Base: 177d05e260072bd57dcc35a3ee0ae5b24aa734c3.
Decision: **Offline source/contract delivery ONLY; native persistent-journal
acceptance NOT RUN; full PLAT-002/D3B remains NO-GO.**

## Why this exists

The previous PLAT-002D native wrapper-loss trials have immutable FAIL
receipts. In run 01 Windows never obtained READY; in run 02 an owned
Windows wsl.exe was terminated after READY, but the external Linux
auditor found no durable terminal lease record, and a separate guest
process inspection timed out. Neither outcome proves guardian,
worker and descendant were reaped. Even if WSL is currently stopped,
that is not proof of the missing shutdown history.

The Linux-versus-Windows historical SHA custody issue was repaired
separately on the predecessor branch, which passed exact source and
documentation GitHub CI. That code-quality success MUST NOT be
misreported as native wrapper-loss acceptance.

## Implemented test-only journal

scripts/qa/wsl2_persistent_lease.py specifies a strict versioned
one-run lease schema:

- PREPARED: bound 24-hex run ID, 64-hex nonce digest, 64-hex
  source SHA256, Linux boot UUID, nonroot issuer UID/PID/start tick,
  CLOCK_BOOTTIME nanoseconds, fixed seven-second maximum lease.
- READY: exact same immutable PREPARED fields plus guardian,
  worker and grandchild PIDs and independent Linux /proc birth ticks.
- TERMINAL: READY plus a terminal timestamp at or after lease
  expiration, named expired/unknown state and explicit booleans
  asserting child and grandchild were reaped and own cleanup verified.
- All records carry UNKNOWN_DO_NOT_REPLAY, realModelCalls=0,
  agentToolStarted=false and fullD3BAccepted=false.
- Extra/duplicate fields, invalid types, NaN, multi-line frames,
  CRLF wire input, changed boot/run/nonce/source, false security
  claims, PID collisions and timestamp/lease drifts are refused.
- State reconciliation requires an independent boot/clock and exact
  PID/birth-tick observation. Boot change, missing terminal,
  partial PID inspection, PID reuse or still-live PID remain UNKNOWN.
  Even an apparently valid terminal with all three old PIDs absent
  remains RECORDED_PIDS_ABSENT_ORPHAN_CLOSURE_UNPROVEN: an orphan
  with another PID is NOT excluded. The external effect is NEVER
  marked successful or replayable.

## File and permission boundary

The only intended journal root is the fixed name
.alazharness-qa-lease-v1 in the unprivileged WSL user's
/home/<user> directory, **outside /tmp and Windows DrvFs**.
The Linux kernel, current user/home ownership and ext4 backing
must be checked before a native disk operation.

The sole opt-in write action is --mode prepare, which creates
run-<24-hex-id>/prepare.json and starts **no worker**.
It requires ALAZ_PLAT002D_PERSISTENT_QA=1, the exact SHA of
the script being run, a never-before-used run ID and a valid nonce
digest. Root and run directories are required to be UID-owned
mode 0700; record files UID-owned mode 0600 and link count one.

Directories are opened/created relative to already verified
directory file descriptors. O_DIRECTORY, O_NOFOLLOW,
O_CLOEXEC, O_EXCL and strictly whitelisted file names
eliminate generic user paths and reject symlink/replay attacks.
Records use bounded exclusive writes, fsync(file) and fsync(parent
directory); newly created directory entries are fsynced too.
Interrupted writes become incomplete/unknown state, never a
completed transaction. No automatic cleanup removes existing
ledger or user data.

--mode inspect is read-only; it will not create a ledger,
start WSL or a child process, renew an old lease, terminate a PID
or silently retry. Historical run and nonce hashes must match.

## Precise limitations and native next steps

**Not implemented/accepted in this delivery:**
- A real Linux guardian issuing authenticated READY/TERMINAL
  records or testing the actual WSL ext4 persistence across exit.
- Watchdog process execution, tool/agent start, host-wrapper kill,
  actual Linux descendant/grandchild reaping after wrapper loss.
- A reliable complete process-tree/orphan scan or PID-fenced
  foreign-process separation beyond the known three birth ticks.
- Authenticated server/broker identity, a hostile same-UID writer,
  tamper-evident cryptographic journal or different host principals.
  A private UID-owned record is not a signature or security
  attestation against other processes running as that same UID.
- Host filesystem isolation, netns/Landlock, IPC projection,
  broker-owned budget, real Hermes Gateway, paid provider,
  macOS support or M1/M2 autonomous work.

Initial offline QA tests are in:
tests/test_plat002d_persistent_lease.py (pure strict schemas
and state machine) and tests/test_plat002d_persistent_io.py
(POSIX-only disposable TemporaryDirectory dirfd/open/symlink/hardlink/
O_EXCL/fsync behavior; skipped on Windows).
These tests do not access the WSL user's home.

The next native gate must first independently establish WSL guest
process/query health. Only with explicit bounded authorization,
evaluate an owned disposable Linux ext4 journal path and its
persistence, then a guardian lifecycle. Never overwrite or
retroactively relabel the earlier two FAIL/UNKNOWN receipts.

## Acceptance table

- Versioned PREPARED/READY/TERMINAL schema: implemented; offline QA.
- Durable exclusive file descriptor writer: implemented; Linux
  fixture QA / native WSL persistent home NOT RUN.
- Conservative unknown-outcome reconciliation: implemented; offline QA.
- Linux process-tree and forced Windows wrapper-loss closure: NOT ACCEPTED.
- PLAT-002D security completion, full D3B and M1/M2: NO-GO.

No real model calls, WSL startup, guest home writes, production
service changes, privileged operations, main merge or policy downgrade.


## Initial offline acceptance and source checking

Windows focused suite discovered 60 tests: 48 PASS, 12 POSIX-only
temp-fixture tests SKIP. The default root static validator reported
PASS: 2,351 Python tests discoverable, 1,567 root text files and
two pinned source gitlinks, exit0. Source LF SHA256 values for the
Python journal and two test modules are bound in the local evidence.
Native Linux POSIX temp-fixture tests will be independently validated
on GitHub Linux CI; this is not evidence of actual WSL home writes.
Exact code CI and full local root test are separate subsequent gates.
