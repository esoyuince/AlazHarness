/** Offline HTTP contract fixtures. No Hermes runtime, model, broker or service install. */
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { LocalControlClient, controlExitCode, controlError } from '../../packages/claw-hermes/local-control.mjs';
import { HarnessError } from '../../packages/claw-hermes/hermes-runs.mjs';

const scenario = process.argv[2], requestId = 'a'.repeat(32), runId = 'run_' + 'b'.repeat(32);
const key = 'ah1-' + 'c'.repeat(32) + '-' + requestId, token = 'fixture-operator-bearer';
const secret = 'MUST_NOT_APPEAR_IN_CONTROL_DIAGNOSTICS', requests = [], serverErrors = [];
const intent = { requestId, model: 'bounded-fixture-model', input: 'Read the allowed fixture.' };
let consumed = false, gets = 0, required = 'all', usage = { input_tokens: 2, output_tokens: 3, total_tokens: 5 };
let requestClassification = 'native_run_located', requestMutation = null;
const requestActions = { not_found: 'retain_request_id_no_retry', issued_not_dispatched: 'retain_issued_request_no_retry',
  handoff_unresolved: 'retain_consumed_request_no_retry', native_run_located: 'observe_existing_run' };
let afterGet = null, queuedCancellation = false;
const server = http.createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const raw = Buffer.concat(chunks).toString('utf8'), body = raw ? JSON.parse(raw) : null;
    requests.push({ method: req.method, path: req.url, body, headers: req.headers });
    assert.equal(req.headers.authorization, 'Bearer ' + token);
    const send = (value, status = 200) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(value)); };
    if (req.url === '/alaz/host/v1/capabilities') {
      send({ hostGateVersion: 1, dispatchPath: '/alaz/host/v1/dispatch', nativeStoreOwner: true,
        dispatchAtMostOnce: true, automaticRetry: false, scope: 'default_profile_new_run',
        executionBoundaryVersion: required === 'no-execution' ? null : 1,
        providerBrokerVersion: required === 'no-broker' ? null : 1,
        providerBrokerBackend: required === 'no-broker' ? null : 'linux_unix_credential_broker' });
    } else if (req.url === '/alaz/host/v1/intents') {
      assert.equal(req.method, 'POST');
      assert.deepEqual(body, { requestId, body: { input: intent.input, model: intent.model } });
      send({ hostGateVersion: 1, requestId, idempotencyKey: key, dispatchState: consumed ? 'consumed' : 'issued',
        expiresAtMs: Date.now() + 30000, replayed: consumed, retryAllowed: false }, 201);
    } else if (req.url === '/alaz/host/v1/dispatch') {
      assert.equal(req.method, 'POST');
      assert.equal(req.headers['idempotency-key'], key);
      assert.equal(req.headers['x-alaz-execution-version'], '1');
      assert.equal(req.headers['x-alaz-provider-broker-version'], '1');
      consumed = true;
      if (['lost-ack', 'cli-lost-ack'].includes(scenario)) { req.socket.destroy(); return; }
      send({ run_id: runId, status: 'started', replayed: false, arbitrarySecret: secret }, 202);
    } else if (req.url === '/alaz/host/v1/requests/' + requestId) {
      assert.equal(req.method, 'GET');
      const observation = { hostGateVersion: 1, requestObservationVersion: 1, requestId,
        classification: requestClassification,
        dispatchState: requestClassification === 'not_found' ? null : requestClassification === 'issued_not_dispatched' ? 'issued' : 'consumed',
        runId: requestClassification === 'native_run_located' ? runId : null,
        snapshotOnly: true, writesPerformed: false, canonicalVerified: false, retryAllowed: false, repairAllowed: false,
        requiresOperator: requestClassification !== 'native_run_located', nextAction: requestActions[requestClassification] };
      send(requestMutation ? requestMutation(observation) : observation);
    } else if (req.url === '/v1/runs/' + runId + '/stop') {
      assert.equal(req.method, 'POST');
      assert.deepEqual(body, {});
      if (scenario === 'cancel-lost-ack') { req.socket.destroy(); return; }
      if (scenario === 'cancel-malformed-ack') { send({ run_id: 'wrong', status: 'stopping' }); return; }
      send({ run_id: runId, status: scenario === 'cancel-ack' ? 'cancelled' : 'stopping' });
    } else if (req.url === '/v1/runs/' + runId) {
      assert.equal(req.method, 'GET');
      gets++;
      let status = 'completed';
      if (['watch-timeout', 'watch-interrupted', 'cancel-timeout', 'cancel-malformed-ack', 'cli-watch-interrupted'].includes(scenario)) status = 'running';
      if (scenario === 'watch' && gets === 1) status = 'running';
      if (scenario === 'cancel-ack') status = gets === 1 ? 'running' : 'cancelled';
      if (scenario === 'cancel-lost-ack') status = 'cancelled';
      if (['cancel-unknown', 'status-unknown'].includes(scenario)) status = 'unknown';
      if (scenario === 'failed-result') status = 'failed';
      const value = { run_id: runId, status, admission_id: 'd'.repeat(32), session_id: 'api-local-fixture',
        execution_generation: 1, output: 'scoped result', usage, arbitrarySecret: secret, error: secret };
      if (queuedCancellation) { value.status = 'cancelled'; value.execution_generation = null; }
      if (scenario === 'unverified-result') delete value.admission_id;
      if (scenario === 'contradiction') value.completed = false;
      send(value);
      afterGet?.();
    } else {
      send({ error: secret }, 404);
    }
  } catch (error) {
    serverErrors.push(error);
    res.writeHead(500, { 'Content-Type': 'application/json' }); res.end('{}');
  }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const baseUrl = 'http://127.0.0.1:' + server.address().port;
