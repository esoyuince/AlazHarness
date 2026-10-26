/** Conservative HTTP projection. Presence of fields is a server claim, not a DB audit. */
const TERMINAL = new Set(['completed', 'failed', 'cancelled', 'interrupted']);
const STATES = new Set([...TERMINAL, 'queued', 'started', 'running', 'stopping', 'unknown', 'waiting_for_approval']);
const RUN = /^run_[a-f0-9]{32}$/;
const ADMISSION = /^[a-f0-9]{32}$/;
const INSTANCE = /^[A-Za-z0-9._-]{1,128}$/;
const QUEUED_PROOF_FIELDS = Object.freeze(['schema', 'kind', 'run_id', 'admission_id',
  'session_id', 'authority_epoch', 'instance_id', 'execution_generation', 'no_worker_started_verified']);

function queuedCancellationReported(run, hasAdmission, hasSession) {
  if (!Object.hasOwn(run, 'execution_proof')) return false;
  const proof = run.execution_proof;
  const valid = proof && typeof proof === 'object' && !Array.isArray(proof)
    && Object.keys(proof).length === QUEUED_PROOF_FIELDS.length
    && QUEUED_PROOF_FIELDS.every(key => Object.hasOwn(proof, key))
    && proof.schema === 1 && proof.kind === 'canonical_queued_cancellation'
    && run.status === 'cancelled' && run.execution_generation === null
    && run.completed !== true && run.failed !== true && run.interrupted !== true && run.partial !== true
    && hasAdmission && hasSession && proof.run_id === run.run_id
    && proof.admission_id === run.admission_id && proof.session_id === run.session_id
    && Number.isSafeInteger(proof.authority_epoch) && proof.authority_epoch > 0
    && typeof proof.instance_id === 'string' && INSTANCE.test(proof.instance_id)
    && proof.execution_generation === null && proof.no_worker_started_verified === true;
  if (!valid) throw new TypeError('invalid_execution_proof');
  return true;
}

export function classifyRunRecovery(run) {
  if (!run || typeof run !== 'object' || Array.isArray(run) || typeof run.run_id !== 'string' || !RUN.test(run.run_id)
      || !STATES.has(run.status)) throw new TypeError('invalid_recovery_projection');
  if (run.status === 'completed' && (run.completed === false || run.partial === true
      || run.failed === true || run.interrupted === true)) throw new TypeError('contradictory_terminal_response');
  const transportTerminal = TERMINAL.has(run.status);
  const hasAdmission = typeof run.admission_id === 'string' && ADMISSION.test(run.admission_id);
  const hasSession = typeof run.session_id === 'string' && run.session_id.trim().length > 0 && run.session_id.length <= 1024;
  const hasGeneration = Number.isSafeInteger(run.execution_generation) && run.execution_generation > 0;
  const noWorkerStartedReported = queuedCancellationReported(run, hasAdmission, hasSession);
  const admissionReported = hasAdmission && hasSession && (hasGeneration || noWorkerStartedReported);
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
    admissionReported, noWorkerStartedReported, canonicalVerified: false,
    requiresOperator: ['terminal_unverified', 'execution_unknown', 'approval_required'].includes(classification),
    retryAllowed: false, repairAllowed: false,
    nextAction: classification === 'terminal_unverified' ? 'inspect_canonical_record'
      : classification === 'execution_unknown' ? 'reconcile_unknown_execution'
      : classification === 'approval_required' ? 'await_scoped_approval'
      : transportTerminal ? 'retain_reported_outcome' : 'observe_existing_run',
  });
}
