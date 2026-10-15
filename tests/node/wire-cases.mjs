import assert from 'node:assert/strict';
import { setTimeout as sleep } from 'node:timers/promises';
import { HermesRunsClient, HarnessError } from '../../packages/claw-hermes/hermes-runs.mjs';
import { createAgentHarnessAttemptCancellation } from '../../packages/upstream/openclaw/attempt-cancellation.ts';
import { createAgentHarnessAttemptDeadlineController } from '../../packages/upstream/openclaw/attempt-deadlines.ts';

const [scenario, baseUrl, token] = process.argv.slice(2);
const client = new HermesRunsClient({ baseUrl, token, requestTimeoutMs: 1000, maxResponseBytes: 8192 });
const opts = { executionTimeoutMs: 1000, settlementTimeoutMs: 300, pollIntervalMs: 5 };
const request = (input = 'success', key = 'test-' + scenario) => ({ input, idempotencyKey: key });
const errorCode = (code) => (error) => error instanceof HarnessError && error.code === code;
let proof = {};

switch (scenario) {
  case 'unverified-terminal': {
    const a=await client.start(request('unverified-terminal'));const r=await client.reconcile(a.run_id);
    assert.equal(r.classification,'terminal_unverified');assert.equal(r.transportConfirmed,true);
    assert.equal(r.backendConfirmed,false);assert.equal(r.canonicalVerified,false);
    assert.equal(r.requiresOperator,true);assert.equal(r.retryAllowed,false);break;
  }
  case 'reconcile-live': {
    const a=await client.start(request('hold'));const r=await client.reconcile(a.run_id);
    assert.equal(r.run.status,'running');assert.equal(r.stopRequested,false);break;
  }
  case 'resume-timeout-readonly': case 'resume-abort-readonly': {
    const a=await client.start(request('hold'));const abort=new AbortController();
    const r=client.resume(a.run_id,{...opts,executionTimeoutMs:40,signal:abort.signal,
      onStatus:()=>{if(scenario==='resume-abort-readonly')abort.abort();}});
    await assert.rejects(r,e=>e.code==='observation_interrupted'&&e.stopRequested===false);break;
  }
  case 'success': {
    const admission = await client.start(request()); const events = [];
    const result = await client.observe(admission.run_id, { ...opts, onStatus: (s) => events.push(s.status) });
    assert.equal(admission.status, 'started'); assert.equal(result.run.status, 'completed');
    assert.equal(result.run.output, '42'); assert.equal(result.backendConfirmed, true);
    assert.equal(result.stopRequested, false); assert.deepEqual(events, ['running', 'completed']);
    proof = { run_id: admission.run_id, events, output: result.run.output, backendConfirmed: true }; break;
  }
  case 'duplicate': {
    const [a, b] = await Promise.all([client.start(request()), client.start(request())]);
    assert.equal(a.run_id, b.run_id); assert.equal(Number(a.replayed) + Number(b.replayed), 1); break;
  }
  case 'conflict': {
    await client.start(request());
    await assert.rejects(client.start(request('different')), errorCode('http_409')); break;
  }
  case 'lost-ack': {
    await assert.rejects(client.start(request('lost-ack')), (e) => e.code === 'write_outcome_unknown' && e.mayHaveBeenAccepted);
    // Deliberate explicit caller retry, identical key/body. Adapter itself did not retry.
    const recovered = await client.start(request('lost-ack')); assert.equal(recovered.replayed, true);
    assert.equal((await client.observe(recovered.run_id, opts)).run.status, 'completed'); break;
  }
  case 'partial': case 'budget': {
    const a = await client.start(request(scenario)); const result = await client.observe(a.run_id, opts);
    assert.equal(result.run.status, 'failed'); assert.equal(result.run.partial, true);
    assert.equal(result.run.completed, false); assert.equal(result.backendConfirmed, true); break;
  }
  case 'cancel': {
    const a = await client.start(request('hold')); const abort = new AbortController();
    const result = await client.observe(a.run_id, { ...opts, signal: abort.signal,
      onStatus: () => abort.abort('user-cancel') });
    assert.equal(result.run.status, 'cancelled'); assert.equal(result.stopRequested, true);
    assert.equal(result.backendConfirmed, true); assert.equal(result.hostReason, 'cancelled'); break;
  }
  case 'timeout': {
    const a = await client.start(request('hold'));
    const result = await client.observe(a.run_id, { ...opts, executionTimeoutMs: 45 });
    assert.equal(result.run.status, 'cancelled'); assert.equal(result.hostReason, 'execution_timeout'); break;
  }
  case 'unconfirmed': {
    const a = await client.start(request('ignore-stop'));
    await assert.rejects(client.observe(a.run_id, { ...opts, executionTimeoutMs: 30, settlementTimeoutMs: 50 }),
      (e) => e.code === 'settlement_unconfirmed' && e.state === 'unknown' && e.backendConfirmed === false); break;
  }
  case 'unknown': case 'approval': {
    const a = await client.start(request(scenario)); const result = await client.observe(a.run_id, opts);
    assert.equal(result.run.status, scenario === 'approval' ? 'waiting_for_approval' : 'unknown');
    assert.equal(result.requiresOperator, true); assert.equal(result.backendConfirmed, false);
    assert.equal(result.stopRequested, false); break;
  }
  case 'resume': {
    const a = await client.start(request());
    const freshClient = new HermesRunsClient({ baseUrl, token });
    assert.equal((await freshClient.resume(a.run_id, opts)).run.output, '42'); break;
  }
  case 'oversized': case 'wrong-id': case 'contradictory': case 'redirect': {
    const expected = { oversized: 'response_too_large', 'wrong-id': 'invalid_run_response',
      contradictory: 'contradictory_terminal_response', redirect: 'transport_error' }[scenario];
    const a = await client.start(request(scenario));
    await assert.rejects(client.status(a.run_id), errorCode(expected)); break;
  }
  case 'preaborted': {
    const abort = new AbortController(); abort.abort();
    await assert.rejects(client.start(request(), { signal: abort.signal }),
      (e) => e.code === 'aborted_before_request' && e.mayHaveBeenAccepted === false); break;
  }
  case 'bad-input': {
    for (const args of [{}, { input: '', idempotencyKey: 'k' }, { input: 'a', idempotencyKey: 'has spaces' },
      { input: 'a', idempotencyKey: '' }, { input: 'x'.repeat(65537), idempotencyKey: 'k' }]) {
      await assert.rejects(client.start(args), (e) => e instanceof HarnessError);
    }
    await assert.rejects(client.status('../outside'), errorCode('invalid_run_id')); break;
  }
  case 'bad-endpoint': {
    for (const url of ['https://example.org/', 'http://localhost/', 'file:///tmp/x',
      'http://127.0.0.1/p/profile', 'http://127.0.0.1/?secret=x', 'http://' + 'u:p@' + '127.0.0.1/']) {
      assert.throws(() => new HermesRunsClient({ baseUrl: url, token }), HarnessError);
    }
    assert.throws(() => new HermesRunsClient({ baseUrl, token: 'invalid\nheader' }), HarnessError); break;
  }
  case 'not-found': {
    await assert.rejects(client.resume('run_' + '0'.repeat(32), opts), errorCode('http_404')); break;
  }
  case 'observer-failure': {
    const a = await client.start(request());
    const result = await client.observe(a.run_id, { ...opts, onStatus: () => { throw new Error('observer'); } });
    assert.equal(result.run.status, 'completed'); break;
  }
  case 'terminal-freeze': {
    const state = { explicitCancellationObserved: false, terminalOutcomeFrozen: false, sharedAbortAllowedAfterTerminalOutcome: false };
    let notifications = 0; const abort = new AbortController();
    const c = createAgentHarnessAttemptCancellation({ upstreamSignal: abort.signal, state, onAttemptAbort: () => notifications++ });
    c.freezeTerminalOutcome(); abort.abort('late'); c.abortExplicitly('later');
    assert.equal(c.controller.signal.aborted, false); assert.equal(notifications, 0); c.dispose(); break;
  }
  case 'cancel-idempotent': {
    const state = { explicitCancellationObserved: false, terminalOutcomeFrozen: false, sharedAbortAllowedAfterTerminalOutcome: false };
    let notifications = 0;
    const c = createAgentHarnessAttemptCancellation({ state, onAttemptAbort: () => notifications++ });
    c.abortExplicitly('first'); c.abortExplicitly('second');
    assert.equal(state.explicitCancellationReason, 'first'); assert.equal(notifications, 1); c.dispose(); break;
  }
  case 'settlement-no-extension': {
    const abort = new AbortController(); let fired = 0; const changed = [];
    const d = createAgentHarnessAttemptDeadlineController({ startedAtMs: Date.now(), startedAtMonotonicMs: performance.now(),
      timeoutMs: 1000, settlementTimeoutMs: 40, signal: abort.signal, onTimeout: () => fired++,
      onDeadlineChanged: (v) => changed.push(v) });
    d.beginSettlement(Date.now()); const first = changed.at(-1).deadlineAtMs;
    await sleep(15); d.beginSettlement(Date.now()); assert.equal(changed.length, 2);
    assert.equal(changed.at(-1).deadlineAtMs, first); await sleep(50); assert.equal(fired, 1);
    d.beginSettlement(Date.now()); await sleep(50); assert.equal(fired, 1); d.dispose(); break;
  }
  case 'disposed-no-revival': {
    const abort = new AbortController(); let fired = 0;
    const d = createAgentHarnessAttemptDeadlineController({ startedAtMs: Date.now(), startedAtMonotonicMs: performance.now(),
      timeoutMs: 20, settlementTimeoutMs: 20, signal: abort.signal, onTimeout: () => fired++ });
    d.dispose(); d.beginSettlement(Date.now()); await sleep(40);
    assert.equal(d.ownsExecutionWait(), false); assert.equal(fired, 0); break;
  }
  case 'unsupported': {
    assert.throws(() => client.events(), errorCode('unsupported_sse'));
    assert.throws(() => client.approve(), errorCode('unsupported_approval'));
    assert.throws(() => client.steer(), errorCode('unsupported_steering'));
    assert.throws(() => client.resolveUnknown(), errorCode('operator_reconciliation_required'));
    assert.equal(client.capabilities().tokenOrCostBudgetEnforced, false); break;
  }
  default: throw new Error('Unknown fixture scenario');
}
console.log(JSON.stringify({ scenario, result: 'PASS', scope: 'mock-wire-contract-not-full-Hermes', ...proof }));
