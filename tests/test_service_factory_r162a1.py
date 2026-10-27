"""Fixed factory contracts and original-owner composition with declared ports.

Real harness factory/startup/consumer/service/R160 control, local selected config
bytes and SQLite close probes execute. See service_factory_fixtures_r162a1 for
the explicit native config/import, lease/preflight, HTTP, broker, publication,
executor and runtime-retirement doubles. No native installation, aiohttp, model,
provider, mounted profile or kernel-confinement acceptance is claimed here.
"""
import asyncio
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]
import execution_boundary as execution
import gateway_prepared_consumer as consumer
import gateway_service_control as control
import gateway_service_factory as factory
import gateway_service_handoff as handoff
import gateway_service_profile as profile
import gateway_service_runtime as runtime
import gateway_store_startup as startup
import host_principal
import service_factory_fixtures_r162a1 as fixtures
import service_profile_fixtures_r161a1 as profiles
import test_gateway_store_startup as store_fixture
import test_service_handoff_r161a1 as wire_fixture

NATIVE_COMPONENTS = factory._native_components


class SettingsTests(unittest.TestCase):
    def test_explicit_settings_are_pure_and_copy_original_document(self):
        raw = fixtures.document()
        with patch('builtins.open', side_effect=AssertionError('no I/O')), \
                patch.object(Path, 'stat', side_effect=AssertionError('no I/O')):
            value = factory.validate_settings(raw)
        self.assertIs(type(value.policy), factory.HostGatePolicy)
        self.assertEqual(value.policy.allowed_models, frozenset(('fixture-model',)))
        self.assertEqual(value.execution, raw['plugins']['entries'][factory.PLUGIN_ID]['settings']['execution'])
        raw['platforms']['api_server']['extra']['key'] = 'changed'
        self.assertEqual(value.api['key'], 'k' * 32)

    def test_discovery_and_unknown_settings_cannot_widen_fixed_factory(self):
        for mutate in (
            lambda x: x.update(factory='caller.module'),
            lambda x: x['plugins'].update(enabled=['foreign']),
            lambda x: x['plugins']['entries'].update(foreign={}),
            lambda x: x['plugins']['entries'][factory.PLUGIN_ID].update(source='bundled'),
            lambda x: x['plugins']['entries'][factory.PLUGIN_ID]['settings'].update(extra={}),
            lambda x: x['platforms'].update(telegram={}),
        ):
            raw = fixtures.document(); mutate(raw)
            with self.subTest(raw=tuple(raw)), self.assertRaises(factory.ServiceFactoryRejected):
                factory.validate_settings(raw)

    def test_watchdogs_sessions_json_and_multiplexing_require_explicit_disable(self):
        for field, value in (('multiplex_profiles', None), ('multiplex_profiles', True),
                ('write_sessions_json', True), ('loop_watchdog', True),
                ('systemd_watchdog_seconds', 1), ('systemd_watchdog_seconds', False)):
            raw = fixtures.document(); raw['gateway'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(factory.ServiceFactoryRejected):
                factory.validate_settings(raw)

    def test_model_route_policy_and_api_share_one_explicit_model(self):
        for section, key, value in (
                ('model', 'default', 'other'), ('model', 'provider', 'openai'),
                ('model', 'base_url', 'https://external.invalid/v1'),
                ('api', 'model_name', 'other'), ('api', 'host', '0.0.0.0'),
                ('api', 'port', True), ('api', 'port', 65536)):
            raw = fixtures.document()
            target = raw['model'] if section == 'model' else raw['platforms']['api_server']['extra']
            target[key] = value
            with self.subTest(section=section, key=key), self.assertRaises(factory.ServiceFactoryRejected):
                factory.validate_settings(raw)

    def test_credentials_are_explicit_distinct_and_native_model_matches_provider(self):
        for api, bearer, signing in (('k' * 31, 'p' * 32, 'd' * 64),
                ('k' * 32, 'k' * 32, 'd' * 64), ('d' * 64, 'p' * 32, 'd' * 64),
                ('k' * 32, 'd' * 64, 'd' * 64), ('k' * 32, 'contains space' * 4, 'd' * 64)):
            raw = fixtures.document(); raw['platforms']['api_server']['extra']['key'] = api
            settings = raw['plugins']['entries'][factory.PLUGIN_ID]['settings']['execution']
            settings['provider_bearer'] = raw['model']['api_key'] = bearer
            settings['provider_broker']['signing_key'] = signing
            with self.assertRaises(factory.ServiceFactoryRejected):factory.validate_settings(raw)
        raw = fixtures.document(); raw['model']['api_key'] = 'different' * 8
        with self.assertRaises(factory.ServiceFactoryRejected):factory.validate_settings(raw)

    def test_override_and_separate_broker_principal_cannot_be_inferred(self):
        for mutate in (
            lambda entry: entry.update(allow_tool_override=False),
            lambda entry: entry['settings']['execution']['provider_broker'].update(principal_contract=None),
            lambda entry: entry['settings']['execution']['provider_broker']['principal_contract'].update(brokerUid=1001),
            lambda entry: entry['settings']['execution']['provider_broker']['principal_contract'].update(version=True),
        ):
            raw = fixtures.document(); mutate(raw['plugins']['entries'][factory.PLUGIN_ID])
            with self.assertRaises(factory.ServiceFactoryRejected):factory.validate_settings(raw)

    def test_read_scope_is_bounded_canonical_posix_txt_only(self):
        for allowed in ([], ['/x.txt'] * 2, ['/x.py'], ['relative.txt'], ['/a/../x.txt'],
                ['/a//x.txt'], ['//x.txt'], ['/a\\x.txt'], [True], ['/x.txt'] * 33):
            raw = fixtures.document()
            raw['plugins']['entries'][factory.PLUGIN_ID]['settings']['execution']['allowed_read_files'] = allowed
            with self.subTest(allowed=allowed[:2]), self.assertRaises(factory.ServiceFactoryRejected):
                factory.validate_settings(raw)

    def test_additional_execution_transport_or_tool_family_is_refused(self):
        for extra in ('upstream_base_url', 'isolated_read', 'record_request_view'):
            raw = fixtures.document()
            raw['plugins']['entries'][factory.PLUGIN_ID]['settings']['execution'][extra] = None
            with self.assertRaises(factory.ServiceFactoryRejected):factory.validate_settings(raw)
        raw = fixtures.document(); raw['platform_toolsets']['api_server'].append('terminal')
        with self.assertRaises(factory.ServiceFactoryRejected):factory.validate_settings(raw)


class DocumentTests(unittest.TestCase):
    def setUp(self):
        profiles.set_up_profile(self, config=fixtures.document())
        self.attempt = factory._Attempt(SimpleNamespace(service=self.expectation), None, 'new', fixtures.SID)
        actor = (os.getpid(), self.uid, self.gid, threading.get_ident())
        self.actor_patch = patch.object(startup.live.profiles, '_actor', return_value=actor)
        self.actor_patch.start(); self.addCleanup(self.actor_patch.stop)

    def test_selected_config_uses_real_bounded_fd_path_without_native_or_lease(self):
        before = (self.home / profile.CONFIG_NAME).read_bytes()
        original = profile._read_aux
        with patch.object(profile, '_read_aux', wraps=original) as read, \
                patch.object(factory, '_native_components') as native, \
                patch.object(startup.live.profiles, 'reserve_profile') as reserve:
            result = factory.read_document(self.attempt)
        self.assertEqual(result, fixtures.document())
        self.assertEqual((self.home / profile.CONFIG_NAME).read_bytes(), before)
        self.assertTrue(read.called)
        self.assertTrue(all(call.args[1] == profile.CONFIG_NAME
                            and call.args[3] == profile.MAX_CONFIG_BYTES for call in read.call_args_list))
        native.assert_not_called(); reserve.assert_not_called()

    def test_same_length_content_change_does_not_reuse_config_receipt(self):
        path = self.home / profile.CONFIG_NAME
        path.write_bytes(self.config_bytes.replace(b'fixture-model', b'changed-model'))
        with self.assertRaises((factory.ServiceFactoryRejected, profile.ServiceProfileRejected)):
            factory.read_document(self.attempt)

    def test_equal_content_replacement_does_not_reuse_file_identity(self):
        path = self.home / profile.CONFIG_NAME
        replacement = self.home / 'new-config'
        replacement.write_bytes(self.config_bytes); replacement.chmod(0o600)
        replacement.replace(path)
        with self.assertRaises((factory.ServiceFactoryRejected, profile.ServiceProfileRejected)):
            factory.read_document(self.attempt)

    def test_drift_after_selected_read_is_rechecked_before_return(self):
        original = profile._read_aux
        calls = 0
        def changed(*args):
            nonlocal calls
            raw = original(*args); calls += 1
            # First read is the opening check; the second is the returned data.
            if calls == 2:(self.home / profile.CONFIG_NAME).write_bytes(b'{}')
            return raw
        with patch.object(profile, '_read_aux', side_effect=changed), self.assertRaises(
                (factory.ServiceFactoryRejected, profile.ServiceProfileRejected)):
            factory.read_document(self.attempt)


class NativeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.home = str(Path(temporary.name).resolve())
        self.attempt = factory._Attempt(SimpleNamespace(service=SimpleNamespace(home=self.home)),
            None, 'new', fixtures.SID)
        self.attempt.settings = factory.validate_settings(fixtures.document())
        self.native = fixtures.NativeConfigPorts(self.home, fixtures.document())
        self.components = self.stack.enter_context(patch.object(factory, '_native_components',
            side_effect=self.native.components))
        self.check = self.stack.enter_context(patch.object(factory, '_config_check'))
        self.verify = self.stack.enter_context(patch.object(consumer, 'verify_imports'))
        self.principal = self.stack.enter_context(patch.object(host_principal, 'gateway_identity'))
        self.stack.enter_context(patch.object(execution, 'scoped_file', side_effect=lambda name, _: name))
        self.stack.enter_context(patch.dict(os.environ, HERMES_HOME=self.home))

    def test_direct_native_constructors_keep_one_manager_context_and_boundary(self):
        factory._configure(self.attempt)
        a = self.attempt
        self.assertIs(type(a.execution), execution.ExecutionBoundary)
        self.assertIs(a.context._manager, a.manager); self.assertIs(a.context.manifest, a.manifest)
        self.assertEqual(a.manager.scope_key, self.home)
        self.assertEqual((a.manifest.name, a.manifest.key, a.manifest.source),
                         (factory.PLUGIN_ID, factory.PLUGIN_ID, 'project'))
        self.assertEqual(a.gateway_config.sessions_dir, Path(self.home) / 'sessions')
        self.assertFalse(a.gateway_config.loop_watchdog or a.gateway_config.write_sessions_json
                         or a.gateway_config.multiplex_profiles)
        self.assertEqual(a.gateway_config.systemd_watchdog_seconds, 0)
        self.assertEqual(a.api_config.extra, a.settings.api)
        self.assertEqual(a.execution.policy.model, next(iter(a.settings.policy.allowed_models)))
        self.assertEqual([call[0] for call in self.native.calls[:5]],
                         ['gateway', 'platform', 'manager', 'manifest', 'context'])
        self.native.config.load_config_readonly.assert_called_once_with()
        self.principal.assert_called_once_with(a.settings.execution['provider_broker']['principal_contract'])
        self.verify.assert_called_once_with(a.source_proof)
        self.assertGreaterEqual(self.check.call_count, 3)

    def test_effective_native_fields_cannot_drift_or_enable_discovery(self):
        changes = (
            lambda x: x['gateway'].update(loop_watchdog=True),
            lambda x: x['model'].update(default='other'),
            lambda x: x['platforms']['api_server']['extra'].update(key='other' * 8),
            lambda x: x['plugins'].update(enabled=['foreign']),
            lambda x: x['plugins']['entries'][factory.PLUGIN_ID].update(allow_tool_override=False),
            lambda x: x['platform_toolsets'].update(api_server=['file', 'terminal']),
        )
        for mutate in changes:
            self.native.effective = fixtures.document(); mutate(self.native.effective)
            with self.assertRaises(factory.ServiceFactoryRejected):factory._configure(self.attempt)
        self.principal.assert_not_called()

    def test_nested_boolean_is_not_equal_to_integer_in_native_settings(self):
        self.native.effective['plugins']['entries'][factory.PLUGIN_ID]['settings'][
            'execution']['provider_broker']['principal_contract']['version'] = True
        with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'native_plugin_settings'):
            factory._configure(self.attempt)

    def test_native_context_must_resolve_same_entry_not_another_scope(self):
        self.native.context_settings = copy.deepcopy(
            self.native.effective['plugins']['entries'][factory.PLUGIN_ID]['settings'])
        self.native.context_settings['execution']['provider_bearer'] = 'x' * 32
        with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'native_context_settings'):
            factory._configure(self.attempt)
        self.principal.assert_not_called()

    def test_native_home_override_and_worker_snapshot_refuse_before_loader(self):
        for path, snapshot in ((Path(self.home) / 'other.yaml', None),
                               (Path(self.home) / profile.CONFIG_NAME, {})):
            self.native.config.get_config_path = lambda: path
            self.native.config._worker_config_snapshot = lambda: snapshot
            with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'native_config_path'):
                factory._configure(self.attempt)
        self.native.config.load_config_readonly.assert_not_called()

    def test_loader_exception_still_checks_selected_raw_config_and_home(self):
        self.native.config.load_config_readonly.side_effect = RuntimeError('native_loader_failed')
        with self.assertRaisesRegex(RuntimeError, 'native_loader_failed'):
            factory._configure(self.attempt)
        self.assertEqual(self.check.call_count, 2)
        self.principal.assert_not_called()

    def test_selected_source_qualification_precedes_new_native_config_imports(self):
        order = []
        selection = object(); self.attempt.record.service.selection = selection
        exported = dict(zip(('GatewayConfig', 'PlatformConfig'), self.native.types[:2]))
        class LookupModule(ModuleType):
            def __getattr__(self, name):
                if name not in exported:raise AttributeError(name)
                order.append('native-' + name)
                return exported[name]
        gateway = ModuleType('gateway'); gateway.__path__ = []
        module = LookupModule('gateway.config')
        modules = self.native.modules() | {'gateway': gateway, 'gateway.config': module}
        self.check.side_effect = lambda _: order.append('config-check')
        self.verify.side_effect = lambda _: order.append('verify-imports')
        def qualify(**kwargs):
            order.append('qualify-sources'); return self.native.proof
        with patch.dict(sys.modules, modules), patch.object(consumer, 'qualify_sources',
                side_effect=qualify) as qualify_sources:
            result = NATIVE_COMPONENTS(self.attempt)
        self.assertEqual(result, (*self.native.types, self.native.config))
        self.assertIs(self.attempt.source_proof, self.native.proof)
        qualify_sources.assert_called_once_with(local_admission=True, canonical_api=True,
            finite_turn=True, service_selection=selection)
        self.assertEqual(order[0:2], ['qualify-sources', 'config-check'])
        self.assertLess(order.index('native-GatewayConfig'), order.index('verify-imports'))
        self.assertEqual(order[-2:], ['verify-imports', 'config-check'])


