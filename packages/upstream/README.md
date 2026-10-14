# Pinned component copies

These eight files (six source modules plus two licenses) are copied from the
submodule commits in `sources.lock.json`. `components.lock.json` records each
original and copied SHA-256. Only the OpenClaw deadline helper's package import
is relocated to the copied local number-coercion module. No logic is rewritten.

OpenClaw: cancellation, execution/settlement deadlines and their pure coercion
dependencies. Hermes: StdioTransport and per-agent IterationBudget. The copied
transport's optional Fanout WebSocket branch still needs upstream async_utils;
that branch is not used or qualified by this component slice. Do not expose it
as a supported feature. Full Gateway, AIAgent, model calls, tools, sessions,
persistent goals and memory are NOT included here.

Keep licenses and attribution with the modules. Update copies only with an
explicit source-pin review, regeneration and behavior tests. Ordinary CI checks
copied-byte integrity without fetching vendor sources; the developer full check
also compares each copy against its pinned local source.
