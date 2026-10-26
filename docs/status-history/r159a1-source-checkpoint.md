# AlazHarness - status

## R159A1 - IN PROGRESS: source verification complete, publication pending

P1 remains DONE. P2 is IN PROGRESS. P3-P5, full D3B, M1 and production are OPEN.
The R159 service plan remains open: this source packet implements the original-owner
native loopback transport, concrete host service owner and queued-cancellation proof.
Installed daily CLI start/close, a long-lived supervised child/control protocol,
a fresh P2 installation and a selected bounded real-model task are NOT RUN.

Active branch: alaz/p2-borrowed-service-r159a1.
Harness base: 37620d5c14afee895b16e3441f7a7ed14b77e7d7.
Native base: d1516731308de8e87130dc68124e69aad35d6911.
Primary worktrees: scratch/worktrees/p2-borrowed-service-r159a1 and
scratch/worktrees/hermes-borrowed-service-r159a1.

### Verified source checkpoint

- 18 harness source/test files and 11 native source/test files transferred to the
  isolated primary worktrees with read/hash preconditions and exact final readback.
- Native official runner: 27 new cases PASS (22 transport, 5 queued cancellation).
  Selected existing native regressions: 34 PASS (8 bind, 23 drain, 3 metrics).
- Host service tests: 31 PASS. Client/recovery/queued tests: 58 PASS.
  Historical archive/provenance tests: 12 PASS. Native Ruff PASS; source-health
  engine on 11 paths: zero blocking/advisory findings.
- One expected old-target regression check: two FAIL at the queued stopping-marker
  defect after restoring only exact d151 authority-runs source in a disposable copy.
  Current tests pass. This mixed-supporting-generation check is not old-install acceptance.
- Host broad regressions in the partial export: 117 successful methods / 118 run,
  one method error plus one separate class-setup error from absent historical
  evidence files. Full primary/CI validation is pending; this run is not PASS.
- Raw logs, exact hashes, test scope and early failed-run corrections are recorded
  under evidence/p2-borrowed-service-r159a1. No provider or model was called.

### Publication and remaining work

Native exact source commit and feature-only push, the separate 760-file service
manifest/selected host lock, full harness CI and fast-forward publication are pending.
The old P1 source manifests, host lock and existing installation remain unchanged.

After this source packet, continue the existing R159 plan with explicit long-lived
supervisor ownership and a separate control/final-receipt channel. An HTTP close ACK
cannot prove the listener, physical stores, child and image owner have all retired.
No user model/route/budget has been selected; source/fixture work does not need one.
Unknown effects retain their original owner and do not permit forced cleanup/retry.

### Work log

- R158 handoff and protected roots verified; isolated R159 worktrees created.
  Prior accepted status: docs/status-history/r159a1-parent.md.
- Initial scope/acceptance record: docs/status-history/r159a1-source-start.md.
- Source checkpoint: implementation and focused checks above complete; publication pending.

Plan: docs/P2-BORROWED-SERVICE-R159A1-PLAN.md.
Roadmap: docs/PRODUCT-ROADMAP.md.
