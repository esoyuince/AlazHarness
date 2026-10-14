/** Alaz-owned local Hermes wire adapter; no model loop, scheduler or transcript writer. */
import { setTimeout as sleep } from 'node:timers/promises';
import { createAgentHarnessAttemptCancellation } from '../upstream/openclaw/attempt-cancellation.ts';
import { createAgentHarnessAttemptDeadlineController } from '../upstream/openclaw/attempt-deadlines.ts';
import { MAX_TIMER_TIMEOUT_MS } from '../upstream/openclaw/number-coercion.ts';

const STATUSES = new Set(['queued', 'started', 'running', 'stopping', 'waiting_for_approval',
  'completed', 'failed', 'cancelled', 'interrupted', 'unknown']);
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'interrupted']);
const RUN_ID = /^run_[a-f0-9]{32}$/;

export class HarnessError extends Error {
  constructor(code, details = {}) {
    super(code); this.name = 'HarnessError'; this.code = code;
    Object.assign(this, details);
  }
}
function fail(code, details) { throw new HarnessError(code, details); }
function bounded(value, min, max, name) {
  if (!Number.isInteger(value) || value < min || value > max) fail('invalid_' + name);
  return value;
}
function runId(value) {
  if (typeof value !== 'string' || !RUN_ID.test(value)) fail('invalid_run_id');
  return value;
}
function text(value, max, name) {
  if (typeof value !== 'string' || !value.trim() || Buffer.byteLength(value) > max) fail('invalid_' + name);
  return value;
}
function snapshot(value, expectedId, admission = false) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || !RUN_ID.test(value.run_id) || (expectedId && value.run_id !== expectedId)
      || !STATUSES.has(value.status)) fail('invalid_run_response');
  if (admission && typeof value.replayed !== 'boolean') fail('invalid_admission_response');
  if (!admission && value.status === 'completed'
      && (value.completed === false || value.partial === true || value.interrupted === true || value.failed === true)) {
    fail('contradictory_terminal_response');
  }
  if (value.output !== undefined && typeof value.output !== 'string') fail('invalid_run_output');
  return value;
}

