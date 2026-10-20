# D3B principal launcher — 21 October 2026

Branch: `alaz/d3b-principal-launch-21oct`.
Base: `cc7ceba8f850da7652a647e984cbae2c45c8fdea` (published main).
Worktree: `scratch/worktrees/d3b-principal-launch-21oct`.
Status: broker-side implementation and scoped unprivileged tests; NOT positive two-UID acceptance.

## Implemented boundary

`packages/claw-hermes/principal_launch.py` and the explicit
`scripts/run_principal_broker.py --contract <path>` entrypoint implement a
one-shot broker launch. They are NOT installed as setuid helpers and never
acquire privileges or invoke sudo. An independently authorized supervisor
must already be host root and provide a trusted immutable installation and
pre-provisioned deployment. This task did not execute a privileged controller.

The closed contract fixes the existing broker entrypoint, Python executable,
config/output paths, config SHA-256 and exact argv digest. It requires distinct
nonzero Gateway and broker UIDs through the existing host-principal policy.
A Gateway role or arbitrary command is rejected; this path cannot serve as an
unconfined Gateway fallback while projection is unfinished.

Admission requires initial host UID/GID maps, the declared host user namespace,
root real/effective/saved/filesystem IDs, one thread and required controller
capabilities. Root-owned, non-group/world-writable code and ancestors are
checked. The root-owned 0600 launcher contract and broker-owned 0600 config
are read through bounded no-follow file descriptors, checked against metadata
before/after and the named path. Broker configuration uses the existing
BrokerConfig validation; its principal must match and a private budget is
mandatory. The existing 0700 budget / 0600 database and empty 0710 socket
directory checks are reused. The launcher creates no users, permissions,
budget or socket directory and never adopts an old ready/socket directory.

The dedicated process enables no_new_privs, disables retained capabilities,
clears ambient capabilities and supplementary groups, drops the capability
bounding set, and sets all real/effective/saved GID and UID slots to the broker
identity. It then clears capabilities and verifies all four kernel UID/GID
slots, all five capability sets, empty groups, unchanged host namespace/maps,
PID, thread count and no_new_privs. No privileged transition was performed
by this task; syscall ordering and failure handling are tested with mocks.

Only pipe or /dev/null standard descriptors are allowed. Other inherited
handles are closed. The deployment is checked again after identity reduction.
The existing seccomp-denial filter is reused, followed by exec of the fixed
broker with isolated Python flags and an explicit small environment. Errors
are fatal; no shell, restart, alternate role or permissive fallback exists.
Diagnostics contain an exception type, not secret content or command arguments.

## Trust assumptions and open acceptance

This is a launch primitive, not a privilege-grant service. The invoking Python
interpreter, its standard library/dependencies, imported code and dynamic-loader
configuration MUST already be trusted by the authorized supervisor. Validation
after Python imports cannot retroactively secure a tampered bootstrap. Do not
run a privileged Python process from a developer-writable checkout; the current
Windows/WSL checkout is intentionally not an accepted privileged installation.

The trusted host and broker are outside the hostile Gateway boundary. File
metadata rechecks are not atomic snapshot/lease protection against a trusted
host or broker modifying their own paths. The fixed executable is checked
under root-controlled ancestry; no general executable delegation is provided.
Dumpability may reset at exec and is not claimed as enduring process isolation.
The broker is allowed provider egress: reusing the seccomp filter does not turn
this broker launcher into a no-network sandbox.

Existing host-principal, broker, IPC, network and filesystem code is unchanged.
Both IPC v2 prepare/project gates remain closed. The existing rootless launcher
creates a user namespace and maps only the Gateway UID, which is incompatible
with the pinned host namespace and a distinct external broker UID. A trusted
Gateway launch/projection path preserving host identity and projecting only
the selected broker socket still needs implementation and separate acceptance.

Positive real privilege reduction, post-exec broker identity/capability proof,
real two-UID Hermes Gateway/broker, budget file-access denial, peer identity,
restart/rebind/replay, production release and full D3B remain NOT ACCEPTED.
No account or service provisioning, privileged command, model call, new
permission, main modification, publication or deployment occurs in this slice.

## Test evidence

All new evidence is in `evidence/d3b-principal-launch-21oct/`.

- `unit-pass-windows.txt`, `unit-pass-linux.txt`: 39/39 each. These cover the
  real validation/orchestration code with mocked privileged/kernel boundaries.
  Passing mocks are not proof of a real UID transition.
- `native-unprivileged-001.json`: 13/13 PASS_SCOPED_UNPRIVILEGED on Linux UID/GID
  1000. Actual CLI/root-admission rejection, exact current-process observations,
  real inherited socket closure in a child, socket-stdio rejection, parent
  socket preservation, unchanged temporary fixture, source pins and cleanup.
  No privilege-changing syscall, account or second host UID was used.
- Three offline receipt tests bind the exact check set and six source hashes,
  and require every broader acceptance flag to remain false. They validate an
  already executed receipt; they are not additional native process trials.
- Initial failed test outputs are retained: `unit-first.txt` (missing mocked
  Windows geteuid), `unit-expanded.txt` (Mock-wrapped Path overlap fixture), and
  `unit-final-windows.txt` (Windows expected path representation). The latter
  name is historical and does NOT mean it passed. Both correction records
  explain the test-fixture repairs; no assertion was deleted and product code
  was unchanged by those fixture corrections.
- Full standard regression is tracked separately in `full-windows.txt` and
  `full-windows-result.json`; its result is only claimed after termination.
  Static discovery is not a full test execution. Counts overlap, never sum
  focused groups into the full standard total.

## Exact continuation

Finish and review the native positive broker transition in an explicitly
authorized, pre-provisioned isolated trusted installation before accepting the
privileged path. Do not bypass a denied privileged operation via another
connector, identity mapping or helper. Continue Gateway network/mount projection
as a separate narrow change; preserve selected-socket ownership and private
budget boundaries. Keep existing v1 behavior and closed v2 gate until exact-source
positive and negative native acceptance exists.

## Primary references used for design

- Linux no_new_privs: https://docs.kernel.org/userspace-api/no_new_privs.html
- Host/user namespace identity: https://man7.org/linux/man-pages/man7/user_namespaces.7.html
- Capability sets and UID transitions: https://man7.org/linux/man-pages/man7/capabilities.7.html

These references explain OS mechanisms; they are not acceptance evidence for
this implementation. The checks and remaining unknowns above remain controlling.

## Final scoped verification

Full Windows standard suite: **2167 total / 2162 PASS / 5 SKIP / 0 failures**,
exit0. The five skips are existing opt-in Linux transport cases, not treated
as passes. Linux launcher selection: **42/42 PASS / 0 SKIP** (39 behavior
contracts + 3 receipt tests). Separate actual unprivileged Linux checks:
**13/13 PASS_SCOPED_UNPRIVILEGED**. These overlapping scopes are not additive.

All **322** source/config/test files remained unchanged during the full suite
and were rechecked afterward. No pre-existing runtime module changed. Native
source pins also match the staged Git blobs, including only the two explicitly
identified historical LF/CRLF representations. Local static gate passes with
2167 discovered tests; it is not remote CI or privileged runtime acceptance.

All submitted test receipts are terminal. This checkpoint is a local feature
commit only, not pushed or merged to main. Main remains cc7ceba. The original
failing fixture outputs and their corrections remain available. The final
commit hash is Git HEAD of this worktree; summary.json records the source/test
boundaries without asserting an unknown self-referential commit hash.
