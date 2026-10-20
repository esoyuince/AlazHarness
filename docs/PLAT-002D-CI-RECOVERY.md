# PLAT-002D — frozen source custody and CI reconciliation

Date: 2026-10-20. Feature branch alaz/plat-002d-ci-recovery-20oct
based on f18da79d43da6dcafa71ddf43ae9a9a400fe8ad6.

Scope: CI/test evidence compatibility, NOT native wrapper-loss acceptance.

Original branch: Windows root unittest 2286/2286 exit0
(five Linux-only skipped), static check PASS (1555 tracked
files, two source gitlinks); GitHub alaz/local-ci on f18da79
reported FAILURE rc1. Without server per-test logs all failing
tests cannot be independently listed.

One reproducible Linux-only failure was isolated: frozen native
Windows CRLF SHA of scripts/qa/run_plat002d_windows_once.py
compared directly with Git/Linux LF data in
tests/test_plat002d_second_pilot.py. The hashes differ,
but exact whole-file LF->CRLF transformation reproduces the
original pinned Windows source. Simulating a Linux Git LF
checkout breaks exactly one of the eight original tests.

The repair keeps original native FAIL receipts and source SHA
values untouched. It permits only one exact full-file LF->CRLF
representation of the specific native path. A content mutation
still fails. A historical six-source manifest remains pinned
to the original Git commit f18da79, not falsely reattributed
to the revised test source.

Focused PLAT002D tests: 62/62 PASS on Windows and 62/62 PASS
with tracked text reads simulated as Git/Linux LF. These tests
launch no WSL guest, process, model or provider.

A non-starting wsl.exe --list --running query currently reports
no running distributions. This is NOT a live Linux process
enumeration or proof that the earlier detached guardian safely
reaped descendants. The original two wrapper-loss attempts
remain FAIL/UNKNOWN and no retry was attempted. No distro
restart, unrelated PID termination, user or server changes.

Next native task: inspect guest health only under an explicit
safe operator-approved approach, and design a strict persistent
test-only private Linux journal outside volatile /tmp, with
source SHA, nonce, PID birth tick, boot ID and fsynced terminal
record. Full PLAT-002, D3B, Hermes, M1/M2 remain NOT ACCEPTED.

Evidence: evidence/plat-002d-recovery-20oct.
Original docs/PLAT-002D-WRAPPER-LOSS-NO-GO.md and native
FAIL receipts remain frozen. The old dirty worktree is untouched.


## Scoped local checks before code commit

The focused full PLAT-002D contract suite reports 62/62 PASS
(Windows) and 62/62 PASS (simulated tracked Git/Linux LF).
The root static checker independently reports PASS: 2,291
default-discovered tests, 1,560 tracked text files, two upstream
source gitlinks, exit code 0, no real model/runtime execution.
The prior base code had 2,286 full Windows unit tests PASS, with
five Linux-only skips, but the recovery branch has not yet
rerun a new full 2,291-test local Windows suite at this point.
Exact new GitHub CI is therefore still required.


## Exact recovery code CI and full Windows regression

Recovery code 0fb821bc027892085bfe716372f13d7347420cbc
was published only to the isolated recovery branch. Its
GitHub alaz/local-ci returned **SUCCESS** (status ID
56747876688, 2026-10-20T01:02:05Z). Original failed
f18da79 rc1 result remains preserved separately.
This verifies the source/CI compatibility repair, NOT
a native WSL lease or guardian acceptance.

A new complete Windows root unittest run on that same
recovery code executed 2,291 discovered tests, exit0,
five Linux-only skips, 386.436 seconds. SHA256 of
the full ignored log is recorded in
evidence/plat-002d-recovery-20oct/full-regression-observed.json.
Root static: PASS, 2,291 discovered, 1,560 tracked files,
two Git source links. A new real WSL native experiment was
NOT RUN because earlier Linux process closure is UNKNOWN
and Ubuntu had no running distro at last non-starting check.

The subsequent documentation/status observation commit is
independent and requires its own exact GitHub CI result.
