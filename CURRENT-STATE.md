# AlazHarness — integrated checkpoint

Date: 2026-10-15. Default workspace: C:\Antigravity\AlazHarness.
Active integration branch: alaz/hyb-003-integration-46cc.
Isolated worktree: scratch/worktrees/hyb-003-integration-46cc under that root.
Always read current git status / HEAD / remote status; concurrent lanes may advance.

## Result and scope

The reviewed stdio and HTTP feature histories are reconciled in this worktree:
c637380706232eb49f835b45da7da1f4fa3573a0 +
eb20b2e7559750db3c61f0b8450b393ae96f6368.
No edits or branch switches were made in the original dirty shared checkout.
Its alaz/hyb-001-component-slice work and older evidence remain preserved.
The integration branch is not main; publication/CI are verified separately.

M0 remains accepted. HYB-001/002 components and contract suites are combined.
HYB-003 direct native AIAgent + real read_file round is now PASS with scripted
model HTTP responses. Full Gateway/ingress HYB-003 and full M1 remain OPEN.
No model inference, paid-provider call or autonomy loop was run.

## Single source owner

OpenClaw pin: 2dcbb6138d57dccfcd54f2f908ef9f38268b1229.
Hermes pin: eb75627faf532fa6ffbdae59a0d14b0b385fc780.
The unchanged original vendor trees remain in the default workspace; this
integration worktree does not duplicate their full checkouts.

Both transports now use packages/upstream with TEN unique payloads (eight source
modules/functions and two MIT licenses). Canonical lock: config/components.lock.json.
Canonical checker: scripts/verify_components.py. Duplicate tree, old root lock and
old checker retired; all behavioral test scenarios retained. Only one actual
Hermes engine may own a live session. Adapters must not co-own its transcript.

## Native evidence

Prepared interpreter (local, Git-ignored):
runtime/hermes-hyb003-46cc/env/Scripts/python.exe under the default workspace.
Hermes's own pm.build_environment used frozen inputs, no extras and an isolated
home/profile/cache/tool store. Existing personal profiles/keys were not used.

- file-read: real public AIAgent constructor, conversation loop and native read_file;
  one actual read result, two loopback model requests, completed=true.
- budget-summary: max_iterations=1, one actual read, two model requests including
  summary, completed=false and max_iterations_reached(1/1). This confirms native
  exhaustion semantics but DOES NOT enforce a hard provider-request/currency cap.
- Initial false assumption of one HTTP call under one iteration is preserved as
  FAIL; an empty summary can be retried once, producing three HTTP requests.
- Python socket audit rejects non-loopback connects; this is not an OS sandbox.
- Native probes are local Windows evidence, not Linux CI engine acceptance.

Sanitized native/preparation evidence: evidence/hyb-003/.
Raw profile/log files remain in the original workspace's ignored runtime tree.

## Verification commands

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_components.py --with-vendor --source-workspace C:\Antigravity\AlazHarness
python -B scripts/demo_hybrid.py
python -B scripts/demo_hybrid_mock.py
```

Ordinary tests: Python3.11+, Node24+ and Git; no model keys or dependencies installed.
Actual native probes: scripts/run_native_hermes_probe.py, explicit prepared Python
3.14 and fresh output; docs/HYB-003-INTEGRATION.md gives exact commands and limits.
The first unified suite passed122/122 before new launcher tests; final counts and
scope are recorded in evidence/hyb-003/local-validation.json after the final run.
A test count or receipt file alone is not exact-commit GitHub success evidence.

## Next work

Qualify the actual Hermes Gateway / SessionAuthority / APIServerAdapter entry
with the scripted loopback model, then call it through HermesRunsClient. No new
parallel transcript store or made-up Gateway API. Include keyed duplicate/lost
admission and native stop semantics, then actual restart reconciliation.

HYB-005: a provider-dispatch request/token/currency budget must account for summary,
retry and auxiliary calls. Do not substitute max_iterations for that cap.
Full OpenClaw ingress, real process isolation, restart-safe identity, memory/skill
transfer, real-model qualification and M2 autonomy are not accepted yet.

## Git and CI custody

Public repository esoyuince/AlazHarness, MIT. Existing alaz-server Local CI and
GitHub alaz/local-ci context unchanged; GitHub Actions remains disabled. No
infrastructure policy, server secret or external service changed in this package.
Historical evidence directories keep their original counts and source versions.
Do not stage unrelated shared-checkout files or force-push any branch.

## Connection interruption recovery

The in-progress merge was found with all conflicts resolved and staged. Its
128 root tests and gates were re-executed successfully; stored native probe
worker hashes matched. No unknown operation was replayed. The integration
checkpoint is being committed on this feature branch, not main.

New user scope: include Pi harness and OpenCode in the component review. This is
not a decision to replace Hermes/OpenClaw or launch extra model loops. Review
source identity, pinned components, ownership, dependencies and acceptance gaps
before adopting code. See the subsequent docs/research checkpoint.
