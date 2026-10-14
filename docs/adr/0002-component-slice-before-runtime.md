# ADR-0002: Selected source components before application bootstrap

Date: 2026-10-15. Scope: HYB-001 / first HYB-002 protocol slice.

## Decision

Take actual reusable code from both pinned upstreams. Copy OpenClaw cancellation,
execution/settlement deadlines and two pure coercion dependencies; copy Hermes
StdioTransport and IterationBudget. Preserve both licenses, original source path,
commit, hashes and the one deterministic import relocation in components.lock.json.
Do not port TypeScript to Python or reimplement the copied behavior.

Compose these modules in a small Node supervisor + Python scripted test peer over
legacy TUI JSON-RPC. The peer deliberately does NOT construct AIAgent and is kept
under tests/fixtures. It is a replaceable contract test fixture, not an agent
engine. Model/tool behavior is explicitly scripted and reported as such.

## Why not start the complete applications here?

At the pinned Hermes commit, run_agent.py performs early recovery/bootstrap and
loads environment/profile state at import. tui_gateway/server.py also sets up
logging, update probes and process-wide transport/session machinery. Importing
only conversation_loop.py does not avoid this dependency graph. Constructing a
fake AIAgent object that bypasses its normal initialization would not prove its
public runtime path. Full environment setup is therefore a separate next gate.

The OpenClaw harness-runtimes module is discovery/configuration, not an executable
model loop. Its queue and event bus depend on wider gateway ownership. The pure
cancellation/deadline modules are a much narrower first reuse point. This does
not mean those wider components are rejected; they remain deferred.

## Ownership and limits

One MockHybridHarness instance owns one active run, local idempotency records,
request/session correlation and the directly spawned fixture child. OpenClaw
owns cancellation/deadline mechanics. Hermes owns frame serialization and the
fixture's per-agent iteration counter. No second scheduler or model routes exist.

Records are in-memory, bounded to 64, and do NOT survive process restart. Separate
harness instances are not globally serialized. Resume explicitly returns
UNSUPPORTED_RESUME. There is no persistent agent identity, memory, budget in
currency, full process-tree isolation, sandbox or autonomy implementation yet.

A submit ACK is not completion. Native terminal payload is not process closure.
Success requires a matching session, explicit complete status, no partial/error,
consistent terminal frames and zero-exit owned-child closure. Unknown execution
outcomes are not automatically replayed. Cleanup uncertainty prevents new work.

## Proof scope

Tests use real Node/Python processes and the copied upstream modules, not the full
Gateway/AIAgent applications. They cover ordinary completion and observable
failure classes. Windows and fresh Linux CI must pass before this slice is landed.
Actual AIAgent with a mock model is HYB-003, still NOT RUN; M1 remains incomplete.
