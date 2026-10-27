/** Bounded one-request control of an explicitly selected, original supervisor.
 * This private Unix channel is separate from the native task HTTP listener.
 * No process discovery, launcher, mutation retry, repair or kernel proof.
 * Every request carries expectedOwner as a pre-effect condition. A compatible
 * server MUST compare all of it with its original owner before any lifecycle
 * effect or status dispatch; reply identity checks cannot replace that gate.
 */
import net from 'node:net';
import { lstat, realpath } from 'node:fs/promises';
import { dirname, posix } from 'node:path';
import { HarnessError } from './hermes-runs.mjs';

export const CONTROL_PROTOCOL = 'alaz-supervisor-control-v1';
export const MAX_CONTROL_FRAME_BYTES = 65536;
const ID = /^[a-f0-9]{32}$/;
const CODE = /^[a-z][a-z0-9_]{0,95}$/;
const STATES = new Set(['NEW', 'STARTING', 'READY', 'DRAINING', 'UNKNOWN', 'CLOSED']);
const COMMANDS = new Set(['start', 'close', 'status']);
const OWNER_FIELDS = ['pid', 'startTicks', 'token'];
const COMPLETION_FIELDS = ['transportRetired', 'runtimeRetired', 'apiSessionsRetired',
  'consumerDetached', 'defaultExecutorJoined', 'physicalStoresClosed',
  'profileLeaseReleased', 'childExited', 'volumeUnmounted', 'imageLeaseReleased',
  'fenceRemovedAfterCleanup'];
const FLAGS = COMPLETION_FIELDS.filter(key => key !== 'physicalStoresClosed');
const REPLY_FIELDS = ['protocol', 'command', 'requestId', 'serviceId', 'owner',
  'state', 'endpoint', 'endpointScope', 'completion', 'retryAllowed', 'error'];
const INPUT_ERRORS = new Set(['invalid_service_socket', 'invalid_service_id',
  'invalid_service_owner', 'invalid_service_request_id', 'invalid_service_command',
  'invalid_service_timeout', 'unsupported_service_platform', 'missing_service_connection',
  'invalid_cli_arguments', 'invalid_cli_command', 'missing_cli_argument',
  'invalid_cli_number', 'invalid_request_id']);

function fail(code, details = {}) { throw new HarnessError(code, { mayHaveBeenAccepted: false, ...details }); }
function exactObject(value, keys) {
  if (!value || typeof value !== 'object' || Array.isArray(value)
      || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) return false;
  const own = Reflect.ownKeys(value);
  return own.length === keys.length && keys.every(key =>
    Object.hasOwn(Object.getOwnPropertyDescriptor(value, key) ?? {}, 'value'))
    && own.every(key => keys.includes(key));
}
function validOwner(value) {
  return exactObject(value, OWNER_FIELDS) && Number.isSafeInteger(value.pid)
    && value.pid > 0 && value.pid <= 2147483647
    && Number.isSafeInteger(value.startTicks) && value.startTicks > 0
    && typeof value.token === 'string' && ID.test(value.token);
}
function validEndpoint(value) {
  if (typeof value !== 'string') return false;
  const match = /^http:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})$/.exec(value);
  return match !== null && Number(match[1]) <= 65535;
}
function validCompletion(value, state) {
  if (!exactObject(value, COMPLETION_FIELDS)
      || !FLAGS.every(key => typeof value[key] === 'boolean')
      || !Number.isSafeInteger(value.physicalStoresClosed)
      || value.physicalStoresClosed < 0 || value.physicalStoresClosed > 3) return false;
  if (['NEW', 'STARTING', 'READY'].includes(state)
      && (FLAGS.some(key => value[key]) || value.physicalStoresClosed !== 0)) return false;
  if (state === 'CLOSED'
      && (!FLAGS.every(key => value[key]) || value.physicalStoresClosed !== 3)) return false;
  if (value.runtimeRetired && !value.transportRetired) return false;
  if (value.apiSessionsRetired && !value.runtimeRetired) return false;
  if (value.consumerDetached && !value.apiSessionsRetired) return false;
  if (value.defaultExecutorJoined && !value.consumerDetached) return false;
  if (value.physicalStoresClosed > 0 && !value.defaultExecutorJoined) return false;
  if (value.profileLeaseReleased && value.physicalStoresClosed !== 3) return false;
  if (value.childExited && !value.profileLeaseReleased) return false;
  if (value.volumeUnmounted && !value.childExited) return false;
  if (value.fenceRemovedAfterCleanup && !value.volumeUnmounted) return false;
  if (value.imageLeaseReleased && !value.fenceRemovedAfterCleanup) return false;
  return true;
}

