# Contributing to AlazHarness

This is an early OpenClaw/Hermes hybrid harness project. Read `AGENTS.md`,
`CURRENT-STATE.md` and `docs/MVP-v0.1.md` before changing the design.

Use a focused branch and include a reproducible test with behavior changes.
Do not silently update vendor pins, remove upstream notices or include personal
agent state, model keys, private infrastructure settings or unrelated files.
New contributions are provided under the root MIT license; upstream files retain
their original licenses and attribution.

## Checks (Python 3.11+, Node 24+ and Git)

```sh
python -B -m unittest discover -s tests -v
python -B scripts/ci_check.py
```

The second command checks tracked/indexed paths. Stage explicitly selected new
files before running it locally; it never stages or commits anything itself.
Full source verification is separate: see `docs/CI.md`.

CI runs on maintainer-managed infrastructure, not GitHub-hosted Actions.
Unreviewed fork pull requests and draft pull requests are not automatically run
on that server. A maintainer must review a contribution before moving its exact
commit to a trusted branch. Never solve a red check by bypassing assertions.
There is no automatic deployment, model call or autonomous agent loop in CI.
