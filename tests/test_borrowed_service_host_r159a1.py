"""Real harness guards/lifecycle; native owners and transport explicitly doubled.

SQLite and threaded ledger work are real fresh fixtures. No native runtime,
listener, provider, model, mount or image is started by this module.
"""
import asyncio
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]
import execution_boundary as boundary
import gateway_service_runtime as service
import gateway_service_sources as sources
import gateway_store_startup as startup
import gateway_consumer_admission as admission
import gateway_prepared_consumer as consumer
import test_api_owner_i133p1 as owner_contract
import host_gate_plugin
from host_gate import HostGateLedger, HostGateError
from test_execution_gate_qa import policy
from test_host_gate_qa import GateFixture
from test_host_request_observation import ObservationFixture, web, make_mocked_request


def native_modules(transport=None, rejection=None, bundle=None):
    result = {}
    for name in ('gateway', 'gateway.platforms'):
        module = ModuleType(name)
        module.__path__ = []
        result[name] = module
    module = ModuleType('gateway.platforms.api_server_borrowed_transport')
    module.BorrowedHTTPTransport = transport
    result[module.__name__] = module
    module = ModuleType('gateway.platforms.api_server_borrowed')
    module.BorrowedStoreRejected = rejection or RuntimeError
    module.BorrowedAPIStores = bundle
    result[module.__name__] = module
    return result


class TransportFixture:
    """Only the native binding check is doubled; HTTP and host ledger are real."""
    def __init__(self, adapter, app):
        self.adapter, self.app = adapter, app
        self.phase = 'ACTIVE'
        self.calls = []

    def check_binding(self, *, for_admission=False, app=None, adapter=None):
        self.calls.append((for_admission, threading.get_ident()))
        if (self.phase not in ('ACTIVE', 'DRAINING')
                or for_admission and self.phase != 'ACTIVE'
                or app is not self.app or adapter is not self.adapter):
            raise RuntimeError('fixture_binding_refused')
        return self.adapter.gateway_runner.session_authority

    def check(self, **kwargs):
        raise AssertionError('request/tool must not require a quiescent SQL snapshot')


def service_binding_fixture(adapter, app, transport):
    """Use the actual pure owner gate with explicit synthetic native identities."""
    value = object.__new__(service.BorrowedServiceOwner)
    value._actor = (os.getpid(), threading.get_ident())
    value._loop = asyncio.get_running_loop()
    value._state = 'READY';value._transport = transport;value._app = app
    value._held = object()
    authority = adapter.gateway_runner.session_authority
    authority.instance_id = 'first-owner'
    expected = SimpleNamespace(epoch=authority.epoch, instance_id=authority.instance_id)
    value._epoch = expected.epoch;value._instance_id = expected.instance_id
    value._connections = tuple(object() for _ in range(3))
    value._stores = tuple(SimpleNamespace(_conn=c) for c in value._connections)
    owner = SimpleNamespace(_stage='VERIFIED', _expected=expected, _held=value._held)
    c = SimpleNamespace(_adapter=adapter, _loop=value._loop, _owner=owner,
        _borrowed_service=True, _admission_phase='ACTIVE', _stage='ATTACHED',
        _expected=expected, _stores=value._stores, _connections=value._connections,
        _binding=SimpleNamespace(_authority=authority))
    value._owner=owner;value._consumer=c;owner._prepared_consumer=c;owner._service_owner=value
    return value


