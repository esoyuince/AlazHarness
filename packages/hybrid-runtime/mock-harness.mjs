// HYB-001/002 component slice. Fixed scripted peer only; NOT an autonomous agent.
import { randomUUID } from 'node:crypto';
import { mkdir, mkdtemp } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createAgentHarnessAttemptCancellation } from '../upstream/openclaw/attempt-cancellation.ts';
import { createAgentHarnessAttemptDeadlineController } from '../upstream/openclaw/attempt-deadlines.ts';
import { StdioPeer } from './stdio-peer.mjs';
import { HarnessError, deferred, abortable, object } from './common.mjs';
export { HarnessError } from './common.mjs';

const FIXTURE = fileURLToPath(new URL('../../tests/fixtures/hermes-scripted-peer.py', import.meta.url));
const SCENARIOS = new Set(['tool-round', 'echo', 'hang', 'ignore-interrupt', 'crash',
  'malformed', 'oversized', 'wrong-session', 'no-status', 'partial', 'duplicate-terminal',
  'conflicting-terminal', 'queued', 'approval', 'unsupported-request', 'early-terminal',
  'environment', 'exit-nonzero', 'settlement-hang', 'frame-flood', 'canonical-wire', 'untrusted-event-name']);

function validate(input) {
  if (!object(input) || Object.keys(input).some(k => !['key','text','scenario','iterationBudget','timeoutMs'].includes(k)))
    throw new HarnessError('INVALID_INPUT');
  const { key, text, scenario = 'tool-round', iterationBudget = 2, timeoutMs = 5000 } = input;
  if (typeof key !== 'string' || !/^[A-Za-z0-9_.-]{1,100}$/.test(key)) throw new HarnessError('INVALID_KEY');
  if (typeof text !== 'string' || Buffer.byteLength(text) > 8192) throw new HarnessError('INVALID_TEXT');
  if (!SCENARIOS.has(scenario)) throw new HarnessError('UNSUPPORTED_SCENARIO');
  if (!Number.isInteger(iterationBudget) || iterationBudget < 1 || iterationBudget > 16) throw new HarnessError('INVALID_BUDGET');
  if (!Number.isInteger(timeoutMs) || timeoutMs < 100 || timeoutMs > 10000) throw new HarnessError('INVALID_TIMEOUT');
  return { key, text, scenario, iterationBudget, timeoutMs };
}
export function isolatedEnvironment(home, inherited = process.env) {
  const env = {};
  for (const [key, value] of Object.entries(inherited)) {
    if (['systemroot', 'windir'].includes(key.toLowerCase())) env[key] = value;
  }
  Object.assign(env, { HOME: home, USERPROFILE: home, APPDATA: home, LOCALAPPDATA: home,
    HERMES_HOME: path.join(home, 'hermes'), OPENCLAW_STATE_DIR: path.join(home, 'openclaw'),
    TMP: home, TEMP: home, TMPDIR: home, LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' });
  return env;
}

export class MockHybridHarness {
  #records = new Map(); #keys = new Map(); #active = null; #poisoned = false;
  constructor({ python, workRoot }) {
    if (typeof python !== 'string' || !path.isAbsolute(python)) throw new HarnessError('ABSOLUTE_PYTHON_REQUIRED');
    if (typeof workRoot !== 'string' || !path.isAbsolute(workRoot)) throw new HarnessError('ABSOLUTE_WORKSPACE_REQUIRED');
    this.python = python; this.workRoot = workRoot;
  }
  capabilities() {
    return { mode: 'scripted-component-slice', start: true, status: true, events: true, cancel: true,
      resume: false, durableIdempotency: false, realModel: false, actualAIAgent: false,
      fullOpenClawGateway: false, autonomousGoals: false, approvals: 'deny', sandbox: false };
  }
  start(input) {
    const request = validate(input); const fingerprint = JSON.stringify(request);
    const oldId = this.#keys.get(request.key);
    if (oldId) {
      if (this.#records.get(oldId).fingerprint !== fingerprint) throw new HarnessError('IDEMPOTENCY_CONFLICT');
      return oldId;
    }
    if (this.#poisoned) throw new HarnessError('CLEANUP_UNCONFIRMED');
    if (this.#active) throw new HarnessError('BUSY');
    if (this.#records.size >= 64) throw new HarnessError('RECORD_LIMIT');
    const runId = randomUUID();
    const state = { explicitCancellationObserved: false, terminalOutcomeFrozen: false, sharedAbortAllowedAfterTerminalOutcome: false };
    const record = { runId, request, fingerprint, state: 'queued', code: null, events: [], completion: deferred(),
      submitted: false, sessionId: null, response: null, process: null, cancellationState: state,
      cancellation: createAgentHarnessAttemptCancellation({ state }) };
    this.#records.set(runId, record); this.#keys.set(request.key, runId); this.#active = runId;
    this.#event(record, 'queued');
    Promise.resolve().then(() => this.#execute(record));
    return runId;
  }
  #get(runId) {
    const record = this.#records.get(runId);
    if (!record) throw new HarnessError('UNKNOWN_RUN');
    return record;
  }
  #event(record, type) {
    // Payload and prompt content are deliberately not copied into operational events.
    if (record.events.length < 160) record.events.push({ seq: record.events.length + 1, type });
  }
  status(runId) {
    const r = this.#get(runId);
    return structuredClone({ runId, state: r.state, code: r.code, sessionId: r.sessionId,
      response: r.response, submitted: r.submitted, process: r.process,
      mock: true, modelCalls: 0, events: r.events });
  }
  events(runId, afterSeq = 0) {
    if (!Number.isInteger(afterSeq) || afterSeq < 0) throw new HarnessError('INVALID_CURSOR');
    return this.status(runId).events.filter(e => e.seq > afterSeq);
  }
  async wait(runId) { await this.#get(runId).completion.promise; return this.status(runId); }
  cancel(runId) {
    const r = this.#get(runId);
    if (r.cancellationState.terminalOutcomeFrozen || r.cancellationState.explicitCancellationObserved) return false;
    this.#event(r, 'cancel_requested');
    r.cancellation.abortExplicitly(new HarnessError('CANCELLED'));
    return true;
  }
  resume() { throw new HarnessError('UNSUPPORTED_RESUME'); }

  async #execute(r) {
    const signal = r.cancellation.controller.signal; const terminal = deferred();
    let peer, deadlines, payload, failure, home;
    const startedAtMs = Date.now(), startedAtMonotonicMs = performance.now();
    const awaitPeer = promise => abortable(peer.guard(promise), signal);
    try {
      if (signal.aborted) throw signal.reason;
      r.state = 'running'; this.#event(r, 'running');
      deadlines = createAgentHarnessAttemptDeadlineController({ startedAtMs, startedAtMonotonicMs,
        timeoutMs: r.request.timeoutMs, settlementTimeoutMs: 1000, signal,
        onTimeout: () => r.cancellation.abortExplicitly(new HarnessError('TIMED_OUT')) });
      await mkdir(this.workRoot, { recursive: true });
      home = await mkdtemp(path.join(this.workRoot, 'run-'));
      if (signal.aborted) throw signal.reason;
      peer = new StdioPeer({ python: this.python, script: FIXTURE,
        args: [r.request.scenario, String(r.request.iterationBudget)], cwd: home,
        env: isolatedEnvironment(home),
        onRequest: frame => {
          if (!r.sessionId || frame.params.session_id !== r.sessionId) throw new HarnessError('SESSION_MISMATCH');
          if (frame.method === 'approval') {
            this.#event(r, 'approval_denied'); return { result: { choice: 'deny' } };
          }
          this.#event(r, 'unsupported_request_denied');
          return { error: { code: -32601, message: 'No handler in mock harness' } };
        },
        onEvent: event => {
          if (!r.sessionId || event.session_id !== r.sessionId) throw new HarnessError('SESSION_MISMATCH');
          if (event.type !== 'message.complete') {
            const known = ['status.update','tool.start','tool.complete','message.delta'];
            this.#event(r, known.includes(event.type) ? event.type : 'peer_notification'); return;
          }
          const next = event.payload;
          if (!object(next) || !['complete','error','interrupted'].includes(next.status) || typeof next.text !== 'string')
            throw new HarnessError('UNPROVEN_TERMINAL');
          if (!r.submitted) throw new HarnessError('UNEXPECTED_TERMINAL');
          if (payload && JSON.stringify(next) !== JSON.stringify(payload)) throw new HarnessError('CONFLICTING_TERMINAL');
          if (!payload) { payload = next; this.#event(r, 'native_terminal'); terminal.resolve(next); }
        } });
      const ready = await awaitPeer(peer.ready.promise);
      if (ready.session_authority === true) throw new HarnessError('UNSUPPORTED_WIRE');
      await awaitPeer(peer.request('client.capabilities', { server_requests: true }));
      const created = await awaitPeer(peer.request('session.create', { idempotency_key: r.runId,
        cwd: home, cwd_explicit: true, provider: 'mock', model: 'scripted', close_on_disconnect: true }));
      if (!object(created) || typeof created.session_id !== 'string' || !created.session_id || created.session_id.length > 160)
        throw new HarnessError('INVALID_SESSION');
      r.sessionId = created.session_id; this.#event(r, 'session_created');
      // Once written, loss of the reply is an uncertain effect. Never resubmit automatically.
      r.submitted = true;
      const ack = await awaitPeer(peer.request('prompt.submit', { session_id: r.sessionId, text: r.request.text }));
      if (!object(ack) || ack.status !== 'streaming') throw new HarnessError('SUBMISSION_NOT_EXCLUSIVE');
      this.#event(r, 'accepted');
      await awaitPeer(terminal.promise);
      r.state = 'settling'; this.#event(r, 'settling');
      deadlines.beginSettlement(Date.now());
      peer.endInput();
      const closure = await abortable(peer.closed.promise, signal);
      if (peer.failureCode) throw new HarnessError(peer.failureCode);
      if (closure.exitCode !== 0) throw new HarnessError('PEER_EXIT_ERROR');
      if (payload.status === 'error' || payload.partial || payload.error) throw new HarnessError('NATIVE_FAILURE');
      if (payload.status === 'interrupted') throw new HarnessError('CANCELLED');
      r.response = payload.text;
    } catch (error) {
      failure = error instanceof HarnessError ? error.code : 'INTEGRATION_ERROR';
    } finally {
      deadlines?.dispose();
      if (peer) {
        if (failure && r.sessionId && !peer.stopping && !peer.closure)
          peer.request('session.interrupt', { session_id: r.sessionId }).catch(() => {});
        try { r.process = await peer.reap(); }
        catch { r.process = { reaped: false, exitCode: null, signal: null, killSent: false }; }
        if (!r.process.reaped) { failure = 'CLEANUP_UNCONFIRMED'; this.#poisoned = true; }
        if (!failure && peer.failureCode) failure = peer.failureCode;
      }
      if (!failure && signal.aborted) failure = signal.reason?.code ?? 'CANCELLED';
      // Success freezes only after transport validation AND owned-child closure.
      r.cancellation.freezeTerminalOutcome(); r.cancellation.dispose();
      r.code = failure ?? null;
      r.state = !failure ? 'completed' : failure === 'CANCELLED' ? 'cancelled'
        : failure === 'TIMED_OUT' ? 'timed_out'
        : ['CLEANUP_UNCONFIRMED','PEER_CLOSED','PEER_EXIT_ERROR','INPUT_CLOSED'].includes(failure) && r.submitted ? 'unknown' : 'failed';
      if (failure) r.response = null;
      this.#event(r, r.state); this.#active = null; r.completion.resolve();
    }
  }
}
