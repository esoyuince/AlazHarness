"""R1B1: trusted isolated-read capture metadata in the existing native state owner.

No new file reader, database, provider call, raw content/path storage or authority.
Internal writer inputs must come from NativeReadIsolation, never an agent manifest.
A complete captured input is NOT complete tool output, dispatch, or comprehension.
"""
from __future__ import annotations
import hashlib
import re
from execution_budget import ExecutionDenied, ExecutionLedger, seal, integer
from recovery_inspector import EvidenceError, _json, _load

PREFIX = 'alaz.evidence.source.v1.'
FIELDS = {'version', 'scope', 'binding', 'policy', 'ticket', 'fingerprint',
          'runId', 'admissionId', 'generation', 'payloadDigest', 'epoch', 'instance',
          'toolCallHash', 'sourceSha256', 'sourceBytes', 'requestedOffset',
          'requestedLimit', 'state', 'outputSha256', 'outputBytes',
          'processOutcome', 'containerId', 'paginationBasis'}


def require(value, reason='source_capture_invalid'):
    if not value:
        raise ExecutionDenied(reason)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hex(value, length=64):
    return type(value) is str and re.fullmatch('[a-f0-9]{'+str(length)+'}', value) is not None


def _call_hash(value):
    require(type(value) is str and 0 < len(value.encode('utf-8')) <= 256,
            'source_tool_identity_missing')
    return sha(value.encode('utf-8'))


def native_tool_identity(session_id):
    """Actual pinned dispatcher context, not kwargs or tool/model-generated proof."""
    try:
        from tools import approval_context
        require(approval_context._approval_session_id.get() == session_id,
                'source_tool_session_mismatch')
        value = approval_context._approval_tool_call_id.get()
        _call_hash(value)
        return value
    except ExecutionDenied:
        raise
    except Exception:
        raise ExecutionDenied('source_tool_identity_missing') from None


def _prefix(context, admission_id):
    require(_hex(admission_id, 32))
    return PREFIX + context.scope + '.' + admission_id + '.'


def _validate(obj, context, policy):
    require(type(obj) is dict and set(obj) == FIELDS | {'digest'})
    require(obj.get('digest') == seal(obj)['digest'])
    require(type(obj['version']) is int and obj['version'] == 1)
    require(obj['paginationBasis'] == 'explicit_arguments_only', 'source_capture_pagination_basis_invalid')
    require((obj['scope'], obj['binding'], obj['policy']) ==
            (context.scope, context.binding, policy.fingerprint), 'source_capture_scope_mismatch')
    for key in ('fingerprint', 'payloadDigest', 'toolCallHash', 'sourceSha256'):
        require(_hex(obj[key]))
    for key in ('ticket', 'admissionId'):
        require(_hex(obj[key], 32))
    require(type(obj['runId']) is str and re.fullmatch('run_[a-f0-9]{32}', obj['runId']))
    integer(obj['generation'], 'capture_generation', 10**15, 1)
    integer(obj['epoch'], 'capture_epoch', context.epoch, 1)
    require(type(obj['instance']) is str and 0 < len(obj['instance']) <= 1024)
    integer(obj['sourceBytes'], 'captured_bytes', 65536)
    for field, maximum in (('requestedOffset', 100000), ('requestedLimit', 1000)):
        if obj[field] is not None:
            integer(obj[field], 'capture_pagination', maximum, 1)
    if obj['state'] == 'captured':
        require(all(obj[k] is None for k in ('outputSha256', 'outputBytes', 'containerId', 'processOutcome')))
    elif obj['state'] == 'returned':
        require(_hex(obj['outputSha256']) and _hex(obj['containerId']))
        integer(obj['outputBytes'], 'captured_output_bytes', 2_097_152)
        require(obj['processOutcome'] in ('completed', 'tool_failed'))
    else:
        raise ExecutionDenied('source_capture_invalid')
    return obj


def _active(conn, call):
    """Reuse canonical live admission and physical ticket validators."""
    from isolated_read import validate_admission
    ledger = call.ledger
    require(type(ledger) is ExecutionLedger, 'source_capture_owner_required')
    require(not ledger._state(conn)['quarantined'], 'execution_budget_quarantined')
    admission = validate_admission(conn, ledger, call.session_id)
    identity = (admission['admission_id'], admission['generation'],
                admission['payload_digest'], admission['owner_epoch'])
    require(identity == call.admission_identity, 'source_capture_admission_changed')
    found = conn.execute('SELECT value FROM state_meta WHERE key=?',
                         (ledger.prefix + call.ticket['ticket'],)).fetchone()
    require(found is not None, 'source_capture_ticket_missing')
    claim = ledger._row(_load(found[0]), call.ticket['ticket'])
    require(claim == call.ticket and claim['state'] == 'reserved' and
            claim['kind'] == 'read_file' and claim['fingerprint'] == call.fingerprint and
            claim['epoch'] == ledger.context.epoch and claim['instance'] == ledger.context.instance_id,
            'source_capture_ticket_mismatch')
    return admission


