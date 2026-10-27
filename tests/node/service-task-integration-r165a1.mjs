/** Real Node/CLI -> Unix server -> child pipes -> actual loopback HTTP fixture.
 * Native lifecycle/store/API handlers and kernel ports are explicit doubles.
 */
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { LocalControlClient } from '../../packages/claw-hermes/local-control.mjs';
import { ServiceControlClient } from '../../packages/claw-hermes/service-control.mjs';

const scenario = process.argv[2];
assert.ok(['task-lifecycle', 'wrong-bearer', 'lost-dispatch-reply'].includes(scenario));
let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  assert.ok(input.length <= 16384, 'fixture connection bound');
}
const config = JSON.parse(input);
const requestId = 'b'.repeat(32), runId = 'run_' + 'd'.repeat(32);
const token = 'fixture-task-bearer', wrongToken = 'fixture-wrong-bearer';
const prompt = 'Read the allowed fixture.\nTürkçe satır.';
const script = fileURLToPath(new URL('../../scripts/alaz_local.mjs', import.meta.url));
let hostTcpCalls = 0, observations = 0;
const trap = http.createServer((request, response) => {
  hostTcpCalls++; response.writeHead(503); response.end();
});
await new Promise((resolve, reject) => {
  trap.once('error', reject); trap.listen(0, '127.0.0.1', resolve);
});
const options = { socketPath: config.socketPath, serviceId: config.serviceId,
  owner: config.owner, requestTimeoutMs: 5000, taskTransport: 'supervised-service',
  baseUrl: 'http://127.0.0.1:' + trap.address().port, token };
const lifecycle = new ServiceControlClient(options);
const client = new LocalControlClient(options);
const oldFetch = globalThis.fetch;
globalThis.fetch = () => { throw new Error('fixture forbids a global fetch fallback'); };

function checked(value) {
  const raw = JSON.stringify(value);
  for (const item of [token, wrongToken, config.owner.token, config.socketPath])
    assert.ok(!raw.includes(item), 'private fixture configuration leaked');
  assert.equal(value.retryAllowed, false);
  if (value.run) assert.equal(value.run.canonicalVerified, false);
  if (value.state) {
    assert.equal(value.kernelVerified, false);
    assert.equal(value.hostHttpReachabilityVerified, false);
  }
  observations++;
  return value;
}

async function cli(command, args = [], bearer = token) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'].includes(key.toUpperCase())));
  Object.assign(env, { ALAZ_TASK_TRANSPORT: 'supervised-service',
    ALAZ_SERVICE_SOCKET: options.socketPath, ALAZ_SERVICE_ID: options.serviceId,
    ALAZ_SERVICE_OWNER_PID: String(options.owner.pid),
    ALAZ_SERVICE_OWNER_START_TICKS: String(options.owner.startTicks),
    ALAZ_SERVICE_OWNER_TOKEN: options.owner.token,
    ALAZ_BASE_URL: options.baseUrl, ALAZ_API_TOKEN: bearer });
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, command, ...args,
      '--request-timeout-ms', '5000'], { env, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', exceeded = false;
    const timer = setTimeout(() => { child.kill(); reject(new Error('fixture CLI deadline')); }, 8000);
    child.stdout.on('data', chunk => {
      stdout += chunk; if (stdout.length > 65536) { exceeded = true; child.kill(); }
    });
    child.stderr.on('data', chunk => {
      stderr += chunk; if (stderr.length > 65536) { exceeded = true; child.kill(); }
    });
    child.stdin.on('error', () => {});
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', (code, signal) => {
      clearTimeout(timer);
      try {
        assert.equal(exceeded, false); assert.equal(signal, null); assert.equal(stderr, '');
        resolve({ code, value: checked(JSON.parse(stdout)) });
      } catch (error) { reject(error); }
    });
    child.stdin.end(command === 'task' ? prompt : '');
  });
}

