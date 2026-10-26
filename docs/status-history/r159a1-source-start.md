# AlazHarness - status

## R159A1 - IN PROGRESS: explicit borrowed loopback service

P1 remains DONE. P2 is IN PROGRESS. P3-P5, full D3B, M1 and production are OPEN.
The current packet adds an explicitly owned local transport to the existing native
runner, authority and three stores. Default P1 preparation stays listener-free.

Active branch: alaz/p2-borrowed-service-r159a1.
Harness base: 37620d5c14afee895b16e3441f7a7ed14b77e7d7.
Native base: d1516731308de8e87130dc68124e69aad35d6911.
Worktrees: scratch/worktrees/p2-borrowed-service-r159a1 and
scratch/worktrees/hermes-borrowed-service-r159a1 on the primary host.

### Verified starting point

R158 final publication journal, 44 owned file hashes, feature/main refs and latest
required CI verified against live primary Git. Protected repositories and original
root33 changes remain intact. R159 uses new isolated worktrees from those bases.
No service or provider/model call has been started in this packet.

### Current work

- Native explicit one-shot borrowed HTTP transport, narrow routes, identity-bound
  readiness, admission seal and actual handler/physical-worker shutdown barriers.
- Existing Host Gate/execution boundary integration with ready/draining checks.
- Independent behavioral tests, including the queued cancellation/retirement race.
- Separate service source manifest and reviewed compatibility/packaging closure.
- CLI/supervisor lifecycle integration must obtain terminal original-owner proof;
  an HTTP close acknowledgement alone is insufficient.

### Acceptance boundary

Source/fixture/native/install and real-model acceptance are separate gates.
R159 is not complete while service lifecycle or package verification is pending.
No real-model route, model or budget is selected for this product yet.
Unknown lifecycle effects retain the same owner; no forced close or silent retry.

Plan: docs/P2-BORROWED-SERVICE-R159A1-PLAN.md.
Roadmap: docs/PRODUCT-ROADMAP.md.
Prior accepted status: docs/status-history/r159a1-parent.md.