@unittest.skipIf(web is None, 'aiohttp unavailable; route qualification not run')
class BorrowedHostRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = ObservationFixture(temporary.name)
        self.f.accepted()
        self.app = web.Application()
        authority = SimpleNamespace(db=self.f.db, epoch=1, retiring=False, retired=False)
        self.adapter = SimpleNamespace(_host='127.0.0.1',
            _expected_api_key=lambda: self.f.context.api_token,
            _room_grant_token=lambda request: None,
            gateway_runner=SimpleNamespace(session_authority=authority,
                session_runtime_descriptor={'state': 'caller_active', 'instance_id': 'first-owner'}))
        self.transport = TransportFixture(self.adapter, self.app)
        self.service = service_binding_fixture(self.adapter, self.app, self.transport)
        self.stop_calls = 0

        async def stop(request):
            self.stop_calls += 1
            return web.json_response({'status': 'stopping'})

        self.app.router.add_post('/v1/runs/{run_id}/stop', stop)
        self.execution = SimpleNamespace(bind=lambda *args, **kwargs: None,
            require_ready=AsyncMock(), broker=object(), isolation=None)
        with patch.dict(sys.modules, native_modules(TransportFixture)), \
                patch.object(host_gate_plugin, 'validate_native_adapter'):
            host_gate_plugin.bind_host_gate(self.app, self.adapter, self.f.policy,
                execution=self.execution, service_transport=self.transport,service_owner=self.service)
        self.app.freeze()

    async def request(self, method, path, value=None, token=True):
        headers = {'Authorization': 'Bearer ' + self.f.context.api_token} if token else {}
        raw = json.dumps(value).encode() if value is not None else b''
        if value is not None:
            headers.update({'Content-Type': 'application/json', 'Content-Length': str(len(raw))})
        request = make_mocked_request(method, path, headers=headers, app=self.app)
        request._read_bytes = raw
        response = await self.app._handle(request)
        return response.status, json.loads(response.text)

    def drain(self):
        self.transport.phase = 'DRAINING'
        self.service._state = 'DRAINING';self.service._consumer._admission_phase = 'DRAINING'
        self.adapter.gateway_runner.session_authority.retiring = True
        self.adapter.gateway_runner.session_runtime_descriptor['state'] = 'caller_draining'

    async def test_locator_uses_exact_service_binding_without_ready_descriptor(self):
        status, value = await self.request('GET', '/alaz/host/v1/requests/' + self.f.rid)
        self.assertEqual(status, 200)
        self.assertEqual(value['classification'], 'native_run_located')
        self.assertEqual(self.adapter.gateway_runner.session_runtime_descriptor['state'], 'caller_active')
        self.execution.require_ready.assert_not_awaited()

    async def test_draining_retains_locator_and_native_stop(self):
        self.drain()
        before = self.f.hashes()
        status, value = await self.request('GET', '/alaz/host/v1/requests/' + self.f.rid)
        self.assertEqual((status, value['classification']), (200, 'native_run_located'))
        status, value = await self.request('POST', '/v1/runs/' + self.f.run_id + '/stop')
        self.assertEqual((status, self.stop_calls), (200, 1))
        self.assertEqual(before, self.f.hashes())

    async def test_draining_refuses_new_intent_without_ledger_write(self):
        self.drain()
        before = self.f.hashes()
        status, value = await self.request('POST', '/alaz/host/v1/intents',
            {'requestId': 'c' * 32, 'body': self.f.body})
        self.assertEqual(status, 409)
        self.assertEqual(value['error']['code'], 'native_owner_unavailable')
        self.assertEqual(before, self.f.hashes())

    async def test_drain_during_execution_readiness_is_rechecked_inside_native_write(self):
        before = self.f.hashes()
        self.execution.require_ready.side_effect = self.drain
        threads=[];original=self.service.require_admission
        def guarded(**kwargs):
            threads.append(threading.get_ident());return original(**kwargs)
        with patch.object(self.service,'require_admission',side_effect=guarded):
            status, value = await self.request('POST', '/alaz/host/v1/intents',
                {'requestId': 'c' * 32, 'body': self.f.body})
        self.assertEqual(status, 409)
        self.assertEqual(value['error']['code'], 'native_owner_unavailable')
        self.assertTrue(any(thread != threading.get_ident() for thread in threads))
        self.assertEqual(before, self.f.hashes())

    async def test_forged_ready_descriptor_does_not_replace_service_proof(self):
        self.transport.phase = 'UNKNOWN'
        self.adapter.gateway_runner.session_runtime_descriptor['state'] = 'ready'
        status, value = await self.request('GET', '/alaz/host/v1/requests/' + self.f.rid)
        self.assertEqual(status, 409)
        self.assertEqual(value['error']['code'], 'native_owner_unavailable')

    async def test_bound_listener_does_not_admit_before_overall_service_ready(self):
        self.service._state = 'STARTING'
        before = self.f.hashes()
        status, value = await self.request('POST', '/alaz/host/v1/intents',
            {'requestId': 'c' * 32, 'body': self.f.body})
        self.assertEqual((status,value['error']['code']), (409,'native_owner_unavailable'))
        self.assertEqual(before,self.f.hashes())
        self.execution.require_ready.assert_not_awaited()

    async def test_unknown_overall_owner_does_not_reuse_transport_ready(self):
        self.service._state = 'UNKNOWN'
        status, value = await self.request('POST', '/alaz/host/v1/intents',
            {'requestId': 'c' * 32, 'body': self.f.body})
        self.assertEqual((status,value['error']['code']), (409,'native_owner_unavailable'))

    async def test_owner_epoch_replacement_does_not_reuse_ready_record(self):
        expected=self.service._owner._expected
        self.service._owner._expected = SimpleNamespace(epoch=1,instance_id='first-owner')
        status, value = await self.request('POST', '/alaz/host/v1/intents',
            {'requestId': 'c' * 32, 'body': self.f.body})
        self.assertEqual((status,value['error']['code']), (409,'native_owner_unavailable'))
        self.service._owner._expected=expected
        self.service._consumer._connections=self.service._consumer._connections[:2]
        status,value=await self.request('POST','/alaz/host/v1/intents',
            {'requestId':'c'*32,'body':self.f.body})
        self.assertEqual((status,value['error']['code']),(409,'native_owner_unavailable'))

    async def test_stop_authentication_still_precedes_native_control(self):
        self.drain()
        status, value = await self.request('POST', '/v1/runs/' + self.f.run_id + '/stop', token=False)
        self.assertEqual(status, 401)
        self.assertEqual(self.stop_calls, 0)


