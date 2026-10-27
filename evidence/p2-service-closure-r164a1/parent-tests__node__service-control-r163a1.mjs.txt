/** R163 cross-language source fixture: the Python server and child pipes are real.
 * Kernel/mount/native ownership ports are explicitly doubled by the Python fixture.
 * No installed runtime, HTTP endpoint, provider, or volume release is exercised.
 */
import assert from 'node:assert/strict';
import net from 'node:net';
import { spawn } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { CONTROL_PROTOCOL, ServiceControlClient } from '../../packages/claw-hermes/service-control.mjs';

const scenario = process.argv[2];
let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  assert.ok(input.length <= 16384, 'fixture configuration bound');
}
const config = JSON.parse(input);
const options = { socketPath: config.socketPath, serviceId: config.serviceId,
  owner: config.owner, requestTimeoutMs: 3000 };
const client = new ServiceControlClient(options);
const id = n => String(n).repeat(32);
const script = fileURLToPath(new URL('../../scripts/alaz_local.mjs', import.meta.url));
let observations = 0;

function checked(value) {
  const text = JSON.stringify(value);
  assert.ok(!text.includes(config.owner.token), 'owner token is not a public diagnostic');
  assert.ok(!text.includes(config.socketPath), 'private path is not a public diagnostic');
  assert.equal(value.retryAllowed, false);
  assert.equal(value.kernelVerified, false);
  if (value.state) {
    assert.notEqual(value.state, 'CLOSED', 'plan step4 remains open');
    assert.equal(value.serviceClosed, false);
    assert.equal(value.closureReported, false);
    assert.equal(value.hostHttpReachabilityVerified, false);
    for (const flag of ['volumeUnmounted', 'imageLeaseReleased', 'fenceRemovedAfterCleanup'])
      assert.equal(value.completion[flag], false);
  }
  observations++;
  return value;
}

async function logRows() {
  try {
    const raw = await readFile(config.journal, 'utf8');
    return raw.trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
  } catch (error) {
    if (error.code === 'ENOENT') return [];
    throw error;
  }
}

async function until(predicate, reason) {
  const deadline = performance.now() + 4000;
  while (performance.now() < deadline) {
    if (await predicate()) return;
    await delay(10);
  }
  assert.fail(reason);
}

async function ready() {
  let last;
  await until(async () => {
    last = checked(await client.status(id(7)));
    return last.state === 'READY';
  }, 'same original child did not become READY');
  return last;
}

async function retiredChild() {
  let last;
  await until(async () => {
    last = checked(await client.status(id(8)));
    return last.state === 'DRAINING' && last.completion.childExited;
  }, 'same child final/exit/EOF was not observed');
  assert.equal(last.completion.physicalStoresClosed, 3);
  assert.equal(last.completion.profileLeaseReleased, true);
  return last;
}

async function cli(command, requestId) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'].includes(key.toUpperCase())));
  Object.assign(env, { ALAZ_SERVICE_SOCKET: options.socketPath, ALAZ_SERVICE_ID: options.serviceId,
    ALAZ_SERVICE_OWNER_PID: String(options.owner.pid),
    ALAZ_SERVICE_OWNER_START_TICKS: String(options.owner.startTicks),
    ALAZ_SERVICE_OWNER_TOKEN: options.owner.token });
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, command, '--request-id', requestId,
      '--request-timeout-ms', '3000'], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', exceeded = false;
    const timer = setTimeout(() => { child.kill(); reject(new Error('fixture CLI deadline')); }, 5000);
    child.stdout.on('data', chunk => { stdout += chunk; if (stdout.length > 65536) { exceeded = true; child.kill(); } });
    child.stderr.on('data', chunk => { stderr += chunk; if (stderr.length > 65536) { exceeded = true; child.kill(); } });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', (code, signal) => {
      clearTimeout(timer);
      try {
        assert.equal(exceeded, false); assert.equal(signal, null); assert.equal(stderr, '');
        resolve({ code, value: checked(JSON.parse(stdout)) });
      } catch (error) { reject(error); }
    });
  });
}

