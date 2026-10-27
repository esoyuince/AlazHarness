"""Strict host-side envelopes for the original supervisor's task transport.

The envelope authorizes neither a native task nor a destination. Its owner
identity is checked before the original child's authenticated API is reached.
Request bodies and API credentials are never returned in control diagnostics.
"""
from __future__ import annotations

import hashlib
import re

import service_task_protocol as wire

PROTOCOL = 'alaz-service-task-client-v1'
MAX_MUTATIONS = 4096
_ID = re.compile('[a-f0-9]{32}')
_CODE = re.compile('[a-z][a-z0-9_]{0,95}')


class ServiceTaskServerRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceTaskServerRejected(reason)


def owner_identity(value):
    require(type(value) is dict and set(value) == {'pid', 'startTicks', 'token'},
            'service_task_owner_fields')
    require(type(value['pid']) is int and 0 < value['pid'] < 2**31
            and type(value['startTicks']) is int and 0 < value['startTicks'] <= 2**53 - 1
            and type(value['token']) is str and _ID.fullmatch(value['token']) is not None,
            'service_task_owner_identity')
    return dict(value)


def validate_request(value):
    require(type(value) is dict and set(value) ==
            {'protocol', 'requestId', 'serviceId', 'expectedOwner', 'http'},
            'service_task_client_fields')
    require(value['protocol'] == PROTOCOL, 'service_task_client_protocol')
    for name in ('requestId', 'serviceId'):
        require(type(value[name]) is str and _ID.fullmatch(value[name]) is not None,
                'service_task_client_identity')
    return {**value, 'expectedOwner': owner_identity(value['expectedOwner']),
            'http': wire.validate_http_request(value['http'])}


def decode_request(raw):
    return validate_request(wire.decode(raw, sorted_keys=False))


def fingerprint(request):
    """Only bounded replay metadata survives a completed HTTP exchange."""
    import json
    http = validate_request(request)['http']
    raw = json.dumps(http, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('ascii')
    return hashlib.sha256(raw).hexdigest()


def reply(request, owner, *, response=None, error=None):
    request = validate_request(request)
    owner = owner_identity(owner)
    require(owner == request['expectedOwner'], 'service_task_reply_owner')
    require((response is None) != (error is None), 'service_task_reply_outcome')
    if response is not None:
        response = wire.validate_http_response(response,
            max_response_bytes=request['http']['maxResponseBytes'])
    else:
        require(type(error) is str and _CODE.fullmatch(error) is not None
                and owner['token'] not in error, 'service_task_reply_error')
    return {'protocol': PROTOCOL, 'requestId': request['requestId'],
            'serviceId': request['serviceId'], 'owner': owner, 'response': response,
            'error': error, 'retryAllowed': False}