@unittest.skipIf(web is None, 'aiohttp unavailable; provider route qualification not run')
class BorrowedProviderEntry(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        allowed=Path(temporary.name)/'allowed.txt';allowed.write_text('fixture')
        self.execution=boundary.ExecutionBoundary(dict(policy=asdict(policy()),
            provider_bearer='p'*32,allowed_read_files=[str(allowed)],
            upstream_base_url='http://127.0.0.1:45551/v1'))
        self.app=web.Application()
        self.adapter=SimpleNamespace(gateway_runner=SimpleNamespace(
            session_authority=SimpleNamespace(epoch=1,instance_id='first-owner')))
        self.transport=TransportFixture(self.adapter,self.app)
        self.service=service_binding_fixture(self.adapter,self.app,self.transport)
        self.execution.context=object();self.execution.require_ready=AsyncMock()
        with patch.dict(sys.modules,native_modules(TransportFixture)), \
                patch.object(self.execution.tools,'register'):
            self.execution.bind(self.app,self.adapter,service_transport=self.transport,
                                service_owner=self.service)
        self.app.freeze()

    async def request(self,method,path):
        request=make_mocked_request(method,path,
            headers={'Authorization':'Bearer '+'p'*32},app=self.app)
        response=await self.app._handle(request)
        return response.status,json.loads(response.text)

    async def test_provider_post_cannot_claim_during_starting_or_unknown(self):
        for state in ('STARTING','UNKNOWN'):
            self.service._state=state
            status,value=await self.request('POST','/alaz/provider/v1/chat/completions')
            self.assertEqual((status,value['error']['code']),(403,'execution_service_unavailable'))
        self.execution.require_ready.assert_not_awaited()

    async def test_provider_metadata_cannot_advertise_starting_as_ready(self):
        self.service._state='STARTING'
        status,value=await self.request('GET','/alaz/provider/v1/models')
        self.assertEqual(status,403)
        self.execution.require_ready.assert_not_awaited()

    async def test_draining_existing_provider_entry_remains_available(self):
        self.service._state='DRAINING';self.service._consumer._admission_phase='DRAINING'
        self.transport.phase='DRAINING'
        status,value=await self.request('GET','/alaz/provider/v1/models')
        self.assertEqual(status,200)
        self.assertEqual(value['data'][0]['id'],self.execution.policy.model)
        self.execution.require_ready.assert_awaited_once()


class BorrowedExecutionWorker(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = GateFixture(temporary.name)
        allowed = Path(temporary.name) / 'allowed.txt'
        allowed.write_text('owned worker fixture', encoding='utf-8')
        self.execution = boundary.ExecutionBoundary(dict(policy=asdict(policy()),
            provider_bearer='p' * 32, allowed_read_files=[str(allowed)],
            upstream_base_url='http://127.0.0.1:45551/v1'))
        authority = SimpleNamespace(db=self.f.db, epoch=1, retiring=True, retired=False)
        self.execution.adapter = SimpleNamespace(_expected_api_key=lambda: self.f.context.api_token,
            gateway_runner=SimpleNamespace(session_authority=authority,
                session_runtime_descriptor={'state': 'caller_draining', 'instance_id': 'first-owner'}))
        self.execution._service_app = object()
        self.transport = TransportFixture(self.execution.adapter, self.execution._service_app)
        self.transport.phase = 'DRAINING'
        self.execution.service_transport = self.transport
        self.addCleanup(patch.stopall)
        patch.object(self.execution, 'validate_profile').start()
        self.allowed = allowed

    def test_actual_guarded_read_and_settlement_run_on_worker_during_drain(self):
        # Registry and original core reader are explicitly declared fixtures;
        # GuardedFileTools.guarded, ledger and SQLite transactions are real.
        entries = {}
        file_tools = ModuleType('tools.file_tools')
        file_tools.__file__ = str(ROOT / 'native-fixture/tools/file_tools.py')
        for name, symbol in {'read_file': '_handle_read_file', 'write_file': '_handle_write_file',
                             'patch': '_handle_patch', 'search_files': '_handle_search_files'}.items():
            handler = lambda args, **kwargs: Path(args['path']).read_text(encoding='utf-8')
            setattr(file_tools, symbol, handler)
            entries[name] = SimpleNamespace(handler=handler, schema={}, check_fn=None)
        registry = SimpleNamespace(get_entry=lambda name, scope: entries.get(name))
        tools = ModuleType('tools');tools.__path__ = [];tools.file_tools = file_tools
        registry_module = ModuleType('tools.registry');registry_module.registry = registry

        def register_tool(**kwargs):
            entries[kwargs['name']] = SimpleNamespace(handler=kwargs['handler'])
            return object()

        context = SimpleNamespace(_manager=SimpleNamespace(scope_key=str(self.f.home)),
                                  register_tool=register_tool)
        original_load = boundary._load
        def loader(raw, *args):
            if type(raw) is str and 'source_commit' in raw and 'files' in raw:
                return {'files': []}  # Source attestation is explicitly doubled here.
            return original_load(raw, *args)
        with patch.dict(sys.modules, {'tools': tools, 'tools.file_tools': file_tools,
                                      'tools.registry': registry_module}), patch.object(boundary, '_load', loader):
            self.execution.tools.register(context)
            self.execution.ledger().initialize()
            run_id = 'run_' + 'd' * 32
            self.f.sql('CREATE TABLE session_admissions(request_id TEXT,target_session_id TEXT)')
            self.f.sql('INSERT INTO session_admissions VALUES(?,?)', (run_id, run_id))
            result = []
            worker = threading.Thread(target=lambda: result.append(
                self.execution.tools.handlers['read_file']({'path': str(self.allowed)}, session_id=run_id)))
            worker.start();worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result, ['owned worker fixture'])
            self.assertTrue(any(thread != threading.get_ident() for _, thread in self.transport.calls))
            state = self.execution.ledger().snapshot()
            self.assertEqual(state['toolCalls'], 1)
            self.assertEqual(state['providerCalls'], 0)

    def test_unknown_service_cannot_claim_or_settle_under_forged_ready(self):
        self.transport.phase = 'UNKNOWN'
        self.execution.adapter.gateway_runner.session_runtime_descriptor['state'] = 'ready'
        before = self.f.rows()
        with self.assertRaisesRegex(boundary.ExecutionDenied, 'execution_owner_unavailable'):
            self.execution.ledger()
        self.assertEqual(before, self.f.rows())


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'config').mkdir()
        self.manifest = {'schema': 1, 'nativeFeature': 'a' * 40, 'purpose': 'test fixture',
                         'sources': {name: 'b' * 64 for name in sources.REQUIRED}}
        self.write()
        self.addCleanup(patch.stopall)
        patch.object(sources, 'ROOT', self.root).start()

    def write(self):
        raw = json.dumps(self.manifest).encode()
        (self.root / sources.MANIFEST).write_bytes(raw)
        selection = {'schema': 1, 'nativeFeature': 'a' * 40, 'sourceManifest': sources.MANIFEST,
                     'sourceManifestSha256': hashlib.sha256(raw).hexdigest()}
        (self.root / sources.SELECTION).write_text(json.dumps(selection), encoding='utf-8')

    def test_new_service_generation_loads_from_its_own_fixed_envelope(self):
        selected = sources.load_selection()
        self.assertEqual(sources.selected_manifest(selected), self.manifest)

    def test_manifest_changes_do_not_reuse_prepared_selection(self):
        selected = sources.load_selection()
        (self.root / sources.MANIFEST).write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(sources.ServiceSourcesRejected, 'manifest_changed'):
            sources.selected_manifest(selected)

    def test_command_and_http_sources_must_be_present_in_service_closure(self):
        for name in ('agent/secret_sources/command.py','gateway/platforms/api_server_metrics.py',
                     'gateway/platforms/api_server_authority_runs.py'):
            with self.subTest(source=name):
                self.manifest['sources'].pop(name)
                self.write()
                with self.assertRaisesRegex(sources.ServiceSourcesRejected, 'manifest_closure'):
                    sources.selected_manifest(sources.load_selection())
                self.manifest['sources'][name]='b'*64

    def test_parent_path_cannot_expand_source_closure(self):
        self.manifest['sources']['../outside.py'] = 'a' * 64
        self.write()
        with self.assertRaisesRegex(sources.ServiceSourcesRejected, 'manifest_entry'):
            sources.selected_manifest(sources.load_selection())


