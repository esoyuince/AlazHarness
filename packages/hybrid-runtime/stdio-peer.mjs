// Legacy Hermes TUI JSON-RPC client; not the canonical hermes-gateway-v1 wire.
import { spawn } from 'node:child_process';
import { deferred, boundedWait, HarnessError, object } from './common.mjs';
const MAX_FRAME_BYTES = 64 * 1024;
const MAX_OUTPUT_BYTES = 1024 * 1024;
const MAX_FRAMES = 128;

export class StdioPeer {
  constructor({ python, script, args, cwd, env, onEvent, onRequest }) {
    this.ready = deferred(); this.closed = deferred(); this.failure = deferred();
    this.pending = new Map(); this.nextId = 0; this.buffer = Buffer.alloc(0);
    this.bytes = 0; this.frames = 0; this.stderrBytes = 0; this.failureCode = null;
    this.closure = null; this.stopping = false; this.killSent = false;
    this.onEvent = onEvent; this.onRequest = onRequest;
    this.child = spawn(python, ['-I', '-B', '-u', '-X', 'utf8', script, ...args], {
      cwd, env, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, shell: false,
    });
    this.child.once('error', () => this.fail('SPAWN_ERROR'));
    this.child.stdin.on('error', () => { if (!this.stopping) this.fail('INPUT_CLOSED'); });
    this.child.stdout.on('data', chunk => this.receive(chunk));
    this.child.stderr.on('data', chunk => {
      this.stderrBytes += chunk.length;
      if (this.stderrBytes > MAX_OUTPUT_BYTES) this.fail('STDERR_LIMIT');
    });
    this.child.once('close', (code, signal) => {
      if (this.buffer.length && !this.failureCode) this.fail('PARTIAL_FRAME');
      this.closure = { reaped: true, exitCode: code, signal, killSent: this.killSent };
      this.closed.resolve(this.closure);
      const error = new HarnessError('PEER_CLOSED');
      this.ready.reject(error);
      for (const request of this.pending.values()) request.reject(error);
      this.pending.clear();
    });
  }
  fail(code) {
    if (this.failureCode) return;
    this.failureCode = code;
    const error = new HarnessError(code);
    this.failure.reject(error); this.ready.reject(error);
    for (const request of this.pending.values()) request.reject(error);
    this.pending.clear();
  }
  guard(promise) {
    return Promise.race([promise, this.failure.promise,
      this.closed.promise.then(() => { throw new HarnessError('PEER_CLOSED'); })]);
  }
  send(frame) {
    if (this.closure || this.child.stdin.destroyed || this.child.stdin.writableEnded)
      throw new HarnessError('INPUT_CLOSED');
    const line = JSON.stringify(frame) + '\n';
    if (Buffer.byteLength(line) > MAX_FRAME_BYTES) throw new HarnessError('REQUEST_TOO_LARGE');
    this.child.stdin.write(line, 'utf8');
  }
  request(method, params) {
    if (this.failureCode) return Promise.reject(new HarnessError(this.failureCode));
    const id = 'alaz-' + (++this.nextId);
    const result = deferred(); this.pending.set(id, result);
    try { this.send({ jsonrpc: '2.0', id, method, params }); }
    catch (error) { this.pending.delete(id); result.reject(error); }
    return result.promise;
  }
  receive(chunk) {
    if (this.failureCode) return;
    this.bytes += chunk.length;
    if (this.bytes > MAX_OUTPUT_BYTES) { this.fail('OUTPUT_LIMIT'); return; }
    this.buffer = Buffer.concat([this.buffer, chunk]);
    let end;
    while ((end = this.buffer.indexOf(10)) !== -1) {
      const raw = this.buffer.subarray(0, end); this.buffer = this.buffer.subarray(end + 1);
      if (raw.length > MAX_FRAME_BYTES || ++this.frames > MAX_FRAMES) {
        this.fail('FRAME_LIMIT'); return;
      }
      try {
        const text = new TextDecoder('utf-8', { fatal: true }).decode(raw);
        this.accept(JSON.parse(text));
      } catch (error) { this.fail(error instanceof HarnessError ? error.code : 'MALFORMED_FRAME'); return; }
      if (this.failureCode) return;
    }
    if (this.buffer.length > MAX_FRAME_BYTES) this.fail('FRAME_LIMIT');
  }
  accept(frame) {
    if (!object(frame) || frame.jsonrpc !== '2.0') throw new HarnessError('INVALID_RPC');
    if (frame.method !== undefined) {
      if (typeof frame.method !== 'string' || !object(frame.params)) throw new HarnessError('INVALID_RPC');
      if (frame.id !== undefined) {
        if (typeof frame.id !== 'string') throw new HarnessError('INVALID_REQUEST_ID');
        const response = this.onRequest(frame);
        this.send({ jsonrpc: '2.0', id: frame.id, ...response });
        return;
      }
      if (frame.method !== 'event' || typeof frame.params.type !== 'string')
        throw new HarnessError('INVALID_EVENT');
      if (frame.params.type === 'gateway.ready') {
        if (this.seenReady || !object(frame.params.payload)) throw new HarnessError('INVALID_READY');
        this.seenReady = true; this.ready.resolve(frame.params.payload);
      } else this.onEvent(frame.params);
      return;
    }
    const result = this.pending.get(frame.id);
    if (!result) throw new HarnessError('UNEXPECTED_REPLY');
    if (('result' in frame) === ('error' in frame)) throw new HarnessError('INVALID_REPLY');
    this.pending.delete(frame.id);
    if ('error' in frame) result.reject(new HarnessError('RPC_ERROR'));
    else result.resolve(frame.result);
  }
  endInput() {
    this.stopping = true;
    if (!this.child.stdin.destroyed && !this.child.stdin.writableEnded) this.child.stdin.end();
  }
  async reap(graceMs = 500) {
    this.endInput();
    let closure = this.closure ?? await boundedWait(this.closed.promise, graceMs);
    if (closure) return closure;
    // Only this fixed fixture child is owned; no generic process-tree/sandbox claim.
    this.killSent = this.child.kill('SIGKILL');
    closure = await boundedWait(this.closed.promise, 2000);
    return closure ?? { reaped: false, exitCode: null, signal: null, killSent: this.killSent };
  }
}
