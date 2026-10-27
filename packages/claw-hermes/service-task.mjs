/** Bounded task HTTP exchange through the explicitly selected original supervisor.
 * The URL is a route anchor, never a host TCP destination. The child selects its
 * original native endpoint. This transport owns no task, retry, queue or store.
 */
import net from 'node:net';
import { randomBytes } from 'node:crypto';
import { lstat, realpath } from 'node:fs/promises';
import { dirname, posix } from 'node:path';
import { HarnessError } from './hermes-runs.mjs';

export const TASK_PREFIX = 'ALAZTASK/1 ';
export const TASK_CLIENT_PROTOCOL = 'alaz-service-task-client-v1';
export const MAX_TASK_REQUEST_FRAME_BYTES = 1_500_000;
export const MAX_TASK_RESPONSE_FRAME_BYTES = 5_700_000;
const MAX_REQUEST_BODY = 1_048_576;
const MAX_RESPONSE_BODY = 4_194_304;
const MAX_HEADERS = 8192;
const ID = /^[a-f0-9]{32}$/;
const CODE = /^[a-z][a-z0-9_]{0,95}$/;
const OWNER_KEYS = ['pid', 'startTicks', 'token'];
const REQUEST_HEADERS = new Set(['authorization', 'accept', 'content-type', 'idempotency-key',
  'x-alaz-execution-version', 'x-alaz-provider-broker-version', 'x-alaz-isolated-read-version']);
const VERSIONS = new Set(['x-alaz-execution-version', 'x-alaz-provider-broker-version', 'x-alaz-isolated-read-version']);
const REDIRECTS = new Set([301, 302, 303, 307, 308]);

