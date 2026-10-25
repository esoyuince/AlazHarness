# AlazHarness - status

## R152A1 - COMPLETE: SCOPED_KERNEL_AND_RETAINED_LIFECYCLE_PASS

Updated: 2026-10-25T22:08:49.276750+03:00.
Code/evidence commit: 870da7ae310ca20ab4392aa7b998531056ee8384.
Feature branch: alaz/d3b-retained-acceptance-r152a1.
Exact code-commit alaz/local-ci: SUCCESS, observed 2026-10-25 19:08:07 UTC.
Native source pin: d1516731308de8e87130dc68124e69aad35d6911, unchanged.

Continuation after gated publication: main in
C:\Antigravity\AlazHarness\scratch\worktrees\main-published-21oct-a37c.
Live Git HEAD/ref state is authoritative. Root remains on its older branch with
existing user changes; no root status mirror was overwritten.

### Completed outcome

- native003: normal and controlled-error both PASS, exit 0.
- Actual original Landlock ABI3, fresh bootstrap and two fixed same-PID QA execs.
- Four primary baseline-to-EACCES denial pairs and four inherited observations.
- Same three database identities, owner epoch 1 to 2, exact saved result/usage
  replay without recomputation, one new physical-thread computation per scenario,
  and persisted/API equality with new owner epoch/generation 2.
- Three native connections physically close, retained receipt is captured while
  the caller lease is held, then the caller releases it.
- Source/dependency bytes unchanged. Both successful groups already empty without
  timeout/signal; successful trees removed only after all acceptance checks.
- native001 and native002 remain FAIL with raw evidence and original failed-tree
  preservation observations. No earlier attempt was replayed.
- Independent review: 115 recorded-data/source/hash checks passed. These are not
  additional runtime tests.
- Local static gate: PASS, exit 0; 6221 tracked files checked, 3638 tests discovered.
  No new full standard suite was run locally. Historical 3615 PASS / 23 SKIP is
  prior evidence. Exact remote CI success does not provide a new test count.
- Four exact frozen driver files retain an extra EOF blank line. The default
  whitespace result and successful path-scoped checks are in local-gate.json;
  executed bytes and global Git settings were preserved.
- Four QA scripts plus documentation/evidence only; product/native/config/source
  pins and installed dependencies were not changed.

### Evidence and accepted limits

Report: docs/D3B-LANDLOCK-RETAINED-R152A1.md.
Summary: evidence/d3b-retained-acceptance-r152a1/summary.json.
Raw accepted attempt: evidence/d3b-retained-acceptance-r152a1/native003/.
Independent review and exact code CI: independent-review.json and
publication-code-ci.json in the same evidence directory.

Initial lifecycle is unconfined; the retained second owner is under the explicit
laboratory Landlock policy. Only the declared AIAgent computation fixture is
doubled. Four optional IPv6 bind probes were denied and accounted for. Native
SQLite fallback/optional-module warnings remain in child stderr. API/handoff
equality is supported by hash-matched executed assertions with export/review
limits documented.

### Publication rule and next gate

Code/evidence is pushed and its exact CI succeeded. This final closure contains
documentation/publication metadata only. Its own exact HEAD CI must succeed
before ordinary fast-forward main publication. Final local/origin/remote main
equality and final-SHA CI are checked live; no force/squash/reset or service
deployment is part of publication.

Full projected launch/receive/target_main, privileged supervisor, separate UID,
zero CapBnd, namespace/network isolation, HTTP/provider, crash recovery and full
D3B remain NOT RUN. No root/bootstrap/mount/service operation or earlier denied
operation was retried.

Exact next product gate: qualify the current fixed projected launcher in the
existing authorized volume-supervisor context with original export, identity,
namespace, mount and native ownership checks. Current privileged installation
and invocation are not qualified; this component result does not authorize a
retry of earlier denied privileged actions.

History: docs/status-history/r152a1-parent.md, r152a1-prepublication.md and
r152a1-work-log.md.
