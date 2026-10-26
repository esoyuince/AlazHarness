# R156 acceptance render and fixture source review

## Verdict

**No concrete blocker found against the final stable source hashes below.** The rendered acceptance path validates the actual finite protocol directly, preserves the original seed/controller/cgroup ownership and unknown-custody behavior, and binds ordinary proof to the new actual installation. It does not convert an R155 readiness receipt into finite evidence.

This review was source/AST/hash inspection only. No renderer, tests, WSL, native work, model/provider call or primary-repository mutation was executed by this reviewer. Reported fixture-test success from the owning agent is not counted here as independent runtime evidence. Actual generated sources with final candidate/receipt pins and the subsequent dedicated-lab run remain separate steps.

## Stable reviewed files

| File | SHA256 |
|---|---|
| `/workspace/scratch/288e2938ab4c/r156-acceptance/scripts/qa/r156a1_prepare.py` | `cc652865855cedca4f1d06f4d8ed7d58be462d5612082d02b843b2b688130a54` |
| `/workspace/scratch/288e2938ab4c/r156-acceptance/scripts/qa/r156a1_acceptance_templates.py` | `e2aa6b659e2926222be552dfa47835b6ef67aaa1c0296104b6c1a994c9d794f0` |

Both were hashed at review start and end; unchanged. The preparation script's template pin equals the second hash. All six original R155 template files independently hash-match their pinned entries in `SEED_TEMPLATES`.

## Direct finite validation

The preparer (`render_acceptance`, lines 465–563) takes the pure finite protocol from the verified candidate source map and appends a fixed assertion suffix. Installation receipt/harness identity and the fixed normal/replay/new/error request identities are part of that generated source. The protocol is never replaced by a readiness validator.

The assertion suffix (`r156a1_acceptance_templates.py:14–93`) does the following:

- Requires the finite supervisor state, successful child exit and volume-close authorization, with `observedAfterUnknown=False` and full D3B excluded.
- Calls the candidate's original `validate_result` for the fixed work, original child PID and previous epoch 1. This enforces the four receipts, computation counts 1/1/2/3, replay equality, new identities, failed error case, native trace, explicit fixture/zero-provider scope and native close evidence.
- Binds the finite owner result to `SHA256(canonical(owner) + newline)` and then to the actual captured stdout bytes. It checks the observed stderr bytes/digest independently instead of assuming empty native diagnostics.
- Checks the original retained-child observation: phase COMPLETED, matching PID/startTicks, exit zero, complete bounded capture, no overflow, integer positive bounded input byte count, and matching payload digest.
- Requires the original volume finish result with users gone, loop attachment gone, fence removed after cleanup and lease released last.

Caller, Linux transport and host all validate this finite assertion directly. Transport additionally waits for the original caller's successful exit; host reconstructs captured caller bytes, compares them with the embedded report and runs full seed validation. Changing the caller label alone cannot satisfy the finite protocol or native captured-output binding.

The renderer does replace the old readiness-state literal inside the preserved `close_volume` precondition, because its observed child is now the finite operation. That is a source-level precondition change before execution; it is not result rewriting.

## One controller, one finite child, ordered close

`CALLER_EXECUTE` retains this order:

1. Validate dedicated actor, source manifest, full installed bytes and fixed formatter.
2. Provision fresh image/paths and metadata-only broker socket.
3. Begin, attach and start the original `RetainedVolumeSupervisor`.
4. Run the original supervised seed child and validate its actual profile/store identities and handoff.
5. Call `run_finite` exactly once with the fixed work; validate its returned receipt and require `observe_finite()` to return the same original result.
6. Call original volume `stop`, then `finish`, then stop the metadata broker only after the volume is CLOSED.
7. Recheck unchanged host mount namespace/table, no host mount, no live scope/attachment/fence and unchanged image identity before producing PASS.

The controller's seed, finite attempt, worker and original supervisor objects remain in the original object graph. `run_finite` and readiness share one native child-attempt slot; the caller does not invoke readiness as an intermediate task. The second finite call is an observation method, not launch or resend.

