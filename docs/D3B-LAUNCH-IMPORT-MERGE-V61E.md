# D3B launcher + isolated-import integration — V61E

Branch: `alaz/d3b-principal-launch-21oct`.
Base: `edb4ae1262b082b9bf358e04ff4c6565b09fde10`.
Incoming: `01791c1ff485d9950a72728b00de83c2b520c748`, including code fix `797b4aa`.
Worktree: `scratch/worktrees/d3b-principal-launch-21oct`.
Status: LOCAL SCOPED PASS; full D3B NOT ACCEPTED.

## Integrated change

The completed post-exec launcher/independent QA tree now contains the isolated
interpreter import correction and its unchanged three fresh-process regression
cases. Only two product lines are added: after target.prepare succeeds, the
installation-relative scripts path is inserted before importing the existing
broker lifecycle. No current-directory or PYTHONPATH fallback is added.
The import tests mock identity admission and asyncio execution; they inspect
and close the actual coroutine without starting the broker. They are not proof
of a successful privileged launch. Original before/after failures are retained.

The complete incoming history and report/evidence are merged, not squashed or
rewritten. Only status.md conflicted (two blocks); both historical narratives
are preserved below this task's live continuation. No product/test conflict
occurred. The inherited evidence from both parents remains byte-identical in
Git, including earlier failures. The two input evidence inventories overlap
and must not be summed as unique files.

## Current-source validation

Evidence: `evidence/d3b-launch-import-merge-v61e/`.
Source inventory: 331 package/script/test/config files in sources-frozen.json.
Fresh raw outputs, commands, outcomes and hashes are recorded by each run.
Do not infer success from historical parent results or nonterminal requests.

Current-source full Windows standard suite: **2203 total / 2198 PASS / 5 SKIP /
0 failures / 0 errors**, unittest exit0, 193.247 seconds. The331 source hashes
match before/after/current. Five existing opt-in Linux transport skips are not
reported as passes or newly executed by this integration.

Windows and Linux principal selections each passed83/83 without skips,
including the3 fresh isolated-import tests. Unmodified independent B72D tests
passed22/22 on each OS with privileged kernel state explicitly mocked. Actual
unprivileged Linux file/FD26, postexec16 and launcher-denial13 checks all passed.
All seven selected/native runs are terminal exit0 and source-pinned. Local static
inspection PASS,2203 discovered. Static discovery is separate from execution;
selected/native/cross-platform counts overlap and are not added to the full suite.

### Collector outcome reconciliation (original failure preserved)

The unittest subprocess completed with exit0 and an OK(skipped=5) footer, but
its enclosing one-off collector returned exit1: a strict dollar-anchored regex
failed to consume Windows CRLF framing. `full-windows-result.json` retains that
original FAIL_OR_INCOMPLETE outcome; `full-windows.txt` retains the exact bytes.
`full-windows-reviewed.json` is a separate correction, not a rerun: it checks
all2203 unique named terminal results,2198 ok and5 skips, the unique final total,
footer, actual subprocess exit and frozen source. The read-only reviewer has
11 positive/negative controls (LF, CRLF, bad exit, timeout, missing/duplicate
result, incorrect skip count, failed case, extra output and zero discovery).
Its source is preserved in full-log-review.py.txt. No product test assertion,
raw output, historical receipt or product source was changed to obtain this result.


## Still-open positive gate

This revision is not a root-controlled installation. No root command, identity
provisioning, privilege transition or two-UID broker/Gateway execution is
performed here. Known positive blockers remain: explicitly authorized isolated
Linux installation with trusted interpreter/code/dependencies, distinct broker
and Gateway host UIDs, designated GID, pinned initial host user namespace, and
pre-provisioned private config/budget plus an empty broker socket directory.

The next positive proof must observe the actual broker after exec, peer
credentials on both ends, private-budget read AND write denials with positive
owner controls, controlled restart/rebind and cleanup. Broker read-only access
to Gateway state.db/epoch/grants must be specified separately before a send
trial; a ping alone cannot qualify provider dispatch. Dummy local provider only
until a separately configured real-model gate is authorized.

IPC v2 prepare/project remain closed. The separate Gateway projection path still
needs implementation and native acceptance; do not delete its gates, weaken
v1 permissions or bypass prior privilege denial. Main remains the published
cc7ceba development baseline; no main update, push, release, service or model call.

## Final verification and continuation

The root modified-file snapshot and status, clean published main, incoming import
branch and independent QA branch are preserved. Current remote main is cc7ceba.
Both parent evidence inventories match their original Git blobs. This local merge
closes the missing import integration; it does not close privileged/two-UID runtime
acceptance. The positive environment/proof described above is the next meaningful
gate, not another readiness-only repetition. Exact commit follows in Git history.

### Raw-evidence line endings

The staged formatting check first reported only39 CRLF end markers in the new
Windows independent-QA JSON. No trailing spaces/tabs were present. The existing
evidence/.gitattributes was extended by one exact-filename cr-at-eol rule, leaving
all inherited rules and every raw receipt unchanged. This is the only intentionally
modified inherited evidence configuration; all inherited evidence payload blobs
remain exact. Original diagnostic and before/after attribute hashes are retained.
