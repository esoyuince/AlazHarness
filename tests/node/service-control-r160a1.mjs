/** Real Unix/CLI contract fixtures. No installed supervisor/native/model claim. */
import assert from 'node:assert/strict';
import net from 'node:net';
import { spawn } from 'node:child_process';
import { chmod, mkdtemp, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { HarnessError } from '../../packages/claw-hermes/hermes-runs.mjs';
import { CONTROL_PROTOCOL, ServiceControlClient, validateServiceReply,
  serviceControlError, serviceControlExitCode } from '../../packages/claw-hermes/service-control.mjs';

const scenario = process.argv[2];
const requestId = 'a'.repeat(32), serviceId = 'b'.repeat(32);
const owner = { pid: 1234, startTicks: 5678, token: 'c'.repeat(32) };
const endpoint = 'http://127.0.0.1:17654';
const secret = 'PRIVATE_CREDENTIAL_MUST_NOT_APPEAR';
const flags = ['transportRetired', 'runtimeRetired', 'apiSessionsRetired', 'consumerDetached',
  'defaultExecutorJoined', 'profileLeaseReleased', 'childExited', 'volumeUnmounted',
  'imageLeaseReleased', 'fenceRemovedAfterCleanup'];
const expected = { command: 'start', requestId, serviceId, owner };
let fixtureCalls = 0, mutationCalls = 0;

function reply(command = 'start', state = 'READY', id = requestId) {
  return { protocol: CONTROL_PROTOCOL, command, requestId: id, serviceId, owner: { ...owner }, state,
    endpoint: ['NEW', 'CLOSED'].includes(state) ? null : endpoint,
    endpointScope: ['NEW', 'CLOSED'].includes(state) ? null : 'private-service-loopback',
    completion: { ...Object.fromEntries(flags.map(key => [key, state === 'CLOSED'])),
      physicalStoresClosed: state === 'CLOSED' ? 3 : 0 }, retryAllowed: false, error: null };
}
function frame(value) { return JSON.stringify(value) + '\n'; }
function noSecrets(value) {
  const text = JSON.stringify(value);
  assert.ok(!text.includes(secret));
  assert.ok(!text.includes(owner.token));
}
async function withSocket(handler, run) {
  const dir = await mkdtemp(join(tmpdir(), 'alaz-svc-'));
  const path = join(dir, 'control.sock');
  const calls = [], failures = [], connections = new Set();
  const server = net.createServer({ allowHalfOpen: true }, socket => {
    connections.add(socket);
    socket.on('close', () => connections.delete(socket));
    socket.on('error', () => {});
    const chunks = [];
    socket.on('data', chunk => chunks.push(chunk));
    socket.on('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('ascii');
        assert.ok(raw.endsWith('\n'));
        assert.equal(raw.split('\n').length, 2);
        const request = JSON.parse(raw);
        assert.deepEqual(Object.keys(request).sort(), ['command', 'expectedOwner', 'protocol', 'requestId', 'serviceId']);
        assert.equal(request.protocol, CONTROL_PROTOCOL);
        assert.equal(request.serviceId, serviceId);
        assert.ok(/^[a-f0-9]{32}$/.test(request.requestId));
        assert.deepEqual(Object.keys(request.expectedOwner).sort(), ['pid', 'startTicks', 'token']);
        assert.ok(Number.isSafeInteger(request.expectedOwner.pid) && request.expectedOwner.pid > 0);
        assert.ok(Number.isSafeInteger(request.expectedOwner.startTicks) && request.expectedOwner.startTicks > 0);
        assert.ok(/^[a-f0-9]{32}$/.test(request.expectedOwner.token));
        calls.push(request); fixtureCalls++;
        // Required future server contract: check the ORIGINAL owner before
        // any synthetic lifecycle effect, including any command handler call.
        if (!['pid', 'startTicks', 'token'].every(key => request.expectedOwner[key] === owner[key])) {
          const refusal = reply(request.command, 'NEW', request.requestId);
          refusal.error = 'service_owner_precondition_failed';
          socket.end(frame(refusal));
          return;
        }
        if (request.command !== 'status') mutationCalls++;
        handler(request, socket, calls);
      } catch (error) { failures.push(error); socket.destroy(); }
    });
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(path, resolve); });
  await chmod(path, 0o600);
  const options = { socketPath: path, serviceId, owner, requestTimeoutMs: 500 };
  try {
    await run(new ServiceControlClient(options), calls, options);
    assert.deepEqual(failures, [], failures.map(error => error.stack).join('\n'));
  } finally {
    for (const connection of connections) connection.destroy();
    await new Promise(resolve => server.close(resolve));
    await rm(dir, { recursive: true, force: true });
  }
}
const script = fileURLToPath(new URL('../../scripts/alaz_local.mjs', import.meta.url));
async function cli(args, options, { configure = true, patchEnv = {}, onSpawn } = {}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'].includes(key.toUpperCase())));
  if (configure) Object.assign(env, { ALAZ_SERVICE_SOCKET: options.socketPath,
    ALAZ_SERVICE_ID: serviceId, ALAZ_SERVICE_OWNER_PID: String(owner.pid),
    ALAZ_SERVICE_OWNER_START_TICKS: String(owner.startTicks), ALAZ_SERVICE_OWNER_TOKEN: owner.token });
  Object.assign(env, patchEnv);
  return await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], { env, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    child.stdout.on('data', data => { stdout += data; });
    child.stderr.on('data', data => { stderr += data; });
    child.on('error', reject);
    child.on('close', (code, signal) => {
      try { resolve({ code, signal, stdout, stderr, value: JSON.parse(stdout) }); }
      catch (error) { reject(new Error('CLI output invalid: ' + stderr, { cause: error })); }
    });
    onSpawn?.(child);
  });
}