def begin_capture(call, args: dict, tool_call_id: str) -> dict:
    """Commit metadata for already captured immutable bytes BEFORE tool execution.

    Repeating begin, including after a lost commit acknowledgement, never grants
    another attempt. No content is reopened, returned, or stored here.
    """
    require(type(call.ledger) is ExecutionLedger, 'source_capture_owner_required')
    require(type(call.input_data) is bytes and len(call.input_data) <= 65536)
    require(type(args) is dict and set(args) <= {'path', 'offset', 'limit'} and 'path' in args)
    for field, maximum in (('offset', 100000), ('limit', 1000)):
        if field in args:
            integer(args[field], 'capture_pagination', maximum, 1)
    expected = sha(_json({'name': 'read_file', 'args': args, 'session_id': call.session_id}).encode())
    require(expected == call.fingerprint, 'source_capture_arguments_mismatch')
    ledger = call.ledger
    aid, generation, digest, epoch = call.admission_identity
    row = seal({'version': 1, 'scope': ledger.context.scope, 'binding': ledger.context.binding,
        'policy': ledger.policy.fingerprint, 'ticket': call.ticket['ticket'], 'fingerprint': expected,
        'runId': call.session_id, 'admissionId': aid, 'generation': generation,
        'payloadDigest': digest, 'epoch': epoch, 'instance': ledger.context.instance_id,
        'toolCallHash': _call_hash(tool_call_id), 'sourceSha256': sha(call.input_data),
        'sourceBytes': len(call.input_data), 'requestedOffset': args.get('offset'),
        'requestedLimit': args.get('limit'), 'state': 'captured', 'outputSha256': None,
        'outputBytes': None, 'processOutcome': None, 'containerId': None,
        'paginationBasis': 'explicit_arguments_only'})
    _validate(row, ledger.context, ledger.policy)
    key = _prefix(ledger.context, aid) + row['ticket']
    def tx(conn):
        _active(conn, call)
        require(conn.execute('SELECT 1 FROM state_meta WHERE key=?', (key,)).fetchone() is None,
                'source_capture_already_recorded')
        conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?)', (key, _json(row)))
        return dict(row)
    return ledger._write(tx)


def finish_capture(call, captured: dict, output: str) -> dict:
    """Bind the validated isolated invocation's redacted RETURN, not its delivery."""
    ledger = call.ledger
    require(type(ledger) is ExecutionLedger, 'source_capture_owner_required')
    captured = _load(_json(captured), 16384)
    _validate(captured, ledger.context, ledger.policy)
    require(captured['state'] == 'captured' and captured['ticket'] == call.ticket['ticket'])
    require(type(output) is str and len(output.encode('utf-8')) <= 2_097_152)
    receipt = call.receipt
    require(call.used is True and call.failure is None and type(receipt) is dict,
            'source_capture_execution_unverified')
    require((receipt.get('ticket'), receipt.get('runId'), receipt.get('admissionId'),
             receipt.get('executionGeneration'), receipt.get('inputDigest')) ==
            (captured['ticket'], captured['runId'], captured['admissionId'],
             captured['generation'], captured['sourceSha256']), 'source_capture_receipt_mismatch')
    require(receipt.get('exited') is True and receipt.get('removed') is True and
            receipt.get('outcome') in ('completed', 'tool_failed') and _hex(receipt.get('containerId')),
            'source_capture_execution_unverified')
    require(sha(call.input_data) == captured['sourceSha256'] and len(call.input_data) == captured['sourceBytes'])
    row = seal(captured | {'state': 'returned', 'outputSha256': sha(output.encode('utf-8')),
        'outputBytes': len(output.encode('utf-8')), 'processOutcome': receipt['outcome'],
        'containerId': receipt['containerId']})
    _validate(row, ledger.context, ledger.policy)
    key = _prefix(ledger.context, captured['admissionId']) + captured['ticket']
    def tx(conn):
        _active(conn, call)
        saved = conn.execute('SELECT value FROM state_meta WHERE key=?', (key,)).fetchone()
        require(saved is not None and _load(saved[0], 16384) == captured,
                'source_capture_changed')
        conn.execute('UPDATE state_meta SET value=? WHERE key=?', (_json(row), key))
        return dict(row)
    return ledger._write(tx)