if (scenario === 'lifecycle') {
  const before = await cli('service-status', id(4));
  assert.equal(before.code, 0); assert.equal(before.value.state, 'NEW');
  const start = await cli('start', id(1));
  assert.equal(start.code, 0); assert.equal(start.value.state, 'READY');
  assert.equal(start.value.serviceStarted, true);
  const status = await cli('service-status', id(5));
  assert.equal(status.code, 0); assert.equal(status.value.state, 'READY');
  const close = await cli('close', id(2));
  assert.equal(close.code, 3); assert.equal(close.value.state, 'DRAINING');
  assert.equal(close.value.completion.childExited, true);
  const after = await cli('service-status', id(6));
  assert.equal(after.code, 3); assert.equal(after.value.state, 'DRAINING');
  assert.equal(after.value.completion.childExited, true);
} else if (scenario === 'lost-start') {
  const abort = new AbortController();
  const pending = client.start(id(1), { signal: abort.signal });
  await until(async () => (await logRows()).some(row => 'bootstrapBytes' in row),
    'bootstrap was not written before disconnect');
  abort.abort();
  const lost = checked(await pending);
  assert.equal(lost.outcome, 'error'); assert.equal(lost.error.mayHaveBeenAccepted, true);
  await writeFile(config.journal + '.release', 'release fixture reply');
  await ready();
  assert.equal(checked(await client.start(id(1))).state, 'READY');
  assert.equal(checked(await client.start(id(9))).outcome, 'error');
  checked(await client.close(id(2))); await retiredChild();
} else if (scenario === 'lost-close') {
  assert.equal(checked(await client.start(id(1))).state, 'READY');
  const abort = new AbortController();
  const pending = client.close(id(2), { signal: abort.signal });
  await until(async () => (await logRows()).some(row => row.action === 'close'),
    'close was not written before disconnect');
  abort.abort();
  const lost = checked(await pending);
  assert.equal(lost.outcome, 'error'); assert.equal(lost.error.mayHaveBeenAccepted, true);
  await writeFile(config.journal + '.close-release', 'release fixture final');
  await retiredChild();
  checked(await client.close(id(2)));
  checked(await client.close(id(9)));  // The existing final may be observed; no second close is sent.
} else if (scenario === 'stale-owner') {
  const wrong = new ServiceControlClient({ ...options,
    owner: { ...options.owner, token: options.owner.token === 'f'.repeat(32) ? 'e'.repeat(32) : 'f'.repeat(32) } });
  const refused = checked(await wrong.start(id(1)));
  assert.equal(refused.outcome, 'error');
  const oldTicks = new ServiceControlClient({ ...options,
    owner: { ...options.owner, startTicks: options.owner.startTicks + 1 } });
  assert.equal(checked(await oldTicks.status(id(2))).outcome, 'error');
  assert.equal(checked(await client.status(id(3))).state, 'NEW');
} else if (scenario === 'id-conflict') {
  assert.equal(checked(await client.start(id(1))).state, 'READY');
  assert.equal(checked(await client.close(id(1))).outcome, 'error');
  assert.equal(checked(await client.status(id(3))).state, 'READY');
  checked(await client.close(id(2))); await retiredChild();
} else if (scenario === 'trailing-frame') {
  await new Promise((resolve, reject) => {
    const socket = net.createConnection({ path: options.socketPath, allowHalfOpen: true });
    const timer = setTimeout(() => { socket.destroy(); reject(new Error('fixture socket deadline')); }, 3000);
    socket.once('connect', () => socket.end(JSON.stringify({ command: 'start',
      expectedOwner: options.owner, protocol: CONTROL_PROTOCOL, requestId: id(1),
      serviceId: options.serviceId }) + '\n{}\n'));
    socket.on('data', () => {});
    socket.once('error', error => { clearTimeout(timer); reject(error); });
    socket.once('end', () => { clearTimeout(timer); socket.destroy(); resolve(); });
    socket.once('close', () => { clearTimeout(timer); resolve(); });
  });
  assert.equal(checked(await client.status(id(3))).state, 'NEW');
} else if (scenario === 'pending-start') {
  const first = checked(await client.start(id(1)));
  assert.equal(first.state, 'UNKNOWN');
  assert.equal(first.completion.childExited, false);
  await until(async () => (await logRows()).some(row => 'bootstrapBytes' in row),
    'original timed-out bootstrap did not reach the synthetic child');
  const before = await logRows();
  assert.equal(before.filter(row => 'bootstrapBytes' in row).length, 1);
  checked(await client.status(id(3)));
  await writeFile(config.journal + '.release', 'release fixture reply');
  await ready();
  assert.equal(checked(await client.start(id(9))).outcome, 'error');
  checked(await client.close(id(2))); await retiredChild();
} else {
  assert.fail('unknown source fixture scenario');
}

const rows = await logRows();
const expected = ['stale-owner', 'trailing-frame'].includes(scenario) ? 0 : 1;
assert.equal(rows.filter(row => 'bootstrapBytes' in row).length, expected);
assert.deepEqual(rows.filter(row => 'action' in row).map(row => row.action), expected ? ['close'] : []);
console.log(JSON.stringify({ result: 'PASS', scenario, observations,
  bootstrapCount: expected, closeCommandCount: expected,
  readOnlyStatusSentChildCommand: false, installedSupervisor: false,
  kernelConfinementTested: false, nativeRuntime: false, realProviderCalls: 0 }));