class CompositionBase(unittest.TestCase):
    setUp = fixtures.set_up
    mark = store_fixture.Lifecycle.mark
    make_store = store_fixture.Lifecycle.make_store

    def start_pending(self):
        self.attempt.task = self.loop.create_task(factory._run(self.attempt))

    def assert_retained(self):
        self.assertIs(factory._attempt, self.attempt)
        self.assertIs(self.attempt.loop, self.loop)
        self.assertFalse(self.loop.is_closed() or self.attempt.task.done())
        self.assertFalse(self.attempt.task.cancelled())
        self.finish.assert_not_called()
        for store in self.created:
            store.close.assert_not_called()
            self.assertEqual(store._conn.execute('SELECT 1').fetchone(), (1,))
        with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'process_already_owned'):
            factory.execute(self.record, self.mount, fixtures.INSTANCE, fixtures.SID)


class CompositionTests(CompositionBase):
    def test_real_owner_service_and_control_chain_closes_only_original_generation(self):
        result = fixtures.run(self)
        a = self.attempt; owner = a.owner; service = a.service
        self.assertEqual(a.stage, 'CLOSED')
        self.assertEqual([frame['type'] for frame in self.channel.frames],
                         ['ready', 'reply', 'reply', 'final'])
        self.assertEqual(result, self.channel.frames[-1])
        self.assertEqual(result['owner']['close']['physicalStoresClosed'], 3)
        self.assertFalse(result['owner']['close']['imageLeaseReleasedHere'])
        self.start.assert_called_once_with(owner); self.epoch.assert_called_once()
        self.reserve.assert_called_once_with(self.home, self.mount)
        self.assertIs(type(owner), startup.NativeStoreStartup)
        self.assertIs(type(service), runtime.BorrowedServiceOwner)
        self.assertIs(type(service._consumer), consumer.PreparedRuntimeConsumer)
        self.assertIs(type(control._attempt), control.ServiceControl)
        self.assertIs(owner._service_profile, self.record.service)
        self.assertIs(owner._held, a.held); self.assertIs(a.held, self.held)
        self.assertIs(owner._prepared_consumer, self.consumer)
        self.assertIs(service._consumer, self.consumer)
        self.assertIs(service._loop, self.loop); self.assertIs(control._attempt.loop, self.loop)
        self.assertIs(service._owner, owner); self.assertIs(control._attempt.service, service)
        self.assertIs(owner._expected, self.consumer._expected)
        self.assertIs(self.consumer._binding._authority.runner, self.consumer._runner)
        self.assertIs(self.consumer._runner.session_authority, self.consumer._binding._authority)
        self.assertEqual((owner._expected.epoch, owner._expected.instance_id), (2, fixtures.INSTANCE))
        self.assertEqual(len(self.created), 3)
        self.assertTrue(all(a is b for a, b in zip(self.created, service._stores)))
        self.assertTrue(all(a is b for a, b in zip(service._connections, self.consumer._connections)))
        self.assertIs(a.execution.context, a.context)
        self.assertIs(self.host_binding[3]['execution'], a.execution)
        self.assertIs(self.host_binding[3]['service_owner'], service)
        self.assertEqual(self.prepare_inputs[3], dict(local_admission=True, canonical_api=True,
                         finite_turn=True, borrowed_service=True))
        self.assertLess(self.events.index('epoch'), self.events.index('native-config'))
        self.assertLess(self.events.index('native-config'), self.events.index('prepare'))
        self.assertEqual([e for e in self.events if e in ('transport', 'runtime', 'api',
            'finish-drain', 'detach-api', 'detach-runner', 'executor', 'close-response',
            'close-replay', 'close-state', 'lease')], ['transport', 'runtime', 'api',
            'finish-drain', 'detach-api', 'detach-runner', 'executor', 'close-response',
            'close-replay', 'close-state', 'lease'])
        self.assertFalse(asyncio.all_tasks(self.loop))
        for connection in service._connections:
            with self.assertRaises(sqlite3.ProgrammingError):connection.execute('SELECT 1')

    def test_known_busy_close_reobserves_same_owner_without_second_start_or_epoch(self):
        self.busy_close = True; self.channel.actions = iter(enumerate(('close', 'close'), 1))
        result = fixtures.run(self)
        self.assertEqual([f['owner']['state'] for f in self.channel.frames],
                         ['READY', 'DRAINING', 'CLOSED'])
        self.assertEqual(result['type'], 'final')
        self.assertEqual(self.events.count('transport'), 2)
        self.start.assert_called_once(); self.epoch.assert_called_once(); self.finish.assert_called_once()

    def test_ready_and_final_frames_do_not_serialize_private_settings(self):
        fixtures.run(self)
        raw = b'\n'.join(control.canonical(frame) for frame in self.channel.frames)
        for secret in (b'k' * 32, b'p' * 32, b'd' * 64, b'principal_contract', b'allowed_read_files'):
            self.assertNotIn(secret, raw)

    def test_unknown_cleanup_keeps_real_handles_loop_driver_and_original_owner(self):
        self.cleanup_error = True
        self.channel.actions = iter(enumerate(('close',), 1))
        self.start_pending()
        fixtures.advance(self, lambda: control._attempt is not None and control._attempt._fenced)
        self.assertEqual(self.attempt.service._state, 'UNKNOWN')
        self.assertIs(control._attempt.service, self.attempt.service)
        self.assertIsNone(control._attempt.final)
        self.assertEqual([f['type'] for f in self.channel.frames], ['ready'])
        self.assertEqual(self.events.count('transport'), 1)
        self.assertNotIn('runtime', self.events)
        self.assert_retained()

    def test_final_cannot_be_reused_for_replaced_owner_or_lease(self):
        result = fixtures.run(self)
        owner = self.attempt.owner
        self.attempt.owner = object()
        with self.assertRaises(factory.ServiceFactoryRejected):factory._validate_final(self.attempt, result)
        self.attempt.owner = owner; self.attempt.held = object()
        with self.assertRaises(factory.ServiceFactoryRejected):factory._validate_final(self.attempt, result)