def enrich_source_captures(conn, section: dict, record: dict, admission: dict, context, policy) -> None:
    """Inside the existing report snapshot; metadata only, no paths opened or writes.

    No receipt -> legacy UNKNOWN. Hash matching alone is not sufficient: bind
    scope, live/archived canonical admission, generation, claim and native tool ID.
    """
    prefix = _prefix(context, admission['admission_id'])
    found = conn.execute('SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key LIMIT 1001',
                         (prefix + '*',)).fetchall()
    if not found:
        return
    require(len(found) <= 1000, 'source_capture_history_limit')
    from host_report import _NoWriteOwner
    ledger = ExecutionLedger(_NoWriteOwner(str(context.profile_home / 'state.db')), context, policy)
    ledger._state(conn)
    refs = section['references']
    messages = record['result'].get('messages') or []
    captures, assignments = [], {}
    for key, raw in found:
        value = _validate(_load(raw, 16384), context, policy)
        require(key == prefix + value['ticket'])
        require((value['runId'], value['admissionId'], value['generation'], value['payloadDigest'], value['epoch']) ==
                (admission['request_id'], admission['admission_id'], admission['generation'],
                 admission['payload_digest'], admission['owner_epoch']), 'source_capture_admission_mismatch')
        claim_raw = conn.execute('SELECT value FROM state_meta WHERE key=?',
                                (ledger.prefix + value['ticket'],)).fetchone()
        require(claim_raw is not None, 'source_capture_ticket_missing')
        claim = ledger._row(_load(claim_raw[0]), value['ticket'])
        require(claim['kind'] == 'read_file' and claim['fingerprint'] == value['fingerprint'] and
                claim['epoch'] == value['epoch'] and claim['instance'] == value['instance'],
                'source_capture_ticket_mismatch')
        candidates = []
        if value['state'] == 'returned' and claim['state'] == 'settled' and claim['outcome'] == 'tool_return':
            for ref in refs:
                if ref['kind'] != 'retained_tool_result' or ref['pairing'] != 'structurally_paired_not_execution_proof':
                    continue
                m = messages[ref['messageIndex']]
                if (_call_hash(m['tool_call_id']) == value['toolCallHash'] and
                    ref['content']['sha256'] == value['outputSha256'] and
                    ref['content']['utf8Bytes'] == value['outputBytes']):
                    candidates.append(ref['evidenceId'])
        require(len(candidates) <= 1, 'ambiguous_source_capture_binding')
        capture_id = 'sc_' + value['digest']
        entry = {'captureId': capture_id, 'status': value['state'],
            'captureBasis': 'trusted_isolated_input_snapshot', 'sourceSha256': value['sourceSha256'],
            'sourceBytes': value['sourceBytes'], 'capturedRange': {'unit': 'raw_bytes', 'start': 0,
                'end': value['sourceBytes'], 'endExclusive': True}, 'snapshotCoverage': 'complete',
            'currentSourceAvailability': 'unknown', 'requestedLines': {'offset': value['requestedOffset'],
                'limit': value['requestedLimit'], 'basis': value['paginationBasis'], 'actualOutputCoverage': 'unknown'},
            'returnedOutput': {'sha256': value['outputSha256'], 'utf8Bytes': value['outputBytes'],
                'processOutcome': value['processOutcome'], 'deliveryVerified': False},
            'matchedEvidenceId': candidates[0] if candidates else None,
            'modelVisibility': 'unknown', 'claimTruthVerified': False, 'grantsExecutionPermission': False}
        captures.append(entry)
        for eid in candidates:
            require(eid not in assignments, 'ambiguous_source_capture_binding')
            assignments[eid] = entry
    # Publish only after every selected record passed. Any later host snapshot
    # recheck failure discards this entire report in LocalRecoveryInspector.
    for ref in refs:
        entry = assignments.get(ref['evidenceId'])
        if entry is not None:
            ref['executionAttribution'] = 'isolated_return_bound_to_admission'
            ref['originalSource'] = {'sha256': entry['sourceSha256'], 'coverage': 'captured_snapshot_complete',
                'availability': 'unknown', 'captureId': entry['captureId'], 'bytes': entry['sourceBytes'],
                'toolOutputCoverage': 'unknown'}
    section['warnings'] = [
        'unmatched_tool_messages_not_attributed_to_this_execution'
        if warning == 'historical_tool_messages_not_attributed_to_this_execution' else warning
        for warning in section['warnings']]
    section['sourceCaptures'] = captures
    section['sourceCaptureVersion'] = 1
    section['storageEffects'] = {'applicationStateWrites': False,
        'filesystemSilenceGuaranteed': False, 'sqliteAuxiliaryFilesMayBeCreated': True}
