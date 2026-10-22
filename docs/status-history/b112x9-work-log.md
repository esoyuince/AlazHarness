# AlazHarness - status

## D3B-API-BORROW-B112X9 - IN PROGRESS

Branch alaz/d3b-api-borrow-b112x9; worktree scratch/worktrees/d3b-api-borrow-b112x9; base31abe58. Qualify a narrow explicit borrowed-store constructor/selection/shutdown seam in the pinned native API adapter. Existing runtime and vendor main remain unchanged. Store three real native handles under caller ownership; no reconnect, hidden opens, routed profile fallback or borrowed close. Work/model/listener activation in borrowed mode stays explicitly refused until readiness/response-state lifecycle acceptance. No second gateway runtime.

Prepare source-hash-pinned patch, apply ONLY in an owned scratch export of immutable Hermes source, test real native adapter/ResponseStore/SessionDB/replay with new temporary files and no provider/network. Do not update sources.lock or installed submodules, main/push/CI/production. Existing427 source baseline captured. Prior status archived docs/status-history/b112x9-parent.md.

Next inspect ownership side effects, implement minimal default-compatible opt-in patch and exact artifact application checks, test wrong home/invalid handles/reuse/cancellation/drain/refused close. Prepared response schema, integration into A109 and healthy/busy policy remain separate unless explicitly qualified here. No test pending yet.


### Complementary scope selected

Concurrent A112X7D owns the native fork borrowed-store patch including canonical SessionDB reuse from ResponseStore. This branch no longer proposes a separate product patch: own unexecuted draft+manifest are archived under evidence and removed from deployable paths. New work is independent real native constructor/open/close/cancellation/lock-preservation QA against selected patch and original baseline. No parallel sources modified; existing installed vendor/main/source lock unchanged.


### Responsibility reconciliation

Read latest A112X7D refinement: that task has selected ONLY ResponseStore canonical-state borrowing and leaves API constructor/selection/drain seam to this branch. Therefore B112X9 retains its adapter seam as the single selected implementation, with the archived draft as history; A112X7D response-state component is complementary, not a second adapter. Restore and harden own patch, do not rewrite other source. Add explicit compatibility with its canonical-state view, test actual native adapter and ResponseStore together on isolated source snapshots. No listener/work/model activation.


### B112X9 native checkpoint

Original response and borrowed response Linux comparisons terminal exit0: original extra canonical read connection observed (no lock corruption), borrowed0 extra connections; committed terminal settles while EXCLUSIVE owner lock stays BUSY to competitor; uncommitted terminal and TEMP shadow do not settle; caller close releases lock. First missing-BEGIN fixture failure retained. Adapter001 did not reach test setup because Windows unittest loop socketpair was rejected by test-only audit; fixture now permits local loop construction only and reruns002 with actual native stores. No product network allowance or listener enabled. Current adapter002 request020 pending; do not repeat while running.