class RetentionTests(CompositionBase):
    def test_reservation_exception_is_unknown_and_does_not_allow_second_attempt(self):
        self.reserve.side_effect = RuntimeError('fixture_reserve_unknown')
        self.start_pending()
        with redirect_stderr(io.StringIO()):
            fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual((self.attempt.stage, self.attempt.failed_stage), ('UNKNOWN', 'PROFILE_RESERVING'))
        self.assertTrue(self.attempt.effects_started)
        self.assertIsNone(self.attempt.held); self.assertIsNone(self.attempt.owner)
        self.assert_retained(); self.components.assert_not_called()

    def test_owner_constructor_failure_retains_returned_lease(self):
        with patch.object(startup, 'NativeStoreStartup', side_effect=RuntimeError('fixture_ctor_unknown')):
            self.start_pending()
            with redirect_stderr(io.StringIO()):
                fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual(self.attempt.failed_stage, 'OWNER_CONSTRUCTING')
        self.assertIs(self.attempt.held, self.held)
        self.assertIsNone(self.attempt.owner); self.assert_retained()

    def test_original_start_failure_retains_owner_and_never_replays_epoch(self):
        self.epoch.side_effect = RuntimeError('fixture_epoch_ack_lost')
        self.start_pending()
        with redirect_stderr(io.StringIO()):
            fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual(self.attempt.failed_stage, 'OWNER_STARTING')
        self.assertTrue(self.attempt.owner.status()['epochMayHaveAdvanced'])
        self.start.assert_called_once(); self.epoch.assert_called_once()
        self.components.assert_not_called(); self.assert_retained()

    def test_native_configuration_failure_retains_exact_started_owner_and_source_objects(self):
        def interrupted(attempt):
            result = self.native_config.components(attempt)
            attempt.manager = result[2](scope_key=str(self.home))
            raise RuntimeError('fixture_native_config_unknown')
        self.components.side_effect = interrupted
        self.start_pending()
        with redirect_stderr(io.StringIO()):
            fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual(self.attempt.failed_stage, 'NATIVE_CONFIGURING')
        self.assertEqual(self.attempt.owner._stage, 'VERIFIED')
        self.assertIs(self.attempt.source_proof, self.native_config.proof)
        self.assertEqual(self.attempt.manager.scope_key, str(self.home))
        self.assertIsNone(self.attempt.service)
        self.assert_retained()

    def test_partially_constructed_service_remains_reachable_from_original_owner(self):
        original = runtime.BorrowedServiceOwner
        constructed = []
        def interrupted(owner, **kwargs):
            constructed.append(original(owner, **kwargs))
            raise RuntimeError('fixture_service_constructor_unknown')
        with patch.object(factory, 'BorrowedServiceOwner', side_effect=interrupted):
            self.start_pending()
            with redirect_stderr(io.StringIO()):
                fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual(self.attempt.failed_stage, 'SERVICE_CONSTRUCTING')
        self.assertIs(self.attempt.owner._service_owner, constructed[0])
        self.assertIs(constructed[0]._held, self.held)
        self.assertIsNone(self.attempt.service)
        self.assert_retained()

    def test_lost_stderr_cannot_abort_unknown_retention(self):
        self.components.side_effect = RuntimeError('private details must not escape')
        output = Mock(); output.write.side_effect = BrokenPipeError('closed observer')
        self.start_pending()
        with patch.object(sys, 'stderr', output):
            fixtures.advance(self, lambda: self.attempt.retained is not None)
        self.assertEqual(self.attempt.reason, 'service_factory_unavailable')
        self.assert_retained()


