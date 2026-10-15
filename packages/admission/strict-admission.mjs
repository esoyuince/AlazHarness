/** Experimental single-owner Pi adapter. No new queue, database, or model loop. */
import { createHash } from 'node:crypto';

export class AdmissionError extends Error {
  constructor(code) { super(code); this.name = 'AdmissionError'; this.code = code; }
}
export const BINDING_KIND = 'alaz.admission.v1';
const fail = code => { throw new AdmissionError(code); };
const hash = text => createHash('sha256').update(text, 'utf8').digest('hex');
const own = (value, key) => Object.hasOwn(value, key);
const plain = value => value !== null && typeof value === 'object' &&
  (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);

/** Versioned strict JSON, not an RFC8785 claim. Reject lossy/active JS inputs. */
export function canonicalJson(value, {maxBytes = 262144, maxDepth = 32} = {}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1 || !Number.isSafeInteger(maxDepth) || maxDepth < 1)
    fail('invalid_limits');
  const ancestors = new Set(); let nodes = 0;
  function visit(item, depth) {
    if (depth > maxDepth || ++nodes > 20000) fail('payload_limit');
    if (item === null || typeof item === 'boolean') return JSON.stringify(item);
    if (typeof item === 'string') {
      if (!item.isWellFormed()) fail('invalid_unicode');
      if (Buffer.byteLength(item, 'utf8') > maxBytes) fail('payload_limit');
      return JSON.stringify(item);
    }
    if (typeof item === 'number') {
      if (!Number.isFinite(item)) fail('invalid_number');
      return JSON.stringify(item); // -0 and 0 have the same JSON meaning.
    }
    if (typeof item !== 'object') fail('non_json_payload');
    if (ancestors.has(item)) fail('cyclic_payload');
    ancestors.add(item);
    let text;
    if (Array.isArray(item)) {
      if (item.length > 20000 || Reflect.ownKeys(item).length !== item.length + 1)
        fail('non_dense_array');
      const values = [];
      for (let i = 0; i < item.length; i++) {
        const d = Object.getOwnPropertyDescriptor(item, String(i));
        if (!d || !own(d, 'value') || !d.enumerable) fail('active_payload');
        values.push(visit(d.value, depth + 1));
      }
      text = '[' + values.join(',') + ']';
    } else {
      if (!plain(item)) fail('non_json_payload');
      const keys = Reflect.ownKeys(item);
      if (keys.some(key => typeof key !== 'string')) fail('non_json_payload');
      const values = [];
      for (const key of keys.sort()) {
        const d = Object.getOwnPropertyDescriptor(item, key);
        if (!own(d, 'value') || !d.enumerable) fail('active_payload');
        if (!key.isWellFormed()) fail('invalid_unicode');
        values.push(JSON.stringify(key) + ':' + visit(d.value, depth + 1));
      }
      text = '{' + values.join(',') + '}';
    }
    ancestors.delete(item);
    if (Buffer.byteLength(text, 'utf8') > maxBytes) fail('payload_limit');
    return text;
  }
  const text = visit(value, 0);
  if (Buffer.byteLength(text, 'utf8') > maxBytes) fail('payload_limit');
  return text;
}

/** Snapshot synchronously before admission can yield. No caller object reaches Tx. */
export function prepareAdmission(draft, executionScope = {}) {
  const snapshot = JSON.parse(canonicalJson({draft, executionScope}));
  const d = snapshot.draft;
  if (!plain(d) || !plain(snapshot.executionScope)) fail('invalid_request');
  if (typeof d.requestId !== 'string' || d.requestId.length === 0 || Buffer.byteLength(d.requestId) > 256)
    fail('invalid_request_id');
  const allowed = d.type === 'input' ? ['type','requestId','content','entry','whenBusy'] :
    d.type === 'write' ? ['type','requestId','entry'] : fail('unsupported_submission_type');
  if (Object.keys(d).some(key => !allowed.includes(key))) fail('unsupported_request_field');
  if (d.type === 'input') {
    if (!own(d,'content') || !(typeof d.content === 'string' || Array.isArray(d.content))) fail('invalid_input');
    if (!own(d, 'whenBusy')) d.whenBusy = 'followUp';
    if (!['followUp','steer','reject'].includes(d.whenBusy)) fail('invalid_busy_policy');
  } else if (!plain(d.entry)) fail('invalid_entry');
  const payload = {...d}; delete payload.requestId;
  const canonical = canonicalJson({version:1, draft:payload, executionScope:snapshot.executionScope});
  return {draft:d, fingerprint:hash(canonical), key:hash('alaz.admission.v1\0' + d.requestId)};
}

/**
 * Pi's transaction-level admitSubmission is an INTERNAL pinned compatibility seam.
 * The loader must verify the source commit/file before injecting it. No private
 * Harness fields are reached; public Conversation.commit owns the whole write.
 * All external submissions MUST enter here; raw native submit is not intercepted.
 * The host still owns authorization, stable executionScope and single-writer policy.
 */
export function createStrictAdmission({harness, defineDocFamily, admitSubmission}) {
  if (!harness || typeof harness.submission !== 'function' || typeof harness.resume !== 'function' ||
      typeof harness.conversation !== 'function' || typeof defineDocFamily !== 'function' || typeof admitSubmission !== 'function') fail('invalid_adapter');
  const Binding = defineDocFamily({kind:BINDING_KIND,version:1,family:true,scope:'conversation',
    history:'latest',fork:'initial',initial:() => ({})});
  return {
    Binding,
    async submit(conversationId, draft, context, executionScope = {}) {
      const prepared = prepareAdmission(draft, executionScope); // before first await
      const cid = conversationId;
      if (!Number.isSafeInteger(cid) || cid <= 0) fail('invalid_conversation');
      // Never execute an arbitrary or foreign Harness conversation.commit callback.
      const conversation = await harness.conversation(cid, context);
      if (!conversation || conversation.id !== cid || typeof conversation.commit !== 'function') fail('invalid_conversation');
      const outcome = await conversation.commit(async tx => {
        const existing = await tx.submissionByRequest(cid, prepared.draft.requestId);
        const binding = await tx.doc(Binding, cid, prepared.key, null);
        if (existing !== undefined) {
          // Never backfill an unknown legacy payload with the retry caller's data.
          if (binding.schema !== 1 || binding.submissionId !== existing.id ||
              binding.requestId !== prepared.draft.requestId) fail('unmanaged_or_inconsistent_admission');
          if (binding.fingerprint !== prepared.fingerprint) fail('request_payload_conflict');
          if (binding.type !== prepared.draft.type || existing.type !== prepared.draft.type)
            fail('inconsistent_admission');
          return {id:existing.id,reused:true};
        }
        if (Object.keys(binding).length !== 0) fail('orphan_admission_binding');
        const id = await admitSubmission(tx, cid, prepared.draft, Date.now(),
          {steeringMode:'one',followUpMode:'one'});
        if (!Number.isSafeInteger(id) || id <= 0) fail('invalid_native_id');
        // Same native Storage.commit / SQLite transaction as entry + submission.
        binding.schema = 1; binding.requestId = prepared.draft.requestId;
        binding.fingerprint = prepared.fingerprint; binding.submissionId = id;
        binding.type = prepared.draft.type;
        return {id,reused:false};
      }, context);
      const submission = await harness.submission(outcome.id, context);
      if (!submission) fail('admission_ack_uncertain');
      harness.resume(); // never schedule a rejected first admission
      return {submission,reused:outcome.reused,fingerprint:prepared.fingerprint};
    },
  };
}
