# AlazHarness - status

## R159A1 - source delivery complete; daily service plan IN PROGRESS

P1 remains DONE. P2 is IN PROGRESS. P3-P5, full D3B, M1 and production are OPEN.
This packet completes the native transport, concrete host service owner and
queued-cancellation source/test connection. The original R159 plan remains open:
installed daily CLI start/close, a long-lived supervised child/control protocol,
a fresh P2 installation and one explicitly budgeted real-model task are NOT RUN.

Active branch: alaz/p2-borrowed-service-r159a1.
Harness parent: 37620d5c14afee895b16e3441f7a7ed14b77e7d7.
Native parent: d1516731308de8e87130dc68124e69aad35d6911.
Native feature: 5e3635c2cdfc2161fd20c089618bd7f2a7c12f2d, normally pushed to
esoyuince/hermes-agent on the same named feature branch; fork/upstream main unchanged.
Primary worktrees: scratch/worktrees/p2-borrowed-service-r159a1 and
scratch/worktrees/hermes-borrowed-service-r159a1.

### Implemented and reviewed

- Explicit one-shot 127.0.0.1 transport on the original runner, adapter, authority,
  epoch/instance, loop and three stores. Only native GET/events/Stop plus the
  existing Host Gate and execution routes are installed. Ordinary background
  startup and default-profile metric persistence are not started by this path.
- A concrete BorrowedServiceOwner gates external Host Gate submission on the
  overall service READY state, including the actual SQL write boundary. Drain
  retains existing observation/Stop. Status rechecks ownership and native phase.
- Retained outer/inner HTTP handlers, awaited SQL threads, physical workers,
  canonical ledger obligations and native session observers prevent premature
  listener retirement. Pre-effect busy preserves DRAINING; unknown effects retain
  the original owner. Listener/runtime/API/drain/detach/executor/three physical
  stores/profile lease close in order. Image release remains supervisor-owned.
- Fixed queued Stop's late stopping-marker race. Exact canonical queued evidence
  is validated by the client as an admission-specific server report; no global
  physical-worker proof, resend or repair permission is inferred.
- Separate 760-file service selection/manifest and five-path Host Gate lock pin
  exact native Git blobs. Historical finite/retained selections, default host lock,
  execution lock and the accepted R156 installation remain unchanged.
- Nine exact parent source archives preserve historical receipt identity. Old
  expected digests/outcomes remain unchanged; new source acceptance is separate.

### Verification

- Native official runner: 27 new PASS (22 transport, 5 queued) plus 34 selected
  existing PASS (8 bind, 23 active-work drain, 3 ordinary metrics); no skips/errors.
- Native official Ruff PASS. Native source-health on 11 paths: 0 blocking/advisory.
- Linux host service: 31 PASS; native lifecycle interfaces are doubled, while
  harness guards/SQLite/threaded work are real fixtures.
- Linux client/recovery/queued contracts: 58 PASS, 0 skips/errors. Original launcher,
  interpreter and process exit were not retained in that earlier log; explicit
  primary Windows command/terminal receipt is now separately recorded.
- Historical provenance: 12 PASS (six new plus six R158).
- Primary Windows focused regression: 235 run, 218 passed, 17 skipped, 0 failures,
  0 errors; terminal exit0. Sixteen skips require unavailable aiohttp; one is the
  POSIX SIGINT case. This is not installed native-service qualification.
- The partial export's earlier broad host run had 117 successful methods / 118 run,
  one method error and one separate class-setup error from absent evidence files.
  The full primary run above resolves those missing-evidence cases; its raw failed
  precursor remains preserved, not rewritten to PASS.
- Two deliberate old-target failures establish the queued marker regression after
  restoring only d151 authority-runs in a disposable mixed-supporting-generation
  copy. This is bounded regression evidence, not old installation acceptance.

### Git and CI handoff

All source/test transfers use verified parent/current hashes. Native feature
publication and exact 760-blob source generation are recorded in
`evidence/p2-borrowed-service-r159a1/native-publication.json` and
`primary-source-selection.json`. Static checks/discovery have a separate record;
static discovery does not count as test execution.

The exact final harness commit, full required alaz/local-ci result, feature/main
refs, post-main CI, clean worktrees and protected root33 hashes are carried by:
`scratch/r159a1-publication/final-publication.json` in this primary R159 worktree.
Read and verify that final handoff against live Git before continuing. A successful
full exact-commit CI is required before normal fast-forward main publication.
The journal avoids embedding this commit's own hash inside its tracked contents.
Git publication is not deployment to the accepted P1 installation.

### Next concrete work

Continue the existing R159 plan with a deliberately long-lived supervised service
entry and separate ready/control/final-receipt channel. The current finite child
lifetime, mount-worker idle limit and single final stdout protocol do not provide
that daily service. Bind CLI start/close to this original owner and its terminal
receipt; an HTTP close ACK cannot prove later child/store/image retirement.

Then build a separate P2 candidate containing Node/runtime and the selected Python
closure, accept its full localhost flow in one fresh installation, and select a
single route/model, small allowed .txt task and explicit call/token/micro-USD caps
before a real model run. No real model/route/budget has been selected or used.
No provider or model call occurred in R159; no existing user service was adopted.

### Work log and evidence

- R158 handoff, protected repositories and original root33 verified; isolated
  R159 worktrees created. Parent status: docs/status-history/r159a1-parent.md.
- Initial scope: docs/status-history/r159a1-source-start.md.
- Source/test checkpoint: docs/status-history/r159a1-source-checkpoint.md.
- Source delivery: exact native commit, reviewed source selection, focused native,
  host/client/provenance tests and primary regression recorded above.
- Final publication: exact-commit CI and protected-root closure must be read from
  the final-publication journal identified above.

Report: docs/P2-BORROWED-SERVICE-R159A1.md.
Plan: docs/P2-BORROWED-SERVICE-R159A1-PLAN.md.
Roadmap: docs/PRODUCT-ROADMAP.md.
Evidence: evidence/p2-borrowed-service-r159a1/ (raw logs and independent reviews).
