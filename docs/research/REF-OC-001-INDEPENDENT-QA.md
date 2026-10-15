# REF-OC-001 — Independent source-module QA (5a5c)

**20/20 component observations PASS; direct product adoption NOT ACCEPTED.**
This is supplementary evidence on the primary `alaz/ref-oc-001-8ea1` branch,
not another product implementation, permission layer, or execution engine.
OpenCode source commit: `3943b84ef00e83dbc3c48e6a92b02f0d88fb35f9`.

## What really executed

The unchanged Permission and EventFeed source files are imported directly using
a Node resolution hook. Node's built-in TypeScript transform handles runtime
namespace syntax; code bodies are not reimplemented. Real Effect4.0.1, actual
OpenCode schema dependencies, Wildcard and protocol event classification execute.
The exact Effect archive integrity matches the pinned upstream bun.lock; the
prepared dependency tree is hashed before and after, without a new install.

Six dependency ports (Bus, Location, Agent, SessionStore, PermissionSaved,
PluginHooks) and the app-node binding are explicit fixtures. They supply data,
configuration and event callbacks; they do not replace the permission methods or
the EventFeed queue. Real database persistence, full server boot, HTTP routing,
authentication, OS isolation and actual network interruption are NOT tested.
There are zero model/paid-service calls. No existing user profile is imported.

## Permission findings (12 separate observations)

Configured deny is applied before saved approvals and the plugin hook. A rejected
batch clears only pending requests in that session. Duplicate currently pending
IDs are rejected without replacing the original. Once-only replies cannot be
applied a second time while the ID is absent. Closing rejects current waiters and
new asks; interruption removes the pending prompt.

The following are observed boundary requirements, not assertions of remotely
exploitable defects in the full OpenCode product:

| Observation | Narrow result | Requirement before Alaz use |
|---|---|---|
| Empty resources | The service returns allow, including with wildcard deny configured. | Reject empty meaningful protected-operation inputs before evaluation. |
| Mutable caller input | Mutating the original save array after ask changes the scope later saved by always. | Snapshot request and save scope before a wait; do not retain mutable caller data. |
| Mutable getter output | get returns the same live pending request; changing its save array changes approval scope. | Return detached, read-only projections outside the trusted owner. |
| Policy changes while waiting | A selected once reply completes despite a new configured deny; new requests are denied. | Define explicit-human override vs strict revocation; enforce current policy at the actual tool boundary. |
| Explicit ID reuse after settlement | A caller can recreate the same permission ID **in the same session** for different resources; that ID's next reply resolves the new request. | Do not reuse caller-selected approval IDs across generations; bind approvals to an immutable request identity. |

Default generated IDs are not shown to collide by this test. The reuse result
requires an explicitly supplied reused ID. The mutation scenarios are in-process
object mutation, not a claim that JSON HTTP clients retain direct memory access.
Other pending auto-approvals following always are reevaluated and retain newly
configured denies; selected-explicit approval and bulk auto-approval differ.

Source locations: `packages/core/src/permission.ts:165–188,191–228,265–336`.
The real HTTP handler checks session/request ownership at
`packages/server/src/handlers/permission.ts:21–29,77–83`; importing only the raw
service would not carry that handler's check. Same-session generation reuse is a
separate question. No HTTP auth middleware was executed in this supplement.

## Event findings (8 separate observations)

One encoded frame fans out to all subscribers. Unknown internal event types are
filtered before consuming subscriber capacity. A slow subscriber fails explicitly
without stopping a fast one. Encoding failure closes current subscribers; new
subscriptions still work. Scoped shutdown removes the source listener.

The disconnect experiment closes a subscriber scope, publishes an event while
there are no subscribers, then creates a new subscription. Only the subsequent
event arrives. This verifies **volatile feed behavior**, not TCP reconnection.
The SSE frame includes JSON data but no `id:` resume field. An injected newline
in JSON remains escaped and does not create a second SSE frame.

This behavior is declared by `packages/protocol/src/groups/event.ts:44–55`.
OpenCode separately has a durable session-log API described in
`packages/protocol/src/groups/session.ts`; it was not exercised here. Do not
conclude that the product has no durable event functionality. Alaz must requery
its authoritative state or a qualified durable log on reconnect. It must not
reexecute an external side effect merely because a notification was missed.

## Reproduction and evidence

From the active worktree, with the already prepared isolated Effect dependency:

```powershell
python -B scripts/run_independent_opencode_qa.py --source-workspace C:\Antigravity\AlazHarness --prepared C:\Antigravity\AlazHarness\runtime\ref-oc-001-8ea1\prepared --output C:\Antigravity\AlazHarness\runtime\opencode-independent-new
```

Output must be new. The launcher rejects source/lock drift, records exact source
file hashes, child IDs/nonces and process exits, and checks complete ordered case
coverage. It does not install dependencies. The two families contribute12 and8
observations; repeated runs or the standard unit tests are not added to inflate
this count. `evidence/ref-oc-001-qa/independent-components.json` is the sanitized
packaged run. Raw logs remain in runtime/ref-oc-001-qa-5a5c.

The first smoke attempt failed because strip-only TypeScript cannot execute a
schema namespace. Node transform mode fixed only the test loader; original source
was not modified. The failure logs remain in the QA runtime. Expected error logs
from the encoding-failure test are not suppressed or called overall suite failure.

## Integration handoff

These observations supplement REF-OC-001 and inform the component decision. They
do not install or enable OpenCode permission enforcement in AlazHarness. Standard
CI status and exact publication commit must be read separately. Broader M1/M2,
host immutable approval envelope, trusted rule selection and final authorization
remain unaccepted until implemented and tested at the actual execution boundary.

## Standard-suite handoff

Independent full root unittest rerun: **280/280 PASS**, exit0, no skipped tests,
30.348 seconds reported by unittest. The measured OpenCode primary worker,
projection helper, launchers and tests did not change during this rerun.
This is the ordinary dependency-free regression suite, not20 additional native
cases and not exact-commit server CI. See root-recheck.json and root-unittest.txt.
Eleven new offline tests validate this supplement's receipt completeness,
identity, source-provenance presence and model-call counters.
