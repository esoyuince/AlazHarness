# AlazHarness - status

## D3B-NATIVE-RUN-HOOKS-H117B - SCOPED NATIVE PASS; FULL UNION PENDING

Harness branch alaz/d3b-native-run-hooks-h117b, base42b20e9. Original native feature
d0028f680f84298442269affd9c030dbe1fd4ffc extends cc16c10 on separate native worktree
hermes-run-hooks-h117b. Only runs.py + new run_observation.py; vendor main/source
locks/installed runtime unchanged. Patch/config under patches/hermes/h117b and
config/hermes-run-hooks-h117b.json with activation NOT_INSTALLED.

Actual decorated native /v1/runs now emits optional immutable ingress binding,
real Task creation/start/execution-return/retirement/done. No manually seeded
native task maps in QA. Replay/conflict/auth refusal emits no new admission.
Explicit thread-carrier/authority-watcher/external-watcher roles avoid pretending
a transport Task is the executor. Callback errors latch GAP, do NOT cancel or
replay business work. Synchronous-only bounded companion consumer attaches to
existing observer, but does NOT forge canonical owner publication or health.

20 actual-native cases PASS with dummy model/authority/external delivery edges.
12 consumer units +6offline receipts PASS. Native auth decorator exercised; no
HTTP transport listener.473 imported native modules source-matched, exact patch
apply and duplicate refusal proven. Original17-case failed auth fixture retained;
product auth unchanged. All467 prior harness sources unchanged. Full combined
standard regression PENDING original source integration with P117 independent QA.

P117 selects this SAME implementation and owns independent acceptance, not a
second channel. Next original harness commit, source-identical union full suite
and selective canonical delivery. Current producer notification subset is not
canonical executor integration: borrowed runner conflict remains, active-work
profile/mount/storage and HTTP/isolated health still OPEN. Native listener stays
CLOSED; installed pin eb75627, maincc7ceba/no push/CI/production/provider/root/WSL.
Previous blocked cleanup/refinement unchanged, NOT retried. Own native jobs all
terminal. Report docs/D3B-NATIVE-RUN-HOOKS-H117B.md; evidence/d3b-native-run-hooks-h117b/.
