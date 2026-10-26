/** Local operator actions over the existing host gate and native run observer.
 * No listener, scheduler, task queue, transcript writer or stored result copy.
 */
import { HostGateClient } from './host-gate-client.mjs';
import { HarnessError } from './hermes-runs.mjs';
import { classifyRunRecovery } from './run-recovery.mjs';

const REQUEST = /^[a-f0-9]{32}$/;
const RUN = /^run_[a-f0-9]{32}$/;
const CODE = /^[a-z][a-z0-9_]{0,79}$/;
const INPUT_ERRORS = new Set(['invalid_base_url', 'unsupported_endpoint', 'invalid_bearer_token',
  'invalid_request_timeout', 'invalid_response_limit', 'invalid_execution_requirement',
  'invalid_isolation_requirement', 'invalid_provider_broker_requirement', 'invalid_host_intent',
  'invalid_request_id', 'invalid_run_id', 'invalid_watch_timeout', 'invalid_poll_interval',
  'invalid_cli_arguments', 'invalid_cli_command', 'missing_cli_argument', 'invalid_cli_number',
  'missing_local_connection', 'input_too_large', 'input_not_utf8', 'input_empty', 'input_unreadable']);

function fail(code) { throw new HarnessError(code, { mayHaveBeenAccepted: false }); }
function identity(value, pattern, name) {
  if (typeof value !== 'string' || !pattern.test(value)) fail('invalid_' + name);
  return value;
}
function requestIdentity(value) {
  const id = value && typeof value === 'object'
    ? Object.getOwnPropertyDescriptor(value, 'requestId')?.value : null;
  return typeof id === 'string' && REQUEST.test(id) ? id : null;
}
function envelope(command, outcome, fields = {}) {
  return { localControlVersion: 1, command, outcome, retryAllowed: false, ...fields };
}

/** Errors deliberately contain no raw exception, server error text or credential. */
export function controlError(error, { command = null, requestId = null, runId = null } = {}) {
  const code = error instanceof HarnessError && typeof error.code === 'string' && CODE.test(error.code)
    ? error.code : 'local_control_error';
  const detail = { code, mayHaveBeenAccepted: error?.mayHaveBeenAccepted === true };
  if (Number.isInteger(error?.httpStatus) && error.httpStatus >= 100 && error.httpStatus <= 599)
    detail.httpStatus = error.httpStatus;
  if (typeof error?.hostCode === 'string' && CODE.test(error.hostCode)) detail.hostCode = error.hostCode;
  if (['cancelled', 'execution_timeout'].includes(error?.hostReason)) detail.hostReason = error.hostReason;
  return envelope(command, 'error', {
    ...(typeof requestId === 'string' && REQUEST.test(requestId) ? { requestId } : {}),
    ...(typeof runId === 'string' && RUN.test(runId) ? { runId } : {}),
    error: detail,
    nextAction: requestId && detail.mayHaveBeenAccepted ? 'observe_original_request'
      : runId ? 'observe_existing_run' : 'check_configuration_or_input',
  });
}

function runView(run) {
  // Null generation alone is insufficient. Only the strict, identity-bound
  // native queued-cancellation proof can report that this admission never ran.
  const recovery = classifyRunRecovery(run);
  return {
    runId: run.run_id, status: run.status,
    admissionId: recovery.admissionReported ? run.admission_id : null,
    sessionId: recovery.admissionReported ? run.session_id : null,
    executionGeneration: recovery.admissionReported ? run.execution_generation : null,
    classification: recovery.classification,
    terminalReported: recovery.transportConfirmed,
    canonicalTupleReported: recovery.admissionReported,
    noWorkerStartedReported: recovery.noWorkerStartedReported,
    canonicalVerified: false, requiresOperator: recovery.requiresOperator,
    nextAction: recovery.nextAction,
  };
}

