# AlazHarness — source-based component map

Reviewed 2026-10-15 against pinned local source, not current web documentation.
OpenClaw: 2dcbb6138d57dccfcd54f2f908ef9f38268b1229.
Hermes: eb75627faf532fa6ffbdae59a0d14b0b385fc780.

## TAKE / ADAPT now

| Owner | Source path / symbol | Dependency and modification | Current proof |
|---|---|---|---|
| OpenClaw | src/agents/harness/attempt-cancellation.ts:2, createAgentHarnessAttemptCancellation | No imports; verbatim copy | Cancellation/first-reason/frozen-terminal behavior; used by process supervisor |
| OpenClaw | src/agents/harness/attempt-deadlines.ts, createAgentHarnessAttemptDeadlineController | Pure number helper; only import path relocated | Execution and settlement deadline behavior; used by supervisor |
| OpenClaw | packages/normalization-core/src/number-coercion.ts and string-coerce.ts | Pure functions; verbatim complete modules | Transitive runtime use and syntax check |
| Hermes | tui_gateway/transport.py:98, StdioTransport; serialize_frame:83 | Stdlib on used path; verbatim full module | Real child pipe, Unicode/serialization/broken-pipe/concurrent-write tests |
| Hermes | agent/iteration_budget.py:25, IterationBudget | math/threading only; verbatim | Consume/refund/concurrency and scripted two-iteration budget |
| AlazHarness | packages/hybrid-runtime/*.mjs | Host-owned process/correlation/status adapter | Real OS process protocol tests, SCRIPTED peer |

Copies and original bytes are recorded in components.lock.json. Both upstream
licenses are preserved in packages/upstream/. Only StdioTransport is qualified:
the full copied transport also contains optional Fanout WebSocket logic with a
lazy agent.async_utils dependency; that path is not loaded or advertised.

## DEFER with concrete boundaries

| Candidate | Source evidence | Reason / next work |
|---|---|---|
| OpenClaw runtime discovery | src/agents/harness-runtimes.ts:26–60,146–163 | Resolves configured runtime IDs, not executable agent; do not mistake discovery for integration |
| OpenClaw full harness plugin | src/agents/harness/types.ts; docs/plugins/sdk-agent-harness/registration.md | AgentHarnessV2 runAttempt receives host-owned prepared context; dependency/authority mapping required |
| OpenClaw queue/event bus | src/process/command-queue.ts; src/infra/agent-events.ts | Gateway admission, diagnostics and custody dependencies; do not copy a competing state owner blindly |
| Hermes public AIAgent | run_agent.py:9–24,95–101,236+ | Import-time recovery/profile/env plus wide constructor/mixin graph; isolate/provision before launch |
| Hermes actual model/tool loop | agent/conversation_loop.py:18–63; agent/turn_facade.py; agent/turn_facade_lease.py | Many phase dependencies and durable lease; HYB-003 must use real initialization, mock only model I/O |
| Hermes TUI application | tui_gateway/server.py:56–92,200–215 | Profile/env/logging/update probes and shared state at import; full application NOT launched |
| Hermes persistent goals | hermes_cli/goals.py:1089+,1626+ | Persistence, auxiliary judge and lazy runtime dependencies; not a pure engine to fake with one callback |
| Hermes memory | agent/memory_manager.py, agent/memory_provider.py (routed by agent/AGENTS.md:124–139) | Known ownership entry points, not deeply qualified or tested in this slice |
| Uyanma / kendi gündemi | Existing automation vs our later M2 layer | No scheduler or autonomy loop started; M1 must precede M2 |

## Exact legacy TUI wire anchors

- tui_gateway/contracts/sessions.py:118–151: session.create / idempotency key / result.
- tui_gateway/contracts/prompt_voice.py:26–79: prompt.submit.text and admission states.
- tui_gateway/server.py:717–720: event envelope params.type/session_id/payload.
- tui_gateway/contracts/events.py:186–191,237–261: terminal status is optional on general events.
- tui_gateway/prompt_turn.py:915–917,1163–1184: terminal payload and post-event settlement.
- tui_gateway/contracts/sessions.py:481–486,603–619: status is text; interrupt is an ACK.
- tui_gateway/contracts/server_requests.py:166–195: approval choice deny.
- tui_gateway/AGENTS.md:36–53: legacy and canonical authority wire are distinct.

## Ownership decision

The component slice has one in-memory run owner per harness instance; copied
OpenClaw helpers handle lifecycle mechanics, copied Hermes helpers handle frame
serialization and local iteration accounting. It does not add a second agent
model, scheduler, memory store or goal judge. Future session/memory authority stays
with the actual execution engine; our autonomy agenda must not become another
writer to that engine's store.

See ADR-0002 and HYB-001-COMPONENT-SLICE.md for runnable proof and explicit gaps.
Source locations and copied-module checks are not full upstream suite acceptance.

## Integrated ownership (HYB-003)

The two candidates share packages/upstream and config/components.lock.json.
The duplicate tree and old provenance checker were retired in this integration
branch; original feature histories are preserved. HTTP contracts are documented
in HYB-002-HTTP-CONTRACT.md. The real Hermes engine must own admission, transcript
and tools. Two adapters must not independently drive the same live session.

## Pi ve OpenCode inceleme adayları

Pi Agent Core ve Pi Durable farklı katmanlar olarak; OpenCode gömülü SDK, izin hizmeti ve oturum gelen kutusu ise güncel sabit kaynaklarından incelendi. Henüz TAKE kararı veya çalışma zamanı değişikliği yok. Ortak kod kopyaları `packages/upstream/` altında on payload olarak kaldı. Kaynak/test satırları, bağımlılıklar, tekrar sözleşmesi farkları ve deney planı `research/PI-OPENCODE-REVIEW.md` içinde.