/** Check an owner report, never infer independent process or kernel verification. */
export function validateServiceReply(value, { command, requestId, serviceId, owner } = {}) {
  if (!COMMANDS.has(command)) fail('invalid_service_command');
  if (typeof requestId !== 'string' || !ID.test(requestId)) fail('invalid_service_request_id');
  if (typeof serviceId !== 'string' || !ID.test(serviceId)) fail('invalid_service_id');
  if (!validOwner(owner)) fail('invalid_service_owner');
  if (!exactObject(value, REPLY_FIELDS) || value.protocol !== CONTROL_PROTOCOL
      || value.command !== command || value.requestId !== requestId || value.serviceId !== serviceId
      || !validOwner(value.owner) || !OWNER_FIELDS.every(key => value.owner[key] === owner[key])
      || !STATES.has(value.state) || value.retryAllowed !== false
      || !(value.error === null || (typeof value.error === 'string' && CODE.test(value.error)))
      || !validCompletion(value.completion, value.state)) fail('invalid_service_response');
  if (value.endpoint === null ? value.endpointScope !== null
      : !validEndpoint(value.endpoint) || value.endpointScope !== 'private-service-loopback')
    fail('invalid_service_response');
  if (value.state === 'READY' && value.endpoint === null) fail('invalid_service_response');
  if (['NEW', 'CLOSED'].includes(value.state) && value.endpoint !== null) fail('invalid_service_response');
  // Return only exact checked fields in a detached snapshot.
  return JSON.parse(JSON.stringify(value));
}

function decodeReply(bytes, expected) {
  if (bytes.length < 3 || bytes.length > MAX_CONTROL_FRAME_BYTES
      || bytes.at(-1) !== 10 || bytes.subarray(0, -1).includes(10)
      || bytes.some(byte => byte > 127)) fail('invalid_service_response_frame');
  const raw = bytes.subarray(0, -1).toString('ascii');
  let value;
  try { value = JSON.parse(raw); } catch { fail('invalid_service_response_frame'); }
  // Compact JSON is the wire contract. This also rejects duplicate object keys,
  // noncanonical numeric forms/escapes and an unvalidated trailing frame.
  if (JSON.stringify(value) !== raw) fail('invalid_service_response_frame');
  return validateServiceReply(value, expected);
}

function outputCommand(command) { return command === 'status' ? 'service-status' : command; }
function envelope(command, outcome, fields = {}) {
  return { localControlVersion: 1, serviceControlVersion: 1,
    command: outputCommand(command), outcome, retryAllowed: false, kernelVerified: false, ...fields };
}
/** No raw exception/server text, socket path, API credential or owner token. */
export function serviceControlError(error, { command = null, requestId = null, serviceId = null,
    requestAttempted = false } = {}) {
  const code = error instanceof HarnessError && typeof error.code === 'string' && CODE.test(error.code)
    ? error.code : 'service_control_error';
  return envelope(command, 'error', {
    ...(typeof requestId === 'string' && ID.test(requestId) ? { requestId } : {}),
    ...(typeof serviceId === 'string' && ID.test(serviceId) ? { serviceId } : {}),
    error: { code, mayHaveBeenAccepted: error?.mayHaveBeenAccepted === true },
    requestAttempted, serviceStarted: false, serviceClosed: false,
    closureReported: false, nextAction: error?.mayHaveBeenAccepted === true
      ? 'observe_original_service' : 'check_service_configuration_or_input',
  });
}

function report(value, requestAttempted) {
  const ready = value.state === 'READY', closed = value.state === 'CLOSED';
  const pending = ['STARTING', 'DRAINING', 'UNKNOWN'].includes(value.state);
  const outcome = value.error !== null ? 'error'
    : value.command === 'start' ? (ready ? 'ready_reported' : 'unresolved')
      : value.command === 'close' ? (closed ? 'closed_reported' : 'unresolved')
        : closed ? 'closed_reported' : ready ? 'ready_reported' : pending ? 'unresolved' : 'observed';
  const reason = value.error?.includes(value.owner.token) ? 'service_owner_error' : value.error;
  return envelope(value.command, outcome, {
    requestId: value.requestId, serviceId: value.serviceId,
    // The configured token binds the original owner but is not a diagnostic.
    owner: { pid: value.owner.pid, startTicks: value.owner.startTicks },
    state: value.state, endpoint: value.endpoint, endpointScope: value.endpointScope,
    completion: value.completion, requestAttempted,
    serviceStarted: value.command === 'start' && ready && value.error === null,
    serviceClosed: closed, closureReported: closed, hostHttpReachabilityVerified: false,
    ...(reason === null ? {} : { error: { code: reason,
      mayHaveBeenAccepted: value.command !== 'status' && requestAttempted } }),
    nextAction: value.state === 'UNKNOWN' ? 'retain_owner_and_operator_reconciliation'
      : closed ? 'service_closed_no_retry' : 'observe_original_service',
  });
}

async function checkSocket(path) {
  // A deliberately configured private path is required. No default discovery,
  // filesystem creation, socket replacement or adoption of another service.
  const [socket, parent, resolved] = await Promise.all([
    lstat(path), lstat(dirname(path)), realpath(path),
  ]);
  const uid = process.getuid();
  if (!socket.isSocket() || !parent.isDirectory() || socket.isSymbolicLink()
      || parent.isSymbolicLink() || resolved !== path
      || ![0, uid].includes(socket.uid) || parent.uid !== socket.uid
      || (socket.mode & 0o077) !== 0 || (parent.mode & 0o022) !== 0)
    fail('untrusted_service_socket');
}

