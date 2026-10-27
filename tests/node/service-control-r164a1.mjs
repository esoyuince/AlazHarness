/** R164 cross-language closure source fixture: the Python server and child pipes are real.
 * Kernel/mount/native ownership ports are explicitly doubled by the Python fixture.
 * Generic stop/finish execute over explicit test ports; no installed runtime/kernel acceptance.
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
  assert.ok(!text.includes(config.owner.token), 'owner token stays private');
  assert.ok(!text.includes(config.socketPath), 'private socket path stays private');
  assert.equal(value.retryAllowed, false);
  assert.equal(value.kernelVerified, false);
  if (value.state) {
    const closed = value.state === 'CLOSED';
    assert.equal(value.serviceClosed, closed);
    assert.equal(value.closureReported, closed);
    assert.equal(value.hostHttpReachabilityVerified, false);
    if (closed) {
      assert.equal(value.endpoint, null);
      assert.equal(value.completion.physicalStoresClosed, 3);
      for (const [key, flag] of Object.entries(value.completion))
        if (key !== 'physicalStoresClosed') assert.equal(flag, true, key);
    } else assert.equal(value.completion.imageLeaseReleased, false);
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

const before = await cli('service-status', id(4));
assert.equal(before.code, 0); assert.equal(before.value.state, 'NEW');
checked(await client.start(id(1)));
await ready();
const close = await cli('close', id(2));
if (scenario === 'deferred-close') {
  assert.equal(close.code, 3); assert.equal(close.value.state, 'UNKNOWN');
  assert.equal(close.value.completion.childExited, false);
  await until(async () => (await logRows()).some(row => row.action === 'close'),
    'first original child close was not accepted');
  await writeFile(config.journal + '.close-release', 'release fixture final');
  const observed = await retiredChild();
  assert.equal(observed.state, 'DRAINING');
  assert.equal(observed.completion.volumeUnmounted, false);
  const replay = checked(await client.close(id(2)));
  assert.equal(replay.state, 'DRAINING');
  assert.equal(replay.completion.volumeUnmounted, false);
  // New explicit intent advances only the still-unattempted volume closure.
  const finish = await cli('close', id(3));
  assert.equal(finish.code, 0); assert.equal(finish.value.outcome, 'closed_reported');
} else if (scenario === 'lost-final-reply') {
  assert.equal(close.code, 3); assert.equal(close.value.outcome, 'error');
  assert.equal(close.value.error.mayHaveBeenAccepted, true);
  const observed = checked(await client.status(id(6)));
  assert.equal(observed.state, 'CLOSED');
  assert.equal(checked(await client.close(id(2))).state, 'CLOSED');
  assert.equal(checked(await client.close(id(3))).state, 'CLOSED');
} else if (['lost-stop-reply', 'autoclear-pending', 'stream-close-failure'].includes(scenario)) {
  assert.equal(close.code, 3); assert.equal(close.value.state, 'UNKNOWN');
  assert.equal(close.value.completion.childExited, true);
  assert.equal(close.value.completion.volumeUnmounted, scenario !== 'lost-stop-reply');
  for (const value of [await client.status(id(6)), await client.close(id(2)), await client.close(id(3))]) {
    checked(value); assert.equal(value.state, 'UNKNOWN');
    assert.equal(value.completion.childExited, true);
    assert.equal(value.completion.imageLeaseReleased, false);
  }
} else if (['closed-lifecycle', 'stale-after-closed'].includes(scenario)) {
  assert.equal(close.code, 0); assert.equal(close.value.state, 'CLOSED');
  assert.equal(close.value.outcome, 'closed_reported');
  if (scenario === 'stale-after-closed') {
    const wrongOwner = new ServiceControlClient({ ...options, owner: { ...options.owner,
      token: 'f'.repeat(32) } });
    assert.equal(checked(await wrongOwner.status(id(6))).outcome, 'error');
    const wrongService = new ServiceControlClient({ ...options, serviceId: 'b'.repeat(32) });
    assert.equal(checked(await wrongService.close(id(3))).outcome, 'error');
  }
  assert.equal(checked(await client.close(id(2))).state, 'CLOSED');
  assert.equal(checked(await client.close(id(3))).state, 'CLOSED');
} else assert.fail('unknown R164 source fixture scenario');
const terminal = await cli('service-status', id(5));
const failed = ['lost-stop-reply', 'autoclear-pending', 'stream-close-failure'].includes(scenario);
assert.equal(terminal.code, failed ? 3 : 0);
assert.equal(terminal.value.state, failed ? 'UNKNOWN' : 'CLOSED');
const rows = await logRows();
assert.equal(rows.filter(row => 'bootstrapBytes' in row).length, 1);
assert.deepEqual(rows.filter(row => 'action' in row).map(row => row.action), ['close']);
console.log(JSON.stringify({ result: 'PASS', scenario, observations, bootstrapCount: 1,
  closeCommandCount: 1, readOnlyStatusSentChildCommand: false,
  installedSupervisor: false, kernelConfinementTested: false, nativeRuntime: false,
  realProviderCalls: 0 }));
