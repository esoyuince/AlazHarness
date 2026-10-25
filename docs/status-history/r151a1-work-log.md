# AlazHarness - status

## R151A1 - actual unprivileged self-identity kernel validation IN PROGRESS

Active branch alaz/d3b-self-identity-kernel-r151a1.
Path C:\Antigravity\AlazHarness\scratch\worktrees\d3b-self-identity-kernel-r151a1.
Baseline/main 665330a0249ea8ee9396ff8c391b959fc3ca8505.
One writer R151A1. Prior status retained in docs/status-history/r151a1-parent.md.

### Scope

Prepare bounded disposable ordinary-user Linux children running the unchanged
credential_guard.apply and principal_launch.observation. Validate the selected
current-PID uid_map/gid_map reads and default/foreign-process/sensitive-proc
denials with actual Landlock. Test artifacts belong to this worktree.
No root bootstrap, namespace/mount setup, provider, service, profile-store or
installed native changes. Prior denied operations are not retried.
This component witness cannot accept fixed projected exec/start/close or fullD3B.

### Current evidence

Main and root Git status captured in evidence/d3b-self-identity-kernel-r151a1/baseline.json.
Fresh isolated worktree created successfully from exact accepted base.
Current-code source hashes recorded. Kernel experiment NOT RUN.
Existing R150 full suite was 3615PASS23SKIP and is historical, not rerun here.
Inspect environment and review the complete bounded driver before execution.

### Work log

- Initial: recovered current accepted main665330a, created this isolated worktree.
- No unknown effect is rerun. Every native request must reach terminal receipt.

- Preflight: ordinary UID23001/GID23003, Python3.12.3, real WSL Linux6.6.87.2, Landlock ABI3; read-only probe exit0.
- native001 bundle prepared, SHA256 12817fcdfec6420bc3b538d69d0a753304cff334f6f03e9948aa501bdc8fd952,21460bytes; kernel enforcement NOT RUN.
- Same-SHA main665330a alaz/local-ci SUCCESS observed from GitHub API.
