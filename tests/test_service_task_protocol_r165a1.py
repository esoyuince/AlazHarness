"""Task wire scope, hostile envelopes and independent lifecycle limits."""
import base64
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_service_control as lifecycle
import service_task_protocol as task
from test_service_child_control_r160a1 import owner_receipt

SID = 'a' * 32


def http_request(method='GET', path='/alaz/host/v1/capabilities', body=b''):
    headers = {'authorization': 'Bearer ' + 't' * 40, 'accept': 'application/json'}
    if method == 'POST':
        headers['content-type'] = 'application/json'
    return {'method': method, 'path': path, 'headers': headers,
        'bodyBase64': base64.b64encode(body).decode('ascii'), 'timeoutMs': 1000,
        'maxResponseBytes': 1048576}


def task_command(sequence=1, http=None):
    return {'protocol': task.PROTOCOL, 'serviceId': SID, 'sequence': sequence,
        'requestId': lifecycle.request_id(SID, sequence), 'action': 'http',
        'http': http_request() if http is None else http}


def http_response(raw=b'{"ok":true}', status=200):
    return {'status': status, 'headers': {'content-type': 'application/json',
        'content-length': str(len(raw))}, 'bodyBase64': base64.b64encode(raw).decode('ascii')}


def task_reply(sequence=1, *, response=None, error=None, state='READY'):
    if response is None and error is None:
        response = http_response()
    return {'protocol': task.PROTOCOL, 'type': 'task-reply', 'serviceId': SID,
        'sequence': sequence, 'requestId': lifecycle.request_id(SID, sequence),
        'owner': owner_receipt(state), 'response': response, 'error': error}


