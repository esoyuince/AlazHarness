"""One bounded actual HTTP exchange inside the original service namespace.

The destination is the original owner's loopback listener. This module forwards
the supplied API credential and never substitutes authority, calls handlers
directly, retries a mutation, starts a worker, or creates persistent HTTP state.
"""
from __future__ import annotations

import asyncio
import base64
import re

from gateway_service_runtime import BorrowedServiceOwner
import service_task_protocol as task


class ServiceTaskHTTPRejected(RuntimeError):
    pass


def require(value, reason):
    if not value:
        raise ServiceTaskHTTPRejected(reason)


def _binding(service):
    require(type(service) is BorrowedServiceOwner, 'service_task_original_owner_required')
    service._actor_check(loop=True)
    observed = service.status()
    require(observed['state'] in ('READY', 'DRAINING'), 'service_task_owner_unavailable')
    endpoint = observed['endpoint']
    match = re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})', endpoint) if type(endpoint) is str else None
    require(match is not None and 1 <= int(match[1]) <= 65535
            and endpoint == service._endpoint, 'service_task_owner_endpoint')
    consumer, transport, app = service._consumer, service._transport, service._app
    service.require_execution(transport=transport, app=app, adapter=consumer._adapter)
    return endpoint, consumer, transport, app, observed['pid'], observed['epoch'], observed['instanceId']


async def exchange(service, http):
    """Return a typed HTTP outcome; ownership failures still fail closed.

An uncertain POST outcome is not a lifecycle failure. Its original native
request can subsequently be queried through another authenticated GET. Native
admission continues to decide whether an intent/dispatch is allowed in DRAINING.
"""
    http = task.validate_http_request(http)
    binding = _binding(service)
    endpoint = binding[0]
    # Import only when the actual exchange is requested, after owner checks.
    import aiohttp
    body = task.body_bytes(http['bodyBase64'], task.MAX_REQUEST_BODY)
    limit = http['maxResponseBytes']
    result = None
    try:
        async with asyncio.timeout(http['timeoutMs'] / 1000):
            timeout = aiohttp.ClientTimeout(total=http['timeoutMs'] / 1000)
            connector = aiohttp.TCPConnector(limit=1, force_close=True, use_dns_cache=False)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout,
                    trust_env=False, auto_decompress=False,
                    skip_auto_headers={'User-Agent', 'Accept-Encoding'}) as session:
                async with session.request(http['method'], endpoint + http['path'],
                        headers=http['headers'], data=body if http['method'] == 'POST' else None,
                        allow_redirects=False) as response:
                    require(response.headers.get('content-encoding', 'identity').lower() == 'identity',
                            'service_task_response_encoding')
                    headers = {}
                    for name in ('content-type', 'content-length'):
                        values = response.headers.getall(name, [])
                        require(len(values) <= 1, 'service_task_response_headers')
                        if values:
                            headers[name] = values[0]
                    length = headers.get('content-length')
                    require(length is None or re.fullmatch(r'0|[1-9][0-9]{0,9}', length)
                            is not None and int(length) <= limit, 'service_task_response_bound')
                    chunks = bytearray()
                    async for chunk in response.content.iter_chunked(16384):
                        require(len(chunks) + len(chunk) <= limit, 'service_task_response_bound')
                        chunks.extend(chunk)
                    result = task.validate_http_response({'status': response.status,
                        'headers': headers, 'bodyBase64': base64.b64encode(chunks).decode('ascii')},
                        max_response_bytes=limit)
        outcome = {'response': result, 'error': None}
    except (TimeoutError, OSError, aiohttp.ClientError):
        outcome = {'response': None, 'error': 'service_task_http_outcome_unknown'}
    except ServiceTaskHTTPRejected as exc:
        # Only our fixed refusal codes are exposed; never foreign exception text.
        outcome = {'response': None, 'error': str(exc)}
    except task.ServiceTaskProtocolRejected:
        outcome = {'response': None, 'error': 'service_task_http_response_invalid'}
    # Awaited HTTP work must not replace the original runtime while in flight.
    after = _binding(service)
    require(after[0] == binding[0] and after[4:] == binding[4:]
            and all(left is right for left, right in zip(after[1:4], binding[1:4])),
            'service_task_owner_changed_during_exchange')
    return outcome
