# AlazHarness continuous integration

## Scope: M0 preparation, not M1/M2 acceptance

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

This lightweight gate does NOT initialize, build, import or execute OpenClaw or
Hermes. It verifies their exact commit references, not downloaded source bytes.
There are no pip/npm installs, model calls or GitHub-hosted Actions jobs. Runtime,
upstream build and autonomy tests will be added as real components are implemented.

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

## HTTP mock-contract branch

New root tests in this branch also execute selected components and the HTTP client
against a loopback fixture. The existing immutable server image contains Node
24.21.0 and Python 3.11.2; Windows uses Node 24.19.0 and Python 3.14.3. No server
image, shared profile, memory limit or webhook changes are needed. Node 24 is now
required: its absence fails the suite, never silently skips the hybrid checks.

Every wire scenario is a separate root unittest case for structured CI counting.
The repository guard checks nine extracted source payload hashes. It does not
install or initialize a complete upstream runtime, prove server durability, or
constitute M1/learning acceptance.

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
python -B scripts/verify_components.py --with-vendor
python -B scripts/demo_hybrid_mock.py
```

For an isolated worktree without restored vendor, use `--with-vendor
--source-workspace <original-workspace>` to read exact pinned source bytes without
copying the source trees. The demo is an ephemeral loopback fixture only; it accepts
no real agent endpoint or model key, and shuts down before returning.
