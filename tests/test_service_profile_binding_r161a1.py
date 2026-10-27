"""Explicit service-profile binding on real harness code and real local files.

Profile bytes, identities and SQLite close probes are real. Native imports,
constructors, preflight/live gates, publication and the config-loader/registry
ports are explicit fixture doubles. No native runtime, kernel confinement,
listener, provider or model is exercised or accepted by this module.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import replace
import os
from pathlib import Path
import sqlite3
import sys
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]
import execution_boundary as execution
import gateway_consumer_admission as admission
import gateway_prepared_consumer as consumer
import gateway_service_profile as profile
import gateway_service_runtime as runtime
import gateway_store_startup as startup
import service_profile_fixtures_r161a1 as fixtures
import test_execution_profile_qa3156 as execution_fixture
import test_gateway_store_startup as startup_fixture
import test_three_store_lifecycle_l113f6 as three_fixture

ORIGINAL_LAYOUT_INSPECT = startup.layout.inspect_profile
SERVICE_OPTIONS = dict(local_admission=True, canonical_api=True,
                       finite_turn=True, borrowed_service=True)


def set_up_startup(case):
    three_fixture.ThreeStoreLifecycle.setUp(case)
    fixtures.set_up_profile(case)
    case.actor = (os.getpid(), case.uid, case.gid, threading.get_ident())
    case.actor_fn.return_value = case.actor
    case.held._actor = case.actor
    case.held._home = case.home
    case.expected = replace(case.expected, epoch=case.expectation.epoch,
        instance_id=case.expectation.instance_id,
        state_identity=case.expectation.database_identities[0],
        replay_identity=case.expectation.database_identities[1])
    case.want = replace(case.want,
        response_identity=case.expectation.database_identities[2])
    case.epoch.side_effect = lambda *a, **k: case.mark('epoch', 2)


def new_owner(case, **overrides):
    options = dict(instance_id='r161-fixture-new', response_expected=case.want,
                   prepared_layout=True, service_profile=case.expectation)
    options.update(overrides)
    return startup.NativeStoreStartup(case.held, case.mount, case.expected, **options)


def drift_config(case):
    (case.home / profile.CONFIG_NAME).write_bytes(b'{}')


class StartupServiceProfileTests(unittest.TestCase):
    setUp = set_up_startup
    mark = startup_fixture.Lifecycle.mark
    make_store = startup_fixture.Lifecycle.make_store
    obj = new_owner

    def test_explicit_service_keeps_original_owner_and_three_handles(self):
        owner = self.obj()
        result = owner.start()
        self.assertIs(type(owner), startup.NativeStoreStartup)
        self.assertIs(owner._service_profile, self.expectation)
        self.layout.assert_not_called()
        self.assertEqual(result['epochObserved'], 2)
        self.assertIs(result['runtimeAdmissionAuthorized'], False)
        self.assertEqual(len(self.created), 3)
        owner.close()
        self.assertEqual(self.events[-3:], ['close-response', 'close-replay', 'close-state'])
        self.finish.assert_not_called()

    def test_default_layout_still_refuses_selected_service_files(self):
        self.layout.side_effect = ORIGINAL_LAYOUT_INSPECT
        owner = self.obj(service_profile=None)
        with patch.object(profile, 'inspect_profile') as selected:
            with self.assertRaises(startup.StoreStartupRejected):
                owner.start()
        selected.assert_not_called()
        self.pre.assert_not_called()
        self.native.assert_not_called()
        owner.close()

    def test_service_requires_prepared_three_store_and_excludes_retained(self):
        for options in ({'prepared_layout': False}, {'response_expected': None},
                        {'retained_profile': object()}):
            with self.subTest(options=tuple(options)), self.assertRaises(startup.StoreStartupRejected):
                self.obj(**options)
        self.pre.assert_not_called()
        self.native.assert_not_called()

    def test_home_epoch_instance_and_each_database_must_match_original_owner(self):
        candidates = [replace(self.expectation, home=str(self.home / 'other')),
                      replace(self.expectation, epoch=2),
                      replace(self.expectation, instance_id='other-previous')]
        for index in range(3):
            identities = list(self.expectation.database_identities)
            identities[index] = (self.device, 2**62 + index)
            candidates.append(replace(self.expectation, database_identities=tuple(identities)))
        for value in candidates:
            with self.subTest(value=value.database_identities), self.assertRaisesRegex(
                    startup.StoreStartupRejected, 'startup_service_profile_binding'):
                self.obj(service_profile=value)
        self.pre.assert_not_called()
        self.native.assert_not_called()

    def test_other_selected_generation_refused_before_preflight(self):
        value = replace(self.expectation, selection=replace(
            self.selection, selection_sha256='f' * 64))
        with self.assertRaisesRegex(startup.StoreStartupRejected, 'startup_service_source_changed'):
            self.obj(service_profile=value)
        self.pre.assert_not_called()

    def test_removed_selected_receipt_cannot_downgrade_to_default_start(self):
        owner = self.obj()
        owner._service_profile = None
        with self.assertRaisesRegex(startup.StoreStartupRejected, 'startup_service_profile_changed'):
            owner.start()
        self.layout.assert_not_called()
        self.pre.assert_not_called()
        owner.close()

    def test_config_drift_before_start_refused_before_preflight(self):
        owner = self.obj()
        drift_config(self)
        with self.assertRaises(startup.StoreStartupRejected):
            owner.start()
        self.pre.assert_not_called()
        self.native.assert_not_called()
        owner.close()

    def test_preflight_config_drift_prevents_native_import(self):
        owner = self.obj()
        self.pre.side_effect = lambda *args: (drift_config(self) or
            {'state': 'COLD_STORES_PREFLIGHT_VERIFIED'})
        with self.assertRaises(startup.StoreStartupRejected):
            owner.start()
        self.native.assert_not_called()
        self.epoch.assert_not_called()
        owner.close()

    def test_import_config_drift_prevents_first_constructor(self):
        owner = self.obj()
        self.native.side_effect = lambda: (drift_config(self) or
            (self.State, self.Replay, self.runtime))
        with self.assertRaises(startup.StoreStartupRejected):
            owner.start()
        self.State.assert_not_called()
        self.epoch.assert_not_called()
        owner.close()

    def test_each_returned_constructor_is_followed_by_config_recheck(self):
        # Each constructor uses a fresh one-shot startup owner.
        for name in ('state', 'replay', 'response'):
            with self.subTest(name=name):
                (self.home / profile.CONFIG_NAME).write_bytes(self.config_bytes)
                owner = self.obj()
                constructor = {'state': self.State, 'replay': self.Replay,
                               'response': self.Response}[name]
                constructor.side_effect = lambda *a, **k: (drift_config(self) or self.make_store(name))
                with self.assertRaises(startup.StoreStartupRejected):
                    owner.start()
                self.assertFalse(owner.status()['unknownConstructorEffects'])
                self.epoch.assert_not_called()
                owner.close()
                constructor.side_effect = lambda *a, _name=name, **k: self.make_store(_name)
                self.finish.assert_not_called()

    def test_epoch_drift_preserves_advanced_epoch_and_known_close(self):
        owner = self.obj()
        self.epoch.side_effect = lambda *a, **k: (drift_config(self) or 2)
        with self.assertRaises(startup.StoreStartupRejected):
            owner.start()
        self.assertEqual(owner.status()['epochObserved'], 2)
        self.assertTrue(owner.status()['epochMayHaveAdvanced'])
        self.assertFalse(owner.status()['storageReady'])
        owner.close()
        self.assertEqual(owner.status()['state'], 'CLOSED')


class RegistryFixture:
    def __init__(self, authority):
        self.launch = authority
        self.multiplexed = False

    def __len__(self):
        return 1

    def for_home(self, home):
        return self.launch


def attach_native_cleanup_fixture(case, value):
    """Synthetic borrowed native objects; real harness detach/close executes."""
    binding = SimpleNamespace(_stage='PREPARED', home=case.home)
    runner = SimpleNamespace(_caller_owned_state=binding, _running=False,
        _executor=None, _housekeeping_executor=None, _loop_heartbeat_task=None,
        _stop_task=None, _draining=False)
    for name in ('adapters', '_profile_adapters', '_sessions',
                 '_completion_notification_batch_tasks', '_completion_notification_batches',
                 '_session_db_handles'):
        setattr(runner, name, {})
    for name in ('_background_tasks', '_fatal_handler_tasks', '_completion_deliveries_inflight',
                 '_completion_notification_batch_flush_tasks'):
        setattr(runner, name, set())
    runner._startup_restore_tasks = []; runner._startup_restore_queue = []
    runner._agent_cache = OrderedDict()
    authority = SimpleNamespace(runner=runner, db=value._stores[0],
        epoch=value._expected.epoch, instance_id=value._expected.instance_id,
        profile_id=str(case.home), retiring=False, retired=False)
    for name in ('sessions', 'waiters', 'events', 'pending_results', 'pending_deliveries',
                 'adopted', 'executing', 'pending_stops', 'pending_steers'):
        setattr(authority, name, {})
    authority.native_waiters = set(); authority.cancel_obligations = set()
    binding._authority = authority; binding._registry = RegistryFixture(authority)
    binding._runner = runner
    binding.status = lambda: {'state': binding._stage}
    runner.session_authority = authority; runner.session_authorities = binding._registry
    runner.session_store = SimpleNamespace(_borrowed_session_state=SimpleNamespace(_closed=False))
    bundle = SimpleNamespace(_stage='ATTACHED', _publication_state='NEW',
        _prepared_binding=binding, _prepared_runner=runner)
    bundle.status = lambda: {'state': bundle._stage}
    bundle.select = lambda adapter, home: value._stores
    adapter = SimpleNamespace(gateway_runner=runner, _borrowed_api_stores=bundle,
        _session_db_cache_closed=False, _running=False, _app=None, _site=None, _runner=None)
    binding._api_bundle = bundle; bundle._adapter = adapter

    async def disconnect():
        case.events.append('detach-api')
        bundle._stage = 'DETACHED'; adapter._session_db_cache_closed = True

    def close_runner():
        case.events.append('detach-runner')
        binding._stage = 'DETACHED'; authority.retiring = authority.retired = True
        runner._draining = True; runner.session_store._borrowed_session_state._closed = True
        binding._descriptor = dict(instance_id=value._expected.instance_id,
            authority_epoch=value._expected.epoch, runtime_protocol=1,
            state='caller_detached', capabilities=[], served_profiles=[])
        runner.session_runtime_descriptor = binding._descriptor

    adapter.disconnect = AsyncMock(side_effect=disconnect)
    runner.close_all_session_db_handles = Mock(side_effect=close_runner)
    value._binding, value._runner, value._bundle, value._adapter = binding, runner, bundle, adapter
    value._stage = 'ATTACHED'; value._source_proof = {'fixtureNativeImports': True}
    publication = ModuleType('gateway.run_borrowed_publication')
    publication.check_publication = Mock()
    borrowed = ModuleType('gateway.platforms.api_server_borrowed')
    borrowed._quiescent = Mock()
    case.stack.enter_context(patch.dict(sys.modules, {publication.__name__: publication,
                                                    borrowed.__name__: borrowed}))
    case.stack.enter_context(patch.object(consumer, 'verify_imports'))
    case.stack.enter_context(patch.object(admission, 'verify_imports'))
    return value


class ConsumerServiceProfileTests(unittest.IsolatedAsyncioTestCase):
    setUp = set_up_startup
    mark = startup_fixture.Lifecycle.mark
    make_store = startup_fixture.Lifecycle.make_store
    obj = new_owner

    def reserve(self):
        owner = self.obj(); owner.start()
        value = consumer.PreparedRuntimeConsumer(owner, **SERVICE_OPTIONS)
        owner._prepared_consumer = value
        return owner, value

    async def test_explicit_profile_requires_service_options_before_reservation(self):
        owner = self.obj(); owner.start()
        with self.assertRaisesRegex(startup.StoreStartupRejected, 'startup_service_profile_requires_service'):
            await owner.prepare_runtime(object(), object(), local_admission=True,
                                        canonical_api=True, finite_turn=True)
        self.assertIsNone(owner._prepared_consumer)
        with self.assertRaisesRegex(consumer.PreparedConsumerRejected, 'consumer_service_profile_requires_service'):
            consumer.PreparedRuntimeConsumer(owner, local_admission=True, canonical_api=True, finite_turn=True)
        owner.close()

    async def test_prepare_runtime_drift_has_no_consumer_slot_effect(self):
        owner = self.obj(); owner.start(); drift_config(self)
        with patch.object(consumer.PreparedRuntimeConsumer, 'prepare') as prepare:
            with self.assertRaises(profile.ServiceProfileRejected):
                await owner.prepare_runtime(object(), object(), **SERVICE_OPTIONS)
        prepare.assert_not_called(); self.assertIsNone(owner._prepared_consumer)
        owner.close()

    async def test_reserved_consumer_drift_precedes_native_qualification_and_prepare(self):
        owner, value = self.reserve(); drift_config(self)
        with patch.object(consumer, 'qualify_sources') as qualify, patch.object(consumer, 'native_types') as native:
            with self.assertRaises(profile.ServiceProfileRejected):
                await value.prepare(object(), object())
        qualify.assert_not_called(); native.assert_not_called()
        self.assertIs(owner._prepared_consumer, value)
        self.assertEqual(value._stage, 'FAILED_UNKNOWN')
        with self.assertRaises(consumer.PreparedConsumerRejected):
            owner.close()

    async def test_consumer_selection_must_equal_profile_generation(self):
        owner = self.obj(); owner.start()
        with patch.object(profile.sources, 'load_selection', return_value=replace(
                self.selection, selection_sha256='f' * 64)):
            with self.assertRaisesRegex(consumer.PreparedConsumerRejected, 'consumer_service_profile_selection'):
                consumer.PreparedRuntimeConsumer(owner, **SERVICE_OPTIONS)
        self.assertIsNone(owner._prepared_consumer); owner.close()

    async def test_replacement_or_removal_of_receipt_refuses_before_config_read(self):
        owner, value = self.reserve()
        for replacement in (None, replace(self.expectation)):
            owner._service_profile = replacement
            with patch.object(profile, 'check_config') as check:
                with self.assertRaisesRegex(consumer.PreparedConsumerRejected, 'consumer_service_profile_changed'):
                    value.check()
            check.assert_not_called()
        owner._service_profile = self.expectation

    async def test_drift_blocks_check_publication_and_activation_before_native_calls(self):
        owner, value = self.reserve()
        value._stage = 'ATTACHED'; drift_config(self)
        import gateway_consumer_api as api
        with patch.object(admission, 'check') as check, patch.object(api, 'publish') as publish, \
                patch.object(admission, 'activate') as activate:
            for operation in (value.check, value.publish_api_adapter, value.activate_admission):
                with self.subTest(operation=operation.__name__), self.assertRaises(profile.ServiceProfileRejected):
                    operation()
        check.assert_not_called(); publish.assert_not_called(); activate.assert_not_called()

    async def test_check_rechecks_after_native_check(self):
        owner, value = self.reserve(); value._stage = 'ATTACHED'
        with patch.object(admission, 'check', side_effect=lambda c: drift_config(self)) as check:
            with self.assertRaises(profile.ServiceProfileRejected):
                value.check()
        check.assert_called_once_with(value)

    async def test_changed_config_still_allows_known_detach_and_store_close(self):
        owner, value = self.reserve()
        attach_native_cleanup_fixture(self, value)
        self.assertEqual(value.check()['state'], 'ATTACHED')
        drift_config(self)
        with self.assertRaises(profile.ServiceProfileRejected):
            value.check()
        with patch.object(profile, 'check_config', side_effect=AssertionError('cleanup must not re-admit config')):
            self.assertEqual((await value.detach())['state'], 'DETACHED')
            owner.close()
        self.assertEqual(owner.status()['state'], 'CLOSED')
        self.assertLess(self.events.index('detach-api'), self.events.index('detach-runner'))
        self.assertLess(self.events.index('detach-runner'), self.events.index('close-response'))
        for store in self.created:
            with self.assertRaises(sqlite3.ProgrammingError):
                store._conn.execute('SELECT 1')
        self.finish.assert_not_called()


class ApplicationFixture(dict):
    def __init__(self):
        super().__init__()
        self.router = SimpleNamespace(add_get=Mock(), add_post=Mock())


class TransportFixture:
    pass


class ExecutionServiceProfileTests(unittest.TestCase):
    def setUp(self):
        execution_fixture.LiveProfileConsistencyTests.setUp(self)
        fixtures.set_up_profile(self, config=self.cfg)
        self.native_owner = object.__new__(startup.NativeStoreStartup)
        self.native_owner._actor = (os.getpid(), self.uid, self.gid, threading.get_ident())
        self.native_owner._held = SimpleNamespace(_home=self.home)
        self.native_owner._service_profile = self.expectation
        self.native_owner._service_profile_binding = self.expectation
        environment_patch = patch.dict(os.environ, {'HERMES_HOME': self.expectation.home})
        environment_patch.start(); self.addCleanup(environment_patch.stop)
        self.service_owner = object.__new__(runtime.BorrowedServiceOwner)
        self.service_owner._owner = self.native_owner
        self.service_owner._held = self.native_owner._held
        self.native_owner._service_owner = self.service_owner
        transport_module = ModuleType('gateway.platforms.api_server_borrowed_transport')
        transport_module.BorrowedHTTPTransport = TransportFixture
        module_patch = patch.dict(sys.modules, {transport_module.__name__: transport_module})
        module_patch.start(); self.addCleanup(module_patch.stop)
        register_patch = patch.object(self.boundary.tools, 'register')
        register_patch.start(); self.addCleanup(register_patch.stop)
        self.config_path = Mock(return_value=self.home / profile.CONFIG_NAME)
        path_patch = patch.object(sys.modules['hermes_cli.config'], 'get_config_path',
                                  self.config_path, create=True)
        path_patch.start(); self.addCleanup(path_patch.stop)
        self.worker_snapshot = Mock(return_value=None)
        snapshot_patch = patch.object(sys.modules['hermes_cli.config'], '_worker_config_snapshot',
                                      self.worker_snapshot, create=True)
        snapshot_patch.start(); self.addCleanup(snapshot_patch.stop)
        self.adapter = self.boundary.adapter; self.boundary.adapter = None
        self.app = ApplicationFixture(); self.transport = TransportFixture()
        self.boundary.bind(self.app, self.adapter, service_transport=self.transport,
                           service_owner=self.service_owner)
        self.loader = Mock(side_effect=lambda: copy.deepcopy(self.cfg))
        loader_patch = patch.object(sys.modules['hermes_cli.config'], 'load_config_readonly', self.loader)
        loader_patch.start(); self.addCleanup(loader_patch.stop)

    def test_original_loader_is_bracketed_by_selected_config_checks(self):
        with patch.object(profile, 'check_config', wraps=profile.check_config) as check:
            self.boundary.validate_profile()
        self.assertEqual(check.call_count, 2)
        self.loader.assert_called_once_with()
        self.registry.assert_called()

    def test_changed_file_prevents_loader_and_policy_observation(self):
        drift_config(self)
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_not_called(); self.registry.assert_not_called()

    def test_file_change_inside_real_loader_port_is_rejected_after_return(self):
        def load():
            drift_config(self)
            return copy.deepcopy(self.cfg)
        self.loader.side_effect = load
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_called_once_with(); self.registry.assert_not_called()

    def test_loader_exception_still_runs_postcheck_without_replacing_unchanged_error(self):
        self.loader.side_effect = RuntimeError('fixture loader failure')
        with patch.object(profile, 'check_config', wraps=profile.check_config) as check:
            with self.assertRaisesRegex(RuntimeError, 'fixture loader failure'):
                self.boundary.validate_profile()
        self.assertEqual(check.call_count, 2)

    def test_removed_replaced_or_deleted_receipt_cannot_disable_bound_guard(self):
        for mode in ('removed', 'replaced', 'deleted'):
            if mode == 'deleted':del self.native_owner._service_profile
            else:self.native_owner._service_profile = None if mode == 'removed' else replace(self.expectation)
            with self.subTest(mode=mode), self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
                self.boundary.validate_profile()
            self.native_owner._service_profile = self.expectation
        self.loader.assert_not_called()

    def test_replaced_service_owner_cannot_disable_bound_guard(self):
        self.boundary.service_owner = None
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_not_called()

    def test_other_source_generation_refuses_before_loader(self):
        with patch.object(profile.sources, 'load_selection', return_value=replace(
                self.selection, selection_sha256='f' * 64)):
            with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
                self.boundary.validate_profile()
        self.loader.assert_not_called()

    def test_changed_home_environment_refuses_before_loader(self):
        for home in (None, str(self.home / 'other')):
            if home is None:os.environ.pop('HERMES_HOME', None)
            else:os.environ['HERMES_HOME'] = home
            with self.subTest(home=home), self.assertRaisesRegex(
                    execution.ExecutionDenied, 'execution_service_profile_changed'):
                self.boundary.validate_profile()
        self.loader.assert_not_called()

    def test_loader_home_environment_change_is_observed_after_return(self):
        def load():
            os.environ['HERMES_HOME'] = str(self.home / 'other')
            return copy.deepcopy(self.cfg)
        self.loader.side_effect = load
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_called_once_with(); self.registry.assert_not_called()

    def test_worker_thread_home_drift_refuses_without_main_thread_lease_check(self):
        os.environ['HERMES_HOME'] = str(self.home / 'other')
        with patch.object(self.native_owner, '_owned', side_effect=AssertionError('main-thread lease check')) as owned:
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
                    pool.submit(self.boundary.validate_profile).result(timeout=10)
        owned.assert_not_called(); self.loader.assert_not_called()

    def test_native_context_home_override_refuses_even_with_matching_environment(self):
        self.config_path.return_value = self.home / 'other' / profile.CONFIG_NAME
        self.assertEqual(os.environ['HERMES_HOME'], self.expectation.home)
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_not_called()

    def test_loader_context_path_change_is_observed_after_return(self):
        def load():
            self.config_path.return_value = self.home / 'other' / profile.CONFIG_NAME
            return copy.deepcopy(self.cfg)
        self.loader.side_effect = load
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_called_once_with(); self.registry.assert_not_called()

    def test_worker_context_path_override_refuses_without_thread_bound_lease(self):
        main_thread = threading.get_ident()
        self.config_path.side_effect = lambda: ((self.home if threading.get_ident() == main_thread
                                                else self.home / 'other') / profile.CONFIG_NAME)
        with patch.object(self.native_owner, '_owned', side_effect=AssertionError('main-thread lease check')) as owned:
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
                    pool.submit(self.boundary.validate_profile).result(timeout=10)
        owned.assert_not_called(); self.loader.assert_not_called()

    def test_worker_config_snapshot_refused_before_selected_file_loader(self):
        self.worker_snapshot.return_value = copy.deepcopy(self.cfg)
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_not_called()

    def test_loader_worker_snapshot_change_is_observed_after_return(self):
        def load():
            self.worker_snapshot.return_value = copy.deepcopy(self.cfg)
            return copy.deepcopy(self.cfg)
        self.loader.side_effect = load
        with self.assertRaisesRegex(execution.ExecutionDenied, 'execution_service_profile_changed'):
            self.boundary.validate_profile()
        self.loader.assert_called_once_with(); self.registry.assert_not_called()

    def test_worker_thread_uses_config_proof_without_main_thread_lease_check(self):
        with patch.object(self.native_owner, '_owned', side_effect=AssertionError('main-thread lease check')) as owned:
            with ThreadPoolExecutor(max_workers=1) as pool:
                self.assertIsNone(pool.submit(self.boundary.validate_profile).result(timeout=10))
        owned.assert_not_called(); self.loader.assert_called_once_with()

    def test_selected_bytes_do_not_replace_existing_loaded_model_policy(self):
        changed = copy.deepcopy(self.cfg)
        changed['model']['base_url'] = 'http://127.0.0.1:45813/v1'
        self.loader.side_effect = None; self.loader.return_value = changed
        with self.assertRaisesRegex(execution.ExecutionDenied, 'model_route_not_guarded'):
            self.boundary.validate_profile()
        self.loader.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
