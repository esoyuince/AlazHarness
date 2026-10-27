/** Real Node/Unix task wire fixtures. No installed supervisor, native runtime or model. */
import assert from 'node:assert/strict';
import net from 'node:net';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { chmod, mkdtemp, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServiceTaskFetch, TASK_PREFIX, TASK_CLIENT_PROTOCOL,
  MAX_TASK_RESPONSE_FRAME_BYTES } from '../../packages/claw-hermes/service-task.mjs';
import { LocalControlClient, controlExitCode } from '../../packages/claw-hermes/local-control.mjs';
import { HostGateClient } from '../../packages/claw-hermes/host-gate-client.mjs';
import { HermesRunsClient, HarnessError } from '../../packages/claw-hermes/hermes-runs.mjs';

const scenario = process.argv[2];
const serviceId = 'b'.repeat(32), owner = { pid: 1234, startTicks: 5678, token: 'c'.repeat(32) };
const requestId = 'a'.repeat(32), runId = 'run_' + 'd'.repeat(32);
const token = 'fixture-task-bearer', key = 'ah1-' + 'e'.repeat(32) + '-' + requestId;
const intent = { requestId, model: 'fixture-model', input: 'Read the allowed fixture.' };
const secret = 'PRIVATE_VALUE_MUST_NOT_APPEAR';
const script = fileURLToPath(new URL('../../scripts/alaz_local.mjs', import.meta.url));
const paths = { capabilities: '/alaz/host/v1/capabilities', intents: '/alaz/host/v1/intents',
  dispatch: '/alaz/host/v1/dispatch', request: '/alaz/host/v1/requests/' + requestId,
  run: '/v1/runs/' + runId, stop: '/v1/runs/' + runId + '/stop' };
const capabilities = { hostGateVersion: 1, dispatchPath: paths.dispatch, nativeStoreOwner: true,
  dispatchAtMostOnce: true, automaticRetry: false, scope: 'default_profile_new_run',
  executionBoundaryVersion: 1, providerBrokerVersion: 1, providerBrokerBackend: 'linux_unix_credential_broker' };
const errorCode = code => error => error instanceof HarnessError && error.code === code;
const headers = method => ({ Authorization: 'Bearer ' + token, Accept: 'application/json',
  ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}) });
const init = (method = 'GET', body) => ({ method, redirect: 'error', headers: headers(method),
  ...(body === undefined ? {} : { body }) });
function response(value, status = 200) {
  const raw = Buffer.from(JSON.stringify(value));
  return { status, headers: { 'content-type': 'application/json', 'content-length': String(raw.length) },
    bodyBase64: raw.toString('base64') };
}
function reply(request, value = response({ ok: true })) {
  return { protocol: TASK_CLIENT_PROTOCOL, requestId: request.requestId, serviceId, owner: { ...owner },
    response: value, error: null, retryAllowed: false };
}
const frame = value => TASK_PREFIX + JSON.stringify(value) + '\n';
function sanitized(value, path) {
  const raw = JSON.stringify(value);
  for (const item of [token, owner.token, secret, path]) if (item) assert.ok(!raw.includes(item));
}