class ExecuteTests(unittest.TestCase):
    def setUp(self):
        wire_fixture.ServiceHandoffContract.setUp(self)
        self.mount = startup.live.mounts.ExpectedMount(11, (7, 0), '/profile', handoff.TARGET, 'ext4')
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(factory, '_attempt', None))
        # makedev is a Linux receiver port. Keep shape/identity checks portable.
        self.stack.enter_context(patch.object(factory.os, 'makedev', lambda major, minor: 1792,
                                            create=True))
        self.read = self.stack.enter_context(patch.object(factory, 'read_document',
                                                        return_value=fixtures.document()))

    def call(self):
        return factory.execute(self.value, self.mount, fixtures.INSTANCE, fixtures.SID)

    def test_pre_effect_schema_refusal_is_bounded_no_loop_lease_and_no_retry(self):
        self.read.return_value = {'secret': 'must not escape'}
        with patch.object(asyncio, 'new_event_loop') as loop, \
                patch.object(startup.live.profiles, 'reserve_profile') as lease:
            with self.assertRaisesRegex(factory.ServiceFactoryRejected, '^service_factory_config_fields$'):
                self.call()
        a = factory._attempt
        self.assertEqual((a.stage, a.failed_stage), ('REFUSED', 'CONFIG_VALIDATING'))
        self.assertFalse(a.effects_started); self.assertIsNone(a.held)
        loop.assert_not_called(); lease.assert_not_called()
        with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'process_already_owned'):self.call()

    def test_wrong_fixed_mount_or_generation_rejected_before_reserved_attempt(self):
        for mount, instance, service_id in ((replace(self.mount, root='/other'), fixtures.INSTANCE, fixtures.SID),
                (self.mount, self.value.state.instance_id, fixtures.SID),
                (self.mount, fixtures.INSTANCE, 'B' * 32)):
            with self.assertRaises((factory.ServiceFactoryRejected, control.ServiceControlRejected)):
                factory.execute(self.value, mount, instance, service_id)
            self.assertIsNone(factory._attempt)
        self.read.assert_not_called()

    def test_existing_running_loop_refuses_before_any_ownership(self):
        loop = asyncio.new_event_loop(); self.addCleanup(loop.close)
        async def attempt():
            with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'dedicated_loop_required'):
                self.call()
        loop.run_until_complete(attempt())
        self.assertIsNone(factory._attempt); self.read.assert_not_called()

    def test_clean_outer_loop_closes_without_printing_returned_final_again(self):
        # Outer-loop/stdio port only. Full real lifecycle is tested above.
        result = {'fixtureFinalAlreadyWritten': True}
        async def clean(a):
            print('native fixture diagnostic')
            a.final = result; a.stage = 'CLOSED'
            return result
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(factory, '_run', side_effect=clean), redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertIs(self.call(), result)
        self.assertTrue(factory._attempt.loop.is_closed())
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), 'native fixture diagnostic\n')

    def test_outer_interruption_and_broken_stderr_preserve_same_loop_and_task(self):
        class TestEscape(BaseException):pass
        original_owner = object()
        async def interrupted(a):
            a.effects_started = True; a.owner = original_owner; a.stage = 'NATIVE_CONFIGURING'
            a.loop.stop()
            await a.loop.create_future()
        observed = []
        def inspect_retention(a):
            observed.append(a)
            self.assertIs(a.owner, original_owner)
            self.assertFalse(a.loop.is_closed() or a.task.done() or a.task.cancelled())
            raise TestEscape()
        broken = Mock(); broken.write.side_effect = BrokenPipeError()
        with patch.object(factory, '_run', side_effect=interrupted), \
                patch.object(factory, '_retain_loop', side_effect=inspect_retention), \
                patch.object(sys, 'stderr', broken), self.assertRaises(TestEscape):
            self.call()
        a = factory._attempt
        self.addCleanup(lambda: fixtures.dispose_test_loop(a.loop))
        self.addCleanup(lambda: asyncio.set_event_loop(None))
        self.assertEqual(observed, [a]); self.assertEqual(a.stage, 'UNKNOWN')
        with self.assertRaisesRegex(factory.ServiceFactoryRejected, 'process_already_owned'):self.call()

    def test_closed_original_loop_parks_same_attempt_without_new_loop_or_owner(self):
        a = factory._Attempt(self.value, self.mount, fixtures.INSTANCE, fixtures.SID)
        a.owner, a.held = object(), object()
        a.loop = asyncio.new_event_loop(); a.loop.close()
        with patch.object(factory, '_park_without_loop', return_value='fixture-park') as park, \
                patch.object(asyncio, 'new_event_loop') as replacement:
            self.assertEqual(factory._retain_loop(a), 'fixture-park')
        park.assert_called_once_with(a); replacement.assert_not_called()

    def test_last_resort_custody_reaches_blocking_wait_without_replacement_resources(self):
        # A fresh test-only child is killed by subprocess.run's bounded timeout.
        # Product code itself must stay parked with the original object graph.
        script = '''
import asyncio, pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd() / 'packages/claw-hermes'))
import gateway_service_factory as factory
a = factory._Attempt(None, None, 'fixture-new', 'a' * 32)
a.loop = asyncio.new_event_loop(); a.loop.close()
a.owner = owner = object(); a.held = held = object()
Event = factory.threading.Event
class ObservedEvent(Event):
    def wait(self, *args, **kwargs):
        assert a.owner is owner and a.held is held and a.loop.is_closed()
        assert factory.threading.active_count() == 1
        print('ORIGINAL_CLOSED_LOOP_BLOCKING_CUSTODY', flush=True)
        return super().wait(*args, **kwargs)
def forbidden(): raise AssertionError('replacement loop')
factory.threading.Event = ObservedEvent
asyncio.new_event_loop = forbidden
factory._retain_loop(a)
raise AssertionError('custody returned')
'''
        with self.assertRaises(subprocess.TimeoutExpired) as observed:
            subprocess.run([sys.executable, '-c', script], cwd=ROOT,
                           capture_output=True, timeout=3)
        self.assertEqual(observed.exception.stdout.splitlines(),
                         [b'ORIGINAL_CLOSED_LOOP_BLOCKING_CUSTODY'])
        self.assertFalse(observed.exception.stderr)

    def test_diagnostic_exception_string_and_flush_failures_are_non_throwing(self):
        class BadReason:
            def __str__(self):raise RuntimeError('private exception renderer')
        a = factory._Attempt(self.value, self.mount, fixtures.INSTANCE, fixtures.SID)
        broken = Mock(); broken.flush.side_effect = OSError('lost stderr flush')
        with patch.object(sys, 'stderr', broken):
            factory._unknown(a, factory.ServiceFactoryRejected(BadReason()))
        self.assertEqual((a.stage, a.reason), ('UNKNOWN', 'service_factory_unavailable'))

    def test_native_exception_tokens_cannot_be_echoed_as_credential_shaped_reasons(self):
        for message in ('p' * 32, 'd' * 64, 'private_configuration_value'):
            a = factory._Attempt(self.value, self.mount, fixtures.INSTANCE, fixtures.SID)
            output = io.StringIO()
            with redirect_stderr(output):factory._unknown(a, RuntimeError(message))
            self.assertNotIn(message, output.getvalue())
            self.assertEqual(a.reason, 'service_factory_unavailable')
        self.assertEqual(factory._reason(factory.ServiceFactoryRejected('service_factory_config_fields')),
                         'service_factory_config_fields')


if __name__ == '__main__':
    unittest.main()