if (scenario === 'schema') {
  assert.deepEqual(validateServiceReply(reply(), expected), reply());
  assert.deepEqual(validateServiceReply(reply('close', 'CLOSED'), { ...expected, command: 'close' }), reply('close', 'CLOSED'));
  for (const key of flags) {
    const value = reply('close', 'CLOSED'); value.completion[key] = false;
    assert.throws(() => validateServiceReply(value, { ...expected, command: 'close' }), /invalid_service_response/);
  }
  for (const count of [0, 1, 2, 4, true, '3', null]) {
    const value = reply('close', 'CLOSED'); value.completion.physicalStoresClosed = count;
    assert.throws(() => validateServiceReply(value, { ...expected, command: 'close' }), /invalid_service_response/);
  }
  for (const mutate of [v => { v.extra = 'x'; }, v => { delete v.error; },
    v => { v.endpoint = 'http://localhost:17654'; }, v => { v.endpoint = 'http://127.0.0.1:80/path'; },
    v => { v.endpoint = null; v.endpointScope = null; }, v => { v.endpointScope = 'host-loopback'; },
    v => { v.retryAllowed = true; }, v => { v.completion.childExited = true; },
    v => { v.error = secret; }, v => { v.owner.pid = true; }]) {
    const value = reply(); mutate(value);
    assert.throws(() => validateServiceReply(value, expected), /invalid_service_response/);
  }
} else if (scenario === 'identity') {
  await withSocket((req, socket, calls) => {
    const value = reply(req.command);
    const mutations = [v => { v.protocol += '-different'; }, v => { v.requestId = 'd'.repeat(32); },
      v => { v.serviceId = 'e'.repeat(32); }, v => { v.command = 'close'; },
      v => { v.owner.pid++; }, v => { v.owner.startTicks++; }, v => { v.owner.token = 'f'.repeat(32); }];
    mutations[calls.length - 1](value); socket.end(frame(value));
  }, async (client, calls) => {
    for (let i = 0; i < 7; i++) {
      const value = await client.start(requestId);
      assert.equal(value.outcome, 'error'); assert.equal(value.serviceStarted, false);
      assert.equal(value.error.code, 'invalid_service_response');
      assert.equal(value.error.mayHaveBeenAccepted, true); noSecrets(value);
    }
    assert.equal(calls.length, 7);
  });
} else if (scenario === 'owner-precondition') {
  let effects = 0;
  await withSocket((req, socket) => {
    if (req.command !== 'status') effects++;
    socket.end(frame(reply(req.command, 'NEW')));
  }, async (client, calls, options) => {
    for (const command of ['start', 'close', 'status']) {
      for (const change of [{ pid: owner.pid + 1 }, { startTicks: owner.startTicks + 1 }, { token: 'f'.repeat(32) }]) {
        const staleOwner = { ...owner, ...change };
        const value = await new ServiceControlClient({ ...options, owner: staleOwner })[command](requestId);
        assert.equal(value.outcome, 'error'); assert.equal(value.error.code, 'invalid_service_response');
        assert.equal(value.requestAttempted, true);
        // A refused response from a different owner is still not an acceptance
        // receipt for the pinned owner; it never authorizes a resend.
        assert.equal(value.error.mayHaveBeenAccepted, command !== 'status');
        assert.equal(value.retryAllowed, false); assert.equal(value.closureReported, false);
        assert.equal(serviceControlExitCode(value), 3); assert.equal(effects, 0);
        noSecrets(value); assert.ok(!JSON.stringify(value).includes(staleOwner.token));
      }
    }
    assert.equal(calls.length, 9); assert.equal(mutationCalls, 0);
    const observed = await client.status(requestId);
    assert.equal(observed.command, 'service-status'); assert.equal(observed.state, 'NEW');
    assert.equal(observed.requestId, requestId); assert.equal(observed.serviceId, serviceId);
    assert.equal(observed.outcome, 'observed'); assert.equal(observed.kernelVerified, false);
    assert.equal(calls.length, 10); assert.equal(effects, 0); assert.equal(mutationCalls, 0);
    assert.equal(calls.at(-1).command, 'status'); noSecrets(observed);
  });
} else if (scenario === 'ready') {
  await withSocket((req, socket) => socket.end(frame(reply(req.command))), async (client, calls) => {
    const value = await client.start(requestId);
    assert.equal(value.outcome, 'ready_reported'); assert.equal(value.serviceStarted, true);
    assert.equal(value.serviceClosed, false); assert.equal(value.closureReported, false);
    assert.equal(value.kernelVerified, false); assert.equal(value.hostHttpReachabilityVerified, false);
    assert.equal(value.endpointScope, 'private-service-loopback'); assert.equal(serviceControlExitCode(value), 0);
    assert.equal(calls.length, 1); noSecrets(value);
  });
} else if (scenario === 'drain-ack') {
  await withSocket((req, socket) => socket.end(frame(reply(req.command, 'DRAINING'))), async (client, calls) => {
    const value = await client.close(requestId);
    assert.equal(value.outcome, 'unresolved'); assert.equal(value.serviceClosed, false);
    assert.equal(value.closureReported, false); assert.equal(value.retryAllowed, false);
    assert.equal(value.nextAction, 'observe_original_service'); assert.equal(serviceControlExitCode(value), 3);
    assert.equal(calls.length, 1); assert.equal(calls[0].command, 'close'); noSecrets(value);
  });
} else if (scenario === 'closed') {
  await withSocket((req, socket) => socket.end(frame(reply(req.command, 'CLOSED'))), async (client, calls) => {
    const value = await client.close(requestId);
    assert.equal(value.outcome, 'closed_reported'); assert.equal(value.serviceClosed, true);
    assert.equal(value.closureReported, true); assert.equal(value.kernelVerified, false);
    assert.equal(value.completion.physicalStoresClosed, 3); assert.equal(serviceControlExitCode(value), 0);
    assert.equal(calls.length, 1); noSecrets(value);
  });
} else if (scenario === 'command-completion') {
  const cases = [['start', 'NEW'], ['start', 'STARTING'], ['start', 'CLOSED'],
    ['close', 'NEW'], ['close', 'STARTING'], ['close', 'READY']];
  await withSocket((req, socket, calls) => socket.end(frame(reply(req.command, cases[calls.length - 1][1]))),
    async (client, calls) => {
      for (const [command, state] of cases) {
        const value = await client[command](requestId);
        assert.equal(value.state, state); assert.equal(value.outcome, 'unresolved');
        assert.equal(serviceControlExitCode(value), 3);
        assert.equal(value.serviceStarted, false);
        assert.equal(value.serviceClosed, state === 'CLOSED');
      }
      assert.equal(calls.length, cases.length);
    });
} else if (scenario === 'partial-close') {
  await withSocket((req, socket, calls) => {
    const value = reply(req.command, 'CLOSED'); value.completion[flags[calls.length - 1]] = false;
    socket.end(frame(value));
  }, async (client, calls) => {
    for (const key of flags) {
      const value = await client.close(requestId);
      assert.equal(value.outcome, 'error', key); assert.equal(value.closureReported, false);
      assert.equal(value.error.mayHaveBeenAccepted, true); assert.equal(serviceControlExitCode(value), 3);
    }
    assert.equal(calls.length, flags.length);
  });
} else if (scenario === 'framing') {
  const raw = frame(reply());
  const cases = [raw.replace('"state":"READY"', '"state":"UNKNOWN","state":"READY"'),
    raw + '{}\n', raw.trimEnd(), raw + 'trailing', '{"invalid":}\n', raw.replace('1234', '1234.0'),
    ' ' + raw, Buffer.from([0xff, 10]), raw.replace('"READY"', '"\\u0052EADY"')];
  await withSocket((req, socket, calls) => socket.end(cases[calls.length - 1]), async (client, calls) => {
    for (const rawCase of cases) {
      const value = await client.start(requestId);
      assert.equal(value.outcome, 'error'); assert.equal(value.serviceStarted, false);
      assert.equal(value.error.mayHaveBeenAccepted, true); noSecrets(value);
    }
    assert.equal(calls.length, cases.length);
  });
} else if (scenario === 'response-bound') {
  await withSocket((req, socket) => socket.end('x'.repeat(65537)), async (client, calls) => {
    const value = await client.start(requestId);
    assert.equal(value.error.code, 'service_response_too_large'); assert.equal(value.error.mayHaveBeenAccepted, true);
    assert.equal(value.closureReported, false); assert.equal(calls.length, 1);
  });
} else if (scenario === 'eof-required') {
  let responseSocket;
  await withSocket((req, socket) => {
    responseSocket = socket;
    socket.write(frame(reply(req.command))); // Deliberately withhold EOF.
  }, async (_, calls, options) => {
    const expectedFrame = Buffer.from(frame(reply()), 'ascii');
    const originalConnect = net.createConnection;
    let clientSocket, settled = false;
    const receivedFrame = new Promise((resolve, reject) => {
      // Observe real client-side bytes without changing transport behavior or
      // adding a product hook. A server write alone does not prove delivery.
      net.createConnection = (...args) => {
        const socket = Reflect.apply(originalConnect, net, args);
        clientSocket = socket;
        const chunks = [];
        let bytes = 0;
        socket.on('data', chunk => {
          chunks.push(chunk); bytes += chunk.length;
          if (bytes >= expectedFrame.length) resolve(Buffer.concat(chunks));
        });
        socket.once('error', reject);
        socket.once('close', () => {
          if (bytes < expectedFrame.length) reject(new Error('Client closed before complete fixture reply'));
        });
        return socket;
      };
    });
    try {
      // This deadline is only a failure watchdog. The proof below uses I/O
      // handshakes, not a scheduling delay or an assumed request-arrival time.
      const pending = new ServiceControlClient({ ...options, requestTimeoutMs: 10000 }).start(requestId)
        .then(value => { settled = true; return value; });
      assert.deepEqual(await receivedFrame, expectedFrame);
      await new Promise(resolve => setImmediate(resolve)); // Let data handlers and promise reactions finish.
      assert.equal(calls.length, 1);
      assert.equal(clientSocket.readableEnded, false);
      assert.equal(settled, false, 'A complete valid frame must remain pending until EOF');
      responseSocket.end(); // Release the EOF only after the pending assertion.
      const value = await pending;
      assert.equal(value.outcome, 'ready_reported'); assert.equal(value.serviceStarted, true);
      assert.equal(calls.length, 1); noSecrets(value);
    } finally {
      net.createConnection = originalConnect;
    }
  });
} else if (scenario === 'lost-response') {
  await withSocket((req, socket) => socket.destroy(), async (client, calls) => {
    const value = await client.close(requestId);
    assert.equal(value.outcome, 'error'); assert.equal(value.error.mayHaveBeenAccepted, true);
    assert.equal(value.nextAction, 'observe_original_service'); assert.equal(value.serviceClosed, false);
    assert.equal(calls.length, 1); assert.equal(calls[0].command, 'close'); noSecrets(value);
  });
} else if (scenario === 'status-recovery') {
  await withSocket((req, socket) => {
    if (req.command === 'close') socket.destroy();
    else socket.end(frame(reply(req.command, 'CLOSED')));
  }, async (client, calls) => {
    const first = await client.close(requestId), observed = await client.status(requestId);
    assert.equal(first.error.mayHaveBeenAccepted, true); assert.equal(observed.closureReported, true);
    assert.equal(observed.command, 'service-status'); assert.equal(observed.serviceId, first.serviceId);
    assert.equal(observed.requestId, first.requestId); assert.equal(observed.kernelVerified, false);
    assert.deepEqual(calls.map(value => value.command), ['close', 'status']); noSecrets(observed);
  });
} else if (scenario === 'unknown') {
  await withSocket((req, socket) => socket.end(frame(reply(req.command, 'UNKNOWN'))), async (client, calls) => {
    const value = await client.status(requestId);
    assert.equal(value.outcome, 'unresolved'); assert.equal(value.closureReported, false);
    assert.equal(value.nextAction, 'retain_owner_and_operator_reconciliation');
    assert.equal(serviceControlExitCode(value), 3); assert.deepEqual(calls.map(value => value.command), ['status']);
  });
} else if (scenario === 'invalid-input') {
  await withSocket(() => { throw new Error('Unexpected request'); }, async (client, calls, options) => {
    for (const id of [null, '', '../path', 'A'.repeat(32), 123]) {
      const value = await client.start(id);
      assert.equal(value.error.code, 'invalid_service_request_id');
      assert.equal(value.error.mayHaveBeenAccepted, false); assert.equal(value.requestAttempted, false);
      assert.equal(serviceControlExitCode(value), 64);
    }
    for (const mutation of [{ socketPath: 'relative.sock' }, { socketPath: '/tmp/../tmp/a' },
      { serviceId: 'not-id' }, { owner: { ...owner, pid: true } }, { owner: { ...owner, startTicks: 0 } },
      { owner: { ...owner, token: secret } }, { requestTimeoutMs: 0 }, { requestTimeoutMs: 60001 }])
      assert.throws(() => new ServiceControlClient({ ...options, ...mutation }), HarnessError);
    const absent = await new ServiceControlClient({ ...options, socketPath: options.socketPath + '-missing' }).start(requestId);
    assert.equal(absent.error.code, 'service_connection_unavailable'); assert.equal(absent.requestAttempted, false);
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'socket-trust') {
  await withSocket(() => { throw new Error('Unexpected request'); }, async (client, calls, options) => {
    await chmod(options.socketPath, 0o666);
    const insecure = await client.close(requestId);
    assert.equal(insecure.error.code, 'untrusted_service_socket'); assert.equal(insecure.requestAttempted, false);
    await chmod(options.socketPath, 0o600);
    await symlink(options.socketPath, options.socketPath + '-link');
    const link = await new ServiceControlClient({ ...options, socketPath: options.socketPath + '-link' }).start(requestId);
    assert.equal(link.error.code, 'untrusted_service_socket'); assert.equal(link.requestAttempted, false);
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'abort-before') {
  await withSocket(() => { throw new Error('Unexpected request'); }, async (client, calls) => {
    const controller = new AbortController(); controller.abort();
    const value = await client.start(requestId, { signal: controller.signal });
    assert.equal(value.error.code, 'service_observation_interrupted'); assert.equal(value.requestAttempted, false);
    assert.equal(value.error.mayHaveBeenAccepted, false); assert.equal(calls.length, 0);
  });
} else if (scenario === 'abort-after') {
  const controller = new AbortController();
  await withSocket(() => controller.abort(), async (client, calls) => {
    const value = await client.close(requestId, { signal: controller.signal });
    assert.equal(value.error.code, 'service_observation_interrupted'); assert.equal(value.requestAttempted, true);
    assert.equal(value.error.mayHaveBeenAccepted, true); assert.equal(value.serviceClosed, false);
    assert.equal(calls.length, 1);
  });
} else if (scenario === 'sanitized-error') {
  const value = serviceControlError(new Error(secret), { command: 'close', requestId, serviceId });
  assert.equal(value.error.code, 'service_control_error'); noSecrets(value);
  const malformed = serviceControlError(new HarnessError(['injected', secret]));
  assert.equal(malformed.error.code, 'service_control_error'); noSecrets(malformed);
  await withSocket((req, socket, calls) => {
    const value = reply(req.command, 'DRAINING');
    value.error = calls.length === 1 ? 'service_busy' : owner.token; socket.end(frame(value));
  }, async (client, calls) => {
    const value = await client.close(requestId);
    assert.equal(value.outcome, 'error'); assert.equal(value.error.code, 'service_busy');
    assert.equal(value.error.mayHaveBeenAccepted, true); assert.equal(value.serviceClosed, false);
    assert.equal(serviceControlExitCode(value), 3); assert.equal(calls.length, 1); noSecrets(value);
    const leaked = await client.status(requestId);
    assert.equal(leaked.error.code, 'service_owner_error'); assert.equal(leaked.error.mayHaveBeenAccepted, false);
    assert.equal(calls.length, 2); noSecrets(leaked);
  });
} else if (['cli-start', 'cli-close', 'cli-status'].includes(scenario)) {
  const command = scenario === 'cli-start' ? 'start' : scenario === 'cli-close' ? 'close' : 'service-status';
  await withSocket((req, socket) => socket.end(frame(reply(req.command, command === 'start' ? 'READY' : 'CLOSED'))),
    async (_, calls, options) => {
      const result = await cli([command, '--request-id', requestId], options);
      assert.equal(result.code, 0, result.stderr); assert.equal(result.value.command, command);
      assert.equal(result.value.kernelVerified, false); assert.equal(result.stderr, '');
      assert.equal(calls.length, 1); assert.equal(calls[0].command, command === 'service-status' ? 'status' : command);
      assert.equal(result.value.serviceClosed, command !== 'start'); noSecrets(result.value);
    });
} else if (scenario === 'cli-config') {
  await withSocket(() => { throw new Error('Unexpected request'); }, async (_, calls, options) => {
    for (const [args, extra] of [[['start'], {}], [['close'], {}],
      [['service-status', '--request-id', requestId], { configure: false }],
      [['start', '--request-id', requestId], { patchEnv: { ALAZ_SERVICE_OWNER_PID: 'true' } }],
      [['close', '--request-id', requestId], { patchEnv: { ALAZ_SERVICE_OWNER_TOKEN: '' } }],
      [['close', '--request-id', requestId, '--request-timeout-ms', '0'], {}]]) {
      const result = await cli(args, options, extra);
      assert.equal(result.code, 64, result.stderr); assert.equal(result.value.error.mayHaveBeenAccepted, false);
      assert.equal(result.value.requestAttempted, false); noSecrets(result.value);
    }
    for (const command of ['start', 'close']) {
      const result = await cli([command], options, { configure: false });
      assert.equal(result.code, 64); assert.equal(result.value.outcome, 'unsupported');
      assert.equal(result.value.serviceStarted, false); assert.equal(result.value.serviceClosed, false);
    }
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'cli-interrupted') {
  let child;
  await withSocket(() => child.kill('SIGINT'), async (_, calls, options) => {
    const result = await cli(['close', '--request-id', requestId], options, { onSpawn: value => { child = value; } });
    assert.equal(result.code, 3, result.stderr); assert.equal(result.value.error.code, 'service_observation_interrupted');
    assert.equal(result.value.error.mayHaveBeenAccepted, true); assert.equal(result.value.serviceClosed, false);
    assert.equal(calls.length, 1); noSecrets(result.value);
  });
} else throw new Error('Unknown scenario');

console.log(JSON.stringify({ result: 'PASS', scenario, fixtureCalls, mutationCalls,
  installedSupervisor: false, nativeRuntime: false, realProviderCalls: 0 }));
