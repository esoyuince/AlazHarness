# AlazHarness - status

## R152A1 - SCOPED_KERNEL_AND_RETAINED_LIFECYCLE_PASS

Checkpoint: 2026-10-25T22:00:14.788443+03:00. Branch: alaz/d3b-retained-acceptance-r152a1.
Starting main: 8aae47fb7efa94fbfb45b22018747d4bb3178c2a.
Native pin: d1516731308de8e87130dc68124e69aad35d6911 (unchanged).

### Completed

- native003: normal + controlled-error scenarios both PASS, exit 0.
- Original current Landlock ABI3 survives the fixed QA exec; four primary denial pairs and four inherited observations.
- Same retained three databases, epoch 1 to 2, exact prior result/usage replay without computation, one new computation per scenario, persisted/API equality and epoch/generation 2.
- Original owner closes all three connections; retained receipt captured before caller lease release. Both owned groups already empty; no timeout/signal.
- Source/dependency hashes unchanged. Only successful fresh trees removed after complete acceptance. native001/native002 failures and original preservation observations remain recorded.
- Independent review corroborated 115 recorded-data checks. This is not 115 new runtime tests.
- Four QA scripts plus documentation/evidence; no product/native/config/pin/installed-dependency changes. Root user changes preserved.

### Evidence and limits

Report: docs/D3B-LANDLOCK-RETAINED-R152A1.md.
Evidence: evidence/d3b-retained-acceptance-r152a1/summary.json and native003/.
Review: evidence/d3b-retained-acceptance-r152a1/independent-review.json.

Initial lifecycle is unconfined; retained second owner is under explicit laboratory Landlock. Only the declared AIAgent computation fixture is doubled. Four optional IPv6 probes were denied and accounted for; this does not establish network isolation. Native SQLite fallback/optional-module warnings remain in raw stderr. API/handoff equality is supported by executed hash-matched assertions, with the export limits documented.

Full projected launch/receive/target_main, privileged supervisor, separate UID/zero CapBnd, namespace/network isolation, HTTP/provider, crash recovery and full D3B remain NOT RUN. No root/bootstrap/mount/service action or earlier denied-operation retry occurred.

### Publication and next gate

Local staged-source gate and exact target-commit CI are next; ordinary fast-forward main publication follows only after those pass. Historical 3615 PASS / 23 SKIP is not a new local suite run.

Next product gate: qualify the exact current fixed projected launcher in the existing authorized volume-supervisor context with original export, identity, namespace, mount and native ownership checks. Current privileged installation/invocation is not qualified; this component result does not authorize retrying earlier denied actions.

History: docs/status-history/r152a1-parent.md, r152a1-prepublication.md and r152a1-work-log.md.

### Local publication gate — 2026-10-25T22:03:59.559263+03:00

Static gate PASS (exit 0): 6221 tracked files, 3638 tests discovered, no test execution. Scoped whitespace checks PASS; four exact frozen driver files retain their extra EOF blank line to preserve executed bytes. Default check/exception recorded in local-gate.json. Feature commit/push and exact-SHA CI are next.
