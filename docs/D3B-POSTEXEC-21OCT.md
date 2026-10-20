# D3B broker post-exec admission — 21 October 2026

Branch: `alaz/d3b-principal-launch-21oct`. Starting commit: `47c70ea914dbc12d4ea2d39ef2a97a8a6b4a0139`.
Published main remains `cc7ceba`. This increment is not a privileged install or positive two-host-UID acceptance.

## Confirmed gap and implementation

The initial launcher verified its identity/capabilities before exec, then
entered the legacy broker CLI. The new process did not verify the complete
post-exec kernel state and did not receive the expected config digest. Its
argv digest also did not bind the expected principal or private config digest.
Six new command-binding tests were run before edits: one passed and five
failed. Their exact unchanged bytes pass after the correction. The first
failure output remains in `binding-before.txt`; it is not presented as success.
This was an incomplete, unactivated launch path, not a claim of a demonstrated
production exploit or a successful privilege transition.

The launcher now executes only `scripts/run_principal_broker_target.py` with
isolated Python flags and explicit canonical principal JSON, config path,
config SHA-256 and output path. Its existing argv digest binds all of these
values. The new target script is also included in trusted-install checks.
Old command digests fail closed and must be regenerated; there is no legacy
argv fallback. The ordinary `run_provider_broker.py` entrypoint is unchanged.

`packages/claw-hermes/principal_target.py` verifies current kernel real,
effective, saved and filesystem UID/GID; empty supplemental groups; initial
host maps and expected user namespace; all five capability sets zero; one
thread; no_new_privs; and inherited seccomp filter mode. Strictly typed fields
cannot be substituted with truthy booleans or incomplete capability dictionaries.
These checks happen before private configuration is read or a broker socket exists.

Filter mode 2 only indicates that a filter exists; it does not identify its
rules. The target therefore loads and installs the existing deny filter itself,
closes ambient descriptors, and rechecks kernel state before reading config.
This does not prohibit the broker's intended provider egress and is not a
complete network sandbox. The target checks the expected config hash before
parsing and checks exact principal equality. It then uses the real BrokerConfig
validator and existing deployment gates for private budget/prepared empty
socket directory, followed by a final kernel-state check. No provisioning,
shell command, alternate identity, automatic retry or permissive fallback exists.

The target invokes the existing asynchronous broker lifecycle only AFTER
synchronous admission and descriptor cleanup. Creating the event loop first
would create internal descriptors that cleanup would close; ordering is tested.
Diagnostics contain an exception type and phase, not config contents or
arbitrary exception text. Trusted interpreter, libraries, imported source and
immutable installation remain supervisor prerequisites, not established by
checking them after import.

## New evidence, not inherited acceptance

All new run logs are under `evidence/d3b-postexec-21oct/`.

- `binding-before.txt`: six tests, five failures and one pass before changes.
  `binding-after.txt`: the same six test methods and bytes pass after changes.
- `target-first.txt`: initial 24 mocked/kernel-boundary target tests pass.
  One test was then strengthened to assert malformed JSON never reaches
  preparation (rather than injecting an exception there). Final focused logs
  include the strengthened test. No product behavior was changed to hide a
  failed assertion.
- `focused-results.json`: Windows 80/80 PASS and Linux 80/80 PASS, no skips.
  This includes existing principal tests and 33 new tests: six command binding,
  24 target behavior, three current-receipt validators. These selections overlap
  the standard suite and are not additional tests added to its total.
- `native-postexec-001.json`: 16/16 PASS_SCOPED_POSTEXEC. Real unprivileged
  subprocess, real exec preserving PID, real no_new_privs/seccomp inheritance,
  a positive recvmsg EBADF baseline changing to EPERM after the actual filter,
  target rejection of the wrong expected host UID, and a Python audit-hook
  observation that the owned config fixture was not opened. The actual target
  CLI also refuses without creating a broker output directory. Owned child
  terminates; temporary files are removed; parent kernel state is unchanged.
- The native observer is UID1000. Broker UID11000 is DECLARED expected data and
  was never observed as a running identity. No actual UID switch was performed.
  No broker service/model/HTTP provider was started. The successful native result
  certifies inheritance and refusal, not positive broker target admission.
- The old 13-check launcher native suite was rerun on the modified sources:
  `evidence/d3b-principal-launch-21oct/native-unprivileged-postexec-001.json`,
  all13 PASS. Its current-source checker points to this fresh execution.
  The original native-unprivileged-001.json remains byte-for-byte in Git.
- Ten source pins bind the new native report before/after execution; six bind
  the refreshed launcher report. Representation exceptions are limited to
  named, unchanged historical Windows CRLF/Git LF text files, not arbitrary drift.
- Full standard regression is recorded in `full-windows-result.json` only once
  its request is terminal. Static test discovery is not execution or remote CI.

## Preserved safety boundaries and next acceptance

The existing broker lifecycle/transport, budget authority, host-principal,
network, filesystem and IPC projection modules are unchanged. Both IPC v2
prepare/project gates remain closed. Main and all earlier worktrees remain
untouched. There is no account creation, service change, privileged launch,
root/user-namespace workaround, paid model call, push or main merge here.

The next positive gate STILL requires a separately authorized and prepared
trusted installation: root-controlled interpreter/source/dependencies and
ancestors; distinct real nonzero Gateway/broker UIDs; the designated shared
socket GID; broker-owned0600 config, private0700 budget with0600 database and
empty0710 socket directory; expected initial host user namespace and pinned
command/config digests. This developer-writable Windows checkout is not that
installation. The earlier privilege denial is not bypassed.

In that authorized environment, execute the actual broker launcher, observe
post-exec UID/capabilities and peer credentials, then qualify Gateway-side
selected-socket projection and denied budget reads/writes. Native two-UID
transport, target success, private-file access isolation, v2 mount, full D3B,
M1/M2 and production readiness remain NOT ACCEPTED. Avoid accumulating more
readiness-only checks instead of arranging that missing execution environment.

## Primary mechanism references

- https://docs.kernel.org/userspace-api/no_new_privs.html
- https://man7.org/linux/man-pages/man2/execve.2.html
- https://man7.org/linux/man-pages/man2/seccomp.2.html

These describe OS behavior. Only the explicitly scoped run receipts above are
execution evidence for this code.

## Final local verification

Full Windows standard suite: **2200 total /2195 PASS /5 SKIP /0 failures /0 errors**, exit0; no timeout. All328 source/config/test files are unchanged before/after. The five skipped cases are existing opt-in Linux IPC/HTTP tests; they were not rerun or counted as passes in this slice. Windows and Linux selected principal groups both pass80/80, and are overlapping subsets, not additive totals. Native post-exec16 and refreshed launcher13 checks pass within their explicitly unprivileged scopes.

The first five failing command-binding cases, the unchanged test-byte hash, all final logs and both fresh native reports remain inspectable. Sixteen current native/index source entries were verified; the earlier native receipt remains identical to its original Git blob. Nine existing broker/isolation modules remain unchanged. Final status, report, raw logs and source manifests are part of the local feature checkpoint; no push, remote CI or main merge. Read Git HEAD for the checkpoint hash rather than a self-referential value.
