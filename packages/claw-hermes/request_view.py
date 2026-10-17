"""R1B2: bounded request metadata written by the existing native ledger owner.

Trusted internal broker-client interfaces, not agent manifests or new authority.
A write-ahead handoff is not a physical send; even a broker HTTP response does
not prove model processing, comprehension, or that the caller received a result.
"""
from __future__ import annotations
import hashlib
import re
from execution_budget import ExecutionLedger, ExecutionDenied, seal, integer
from recovery_inspector import _load, _json
import source_capture

PREFIX = 'alaz.evidence.request.v1.'
MAX_RECORD_BYTES = 131072
MAX_HISTORY_BYTES = 8_388_608
FIELDS = {'version', 'scope', 'binding', 'policy', 'ticket', 'epoch', 'instance',
          'brokerId', 'routeFingerprint', 'egressDigest', 'requestDigest',
          'requestBytes', 'messageCount', 'toolMessages', 'state',
          'responseSha256', 'responseBytes', 'httpStatus', 'responseContentType'}
TOOL_FIELDS = {'index', 'toolCallHash', 'contentSha256', 'contentBytes', 'sourceCaptureDigest'}


def require(value, code='request_view_invalid'):
    if not value:
        raise ExecutionDenied(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ishex(value, size=64):
    return type(value) is str and re.fullmatch('[a-f0-9]{'+str(size)+'}', value) is not None


def key_for(context, ticket):
    require(ishex(ticket, 32))
    return PREFIX + context.scope + '.' + ticket


def call_hash(value):
    if type(value) is str and 0 < len(value.encode('utf-8')) <= 256:
        return sha(value.encode('utf-8'))
    return None


def validate(row, context, policy):
    require(type(row) is dict and set(row) == FIELDS | {'digest'})
    require(row.get('digest') == seal(row)['digest'])
    require(type(row['version']) is int and row['version'] == 1)
    require((row['scope'], row['binding'], row['policy']) ==
            (context.scope, context.binding, policy.fingerprint), 'request_view_scope_mismatch')
    for name in ('ticket', 'brokerId'):
        require(ishex(row[name], 32))
    for name in ('routeFingerprint', 'egressDigest', 'requestDigest'):
        require(ishex(row[name]))
    integer(row['epoch'], 'request_view_epoch', context.epoch, 1)
    require(type(row['instance']) is str and 0 < len(row['instance']) <= 1024)
    integer(row['requestBytes'], 'request_view_bytes', 2_000_000, 1)
    integer(row['messageCount'], 'request_view_messages', 1024, 1)
    require(type(row['toolMessages']) is list and len(row['toolMessages']) <= 256)
    previous = -1
    for item in row['toolMessages']:
        require(type(item) is dict and set(item) == TOOL_FIELDS)
        integer(item['index'], 'request_message_index', row['messageCount']-1)
        require(item['index'] > previous); previous = item['index']
        if item['toolCallHash'] is not None:
            require(ishex(item['toolCallHash']))
        if item['contentSha256'] is None:
            require(item['contentBytes'] is None)
        else:
            require(ishex(item['contentSha256']))
            integer(item['contentBytes'], 'request_tool_bytes', row['requestBytes'])
        if item['sourceCaptureDigest'] is not None:
            require(ishex(item['sourceCaptureDigest']) and item['toolCallHash'] is not None
                    and item['contentSha256'] is not None)
    if row['state'] in ('prepared', 'handoff_armed'):
        require(all(row[k] is None for k in ('responseSha256', 'responseBytes', 'httpStatus', 'responseContentType')))
    elif row['state'] == 'broker_response_observed':
        require(ishex(row['responseSha256']))
        integer(row['responseBytes'], 'request_response_bytes', 4_194_304)
        require(type(row['httpStatus']) is int and (row['httpStatus'] == 200 or 400 <= row['httpStatus'] <= 599))
        require(row['responseContentType'] in ('application/json', 'text/event-stream'))
    else:
        raise ExecutionDenied('request_view_invalid')
    require(len(_json(row).encode('utf-8')) <= MAX_RECORD_BYTES, 'request_view_too_large')
    return row


def inventory(payload):
    """Metadata of exact normalized text messages; no raw content or inferred run."""
    messages = payload.get('messages')
    require(type(messages) is list and 1 <= len(messages) <= 1024, 'request_view_message_limit')
    calls, results = {}, {}
    for i, message in enumerate(messages):
        require(type(message) is dict and message.get('role') in ('system','developer','user','assistant','tool'),
                'request_view_message_invalid')
        content = message.get('content')
        require(content is None or type(content) is str, 'request_view_message_invalid')
        if message['role'] == 'assistant':
            raw = message.get('tool_calls', [])
            if raw is None:raw = []
            require(type(raw) is list and len(raw) <= 256, 'request_view_call_limit')
            for call in raw:
                require(type(call) is dict, 'request_view_call_invalid')
                identifier = call_hash(call.get('id'))
                if identifier is not None:
                    calls.setdefault(identifier, []).append((i, call.get('function')))
        if message['role'] == 'tool':
            identifier = call_hash(message.get('tool_call_id'))
            if identifier is not None:
                results.setdefault(identifier, []).append(i)
    items = []
    for i, message in enumerate(messages):
        if message['role'] != 'tool':
            continue
        raw = message.get('content')
        data = raw.encode('utf-8') if type(raw) is str else None
        identifier = call_hash(message.get('tool_call_id'))
        preceding = calls.get(identifier, [])
        paired = (identifier is not None and len(preceding) == 1 and len(results.get(identifier, [])) == 1
                  and preceding[0][0] < i and type(preceding[0][1]) is dict
                  and preceding[0][1].get('name') == 'read_file')
        items.append(({'index': i, 'toolCallHash': identifier,
                       'contentSha256': sha(data) if data is not None else None,
                       'contentBytes': len(data) if data is not None else None,
                       'sourceCaptureDigest': None}, paired))
    require(len(items) <= 256, 'request_view_tool_limit')
    return items


def _capture_candidates(conn, ledger):
    prefix = source_capture.PREFIX + ledger.context.scope + '.'
    rows = conn.execute('SELECT key,value FROM state_meta WHERE key GLOB ? LIMIT 1001', (prefix+'*',)).fetchall()
    require(len(rows) <= 1000, 'request_source_history_limit')
    total = 0; candidates = {}
    for key, raw in rows:
        require(type(raw) is str)
        total += len(raw.encode('utf-8'))
        require(total <= MAX_HISTORY_BYTES, 'request_source_history_limit')
        cap = source_capture._validate(_load(raw, 16384), ledger.context, ledger.policy)
        require(key == source_capture._prefix(ledger.context, cap['admissionId']) + cap['ticket'])
        saved = conn.execute('SELECT value FROM state_meta WHERE key=?', (ledger.prefix+cap['ticket'],)).fetchone()
        require(saved is not None, 'request_source_claim_missing')
        claim = ledger._row(_load(saved[0],16384), cap['ticket'])
        require((claim['kind'], claim['fingerprint'], claim['epoch'], claim['instance']) ==
                ('read_file', cap['fingerprint'], cap['epoch'], cap['instance']), 'request_source_claim_mismatch')
        if cap['state'] == 'returned' and claim['state'] == 'settled' and claim['outcome'] == 'tool_return':
            signature = (cap['toolCallHash'], cap['outputSha256'], cap['outputBytes'])
            candidates.setdefault(signature, []).append(cap['digest'])
    return candidates


def prepare_in_transaction(conn, ledger, grant, payload):
    """Called only inside authorize_egress's transaction, alongside its grant.

    Source provenance is selected NOW. The reader never retrospectively matches
    an old request to a later-created source record or guesses its initiating run.
    """
    require(type(ledger) is ExecutionLedger, 'request_view_owner_required')
    raw = _json(payload).encode('utf-8')
    require(0 < len(raw) <= 2_000_000 and sha(raw) == grant['fingerprint'], 'request_view_payload_mismatch')
    items = inventory(payload)
    candidates = _capture_candidates(conn, ledger) if any(pair for _, pair in items) else {}
    for item, paired in items:
        if paired and item['contentSha256'] is not None:
            found = candidates.get((item['toolCallHash'], item['contentSha256'], item['contentBytes']), [])
            require(len(found) <= 1, 'ambiguous_request_source')
            item['sourceCaptureDigest'] = found[0] if found else None
    row = seal({'version':1, 'scope':ledger.context.scope, 'binding':ledger.context.binding,
                'policy':ledger.policy.fingerprint, 'ticket':grant['ticket'],
                'epoch':grant['epoch'], 'instance':grant['instance'], 'brokerId':grant['brokerId'],
                'routeFingerprint':grant['routeFingerprint'], 'egressDigest':seal(grant)['digest'],
                'requestDigest':grant['fingerprint'], 'requestBytes':len(raw),
                'messageCount':len(payload['messages']), 'toolMessages':[item for item, _ in items],
                'state':'prepared', 'responseSha256':None, 'responseBytes':None,
                'httpStatus':None, 'responseContentType':None})
    validate(row, ledger.context, ledger.policy)
    key = key_for(ledger.context, grant['ticket'])
    require(conn.execute('SELECT 1 FROM state_meta WHERE key=?', (key,)).fetchone() is None,
            'request_view_already_recorded')
    conn.execute('INSERT INTO state_meta(key,value) VALUES(?,?)', (key, _json(row)))


def linked_claim(conn, ledger, row):
    from provider_egress import EGRESS, GRANT_FIELDS
    saved = conn.execute('SELECT value FROM state_meta WHERE key=?', (ledger.prefix+row['ticket'],)).fetchone()
    require(saved is not None, 'request_view_claim_missing')
    claim = ledger._row(_load(saved[0], 16384), row['ticket'])
    require((claim['kind'], claim['fingerprint'], claim['epoch'], claim['instance']) ==
            ('provider', row['requestDigest'], row['epoch'], row['instance']), 'request_view_claim_mismatch')
    saved = conn.execute('SELECT value FROM state_meta WHERE key=?',
                         (EGRESS+row['scope']+'.'+row['ticket'],)).fetchone()
    require(saved is not None, 'request_view_grant_missing')
    grant = _load(saved[0], 16384)
    require(type(grant) is dict and set(grant) == GRANT_FIELDS | {'digest'} and grant == seal(grant)
            and grant['digest'] == row['egressDigest'], 'request_view_grant_mismatch')
    require((grant['scope'],grant['binding'],grant['policy'],grant['ticket'],grant['fingerprint'],
             grant['epoch'],grant['instance'],grant['brokerId'],grant['routeFingerprint']) ==
            (row['scope'],row['binding'],row['policy'],row['ticket'],row['requestDigest'],
             row['epoch'],row['instance'],row['brokerId'],row['routeFingerprint']), 'request_view_grant_mismatch')
    return claim


def _transition(ledger, ticket, expected, update, previous=None):
    require(type(ledger) is ExecutionLedger, 'request_view_owner_required')
    key = key_for(ledger.context, ticket)
    def tx(conn):
        require(not ledger._state(conn)['quarantined'], 'execution_budget_quarantined')
        found = conn.execute('SELECT value FROM state_meta WHERE key=?', (key,)).fetchone()
        require(found is not None, 'request_view_missing')
        row = validate(_load(found[0], MAX_RECORD_BYTES), ledger.context, ledger.policy)
        require(row['ticket'] == ticket and row['state'] == expected, 'request_view_transition_conflict')
        require((row['epoch'], row['instance']) == (ledger.context.epoch, ledger.context.instance_id),
                'stale_request_view_owner')
        require(previous is None or row == previous, 'request_view_changed')
        require(linked_claim(conn, ledger, row)['state'] == 'reserved', 'request_view_reserved_claim_required')
        result = seal(row | update)
        validate(result, ledger.context, ledger.policy)
        conn.execute('UPDATE state_meta SET value=? WHERE key=?', (_json(result), key))
        return result
    return ledger._write(tx)


def arm_handoff(ledger, ticket):
    """Write-ahead intent BEFORE IPC. Lost ACK may mean no socket was contacted."""
    return _transition(ledger, ticket, 'prepared', {'state':'handoff_armed'})


def observe_response(ledger, armed, raw, status, content_type):
    """Trusted broker client only, AFTER authenticated reply and bounded decoding.

    Persists observation before returning to provider response validation/settlement.
    No proof the SDK or model consumed anything, and no implicit retry on failure.
    """
    require(type(armed) is dict and type(raw) is bytes, 'request_view_invalid_response')
    frozen = _load(_json(armed), MAX_RECORD_BYTES)
    validate(frozen, ledger.context, ledger.policy)
    require(frozen['state'] == 'handoff_armed', 'request_view_transition_conflict')
    return _transition(ledger, frozen['ticket'], 'handoff_armed',
        {'state':'broker_response_observed', 'responseSha256':sha(raw), 'responseBytes':len(raw),
         'httpStatus':status, 'responseContentType':content_type}, previous=frozen)


def enrich_request_views(conn, section, context, policy):
    """Same authorized host-report snapshot. Profile requests != selected-run costs."""
    prefix = PREFIX + context.scope + '.'
    found = conn.execute('SELECT key,value FROM state_meta WHERE key GLOB ? ORDER BY key LIMIT 1001',
                         (prefix+'*',)).fetchall()
    if not found:
        return
    require(len(found) <= 1000, 'request_view_history_limit')
    from host_report import _NoWriteOwner
    ledger = ExecutionLedger(_NoWriteOwner(str(context.profile_home/'state.db')), context, policy)
    ledger._state(conn)
    selected = {item['captureId'][3:]:item for item in section.get('sourceCaptures', [])
                if item['matchedEvidenceId'] is not None}
    refmap = {item['evidenceId']:item for item in section['references']}
    candidate_signatures = ({digest:signature for signature,digests in _capture_candidates(conn,ledger).items()
                             for digest in digests} if selected else {})
    requests = []; assignments = {}; total = 0
    for key, raw in found:
        require(type(raw) is str)
        total += len(raw.encode('utf-8')); require(total <= MAX_HISTORY_BYTES, 'request_view_history_limit')
        row = validate(_load(raw, MAX_RECORD_BYTES), context, policy)
        require(key == key_for(context, row['ticket']))
        claim = linked_claim(conn, ledger, row)
        observed = row['state'] == 'broker_response_observed'
        validated = (observed and row['httpStatus'] == 200 and claim['state'] == 'settled'
                     and claim['outcome'] in ('response', 'unknown_usage'))
        if claim['state'] == 'settled':
            require(observed and ((row['httpStatus'] == 200 and claim['outcome'] in ('response','unknown_usage'))
                    or (row['httpStatus'] != 200 and claim['outcome'] == 'transport_error')),
                    'request_view_settlement_conflict')
        request_id = 'rv_' + row['digest']
        inclusions = []
        for item in row['toolMessages']:
            capture = selected.get(item['sourceCaptureDigest'])
            if capture is None:
                continue
            require((item['contentSha256'], item['contentBytes']) ==
                    (capture['returnedOutput']['sha256'], capture['returnedOutput']['utf8Bytes']),
                    'request_source_output_mismatch')
            eid = capture['matchedEvidenceId']; ref = refmap[eid]
            # Bind the persisted native tool identity again, not just equal text.
            require(candidate_signatures.get(item['sourceCaptureDigest']) ==
                    (item['toolCallHash'],item['contentSha256'],item['contentBytes']),
                    'request_source_identity_mismatch')
            require(ref['executionAttribution'] == 'isolated_return_bound_to_admission')
            inclusion = {'evidenceId':eid, 'captureId':capture['captureId'], 'messageIndex':item['index'],
                         'requestViewId':request_id, 'requestDigest':row['requestDigest'],
                         'contentSha256':item['contentSha256'],
                         'range':{'unit':'utf8_bytes','start':0,'end':item['contentBytes'],'endExclusive':True},
                         'coverageOfReturnedText':'complete', 'sourceFileCoverage':'not_inferred',
                         'preparationRecorded':True, 'handoffIntentRecorded':row['state'] != 'prepared',
                         'brokerHttpResponseObserved':observed, 'providerResponseValidated':validated,
                         'initiatingRunVerified':False, 'modelProcessingVerified':False,
                         'understandingVerified':False, 'grantsExecutionPermission':False}
            inclusions.append(inclusion); assignments.setdefault(eid, []).append(inclusion)
        requests.append({'requestViewId':request_id, 'requestDigest':row['requestDigest'],
                         'requestBytes':row['requestBytes'], 'serialization':'canonical_json_utf8',
                         'messageCount':row['messageCount'], 'toolMessageCount':len(row['toolMessages']),
                         'state':row['state'], 'httpStatus':row['httpStatus'],
                         'responseSha256':row['responseSha256'], 'responseBytes':row['responseBytes'],
                         'brokerHttpResponseObserved':observed, 'providerResponseValidated':validated,
                         'initiatingRunId':None, 'initiatingRunVerified':False,
                         'selectedEvidenceInclusions':inclusions, 'modelProcessingVerified':False})
    for eid, inclusions in assignments.items():
        refmap[eid]['providerRequestInclusions'] = inclusions
    section['providerRequestViews'] = {'version':1, 'inventoryScope':'profile_provider_requests',
        'requests':requests, 'selectedTaskCostAttribution':'not_proven', 'writesPerformed':False,
        'grantsExecutionPermission':False, 'modelProcessingVerified':False,
        'warnings':['handoff_intent_is_not_physical_send_proof',
                    'http_response_is_not_model_processing_or_downstream_delivery',
                    'source_provenance_does_not_identify_request_initiator']}
