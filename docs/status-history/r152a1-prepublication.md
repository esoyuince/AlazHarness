# AlazHarness - status

## R152A1 - current Landlock and retained native lifecycle - IN PROGRESS

- Active branch: alaz/d3b-retained-acceptance-r152a1.
- Starting main: 8aae47fb7efa94fbfb45b22018747d4bb3178c2a; exact alaz/local-ci SUCCESS verified.
- Worktree: C:\Antigravity\AlazHarness\scratch\worktrees\d3b-retained-acceptance-r152a1.
- Current checkpoint: 2026-10-25T21:51:06.722707+03:00.

### Completed and preserved

R151A1 remains SCOPED_KERNEL_PASS (4/4 self-identity cases). Root user changes, published main and native source pin remain untouched.

R152 native001 completed FAIL with exit 1. The original guard rejected an inherited descriptor before installing Landlock, after all 14 first native lifecycle checks passed, including physical closure of all three stores and caller lease release. No timeout or signal; the owned group is empty; source bytes are unchanged. Its original raw results and failed temporary tree are retained. See native001/diagnosis.json and bridge-terminal.json.

### Frozen next experiment

Candidate002 has four QA scripts, independently reviewed. After the initial unconfined native lifecycle closes normally, an ordinary fixed QA exec starts a fresh bootstrap. It applies unchanged current Landlock before native imports, then a second fixed QA exec performs retained reopen, saved-result replay, one new finite request and normal closure. Native/product/OS functions remain original; only the declared AIAgent computation fixture is doubled.

Both fresh trees are kept through all case/audit checks, final dependency verification and confirmed empty process groups. Only then may the owning transport remove them. The dependency's known IPv6 probe remains denied and is accepted as a blocked optional import probe only by exact pinned source/function; unexpected audit events fail.

native002 bundle: 5a68caa5ec8e2a8aff359e0b08be2561328d6ee421b429e26b1fcb5a3a772dc9; 823 files, 6090489 bytes. Execution request: 561507f5-f087-4d65-85d4-24685468d616. State: COMPLETED_FAIL; see native002/diagnosis.json. Never replay an attempt with execution-start.json; poll its original receipt to terminal.

### Scope and next gate

This tests the ordinary-user filesystem component and native retained lifecycle through QA execs. Initial lifecycle is unconfined; second owner is Landlock confined. It does not execute gateway_retained_launch.target_main or establish full projection, separate UID, zero capability bounding set, namespace/network isolation, HTTP, real-model cost or full D3B acceptance.

Current-source full projected execution remains NOT RUN: no qualified current privileged installation/supervisor exists. Earlier denied privileged actions are not retried. No root, installer, mount or service action is part of R152.

Next: execute native002 once, inspect complete terminal evidence, document failures and exact accepted scope, verify required regression/static gates, then publish selected files only after exact-SHA CI.

Parent: docs/status-history/r152a1-parent.md.
Work log: docs/status-history/r152a1-work-log.md.

### native002 failure checkpoint — 2026-10-25T21:52:56.829896+03:00

Original Landlock applied successfully in the fresh bootstrap and remained active through the second same-PID exec. Native prepare_runtime then failed when aiohttp/stdlib mimetypes read /etc/mime.types. No timeout/signal; group empty; failed profile/tree retained; bytes unchanged. native002 remains FAIL. Candidate003 makes one QA-only readonly export addition for that canonical file; no broader /etc grant, product change or guard weakening. New execution has not started.

### Frozen native003 — 2026-10-25T21:53:21.981739+03:00

Bundle ff23ecb92b3c00de7244163ea8ef3b5fc62e6ca636d34314a4b9239b2980de60, 823 files. Four final QA hashes independently reviewed. Request 32533e48-9cc6-4499-80de-d38d3a48a6b1; PREPARED_NOT_RUN. Poll this request after dispatch; never replay. native001 and native002 remain recorded failures.

### native003 completed — 2026-10-25T21:56:05.665289+03:00

SCOPED_KERNEL_AND_RETAINED_LIFECYCLE_PASS: normal and controlled-error both exit0/PASS; source/dependency bytes unchanged; both groups empty without timeout/signal; successful trees removed after all checks. Original failure records/trees remain. Independent recorded-result corroboration and publication gates are next. Full projected launcher and full D3B remain NOT RUN.