function observationOptions({ signal, watchTimeoutMs = 30000, pollIntervalMs = 100 } = {}) {
  if (!Number.isInteger(watchTimeoutMs) || watchTimeoutMs < 10 || watchTimeoutMs > 600000)
    fail('invalid_watch_timeout');
  if (!Number.isInteger(pollIntervalMs) || pollIntervalMs < 1 || pollIntervalMs > 5000)
    fail('invalid_poll_interval');
  return { signal, executionTimeoutMs: watchTimeoutMs, pollIntervalMs };
}

function usageView(run, view) {
  const result = {
    source: 'native_run_response', scope: 'run', coverage: 'unavailable',
    inputTokens: null, outputTokens: null, totalTokens: null,
    physicalAttemptCoverageVerified: false, costMicrousd: null,
    costCoverage: 'unavailable', profileBudgetAvailable: false,
  };
  if (!view.terminalReported || !view.canonicalTupleReported)
    return { ...result, coverage: 'unverified_live_or_terminal_usage' };
  const usage = run.usage;
  if (!usage || typeof usage !== 'object' || Array.isArray(usage)) return result;
  const fields = [['input_tokens', 'inputTokens'], ['output_tokens', 'outputTokens'], ['total_tokens', 'totalTokens']];
  for (const [wire] of fields) {
    if (Object.hasOwn(usage, wire) && (!Number.isSafeInteger(usage[wire]) || usage[wire] < 0 || usage[wire] > 10 ** 15))
      return { ...result, coverage: 'invalid' };
  }
  for (const [wire, field] of fields) if (Object.hasOwn(usage, wire)) result[field] = usage[wire];
  const { inputTokens: input, outputTokens: output, totalTokens: total } = result;
  if (input !== null && output !== null && total !== null && input + output !== total)
    return { ...result, inputTokens: null, outputTokens: null, totalTokens: null, coverage: 'invalid' };
  result.coverage = input !== null && output !== null && total !== null ? 'complete_fields'
    : fields.some(([, field]) => result[field] !== null) ? 'partial_fields' : 'unavailable';
  return result;
}

export class LocalControlClient {
  #host;
  constructor(options = {}) {
    // Product task submission never downgrades to raw runs or an unbudgeted route.
    this.#host = new HostGateClient({ ...options, requireExecution: true, requireProviderBroker: true });
  }

  async task(request, { signal } = {}) {
    const requestId = requestIdentity(request);
    try {
      const permit = await this.#host.prepare(request, { signal });
      const run = await this.#host.dispatch(permit, { signal });
      const view = runView(run);
      return envelope('task', view.requiresOperator ? 'unresolved' : 'accepted', {
        requestId: permit.requestId, run: view, completionVerified: false, nextAction: view.nextAction });
    } catch (error) { return controlError(error, { command: 'task', requestId }); }
  }

  async request(requestId, { signal } = {}) {
    try {
      identity(requestId, REQUEST, 'request_id');
      const observation = await this.#host.observeRequest(requestId, { signal });
      return envelope('request', observation.classification === 'native_run_located' ? 'located' : 'unresolved',
        { requestId, observation });
    } catch (error) { return controlError(error, { command: 'request', requestId }); }
  }

