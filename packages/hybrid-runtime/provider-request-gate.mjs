/** Per-transport request cap. Not a token/currency budget or an OS sandbox. */
export class RequestGateError extends Error {
  constructor(code) { super(code); this.name = 'RequestGateError'; this.code = code; }
}

export function createProviderRequestGate({ endpoint, maxRequests, fetchImpl = globalThis.fetch }) {
  const expected = new URL(endpoint);
  if (expected.protocol !== 'http:' || expected.hostname !== '127.0.0.1' ||
      expected.username || expected.password || expected.search || expected.hash ||
      expected.pathname !== '/v1/chat/completions') throw new TypeError('Loopback completion endpoint required');
  if (!Number.isSafeInteger(maxRequests) || maxRequests < 0 || maxRequests > 1000) {
    throw new TypeError('maxRequests must be an integer in [0,1000]');
  }
  if (typeof fetchImpl !== 'function') throw new TypeError('fetchImpl must be callable');
  let submitted = 0, denied = 0, blockedTargets = 0, failedTransports = 0, closed = false;
  return Object.freeze({
    async fetch(input, init = {}) {
      const url = new URL(input instanceof Request ? input.url : String(input));
      const method = (init.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase();
      if (url.href !== expected.href || method !== 'POST') {
        blockedTargets++; throw new RequestGateError('TARGET_NOT_ALLOWED');
      }
      if (closed) { denied++; throw new RequestGateError('GATE_CLOSED'); }
      const signal = init.signal ?? (input instanceof Request ? input.signal : undefined);
      if (signal?.aborted) throw new RequestGateError('ABORTED_BEFORE_DISPATCH');
      if (submitted >= maxRequests) { denied++; throw new RequestGateError('REQUEST_BUDGET_EXHAUSTED'); }
      // Reserve synchronously before yielding. Never refund uncertain network effects.
      submitted++;
      try {
        const response = await fetchImpl(input, { ...init, redirect: 'manual' });
        if (response.status >= 300 && response.status < 400) {
          await response.body?.cancel();
          throw new RequestGateError('REDIRECT_NOT_ALLOWED');
        }
        return response;
      } catch (error) { failedTransports++; throw error; }
    },
    close() { closed = true; },
    snapshot() { return Object.freeze({ maxRequests, submitted, denied, blockedTargets, failedTransports, closed }); },
  });
}