class TaskProtocolTests(unittest.TestCase):
    def test_six_narrow_routes_accept_and_return_detached_values(self):
        paths = [('GET', '/alaz/host/v1/capabilities'), ('POST', '/alaz/host/v1/intents'),
            ('POST', '/alaz/host/v1/dispatch'),
            ('GET', '/alaz/host/v1/requests/' + 'b' * 32),
            ('GET', '/v1/runs/run_' + 'b' * 32),
            ('POST', '/v1/runs/run_' + 'b' * 32 + '/stop')]
        for method, path in paths:
            value = http_request(method, path)
            result = task.validate_http_request(value)
            self.assertEqual(result, value)
            result['headers']['authorization'] = 'changed'
            self.assertNotEqual(result, value)

    def test_arbitrary_destinations_raw_start_provider_and_ambiguous_paths_refused(self):
        changes = [('/v1/runs', 'POST'), ('/alaz/provider/v1/chat/completions', 'POST'),
            ('http://127.0.0.1:9999/alaz/host/v1/capabilities', 'GET'),
            ('//other/alaz/host/v1/capabilities', 'GET'),
            ('/alaz/host/v1/capabilities?x=1', 'GET'),
            ('/alaz/host/v1/%63apabilities', 'GET'),
            ('/alaz/host/v1/capabilities#x', 'GET'),
            ('/alaz/host/v1/capabilities/../dispatch', 'GET'),
            ('/alaz/host/v1/capabilities', 'DELETE'),
            ('/alaz/host/v1/requests/' + 'A' * 32, 'GET')]
        for path, method in changes:
            with self.subTest(path=path, method=method), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_http_request(http_request(method, path))

    def test_authentication_and_header_injection_are_not_normalized_or_replaced(self):
        changes = [{'authorization': None}, {'authorization': 'Bearer t\r\nHost: evil'},
            {'authorization': 'Bearer '}, {'authorization': 'Bearer ' + 'x' * 4097},
            {'authorization': 'bearer token'}, {'Authorization': 'Bearer token'},
            {'host': '127.0.0.1'}, {'cookie': 'private'}, {'connection': 'upgrade'},
            {'accept': '*/*'}, {'x-alaz-execution-version': '2'},
            {'idempotency-key': 'contains space'}, {'content-type': 'application/json'}]
        for change in changes:
            value = http_request();value['headers'].update(change)
            with self.subTest(change=change), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_http_request(value)
        value = http_request();value['headers']['authorization'] = 'Bearer ' + 'x' * 4096
        task.validate_http_request(value)

    def test_body_encoding_and_decoded_size_are_strict(self):
        value = http_request('POST', '/alaz/host/v1/intents', b'x' * task.MAX_REQUEST_BODY)
        task.validate_http_request(value)
        for encoded in ('AA==\n', 'AA', 'AB==', '====', 'é',
                        base64.b64encode(b'x' * (task.MAX_REQUEST_BODY + 1)).decode('ascii')):
            with self.subTest(encoded=encoded[:10]), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_http_request({**value, 'bodyBase64': encoded})
        with self.assertRaises(task.ServiceTaskProtocolRejected):
            task.validate_http_request(http_request(body=b'x'))

    def test_no_boolean_timeout_limit_or_extra_request_fields(self):
        for change in ({'timeoutMs': True}, {'timeoutMs': 9}, {'timeoutMs': 60001},
                       {'maxResponseBytes': False}, {'maxResponseBytes': 127},
                       {'maxResponseBytes': task.MAX_RESPONSE_BODY + 1}, {'origin': 'http://evil'}):
            with self.subTest(change=change), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_http_request(http_request() | change)

    def test_response_bounds_headers_and_actual_length_preserved(self):
        value = http_response(b'x' * 128, status=401)
        self.assertEqual(task.validate_http_response(value, max_response_bytes=128), value)
        broken = [value | {'status': True}, value | {'status': 101}, value | {'status': 600},
            value | {'headers': {'content-length': '0128'}},
            value | {'headers': {'content-length': '129'}},
            value | {'headers': {'set-cookie': 'secret'}},
            value | {'headers': {'content-type': 'x' * 256}}]
        for row in broken:
            with self.subTest(row=row), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_http_response(row)
        with self.assertRaises(task.ServiceTaskProtocolRejected):
            task.validate_http_response(http_response(b'x' * 129), max_response_bytes=128)

    def test_command_and_reply_bind_shared_sequence_original_owner_and_outcome(self):
        command = task_command()
        self.assertEqual(task.validate_command(command, service_id=SID), command)
        for change in ({'sequence': 2}, {'serviceId': 'b' * 32}, {'action': 'status'}, {'extra': 1}):
            with self.subTest(change=change), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_command(command | change, service_id=SID)
        reply = task_reply()
        identity = tuple(reply['owner'][name] for name in ('pid', 'epoch', 'instanceId'))
        task.validate_reply(reply, service_id=SID, identity=identity)
        bad = [reply | {'response': None}, reply | {'error': 'unknown'},
               reply | {'owner': reply['owner'] | {'epoch': 3}},
               task_reply(error='secret payload included'), task_reply(state='CLOSED')]
        for value in bad:
            with self.assertRaises(task.ServiceTaskProtocolRejected):
                task.validate_reply(value, service_id=SID, identity=identity)

    def test_prefix_canonical_ascii_and_duplicate_field_checks(self):
        value = task_command();raw = task.encode(value)
        self.assertEqual(task.decode(raw), value)
        node = task.encode(value, sorted_keys=False)
        self.assertEqual(task.decode(node, sorted_keys=False), value)
        bad = [raw[len(task.PREFIX):], raw[:-1], raw + b'\n',
               task.PREFIX + b'{"x":1,"x":2}\n', task.PREFIX + b'{"x":NaN}\n',
               task.PREFIX + b'{ "x":1}\n', task.PREFIX + b'{"x":"\xff"}\n']
        for value in bad:
            with self.subTest(raw=value[:40]), self.assertRaises(task.ServiceTaskProtocolRejected):
                task.decode(value)

    def test_large_task_frames_do_not_widen_legacy_lifecycle_decoder(self):
        value = task_command(http=http_request('POST', '/alaz/host/v1/intents', b'x' * 70000))
        raw = task.encode(value)
        self.assertGreater(len(raw), lifecycle.MAX_FRAME)
        self.assertEqual(task.decode(raw), value)
        with self.assertRaises(lifecycle.ServiceControlRejected):
            lifecycle.decode(raw[:-1])
        with self.assertRaises(task.ServiceTaskProtocolRejected):
            task.decode(task.PREFIX + b'x' * task.MAX_REQUEST_FRAME + b'\n')


if __name__ == '__main__':
    unittest.main()
