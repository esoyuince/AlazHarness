"""Real private Unix task envelopes; native HTTP/privileged ports are doubles.

The existing server, peer credentials, EOF, deadlines and original child pipes
are exercised. These tests do not claim an installed service, kernel or model.
"""
import base64
import copy
import json
import os
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import service_control_server as server
import service_task_protocol as wire
import service_task_server as task
import test_service_control_server_r163a1 as legacy
from test_service_task_protocol_r165a1 import http_request, http_response

SID = 'a' * 32
RID = 'b' * 32
OWNER, UNIX = legacy.OWNER, legacy.UNIX


def request(*, owner=None, request_id=RID, http=None):
    return {'protocol': task.PROTOCOL, 'requestId': request_id, 'serviceId': SID,
            'expectedOwner': dict(OWNER if owner is None else owner),
            'http': http_request() if http is None else http}


def frame(value):
    return wire.PREFIX + json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode() + b'\n'


class TaskServerSchemaTests(unittest.TestCase):
    def test_host_schema_and_compact_noncanonical_key_order_are_explicit(self):
        value = request(owner={'token': OWNER['token'], 'startTicks': 5678, 'pid': 1234})
        self.assertEqual(task.decode_request(frame(value)), value)
        parsed = task.decode_request(frame(value))
        parsed['http']['headers']['authorization'] = 'Bearer replaced'
        self.assertNotEqual(parsed, value)

    def test_extensions_and_wrong_owner_types_are_rejected(self):
        for key in request():
            value = request(); del value[key]
            with self.subTest(key=key), self.assertRaises(task.ServiceTaskServerRejected):
                task.validate_request(value)
        for change in ({'command': 'exec'}, {'protocol': server.PROTOCOL},
                       {'serviceId': 'A' * 32}, {'requestId': True}):
            with self.assertRaises(task.ServiceTaskServerRejected):
                task.validate_request(request() | change)
        for key in ('pid', 'startTicks'):
            value = request(); value['expectedOwner'][key] = True
            with self.assertRaises(task.ServiceTaskServerRejected):
                task.validate_request(value)

    def test_duplicate_fields_prefix_eof_and_noncompact_payload_are_refused(self):
        raw = frame(request())
        invalid = [raw[:-1], raw + raw, b' ' + raw, raw.replace(b'"pid":1234', b'"pid":1234,"pid":1234'),
                   raw.replace(b'"pid":1234', b'"pid": 1234'), raw.replace(b'"pid":1234', b'"pid":NaN')]
        for value in invalid:
            with self.subTest(value=value[:40]), self.assertRaises(wire.ServiceTaskProtocolRejected):
                task.decode_request(value)

    def test_task_body_larger_than_lifecycle_limit_preserves_full_bytes(self):
        raw = json.dumps({'input': '\x01' * 65536}, separators=(',', ':')).encode()
        body = request(http=http_request('POST', '/alaz/host/v1/intents', raw))
        encoded = frame(body)
        self.assertGreater(len(encoded), server.MAX_FRAME)
        self.assertEqual(base64.b64decode(task.decode_request(encoded)['http']['bodyBase64']), raw)
        with self.assertRaises(server.ServiceControlServerRejected):
            server.decode_request(encoded)

    def test_reply_binds_owner_and_forwards_bounded_http_error(self):
        req = request(); response = http_response(b'{"error":"native_auth"}', status=401)
        value = task.reply(req, OWNER, response=response)
        self.assertEqual(value['response'], response)
        self.assertFalse(value['retryAllowed'])
        with self.assertRaises(task.ServiceTaskServerRejected):
            task.reply(req, OWNER | {'pid': 9}, response=response)
        with self.assertRaises(task.ServiceTaskServerRejected):
            task.reply(req, OWNER, response=response, error='both')
        with self.assertRaises(task.ServiceTaskServerRejected):
            task.reply(req, OWNER, error='secret body\n')