let fixtureCalls = 0, hostTcpCalls = 0;
async function withSocket(handler, run) {
  const dir = await mkdtemp(join(tmpdir(), 'alaz-task-'));
  await chmod(dir, 0o700);
  const socketPath = join(dir, 'control.sock'), calls = [], errors = [], connections = new Set();
  const trap = http.createServer((req, res) => { hostTcpCalls++; res.writeHead(503); res.end(); });
  await new Promise(resolve => trap.listen(0, '127.0.0.1', resolve));
  const baseUrl = 'http://127.0.0.1:' + trap.address().port;
  const server = net.createServer({ allowHalfOpen: true }, socket => {
    connections.add(socket);
    socket.once('close', () => connections.delete(socket));
    socket.on('error', () => {});
    const chunks = [];
    socket.on('data', chunk => chunks.push(chunk));
    socket.once('end', () => {
      try {
        const raw = Buffer.concat(chunks).toString('ascii');
        assert.ok(raw.startsWith(TASK_PREFIX)); assert.ok(raw.endsWith('\n'));
        assert.equal(raw.split('\n').length, 2);
        const request = JSON.parse(raw.slice(TASK_PREFIX.length, -1));
        assert.equal(frame(request), raw);
        assert.deepEqual(Object.keys(request).sort(), ['expectedOwner', 'http', 'protocol', 'requestId', 'serviceId']);
        assert.equal(request.protocol, TASK_CLIENT_PROTOCOL); assert.equal(request.serviceId, serviceId);
        assert.match(request.requestId, /^[a-f0-9]{32}$/);
        assert.deepEqual(Object.keys(request.http).sort(), ['bodyBase64', 'headers', 'maxResponseBytes', 'method', 'path', 'timeoutMs']);
        assert.ok(request.http.timeoutMs >= 10 && request.http.timeoutMs <= 60000);
        assert.ok(request.http.maxResponseBytes >= 128 && request.http.maxResponseBytes <= 4194304);
        assert.equal(request.http.headers.authorization, 'Bearer ' + token);
        assert.equal(request.http.headers.accept, 'application/json');
        assert.equal(Buffer.from(request.http.bodyBase64, 'base64').toString('base64'), request.http.bodyBase64);
        assert.ok(!Object.hasOwn(request.http, 'endpoint')); assert.ok(!Object.hasOwn(request.http, 'url'));
        fixtureCalls++; calls.push(request);
        if (!['pid', 'startTicks', 'token'].every(field => request.expectedOwner[field] === owner[field])) {
          const value = reply(request); value.response = null; value.error = 'service_owner_precondition_failed';
          socket.end(frame(value)); return;
        }
        Promise.resolve(handler(request, socket, calls)).catch(error => { errors.push(error); socket.destroy(); });
      } catch (error) { errors.push(error); socket.destroy(); }
    });
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(socketPath, resolve); });
  await chmod(socketPath, 0o600);
  const options = { socketPath, serviceId, owner, baseUrl, token, requestTimeoutMs: 3000,
    taskTransport: 'supervised-service' };
  const originalFetch = globalThis.fetch;
  globalThis.fetch = () => { throw new Error('Host TCP/global fetch fallback is forbidden'); };
  try {
    await run(options, calls);
    assert.deepEqual(errors, [], errors.map(error => error.stack).join('\n'));
    assert.equal(hostTcpCalls, 0);
  } finally {
    globalThis.fetch = originalFetch;
    for (const socket of connections) socket.destroy();
    await new Promise(resolve => server.close(resolve));
    trap.closeAllConnections(); await new Promise(resolve => trap.close(resolve));
    await rm(dir, { recursive: true, force: true });
  }
}

