# AlazHarness — REF-PI-001 checkpoint

Date: 2026-10-15. Default workspace: C:\Antigravity\AlazHarness.
Current package: alaz/ref-pi-001-native-ac97.
Worktree: scratch/worktrees/ref-pi-001-ac97 under the default workspace.
Base: 3bf5305f9cadab584429ca4d97a941f394c0522f (review), containing integration 99d6fe1.
Recheck Git status/HEAD on every continuation; other lanes and dirty worktrees exist.

## Completed in this package

Real pinned Pi low-level Agent + native provider parsing + built-in read tool
ran through six scoped scenarios, repeated twice: 12/12 local PASS.
Only model responses were scripted on loopback SSE. No inference or paid call.
Source: earendil-works/pi b06c1f2cf1dea6af8748ddeee18c23587d2cb7c6 (packages1.2.0).
Original Pi reference, OpenCode reference, OpenClaw and Hermes sources unchanged.
No new production dependency, primary worktree change or main merge.

New tools: prepare_native_pi.py (plan by default), run_native_pi_probe.py,
run_native_pi_suite.py, pi_probe_support.py, pi_probe_contract.mjs and the worker.
Test-host controls never count as already enforced production security/budgets.

- file-read: real file result returns to the provider, one read/two requests, final.
- missing-file: native error preserved; test passes but taskCompleted=false.
- cancel-model: native abort during HTTP wait; aborted, no tool, socket closed.
- one-round: explicit finishTurn host hook ends after one tool, no final response.
- request-cap: test fetch boundary rejects extra request; native generic connection
  error retained, normalized request_budget_exhausted preserves the host cause.
- truncated-tool: partial response refuses execution and supplies a tool error.

Native evidence: evidence/ref-pi-001/native-suite.json (12 receipts).
Preparation/source custody: evidence/ref-pi-001/preparation.json and source-custody.json.
Detailed Turkish report and commands: docs/research/REF-PI-001-NATIVE.md.
Local prepared source: runtime/pi-ref001-ac97/source. Personal Pi profile unused.
Raw fresh profiles/logs remain under runtime/pi-ref001-ac97/acceptance-01.

## CI versus native acceptance

Existing root baseline128 tests plus new host/launcher guards run without Pi
installation. Actual Pi runtime acceptance above is separately recorded Windows
Node24.19 evidence, NOT Linux CI native acceptance. No silent skip of host tests.
Exact current commit CI result must be read after push, never inferred from files.

## Prior custody and still-open scope

Runtime source pins remain OpenClaw 2dcbb6138d57dccfcd54f2f908ef9f38268b1229 and
Hermes eb75627faf532fa6ffbdae59a0d14b0b385fc780. The existing ten copied payloads
remain under packages/upstream, with config/components.lock.json as sole owner.
Hermes positive native tool/budget-summary evidence remains historical and valid
in its recorded scope; it was not replayed here or compared as a timing benchmark.

We did not run Pi createAgentSession/SessionManager, Durable, OpenCode runtime,
full OpenClaw ingress or actual Hermes Gateway here. No new persistent model
loop, scheduler or self-selected agenda. M0 accepted; complete M1 and M2 still OPEN.
No engine replacement decision. Pi is now a runtime-qualified narrow candidate.

## Next

REF-PI-002: isolated Durable admission/crash/replay tests, specifically duplicate
requestId with changed payload, external side effects versus committed result,
wait cancellation versus task cancellation and failed storage. Keep one owner of
canonical transcript. OpenCode REF-OC-001 permission/event tests remain pending.
Full provider token/currency budget, OS isolation, memory/skill transfer and
real-model qualification are separate gates; never substitute max_iterations.

## Reproduce standard gate

python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_components.py --with-vendor --source-workspace C:\Antigravity\AlazHarness

Do not reset or auto-merge the original dirty alaz/hyb-001-component-slice root.
Push only this branch, preserve all prior feature branches and current user files.
