# D3B isolated post-exec import repair — R52A

Branch: `alaz/d3b-postexec-import-r52a`. Base: `9469d58bf1aa9b12fed059fae8df6c51282b4644`.
This is an independent, narrow code correction while C91A owns the concurrent
primary/QA merge. No file or index in that primary worktree was changed.

## Confirmed defect

The fixed target was launched with `python -I -B`, added its package directory
to sys.path, then imported `run_provider_broker` from the sibling scripts
folder only after admission. Isolated Python does not add the script directory.
The target therefore returned REFUSED / ModuleNotFoundError on the admitted
branch before it could construct the real lifecycle coroutine.

Existing tests imported the scripts folder before calling main and mocked the
lifecycle by import name, so they could not expose this fresh-interpreter gap.
The previous native negative cases rejected identity before reaching the import.
This is a functional startup failure in an unactivated path, not evidence of a
production compromise or proof of a successful real UID transition.

## Minimal change

After successful target.prepare, add only the installation-relative scripts
folder resolved from this entrypoint's __file__, then import the existing broker
lifecycle. Keep isolated -I/-B, immutable-install prerequisites, exact argv and
configuration digest, all admission checks and the original asynchronous broker
implementation. No working-directory or PYTHONPATH fallback, arbitrary module
path, general command dispatch or new privilege is introduced.

## Reproduction and scope

`tests/test_principal_target_isolated_import.py` creates a fresh real isolated
Python child. It runs the actual entrypoint and real module loader. Only identity
admission and asyncio.run are mocked. The real serve coroutine is inspected and
closed WITHOUT execution; an audit hook rejects any socket creation. No event
loop, config read, UID change, broker provider call or model is executed.

Three regression cases verify: admitted import resolves the exact installed
serve module; dummy modules in cwd/PYTHONPATH cannot shadow either admission or
lifecycle; rejected admission does not import lifecycle or create an event loop.
Both Windows and ordinary-user Ubuntu BEFORE runs had 1 PASS and 2 FAIL with
ModuleNotFoundError. The exact SAME test bytes pass 3/3 on both AFTER runs.
Original target bytes, failing logs and test digests are retained under
`evidence/d3b-postexec-import-r52a/`.

Focused principal tests pass 83/83 on Windows and 83/83 on Linux; this includes
the three new cases and is an overlapping subset of standard discovery.
The actual unprivileged postexec probe was rerun: 16/16 PASS_SCOPED_POSTEXEC,
10 sources unchanged before/after. Its fresh receipt is
`evidence/d3b-postexec-21oct/native-postexec-import-r52a.json`.
The current receipt checker points to that new execution; no previous receipt
was rewritten and no hash assertion was weakened. This real probe proves only
exec/filter inheritance and wrong-identity refusal, not positive broker startup.

Full Windows regression completed: **2203 total = 2198 PASS + 5 SKIP**, exit0,
zero failures/errors. The five skips are existing explicitly opt-in Linux cases,
not counted as passes. All **329** source/config/test bytes stayed unchanged.
The exact independent B72D QA runner was also executed on the corrected source:
**22/22 Windows and 22/22 Linux**, no skips, nine source hashes stable. Its
privileged kernel state is mocked. The immutable runner was used from an owned
temporary copy; the original QA worktree was not written, and the copy was removed.
Local code/static gate: PASS, 2203 discovered; this is not remote CI. Focused
selections overlap the full standard inventory and are not summed into its total.

## Integration ownership and exact next step

Primary C91A concurrently integrates completed postexec `9469d58` with B72D QA
`d0414e2`. A pre-write HEAD guard stopped this lane before modifying primary.
The nine B72D reviewed files match the immutable postexec commit (only exact
LF/CRLF checkout representation differs for historical sources).
This branch does not duplicate that merge or overwrite either status history.
The alternative E6A2 bootstrap is not auto-merged; it supplies a different
entrypoint contract at the same script filename.

Integrate this CODE correction after C91A's worktree is stable, then rerun its
combined checks. The primary's passing import-path-contaminated tests cannot
substitute for this missing isolated regression. Current-code acceptance must
use new source-bound receipts rather than relabeling historical runs.

Positive root-to-broker transition, actual two-host-UID Gateway/broker transport,
private-budget file denial and Gateway projection remain NOT ACCEPTED. Both
IPC v2 gates remain closed. No root, sudo, account provisioning, production,
main write, push, paid model or bypass of the previous privilege denial occurred.
A trusted, separately authorized provisioned installation is still required
for the privileged positive acceptance.

## Interpreter references (not project acceptance)

- https://docs.python.org/3/using/cmdline.html#cmdoption-I
- https://docs.python.org/3/library/runpy.html#runpy.run_path

These document isolated path handling and script execution; the raw before/after
runs above establish this project's narrower behavior.


## Local delivery

Code/acceptance-only commit: `797b4aabd17fdc80f52c24949307050496ca6c79` (4 selected paths, no status/report replacement). The following evidence-only commit records the logs and exact handoff. Current primary observed read-only at `edb4ae1262b082b9bf358e04ff4c6565b09fde10`, dirty=false. It owns the C91A integration; no cherry-pick was forced into its active tree. Main remains cc7ceba; this branch has not been pushed.

Exact next action: the primary owner integrates code commit `797b4aabd17fdc80f52c24949307050496ca6c79`, retains the fresh post-exec receipt and all three isolated-process regressions, then requalifies the combined source. This fixes a real admitted import failure but does not close the authorized-environment/positive-UID gate.