  async status(runId, { signal } = {}) {
    try {
      const run = runView(await this.#host.status(identity(runId, RUN, 'run_id'), { signal }));
      return envelope('status', run.requiresOperator ? 'unresolved' : 'observed', { run,
        observationMode: 'http_get_no_new_dispatch' });
    } catch (error) { return controlError(error, { command: 'status', runId }); }
  }

  async watch(runId, options = {}) {
    try {
      identity(runId, RUN, 'run_id');
      const observed = await this.#host.resume(runId, observationOptions(options));
      const run = runView(observed.run);
      return envelope('watch', run.terminalReported && run.canonicalTupleReported ? 'terminal_reported' : 'unresolved',
        { run, stopRequested: false, observationMode: 'http_get_no_new_dispatch' });
    } catch (error) {
      return { ...controlError(error, { command: 'watch', runId }), stopRequested: false };
    }
  }

  async result(runId, { signal } = {}) {
    try {
      const observed = await this.#host.status(identity(runId, RUN, 'run_id'), { signal });
      const run = runView(observed);
      const available = run.terminalReported && run.canonicalTupleReported && typeof observed.output === 'string';
      return envelope('result', available ? 'result_available' : 'result_unavailable', {
        run, output: available ? observed.output : null,
        outputIsCompletedResponse: available && run.status === 'completed',
        goalAchievementIndependentlyVerified: false,
      });
    } catch (error) { return controlError(error, { command: 'result', runId }); }
  }

  async usage(runId, { signal } = {}) {
    try {
      const observed = await this.#host.status(identity(runId, RUN, 'run_id'), { signal });
      const run = runView(observed), usage = usageView(observed, run);
      return envelope('usage', usage.coverage === 'complete_fields' ? 'usage_observed' : 'usage_unavailable', { run, usage });
    } catch (error) { return controlError(error, { command: 'usage', runId }); }
  }

  async cancel(runId, options = {}) {
    let observedOptions;
    try {
      identity(runId, RUN, 'run_id');
      observedOptions = observationOptions(options); // Validate before sending a stop.
      if (options.signal?.aborted) fail('aborted_before_request');
    } catch (error) {
      return { ...controlError(error, { command: 'cancel', runId }),
        cancellation: { requestAttempted: false, requestAcknowledged: false, requestMayHaveBeenAccepted: false,
          terminalReported: false, noWorkerStartedReported: false, physicalWorkerTerminalVerified: false } };
    }
    const cancellation = { requestAttempted: true, requestAcknowledged: false,
      requestMayHaveBeenAccepted: false, terminalReported: false, noWorkerStartedReported: false,
      physicalWorkerTerminalVerified: false };
    try {
      await this.#host.stop(runId, { signal: options.signal });
      cancellation.requestAcknowledged = true;
      cancellation.requestMayHaveBeenAccepted = true;
    } catch (error) {
      cancellation.requestMayHaveBeenAccepted = error?.mayHaveBeenAccepted === true;
      cancellation.requestError = controlError(error).error;
      if (error?.code === 'aborted_before_request') cancellation.requestAttempted = false;
    }
    try {
      // The stop acknowledgement is not the terminal result. Read the existing run;
      // losing the observer never sends another stop or reopens admission.
      const observed = await this.#host.resume(runId, observedOptions), run = runView(observed.run);
      cancellation.terminalReported = run.terminalReported && run.canonicalTupleReported;
      cancellation.noWorkerStartedReported = run.noWorkerStartedReported;
      cancellation.effectReported = cancellation.terminalReported ? run.status : 'unconfirmed';
      return envelope('cancel', cancellation.terminalReported ? 'terminal_reported' : 'unresolved', { run, cancellation });
    } catch (error) {
      return { ...controlError(error, { command: 'cancel', runId }), cancellation,
        nextAction: 'observe_existing_run' };
    }
  }
}

/** CLI exit contract: 0 observed/accepted, 2 failed work, 3 unresolved, 64 invalid/unsupported. */
export function controlExitCode(value) {
  if (value.outcome === 'unsupported') return 64;
  if (value.outcome === 'error') {
    return INPUT_ERRORS.has(value.error.code) ? 64 : 3;
  }
  if (['unresolved', 'result_unavailable', 'usage_unavailable'].includes(value.outcome)) return 3;
  if (value.command === 'result' && value.run?.status !== 'completed') return 2;
  if (value.command === 'watch' && value.run?.status !== 'completed') return 2;
  if (value.command === 'cancel' && value.run?.status === 'failed') return 2;
  return 0;
}

export function unsupportedLifecycle(command) {
  if (!['start', 'close'].includes(command)) fail('invalid_lifecycle_command');
  return envelope(command, 'unsupported', { error: { code: 'service_lifecycle_not_implemented', mayHaveBeenAccepted: false },
    serviceStarted: false, serviceClosed: false, nextAction: 'complete_native_listener_owner_integration' });
}