const options = { baseUrl, token, requestTimeoutMs: 500 };
const client = new LocalControlClient(options);
const count = path => requests.filter(row => row.path === path).length;
const stops = () => count('/v1/runs/' + runId + '/stop');
const dispatches = () => count('/alaz/host/v1/dispatch');
const script = fileURLToPath(new URL('../../scripts/alaz_local.mjs', import.meta.url));

async function cli(args, { stdin = '', connected = true, onSpawn } = {}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'].includes(key.toUpperCase())));
  if (connected) Object.assign(env, { ALAZ_BASE_URL: baseUrl, ALAZ_API_TOKEN: token });
  return await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], { env, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error('CLI test deadline')); }, 6000);
    child.stdout.on('data', chunk => { stdout += chunk; }); child.stderr.on('data', chunk => { stderr += chunk; });
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('close', (code, signal) => { clearTimeout(timer); resolve({ code, signal, stdout, stderr,
      value: stdout.startsWith('{') ? JSON.parse(stdout) : null }); });
    child.stdin.on('error', () => {}); child.stdin.end(stdin);
    onSpawn?.(child);
  });
}

let temporary = null;
try {
  if (scenario === 'task') {
    const result = await client.task(intent);
    assert.equal(result.outcome, 'accepted'); assert.equal(result.requestId, requestId);
    assert.equal(result.run.runId, runId); assert.equal(result.completionVerified, false);
    assert.equal(controlExitCode(result), 0); assert.equal(dispatches(), 1);
    assert.ok(!JSON.stringify(result).includes(secret));
  } else if (scenario === 'boundaries') {
    for (const [mode, code] of [['no-execution', 'execution_boundary_required'], ['no-broker', 'provider_broker_required']]) {
      required = mode;
      const result = await new LocalControlClient({ ...options, requireExecution: false, requireProviderBroker: false }).task(intent);
      assert.equal(result.error.code, code); assert.equal(dispatches(), 0);
      assert.equal(count('/alaz/host/v1/intents'), 0);
    }
  } else if (scenario === 'lost-ack') {
    const first = await client.task(intent);
    assert.equal(first.error.code, 'host_write_outcome_unknown'); assert.equal(first.error.mayHaveBeenAccepted, true);
    assert.equal(first.requestId, requestId); assert.equal(first.nextAction, 'observe_original_request');
    const repeated = await new LocalControlClient(options).task(intent);
    assert.equal(repeated.error.code, 'host_dispatch_already_attempted'); assert.equal(dispatches(), 1);
    const observed = await new LocalControlClient(options).request(requestId);
    assert.equal(observed.outcome, 'located'); assert.equal(observed.observation.runId, runId);
    assert.equal(observed.observation.canonicalVerified, false); assert.equal(dispatches(), 1);
  } else if (scenario === 'request-states') {
    for (const classification of Object.keys(requestActions)) {
      requestClassification = classification;
      const result = await client.request(requestId);
      assert.equal(result.observation.classification, classification);
      assert.equal(result.observation.runId, classification === 'native_run_located' ? runId : null);
      assert.equal(controlExitCode(result), classification === 'native_run_located' ? 0 : 3);
    }
    assert.equal(requests.length, 4); assert.ok(requests.every(row => row.method === 'GET'));
  } else if (scenario === 'request-malformed') {
    requestClassification = 'not_found';
    for (const mutation of [
      row => ({ ...row, classification: ['not_found'] }),
      row => ({ ...row, classification: {} }),
      row => ({ ...row, classification: 1 }),
      row => ({ ...row, writesPerformed: true }),
      row => ({ ...row, canonicalVerified: true }),
      row => ({ ...row, retryAllowed: true }),
      row => ({ ...row, requestId: 'f'.repeat(32) }),
      row => ({ ...row, runId }),
      row => ({ ...row, unexpected: secret }),
    ]) {
      requestMutation = mutation;
      const result = await client.request(requestId);
      assert.equal(result.error.code, 'invalid_request_observation'); assert.equal(controlExitCode(result), 3);
      assert.ok(!JSON.stringify(result).includes(secret));
    }
    assert.ok(requests.every(row => row.method === 'GET')); assert.equal(dispatches(), 0);
  } else if (scenario === 'watch') {
    const result = await client.watch(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.run.status, 'completed'); assert.equal(result.outcome, 'terminal_reported');
    assert.equal(result.stopRequested, false); assert.equal(gets, 2); assert.equal(stops(), 0);
  } else if (scenario === 'watch-timeout') {
    const result = await client.watch(runId, { watchTimeoutMs: 40, pollIntervalMs: 5 });
    assert.equal(result.error.code, 'observation_interrupted'); assert.equal(result.stopRequested, false);
    assert.equal(controlExitCode(result), 3); assert.ok(gets > 0); assert.equal(stops(), 0);
  } else if (scenario === 'watch-interrupted') {
    const controller = new AbortController(); afterGet = () => controller.abort();
    const result = await client.watch(runId, { signal: controller.signal, watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.error.code, 'observation_interrupted'); assert.equal(result.stopRequested, false); assert.equal(stops(), 0);
  } else if (scenario === 'cancel-ack') {
    const result = await client.cancel(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.cancellation.requestAcknowledged, true); assert.equal(result.cancellation.terminalReported, true);
    assert.equal(result.cancellation.effectReported, 'cancelled'); assert.equal(gets, 2); assert.equal(stops(), 1);
    assert.equal(result.cancellation.physicalWorkerTerminalVerified, false); assert.equal(controlExitCode(result), 0);
    queuedCancellation = true;
    const queued = await client.cancel(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(queued.run.status, 'cancelled'); assert.equal(queued.run.terminalReported, true);
    assert.equal(queued.run.canonicalTupleReported, false); assert.equal(queued.run.classification, 'terminal_unverified');
    assert.equal(queued.outcome, 'unresolved'); assert.equal(queued.cancellation.terminalReported, false);
    assert.equal(queued.cancellation.physicalWorkerTerminalVerified, false); assert.equal(controlExitCode(queued), 3);
    assert.equal(stops(), 2); // One explicit stop per call; the null generation grants no retry.
  } else if (scenario === 'cancel-timeout') {
    const result = await client.cancel(runId, { watchTimeoutMs: 40, pollIntervalMs: 5 });
    assert.equal(result.cancellation.requestAcknowledged, true); assert.equal(result.cancellation.terminalReported, false);
    assert.equal(result.error.code, 'observation_interrupted'); assert.equal(controlExitCode(result), 3); assert.equal(stops(), 1);
  } else if (scenario === 'cancel-lost-ack') {
    const result = await client.cancel(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.cancellation.requestAcknowledged, false); assert.equal(result.cancellation.requestMayHaveBeenAccepted, true);
    assert.equal(result.cancellation.terminalReported, true); assert.equal(result.cancellation.effectReported, 'cancelled');
    assert.equal(stops(), 1); assert.equal(controlExitCode(result), 0);
  } else if (scenario === 'cancel-malformed-ack') {
    const result = await client.cancel(runId, { watchTimeoutMs: 40, pollIntervalMs: 5 });
    assert.equal(result.cancellation.requestAcknowledged, false); assert.equal(result.cancellation.requestMayHaveBeenAccepted, true);
    assert.equal(result.cancellation.requestError.code, 'invalid_run_response');
    assert.equal(result.cancellation.terminalReported, false); assert.equal(controlExitCode(result), 3); assert.equal(stops(), 1);
  } else if (scenario === 'cancel-unknown') {
    const result = await client.cancel(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.outcome, 'unresolved'); assert.equal(result.cancellation.terminalReported, false);
    assert.equal(result.cancellation.effectReported, 'unconfirmed'); assert.equal(stops(), 1); assert.equal(controlExitCode(result), 3);
  } else if (scenario === 'cancel-race') {
    const result = await client.cancel(runId, { watchTimeoutMs: 1000, pollIntervalMs: 1 });
    assert.equal(result.cancellation.effectReported, 'completed'); assert.equal(result.run.status, 'completed');
    assert.equal(stops(), 1); assert.equal(gets, 1);
  } else if (scenario === 'cancel-invalid') {
    const controller = new AbortController(); controller.abort();
    for (const option of [{ watchTimeoutMs: 0 }, { pollIntervalMs: 0 }, { signal: controller.signal }]) {
      const result = await client.cancel(runId, option);
      assert.equal(result.cancellation.requestAttempted, false);
    }
    assert.equal(requests.length, 0);
  } else if (scenario === 'result') {
    const result = await client.result(runId);
    assert.equal(result.output, 'scoped result'); assert.equal(result.outputIsCompletedResponse, true);
    assert.equal(result.run.canonicalVerified, false); assert.equal(result.goalAchievementIndependentlyVerified, false);
    assert.ok(!JSON.stringify(result).includes(secret)); assert.equal(controlExitCode(result), 0);
  } else if (scenario === 'failed-result') {
    const result = await client.result(runId);
    assert.equal(result.output, 'scoped result'); assert.equal(result.outputIsCompletedResponse, false);
    assert.equal(controlExitCode(result), 2); assert.ok(!JSON.stringify(result).includes(secret));
  } else if (scenario === 'unverified-result') {
    const result = await client.result(runId);
    assert.equal(result.output, null); assert.equal(result.outcome, 'result_unavailable'); assert.equal(controlExitCode(result), 3);
  } else if (scenario === 'contradiction') {
    const result = await client.status(runId);
    assert.equal(result.error.code, 'contradictory_terminal_response'); assert.equal(controlExitCode(result), 3);
    assert.ok(!JSON.stringify(result).includes(secret));
  } else if (scenario === 'status-unknown') {
    const result = await client.status(runId);
    assert.equal(result.outcome, 'unresolved'); assert.equal(result.run.status, 'unknown'); assert.equal(controlExitCode(result), 3);
  } else if (scenario === 'usage') {
    const result = await client.usage(runId);
    assert.equal(result.usage.coverage, 'complete_fields'); assert.equal(result.usage.totalTokens, 5);
    assert.equal(result.usage.costMicrousd, null); assert.equal(result.usage.physicalAttemptCoverageVerified, false);
    assert.equal(result.usage.profileBudgetAvailable, false); assert.equal(controlExitCode(result), 0);
  } else if (scenario === 'usage-incomplete') {
    for (const [value, coverage] of [[null, 'unavailable'], [{}, 'unavailable'],
      [{ input_tokens: 2 }, 'partial_fields'], [{ input_tokens: true }, 'invalid'],
      [{ input_tokens: -1 }, 'invalid'], [{ input_tokens: '2' }, 'invalid'],
      [{ input_tokens: 2, output_tokens: 3, total_tokens: 99 }, 'invalid']]) {
      usage = value;
      const result = await client.usage(runId);
      assert.equal(result.usage.coverage, coverage); assert.equal(result.usage.totalTokens, null);
      assert.equal(result.usage.costMicrousd, null); assert.equal(controlExitCode(result), 3);
    }
  } else if (scenario === 'cli-task') {
    const result = await cli(['task', '--request-id', requestId, '--model', intent.model, '--input', '-'], { stdin: intent.input });
    assert.equal(result.code, 0, result.stderr); assert.equal(result.value.outcome, 'accepted');
    assert.equal(result.value.requestId, requestId); assert.equal(dispatches(), 1);
    assert.ok(!result.stdout.includes(token)); assert.ok(!result.stdout.includes(intent.input));
  } else if (scenario === 'cli-file') {
    temporary = await mkdtemp(join(tmpdir(), 'alaz-control-test-'));
    const path = join(temporary, 'input.txt'); await writeFile(path, intent.input);
    const result = await cli(['task', '--request-id', requestId, '--model', intent.model, '--input', path]);
    assert.equal(result.code, 0, result.stderr); assert.equal(dispatches(), 1);
  } else if (scenario === 'cli-input-errors') {
    for (const input of [Buffer.alloc(65537, 65), Buffer.from([0xc3, 0x28]), '   ']) {
      const result = await cli(['task', '--request-id', requestId, '--model', intent.model, '--input', '-'], { stdin: input });
      assert.equal(result.code, 64, result.stderr); assert.equal(result.value.error.mayHaveBeenAccepted, false);
    }
    assert.equal(requests.length, 0);
  } else if (scenario === 'cli-lost-ack') {
    const result = await cli(['task', '--request-id', requestId, '--model', intent.model, '--input', '-'], { stdin: intent.input });
    assert.equal(result.code, 3, result.stderr); assert.equal(result.value.requestId, requestId);
    assert.equal(result.value.error.mayHaveBeenAccepted, true); assert.equal(dispatches(), 1);
    assert.ok(!result.stdout.includes(intent.input)); assert.ok(!result.stdout.includes(token));
  } else if (scenario === 'cli-request') {
    const result = await cli(['request', '--request-id', requestId]);
    assert.equal(result.code, 0, result.stderr); assert.equal(result.value.observation.runId, runId);
    assert.equal(requests.length, 1); assert.equal(requests[0].method, 'GET');
  } else if (scenario === 'cli-unsupported') {
    for (const command of ['start', 'close']) {
      const result = await cli([command], { connected: false });
      assert.equal(result.code, 64); assert.equal(result.value.outcome, 'unsupported');
      assert.equal(result.value.serviceStarted, false); assert.equal(result.value.serviceClosed, false);
    }
    assert.equal(requests.length, 0);
  } else if (scenario === 'cli-arguments') {
    for (const args of [['task'], ['status', '--token', secret], ['watch', '--run-id', runId, '--wait-ms', '0'],
      ['status', '--run-id', runId, '--run-id', runId], ['status', '--run-id', runId, '--unknown', secret]]) {
      const result = await cli(args);
      assert.equal(result.code, 64, result.stderr); assert.ok(!result.stdout.includes(secret));
    }
    const absent = await cli(['status', '--run-id', runId], { connected: false });
    assert.equal(absent.code, 64); assert.equal(absent.value.error.code, 'missing_local_connection');
    assert.equal(requests.length, 0);
  } else if (scenario === 'cli-watch-interrupted') {
    const result = await cli(['watch', '--run-id', runId, '--wait-ms', '1000', '--poll-ms', '5'], {
      onSpawn: child => { afterGet = () => { afterGet = null; child.kill('SIGINT'); }; },
    });
    assert.equal(result.code, 3, result.stderr); assert.equal(result.value.error.code, 'observation_interrupted');
    assert.equal(result.value.stopRequested, false); assert.equal(stops(), 0);
  } else if (scenario === 'errors-sanitized') {
    const result = controlError(new Error(secret), { command: 'task' });
    assert.equal(result.error.code, 'local_control_error'); assert.ok(!JSON.stringify(result).includes(secret));
    const malformed = controlError(new HarnessError(['transport_error']), { command: 'status' });
    assert.equal(malformed.error.code, 'local_control_error'); assert.equal(typeof malformed.error.code, 'string');
    const typed = controlError(new HarnessError('host_http_500', { httpStatus: 500, hostCode: secret,
      mayHaveBeenAccepted: true, token, stack: secret }), { command: 'task', requestId });
    assert.equal(typed.error.httpStatus, 500); assert.equal(typed.error.mayHaveBeenAccepted, true);
    assert.ok(!JSON.stringify(typed).includes(secret)); assert.ok(!JSON.stringify(typed).includes(token));
  } else throw new Error('Unknown test scenario');
  assert.equal(serverErrors.length, 0, serverErrors.map(error => error.stack).join('\n'));
  assert.equal(count('/v1/runs'), 0);
  console.log(JSON.stringify({ scenario, result: 'PASS', calls: requests.length, dispatches: dispatches(), stops: stops(),
    rawStartCalls: 0, nativeRuntime: false, realProviderCalls: 0 }));
} finally {
  server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  if (temporary) await rm(temporary, { recursive: true, force: true });
}
