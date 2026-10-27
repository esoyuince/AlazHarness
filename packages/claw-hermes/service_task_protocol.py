"""Bounded task envelopes for the existing owned service pipe.

This is a separate protocol, not a relaxation of lifecycle framing. A caller
can name only the existing authenticated task routes. No endpoint, executable,
native owner, queue, store or replacement credential is accepted here.
"""
from __future__ import annotations

import base64
import binascii
import json
import re

PREFIX = b'ALAZTASK/1 '
PROTOCOL = 'alaz-service-task-v1'
CLIENT_PROTOCOL = 'alaz-service-task-client-v1'
MAX_REQUEST_FRAME = 1_500_000
MAX_RESPONSE_FRAME = 5_700_000
MAX_REQUEST_BODY = 1_048_576
MAX_RESPONSE_BODY = 4_194_304
MAX_HEADERS = 8192
_HTTP_FIELDS = frozenset(('method', 'path', 'headers', 'bodyBase64',
                          'timeoutMs', 'maxResponseBytes'))
_REQUEST_HEADERS = frozenset(('authorization', 'accept', 'content-type',
    'idempotency-key', 'x-alaz-execution-version', 'x-alaz-provider-broker-version',
    'x-alaz-isolated-read-version'))
_VERSION_HEADERS = frozenset(name for name in _REQUEST_HEADERS if name.startswith('x-alaz-'))
_CODE = re.compile('[a-z][a-z0-9_]{0,95}')


class ServiceTaskProtocolRejected(RuntimeError):
    """Only fixed diagnostics; never include the supplied private data."""


def require(value, reason):
    if not value:
        raise ServiceTaskProtocolRejected(reason)


def _copy(value):
    return json.loads(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                ensure_ascii=True, allow_nan=False))


def _bounded(value, minimum, maximum, reason):
    require(type(value) is int and minimum <= value <= maximum, reason)
    return value


