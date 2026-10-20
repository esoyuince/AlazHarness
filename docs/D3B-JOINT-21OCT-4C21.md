# D3B joint integration — 21 October 2026

Active branch: `alaz/d3b-joint-21oct-4c21`.
Workspace: `C:\Antigravity\AlazHarness\scratch\worktrees\d3b-joint-21oct-4c21`.
Job: D3B-JOINT-21OCT-4C21. Scope: joint regression of two completed corrections.
Full D3B, a real two-host-UID Gateway/broker deployment and IPC v2 mount: NOT ACCEPTED.

## Integrated work

Startup parent: `c03351b5f976fc527270f95376384d7e54e4e99d` (code `456e6f3`).
IPC custody parent: `95e80ac9ff75844e7d4a46dc6c64b13b2cf0f115` (code `bbc0df0`).
Both parent worktrees were clean and are left untouched. The default root has
unrelated work, preserved rather than reset, cleaned or folded into this merge.

The broker CLI now supports an explicitly pre-provisioned principal directory
without changing the legacy fresh-directory rule. Acquired-listener cleanup,
no-clobber ready/shutdown publication and local Gateway identity checks are
retained from the startup parent. The IPC preflight now holds a detached
validated principal and rejects inconsistent directory/socket observations;
those corrections are retained from the custody parent.

No product-code conflict occurred. There were two conflicted paths:
`status.md` and `tests/test_d3b_integration_acceptance.py`. Both status histories
are kept, with the new continuation pointer first. The historical acceptance
checker is exactly the independently tested custody-parent version, including
missing-source and changed-blob rejection. New current-code acceptance is
separate in `tests/test_d3b_joint_acceptance.py`; it requires NEW native runs,
exact source sets and hashes, positive controls, explicit denials and cleanup.
An empty check set, truthy integer, missing pin or altered source hash fails.

`product-integration-audit.json` verifies that the six reviewed runtime files
match their intended parent. Permission rules, namespace maps, upstream pins,
accounts and production defaults were not broadened. Inherited before/after
failure evidence is retained with its original bytes and original scope.

## Fresh native execution on the combined source

The following runs were executed afresh, unprivileged, on Ubuntu WSL, with
317 selected source/config/test files unchanged across the whole group.
Their individual source manifests are checked as well.

- Broker CLI: 23 checks PASS_SCOPED. Real process, one authenticated local
  Unix-socket ping, wrong-principal refusal, normal shutdown and cleanup.
- Socket metadata: 7 checks PASS_SCOPED_METADATA. Real socket inode and mode
  changes at injected timing; no second observed UID and no mount.
- Principal admission: 8 checks PASS_DENIAL_ONLY. Same-UID budget/socket/peer
  rejection; no implicit provisioning or provider attempt.
- Existing kernel confinement: 24 checks and 5 startup refusals PASS. Positive
  endpoint controls, selected broker allowed, host pathname/abstract/TCP
  blocked, inherited descriptors closed, child restrictions and cleanup.
  This is the existing v1 same-UID projection, NOT a v2/two-UID certificate.

The four new receipt paths and commands are indexed by
`evidence/d3b-joint-21oct-4c21/native-run-summary.json`. Old receipts are never
rewritten or relabeled as joint execution. Source snapshots are saved under
`sources-before-native.json` and `sources-after-native.json`.

## Standard regression and remaining work

Full Windows regression: **2125 total, 2120 PASS, 5 SKIP, zero failures/errors**,
exit 0; 245.151 seconds of unittest execution. Linux selected regression:
**175/175 PASS, zero skips**, including the five actual IPC/HTTP private-budget
cases skipped on Windows. The tests use a local scripted provider and synthetic
Gateway ledger, not paid inference or a real two-UID Gateway deployment.
The 56 IPC tests, 19 startup cases, 44 principal cases and other focused groups
are overlapping selections from the full inventory, not additive totals.

All 317 selected source/config/test files remained unchanged across native
runs, Linux selections and the full Windows suite. Fifty inherited evidence
files match their parent index bytes exactly. Local staged static CI PASS,
2125 tests discovered; this does not stand in for execution or remote CI.
Fresh raw/structured results are in `evidence/d3b-joint-21oct-4c21/`.
There was no failed runtime/test group in this integration; the two Git merge
conflicts are documented separately. Per-parent failed tests remain preserved.
The local merge and exact final source/evidence custody are recorded below.

The still-open implementation is a trusted two-host-principal launch path and
an appropriate socket projection. The existing rootless namespace maps only
the Gateway UID, the principal client requires the pinned host user namespace,
and the v1 synthetic socket parent is Gateway-owned 0700 rather than the
principal broker-owned 0710 path. None of these constraints is removed by
merging the two fixes. Do not enable v2 by deleting the gate, accept unmapped
numeric overflow IDs, widen the v1 permissions or bypass the prior privileged
execution denial. A pre-provisioned, authorized isolated test environment is
required before the positive two-UID runtime acceptance can be executed.

Next product gate: implement and bind the trusted launch/projection path, then
run real Gateway + separate broker, budget-file access denial, selected socket,
peer credentials, restart/rebind and ACK-loss/replay cases on the exact source.
This job creates no privileged bootstrap, system account, production service,
real model request, automatic agent loop, main merge or GitHub push.
