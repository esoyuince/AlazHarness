# AlazHarness continuous integration

## Scope: M0 preparation + selected-component mock tests, not full M1/M2 acceptance

The `alaz/local-ci` GitHub commit status is produced by the existing maintainer
Local CI service. GitHub is the canonical source. The service fetches a bare
mirror, checks out the event's exact SHA and runs a resource-bounded Docker job.
Only status metadata is sent back. No source push or deployment is performed.

Initial profile: immutable infrastructure image, 1 CPU, 512 MiB RAM, 768 MiB total
RAM+swap and a 180-second job timeout. Existing server-wide limits are unchanged.
The actual deployment profile and its image digest are versioned in the private
infrastructure repository; private addresses, keys and backup paths stay there.

The job runs all root `tests/test_*.py` tests through an external read-only
structured unittest reporter, then checks source-lock/gitlink consistency,
exact allowed submodule URLs, required public documents, safe example settings,
root Python syntax, JSON validity and secret/runtime file hygiene. Zero discovered
tests fail the repository gate. Reports use `.alaz-ci/`, which is Git-ignored.

The root publication gate does not initialize or build full vendor applications.
The test suite additionally executes copied OpenClaw cancellation/deadline helpers
and Hermes StdioTransport/IterationBudget with a SCRIPTED Python peer. Node 24+
is now required alongside Python 3.11+ and Git; the existing CI image supplies it.
It does not construct the real Hermes AIAgent or full OpenClaw Gateway. No pip/npm
installs, model calls, live tools, scheduler or autonomous goal loop are involved.

The copied source files are root-tracked, license-preserving components. Their
hashes and transformations are checked against config/components.lock.json in CI without
initializing submodules. `verify_components.py --with-vendor` separately checks the
original pinned local vendor bytes. Test status applies to this scoped component
slice, not to full application, sandbox, persistent recovery or learning acceptance.
Node tests are invoked one case per unittest so structured counts stay inspectable.

## Reproduce locally

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

## Full pinned-source check (separate developer gate)

```sh
python -B scripts/restore_sources.py --apply
python -B scripts/verify_workspace.py --deep
python -B scripts/verify-source-snapshot.py
```

`restore_sources.py --apply` downloads only the pinned public submodules and sets
up upstream remotes. It does not install agent dependencies. It refuses dirty
source worktrees. The other two commands verify restored bytes and Git objects.

## Trust and operations

External fork PRs, drafts and PRs changing workflow files are blocked by the
server before running project code. Public contributors run tests locally; a
maintainer reviews them before execution on trusted branches. CI configuration
changes require private infrastructure review, validation, backup and exact-SHA
live acceptance. A written profile alone is not proof of a successful live run.

Do not assume this Docker job can safely execute hostile code: the trust gate is
intentional. Before opening execution to public forks, use separate disposable
workers with a separately reviewed isolation and network policy.

## Portable Node syntax gate

Node's file-extension handling for `--check file.ts` differed between the tested
Windows and Linux binaries. `scripts/check_node_syntax.mjs` now parses erasable
TypeScript with Node's built-in stripTypeScriptTypes and syntax-checks the result
as ESM on stdin, without executing the source. This is a syntax check, not a
TypeScript static type check. Runtime tests still execute the copied .ts modules.

## Integrated stdio and HTTP tests

Ten unique upstream payloads, including both licenses, are checked by the single
verify_components.py implementation. Both suites report individual unittest
cases. Use --with-vendor --source-workspace <original-workspace> to compare the
original pinned files from an isolated worktree.

The real AIAgent probe is explicitly separate: run_native_hermes_probe.py requires
an already prepared Python environment and a fresh output directory. Default CI
never installs Hermes dependencies or invokes a real model. A dependency-build
receipt is not a runtime-acceptance receipt.

## REF-PI-001 distinction

The root suite adds stdlib Python launcher guards and Node host-gate unit tests.
It does NOT install or execute Pi. Actual pinned Pi native runs are an opt-in
Windows gate via scripts/run_native_pi_suite.py and documented separately in
docs/research/REF-PI-001-NATIVE.md. Six native scenarios were repeated twice; their
12 receipts are not added to the root unittest count.

## REF-PI-002 native versus default CI

The default suite now contains171 root tests, including25 offline Durable
evidence/identity/counter guards. It does not import or run native Pi. The9
real SQLite/Harness scenarios (18 runs) are opt-in local Windows evidence and
are not included in the171 count. No server policy, dependency installer or
secret mount was added. Exact commit CI status must still be read after push.
See docs/research/REF-PI-002-SQLITE.md for scope, fault injection and limits.

## REF-PI-002B reconciliation

Both Durable characterization suites are retained with separate historical receipts.
The 4c9f suite adds storage-after-commit/ack-loss and provider identity; the ac97
suite adds a non-idempotent safe negative control and an independent SQLite effect
counter. Prior 169/171 or native18 totals are not added into a new acceptance claim.
All current standard tests will be rerun. status.md is the live handoff owner.

## REF-PI-002B separation

Root CI includes the reconciled previous validator tests and the new strict-JSON,
owner identity and independent-evidence unit tests. Native Pi admission24 runs and
independent SQLite QA12 cases are opt-in local gates, not part of the248 root tests.
The CI image/profile, resource bounds and no-install rule were not changed.

## REF-OC-001 scope

The offline suite adds21 launcher/projection/receipt tests without installing Effect or OpenCode. The35 selected-source component scenarios run twice only through the explicit prepare_opencode_components.py / run_opencode_components.py flow, using pinned Effect and fixture external services. Neither these local70 runs nor TypeScript runtime transpilation are a full OpenCode application build/typecheck/HTTP authorization test. See REF-OC-001-COMPONENTS.md.

The supplementary independent OpenCode QA adds11 offline receipt tests. Its20 source-component observations use explicit fixture ports and are a separate opt-in gate; standard CI does not run them. The final combined root suite count is recorded per exact commit, not inferred by adding native experiment totals.

## Native Gateway opt-in

`run_native_gateway.py` real Gateway boot/authority/API/read_file testidir; model sunucusu kontrollü localhosttur. `test_gateway_probe_contract.py` yalnız makbuz ve process sahiplik kurallarını offline sınar. Standart sunucu CI native Gateway ortamı kurmaz; native koşular ayrı kanıt dosyalarında tutulur. Rapor: docs/HYB-003-GATEWAY.md.
