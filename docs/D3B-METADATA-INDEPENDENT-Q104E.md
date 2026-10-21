# Independent metadata boundary QA — Q104E

Base:1207d37; branch alaz/d3b-native-profile-q104e. This branch changes NO
existing product source. Canonical P102 fixed-profile projection stays selected;
alternative P102X is not merged. When concurrent F104X was found implementing
the same permission/native-profile step, this task switched to independent QA.
It does not claim authorship of F104X or turn its pending work into acceptance.

## Exact candidate and independent rule tests

The guard and projection snapshots in candidate-001.json came from F104X before
its commit. SHA-256 pins are authoritative, not the base commit alone. Only the
guard snapshot is executed by this QA; the projection snapshot is provenance.
Twelve tests intercept the actual guard's rule-building calls and check exact
READ_FILE=4 for every metadata rule, fixed numeric-PID path, unchanged default,
separate opt-in digest, no policy-JSON permission smuggling, failed open/add/
restrict handling, nonregular mountinfo rejection, protected-path conflict,
O_PATH|CLOEXEC|NOFOLLOW and complete descriptor closure. They are kernel doubles,
not native confinement evidence. All12 pass on Windows and Linux.

First Windows result3PASS/9FAIL is retained. The fixture represented Path.stat
with Windows backslashes but the synthetic syscall identity used POSIX names;
normalizing ONLY that fixture with as_posix fixed the inconsistency. Expected
assertions and both candidate snapshots were unchanged. No product defect was
inferred from that platform-fixture error.

## Actual ordinary-user Linux audit

scripts/qa/q104e_metadata_probe.py ran in the approved P71C lab as the existing
UID23001/GID23003, using only new temporary code/data. It did not use root,
change users/namespaces/mounts, create accounts, install dependencies, start a
broker, call a model or execute Hermes. It exercises Landlock alone, not the
full Gateway network/IPC sandbox. Standard runtime /usr is read-only solely
for this test; this is not a new production filesystem policy.

Three fresh-process cases: default omitted, explicitFalse, explicitTrue. Each
applies the exact candidate then performs a REAL exec while retaining PID.
Each passed21 overlapping observations; these are not63 independent runs.
Each has one fork child and one new exec child: nine tested process instances.

- Before restriction, ordinary-user positive controls could open own metadata,
  parent's mountinfo, fd directory and a dummy protected canary. No environment,
  memory or maps contents were read; opens are permission controls only.
- After exec, default/False deny both self and numeric current mountinfo with
  EACCES. True allows exactly those aliases; actual mountinfo bytes match the
  unchanged kernel mount table. Existing self status remains readable.
- All cases deny own environ/mem/maps/mounts/mountstats/fd directory, parent
  mountinfo and dummy canary with EACCES. Workspace remains writable; no_new_privs
  holds and effective capabilities remain zero. Mountinfo write-open is denied,
  but procfs also restricts writing, so exact Landlock mask proof comes from
  the independent rule tests, not an overclaim from that denial alone.
- Fork/exec descendants do NOT receive a new own-PID mountinfo grant. They DO
  inherit the original numeric launch-PID grant when enabled. The latter is
  expected inherited access, not evidence of universal self-only access for
  every descendant. Future child admission must handle this explicitly.
- Source hashes, parent identity/user and mount namespaces, and mount table
  stay unchanged. All child PIDs are reaped and own temporary trees removed.
  Separate ordinary-user cleanup found no matching process or residual tree.

The lab was initially Stopped and our ordinary invocation started it. No stop
was requested because F104X was concurrently using the same approved lab.
Default Ubuntu remained untouched. No root command or physical image operation
was performed by this QA. Cleanup is scoped to our UID/temporary prefixes.

## Provenance and concurrent native profile evidence

Four offline receipt tests pin actual terminal output, candidate/script hashes,
three case outcomes, nine process identities, inheritance and limits. These are
not new native executions. The original guard implementation remains unchanged
in this branch; full local regression includes the snapshot audit separately.

F104X native002 was inspected read-only, not rerun or relabeled as ours. Its
41 parent and two38-condition proofs are source-verified against its current
files, pinned immutable Hermes Git objects and prior verified ruamel dependency
hashes. Each process's imported sources matches the original manifest. The two
permission files exactly match our candidate snapshots. This corroborates the
permission primitive used in its post-exec native-profile experiment; no new
full Gateway/replay/provider/paired-recovery claim follows. Final F104X commit
and complete regression must be checked separately before integration.

## Remaining boundary

Keep canonical P102/F104X runtime singular. Merge this QA only after it is
committed and its snapshots match the final implementation, preserving both
histories and running the combined standard gate. This branch does not repair
R91F or replay G82C denied work. Legacy IPCv2 remains closed/fullD3B open.
Actual Hermes Gateway, native database/epoch/recovery and live broker ledger
read path/provider send remain separate from metadata and profile ownership.

Evidence:evidence/d3b-native-profile-q104e/. Current pointer:status.md.
Own complete regression/static/commit outcomes are appended after completion.

## Final independent full regression

NEW complete standard Windows run:2444 total /2421 PASS /23 SKIP /0 errors /
0 failures, exit0. All376 current source/config/test/script hashes stable;
all373 prior source bytes unchanged. Twelve rule tests and four offline receipt
methods are included in that total. Same12 rule tests ran on Linux; native
three cases and their nested descendant observations are not additional unique
unit tests. The23 preexisting Linux/explicit-opt-in skipped methods were NOT
reexecuted by this task. This is canonical1207d37 plus QA of pinned candidate
snapshots, NOT the integrated F104X product regression.

All own native/full jobs are terminal. First fixture failure output remains
immutable; no assertion weakening, timeout increase or product fix was needed.
Final local static runs after complete tests and is recorded independently.
Do not promote this QA's own full result as proof the concurrent implementation
was integrated; check its final commit/regression separately.
