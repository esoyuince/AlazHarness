/** Conservative HTTP projection. Presence of fields is a server claim, not a DB audit. */
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'interrupted']);
const STATES = new Set([...TERMINAL, 'queued', 'started', 'running', 'stopping', 'unknown', 'waiting_for_approval']);
const RUN = /^run_[a-f0-9]{32}$/;
const ADMISSION = /^[a-f0-9]{32}$/;

export function classifyRunRecovery(run) {
  if (!run || typeof run !== 'object' || Array.isArray(run) || typeof run.run_id !== 'string' || !RUN.test(run.run_id)
      || !STATES.has(run.status)) throw new TypeError('invalid_recovery_projection');
  if (run.status === 'completed' && (run.completed === false || run.partial === true
      || run.failed === true || run.interrupted === true)) throw new TypeError('contradictory_terminal_response');
  const transportTerminal = TERMINAL.has(run.status);
  const hasAdmission = typeof run.admission_id === 'string' && ADMISSION.test(run.admission_id);
  const hasSession = typeof run.session_id === 'string' && run.session_id.trim().length > 0 && run.session_id.length <= 1024;
  const hasGeneration = Number.isSafeInteger(run.execution_generation) && run.execution_generation > 0;
  const admissionReported = hasAdmission && hasSession && hasGeneration;
  let classification;
  if (transportTerminal && !admissionReported) classification = 'terminal_unverified';
  else if (run.status === 'unknown') classification = 'execution_unknown';
  else if (run.status === 'waiting_for_approval') classification = 'approval_required';
  else if (transportTerminal) classification = 'canonical_terminal_reported';
  else classification = 'in_progress';
  return Object.freeze({
    recoveryContractVersion: 1, classification, transportConfirmed: transportTerminal,
    // Compatibility flag now requires the native admission tuple. It still is NOT
    // independent database verification, successful completion, or retry authority.
    backendConfirmed: transportTerminal && admissionReported,
    admissionReported, canonicalVerified: false,
    requiresOperator: ['terminal_unverified', 'execution_unknown', 'approval_required'].includes(classification),
    retryAllowed: false, repairAllowed: false,
    nextAction: classification === 'terminal_unverified' ? 'inspect_canonical_record'
      : classification === 'execution_unknown' ? 'reconcile_unknown_execution'
      : classification === 'approval_required' ? 'await_scoped_approval'
      : transportTerminal ? 'retain_reported_outcome' : 'observe_existing_run',
  });
}
