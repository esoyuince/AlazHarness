"""R165 fixture child: real ServiceControl/FDChannel and actual loopback HTTP.

BorrowedServiceOwner is the exact original wrapper object. Native startup,
store/consumer/transport ports and API handlers are explicit doubles; the
wrapper's original actor/loop/execution binding checks remain active. This is
source integration, not an installed native runtime or kernel acceptance.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'packages/claw-hermes')]
from aiohttp import web
import gateway_service_control as control
from test_service_child_control_r160a1 import ServiceDouble

SID = 'a' * 32
REQUEST_ID = 'b' * 32
RUN_ID = 'run_' + 'd' * 32
TOKEN = 'fixture-task-bearer'
KEY = 'ah1-' + 'e' * 32 + '-' + REQUEST_ID
PROMPT = 'Read the allowed fixture.\nTürkçe satır.'
PATHS = {'capabilities': '/alaz/host/v1/capabilities', 'intents': '/alaz/host/v1/intents',
         'dispatch': '/alaz/host/v1/dispatch', 'request': '/alaz/host/v1/requests/' + REQUEST_ID,
         'run': '/v1/runs/' + RUN_ID, 'stop': '/v1/runs/' + RUN_ID + '/stop'}


def main():
    scenario, journal = sys.argv[1:]
    assert scenario in ('task-lifecycle', 'wrong-bearer', 'lost-dispatch-reply')
    journal = Path(journal)

    def log(value):
        with journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, sort_keys=True) + '\n')
            stream.flush()

    # Consume the actual bounded supervisor bootstrap before making stdin
    # nonblocking. Namespace/source checks are deliberately fixture ports here.
    bootstrap = sys.stdin.buffer.readline(131074)
    assert 0 < len(bootstrap) <= 131073 and bootstrap.endswith(b'\n')
    plan = json.loads(json.loads(bootstrap)['plan'])
    assert plan['serviceId'] == SID and plan['instanceId'] == 'owned-service-2'
    log({'event': 'bootstrap', 'bytes': len(bootstrap)})

    async def run():
        state = {'intents': 0, 'dispatches': 0, 'stops': 0, 'queries': 0,
                 'httpRequests': 0, 'unauthorized': 0, 'consumed': False,
                 'lossInjected': False, 'bindingChecks': 0}
        fixture = ServiceDouble()
        service = fixture.service
        original_owner = service

        async def handler(request):
            state['httpRequests'] += 1
            body = await request.read()
            authorized = request.headers.get('Authorization') == 'Bearer ' + TOKEN
            log({'event': 'http', 'method': request.method, 'path': request.path,
                 'bytes': len(body), 'authorized': authorized})
            if not authorized:
                state['unauthorized'] += 1
                return web.json_response({'hostGateVersion': 1,
                    'error': {'code': 'unauthorized'}}, status=401)
            assert request.headers.get('Accept') == 'application/json'
            assert request.query_string == ''
            if request.method == 'GET':
                assert body == b''
            else:
                assert request.headers.get('Content-Type') == 'application/json'
            if request.path == PATHS['capabilities']:
                assert request.method == 'GET'
                return web.json_response({'hostGateVersion': 1,
                    'dispatchPath': PATHS['dispatch'], 'nativeStoreOwner': True,
                    'dispatchAtMostOnce': True, 'automaticRetry': False,
                    'scope': 'default_profile_new_run', 'executionBoundaryVersion': 1,
                    'providerBrokerVersion': 1,
                    'providerBrokerBackend': 'linux_unix_credential_broker'})
            if request.path == PATHS['intents']:
                assert request.method == 'POST'
                assert json.loads(body) == {'requestId': REQUEST_ID,
                    'body': {'model': 'fixture-model', 'input': PROMPT}}
                assert not state['consumed']
                state['intents'] += 1
                return web.json_response({'hostGateVersion': 1, 'requestId': REQUEST_ID,
                    'idempotencyKey': KEY, 'dispatchState': 'issued',
                    'expiresAtMs': int(time.time() * 1000) + 30000,
                    'replayed': False, 'retryAllowed': False}, status=201)
            if request.path == PATHS['dispatch']:
                assert request.method == 'POST'
                assert json.loads(body) == {'model': 'fixture-model', 'input': PROMPT}
                assert request.headers.get('Idempotency-Key') == KEY
                assert request.headers.get('X-Alaz-Execution-Version') == '1'
                assert request.headers.get('X-Alaz-Provider-Broker-Version') == '1'
                state['dispatches'] += 1
                assert state['dispatches'] == 1 and state['intents'] == 1
                state['consumed'] = True
                if scenario == 'lost-dispatch-reply':
                    # The fixture has consumed this native request before the
                    # real HTTP connection is lost. No task reply is invented.
                    state['lossInjected'] = True
                    request.transport.close()
                    return web.Response(status=202)
                return web.json_response({'run_id': RUN_ID, 'status': 'started',
                                          'replayed': False}, status=202)
            if request.path == PATHS['request']:
                assert request.method == 'GET' and state['consumed']
                assert request.headers.get('X-Alaz-Execution-Version') is None
                assert request.headers.get('X-Alaz-Provider-Broker-Version') is None
                state['queries'] += 1
                return web.json_response({'hostGateVersion': 1, 'requestObservationVersion': 1,
                    'requestId': REQUEST_ID, 'classification': 'native_run_located',
                    'dispatchState': 'consumed', 'runId': RUN_ID, 'snapshotOnly': True,
                    'writesPerformed': False, 'canonicalVerified': False,
                    'retryAllowed': False, 'repairAllowed': False, 'requiresOperator': False,
                    'nextAction': 'observe_existing_run'})
            if request.path == PATHS['stop']:
                assert request.method == 'POST' and state['consumed']
                assert json.loads(body) == {}
                state['stops'] += 1
                assert state['stops'] == 1
                return web.json_response({'run_id': RUN_ID, 'status': 'stopping'})
            if request.path == PATHS['run']:
                assert request.method == 'GET' and state['consumed']
                return web.json_response({'run_id': RUN_ID,
                    'status': 'cancelled' if state['stops'] else 'completed',
                    'admission_id': 'f' * 32, 'session_id': 'api-service-task-fixture',
                    'execution_generation': 1, 'output': 'scoped result',
                    'usage': {'input_tokens': 2, 'output_tokens': 3, 'total_tokens': 5}})
            raise AssertionError('unexpected fixture HTTP route')

        app = web.Application()
        app.router.add_route('*', '/{path:.*}', handler)
        runner = web.AppRunner(app, shutdown_timeout=.2)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0)
        await site.start()
        endpoint = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])

        # Populate the original wrapper's real actor and execution bindings.
        # None of these objects claims physical stores or a native lease.
        loop = asyncio.get_running_loop()
        held, adapter = object(), object()
        expected = SimpleNamespace(epoch=2, instance_id='owned-service-2')
        authority = SimpleNamespace(epoch=2, instance_id='owned-service-2')
        connections = tuple(object() for _ in range(3))
        stores = tuple(SimpleNamespace(_conn=value) for value in connections)
        owner = SimpleNamespace(_service_owner=service, _held=held, _stage='VERIFIED',
                                _expected=expected)
        consumer = SimpleNamespace(_adapter=adapter, _loop=loop, _owner=owner,
            _borrowed_service=True, _admission_phase='ACTIVE', _stage='ATTACHED',
            _expected=expected, _stores=stores, _connections=connections,
            _binding=SimpleNamespace(_authority=authority))
        owner._prepared_consumer = consumer

        class TransportDouble:
            def check_binding(self, *, for_admission, app, adapter):
                assert for_admission is False
                assert app is service._app and adapter is consumer._adapter
                state['bindingChecks'] += 1
                return authority

        service._actor, service._loop = (os.getpid(), threading.get_ident()), loop
        service._held, service._owner, service._consumer = held, owner, consumer
        service._transport, service._app = TransportDouble(), app
        service._stores, service._connections = stores, connections
        service._epoch, service._instance_id = 2, 'owned-service-2'
        service._endpoint = endpoint
        fixture.value['endpoint'] = endpoint
        native_drain, native_close = service.begin_drain, service.close_when_idle

        def drain():
            native_drain()
            consumer._admission_phase = 'DRAINING'
            fixture.value['endpoint'] = endpoint
            return copy.deepcopy(fixture.value)

        async def close():
            # The actual HTTP fixture must release every connection/task before
            # ServiceControl performs its production all_tasks final check.
            await runner.cleanup()
            await native_close()
            fixture.value['endpoint'] = endpoint
            return copy.deepcopy(fixture.value)

        service.begin_drain, service.close_when_idle = drain, close
        driver = control.ServiceControl(service, SID)

        class ObservedChannel(control.FDChannel):
            async def read(self):
                value = await super().read()
                log({'event': 'command', 'action': value['action'],
                     'sequence': value['sequence'],
                     **({'path': value['http']['path']} if 'http' in value else {})})
                return value

            async def write(self, value):
                await super().write(value)
                log({'event': 'reply', 'type': value['type'], 'sequence': value['sequence'],
                     'state': value['owner']['state'],
                     **({'httpStatus': None if value['response'] is None else value['response']['status'],
                         'error': value['error']} if value['type'] == 'task-reply' else {})})

        channel = ObservedChannel(loop)
        final = await driver.drive(channel, object(), object())
        assert final['type'] == 'final' and final['owner']['state'] == 'CLOSED'
        pending = [task for task in asyncio.all_tasks(loop)
                   if task is not asyncio.current_task() and not task.done()]
        assert not pending
        assert service is original_owner and driver.service is service
        assert service._control_owner is driver and owner._service_owner is service
        assert not driver._fenced
        assert fixture.calls == ['start', 'close']
        assert state['bindingChecks'] == 2 * state['httpRequests']
        log({'event': 'final', **state, 'sameOriginalOwner': True,
             'controlFenced': driver._fenced, 'pendingTasks': len(pending),
             'nativeLifecycleCalls': fixture.calls, 'nativeMethodsDoubled': True,
             'nativeApiHandlersDoubled': True, 'installedRuntime': False})

    asyncio.run(run())


if __name__ == '__main__':
    main()