class ServiceConsumerSelection(unittest.IsolatedAsyncioTestCase):
    setUp=owner_contract.SelectionContracts.setUp
    mark=owner_contract.SelectionContracts.mark
    make_store=owner_contract.SelectionContracts.make_store
    obj=owner_contract.SelectionContracts.obj

    async def test_explicit_service_reserves_same_original_consumer_and_stores(self):
        owner=self.obj();owner.start()
        selected=sources.ServiceSourceSelection('a'*40,'b'*64,'c'*64)
        async def prepared(value,*args):
            self.assertIs(owner._prepared_consumer,value)
            self.assertIs(value._owner,owner)
            self.assertIs(value._service_source,selected)
            self.assertTrue(value._borrowed_service and value._finite_turn
                            and value._canonical_api and value._local_admission)
            self.assertEqual(value._selected_feature,'a'*40)
            self.assertIs(value._stores[0],owner.state_store)
            self.assertIs(value._stores[1],owner.replay_store)
            self.assertIs(value._stores[2],owner.response_store)
        with patch.object(sources,'load_selection',return_value=selected), \
                patch.object(consumer.PreparedRuntimeConsumer,'prepare',prepared):
            await owner.prepare_runtime(object(),object(),local_admission=True,
                canonical_api=True,finite_turn=True,borrowed_service=True)

    async def test_legacy_finite_does_not_read_or_select_service_configuration(self):
        owner=self.obj();owner.start()
        with patch.object(sources,'load_selection',side_effect=AssertionError('service selection read')), \
                patch.object(consumer.PreparedRuntimeConsumer,'prepare',new=AsyncMock()):
            value=await owner.prepare_runtime(object(),object(),local_admission=True,
                canonical_api=True,finite_turn=True)
        self.assertFalse(value._borrowed_service)
        self.assertEqual(value._selected_feature,consumer.FINITE_FEATURE)

    async def test_invalid_or_incomplete_service_options_never_reserve_consumer(self):
        owner=self.obj();owner.start()
        for selected in (0,1,None,'true',{}):
            with self.assertRaises(startup.StoreStartupRejected):
                await owner.prepare_runtime(object(),object(),local_admission=True,
                    canonical_api=True,finite_turn=True,borrowed_service=selected)
            self.assertIsNone(owner._prepared_consumer)
        with self.assertRaises(startup.StoreStartupRejected):
            await owner.prepare_runtime(object(),object(),local_admission=True,
                canonical_api=True,borrowed_service=True)
        self.assertIsNone(owner._prepared_consumer)

