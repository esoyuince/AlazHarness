"""Actual loopback HTTP/authorization fixtures and original child control.

The native service owner/HTTP handlers are explicit doubles. These tests do not
qualify native stores, an installed projected service, kernel isolation or a
real provider/model. HTTP framing and client resource lifetimes are real.
"""
import asyncio
import base64
import copy
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_service_control as control
import service_task_http as relay
import service_task_protocol as task
from gateway_service_runtime import BorrowedServiceOwner
import test_service_child_control_r160a1 as prior
from test_service_task_protocol_r165a1 import http_request, http_response, task_command

try:
    from aiohttp import web
except ImportError:
    web = None


class TaskControlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.f = prior.ServiceDouble()
        self.driver = control.ServiceControl(self.f.service, prior.SID)
        await self.driver.start(object(), object())

    async def test_http_reply_then_lifecycle_share_one_sequence_and_original_owner(self):
        response = http_response()
        with patch.object(relay, 'exchange', AsyncMock(return_value={'response': response, 'error': None})) as call:
            reply = await self.driver.handle(task_command())
            self.assertEqual(reply['type'], 'task-reply')
            self.assertEqual(reply['response'], response)
            self.assertEqual(reply['owner'], self.f.value)
            self.assertEqual(await self.driver.handle(task_command()), reply)
            self.assertEqual(call.await_count, 1)
            self.assertIs(call.call_args.args[0], self.f.service)
        status = await self.driver.handle(prior.command(2))
        self.assertEqual(status['sequence'], 2)
        self.assertEqual(status['owner']['state'], 'READY')
        self.assertNotIn('response', status)
        self.assertFalse(self.driver._fenced)

    async def test_uncertain_http_preserves_lifecycle_and_original_request_query(self):
        results = [{'response': None, 'error': 'service_task_http_outcome_unknown'},
                   {'response': http_response(), 'error': None}]
        with patch.object(relay, 'exchange', AsyncMock(side_effect=results)) as call:
            first = task_command(http=http_request('POST', '/alaz/host/v1/dispatch', b'{}'))
            unknown = await self.driver.handle(first)
            self.assertEqual(unknown['error'], 'service_task_http_outcome_unknown')
            self.assertFalse(self.driver._fenced)
            query = task_command(2, http_request(path='/alaz/host/v1/requests/' + 'b' * 32))
            reply = await self.driver.handle(query)
            self.assertIsNone(reply['error'])
            self.assertEqual(call.await_count, 2)
        self.assertEqual(self.f.calls, ['start'])
        self.assertEqual((await self.driver.handle(prior.command(3, 'close')))['type'], 'final')

    async def test_conflicting_task_does_not_replace_original_attempt(self):
        with patch.object(relay, 'exchange', AsyncMock(return_value={'response': http_response(), 'error': None})) as call:
            await self.driver.handle(task_command())
            changed = task_command(http=http_request(path='/v1/runs/run_' + 'b' * 32))
            with self.assertRaisesRegex(control.ServiceControlRejected, 'request_conflict'):
                await self.driver.handle(changed)
            with self.assertRaisesRegex(control.ServiceControlRejected, 'request_conflict'):
                await self.driver.handle(prior.command())
            self.assertEqual(call.await_count, 1)

    async def test_cancelled_observer_does_not_cancel_or_resend_http(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def exchange(*args):
            entered.set();await release.wait()
            return {'response': http_response(), 'error': None}
        with patch.object(relay, 'exchange', side_effect=exchange) as call:
            observer = asyncio.create_task(self.driver.handle(task_command()))
            await entered.wait();observer.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await observer
            self.assertFalse(self.driver._last_task.cancelled())
            with self.assertRaisesRegex(control.ServiceControlRejected, 'busy_or_closed'):
                await self.driver.handle(prior.command(2))
            release.set()
            reply = await self.driver.handle(task_command())
            self.assertIsNone(reply['error'])
            self.assertEqual(call.call_count, 1)

    async def test_invalid_task_never_reserves_sequence_or_calls_http(self):
        with patch.object(relay, 'exchange', AsyncMock()) as call:
            bad = task_command(http=http_request('POST', '/v1/runs', b'{}'))
            with self.assertRaises(task.ServiceTaskProtocolRejected):
                await self.driver.handle(bad)
            self.assertEqual(self.driver._last_sequence, 0)
            self.assertIsNone(self.driver._last_command)
            call.assert_not_awaited()


@unittest.skipIf(web is None, 'aiohttp unavailable; actual HTTP fixture not run')
class TaskHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []
        self.mode = 'normal'
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        app = web.Application()
        app.router.add_route('*', '/{path:.*}', self.handler)
        self.runner = web.AppRunner(app, shutdown_timeout=.1)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await self.site.start()
        self.endpoint = 'http://127.0.0.1:' + str(self.site._server.sockets[0].getsockname()[1])
        self.service = object.__new__(BorrowedServiceOwner)
        self.service._actor = (os.getpid(), threading.get_ident())
        self.service._loop = asyncio.get_running_loop()
        self.service._held = object()
        self.service._owner = SimpleNamespace(_service_owner=self.service, _held=self.service._held)
        self.service._endpoint = self.endpoint
        self.service._consumer = SimpleNamespace(_adapter=object())
        self.service._transport, self.service._app = object(), object()
        self.observed = prior.owner_receipt() | {'endpoint': self.endpoint}
        self.service.status = lambda: copy.deepcopy(self.observed)
        self.bound = 0
        def execution(**values):
            self.assertIs(values['transport'], self.service._transport)
            self.assertIs(values['app'], self.service._app)
            self.assertIs(values['adapter'], self.service._consumer._adapter)
            self.bound += 1
        self.service.require_execution = execution

    async def asyncTearDown(self):
        self.release.set()
        await self.runner.cleanup()

    async def handler(self, request):
        body = await request.read()
        self.requests.append((request.method, request.path,
                              {key.lower(): value for key, value in request.headers.items()}, body))
        self.entered.set()
        if request.headers.get('Authorization') != 'Bearer ' + 't' * 40:
            return web.json_response({'error': 'unauthorized'}, status=401)
        if self.mode == 'delay':
            await self.release.wait()
        if self.mode == 'redirect':
            return web.Response(status=302, headers={'Location': self.endpoint + '/v1/runs/run_' + 'b' * 32})
        if self.mode == 'oversized':
            return web.Response(body=b'x' * 129, content_type='application/json')
        if self.mode == 'chunked':
            response = web.StreamResponse(headers={'Content-Type': 'application/json'})
            await response.prepare(request)
            await response.write(b'x' * 129)
            await response.write_eof()
            return response
        if self.mode == 'encoded':
            return web.Response(body=b'encoded', headers={'Content-Encoding': 'gzip'})
        if self.mode == 'replace_owner':
            self.service._consumer = SimpleNamespace(_adapter=object())
        if self.observed['state'] == 'DRAINING' and request.path in (
                '/alaz/host/v1/intents', '/alaz/host/v1/dispatch'):
            return web.json_response({'error': 'not_ready'}, status=409)
        return web.json_response({'ok': True, 'method': request.method}, status=202 if request.path.endswith('/dispatch') else 200)

    async def test_actual_http_uses_supplied_auth_and_preserves_rejection(self):
        request = http_request()
        request['headers']['authorization'] = 'Bearer wrong-caller-token'
        result = await relay.exchange(self.service, request)
        self.assertIsNone(result['error'])
        self.assertEqual(result['response']['status'], 401)
        self.assertEqual(self.requests[0][2]['authorization'], request['headers']['authorization'])
        self.assertIn(b'unauthorized', task.body_bytes(result['response']['bodyBase64'], 1024))
        self.assertEqual(self.bound, 2)

    async def test_authenticated_post_preserves_body_key_and_requirement_headers(self):
        request = http_request('POST', '/alaz/host/v1/dispatch', 'özel görev'.encode())
        request['headers'].update({'idempotency-key': 'ah1-' + 'a' * 32 + '-' + 'b' * 32,
            'x-alaz-execution-version': '1', 'x-alaz-provider-broker-version': '1'})
        result = await relay.exchange(self.service, request)
        self.assertEqual(result['response']['status'], 202)
        method, path, headers, body = self.requests[0]
        self.assertEqual((method, path, body), ('POST', '/alaz/host/v1/dispatch', 'özel görev'.encode()))
        self.assertEqual(headers['idempotency-key'], request['headers']['idempotency-key'])
        self.assertEqual(headers['x-alaz-execution-version'], '1')
        self.assertEqual(headers['x-alaz-provider-broker-version'], '1')
        self.assertNotIn('cookie', headers)

    async def test_drain_leaves_read_stop_and_admission_decision_to_http(self):
        self.observed = prior.owner_receipt('DRAINING') | {'endpoint': self.endpoint}
        read = await relay.exchange(self.service, http_request(path='/v1/runs/run_' + 'b' * 32))
        stop = await relay.exchange(self.service, http_request('POST', '/v1/runs/run_' + 'b' * 32 + '/stop', b'{}'))
        dispatch = await relay.exchange(self.service, http_request('POST', '/alaz/host/v1/dispatch', b'{}'))
        self.assertEqual([r['response']['status'] for r in (read, stop, dispatch)], [200, 200, 409])

    async def test_timeout_never_replays_post_and_allows_next_read(self):
        self.mode = 'delay'
        request = http_request('POST', '/alaz/host/v1/dispatch', b'{}')
        request['timeoutMs'] = 250
        operation = asyncio.create_task(relay.exchange(self.service, request))
        await self.entered.wait()
        result = await operation
        self.assertEqual(result, {'response': None, 'error': 'service_task_http_outcome_unknown'})
        self.assertEqual(len(self.requests), 1)
        self.release.set();self.mode = 'normal'
        query = await relay.exchange(self.service,
            http_request(path='/alaz/host/v1/requests/' + 'b' * 32))
        self.assertEqual(query['response']['status'], 200)
        self.assertEqual(len(self.requests), 2)

    async def test_redirect_is_returned_without_following_another_path(self):
        self.mode = 'redirect'
        result = await relay.exchange(self.service, http_request())
        self.assertEqual(result['response']['status'], 302)
        self.assertEqual(len(self.requests), 1)
        self.assertNotIn('location', result['response']['headers'])

    async def test_declared_and_chunked_overflow_and_encoding_are_bounded_errors(self):
        for mode in ('oversized', 'chunked', 'encoded'):
            self.mode = mode
            request = http_request();request['maxResponseBytes'] = 128
            with self.subTest(mode=mode):
                result = await relay.exchange(self.service, request)
                self.assertIsNone(result['response'])
                self.assertRegex(result['error'], '^service_task_response_')
        self.assertEqual(self.observed['state'], 'READY')

    async def test_arbitrary_owner_and_unready_owner_fail_before_socket(self):
        with self.assertRaises(relay.ServiceTaskHTTPRejected):
            await relay.exchange(object(), http_request())
        self.observed['state'] = 'UNKNOWN'
        with self.assertRaises(relay.ServiceTaskHTTPRejected):
            await relay.exchange(self.service, http_request())
        self.assertEqual(self.requests, [])

    async def test_replaced_native_consumer_after_await_does_not_qualify_reply(self):
        self.mode = 'replace_owner'
        with self.assertRaisesRegex(relay.ServiceTaskHTTPRejected, 'owner_changed'):
            await relay.exchange(self.service, http_request())
        self.assertEqual(len(self.requests), 1)


@unittest.skipUnless(os.name == 'posix', 'requires POSIX pipe readiness')
class TaskPipeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.input_read, self.input_write = os.pipe()
        self.output_read, self.output_write = os.pipe()
        self.fds = (self.input_read, self.input_write, self.output_read, self.output_write)
        self.channel = control.FDChannel(asyncio.get_running_loop(), input_fd=self.input_read,
                                         output_fd=self.output_write)
        os.set_blocking(self.input_write, False)
        os.set_blocking(self.output_read, False)

    async def asyncTearDown(self):
        for fd in self.fds:
            os.close(fd)

    async def send(self, raw):
        while raw:
            try:
                raw = raw[os.write(self.input_write, raw):]
            except BlockingIOError:
                await self.channel._ready(self.input_write, write=True, timeout=3)

    async def receive(self):
        raw = bytearray()
        while not raw.endswith(b'\n'):
            try:
                raw.extend(os.read(self.output_read, 16384))
            except BlockingIOError:
                await self.channel._ready(self.output_read, timeout=3)
        return bytes(raw)

    async def test_large_task_request_then_legacy_frame_use_separate_limits(self):
        value = task_command(http=http_request('POST', '/alaz/host/v1/intents', b'x' * 70000))
        writer = asyncio.create_task(self.send(task.encode(value) + control.canonical(prior.command(2)) + b'\n'))
        self.assertEqual(await self.channel.read(), value)
        self.assertEqual(await self.channel.read(), prior.command(2))
        await writer
        self.assertEqual(self.channel._buffer, bytearray())

    async def test_large_task_reply_is_prefixed_without_new_reader_thread(self):
        from test_service_task_protocol_r165a1 import task_reply
        value = task_reply(response=http_response(b'x' * 70000))
        before = threading.active_count()
        _, raw = await asyncio.gather(self.channel.write(value), self.receive())
        self.assertEqual(task.decode(raw, reply=True), value)
        self.assertEqual(threading.active_count(), before)


if __name__ == '__main__':
    unittest.main()