function nativeFixture({ lostDispatch = false, lostStop = false, rejectDispatch = false } = {}) {
  const state = { consumed: false, dispatches: 0, stops: 0, forwarded: 0 };
  const handler = (request, socket) => {
    const wire = request.http; state.forwarded++;
    let value, status = 200;
    if (wire.path === paths.capabilities) value = capabilities;
    else if (wire.path === paths.intents) {
      const body = JSON.parse(Buffer.from(wire.bodyBase64, 'base64').toString('utf8'));
      assert.equal(body.requestId, requestId); assert.equal(body.body.model, intent.model);
      value = { hostGateVersion: 1, requestId, idempotencyKey: key, dispatchState: state.consumed ? 'consumed' : 'issued',
        expiresAtMs: Date.now() + 30000, replayed: state.consumed, retryAllowed: false }; status = 201;
    } else if (wire.path === paths.dispatch) {
      assert.equal(wire.headers['idempotency-key'], key);
      assert.equal(wire.headers['x-alaz-execution-version'], '1');
      assert.equal(wire.headers['x-alaz-provider-broker-version'], '1');
      state.consumed = true; state.dispatches++;
      if (lostDispatch) { socket.destroy(); return; }
      if (rejectDispatch) { value = { hostGateVersion: 1, error: { code: 'dispatch_limit_reached' } }; status = 409; }
      else { value = { run_id: runId, status: 'started', replayed: false }; status = 202; }
    } else if (wire.path === paths.request) {
      assert.equal(wire.headers['x-alaz-provider-broker-version'], undefined);
      value = { hostGateVersion: 1, requestObservationVersion: 1, requestId, classification: 'native_run_located',
        dispatchState: 'consumed', runId, snapshotOnly: true, writesPerformed: false, canonicalVerified: false,
        retryAllowed: false, repairAllowed: false, requiresOperator: false, nextAction: 'observe_existing_run' };
    } else if (wire.path === paths.stop) {
      state.stops++;
      assert.deepEqual(JSON.parse(Buffer.from(wire.bodyBase64, 'base64')), {});
      if (lostStop) { socket.destroy(); return; }
      value = { run_id: runId, status: 'stopping' };
    } else if (wire.path === paths.run) {
      value = { run_id: runId, status: state.stops ? 'cancelled' : 'completed', admission_id: 'f'.repeat(32),
        session_id: 'api-service-task-fixture', execution_generation: 1, output: 'scoped result',
        usage: { input_tokens: 2, output_tokens: 3, total_tokens: 5 } };
    } else throw new Error('Unexpected route');
    socket.end(frame(reply(request, response(value, status))));
  };
  return { state, handler };
}
async function cli(options, args, { stdin = '', envPatch = {} } = {}) {
  const env = Object.fromEntries(Object.entries(process.env).filter(([name]) =>
    ['PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'].includes(name.toUpperCase())));
  Object.assign(env, { ALAZ_BASE_URL: options.baseUrl, ALAZ_API_TOKEN: token,
    ALAZ_TASK_TRANSPORT: 'supervised-service', ALAZ_SERVICE_SOCKET: options.socketPath,
    ALAZ_SERVICE_ID: serviceId, ALAZ_SERVICE_OWNER_PID: String(owner.pid),
    ALAZ_SERVICE_OWNER_START_TICKS: String(owner.startTicks), ALAZ_SERVICE_OWNER_TOKEN: owner.token }, envPatch);
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [script, ...args], { env, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error('CLI fixture deadline')); }, 8000);
    child.stdout.on('data', chunk => { stdout += chunk; }); child.stderr.on('data', chunk => { stderr += chunk; });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', code => {
      clearTimeout(timer);
      try { resolve({ code, value: JSON.parse(stdout), stdout, stderr }); }
      catch (error) { reject(error); }
    });
    child.stdin.on('error', () => {}); child.stdin.end(stdin);
  });
}

