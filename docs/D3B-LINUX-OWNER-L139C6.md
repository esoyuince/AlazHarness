# L139C6 — Actual Linux finite work and owner close

## Decision

PASS for two fresh-profile finite lifecycles on the actual ordinary Linux owner:
normal bounded computation and controlled computation failure both settle through
native code, preserve exact-retry identity, close the three original connections,
and leave profile release to the caller. No operating-system or lifecycle method
is replaced. Only AIAgent factory/computation/close is an explicit finite fixture.

NOT ACCEPTED for reopening that profile after its first work, full active kernel
confinement, authenticated HTTP, real AIAgent/tool/memory-manager/provider use,
crash recovery, power-loss durability, or complete M1/M2. These are separate gates.

## Exact source and environment

Base0b20f61 includes the prior Linux import prerequisite; published main remains
f08fab0. Optional native d1516731308de8e87130dc68124e69aad35d6911 is transported by
exact755-source manifest. Original product files, source selections, cold layout,
11patches, installed vendor and source lock are unchanged. No new system package
or service configuration. Existing Linux dependency payload has1162file hashes
matching the previous accepted installation; transport verifies all before use.

Dedicated AlazHarness-D3B-P71C, alazgateway UID23001/GID23003, isolated Python3.12
interpreter. Fresh temp transport/profile/scratch, umask077, actual ext4 observation.
No root, mounts, namespaces, listener or installer is started. The unchanged mount
and namespace identities prove no reconfiguration here, NOT process confinement.
The audit hook is a fixture effect limiter, not a hostile-code security sandbox.

No config.yaml was needed. The original native provider-selection environment
supports the openai alias with a dummy key and loopback port9; the fake model alone
performs the calculation. Network calls remain refused. This solves the test's
configuration requirement without adding a forbidden profile file, altering the
layout gate, overriding config loaders or assigning a private runtime selection.
The earlier source-review concern was not a product failure needing a relaxation.

## Real sequence, normal and error

Each scenario first prepares a fresh trusted three-store fixture with ordinary
native constructors, closes it, and releases initial ownership. Then the actual
ProfileLease observes real Linux metadata/mount identity and reserves the profile.
NativeStoreStartup uses both fixed separate read-only helper processes before
opening its own three writable handles. All six cold/live checks run, then one
accepted epoch advances from0to1. No forged metadata or cold-helper mock is used.

The original consumer selects finite mode, publishes its same native API adapter,
and activates local admission. Real run_api_turn/authority/finite/TurnRunner execute
on an actual non-main worker thread. For SUM:17,25,8 the bounded model returns50;
result persistence and terminal/completed settlement are native. In the second
scenario the model throws the declared computation error and native settlement
records terminal/failed and completed=false. Neither case writes terminal SQL from
the test. Trace stacks identify native commit_and_publish->settle_session_input.

Exact retry returns the same result with computation count still1 in both cases.
Different content under the same request ID is rejected as admission_conflict.
Each model receives the original caller-owned primary SessionDB. No additional
state.db connection is opened during the turn.

After settlement: begin_drain -> native retire_idle_runtime -> native session
retirement -> finish_drain -> API/runner detach -> original owner closes stores.
SQL total_changes stays unchanged during retirement/detach, the native registry
has zero references BEFORE fixture cleanup, the model close surface is invoked,
and all three connections physically reject further SQL. The caller's real lease
remains held until its own finish(). Both profile and transport temps are removed.
Fifteen nested checks per scenario pass; these are not thirty independent runs.

Raw result/transport outputs and source hashes for owner001/002 are retained.
Both executions use the identical driver and bundle, only the explicit error flag
changes. Normal721 and error718 actual native imports match immutable d151 Git and
the selected manifest; union721. This is not the full dependency dynamic-call map.
One bind attempt is refused during imports; the captured stack names _has_ipv6.
It is recorded rather than hidden under an assertion of no attempted effects.

## Actual cold-restart boundary

Normal work creates native helper state outside the old cold store-only layout:
cache/tool_discovery_cache.json and runtime/active_sessions.json plus its lock.
These remain after normal connection closure. No test deletes them to make the
second startup appear accepted. The old strict layout intentionally rejects them.

A separate control performs a full fresh normal lifecycle, then reserves the same
profile and calls a second actual NativeStoreStartup. It is rejected with cause
NativeLayoutRejected/native_layout_unexpected_entry BEFORE writable stores or a
new epoch. All three database file hashes remain identical. This is a reproduced
product-integration gap, not a successful restart or a data-loss incident.

The first control itself was wrong: it requested owner.expectation after closing
the old owner/lease, and correctly received profile_lease_finished before restart.
Its raw failure and original driver are preserved. The corrected control captures
the immutable accepted expectation while the first owner is VERIFIED and reuses
that value for second startup. Assertions and product code are unchanged. The
corrected control's exit0 means the expected refusal was observed, NOT restartPASS.

Next design a narrow explicit persisted-active-layout contract or supported native
auxiliary-state retirement path. Preserve durable session/job/result history and
verify legitimate helper files rather than silently expanding the old layout,
clearing records, changing epoch assertions or treating all runtime files as safe.
Only then claim retained-profile restart, and apply the existing kernel projection
and authenticatedHTTP acceptance to that exact selected source.

## Independent real boundary checks

Q139R6 ran one separate ordinary-user Linux boundary experiment with18nested
predicates: real modes/layout, forbidden config, wrong mount, foreign thread,
wrong cold schema before parent write, three outstanding transactions blocking
close without rollback, exact handles and caller lease order. No model/finite
job was run by that test, no OS/product method doubled. Exact original source,
raw result and provenance are copied under independent-q139r6; its original
worktree and Git history are unchanged and not merged. Copying results is not a
new experiment. Nine L139 offline receipts bind both finite results, restart gap,
source identity and independent evidence; these are standard-suite subsets.

## Regression and handoff

All605baseline source/config/test files remain byte-exact; new code is three QA
scripts and one offline test file only. Current exact complete standard run and
static result are recorded separately; do not infer them from the Linux result.
Raw prior failures and23historical Windows skip IDs/reasons stay unchanged.
Main staysf08fab0, installed nativeeb75627,33dirtyroot user files preserved.
No automation or delegated work started by this lane. Read status.md and the
terminal delivery record for commit/full-test outcome and exact next work.

## Terminal complete standard regression

New full standard3464=3441PASS/23SKIP/0ERROR/0FAIL, actual commandf139c601...000016 exit0.609 source/config/test hashes and11patches remain identical. All605baseline files unchanged. Nine new offline receipts are included in the full count, not new Linux runs. Same23skip IDs/reasons preserved. The passing full suite does not change the recorded restart refusal or add kernel/HTTP acceptance.

## Local delivery

Tested commit `7559b6befbfc0e2583733fb25e9d0e1b7d08c63c` contains exact current QA and evidence. Full3464=3441PASS/23SKIP exit0 and local staticPASS. All609source/config/test and11patch hashes rechecked after commit. Final handoff adds documentation only. Local/remote main remainsf08fab0; this branch is not pushed, native feature not installed. The reproduced restart refusal remains open. Root33user-file bytes/status and installed native verified preserved.
