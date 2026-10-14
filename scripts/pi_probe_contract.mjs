/** Test-host controls, not a Pi patch or a production sandbox. */
export const SCENARIOS = Object.freeze(['file-read', 'missing-file', 'cancel-model', 'one-round', 'request-cap', 'truncated-tool']);
export function requestGate(endpoint, limit, fetchImpl = globalThis.fetch) {
  const target = new URL(endpoint);
  if (target.protocol !== 'http:' || target.hostname !== '127.0.0.1' || target.username || target.password || target.search || target.hash) {
    throw new Error('Explicit credential-free IPv4 loopback endpoint required');
  }
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > 8) throw new Error('Invalid request limit');
  const state = { admitted: 0, budgetDenied: 0, endpointDenied: 0 };
  return {
    state,
    async fetch(input, init) {
      const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
      if (url.href !== target.href || (init?.method ?? input?.method ?? 'GET').toUpperCase() !== 'POST') {
        state.endpointDenied++; throw new Error('PROBE_ENDPOINT_DENIED');
      }
      if (state.admitted >= limit) { state.budgetDenied++; throw new Error('PROBE_REQUEST_BUDGET_EXHAUSTED'); }
      state.admitted++;
      return fetchImpl(input, { ...init, redirect: 'error' });
    },
  };
}
export function evaluateProbe(r) {
  if (!r || typeof r !== 'object' || !r.gate || !Array.isArray(r.serverErrors)) return ['malformed-receipt'];
  const counts = ['modelRequests', 'toolResults', 'toolErrors', 'pendingTools', 'agentEnds', 'beforeToolCalls', 'finishHookEnds', 'modelInferenceCalls', 'paidCalls'];
  const flags = ['isStreaming', 'timedOut', 'markerInToolResult', 'markerInFinal', 'modelSawMarker', 'modelSawError', 'cancelSocketClosed'];
  if (counts.some(k => !Number.isSafeInteger(r[k]) || r[k] < 0) || flags.some(k => typeof r[k] !== 'boolean') ||
      ['admitted', 'budgetDenied', 'endpointDenied'].some(k => !Number.isSafeInteger(r.gate[k]) || r.gate[k] < 0)) return ['malformed-receipt'];
  const errors = [];
  if (!SCENARIOS.includes(r.scenario)) errors.push('scenario');
  if (r.isStreaming || r.pendingTools !== 0 || r.agentEnds !== 1) errors.push('native-not-idle');
  if (r.timedOut || r.serverErrors.length || r.gate.endpointDenied) errors.push('test-host-failure');
  if (r.modelInferenceCalls !== 0 || r.paidCalls !== 0) errors.push('real-model-forbidden');
  const okRead = r.toolResults === 1 && r.toolErrors === 0 && r.markerInToolResult;
  switch (r.scenario) {
    case 'file-read':
      if (!okRead || r.modelRequests !== 2 || !r.modelSawMarker || !r.markerInFinal || r.stopReason !== 'stop') errors.push('native-read-round');
      break;
    case 'missing-file':
      if (r.toolResults !== 1 || r.toolErrors !== 1 || r.modelRequests !== 2 || !r.modelSawError || r.markerInFinal) errors.push('native-error-round');
      break;
    case 'cancel-model':
      if (r.toolResults !== 0 || r.modelRequests !== 1 || r.stopReason !== 'aborted' || !r.cancelSocketClosed) errors.push('native-cancel');
      break;
    case 'one-round':
      if (!okRead || r.modelRequests !== 1 || r.finishHookEnds !== 1 || r.markerInFinal) errors.push('host-end-after-tool');
      break;
    case 'request-cap':
      if (!okRead || r.modelRequests !== 1 || r.gate.admitted !== 1 || r.gate.budgetDenied < 1 || r.stopReason !== 'error') errors.push('provider-cap');
      break;
    case 'truncated-tool':
      if (r.toolResults !== 1 || r.toolErrors !== 1 || r.markerInToolResult || r.modelRequests !== 2 || r.beforeToolCalls !== 0) errors.push('truncated-call-not-rejected');
      break;
  }
  return errors;
}

export function normalizedOutcome(r) {
  if (r.gate?.budgetDenied > 0) return 'request_budget_exhausted';
  if (r.stopReason === 'aborted') return 'cancelled';
  if (r.finishHookEnds > 0) return 'stopped_at_host_boundary';
  if (r.scenario === 'truncated-tool' && r.toolErrors > 0) return 'invalid_tool_response';
  if (r.toolErrors > 0) return 'tool_failed';
  return r.taskCompleted ? 'completed' : 'incomplete';
}