Native supervisor `_observe` still reaps the child, validates the candidate finite result against that child's expected work and prior epoch, rechecks original ownership, requires the mount worker alive and confirms the cgroup contains only that worker. Stop/finish still refuse any unresolved retained child.

## Budgets and membership

The source renames `READY_SECONDS` to `FINITE_SECONDS` without changing values: seed 35 seconds, finite 60 seconds, stop margin 15 seconds. Their total is 110, below the existing 120-second worker lifetime. The preserved seed gate checks current monotonic time plus that entire allocation against the original worker deadline before launching the seed. The native finite supervisor checks remaining timeout plus the same 15-second margin before setup and again immediately before spawning the finite child.

The supervisor sets its conservative deadline from before the original worker startup, so it does not accidentally extend the worker's real 120-second wait. Original cgroup membership checks remain: worker alone before seed/finite work, original child registered before namespace use, worker alone again after child reap. No worker restart or extended lifetime is introduced by rendering.

This proves a coherent bounded source contract, not that new import/compute costs will fit the limits in the actual lab. A budget failure remains unknown/unaccepted and does not relax the deadline.

## Ordinary proof and installation binding

`verify_receipt(:423–455)` requires actual canonical receipt bytes with the supplied exact SHA256, the new destination, manifest/archive/harness/native identities, source/dependency counts, interpreter identity and non-executed installation claims. `render_acceptance` additionally checks the receipt's dependency inventory against the candidate bytes and refuses any changed original seed helper rather than silently repinning it.

The generated producer gets the new exact installer hash, receipt hash and candidate pins. Its original `verify_installation` calls the reviewed installer's `verify_installed`, which reads back the entire installed source/dependency tree before runtime imports. The original producer's task-free native lifecycle and offline boundary remain the same source.

The ordinary driver binds its embedded Linux producer check to the generated producer SHA, actual installation receipt SHA and actual harness commit. Host `validate_ordinary` requires the exact current producer bytes, ordinary-driver Linux literal, start record, output digests, parsed producer frame, new receipt/harness/native identity, six startup checks, no work, physical database close and normal caller lease release. R155 ordinary proof therefore fails against the changed R156 producer/runtime binding.

Host preparation freezes the original ordinary proof, producer/driver sources, four acceptance input sources, transport, host script and intent. Apply reruns ordinary validation against current bytes and the same fixed base commit, reconstructs the expected frozen bundle, checks exact inventory/bytes, and only then writes an exclusive execution-start marker.

## Unknown custody and failed evidence writes

The preserved caller marks effects before provisioning. Any later failure produces NOT_ACCEPTED/OUTCOME_UNKNOWN, captures original object observations, emits its original PID/startTicks custody record, then retains the same controller/supervisor references in `retain_alive`. It closes only diagnostic stdio and waits; no retry, signal, volume stop, unmount, lease release or reconstruction is added.

The transport validates live custody against the original spawned process identity. Host reports that custody was observed before transport exit and deliberately keeps `continuingLiveCustodyVerified=False`; it does not claim ongoing observation after its own check. Missing/invalid frames and unobserved exits remain unknown.

The host renderer's `_function_literals` handles both string keys and keyword identifiers. Thus the inherited evidence-write-failure path now sets `projectedFiniteAccepted=False` correctly, along with result/state UNKNOWN. If a full finite PASS was already observed before evidence writing failed, `finiteWorkExecuted=True` may remain as an observed-effect field. The owning agent confirmed that distinction is intentional: it is not a retained acceptance flag or permission to retry. Full D3B, M1 and production-ready flags remain false.

## Remaining execution gates

The final candidate-specific generated sources and transport should still be reviewed with actual commit/archive/manifest/receipt hashes. The ordinary proof must actually complete for that exact producer and installed runtime before root acceptance preparation/apply. Actual projected normal/replay/new/error/native-close execution is not established by this source review or the owned fixtures. A final result requires observed original-child completion and ordered original-volume close.