class NativeBusyFixture(RuntimeError):
    pass


class ServiceClosureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = GateFixture(temporary.name)
        allowed = Path(temporary.name) / 'allowed.txt';allowed.write_text('fixture')
        execution = boundary.ExecutionBoundary(dict(policy=asdict(policy()), provider_bearer='p' * 32,
            allowed_read_files=[str(allowed)], upstream_base_url='http://127.0.0.1:45551/v1'))
        execution.broker = SimpleNamespace(link=SimpleNamespace(signing_key='b' * 32))
        self.trace = []
        held = SimpleNamespace(_finished=False, _owner=SimpleNamespace(homes=('fixture',)),
                               check=lambda: None)
        def finish():
            self.trace.append('lease');held._finished = True;held._owner.homes = ()
        held.finish = finish
        owner = object.__new__(startup.NativeStoreStartup)
        owner._stage = 'VERIFIED';owner._owned = lambda: None;owner._held = held
        owner._prepared_consumer = None;owner._response_expected = object()
        self.s = service.BorrowedServiceOwner(owner, host_policy=self.f.policy.__class__(
            frozenset((execution.policy.model,))), execution=execution, context=object())
        self.s._loop = asyncio.get_running_loop();self.s._state = 'READY'
        self.connections = tuple(sqlite3.connect(':memory:') for _ in range(3))
        for connection in self.connections:self.addCleanup(connection.close)
        self.s._connections = self.connections
        self.s._stores = tuple(SimpleNamespace(_conn=c) for c in self.connections)
        def close():
            self.trace.append('stores')
            for connection in self.connections:connection.close()
            owner._stage = 'CLOSED'
        owner.close = close
        owner.status = lambda: {'callerLeaseMayBeReleased': owner._stage == 'CLOSED'}
        c = SimpleNamespace(_stage='ATTACHED', _admission_phase='ACTIVE', _adapter=object())
        def drain():
            self.trace.append('drain');c._admission_phase = 'DRAINING'
        async def runtime():
            self.trace.append('runtime');return {'state': 'IDLE_RUNTIME_RETIRED'}
        def sessions():
            self.trace.append('api');return {'state': 'IDLE_API_SESSIONS_RETIRED'}
        def finish_drain():
            self.trace.append('finish_drain');c._admission_phase = 'DRAINED'
        async def detach():
            self.trace.append('detach');c._stage = c._admission_phase = 'DETACHED'
        c.begin_drain = drain;c.retire_idle_runtime = runtime;c.retire_idle_api_sessions = sessions
        c.finish_drain = finish_drain;c.detach = detach;self.s._consumer = c
        self.native_phase = 'DRAINING'
        async def retire():
            self.trace.append('transport');self.native_phase = 'RETIRED'
            return {'state': 'RETIRED', 'callerStoresClosed': False}
        self.s._transport = SimpleNamespace(retire_idle=retire,
            status=lambda: {'state': self.native_phase}, check_binding=lambda **kwargs: None)
        async def join():self.trace.append('executor')
        self.addCleanup(patch.stopall)
        patch.object(self.s._loop, 'shutdown_default_executor', join).start()
        patch.dict(sys.modules, native_modules(rejection=NativeBusyFixture)).start()

    async def test_only_ordered_terminal_receipt_releases_original_stores_and_lease(self):
        result = await self.s.close_when_idle()
        self.assertEqual(self.trace, ['drain', 'transport', 'runtime', 'api', 'finish_drain',
                                     'detach', 'executor', 'stores', 'lease'])
        self.assertEqual(result['state'], 'CLOSED')
        self.assertEqual(result['close']['physicalStoresClosed'], 3)
        self.assertTrue(result['close']['callerLeaseReleased'])
        self.assertFalse(result['close']['imageLeaseReleasedHere'])
        again = await self.s.close_when_idle()
        self.assertEqual(again, result)
        self.assertEqual(self.trace.count('lease'), 1)

    async def test_busy_close_retains_listener_control_and_every_original_handle(self):
        async def busy():raise NativeBusyFixture('borrowed_transport_handlers_active')
        self.s._transport.retire_idle = busy
        result = await self.s.close_when_idle()
        self.assertEqual(result['state'], 'DRAINING')
        self.assertEqual(self.native_phase, 'DRAINING')
        self.assertEqual(self.trace, ['drain'])
        self.assertFalse(result['close']['callerLeaseReleased'])
        for connection in self.connections:self.assertEqual(connection.execute('SELECT 1').fetchone(), (1,))

    async def test_observer_cancellation_keeps_one_original_close_task(self):
        entered, release = asyncio.Event(), asyncio.Event()
        original = self.s._transport.retire_idle
        async def delayed():
            entered.set();await release.wait();return await original()
        self.s._transport.retire_idle = delayed
        observer = asyncio.create_task(self.s.close_when_idle())
        await entered.wait()
        original_task = self.s._close_task
        observer.cancel()
        with self.assertRaises(asyncio.CancelledError):await observer
        self.assertFalse(original_task.cancelled())
        self.assertFalse(original_task.done())
        second = asyncio.create_task(self.s.close_when_idle())
        release.set()
        result = await second
        self.assertIs(self.s._close_task, original_task)
        self.assertEqual(result['state'], 'CLOSED')
        self.assertEqual(self.trace.count('transport'), 1)

    async def test_partial_transport_cleanup_never_releases_or_retries(self):
        async def unknown():
            self.native_phase = 'UNKNOWN'
            raise NativeBusyFixture('borrowed_transport_retirement_unknown')
        self.s._transport.retire_idle = unknown
        with self.assertRaises(NativeBusyFixture):await self.s.close_when_idle()
        self.assertEqual(self.s.status()['state'], 'UNKNOWN')
        self.assertEqual(self.trace, ['drain'])
        with self.assertRaises(service.ServiceRuntimeRejected):await self.s.close_when_idle()
        self.assertFalse(self.s._held._finished)

    async def test_owner_cannot_be_wrapped_twice(self):
        with self.assertRaisesRegex(service.ServiceRuntimeRejected, 'already_reserved'):
            service.BorrowedServiceOwner(self.s._owner, host_policy=self.s._policy,
                execution=self.s._execution, context=object())

    async def test_status_does_not_reuse_ready_after_native_phase_or_identity_loss(self):
        def failed_identity(**kwargs):raise RuntimeError('fixture_identity_changed')
        def failed_status():raise RuntimeError('fixture_status_unavailable')
        original_owner=self.s._owner;original_transport=self.s._transport
        for phase,binding,status in (
                ('UNKNOWN',lambda **kwargs:None,None),
                ('READY',failed_identity,None),
                ('READY',lambda **kwargs:None,failed_status)):
            with self.subTest(phase=phase,binding_failed=binding is failed_identity,
                              getter_failed=status is failed_status):
                self.s._state='READY';self.s._last_reason=None;self.native_phase=phase
                self.s._transport.check_binding=binding
                self.s._transport.status=status or (lambda:{'state':self.native_phase})
                result=self.s.status()
                self.assertEqual(result['state'],'UNKNOWN')
                self.assertFalse(result['serviceReady'] or result['admissionOpen'])
                self.assertIs(self.s._owner,original_owner)
                self.assertIs(self.s._transport,original_transport)
                self.assertEqual(self.trace,[])
                self.assertFalse(self.s._held._finished)
        self.s._last_reason='fixture_original_startup_failure'
        self.s._transport.status=failed_status
        self.assertEqual(self.s.status()['reason'],'fixture_original_startup_failure')