export class HermesRunsClient {
  #base; #token; #requestTimeout; #maxBytes;
  constructor({ baseUrl, token, requestTimeoutMs = 5000, maxResponseBytes = 1_048_576 } = {}) {
    let url;
    try { url = new URL(baseUrl); } catch { fail('invalid_base_url'); }
    // HYB-002 only permits explicit literal loopback endpoints, not DNS/remote profiles.
    if (!['http:', 'https:'].includes(url.protocol)
        || !['127.0.0.1', '[::1]'].includes(url.hostname)
        || url.username || url.password || url.search || url.hash || url.pathname !== '/') fail('unsupported_endpoint');
    if (typeof token !== 'string' || !/^[\x21-\x7E]{1,4096}$/.test(token)) fail('invalid_bearer_token');
    this.#base = url.origin; this.#token = token;
    this.#requestTimeout = bounded(requestTimeoutMs, 10, 60000, 'request_timeout');
    this.#maxBytes = bounded(maxResponseBytes, 128, 4_194_304, 'response_limit');
  }
  capabilities() {
    return Object.freeze({ protocol: 'hermes-runs-pinned-v1', start: true, status: true,
      stopRequest: true, observe: true, resumeReadOnly: true,
      sse: false, interactiveApproval: false, resolveUnknown: false,
      ownScheduler: false, ownModelLoop: false, ownTranscript: false,
      tokenOrCostBudgetEnforced: false, serverDurabilityVerified: false });
  }
  async #request(method, path, { body, key, signal, expected = 200 } = {}) {
    if (signal?.aborted) fail('aborted_before_request', { mayHaveBeenAccepted: false });
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort('request_timeout'), this.#requestTimeout);
    const combined = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
    const write = method !== 'GET';
    try {
      const response = await fetch(this.#base + path, {
        method, redirect: 'error', signal: combined,
        headers: { Authorization: 'Bearer ' + this.#token, Accept: 'application/json',
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...(key ? { 'Idempotency-Key': key } : {}) },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      const reader = response.body?.getReader();
      const chunks = []; let total = 0;
      try {
        if (Number(response.headers.get('content-length') || 0) > this.#maxBytes) fail('response_too_large');
        if (!/^application\/json(?:;|$)/i.test(response.headers.get('content-type') || '')) fail('invalid_content_type');
        if (!reader) fail('empty_response');
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          total += value.length;
          if (total > this.#maxBytes) fail('response_too_large');
          chunks.push(value);
        }
      } finally { await reader?.cancel().catch(() => {}); }
      let value;
      try { value = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { fail('invalid_json_response'); }
      if (response.status !== expected) {
        // Never echo remote error text: it may contain prompts or credentials.
        fail('http_' + response.status, { httpStatus: response.status,
          mayHaveBeenAccepted: write && response.status >= 500 });
      }
      return value;
    } catch (error) {
      if (error instanceof HarnessError) {
        if (error.mayHaveBeenAccepted === undefined) error.mayHaveBeenAccepted = write;
        throw error;
      }
      fail(write ? 'write_outcome_unknown' : 'transport_error', { mayHaveBeenAccepted: write });
    } finally { clearTimeout(timer); }
  }
  async start({ input, model, sessionId, idempotencyKey } = {}, { signal } = {}) {
    const body = { input: text(input, 65536, 'input') };
    if (model !== undefined) body.model = text(model, 200, 'model');
    if (sessionId !== undefined) body.session_id = text(sessionId, 256, 'session_id');
    if (typeof idempotencyKey !== 'string' || !/^[\x21-\x7E]{1,255}$/.test(idempotencyKey)) fail('invalid_idempotency_key');
    // Intentionally no automatic POST retry, even when the server advertises idempotency.
    const value = await this.#request('POST', '/v1/runs', { body, key: idempotencyKey, signal, expected: 202 });
    try { return snapshot(value, undefined, true); }
    catch (error) { error.mayHaveBeenAccepted = true; throw error; }
  }
  async status(id, { signal } = {}) {
    return snapshot(await this.#request('GET', '/v1/runs/' + runId(id), { signal }), id);
  }
  async stop(id, { signal } = {}) {
    return snapshot(await this.#request('POST', '/v1/runs/' + runId(id) + '/stop', { body: {}, signal }), id);
  }
  events() { fail('unsupported_sse'); }
  approve() { fail('unsupported_approval'); }
  steer() { fail('unsupported_steering'); }
  resolveUnknown() { fail('operator_reconciliation_required'); }
  async resume(id, options = {}) {
    // Reattach to an existing run; never resubmit a prompt or resolve an unknown effect.
    return this.observe(id, options);
  }
  async observe(id, { signal, executionTimeoutMs = 30000, settlementTimeoutMs = 5000,
      pollIntervalMs = 100, onStatus } = {}) {
    runId(id);
    bounded(executionTimeoutMs, 10, 600000, 'execution_timeout');
    bounded(settlementTimeoutMs, 10, 60000, 'settlement_timeout');
    bounded(pollIntervalMs, 1, 5000, 'poll_interval');
    const state = { explicitCancellationObserved: false, terminalOutcomeFrozen: false,
      sharedAbortAllowedAfterTerminalOutcome: false };
    const cancellation = createAgentHarnessAttemptCancellation({ upstreamSignal: signal, state });
    const execution = createAgentHarnessAttemptDeadlineController({
      startedAtMs: Date.now(), startedAtMonotonicMs: performance.now(),
      timeoutMs: executionTimeoutMs, settlementTimeoutMs,
      signal: cancellation.controller.signal,
      onTimeout: () => cancellation.abortExplicitly('execution_timeout'),
    });
    let settlement; let settlementAbort; let stopRequested = false; let stopError = null;
    const result = (value) => ({ run: value, backendConfirmed: TERMINAL.has(value.status),
      stopRequested, hostReason: state.explicitCancellationObserved
        ? (state.explicitCancellationReason === 'execution_timeout' ? 'execution_timeout' : 'cancelled') : null,
      requiresOperator: value.status === 'unknown' || value.status === 'waiting_for_approval',
      ...(stopError ? { stopError } : {}) });
    try {
      while (true) {
        if (state.explicitCancellationObserved && !stopRequested) {
          stopRequested = true;
          execution.dispose();
          settlementAbort = new AbortController();
          // Separate settlement lifetime: an already-aborted execution cannot be revived.
          settlement = createAgentHarnessAttemptDeadlineController({
            startedAtMs: Date.now(), startedAtMonotonicMs: performance.now(),
            timeoutMs: MAX_TIMER_TIMEOUT_MS, settlementTimeoutMs,
            signal: settlementAbort.signal,
            onTimeout: () => settlementAbort.abort('settlement_timeout'),
          });
          settlement.beginSettlement(Date.now());
          try { await this.stop(id, { signal: settlementAbort.signal }); }
          catch (error) { stopError = error.code || 'stop_request_failed'; }
          // A stop ACK is not terminal proof. Always read the canonical run status.
        }
        if (settlementAbort?.signal.aborted) fail('settlement_unconfirmed', { runId: id, backendConfirmed: false, state: 'unknown' });
        const activeSignal = settlementAbort?.signal || cancellation.controller.signal;
        let value;
        try { value = await this.status(id, { signal: activeSignal }); }
        catch (error) {
          if (settlementAbort?.signal.aborted) fail('settlement_unconfirmed', { runId: id, backendConfirmed: false, state: 'unknown' });
          if (!stopRequested && cancellation.controller.signal.aborted) continue;
          // Read failures neither prove success nor authorize replay.
          error.runId = id; error.backendConfirmed = false; throw error;
        }
        try {
          const notification = onStatus?.(structuredClone(value));
          notification?.catch?.(() => {});
        } catch { /* Observers do not own the execution result. */ }
        if (TERMINAL.has(value.status)) {
          cancellation.freezeTerminalOutcome();
          return result(value);
        }
        if (value.status === 'unknown' || (value.status === 'waiting_for_approval' && !state.explicitCancellationObserved)) {
          return result(value);
        }
        try { await sleep(pollIntervalMs, undefined, { signal: activeSignal }); }
        catch { /* Re-check cancellation/settlement before another read. */ }
      }
    } finally {
      execution.dispose(); settlement?.dispose(); cancellation.dispose();
    }
  }
}
