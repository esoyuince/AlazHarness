/** Strict queued cancellation reports; HTTP fixtures never run a native worker. */
import assert from 'node:assert/strict';
import http from 'node:http';
import { classifyRunRecovery } from '../../packages/claw-hermes/run-recovery.mjs';
import { LocalControlClient, controlExitCode } from '../../packages/claw-hermes/local-control.mjs';

const scenario = process.argv[2];
const runId = 'run_' + 'a'.repeat(32), admissionId = 'b'.repeat(32);
const queued = () => ({ run_id: runId, admission_id: admissionId, session_id: runId,
  status: 'cancelled', execution_generation: null,
  execution_proof: { schema: 1, kind: 'canonical_queued_cancellation',
    run_id: runId, admission_id: admissionId, session_id: runId,
    authority_epoch: 3, instance_id: 'owned-r159-instance', execution_generation: null,
    no_worker_started_verified: true } });
const rejected = value => assert.throws(() => classifyRunRecovery(value), TypeError);

if (scenario === 'valid') {
  const result = classifyRunRecovery(queued());
  assert.equal(result.classification, 'canonical_terminal_reported');
  assert.equal(result.noWorkerStartedReported, true);
  assert.equal(result.backendConfirmed, true);
  assert.equal(result.canonicalVerified, false);
  assert.equal(result.requiresOperator, false);
  assert.equal(result.retryAllowed, false);
  assert.equal(result.repairAllowed, false);
  assert.equal(Object.isFrozen(result), true);
} else if (scenario === 'null-alone') {
  const run = queued(); delete run.execution_proof;
  run.no_worker_started_verified = true; run.canonicalVerified = true;
  const result = classifyRunRecovery(run);
  assert.equal(result.classification, 'terminal_unverified');
  assert.equal(result.noWorkerStartedReported, false);
  assert.equal(result.backendConfirmed, false);
  assert.equal(result.canonicalVerified, false);
  assert.equal(result.requiresOperator, true);
} else if (scenario === 'identity') {
  for (const [name, value] of [['run_id', 'run_' + 'c'.repeat(32)],
    ['admission_id', 'd'.repeat(32)], ['session_id', 'another-session']]) {
    const run = queued(); run.execution_proof[name] = value; rejected(run);
  }
  for (const name of ['admission_id', 'session_id']) {
    const run = queued(); delete run[name]; rejected(run);
  }
} else if (scenario === 'shape') {
  for (const value of [null, [], true, {}, 'claimed-proof']) {
    const run = queued(); run.execution_proof = value; rejected(run);
  }
  for (const name of Object.keys(queued().execution_proof)) {
    const run = queued(); delete run.execution_proof[name]; rejected(run);
  }
  const extra = queued(); extra.execution_proof.physical_worker_terminal = true; rejected(extra);
  for (const [name, value] of [['schema', 2], ['schema', true], ['kind', 'physical_completion'],
    ['no_worker_started_verified', 1], ['no_worker_started_verified', false]]) {
    const run = queued(); run.execution_proof[name] = value; rejected(run);
  }
} else if (scenario === 'authority') {
  for (const value of [null, 0, -1, true, 1.5, '3', Number.MAX_SAFE_INTEGER + 1]) {
    const run = queued(); run.execution_proof.authority_epoch = value; rejected(run);
  }
  for (const value of [null, '', '../owner', 'bad instance', 'x'.repeat(129)]) {
    const run = queued(); run.execution_proof.instance_id = value; rejected(run);
  }
} else if (scenario === 'contradictions') {
  for (const status of ['completed', 'failed', 'interrupted', 'started', 'queued', 'unknown']) {
    const run = queued(); run.status = status; rejected(run);
  }
  for (const name of ['completed', 'failed', 'interrupted', 'partial']) {
    const run = queued(); run[name] = true; rejected(run);
  }
  for (const value of [0, 1, false, undefined]) {
    const run = queued(); run.execution_generation = value; rejected(run);
    const other = queued(); other.execution_proof.execution_generation = value; rejected(other);
  }
} else if (['http-valid', 'http-lost-ack', 'http-malformed'].includes(scenario)) {
  const requests = [];
  const server = http.createServer((req, res) => {
    requests.push({ method: req.method, path: req.url });
    assert.equal(req.headers.authorization, 'Bearer fixture-r159-operator');
    req.resume();
    if (req.method === 'POST' && req.url === '/v1/runs/' + runId + '/stop') {
      if (scenario === 'http-lost-ack') { req.socket.destroy(); return; }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ run_id: runId, status: 'cancelled' }));
    } else if (req.method === 'GET' && req.url === '/v1/runs/' + runId) {
      const run = queued();
      if (scenario === 'http-malformed') run.execution_proof.admission_id = 'f'.repeat(32);
      res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(run));
    } else { res.writeHead(404); res.end('{}'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const client = new LocalControlClient({ baseUrl: 'http://127.0.0.1:' + server.address().port,
      token: 'fixture-r159-operator', requestTimeoutMs: 1000 });
    const result = await client.cancel(runId, { watchTimeoutMs: 2000, pollIntervalMs: 5 });
    assert.equal(requests.filter(row => row.method === 'POST').length, 1);
    assert.equal(requests.filter(row => row.method === 'GET').length, 1);
    assert.equal(result.cancellation.physicalWorkerTerminalVerified, false);
    assert.equal(result.retryAllowed, false);
    if (scenario === 'http-malformed') {
      assert.equal(controlExitCode(result), 3);
      assert.equal(result.cancellation.terminalReported, false);
      assert.equal(result.cancellation.noWorkerStartedReported, false);
    } else {
      assert.equal(controlExitCode(result), 0);
      assert.equal(result.outcome, 'terminal_reported');
      assert.equal(result.run.executionGeneration, null);
      assert.equal(result.run.canonicalTupleReported, true);
      assert.equal(result.run.canonicalVerified, false);
      assert.equal(result.run.noWorkerStartedReported, true);
      assert.equal(result.cancellation.noWorkerStartedReported, true);
      assert.equal(result.cancellation.terminalReported, true);
      assert.equal(result.cancellation.requestAcknowledged, scenario !== 'http-lost-ack');
      assert.equal(result.cancellation.requestMayHaveBeenAccepted, true);
    }
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
} else throw new Error('unknown scenario');
console.log(JSON.stringify({ result: 'PASS', scenario, realProviderCalls: 0, nativeWorkerStarted: false }));
