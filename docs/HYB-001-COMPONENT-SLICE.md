# HYB-001 / HYB-002: first executable component slice

This is a real code reuse + protocol experiment with a SCRIPTED peer, not a
finished autonomous agent or a complete OpenClaw/Hermes application integration.

## Run

From the repository root, with Node 24+ and Python 3.11+:

```sh
python -B scripts/demo_hybrid.py
python -B scripts/demo_hybrid.py --scenario echo --text "Merhaba AlazHarness"
python -B -m unittest discover -s tests -v
python -B scripts/verify_components.py
```

The default demo returns the scripted 2 + 3 result and two consumed iterations.
It proves a frame/ownership/budget boundary, not reasoning or learned ability.
No npm/pip install, model key, external tool, internet call or personal agent
profile is needed. Local demo state uses ignored runtime/component-demo/ folders.

With the full source submodules already present:

```sh
python -B scripts/verify_components.py --with-vendor
```

## API in this slice

`MockHybridHarness({python, workRoot})` accepts an absolute interpreter and working
root controlled by the host, not commands from agent messages. `start({key,text,
scenario,iterationBudget,timeoutMs})` returns runId. `wait`, `status`, `events`,
`cancel`, `capabilities` are implemented. `resume` explicitly rejects the request.

Scenario selects a fixed local test behavior, NOT a provider or model. Inputs
cannot select a shell command, script, remote endpoint or plugin. Text crosses
JSON stdin unchanged and is never interpolated into a shell command.

The first slice supports one process-local active job and idempotency for that
instance. Same key/same normalized request returns the same run; changed payload
conflicts. A different key while active is BUSY. At 64 retained records new runs
are refused; records are never silently evicted and re-executed.

## Wire observations that drove the adapter

- This is legacy TUI JSON-RPC, not `hermes-gateway-v1` session authority.
- `gateway.ready` is a sessionless notification. A canonical authority flag is
  rejected until its distinct API has an implementation and acceptance tests.
- `session.create` returns an identity but not a completed/ready agent turn.
- `prompt.submit` takes `text`. Its streaming/queued/steered/redirected ACK must
  not be conflated with terminal success; this exclusive slice accepts streaming.
- Native events use `params.type`, `params.session_id`, `params.payload`.
- `message.complete` may lack status on some upstream paths. A text-only event is
  insufficient for success. This adapter requires explicit status and same session.
- The upstream terminal event precedes some post-turn work. The adapter waits for
  its directly owned child to close before releasing the active slot.
- `session.status` is rendered text, not machine-readable job state. It is unused.
- Approval requests receive deny. Other unimplemented peer requests return -32601.
  No tool execution authority is created by receiving a peer request.

## Tested failure classes and deliberate limits

Input validation, duplicate/conflicting submission, BUSY, output/frame bounds,
UTF-8 and quoted input, mismatched session, malformed/partial/conflicting terminal,
terminal-before-ACK ordering, execution/settlement timeout, cooperative/forced
fixture cancellation, process crash, nonzero exit, denied approval, unsupported
request, isolated launch environment and source-copy provenance are covered.

Only safe OS bootstrap variables are inherited. Child home/profile/temp paths
are explicit isolated directories. This is environment hygiene, NOT an OS sandbox:
the same host account could still access host files if arbitrary code were allowed.
The fixture never spawns descendants; process reaping evidence applies only to
that owned child, not arbitrary terminal/browser process trees.

OpenClaw deadlines bound execution and settlement; cleanup additionally uses a
bounded grace + kill/readback interval. Hermes iteration accounting is per-agent,
not a global token/currency ledger. There are no paid model calls.

## Next acceptance boundary

HYB-003 must provision an isolated Hermes runtime, enter via its real public
AIAgent path and replace only model I/O with a mock. It must prove a real tool round,
not bypass initialization with a hand-built object. Then qualify persistent session,
restart/reconciliation and memory ownership. Full OpenClaw Gateway and scheduling
integration must also be qualified before M1 acceptance. M2 autonomy stays later.