try {
  const before = await cli('service-status', ['--request-id', '1'.repeat(32)]);
  assert.equal(before.code, 0); assert.equal(before.value.state, 'NEW');
  const started = await cli('start', ['--request-id', '2'.repeat(32)]);
  assert.equal(started.code, 0); assert.equal(started.value.state, 'READY');
  let ready = checked(await lifecycle.status('3'.repeat(32)));
  assert.equal(ready.state, 'READY');

  let taskOutcome;
  if (scenario === 'wrong-bearer') {
    const rejected = await cli('task', ['--request-id', requestId, '--model', 'fixture-model',
      '--input', '-'], wrongToken);
    assert.equal(rejected.code, 3); assert.equal(rejected.value.outcome, 'error');
    assert.equal(rejected.value.error.httpStatus, 401);
    assert.equal(rejected.value.error.mayHaveBeenAccepted, false);
    taskOutcome = rejected.value.outcome;
  } else {
    let task;
    if (scenario === 'lost-dispatch-reply') {
      task = checked(await client.task({ requestId, model: 'fixture-model', input: prompt }));
      assert.equal(task.outcome, 'error');
      assert.equal(task.error.mayHaveBeenAccepted, true);
      assert.equal(task.nextAction, 'observe_original_request');
    } else {
      const accepted = await cli('task', ['--request-id', requestId, '--model', 'fixture-model', '--input', '-']);
      assert.equal(accepted.code, 0); task = accepted.value;
      assert.equal(task.outcome, 'accepted'); assert.equal(task.run.runId, runId);
    }
    taskOutcome = task.outcome;
    // A fresh CLI performs a read-only original native request lookup. There is
    // no retained client permit to replay and no second task submission.
    const request = await cli('request', ['--request-id', requestId]);
    assert.equal(request.code, 0); assert.equal(request.value.outcome, 'located');
    assert.equal(request.value.observation.requestId, requestId);
    assert.equal(request.value.observation.runId, runId);
    assert.equal(request.value.observation.writesPerformed, false);
    const status = checked(await client.status(runId));
    assert.equal(status.outcome, 'observed'); assert.equal(status.run.status, 'completed');
    const result = await cli('result', ['--run-id', runId]);
    assert.equal(result.code, 0); assert.equal(result.value.outcome, 'result_available');
    assert.equal(result.value.output, 'scoped result');
    assert.equal(result.value.goalAchievementIndependentlyVerified, false);
    const usage = checked(await client.usage(runId));
    assert.equal(usage.outcome, 'usage_observed');
    assert.equal(usage.usage.totalTokens, 5); assert.equal(usage.usage.costMicrousd, null);
    const cancel = await cli('cancel', ['--run-id', runId, '--wait-ms', '2000', '--poll-ms', '10']);
    assert.equal(cancel.code, 0); assert.equal(cancel.value.outcome, 'terminal_reported');
    assert.equal(cancel.value.run.status, 'cancelled');
    assert.equal(cancel.value.cancellation.requestAcknowledged, true);
    assert.equal(cancel.value.cancellation.physicalWorkerTerminalVerified, false);
  }
  ready = checked(await lifecycle.status('4'.repeat(32)));
  assert.equal(ready.state, 'READY', 'HTTP uncertainty/rejection must retain original lifecycle');
  const closed = await cli('close', ['--request-id', '5'.repeat(32)]);
  assert.equal(closed.code, 0); assert.equal(closed.value.state, 'CLOSED');
  assert.equal(closed.value.completion.childExited, true);
  assert.equal(closed.value.completion.imageLeaseReleased, true);
  const final = checked(await lifecycle.status('6'.repeat(32)));
  assert.equal(final.state, 'CLOSED');
  // Flush any already-scheduled local listener callback before asserting that
  // both in-process and CLI code ignored the caller's TCP route anchor.
  await delay(0);
  assert.equal(hostTcpCalls, 0);
  console.log(JSON.stringify({ result: 'PASS', scenario, observations, taskOutcome,
    serviceStateAfterTasks: ready.state, lifecycleState: final.state, hostTcpCalls,
    installedSupervisor: false, nativeRuntime: false, nativeApiHandlersDoubled: true,
    kernelConfinementTested: false, realModelCalls: 0, realProviderCalls: 0 }));
} finally {
  globalThis.fetch = oldFetch;
  trap.closeAllConnections(); await new Promise(resolve => trap.close(resolve));
}