@unittest.skipUnless(UNIX, 'Linux Unix sockets and peer credentials required')
class TaskUnixServerTests(unittest.TestCase):
    setUp = legacy.ServerTests.setUp
    _close_listeners = legacy.ServerTests._close_listeners
    make = legacy.ServerTests.make
    body = legacy.ServerTests.body
    start = legacy.ServerTests.start

    def exchange(self, instance, value, *, eof=True, disconnect=False, pieces=None):
        if type(value) is dict:
            raw = frame(value) if value.get('protocol') == task.PROTOCOL else server._compact(value) + b'\n'
        else:
            raw = value
        result = {'data': b'', 'error': None}
        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                    peer.settimeout(4)
                    peer.connect(str(instance._path))
                    for part in pieces if pieces is not None else (raw,):
                        peer.sendall(part)
                    if eof:
                        peer.shutdown(socket.SHUT_WR)
                    if disconnect:
                        return
                    chunks = []
                    while True:
                        data = peer.recv(65536)
                        if not data:
                            break
                        chunks.append(data)
                    result['data'] = b''.join(chunks)
            except OSError as exc:
                result['error'] = type(exc).__name__
        thread = threading.Thread(target=client, daemon=True)
        thread.start()
        diagnostic = instance.serve_one(timeout=2)
        thread.join(5)
        self.assertFalse(thread.is_alive())
        raw_reply = result['data']
        value = (wire.decode(raw_reply, reply=True) if raw_reply.startswith(wire.PREFIX)
                 else json.loads(raw_reply) if raw_reply else None)
        return value, diagnostic, result

    def task_body(self, instance, *, http=None, request_id=RID):
        return request(owner=instance.connection()['owner'], http=http, request_id=request_id)

    def test_real_unix_route_headers_and_error_status_reach_original_volume(self):
        instance = self.make(); self.start(instance)
        body = self.task_body(instance)
        expected = http_response(b'{"error":"bad_token"}', status=401)
        with patch.object(type(self.harness.volume), 'task_service', autospec=True,
                          return_value={'response': expected, 'error': None}) as forward:
            reply, diagnostic, _ = self.exchange(instance, body)
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(reply['response'], expected)
        forward.assert_called_once_with(self.harness.volume, body['http'], timeout=2)
        self.assertEqual(instance._view['state'], 'READY')
        self.assertEqual(instance._task_mutations, {})

    def test_owner_mismatch_and_route_escape_refused_before_forwarding(self):
        instance = self.make(); self.start(instance)
        with patch.object(type(self.harness.volume), 'task_service') as forward:
            variants = []
            for key, value in [('pid', os.getpid() + 1), ('startTicks', 101), ('token', 'e' * 32)]:
                body = self.task_body(instance); body['expectedOwner'][key] = value; variants.append(body)
            body = self.task_body(instance); body['serviceId'] = 'e' * 32; variants.append(body)
            for path in ['/v1/runs', '/alaz/provider/v1/call', '/v1/runs/run_' + 'a' * 32 + '?x=1']:
                body = self.task_body(instance); body['http']['path'] = path; variants.append(body)
            for body in variants:
                reply, diagnostic, _ = self.exchange(instance, body)
                self.assertIsNone(reply)
                self.assertFalse(diagnostic['requestDispatched'])
            forward.assert_not_called()
        self.assertEqual(instance._view['state'], 'READY')

    def test_task_requires_complete_write_eof_and_has_no_early_effect(self):
        instance = self.make(request_seconds=.03); self.start(instance)
        with patch.object(type(self.harness.volume), 'task_service') as forward:
            reply, diagnostic, _ = self.exchange(instance, self.task_body(instance), eof=False)
            self.assertIsNone(reply)
            self.assertEqual(diagnostic['reason'], 'service_server_connection_timeout')
            forward.assert_not_called()

    def test_duplicate_write_id_cannot_forward_again_and_conflict_is_bounded(self):
        instance = self.make(); self.start(instance)
        http = http_request('POST', '/alaz/host/v1/intents', b'{}')
        body = self.task_body(instance, http=http)
        result = {'response': http_response(b'{}', status=201), 'error': None}
        with patch.object(type(self.harness.volume), 'task_service', return_value=result) as forward:
            first, _, _ = self.exchange(instance, body)
            second, _, _ = self.exchange(instance, body)
            third, _, _ = self.exchange(instance, self.task_body(instance))
        self.assertEqual(first['response']['status'], 201)
        self.assertEqual(second['error'], 'service_task_exchange_already_attempted')
        self.assertEqual(third['error'], 'service_task_exchange_conflict')
        self.assertEqual(forward.call_count, 1)
        self.assertEqual(len(instance._task_mutations), 1)
        self.assertNotIn('Bearer', repr(instance._task_mutations))

    def test_write_capacity_does_not_disable_readonly_recovery(self):
        instance = self.make(max_task_mutations=1); self.start(instance)
        http = http_request('POST', '/alaz/host/v1/intents', b'{}')
        with patch.object(type(self.harness.volume), 'task_service',
                          return_value={'response': http_response(), 'error': None}) as forward:
            self.exchange(instance, self.task_body(instance, http=http))
            denied, _, _ = self.exchange(instance, self.task_body(instance, http=http, request_id='c' * 32))
            read, _, _ = self.exchange(instance, self.task_body(instance, request_id='d' * 32))
        self.assertEqual(denied['error'], 'service_task_exchange_capacity')
        self.assertIsNone(read['error'])
        self.assertEqual(forward.call_count, 2)

    def test_typed_http_uncertainty_preserves_lifecycle_and_native_lookup_path(self):
        instance = self.make(); self.start(instance)
        body = self.task_body(instance, http=http_request('POST', '/alaz/host/v1/dispatch', b'{}'))
        body['http']['headers']['idempotency-key'] = 'ah1-' + 'a' * 32 + '-' + 'b' * 32
        with patch.object(type(self.harness.volume), 'task_service',
                          side_effect=[{'response': None, 'error': 'service_task_http_unknown'},
                                       {'response': http_response(), 'error': None}]) as forward:
            unknown, _, _ = self.exchange(instance, body)
            lookup = self.task_body(instance, request_id='c' * 32,
                http=http_request(path='/alaz/host/v1/requests/' + 'b' * 32))
            recovered, _, _ = self.exchange(instance, lookup)
        self.assertEqual(unknown['error'], 'service_task_http_unknown')
        self.assertIsNone(recovered['error'])
        self.assertEqual(forward.call_count, 2)
        self.assertEqual(instance._view['state'], 'READY')

    def test_lost_task_reply_keeps_ready_and_never_repeats_the_write(self):
        instance = self.make(); self.start(instance)
        body = self.task_body(instance, http=http_request('POST', '/alaz/host/v1/intents', b'{}'))
        with patch.object(type(self.harness.volume), 'task_service',
                          return_value={'response': http_response(b'{}', status=201), 'error': None}) as forward:
            with patch.object(instance, '_write', side_effect=BrokenPipeError('not logged')):
                reply, diagnostic, _ = self.exchange(instance, body)
            again, _, _ = self.exchange(instance, body)
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertEqual(instance._view['state'], 'READY')
        self.assertEqual(again['error'], 'service_task_exchange_already_attempted')
        self.assertEqual(forward.call_count, 1)

    def test_large_task_request_and_response_do_not_change_lifecycle_bound(self):
        instance = self.make(request_seconds=2, response_seconds=2); self.start(instance)
        raw = json.dumps({'input': '\x01' * 65536}, separators=(',', ':')).encode()
        body = self.task_body(instance, http=http_request('POST', '/alaz/host/v1/intents', raw))
        body['http']['maxResponseBytes'] = 4194304
        response = http_response(b'x' * 1100000)
        with patch.object(type(self.harness.volume), 'task_service',
                          return_value={'response': response, 'error': None}) as forward:
            reply, diagnostic, _ = self.exchange(instance, body)
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(base64.b64decode(reply['response']['bodyBase64']), b'x' * 1100000)
        self.assertEqual(forward.call_args.args[0]['bodyBase64'], body['http']['bodyBase64'])
        self.assertEqual(server.MAX_FRAME, 65536)

    def test_task_before_service_start_has_no_native_effect(self):
        instance = self.make()
        with patch.object(type(self.harness.volume), 'task_service') as forward:
            reply, diagnostic, _ = self.exchange(instance, self.task_body(instance))
        self.assertEqual(reply['error'], 'service_task_service_unavailable')
        self.assertFalse(diagnostic['requestDispatched'])
        forward.assert_not_called()


if __name__ == '__main__':
    unittest.main()