class ServiceStartupGuards(unittest.IsolatedAsyncioTestCase):
    """Harness start/failure gates; native prepare and HTTP bind explicitly doubled."""
    async def asyncSetUp(self):
        await ServiceClosureTests.asyncSetUp(self)
        self.s._state='NEW';self.s._loop=None
        owner=self.s._owner;c=self.s._consumer
        owner._state,owner._replay,owner._response=self.s._stores
        expected=SimpleNamespace(epoch=1,instance_id='first-owner')
        owner._expected=expected;c._expected=expected
        c._stores=self.s._stores;c._connections=self.s._connections
        c._owner=owner;c._loop=asyncio.get_running_loop();c._source_proof=object()
        c._borrowed_service=True;c._local_admission=True;c._admission_phase='PREPARED'
        c._binding=SimpleNamespace(_stage='PREPARED',
            _authority=SimpleNamespace(epoch=1,instance_id='first-owner'))
        c._runner=SimpleNamespace(_caller_owned_state=c._binding)
        c._adapter=SimpleNamespace()
        class BundleFixture:pass
        bundle=BundleFixture();bundle._prepared_binding=c._binding
        bundle._prepared_runner=c._runner;bundle._adapter=c._adapter
        c._bundle=bundle;c._binding._api_bundle=bundle;c._adapter._borrowed_api_stores=bundle
        def native_drain():
            self.trace.append('native_failure_seal');c._binding._stage='DRAINING'
            return {'state':'DRAINING'}
        bundle.begin_drain=native_drain
        c.status=lambda:{'state':c._stage}
        c.seal_service_admission=lambda:admission.seal_service_failure(c)
        c.publish_api_adapter=lambda:self.trace.append('publish')
        def activate():
            self.trace.append('activate');c._binding._stage=c._admission_phase='ACTIVE'
        c.activate_admission=activate
        async def prepare(*args,**kwargs):
            owner._prepared_consumer=c;return c
        owner.prepare_runtime=prepare
        class StartTransportFixture:
            def __init__(native_self,native_bundle,*,configure_app):
                native_self.bundle=native_bundle;native_self.phase='NEW'
            async def start(native_self):
                native_self.phase='READY';self.trace.append('listener')
                return {'state':'READY','listenerAuthorized':True,'endpoint':'http://127.0.0.1:45550'}
            def check(native_self,**kwargs):return c._binding._authority
            def status(native_self):
                return {'state':'DRAINING' if c._binding._stage=='DRAINING' else native_self.phase}
            def check_binding(native_self,*,for_admission=False,**kwargs):
                if for_admission and c._binding._stage!='ACTIVE':
                    raise NativeBusyFixture('fixture_native_admission_closed')
                return c._binding._authority
        patch.dict(sys.modules,native_modules(StartTransportFixture,NativeBusyFixture,BundleFixture)).start()
        self.verify=patch('gateway_prepared_consumer.verify_imports').start()
        self.s._execution.require_ready=AsyncMock()
        self.config=SimpleNamespace(extra={'host':'127.0.0.1','port':45550,'key':'k'*32,
            'model_name':self.s._execution.policy.model})

    async def test_post_bind_readiness_failure_seals_native_admission_and_retains_owner(self):
        self.s._execution.require_ready.side_effect=RuntimeError('fixture_readiness_failed')
        with self.assertRaisesRegex(RuntimeError,'fixture_readiness_failed'):
            await self.s.start(object(),self.config)
        self.assertEqual(self.trace,['publish','activate','listener','native_failure_seal'])
        self.assertEqual(self.s.status()['state'],'UNKNOWN')
        self.assertEqual(self.s._consumer._binding._stage,'DRAINING')
        self.assertEqual(self.s._consumer._admission_phase,'DRAINING')
        with self.assertRaisesRegex(NativeBusyFixture,'admission_closed'):
            self.s._transport.check_binding(for_admission=True)
        self.assertFalse(self.s._held._finished)
        for connection in self.connections:self.assertEqual(connection.execute('SELECT 1').fetchone(),(1,))

    async def test_source_revalidation_failure_does_not_prevent_native_seal(self):
        self.verify.side_effect=RuntimeError('fixture_source_changed')
        with self.assertRaisesRegex(RuntimeError,'fixture_source_changed'):
            await self.s.start(object(),self.config)
        self.assertEqual(self.s._consumer._binding._stage,'DRAINING')
        self.assertEqual(self.s.status()['reason'],'fixture_source_changed')
        self.assertIsNone(self.s.status()['admissionSealReason'])

    async def test_failed_seal_preserves_original_error_and_closes_overall_gate(self):
        original=RuntimeError('fixture_original_failure')
        self.s._execution.require_ready.side_effect=original
        def fail():raise RuntimeError('fixture_seal_failed')
        self.s._consumer._bundle.begin_drain=fail
        with self.assertRaises(RuntimeError) as observed:await self.s.start(object(),self.config)
        self.assertIs(observed.exception,original)
        status=self.s.status()
        self.assertEqual((status['reason'],status['admissionSealReason']),
                         ('fixture_original_failure','fixture_seal_failed'))
        with self.assertRaisesRegex(service.ServiceRuntimeRejected,'not_ready'):
            self.s.require_admission(transport=self.s._transport,app=self.s._app,
                                     adapter=self.s._consumer._adapter)
        self.assertFalse(self.s._held._finished)

    async def test_bound_listener_waits_for_overall_ready_and_start_observer_can_disconnect(self):
        entered,release=asyncio.Event(),asyncio.Event()
        async def pending():entered.set();await release.wait()
        self.s._execution.require_ready.side_effect=pending
        observer=asyncio.create_task(self.s.start(object(),self.config))
        await entered.wait()
        with self.assertRaisesRegex(service.ServiceRuntimeRejected,'not_ready'):
            self.s.require_admission(transport=self.s._transport,app=self.s._app,
                                     adapter=self.s._consumer._adapter)
        original=self.s._start_task;observer.cancel()
        with self.assertRaises(asyncio.CancelledError):await observer
        self.assertFalse(original.cancelled());release.set()
        result=await original
        self.assertEqual(result['state'],'READY')
        with self.assertRaisesRegex(service.ServiceRuntimeRejected,'already_started'):
            await self.s.start(object(),self.config)


if __name__ == '__main__':
    unittest.main()
