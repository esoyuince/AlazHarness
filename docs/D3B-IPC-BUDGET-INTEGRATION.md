# D3B IPC projection + broker-private budget — scoped acceptance

Date: 19 October 2026. Branch: alaz/d3b-integration-19oct.
Base: budget 4d96b5ff45677907a8fb5ca215187de015f83e05 (exact CI SUCCESS);
other parent: IPC 436f3f792f50950b2f0984269d36627327441c52 (CI SUCCESS).
Dedicated worktree, not main. Both components explicitly opt-in.

## Security boundary

The same real Hermes Gateway PID enters a user/network namespace, a projected
private root with exactly ONE selected broker Unix socket, then Landlock
before actual Gateway execution. Broker/original aiohttp stays host-side.
Broker-owned private SQLite commits full exposure before HTTP send, never
automatically refunds lost replies/HTTP 500/restarts. Gateway SQLite cannot
authorize additional independent budget. No real external provider.

## Real native evidence — scripted localhost origin only

| Scenario | Fresh run ID | Persisted reservations | HTTP responses | Result |
|---|---|---:|---:|---|
| Normal | int19-normal2 | 4 | 4 | PASS |
| Token exposure cap | int19-limit2 | 3 | 3 | PASS |
| Candidate disconnected | int19-disconnect2 | 4 | 3 | PASS |
| Review revoked | int19-revoke2 | 3 | 3 | PASS |

All four real native Gateway runs are source-frozen, 189 files before and
after, identical manifests with canonical JSON SHA-256: a3ecb25c2778db24763627baafe3c6ee26168e02a8f39d89087397848037d2e4
Source code matches current local bytes; original Linux ext4 snapshotted
runtime used. Actual IPC projection, selected broker socket, detached old root,
combined netns/Landlock and private authority separately verified.

Fresh local owned kernel negative proof:
evidence/d3b-integration-19oct/kernel-int19-final1.json — PASS:
24/24 kernel/child access checks and 5/5 startup refusals. Preflight
proved test endpoints live. Child broker allowed 2 connections, extra
pathname/abstract/TCP host endpoints accepted 0; protected canary unchanged,
temporary roots removed. NO existing host services were used.

Prepared isolated Linux Python 3.14.3 + aiohttp broker focused unittest
with ALAZ_BROKER_NATIVE_TESTS=1: 42/42 PASS, skip0, including the five
real local Unix-socket/HTTP behaviors. A first WSL default run had 1 test
error because Windows .git worktree pointer is not Linux-resolvable;
the historical archive checker now falls back READ-ONLY to the same
mapped, validated Git metadata. No Git or host-wide config was altered.

Historical int19-normal1 outer report says PASS but recorded
ipcProjectionVerified=false. It was a false-positive classification
and is NOT accepted. It remains immutable in evidence, and new strict
outer classifier + 7 negative/positive unit tests reject it.
All original budget/IPC receipts remain bound to predecessor commits
and do not prove the merged source.

Current policy/receipt contracts:
tests/test_d3b_integration_contract.py and
tests/test_d3b_integration_acceptance.py. The latter checks the four
fresh native reports, source custody, and kernel denials without
starting a model or network listener.

## Local regression and release gate

Windows Python 3.14.3 / Node 24.19: **2019/2019** full unittest,
exit0, **five Linux-only skipped**; elapsed unittest 174.539 sec.
Fresh log: evidence/d3b-integration-19oct/full-standard-windows.txt.
Prepared Linux broker unittest **42/42**, exit0, no skips, log
evidence/d3b-integration-19oct/linux-budget-unit-final.txt.
Final staged-source static root CI: PASS, 2019 tests discovered,
1476 tracked root files inspected, 2 source gitlinks, exit0. The summary JSON retains SHA-256 for these
logs and all four acceptance receipts.

## Git publication and exact-code CI

Merge code commit 29f6a353799dcdf0279ebcabf44593fbcbcfa160;
parents 360da97698e33aa4fa3a8a211723247f294ee062 and
436f3f792f50950b2f0984269d36627327441c52.
All 189 source/config Git blobs match frozen native source bytes,
with only the explicitly SHA-verified C# CRLF/LF representation exception.
Clean dedicated worktree was pushed to origin on the own feature branch;
main and original user root worktree unchanged.

GitHub context alaz/local-ci: SUCCESS (status 56667429890,
2026-10-19T07:31:09Z) for that exact merge code commit. This result
is separate from both predecessor CIs. Any documentation follow-up
commit is tracked and verified separately, not silently assumed green.
Native tests never contacted a real/paid provider. No whole-product
acceptance follows from this narrow code CI.

## Deliberate open risks

Same OS UID between Gateway and broker persists: malicious same-UID
host code/administrator can alter broker-private files. No full PID/
host-process isolation or immutable export protection across a hostile
host writer. No actual model, tokenization, tariff/pricing, provider
invoice reconciliation or paid traffic. Arbitrary agent tool and
runtime IPC inheritance and all production profiles remain outside scope.
No active memory/skill promotion, M2 self-agenda, or general activation.

**Full D3B, full M1 and M2: NOT ACCEPTED.**
Main and existing users' environments unchanged.

## Repro boundary

From this dedicated worktree, use:
- Windows: python -B -m unittest discover -s tests -v
- Windows: python -B scripts/ci_check.py
- Prepared Ubuntu Linux: python3 -B scripts/qa/native_budget_ext4.py
  --ipc --scenario normal --run-id NEW-unique-id

Do not replay a possibly interrupted native run before inspecting its
receipt/process state. No real provider endpoint may be substituted.