function fail(code, details = {}) {
  throw new HarnessError(code, { mayHaveBeenAccepted: false, retryAllowed: false, ...details });
}
function dataObject(value, keys = null) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) return false;
  const names = Reflect.ownKeys(value);
  return names.every(key => typeof key === 'string'
      && Object.hasOwn(Object.getOwnPropertyDescriptor(value, key) ?? {}, 'value'))
    && (keys === null || names.length === keys.length && names.every(key => keys.includes(key)));
}
function validOwner(owner) {
  return dataObject(owner, OWNER_KEYS) && Number.isSafeInteger(owner.pid)
    && owner.pid > 0 && owner.pid <= 2147483647 && Number.isSafeInteger(owner.startTicks)
    && owner.startTicks > 0 && typeof owner.token === 'string' && ID.test(owner.token);
}
function bounded(value, minimum, maximum, code) {
  if (!Number.isInteger(value) || value < minimum || value > maximum) fail(code);
  return value;
}
function endpoint(value) {
  let url;
  try { url = new URL(value); } catch { fail('invalid_base_url'); }
  if (!['http:', 'https:'].includes(url.protocol) || !['127.0.0.1', '[::1]'].includes(url.hostname)
      || url.username || url.password || url.search || url.hash || url.pathname !== '/') fail('unsupported_endpoint');
  return url.origin;
}
function route(method, path) {
  if (method === 'GET') return path === '/alaz/host/v1/capabilities'
    || /^\/alaz\/host\/v1\/requests\/[a-f0-9]{32}$/.test(path)
    || /^\/v1\/runs\/run_[a-f0-9]{32}$/.test(path);
  if (method === 'POST') return ['/alaz/host/v1/intents', '/alaz/host/v1/dispatch'].includes(path)
    || /^\/v1\/runs\/run_[a-f0-9]{32}\/stop$/.test(path);
  return false;
}
function requestHeaders(value, method) {
  if (!dataObject(value)) fail('invalid_task_headers');
  const headers = {};
  let total = 0;
  for (const key of Object.keys(value)) {
    const name = key.toLowerCase(), item = value[key];
    if (!REQUEST_HEADERS.has(name) || Object.hasOwn(headers, name)
        || typeof item !== 'string' || !/^[\x20-\x7e]*$/.test(item)) fail('invalid_task_headers');
    total += Buffer.byteLength(name) + Buffer.byteLength(item) + 4;
    if (total > MAX_HEADERS) fail('invalid_task_headers');
    headers[name] = item;
  }
  if (!/^Bearer [\x21-\x7e]{1,4096}$/.test(headers.authorization ?? '')
      || headers.accept !== 'application/json'
      || (method === 'POST' ? headers['content-type'] !== 'application/json'
        : Object.hasOwn(headers, 'content-type'))) fail('invalid_task_headers');
  if (Object.hasOwn(headers, 'idempotency-key') && !/^[\x21-\x7e]{1,255}$/.test(headers['idempotency-key']))
    fail('invalid_task_headers');
  for (const name of VERSIONS) if (Object.hasOwn(headers, name) && headers[name] !== '1') fail('invalid_task_headers');
  return headers;
}
function decodeBase64(value, limit) {
  if (typeof value !== 'string' || value.length % 4 !== 0
      || value.length > Math.ceil(limit / 3) * 4 || /[^A-Za-z0-9+/=]/.test(value))
    fail('invalid_service_task_response');
  const body = Buffer.from(value, 'base64');
  if (body.length > limit || body.toString('base64') !== value) fail('invalid_service_task_response');
  return body;
}
function nativeResponse(value, maximum) {
  if (!dataObject(value, ['status', 'headers', 'bodyBase64']) || !Number.isInteger(value.status)
      || value.status < 200 || value.status > 599 || !dataObject(value.headers))
    fail('invalid_service_task_response');
  const body = decodeBase64(value.bodyBase64, maximum), headers = {};
  let total = 0;
  for (const [name, item] of Object.entries(value.headers)) {
    if (!['content-type', 'content-length'].includes(name) || typeof item !== 'string'
        || !/^[\x20-\x7e]*$/.test(item)) fail('invalid_service_task_response');
    total += name.length + item.length + 4;
    if (total > MAX_HEADERS) fail('invalid_service_task_response');
    if (name === 'content-type' && (item.length === 0 || item.length > 255)) fail('invalid_service_task_response');
    if (name === 'content-length' && (!/^(0|[1-9][0-9]{0,9})$/.test(item) || Number(item) !== body.length))
      fail('invalid_service_task_response');
    headers[name] = item;
  }
  if (REDIRECTS.has(value.status)) fail('service_task_redirect_refused');
  const emptyOnly = [204, 205, 304].includes(value.status);
  if (emptyOnly && body.length !== 0) fail('invalid_service_task_response');
  return new Response(emptyOnly ? null : body, { status: value.status, headers });
}
function decodeReply(bytes, expected, maximum) {
  if (bytes.length > MAX_TASK_RESPONSE_FRAME_BYTES || bytes.length <= TASK_PREFIX.length + 2
      || bytes.at(-1) !== 10 || bytes.subarray(0, -1).includes(10)
      || bytes.some(byte => byte > 127) || bytes.subarray(0, TASK_PREFIX.length).toString('ascii') !== TASK_PREFIX)
    fail('invalid_service_task_frame');
  const raw = bytes.subarray(TASK_PREFIX.length, -1).toString('ascii');
  let value;
  try { value = JSON.parse(raw); } catch { fail('invalid_service_task_frame'); }
  if (JSON.stringify(value) !== raw) fail('invalid_service_task_frame');
  if (!dataObject(value, ['protocol', 'requestId', 'serviceId', 'owner', 'response', 'error', 'retryAllowed'])
      || value.protocol !== TASK_CLIENT_PROTOCOL || value.requestId !== expected.requestId
      || value.serviceId !== expected.serviceId || !validOwner(value.owner)
      || !OWNER_KEYS.every(key => value.owner[key] === expected.owner[key]) || value.retryAllowed !== false
      || (value.response === null) === (value.error === null)) fail('invalid_service_task_response');
  if (value.error !== null) {
    if (typeof value.error !== 'string' || !CODE.test(value.error)) fail('invalid_service_task_response');
    // Server text is not a public diagnostic, even if it resembles a reason code.
    fail('service_task_rejected');
  }
  return nativeResponse(value.response, maximum);
}

