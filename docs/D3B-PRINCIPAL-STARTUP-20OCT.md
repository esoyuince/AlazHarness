# D3B principal startup repair — 20 October 2026

Branch: `alaz/d3b-ipc-principal-20oct`. Base: `4d86f30`.
Status: scoped startup/lifecycle repair; full D3B NOT ACCEPTED.

## Actual defects repaired

The command-line lifecycle required an absent output directory, while the
principal-aware server required the same directory to be host-provisioned.
The principal CLI therefore could not start through its real entrypoint.
The CLI now keeps the absent-directory rule for legacy mode and requires
an existing, empty, canonical principal directory with broker UID, designated
GID and mode 0710. It invokes the existing broker identity and path checks;
it never creates identities, guesses an owner, chmods the principal directory,
or adopts an old output. The server repeats its own admission checks.

Previously, start, ready-file publication and signal-handler setup were
outside the cleanup region. A failure after listener acquisition could omit
shutdown. They are now inside try/finally, with only an acquired listener
eligible for cleanup, and only installed signal handlers removed. A failed
startup before acquiring a listener grants no authority to remove another
process's socket. A shutdown receipt is published only after a ready receipt
was successfully published and the owned server has closed.

Ready/shutdown metadata uses a private temporary file, fsync and no-clobber
hard-link publication. Readers never observe partially written JSON through
the published filename; existing files/symlinks are not overwritten. A local
filesystem supporting that operation is required; there is no unsafe replace
fallback. The parent directory must remain under trusted host control.

The opt-in broker client now validates its own Gateway UID/EUID/GID/EGID and
pinned host user namespace before socket inspection or connection. A mismatch
or unavailable namespace produces `broker_gateway_principal_refused` before
sending. Legacy clients retain their previous behavior. This is not a way to
accept overflow IDs or to pretend a user-namespace remap is another host UID.

## Evidence and reproducibility

Evidence folder: `evidence/d3b-principal-startup-20oct/`.

- New regressions: 19/19 PASS on Windows and unprivileged Ubuntu. These test
  actual CLI/client code with mocked process identity/server boundaries;
  they are not positive two-host-UID execution evidence.
- Before product edits, the portable regression run had 5 PASS, 11 FAIL and
  3 ERROR. The earlier Windows fixture run is also retained. Its four
  Unix-asyncio mock setup errors were corrected with create=True; assertions
  were not relaxed. Files: `regression-before-fix*.txt`, `fixture-correction.json`.
- Actual unprivileged Linux CLI: `native-cli-001.json`, 23/23 checks PASS_SCOPED.
  A real broker process receives exactly one authenticated AF_UNIX ping,
  rejects invalid principal admission, exits cleanly on its owned SIGTERM,
  removes its socket, and has zero physical provider attempts. No forced
  cleanup; temporary files removed; five input sources unchanged before/after.
- Fresh current-source negative-only principal proof: 8/8 PASS_DENIAL_ONLY,
  `evidence/d3b-host-principal-7a19/native-denial-startup-20oct.json`.
- Current-source legacy IPC kernel proof: 24 checks and 5 startup refusals PASS,
  `evidence/d3b-integration-19oct/kernel-principal-startup-20oct.json`.
  Only selected test sockets are reachable; inherited descriptors and host
  paths are excluded; private loopback/runtime IPC still work; cleanup passes.
- The old native receipts remain immutable. Current-source tests now point
  to new actual executions instead of applying stale source hashes to new code.
  Cross-platform exceptions allow only exact LF/CRLF representations of the
  specifically named unchanged files, never arbitrary source drift.
- Full Windows regression: 2099 total, 2094 PASS, 5 explicitly Linux-only
  SKIP, exit 0; unittest runtime 210.648 seconds. All 314 selected source files
  are unchanged before/after. Full output: `full-windows.txt`; measured source
  manifest and terminal outcome: `full-windows-result.json`.
- Staged local static CI: PASS, 2099 discovered, 1509 root files inspected,
  exit 0. This is separate from execution and is not GitHub CI.
- Twelve native/staged source representation checks PASS in
  `staged-native-source-custody.json`. No original native receipt was rewritten.

Linux CLI reproduction, from a clean test worktree, with a NEW output filename:

```text
python3 -I -B scripts/qa/native_principal_startup.py --output <this-worktree>/evidence/d3b-principal-startup-20oct/<fresh-name>.json
```

The runner must be unprivileged. It creates only owned temporary fixtures,
uses a dummy loopback provider route, and never calls a model or provisions
a user. Read an interrupted run's receipt and process state before rerunning.

## Remaining boundary and exact next work

IPC v2 `prepare` and `project` remain closed. The current rootless network
launcher maps only the Gateway UID/GID; an external broker UID is not in that
mapping. The projected socket parent is also a synthetic Gateway-owned 0700
directory, not the broker-owned 0710 directory required by the principal
contract. Opening that gate or accepting numeric overflow IDs would not solve
the security boundary. A trusted, separately provisioned launch environment
and a namespace-aware socket projection still require implementation and
positive native acceptance. Earlier privileged test denial was not bypassed.

No positive two-host-UID Gateway/broker run, current real Hermes Gateway run,
private-budget access-isolation proof, production activation, main merge,
paid-provider accounting or autonomous learning acceptance is claimed here.
No system account, service, upstream pin, root worktree or production state changed.

The older `principal_readiness.py` reports NOT_READY unconditionally on Linux;
it inventories the current process/tools but does not inspect a supplied
multi-principal deployment. Its output must not be used as proof no such
deployment exists, or as a positive readiness gate.

## Local delivery

Code and tested evidence commit: `456e6f3466c115bcaf62767e3b37d92d4de9e3f5`. No push or GitHub CI. The subsequent documentation/static-receipt commit carries the same runtime sources.