async function boundedSocketCheck(path, signal, timeout) {
  let timer, abort;
  try {
    await Promise.race([
      checkSocket(path),
      new Promise((resolve, reject) => {
        timer = setTimeout(() => reject(new HarnessError('service_control_timeout')), timeout);
        abort = () => reject(new HarnessError('service_observation_interrupted'));
        signal?.addEventListener('abort', abort, { once: true });
        if (signal?.aborted) abort();
      }),
    ]);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

export class ServiceControlClient {
  #socket; #serviceId; #owner; #timeout;
  constructor({ socketPath, serviceId, owner, requestTimeoutMs = 5000 } = {}) {
    if (process.platform !== 'linux') fail('unsupported_service_platform');
    if (typeof socketPath !== 'string' || !posix.isAbsolute(socketPath)
        || posix.normalize(socketPath) !== socketPath || /[\0\r\n]/.test(socketPath)
        || Buffer.byteLength(socketPath) > 107) fail('invalid_service_socket');
    if (typeof serviceId !== 'string' || !ID.test(serviceId)) fail('invalid_service_id');
    if (!validOwner(owner)) fail('invalid_service_owner');
    if (!Number.isInteger(requestTimeoutMs) || requestTimeoutMs < 10 || requestTimeoutMs > 60000)
      fail('invalid_service_timeout');
    this.#socket = socketPath; this.#serviceId = serviceId;
    this.#owner = Object.freeze({ ...owner }); this.#timeout = requestTimeoutMs;
  }

  async start(requestId, options) { return this.#invoke('start', requestId, options); }
  async close(requestId, options) { return this.#invoke('close', requestId, options); }
  async status(requestId, options) { return this.#invoke('status', requestId, options); }

  async #invoke(command, requestId, { signal } = {}) {
    let attempted = false;
    const deadline = performance.now() + this.#timeout;
    try {
      if (typeof requestId !== 'string' || !ID.test(requestId)) fail('invalid_service_request_id');
      if (signal?.aborted) fail('service_observation_interrupted');
      try { await boundedSocketCheck(this.#socket, signal, this.#timeout); }
      catch (error) {
        if (error instanceof HarnessError) throw error;
        fail('service_connection_unavailable');
      }
      if (signal?.aborted) fail('service_observation_interrupted');
      if (performance.now() >= deadline) fail('service_control_timeout');
      // This is an operation precondition, not merely a response correlation.
      // The future server must reject a stale owner before dispatching anything.
      const request = { command, expectedOwner: this.#owner, protocol: CONTROL_PROTOCOL,
        requestId, serviceId: this.#serviceId };
      const expected = { command, requestId, serviceId: this.#serviceId, owner: this.#owner };
      const response = await new Promise((resolve, reject) => {
        let socket, done = false, total = 0;
        const chunks = [];
        const finish = (error, value) => {
          if (done) return;
          done = true;
          clearTimeout(timer); signal?.removeEventListener('abort', abort);
          socket?.destroy();
          if (error) {
            error.mayHaveBeenAccepted = command !== 'status' && attempted;
            reject(error);
          } else resolve(value);
        };
        const failRequest = code => finish(new HarnessError(code));
        const abort = () => failRequest('service_observation_interrupted');
        const timer = setTimeout(() => failRequest('service_control_timeout'),
          Math.max(1, Math.ceil(deadline - performance.now())));
        signal?.addEventListener('abort', abort, { once: true });
        if (signal?.aborted) { abort(); return; }
        try { socket = net.createConnection({ path: this.#socket, allowHalfOpen: true }); }
        catch { failRequest('service_transport_error'); return; }
        socket.once('connect', () => {
          if (done) return;
          attempted = true;
          socket.end(JSON.stringify(request) + '\n');
        });
        socket.on('data', chunk => {
          if (done) return;
          total += chunk.length;
          if (total > MAX_CONTROL_FRAME_BYTES) { failRequest('service_response_too_large'); return; }
          chunks.push(chunk);
        });
        socket.once('end', () => {
          if (done) return;
          try { finish(null, decodeReply(Buffer.concat(chunks), expected)); }
          catch (error) { finish(error); }
        });
        socket.once('error', () => failRequest('service_transport_error'));
        socket.once('close', () => { if (!done) failRequest('service_response_incomplete'); });
      });
      return report(response, attempted);
    } catch (error) {
      return serviceControlError(error, { command, requestId, serviceId: this.#serviceId,
        requestAttempted: attempted });
    }
  }
}

export function serviceControlExitCode(value) {
  if (value.outcome === 'unsupported') return 64;
  if (value.outcome === 'error') return INPUT_ERRORS.has(value.error?.code) ? 64 : 3;
  return value.outcome === 'unresolved' ? 3 : 0;
}