async function checkSocket(path) {
  // Same private path trust rules as the separate lifecycle client. No adoption,
  // discovery, creation or replacement of another owner's endpoint.
  const [socket, parent, resolved] = await Promise.all([lstat(path), lstat(dirname(path)), realpath(path)]);
  const uid = process.getuid();
  if (!socket.isSocket() || !parent.isDirectory() || socket.isSymbolicLink() || parent.isSymbolicLink()
      || resolved !== path || ![0, uid].includes(socket.uid) || parent.uid !== socket.uid
      || (socket.mode & 0o077) !== 0 || (parent.mode & 0o022) !== 0) fail('untrusted_service_socket');
}
async function boundedSocketCheck(path, signal, timeout) {
  let timer, abort;
  try {
    await Promise.race([checkSocket(path), new Promise((resolve, reject) => {
      timer = setTimeout(() => reject(new HarnessError('service_task_timeout')), timeout);
      abort = () => reject(new HarnessError('service_task_observation_interrupted'));
      signal?.addEventListener('abort', abort, { once: true });
      if (signal?.aborted) abort();
    })]);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

export function createServiceTaskFetch({ socketPath, serviceId, owner, baseUrl,
    requestTimeoutMs = 5000, maxResponseBytes = 1_048_576 } = {}) {
  if (process.platform !== 'linux') fail('unsupported_service_platform');
  if (typeof socketPath !== 'string' || !posix.isAbsolute(socketPath) || posix.normalize(socketPath) !== socketPath
      || /[\0\r\n]/.test(socketPath) || Buffer.byteLength(socketPath) > 107) fail('invalid_service_socket');
  if (typeof serviceId !== 'string' || !ID.test(serviceId)) fail('invalid_service_id');
  if (!validOwner(owner)) fail('invalid_service_owner');
  const originalOwner = Object.freeze({ ...owner }), base = endpoint(baseUrl);
  const timeout = bounded(requestTimeoutMs, 10, 60000, 'invalid_request_timeout');
  const maximum = bounded(maxResponseBytes, 128, MAX_RESPONSE_BODY, 'invalid_response_limit');

  return async function serviceTaskFetch(url, init = {}) {
    let attempted = false, write = false;
    const deadline = performance.now() + timeout;
    try {
      if (!dataObject(init) || Object.keys(init).some(key => !['method', 'headers', 'body', 'signal', 'redirect'].includes(key))
          || typeof url !== 'string' || !url.startsWith(base + '/')
          || (init.redirect !== undefined && init.redirect !== 'error')) fail('invalid_task_request');
      const method = init.method ?? 'GET', path = url.slice(base.length), signal = init.signal;
      if (!route(method, path) || (signal !== undefined && !(signal instanceof AbortSignal))) fail('invalid_task_request');
      write = method === 'POST';
      if (signal?.aborted) fail('aborted_before_request');
      const headers = requestHeaders(init.headers, method);
      if (init.body !== undefined && typeof init.body !== 'string') fail('invalid_task_request');
      const body = Buffer.from(init.body ?? '', 'utf8');
      if (body.length > MAX_REQUEST_BODY || (!write && body.length !== 0)) fail('invalid_task_request');
      const http = { method, path, headers, bodyBase64: body.toString('base64'),
        timeoutMs: timeout, maxResponseBytes: maximum };
      const requestId = randomBytes(16).toString('hex');
      const request = { protocol: TASK_CLIENT_PROTOCOL, requestId, serviceId, expectedOwner: originalOwner, http };
      if (Buffer.byteLength(TASK_PREFIX + JSON.stringify(request) + '\n') > MAX_TASK_REQUEST_FRAME_BYTES)
        fail('invalid_task_request');
      try { await boundedSocketCheck(socketPath, signal, Math.max(1, deadline - performance.now())); }
      catch (error) {
        if (error instanceof HarnessError) throw error;
        fail('service_connection_unavailable');
      }
      if (signal?.aborted) fail('aborted_before_request');
      if (deadline - performance.now() < 10) fail('service_task_timeout');
      return await new Promise((resolve, reject) => {
        let socket, done = false, total = 0;
        const chunks = [];
        const finish = (error, response) => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          signal?.removeEventListener('abort', abort);
          socket?.destroy();
          if (error) {
            error.mayHaveBeenAccepted = write && attempted;
            error.retryAllowed = false;
            reject(error);
          } else resolve(response);
        };
        const failRequest = code => finish(new HarnessError(code));
        const abort = () => failRequest('service_task_observation_interrupted');
        const timer = setTimeout(() => failRequest('service_task_timeout'), Math.max(1, Math.ceil(deadline - performance.now())));
        signal?.addEventListener('abort', abort, { once: true });
        if (signal?.aborted) { abort(); return; }
        try { socket = net.createConnection({ path: socketPath, allowHalfOpen: true }); }
        catch { failRequest('service_task_transport_error'); return; }
        socket.once('connect', () => {
          if (done) return;
          const remaining = Math.floor(deadline - performance.now());
          if (remaining < 10) { failRequest('service_task_timeout'); return; }
          http.timeoutMs = Math.min(timeout, remaining);
          attempted = true;
          try { socket.end(TASK_PREFIX + JSON.stringify(request) + '\n'); }
          catch { failRequest('service_task_transport_error'); }
        });
        socket.on('data', chunk => {
          if (done) return;
          total += chunk.length;
          if (total > MAX_TASK_RESPONSE_FRAME_BYTES) { failRequest('service_task_response_too_large'); return; }
          chunks.push(chunk);
        });
        socket.once('end', () => {
          if (done) return;
          try { finish(null, decodeReply(Buffer.concat(chunks), { requestId, serviceId, owner: originalOwner }, maximum)); }
          catch (error) { finish(error); }
        });
        socket.once('error', () => failRequest('service_task_transport_error'));
        socket.once('close', () => { if (!done) failRequest('service_task_response_incomplete'); });
      });
    } catch (error) {
      if (!(error instanceof HarnessError)) fail('service_task_transport_error', { mayHaveBeenAccepted: write && attempted });
      error.mayHaveBeenAccepted = write && attempted;
      error.retryAllowed = false;
      throw error;
    }
  };
}
