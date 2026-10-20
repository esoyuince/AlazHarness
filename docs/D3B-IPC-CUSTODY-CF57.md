# D3B IPC socket-custody correction — CF57

## Scope and ownership

Branch: `alaz/d3b-ipc-custody-cf57`.
Worktree: `scratch/worktrees/d3b-ipc-custody-cf57`.
Base: `4d86f3081791c1f444d1de256d7b266eec4af6f7`.
Status: LOCAL SCOPED PASS. Full Windows regression, focused Linux/Windows checks and owned-socket metadata tests PASS. Full D3B NOT ACCEPTED.

This is complementary to concurrent `D3B-PRINCIPAL-STARTUP-20OCT` in
`d3b-ipc-principal-20oct`. That writer owns broker CLI/transport/startup changes.
CF57 modifies only the IPC preflight, its tests, and historical evidence custody.
No files in the primary worktree, root mirror or another project were changed.

## Confirmed faults and implemented changes

`ipc_view.validate()` discarded the validated principal copy and returned the
caller's mutable nested dictionary. A later caller mutation could change the
already-validated broker UID. Version 2 now retains the detached validated
principal; version 1 keeps its original behavior.

`inspect_principal_socket()` checked owner/group/mode once, then separately read
an inode identity without comparing the observations. Rebind, socket-mode drift,
and parent-mode drift could therefore return mixed or outdated proof. The
middle read could also raise an unnormalized OS exception. The corrected path
copies the full directory/socket metadata before the inode observation, rechecks
it afterward, and requires both snapshots and the inode/type/owner/group/device
tuple to agree. Unavailable or inconsistent evidence is rejected; no retry is
performed. Returned proof is detached from mutable helper objects.

This is a consistency check, NOT an atomic filesystem snapshot, descriptor pin,
path lease or proof against an A-to-B-to-A change between observations. A future
mount/connection still needs its own trusted point-of-use verification. No
preflight result grants a mount: `mountAuthorized` remains false. The v2
`prepare` and `project` gates stay closed, and their ASTs are unchanged. This
correction does not claim an exploitable production bypass in the currently
mount-disabled v2 mode.

## Before/after evidence

All paths below are under `evidence/d3b-ipc-custody-cf57/`.

- The 15 new tests were run BEFORE the product correction. Initial failure is
  retained in `before-fix-windows.txt` and `.json`, together with the exact
  original source in `ipc_view.before.py.txt`. The unittest summary counts
  failing subtests, not 16 distinct test methods.
- The SAME new test bytes pass after the correction: 15/15, recorded in
  `fixed-new-windows.txt`. They are part of, not additional to, the 56-test
  Windows IPC group. The Linux IPC group also passes 56/56. The existing
  Windows host-principal group passes 44/44; these runs are not added to the
  full-suite total.
- One existing mock-call assertion now requires the two identical principal
  inspections instead of one. All its identity/output assertions remain.
- Native Linux before/after uses real, current-user-owned AF_UNIX socket inodes
  and directories. Controlled timing performs real unlink/rebind and chmod
  between the reads. The original listener stays open to exclude inode reuse
  in the rebind case. Original code missed all three mutation checks; fixed
  code passes all seven checks. See `before-fix-linux.json` and
  `fixed-linux-native.json`. The runner and new regression-test bytes are
  identical before/after; source SHA maps are verified before and after each run.
- The native observer is UID/GID 1000/1000. The alternate Gateway UID in the
  fixture is DECLARED data, not an observed process. This is metadata testing,
  not two-host-UID Gateway/broker communication. There were no mounts, account
  edits, privileged launches, real providers or paid calls.

## Historical evidence correction

The first full run finished, without timeout, with 2092 tests: 2086 passed,
5 skipped and 1 failure. The failure came from the old kernel receipt test
comparing its historic `ipc_view.py` hash against a newer working tree.
Its original three hashes match immutable commit
`29f6a353799dcdf0279ebcabf44593fbcbcfa160` exactly. Even the CF57 base had a newer
IPC hash. The test now reads that original Git archive, using the same checked
Windows/WSL metadata-path handling already used by the four historical Gateway
receipts. It requires exactly the original three paths and exact SHA-256 bytes;
there is no fallback to current files and no changed historic receipt.

Two additional tests ensure missing sources and changed original Git bytes fail.
The historical acceptance group passes 5/5 on both Windows and Linux. Current CF57 acceptance
comes from NEW records, not the historical kernel test. Original failure output
is retained in `full-standard-windows.txt`. Its first wrapper incorrectly parsed
skips only from an OK summary; the raw FAILED line says skipped=5. The additive
`historical-kernel-git-custody.json` records the correction without rewriting the
original JSON or raw output.

## Final verification and integration handoff

Final full suite: **2094 discovered, 2089 passed, 5 skipped, zero failures/errors**,
exit 0; 313 source files unchanged before/after. It started
2026-10-20T23:57:38.592994+03:00 and completed without timeout. Raw and structured results:
`full-final-windows.txt` / `.json`. Local code-static gate PASS, 2094 discovered;
this is not GitHub CI. `staged-code-custody.json` verifies exact working/index
bytes for all five changed paths; `unchanged-runtime-audit.json` retains the
unmodified v1/gate AST and unchanged broker/namespace source checks.

**Code-only commit:** `bbc0df06b8964c4851d12ed2ae915d71c1c9161f`. Evidence/docs are a separate follow-up commit
so the primary can integrate code without replacing its active status file.
No GitHub push, remote CI, main merge or production deployment is claimed.

Integrate the CODE commit into the primary startup work only after that writer
finishes its source edits; do not copy CF57's status over primary status. The
scope is `ipc_view.py`, the existing IPC contract test, the new IPC custody test,
the owned Linux probe, and historical D3B evidence tests. No broker CLI or
transport source is changed by CF57. Re-run combined tests on the integrated
source. Two-host-UID launch, the v2 mount path, real Gateway communication,
budget file-access boundaries and full D3B remain open.

Reproduce focused tests with `python -B -m unittest discover -s tests -p
"test_ipc*.py" -v`, and full regression with `python -B -m unittest discover -s
tests -v`. Use the existing Ubuntu environment and a fresh output filename
under the evidence directory when running
`scripts/qa/ipc_principal_custody_linux.py --output <fresh-path>`.


## Final handoff record — 2026-10-21T00:06:23+03:00

Local staged documentation/evidence static gate PASS: 2094 tests discovered, 1528 tracked files checked, exit0. Source and test bytes still equal the final full-run snapshot after code commit. The evidence directory has local Git attributes to preserve original LF/CRLF bytes and raw unittest progress spaces; product-code formatting checks are unchanged. `files.sha256.json` hashes every evidence file except itself. Original test/native failures and first full failure remain stored alongside the passing results. This documentation/evidence commit is separate from code bbc0df06b8964c4851d12ed2ae915d71c1c9161f. Local branch only; no push/remote CI/main merge.
