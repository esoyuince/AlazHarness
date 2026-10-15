# Selected upstream components

OpenClaw: Copyright 2026 OpenClaw Foundation; MIT license retained at
`upstream/openclaw/LICENSE`. Four complete TypeScript source modules are reused;
only the deadline module import specifier is localized. Node 24 executes erasable
TypeScript directly; there is no npm install or manual rewrite of behavior.

Hermes Agent: Copyright 2025 Nous Research; MIT license retained at
`upstream/hermes/LICENSE`. The complete iteration-budget and pure identity modules
are copied unchanged. `terminal_run_status` is an AST-selected, unchanged function
with explicit typing imports. These Python modules exercise the fixture boundary
and are not a replacement for `AIAgent` or the canonical SessionAuthority.

Exact source paths, commits, transforms and SHA256 values are in
`config/components.lock.json`. Run `python -B scripts/verify_components.py
--with-vendor` from the repository root to compare against the pinned source.
The code under `upstream/` retains its original MIT attribution. AlazHarness owns
only the adapter and new tests. Upstream full test suites have NOT been run.

The OpenClaw helpers are private upstream contracts. Updates require explicit
pin review and our contract suite, not an automatic moving SDK dependency.

HYB-004B adds Alaz-owned run-recovery.mjs and recovery_inspector.py. They do not modify upstream bytes; the local inspector reuses the selected Hermes identity and terminal helpers. Schema provenance is config/recovery-inspector/source-lock.json. The host contract is version1, readonly and does not authorize retries or data repair.
