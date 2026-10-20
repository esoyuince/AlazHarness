# D3B independent launch/target QA â€” B72D

Branch `alaz/d3b-launch-qa-b72d`, base `47c70ea914dbc12d4ea2d39ef2a97a8a6b4a0139`.
Result: LOCAL SCOPED PASS, not privileged transition or full D3B acceptance.

## Ownership and source

The primary worktree `d3b-principal-launch-21oct` became dirty after the initial
read: another writer had begun D3B-POSTEXEC-21OCT. A pre-write cleanliness check
stopped this lane before any edit. Independent QA moved to its own worktree.
No primary, main, default-root or production file was edited or staged here.

This lane adds two explicitly invoked QA scripts under `scripts/qa`, not product
code and not new default-discovery tests. Primary target implementation was read
and tested from an explicit source path. Nine exact source files were pinned,
rechecked after both platform runs and saved byte-for-byte in
`evidence/d3b-launch-qa-b72d/reviewed-primary-source/` with `.txt` suffixes.
`reviewed-primary-snapshot.json` records the then-uncommitted source boundary.
These observations do not automatically certify a later primary commit.

## Executed native checks

`principal_files_fds_b72d.py`: 26/26 PASS on the base launcher, then 26/26 PASS
again against the primary post-exec launch source. These are the SAME cases,
not 52 different scenarios. Tests run as the existing unprivileged Linux user.

Actual filesystem cases: bounded valid reads, wrong permissions, hard links,
leaf/parent symbolic links, FIFO nonblocking refusal, directory/socket instead
of regular file, empty/oversize files, writable ancestry, and real pathname
replacement, chmod, truncation and timestamp change during descriptor reads.
The race probes use a controlled callback for timing; open/stat/read results
are actual kernel results. They do not prove atomic leases or ABA immunity.

Actual process cases: inherited socket AND regular-file descriptors are closed
in a child and absent after a real exec. The PID/UID remain the same. Socket and
regular-file standard input are refused; parent socket/file remain usable.
Successful and refused reads do not leak descriptors. Own temporary fixtures
are removed, and observer identity/groups/namespace/descriptors stay unchanged.
Fixtures are created only in a new owned HOME subdirectory because `/tmp`'s
writable ancestry is intentionally refused by the product helper.

First run: 24/26 passed; the two stdio cases failed because the QA child parsed
an absent optional fd-identity argument before calling product code. This was
a test-runner bug, not a product fix. Both original raw failure and JSON are
retained. `fixture-correction.json` records the one-line repair. The exact
pre-repair runner was reconstructed and SHA-verified from that one-line change;
its file explicitly says reconstruction, not original-time capture.

## Independent post-exec logic tests

`principal_target_independent_b72d.py`: 22/22 PASS on Windows and 22/22 PASS on
Ubuntu, against identical nine-file source bytes. The privileged kernel state,
filter installation and broker lifecycle are MOCKED in this suite. No root UID
transition, broker provider call or actual two-process principal communication
is claimed by these tests.

Coverage includes binding the principal/config digest into fixed isolated argv;
rejecting all incorrect real/effective/saved/filesystem identity slots; zero
capability inventory, host maps and namespace, empty groups, no_new_privs and
single-thread admission; mandatory installation of the known filter rather
than trusting Seccomp=2; no secret-file read after early failure; changed digest,
duplicate JSON and principal mismatch; no provisioning fallback; final kernel
recheck; redacted CLI errors; only the admitted configuration reaching the
existing broker lifecycle.

No product failure was identified by these tested cases. This is not a complete
security review and not authorization for privileged deployment.

## Reproduction

Run from this QA worktree, with a NEW result filename:

```text
python -B scripts/qa/principal_target_independent_b72d.py --source-root <reviewed-postexec-worktree> --output <qa-worktree>/evidence/d3b-launch-qa-b72d/<fresh>.json
python3 -I -B scripts/qa/principal_files_fds_b72d.py --source-root <reviewed-worktree> --output <qa-worktree>/evidence/d3b-launch-qa-b72d/<fresh>.json
```

The second command requires ordinary nonroot Linux. It never invokes sudo,
creates users, changes UID/GID, mounts, or provisions a service. Source hashes
must match the intended reviewed revision. Explicit selection counts are not
added to the existing full-standard suite count. This QA-only lane does not
relabel its inherited 2167-test receipt as a fresh full regression.

## Open gate / next action

Primary post-exec work was still in full regression at the snapshot. Wait for
its terminal result and code commit, compare that commit's nine source files
with the independent snapshot, then carry these QA scripts/evidence forward
without overwriting primary status or deleting earlier receipts.

The positive root-to-broker UID transition remains untested. It requires an
explicitly authorized isolated trusted installation: root-controlled runtime
and code, distinct nonzero Gateway/broker host identities, expected primary
socket group, initial user namespace, prepared broker-private config/budget,
and empty correctly owned socket directory. The current developer-writable
checkout is not that installation. Do not bypass a denied privilege operation
using a different connector, identity remap or helper. IPC v2 stays closed;
Gateway projection and two-UID budget-access acceptance remain open.

## OS references (mechanisms, not project evidence)

- https://man7.org/linux/man-pages/man2/execve.2.html
- https://docs.kernel.org/userspace-api/no_new_privs.html
- https://docs.kernel.org/userspace-api/seccomp_filter.html

The new native tests verify only the narrower file/descriptor observations
listed above; the references are not substitutes for runtime acceptance.

## Local QA delivery

Local static check PASS: 2167 tests discovered, not newly executed full regression. All 322 previously tracked runtime/config/test Git blobs are unchanged. The only new executable files are the two independent opt-in QA runners. All nine reviewed primary source hashes still match at delivery; observed primary HEAD `47c70ea914dbc12d4ea2d39ef2a97a8a6b4a0139`, working tree still dirty/in progress. Main remains `cc7ceba8f850da7652a647e984cbae2c45c8fdea`.

Raw Windows JSON contains native CRLF. The initial Git whitespace check refused that raw artifact; its output is retained in raw-evidence-format-first.txt. A file-specific evidence attribute preserves the original bytes without changing product whitespace checks or any test assertion. No secret-finding or code-test failure was suppressed.
