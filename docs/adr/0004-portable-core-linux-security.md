# ADR-0004 — Platform-neutral AlazHarness core, Linux-first secure execution

Date: 2026-10-19. Decision: **ACCEPTED as architecture direction**.
Implementation: PLAT-001 **read-only routing/planning contract**;
whole-product/multi-OS runtime acceptance: **NOT ACCEPTED**.

## Decision and product boundary

AlazHarness is one hybrid OpenClaw–Hermes agent system, not a Linux-only app
or a second competing scheduler. Keep portable control/coordination in the
Node 24 integration layer. Existing Hermes native model/tool loop remains
the chosen M1 engine (ADR-0003), with selected OpenClaw cancellation,
deadline and control components. Put actual native OS confinement, provider
broker and broker-owned private budget behind platform-specific execution
adapters. No port of the real Hermes loop or extra LLM route selection.

Platform-neutral responsibilities: agent/run/session/goal IDs, single
scheduler and active work owner, admission, retry/reconciliation of
ambiguous outcomes, portable capability and event formats, cancel and
status semantics, per-run permission/budget intent. Future learning
policies are M2, NOT enabled by this decision.

Execution-plane responsibilities: process and FD lifetime, filesystem,
IPC and network isolation, native OS/kernel and user principal checks,
private provider credentials, broker-owned financial authority, and
durable external-effect accounting. The host label is NOT security proof.

## Target composition

1. **Linux x86_64 native**: first secure execution adapter candidate.
   Existing rootless netns, seccomp, Landlock, one projected Unix socket
   and broker SQLite budget have scoped tests. Two real host UID
   end-to-end, full D3B, arbitrary hostile host writer, provider tariffs
   and real paid models are **NOT ACCEPTED**.
2. **Windows x64 host**: Node coordinator and scripted mock fixture are
   available in development. Future secure work runs through separately
   approved WSL2 Linux x86_64 guest, NOT silent local Windows subprocess
   fallback. Host/guest bridge and process/path/socket/credential life
   cycle are **NOT IMPLEMENTED**.
3. **macOS Apple Silicon ARM64**: future Node coordinator host. Secure
   execution initially via explicitly approved remote Linux x86_64
   worker or future Linux ARM64 guest after separate native ARM64
   kernel/syscall/ABI proof. Current guard only supports Linux x86_64.
   A Linux ARM64 VM does not magically qualify it. Emulating x64 on
   Apple Silicon is NOT an accepted cost/security baseline.
4. **macOS Intel x64**: future coordinator; candidate Linux x64 VM or
   approved remote worker, but no verified host/guest transport.
5. **Linux ARM64 / Windows ARM64**: portable orchestration target and
   route simulations only, not a working x86_64-grade Linux guard.

## Portable adapter contract (future runtime)

One explicit adapter per run. Required operations:
- capabilities: real kernel/OS/arch/guest, mock versus native, tool
  allowance and permission/budget boundary, accepted test tier.
- start: one authoritative native owner, bound run/session/permission/
  budget/target and stable idempotency; no generated generic shell.
- events, status and resume: strictly read-only recovery observation
  when last external effect is unknown; never silently repeat POST.
- cancel: scoped owned process-tree teardown, settlement and
  unknown cleanup isolation; no stronger permissions or new scheduler.
- missing/unsupported adapter always fails closed with no downgrade to
  legacy direct provider, unconfined host shell or weaker sandbox.

These are interface goals. PLAT-001 DOES NOT implement actual start,
transport, remote dispatch, cancellation or any privileged launcher.

## PLAT-001 implemented now

- packages/hybrid-runtime/platform-routing.mjs — pure versioned
  side-effect-free route planning.
- scripts/inspect_platform.mjs — read-only OS/arch/guest inspector.
- Mode scripted-mock is fixture-plan-only; even mock plan cannot grant
  process launch. Guarded mode always guarded-not-accepted and denies
  processLaunchAuthorized, realModelCallAuthorized and any model spend,
  regardless of Linux x64 candidate or forged kernelAttested flag.
- Require accepted on guarded CLI fails with exit 2, without fallback.
- WSL2 guest is identified only from Linux kernel release; ambiguous
  Microsoft kernels become unverified, never WSL2-approved.
- Exact request schema with explicit no-extra-fields, no arbitrary
  CLI OS/architecture/kernel overrides, no secret or path display.
- Real Windows x64 host and WSL2 Linux x64 guest inspected separately.
  macOS and ARM64 results currently ONLY simulated.
- Default mock HYB-001/002 and prior D3B code paths unchanged.

## Release/acceptance path

PLAT-001: deterministic planning contract + offline Windows and WSL2
Node tests + real read-only host classification + same-commit GitHub CI.
PLAT-002: bounded Windows/WSL2 adapter and verified guest identity,
path and process isolation, local negative cancellation/restart tests.
PLAT-003: native Linux worker adapter binds real D3B host principal,
IPC/socket projection and existing broker budget before process spawn.
PLAT-004: actual Apple Silicon coordinator test; authorized remote
Linux worker protocol, credentials/attestation/retry/effect closure,
and optional Linux ARM64 port if separately justified.
PLAT-005: cross-host end-to-end identity/restart/events/authorization
and local-scripted real Gateway parity, then separately approved
real-provider tokenizer/cost acceptance.

No daemon, privileged launch, paid call, production profile, upstream
modification, M1/M2 promotion, hidden Windows fallback or source pin
change is authorized by this decision. ADR-0001..0003 still govern the
single hybrid engine and source choices.
