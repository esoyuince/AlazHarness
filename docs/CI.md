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
hashes and transformations are checked against components.lock.json in CI without
initializing submodules. `verify_component_slices.py --full` separately checks the
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