if (scenario === 'fetch-seam') {
  const opts = { baseUrl: 'http://127.0.0.1:9876', token };
  const original = globalThis.fetch, seen = [];
  try {
    // The established default still resolves global fetch at request time.
    const host = new HostGateClient(opts), runs = new HermesRunsClient(opts);
    globalThis.fetch = async (url, init) => {
      seen.push({ url, init });
      return new Response(JSON.stringify(url.endsWith('/capabilities') ? capabilities
        : { run_id: runId, status: 'running' }), { headers: { 'content-type': 'application/json' } });
    };
    await host.capabilities(); await runs.status(runId); assert.equal(seen.length, 2);
    let custom = 0;
    const fetchImpl = async (...args) => { custom++; return globalThis.fetch(...args); };
    const alternate = new HostGateClient({ ...opts, fetchImpl });
    await alternate.capabilities(); await alternate.status(runId); assert.equal(custom, 2);
    for (const value of [null, false, {}, 'fetch']) {
      assert.throws(() => new HostGateClient({ ...opts, fetchImpl: value }), errorCode('invalid_task_transport'));
      assert.throws(() => new HermesRunsClient({ ...opts, fetchImpl: value }), errorCode('invalid_task_transport'));
    }
  } finally { globalThis.fetch = original; }
} else if (scenario === 'workflow') {
  const { handler, state } = nativeFixture();
  await withSocket(handler, async options => {
    const client = new LocalControlClient(options);
    const task = await client.task(intent); assert.equal(task.outcome, 'accepted');
    assert.equal((await client.request(requestId)).outcome, 'located');
    assert.equal((await client.status(runId)).outcome, 'observed');
    assert.equal((await client.watch(runId)).outcome, 'terminal_reported');
    const result = await client.result(runId); assert.equal(result.output, 'scoped result');
    assert.equal(result.goalAchievementIndependentlyVerified, false);
    const usage = await client.usage(runId); assert.equal(usage.usage.totalTokens, 5); assert.equal(usage.usage.costMicrousd, null);
    const cancel = await client.cancel(runId); assert.equal(cancel.cancellation.terminalReported, true);
    assert.equal(cancel.cancellation.physicalWorkerTerminalVerified, false);
    assert.equal(state.dispatches, 1); assert.equal(state.stops, 1);
    sanitized(task, options.socketPath); sanitized(cancel, options.socketPath);
  });
} else if (scenario === 'lost-dispatch') {
  const { handler, state } = nativeFixture({ lostDispatch: true });
  await withSocket(handler, async options => {
    const task = await new LocalControlClient(options).task(intent);
    assert.equal(task.outcome, 'error'); assert.equal(task.error.mayHaveBeenAccepted, true);
    assert.equal(task.nextAction, 'observe_original_request'); assert.equal(controlExitCode(task), 3);
    const observed = await new LocalControlClient(options).request(requestId); assert.equal(observed.outcome, 'located');
    const repeated = await new LocalControlClient(options).task(intent);
    assert.equal(repeated.error.code, 'host_dispatch_already_attempted'); assert.equal(state.dispatches, 1);
    sanitized(task, options.socketPath);
  });
} else if (scenario === 'lost-stop') {
  const { handler, state } = nativeFixture({ lostStop: true });
  await withSocket(handler, async options => {
    const result = await new LocalControlClient(options).cancel(runId);
    assert.equal(result.cancellation.requestAcknowledged, false);
    assert.equal(result.cancellation.requestMayHaveBeenAccepted, true);
    assert.equal(result.cancellation.terminalReported, true); assert.equal(result.run.status, 'cancelled');
    assert.equal(state.stops, 1); assert.equal(controlExitCode(result), 0);
  });
} else if (scenario === 'native-rejection') {
  const { handler, state } = nativeFixture({ rejectDispatch: true });
  await withSocket(handler, async options => {
    const result = await new LocalControlClient(options).task(intent);
    assert.equal(result.error.code, 'host_http_409'); assert.equal(result.error.httpStatus, 409);
    assert.equal(result.error.hostCode, 'dispatch_limit_reached'); assert.equal(result.retryAllowed, false);
    assert.equal(state.dispatches, 1);
  });
} else if (scenario === 'route-header-guards') {
  await withSocket(() => { throw new Error('Invalid request forwarded'); }, async (options, calls) => {
    const fetch = createServiceTaskFetch(options), get = init();
    for (const [url, request] of [
      [options.baseUrl + '/v1/runs', init('POST', '{}')],
      [options.baseUrl + '/provider', get], [options.baseUrl + paths.run + '?x=1', get],
      [options.baseUrl + paths.run + '#x', get], [options.baseUrl + '/v1/runs/%72un_' + 'd'.repeat(32), get],
      ['http://localhost:9876' + paths.run, get], ['https://example.org' + paths.run, get],
      [options.baseUrl + '/x/../' + paths.run.slice(1), get], [options.baseUrl + paths.run, { ...get, method: 'DELETE' }],
      [options.baseUrl + paths.run, { ...get, redirect: 'follow' }], [options.baseUrl + paths.run, { ...get, body: '{}' }],
      [options.baseUrl + paths.run, { ...get, headers: { ...get.headers, Cookie: secret } }],
      [options.baseUrl + paths.run, { ...get, headers: { ...get.headers, authorization: 'Bearer ' + token } }],
      [options.baseUrl + paths.run, { ...get, headers: { ...get.headers, Authorization: 'Bearer bad token' } }],
      [options.baseUrl + paths.run, { ...get, headers: { ...get.headers, 'X-Alaz-Execution-Version': '2' } }],
      [options.baseUrl + paths.stop, { ...init('POST', '{}'), headers: headers('GET') }],
    ]) await assert.rejects(fetch(url, request), error => error instanceof HarnessError && error.mayHaveBeenAccepted === false);
    const accessor = { ...get }; Object.defineProperty(accessor, 'body', { get() { throw new Error('Getter ran'); } });
    await assert.rejects(fetch(options.baseUrl + paths.run, accessor), errorCode('invalid_task_request'));
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'input-bounds') {
  const { handler, state } = nativeFixture();
  await withSocket(handler, async (options, calls) => {
    const client = new LocalControlClient(options);
    const result = await client.task({ ...intent, input: '\u0001'.repeat(65536) });
    assert.equal(result.outcome, 'accepted'); assert.equal(state.dispatches, 1);
    const body = Buffer.from(calls.find(row => row.http.path === paths.dispatch).http.bodyBase64, 'base64');
    assert.ok(body.length > 393216); assert.equal(JSON.parse(body).input.length, 65536);
    const count = calls.length;
    await assert.rejects(createServiceTaskFetch(options)(options.baseUrl + paths.intents,
      init('POST', 'x'.repeat(1048577))), errorCode('invalid_task_request'));
    assert.equal(calls.length, count);
  });
} else if (scenario === 'response-bounds') {
  const limit = 4194304;
  const body = Buffer.from('{"data":"' + 'x'.repeat(limit - 11) + '"}'); assert.equal(body.length, limit);
  await withSocket((request, socket, calls) => {
    if (calls.length === 3) { socket.end('x'.repeat(MAX_TASK_RESPONSE_FRAME_BYTES + 1)); return; }
    socket.end(frame(reply(request, { status: 200, headers: { 'content-type': 'application/json', 'content-length': String(body.length) },
      bodyBase64: body.toString('base64') })));
  }, async options => {
    const large = createServiceTaskFetch({ ...options, maxResponseBytes: limit, requestTimeoutMs: 10000 });
    assert.equal((await (await large(options.baseUrl + paths.run, init())).arrayBuffer()).byteLength, limit);
    await assert.rejects(createServiceTaskFetch({ ...options, maxResponseBytes: 128 })(options.baseUrl + paths.run, init()),
      errorCode('invalid_service_task_response'));
    await assert.rejects(large(options.baseUrl + paths.run, init()), errorCode('service_task_response_too_large'));
  });
} else if (scenario === 'response-schema') {
  const mutations = [
    value => { value.requestId = 'f'.repeat(32); }, value => { value.serviceId = 'f'.repeat(32); },
    value => { value.owner.pid++; }, value => { value.owner.startTicks++; }, value => { value.owner.token = 'f'.repeat(32); },
    value => { value.protocol += '-other'; }, value => { value.retryAllowed = true; },
    value => { value.extra = true; }, value => { value.error = 'both_response_and_error'; },
    value => { value.response = null; }, value => { value.response.extra = true; },
    value => { value.response.status = 100; }, value => { value.response.status = true; },
    value => { value.response.bodyBase64 = 'e30'; }, value => { value.response.bodyBase64 = 'e31='; },
    value => { value.response.headers['content-length'] = '999'; },
    value => { value.response.headers['content-length'] = '011'; },
    value => { value.response.headers['content-type'] = 'x'.repeat(256); },
    value => { value.response.headers['set-cookie'] = secret; },
  ];
  await withSocket((request, socket, calls) => { const value = reply(request); mutations[calls.length - 1](value); socket.end(frame(value)); },
    async (options, calls) => {
      const fetch = createServiceTaskFetch(options);
      for (const mutate of mutations) await assert.rejects(fetch(options.baseUrl + paths.run, init()),
        error => error instanceof HarnessError && error.mayHaveBeenAccepted === false);
      assert.equal(calls.length, mutations.length);
    });
} else if (scenario === 'framing') {
  const mutations = [raw => raw.slice(TASK_PREFIX.length), raw => raw.trimEnd(), raw => raw + '{}\n',
    raw => raw.replace('"retryAllowed":false', '"retryAllowed":true,"retryAllowed":false'),
    raw => raw.replace('1234', '1234.0'), raw => raw.replace('{', '{ '),
    raw => raw.replace('"owner"', '"\\u006fwner"'), () => Buffer.from([255, 10])];
  await withSocket((request, socket, calls) => socket.end(mutations[calls.length - 1](frame(reply(request)))),
    async (options, calls) => {
      const fetch = createServiceTaskFetch(options);
      for (const mutate of mutations) await assert.rejects(fetch(options.baseUrl + paths.stop, init('POST', '{}')),
        error => error instanceof HarnessError && error.mayHaveBeenAccepted === true && error.retryAllowed === false);
      assert.equal(calls.length, mutations.length);
    });
} else if (scenario === 'eof-required') {
  let serverSocket;
  await withSocket((request, socket) => { serverSocket = socket; socket.write(frame(reply(request))); }, async options => {
    const originalConnect = net.createConnection;
    let clientSocket, settled = false, received;
    const data = new Promise(resolve => { received = resolve; });
    net.createConnection = (...args) => {
      const socket = Reflect.apply(originalConnect, net, args); clientSocket = socket;
      const chunks = [];
      socket.on('data', chunk => { chunks.push(chunk); if (chunk.includes(10)) received(Buffer.concat(chunks)); });
      return socket;
    };
    try {
      const pending = createServiceTaskFetch({ ...options, requestTimeoutMs: 10000 })(options.baseUrl + paths.run, init())
        .then(value => { settled = true; return value; });
      assert.ok((await data).toString().startsWith(TASK_PREFIX));
      await new Promise(resolve => setImmediate(resolve));
      assert.equal(settled, false); assert.equal(clientSocket.readableEnded, false);
      serverSocket.end(); assert.equal((await pending).status, 200);
    } finally { net.createConnection = originalConnect; }
  });
} else if (scenario === 'stale-owner') {
  let effects = 0;
  await withSocket((request, socket) => { effects++; socket.end(frame(reply(request))); }, async (options, calls) => {
    for (const change of [{ pid: owner.pid + 1 }, { startTicks: owner.startTicks + 1 }, { token: 'f'.repeat(32) }]) {
      const fetch = createServiceTaskFetch({ ...options, owner: { ...owner, ...change } });
      await assert.rejects(fetch(options.baseUrl + paths.stop, init('POST', '{}')), errorCode('invalid_service_task_response'));
    }
    assert.equal(effects, 0); assert.equal(calls.length, 3);
  });
} else if (scenario === 'socket-trust') {
  await withSocket(() => { throw new Error('Untrusted request forwarded'); }, async (options, calls) => {
    const fetch = createServiceTaskFetch(options);
    await chmod(options.socketPath, 0o666);
    await assert.rejects(fetch(options.baseUrl + paths.stop, init('POST', '{}')), errorCode('untrusted_service_socket'));
    await chmod(options.socketPath, 0o600);
    await symlink(options.socketPath, options.socketPath + '-link');
    const linked = createServiceTaskFetch({ ...options, socketPath: options.socketPath + '-link' });
    await assert.rejects(linked(options.baseUrl + paths.run, init()), errorCode('untrusted_service_socket'));
    const absent = createServiceTaskFetch({ ...options, socketPath: options.socketPath + '-missing' });
    await assert.rejects(absent(options.baseUrl + paths.run, init()), error => error.code === 'service_connection_unavailable'
      && error.mayHaveBeenAccepted === false);
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'abort-before') {
  await withSocket(() => { throw new Error('Aborted request forwarded'); }, async (options, calls) => {
    const controller = new AbortController(); controller.abort();
    await assert.rejects(createServiceTaskFetch(options)(options.baseUrl + paths.stop,
      { ...init('POST', '{}'), signal: controller.signal }), error => error.code === 'aborted_before_request'
        && error.mayHaveBeenAccepted === false);
    assert.equal(calls.length, 0);
  });
} else if (scenario === 'abort-after') {
  const controller = new AbortController();
  await withSocket(() => controller.abort(), async (options, calls) => {
    await assert.rejects(createServiceTaskFetch(options)(options.baseUrl + paths.stop,
      { ...init('POST', '{}'), signal: controller.signal }), error => error.code === 'service_task_observation_interrupted'
        && error.mayHaveBeenAccepted === true && error.retryAllowed === false);
    assert.equal(calls.length, 1);
  });
} else if (scenario === 'timeout') {
  await withSocket(() => {}, async (options, calls) => {
    await assert.rejects(createServiceTaskFetch({ ...options, requestTimeoutMs: 250 })(options.baseUrl + paths.stop, init('POST', '{}')),
      error => error.code === 'service_task_timeout' && error.mayHaveBeenAccepted === true);
    assert.equal(calls.length, 1);
  });
} else if (scenario === 'sanitized-errors') {
  await withSocket((request, socket, calls) => {
    const value = reply(request); value.response = null; value.error = calls.length === 1 ? owner.token : 'service_task_busy';
    socket.end(frame(value));
  }, async options => {
    const client = new LocalControlClient(options);
    for (let i = 0; i < 2; i++) {
      const result = await client.status(runId); assert.equal(result.error.code, 'service_task_rejected');
      assert.equal(result.error.mayHaveBeenAccepted, false); sanitized(result, options.socketPath);
    }
  });
} else if (scenario === 'redirect') {
  await withSocket((request, socket) => socket.end(frame(reply(request, response({}, 302)))), async (options, calls) => {
    const result = await new LocalControlClient(options).request(requestId);
    assert.equal(result.error.code, 'service_task_redirect_refused'); assert.equal(result.retryAllowed, false);
    assert.equal(calls.length, 1);
  });
} else if (scenario === 'cli-task' || scenario === 'cli-lost-dispatch' || scenario === 'cli-cancel') {
  const { handler, state } = nativeFixture({ lostDispatch: scenario === 'cli-lost-dispatch', lostStop: scenario === 'cli-cancel' });
  await withSocket(handler, async options => {
    const result = scenario === 'cli-cancel' ? await cli(options, ['cancel', '--run-id', runId])
      : await cli(options, ['task', '--request-id', requestId, '--model', intent.model, '--input', '-'], { stdin: intent.input });
    assert.equal(result.stderr, ''); sanitized(result.value, options.socketPath);
    if (scenario === 'cli-lost-dispatch') {
      assert.equal(result.code, 3); assert.equal(result.value.error.mayHaveBeenAccepted, true);
      const observed = await cli(options, ['request', '--request-id', requestId]);
      assert.equal(observed.code, 0); assert.equal(observed.value.outcome, 'located'); assert.equal(state.dispatches, 1);
    } else {
      assert.equal(result.code, 0);
      if (scenario === 'cli-cancel') { assert.equal(result.value.cancellation.terminalReported, true); assert.equal(state.stops, 1); }
      else { assert.equal(result.value.outcome, 'accepted'); assert.equal(state.dispatches, 1); }
    }
  });
} else if (scenario === 'configuration') {
  await withSocket(() => { throw new Error('Invalid configuration forwarded'); }, async (options, calls) => {
    for (const change of [{ socketPath: 'relative' }, { socketPath: '/tmp/../tmp/a' }, { socketPath: '/x'.repeat(100) },
      { serviceId: 'wrong' }, { owner: { ...owner, pid: true } }, { owner: { ...owner, startTicks: 0 } },
      { owner: { ...owner, extra: true } }, { requestTimeoutMs: 0 }, { maxResponseBytes: 127 },
      { maxResponseBytes: 4194305 }, { baseUrl: 'https://example.org/' }])
      assert.throws(() => createServiceTaskFetch({ ...options, ...change }), HarnessError);
    assert.throws(() => new LocalControlClient({ ...options, fetchImpl: async () => new Response('{}') }),
      errorCode('invalid_task_transport'));
    for (const envPatch of [{ ALAZ_TASK_TRANSPORT: 'unknown' }, { ALAZ_SERVICE_OWNER_TOKEN: '' },
      { ALAZ_SERVICE_ID: 'wrong' }, { ALAZ_SERVICE_OWNER_PID: 'true' }, { ALAZ_SERVICE_SOCKET: '' }]) {
      const result = await cli(options, ['status', '--run-id', runId], { envPatch });
      assert.equal(result.code, 64); assert.equal(result.value.error.mayHaveBeenAccepted, false);
      sanitized(result.value, options.socketPath);
    }
    assert.equal(calls.length, 0);
  });
} else throw new Error('Unknown fixture scenario');

console.log(JSON.stringify({ result: 'PASS', scenario, fixtureCalls, hostTcpCalls,
  installedSupervisor: false, nativeRuntime: false, realProviderCalls: 0 }));
