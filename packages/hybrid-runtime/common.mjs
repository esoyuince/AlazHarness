// AlazHarness integration code. No model or tool execution lives in this module.
export class HarnessError extends Error {
  constructor(code) { super(code); this.name = 'HarnessError'; this.code = code; }
}
export function deferred() {
  let resolve, reject;
  const promise = new Promise((ok, no) => { resolve = ok; reject = no; });
  // A frame may arrive before its consumer awaits it; still propagate to that consumer.
  promise.catch(() => {});
  return { promise, resolve, reject };
}
export async function abortable(promise, signal) {
  if (signal.aborted) throw signal.reason;
  const stop = deferred();
  const onAbort = () => stop.reject(signal.reason);
  signal.addEventListener('abort', onAbort, { once: true });
  try { return await Promise.race([promise, stop.promise]); }
  finally { signal.removeEventListener('abort', onAbort); }
}
export async function boundedWait(promise, ms) {
  let timer;
  try {
    return await Promise.race([promise, new Promise(resolve => {
      timer = setTimeout(() => resolve(null), ms);
    })]);
  } finally { clearTimeout(timer); }
}
export function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
