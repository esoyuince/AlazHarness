# HYB-001/002 — Native HTTP contract candidate

> Integration note (2026-10-15): this candidate is now combined with the reviewed
> stdio branch in alaz/hyb-003-integration-46cc. Source copies moved to
> packages/upstream and the canonical lock remains config/components.lock.json.
> Original branch-specific notes below are historical; CURRENT-STATE.md is current.

Status: isolated HTTP candidate IMPLEMENTED; mock boundary implemented. Full Hermes
Gateway/AIAgent execution and full M1 acceptance are NOT RUN.

## Branch ownership

This candidate lives on `alaz/hyb-002-http-contract`, based on bootstrap 58b210a.
During implementation, a separate writer changed the main workspace to
`alaz/hyb-001-component-slice` and added a different slice. Those changes were
preserved. This package was moved to an isolated worktree; no automatic merge,
source-layout replacement or claim over the other writer's tests is made here.
Reconcile the shared source layout and execution boundary before combining them.

## Decision in this candidate

Take selected source components, preserve their licenses and pin exact bytes.
Use OpenClaw attempt cancellation/deadline helpers as the Alaz host-side control
mechanics. Use Hermes native `/v1/runs` as the selected execution boundary, rather
than writing a second task queue, transcript store or language-model loop.
The adapter currently connects only to an explicitly supplied literal loopback
origin. It has no default endpoint and discovers no personal agent installation.

This is a source-level hybrid slice, NOT two complete assistants asking each other
to think, and NOT proof that the complete OpenClaw Gateway already routes Hermes.
Full Gateway plugin registration is deferred until the narrower wire acceptance.

## Selected source components (MIT licenses retained)

Pins are unchanged in `sources.lock.json`; exact paths, transformations and hashes
are in `config/components.lock.json` (nine payloads including two license files).

| Component | Source / symbol | Dependencies | Use / verification |
|---|---|---|---|
| OpenClaw cancellation | src/agents/harness/attempt-cancellation.ts:2-46; createAgentHarnessAttemptCancellation | AbortController only | Real imported code; duplicate cancellation and frozen terminal tests |
| OpenClaw deadlines | src/agents/harness/attempt-deadlines.ts:19-98; createAgentHarnessAttemptDeadlineController | normalization number helpers, Node timers | Real imported code; timeouts, settlement no-extension, disposal tests |
| OpenClaw normalization | packages/normalization-core/src/number-coercion.ts and string-coerce.ts | No external package after one localized import | Complete modules, not a behavioral rewrite |
| Hermes iteration budget | agent/iteration_budget.py:25-59; IterationBudget | math, threading | Real copied module in fixture/component tests; limits, refund, concurrency |
| Hermes identity | hermes_state_keys.py:11-23 | hashlib, json | Real pure identity derivation in fixture; canonical JSON/target isolation tests |
| Hermes result mapping | gateway/platforms/api_server_runs.py:186-205; terminal_run_status | typing only | Unchanged function extracted by AST; partial/interrupted cannot become completed |

Nine payloads is not nine whole systems: four TypeScript modules, two complete
Python modules, one Python function and two licenses. No vendor checkout changed.
`python -B scripts/verify_components.py --with-vendor` reproduces all transforms.
The normal CI checks destination hashes and pin consistency without cloning vendor.

## Native Hermes wire contract inspected at the pinned commit

- `api_server_runs.py:644-651,704-838`: POST /v1/runs, `input` with optional
  `model` / `session_id`; explicit Idempotency-Key. Admission is 202 with run_id,
  status and replayed. Initial `started` means admission, not task completion.
- `api_server_runs.py:484-501`: identical keys replay, changed payload is 409.
- `api_server_runs.py:1172-1176`: canonical GET run status.
- `api_server_authority_runs.py:46-75`: unknown remains nonterminal; approval may
  yield waiting_for_approval; partial or failed model outcome cannot be success.
- `api_server_runs.py:1420-1451` and `api_server_authority_runs.py:116-145`:
  POST stop may return stopping; it is NOT a receipt that execution has stopped.
- `api_server_run_idempotency.py:53-109`: store can fall back to memory when disk
  cannot open. A documented durable feature is not evidence of an actual durable
  deployment. Its retention is finite. The client does not verify server durability.
- `api_server_authority_runs.py:148-167`: unknown resolution needs an exact
  admission/generation and explicit operator decision; never auto-resolve.

## Why not copy the broad entrypoints in this step?

OpenClaw harness-runtimes.ts selects a runtime but does not execute one. Its
agent-events/system-events/command-queue modules have wider ownership and global
registry dependencies; the system-event queue is ephemeral, not durable admission.

Hermes run_agent.py imports bootstrap/recovery/environment/profile code. Its
conversation_loop.py uses many turn mixins. tui_gateway/server.py also starts
profile/update/bootstrap paths. Copying one entrypoint is not a self-contained
engine. AIAgent, canonical SessionAuthority, memory and skills remain TAKE-via-
existing-runtime candidates for HYB-003; they are not reimplemented in this slice.

## Implemented Alaz boundary

`packages/claw-hermes/hermes-runs.mjs`: start, status, stop-request, observe and
read-only resume. Explicit unsupported errors for SSE, approval, steering and
unknown resolution. Required caller-supplied idempotency key; no hidden POST retry.
Response size, HTTP request time and observation wait are bounded. No redirects.
Remote error text/token is not echoed. Observer callbacks cannot own the result.

OpenClaw freezes observed terminal outcomes and controls execution/settlement
waiting. Hermes owns the actual run, session and effects. A stop request uses one
POST and then polls with an independent bounded settlement deadline. If stop
cannot be confirmed, the client reports unknown, never fabricated cancellation.
`resume` only observes the existing run; it never replays its prompt.

`executionTimeoutMs` bounds this observer's waiting interval and requests a stop;
it is not a server CPU/token/currency budget. No aggregate cost/token enforcement
is claimed. An accepted remote run can outlive a disconnected observer.

## Evidence scope / remaining gaps

`tests/fixtures/hermes_wire.py` is explicitly a stdlib loopback fixture. It executes
the selected real Hermes pure components, but its admission and run maps are
in-memory scripted data. Tests of duplicate/lost ACK behavior prove client protocol
handling, NOT native SessionAuthority locking, restart persistence or exactly-once
effects. `resume` here is client recreation, not a server crash/recovery proof.

No real model, tools, bootstrap, dependency install, personal profiles or continuous
loop is started by these tests. The deterministic result 42 is a fixture outcome,
not reasoning, learning, or an agent solving a novel problem.

Next: run the unmodified pinned Hermes native HTTP handler and AIAgent under an
isolated profile with a loopback scripted model, then replay the same wire suite.
Exercise canonical durability and ownership before claiming HYB-003/004 or M1.
SSE, interactive responses, selected OpenClaw event ingress, memory/skills,
real-model acceptance and autonomy remain separate unaccepted work.