def body_bytes(value, maximum):
    """Bound before allocation and require one canonical RFC4648 spelling."""
    require(type(value) is str and len(value) <= 4 * ((maximum + 2) // 3),
            'service_task_body_bound')
    try:
        raw = base64.b64decode(value.encode('ascii'), validate=True)
    except (ValueError, UnicodeError, binascii.Error):
        raise ServiceTaskProtocolRejected('service_task_body_encoding') from None
    require(len(raw) <= maximum, 'service_task_body_bound')
    require(base64.b64encode(raw).decode('ascii') == value,
            'service_task_body_encoding')
    return raw


def _headers(headers, allowed):
    require(type(headers) is dict and all(type(name) is str and name in allowed
            for name in headers), 'service_task_header_fields')
    require(all(type(value) is str and re.fullmatch(r'[\x20-\x7e]*', value) is not None
                for value in headers.values()), 'service_task_header_value')
    require(sum(len(name) + len(value) + 4 for name, value in headers.items())
            <= MAX_HEADERS, 'service_task_headers_bound')


def validate_http_request(value):
    require(type(value) is dict and set(value) == _HTTP_FIELDS,
            'service_task_http_request_fields')
    method, path, headers = value['method'], value['path'], value['headers']
    require(type(method) is str and type(path) is str,
            'service_task_route')
    allowed = ((method, path) in {
        ('GET', '/alaz/host/v1/capabilities'),
        ('POST', '/alaz/host/v1/intents'),
        ('POST', '/alaz/host/v1/dispatch'),
    } or method == 'GET' and re.fullmatch(
        r'(?:/alaz/host/v1/requests/[a-f0-9]{32}|/v1/runs/run_[a-f0-9]{32})', path)
        is not None or method == 'POST' and re.fullmatch(
        r'/v1/runs/run_[a-f0-9]{32}/stop', path) is not None)
    require(allowed, 'service_task_route')
    _headers(headers, _REQUEST_HEADERS)
    token = headers.get('authorization')
    require(type(token) is str and re.fullmatch(r'Bearer [\x21-\x7e]{1,4096}', token)
            is not None, 'service_task_authorization')
    require(headers.get('accept') == 'application/json', 'service_task_accept')
    require(all(headers[name] == '1' for name in _VERSION_HEADERS if name in headers),
            'service_task_requirement_version')
    if 'idempotency-key' in headers:
        require(re.fullmatch(r'[\x21-\x7e]{1,255}', headers['idempotency-key']) is not None,
                'service_task_idempotency_key')
    raw = body_bytes(value['bodyBase64'], MAX_REQUEST_BODY)
    if method == 'GET':
        require(not raw and 'content-type' not in headers, 'service_task_get_body')
    else:
        require(headers.get('content-type') == 'application/json', 'service_task_content_type')
    _bounded(value['timeoutMs'], 10, 60_000, 'service_task_timeout')
    _bounded(value['maxResponseBytes'], 128, MAX_RESPONSE_BODY, 'service_task_response_limit')
    return _copy(value)


def validate_http_response(value, *, max_response_bytes=MAX_RESPONSE_BODY):
    _bounded(max_response_bytes, 128, MAX_RESPONSE_BODY, 'service_task_response_limit')
    require(type(value) is dict and set(value) == {'status', 'headers', 'bodyBase64'},
            'service_task_http_response_fields')
    _bounded(value['status'], 200, 599, 'service_task_http_status')
    headers = value['headers']
    _headers(headers, frozenset(('content-type', 'content-length')))
    if 'content-type' in headers:
        require(0 < len(headers['content-type']) <= 255, 'service_task_response_content_type')
    raw = body_bytes(value['bodyBase64'], max_response_bytes)
    if 'content-length' in headers:
        size = headers['content-length']
        require(re.fullmatch(r'0|[1-9][0-9]{0,9}', size) is not None
                and int(size) == len(raw), 'service_task_response_content_length')
    return _copy(value)


def _identity(value, service_id):
    # Lazy import keeps lifecycle framing independent of this module at import.
    import gateway_service_control as lifecycle
    sid = value['serviceId']
    try:
        expected = lifecycle.request_id(sid, value['sequence'])
    except lifecycle.ServiceControlRejected:
        raise ServiceTaskProtocolRejected('service_task_request_identity') from None
    require(service_id is None or sid == service_id, 'service_task_other_service')
    require(type(value['requestId']) is str and value['requestId'] == expected,
            'service_task_request_binding')


def validate_command(value, *, service_id=None):
    require(type(value) is dict and set(value) == {'protocol', 'serviceId',
            'sequence', 'requestId', 'action', 'http'}, 'service_task_command_fields')
    require(value['protocol'] == PROTOCOL and value['action'] == 'http',
            'service_task_command_protocol')
    _identity(value, service_id)
    http = validate_http_request(value['http'])
    return _copy({**value, 'http': http})


def validate_reply(value, *, service_id=None, identity=None,
                   max_response_bytes=MAX_RESPONSE_BODY):
    require(type(value) is dict and set(value) == {'protocol', 'type', 'serviceId',
            'sequence', 'requestId', 'owner', 'response', 'error'}, 'service_task_reply_fields')
    require(value['protocol'] == PROTOCOL and value['type'] == 'task-reply',
            'service_task_reply_protocol')
    _identity(value, service_id)
    import gateway_service_control as lifecycle
    try:
        owner = lifecycle.validate_owner(value['owner'], identity=identity)
    except lifecycle.ServiceControlRejected:
        raise ServiceTaskProtocolRejected('service_task_reply_owner') from None
    require(owner['state'] in ('READY', 'DRAINING', 'UNKNOWN'),
            'service_task_reply_owner_state')
    response, error = value['response'], value['error']
    require((response is None) != (error is None), 'service_task_reply_outcome')
    if response is not None:
        response = validate_http_response(response, max_response_bytes=max_response_bytes)
    else:
        require(type(error) is str and _CODE.fullmatch(error) is not None,
                'service_task_reply_error')
    return _copy({**value, 'owner': owner, 'response': response})


def encode(value, *, reply=False, sorted_keys=True):
    require(type(reply) is bool and type(sorted_keys) is bool, 'service_task_encoding_options')
    try:
        raw = json.dumps(value, sort_keys=sorted_keys, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ServiceTaskProtocolRejected('service_task_frame_invalid') from None
    frame = PREFIX + raw + b'\n'
    require(len(frame) <= (MAX_RESPONSE_FRAME if reply else MAX_REQUEST_FRAME),
            'service_task_frame_bound')
    return frame


def decode(raw, *, reply=False, sorted_keys=True):
    require(type(reply) is bool and type(sorted_keys) is bool, 'service_task_encoding_options')
    require(type(raw) is bytes and len(PREFIX) + 3 <= len(raw)
            <= (MAX_RESPONSE_FRAME if reply else MAX_REQUEST_FRAME)
            and raw.startswith(PREFIX) and raw.endswith(b'\n')
            and b'\n' not in raw[:-1], 'service_task_frame_bound')
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'service_task_duplicate_field')
            value[key] = item
        return value
    try:
        value = json.loads(raw[len(PREFIX):-1].decode('ascii'), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        require(type(value) is dict and encode(value, reply=reply, sorted_keys=sorted_keys) == raw,
                'service_task_frame_not_canonical')
        return value
    except ServiceTaskProtocolRejected:
        raise
    except (ValueError, UnicodeError, TypeError, OverflowError, RecursionError):
        raise ServiceTaskProtocolRejected('service_task_frame_invalid') from None
