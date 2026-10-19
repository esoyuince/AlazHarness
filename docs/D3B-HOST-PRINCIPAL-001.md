# D3B-HOST-PRINCIPAL-001 — strict opt-in host-principal contract

Date: 19 October 2026. Branch: alaz/d3b-host-principal-7a19
Base: 62a0fc9062408ec21bf5f4a8b17f7702e1499c57
(previous combined IPC+budget exact-code GitHub local-ci SUCCESS).

**Status: PARTIAL / NEGATIVE-ONLY COMPONENT PASS.**
**Real different host-UID broker + Gateway: NOT RUN.**
**Full D3B: NOT ACCEPTED.**

## Trust boundary and scope

Before this slice, the actual Gateway and provider broker used the same
host UID 1000. A different numeric UID inside a fresh user namespace is
not proof of different host ownership. Gateway-controlled ledger changes
cannot reset the private budget, but same-UID host code is still an
independent filesystem modification risk.

The new default-OFF component requires a trusted, pre-provisioned host
principal contract, exact field list/version, distinct nonroot broker and
Gateway host UIDs, designated group and initial host user namespace ID.
The broker process UID/EUID, GID/EGID, empty supplemental groups and
namespace must match. Budget folder is owned by broker UID mode 0700,
budget DB mode 0600; selected Unix socket directory is broker UID and
shared designated group mode 0710, selected socket mode 0660. No broad
group directory-write grant is accepted. SO_PEERCRED is checked for the
expected opposite principal; socket identity is checked again after
connect. Wrong owner/group/permissions, symlink, changed inode or
missing prerequisites must fail closed.

BrokerLink and BrokerConfig opt-in accept principal_contract; legacy
same-UID mode remains untouched when the field is omitted. The
trusted operator must provision a dedicated broker host principal and
the exact filesystem layout. No code here creates accounts or changes
the host UID, runs sudo, or installs a setuid helper. The system nobody
account was only inspected as a disposable test identity and is not
recommended as a production broker identity.

## Current evidence

- Windows host-principal policy: 30/30 unit tests PASS.
- Windows broker-wiring/negative contract: 10/10 PASS.
- Windows current native negative-receipt assertions: 4/4 PASS.
- Existing broker egress/client/protocol/lifecycle focused tests:
  43+12+17+3 PASS (75 unique tests, separate from the new 44).
- Prepared, unprivileged Linux Python3.14.3 with explicit broker test
  opt-in: 42/42 PASS, skip0. The five real local IPC/HTTP tests are
  included and use legacy identity; they DO NOT test two host UIDs.
- Real unprivileged Linux negative-only proof:
  evidence/d3b-host-principal-7a19/native-denial-hp7a19b.json:
  8/8 negative checks/cleanup PASS_DENIAL_ONLY. Owned temporary paths,
  no real model/provider/host services, current four source SHA256 pins.
  The first unpinned native-denial-hp7a19.json is retained as historical
  diagnostic, not counted as another eight checks.
- Historical IPC+budget Gateway 4 native receipts remain scoped to
  the original accepted code commit 29f6a353799dcdf0279ebcabf44593fbcbcfa160;
  the updated historical acceptance test checks its original Git blobs,
  not this new source's bytes.

A privileged alternate-UID test process invocation was blocked by the
desktop execution platform's safety check. No workaround, elevated system
permissions, account edits, or root-level host operation was pursued.

## What remains OPEN

1. Current ipc_view.prepare() requires the socket UID to match Gateway
   UID, mode 0600 and parent mode 0700. This is incompatible with the
   new split-principal socket 0660 / group-traversal parent 0710.
   Compose an explicitly versioned principal-aware IPC projection in a
   later sandboxed test branch without relaxing the legacy path.
2. Trusted host launch/bootstrap and actual Gateway worker need a
   bound, separately authenticated principal setting and selected
   broker socket identity; then re-verify original grants and retries.
3. Real positive test needs two distinct host UID processes, fixed
   budget owner, denied Gateway budget reads/writes/deletes/replaces,
   selected socket allowed, other socket paths denied, peer creds,
   broker restart/rebind/kill/ACK-loss/replay, and current source freeze.
4. Privileged host administrator, mutable host export, process FD
   inheritance, and paid-provider invoice/token costs remain separate
   trust and acceptance boundaries.
5. Do not enable real/paid model, agent memory, production defaults,
   M1/M2, or merge to main based on this scoped component.

Product modules modified: provider_broker.py and provider_egress.py.
New strict preflight: packages/claw-hermes/host_principal.py.
Negative runner: scripts/qa/principal_denial_linux.py.
New tests: tests/test_host_principal*.py.
Windows full unittest 2063/2063 exit0, five Linux-only skipped; full log evidence/d3b-host-principal-7a19/full-standard-windows.txt. Final staged-source static check PASS: 2063 tests discovered, 1489 tracked text files inspected, 2 gitlinks, exit0. Final post-cross-OS-custody-fix full unittest again 2063/2063 exit0 skip5 (210.215 sec) recorded in evidence/d3b-host-principal-7a19/full-standard-windows-final.txt. Git and exact-commit CI pending.

No personal profiles, server/host configuration, user accounts, deployed
services, real provider, background agent or main have changed.

## Native receipt byte custody (Windows vs Git/Linux)

Stage/checkout byte-pair receipts:
evidence/d3b-host-principal-7a19/source-custody.json (all four PASS).
The four native proof inputs were measured on the WSL-mounted Windows
worktree with CRLF endings, while the repository stores Python source as
LF. For ONLY these four path-bound SHA-256 entries, the read-only
evidence checker accepts either the exact original native hash or an
LF-only file whose exact LF->CRLF byte transformation reproduces the
original digest. The entire remainder of the historical evidence
retains unchanged exact-source checks; unknown source drift still
fails. This is a content-equivalence exception for newline bytes,
not a two-UID positive test or a changed native receipt.

## Exact-code GitHub CI observation

Published code commit a5e9afca5e5d24e5422b251a11c3e642b933e68d
on origin/alaz/d3b-host-principal-7a19. Its parent is the independently
accepted IPC+budget slice 62a0fc9062408ec21bf5f4a8b17f7702e1499c57.
All four current negative-source Git blobs were checked against their
precisely SHA-matched native CRLF/Git LF representations; working tree clean.
GitHub alaz/local-ci exact-code status **SUCCESS** (id 56697273855,
2026-10-19T14:29:19Z). New 44 offline tests independently PASS on both
Windows and unprivileged Ubuntu Linux. No positive separate-host-UID
Gateway/broker process test was run. A later docs/status-only follow-up
commit needs its own independent GitHub CI observation.
