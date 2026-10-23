# P117N1 - independent selected native producer acceptance

## One selected implementation

H117B owns the native source patch and gateway_native_run_provenance consumer.
This branch supplies independent tests and evidence only; no competing scheduler,
observer channel or consumer is selected. Original source commit and patch hashes
are recorded in selected-commit-verification.json. Installed native pins remain
unchanged; this is an optional staged source artifact, not a running endpoint.

The actual native decorated /v1/runs handler computes immutable scope/key/request
fingerprint and publishes ACCEPTED/CREATED/STARTED/EXECUTION_RETURNED/RETIRED/DONE
through an explicit local channel. The original native code owns task maps,
status, worker submission, deduplication and retirement. QA does NOT populate
those maps or call observation notifications. Native request authentication is
executed with an owned fixture bearer; a missing bearer returns401 without work
or provenance. No listening HTTP server or full middleware stack is started.

The role distinguishes executor_thread_carrier, canonical_authority_observer and
external_owner_observer. An API Task may wait for another executor. Neither a
source event nor the provenance consumer proves canonical execution health.
The original strict Task observer remains unchanged and cannot treat an active
unqualified worker/watcher as a valid idle/healthy owner. Positive service health,
dispatch, replay and store release remain unauthorized.

## Independent current native cases

20/20 methods passed on the exact selected H117 native source, using actual native
adapter/stores/handler/scheduler/Task cleanup. Only agent computation and explicitly
identified external-owner boundary are doubled; no model/provider call is made.
Normal complete lifecycle, immutable expected identity, absent/invalid bearer or
key, replay without second work, unkeyed input, disabled default, JSON unable to
enable hooks, callback exceptions/async-result refusal, and explicit listener
refusal are covered. Native closure of its task map is observed, not simulated.

Two independent cases throw asyncio.CancelledError from the observation callback
at admission and retirement. The channel latches GAP without cancelling business
work or skipping native cleanup. A cancelled carrier Task can be DONE while its
actual native worker is still alive; that distinction is recorded, not called
execution completion. An unsupported eager task factory gaps observation rather
than inventing trustworthy order, while default business execution is retained.
The live provenance consumer receives actual events and never grants executor
health. This is not active-work storage/profile/mount or isolation acceptance.

All501 actually imported native modules were matched independently to immutable
native feature d0028f680f84298442269affd9c030dbe1fd4ffc. The existing cc16 prerequisite
and two changed native file hashes are separately retained. No test-time product
monkeypatch installs these hooks: the source files themselves are patched. The
agent computation double and external receipt double remain explicitly named.

Six offline receipt methods verify current source hashes, raw20 case logs,
automatic producer phases, no duplicate execution and scope limits. These are
not six extra native executions. The H117 original20 native methods overlap and
must not be added to ours as40 unique scenarios. One complete selected-union
standard regression is required; neither focused result substitutes for it.

## Preserved earlier results

P117 drafted a competing smaller channel before detecting parallel H117 work.
Its20 passing native methods and10 units apply ONLY to that superseded draft.
All original source bytes are retained as .txt evidence; draft product/QA/test
files were removed from executable selection. The own native review worktree
was then copied to exact H117 source for independent acceptance; H117 worktree
was not edited. Only the original H117 native commit/patch may be promoted.

The initial17-method fixture had3PASS/14ERROR because the fake request omitted
configured bearer/audit metadata. That FAIL remains recorded. Auth was not
mocked/disabled; fixture metadata and an explicit401 control fixed the test.
A pure cancellation red/green check belongs to the old draft; a preliminary
missing-dependency import failure was not called behavior failure. Current
selected implementation independently passes both cancellation boundaries.

## Remaining gate

Native source publication is no longer manual QA. It still reports carrier/waiter
provenance, NOT verified canonical executor ownership. Bind the actual native
SessionAuthority/worker execution lifecycle, independently validate active profile/
mount/storage, then test the same task path under isolation before active-work
HTTP. Current cold/quiescent gates and borrowed listener refusal stay unchanged.
No root/WSL/blocked-cleanup retry, paid/model/provider, main/push/CI or production
change occurred. Earlier blocked independent cleanup remains explicitly OPEN.
