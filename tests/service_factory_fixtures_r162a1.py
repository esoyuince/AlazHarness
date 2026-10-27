"""R162 composition ports, explicitly not an installed native runtime.

The real factory, startup/consumer/service/control classes and real temporary
config files, descriptors and SQLite close probes run. Native source imports,
native config classes/loader, kernel lease/preflight, HTTP, broker readiness,
publication and runtime retirement are declared ports. The file-tool pathname
port is doubled to keep the POSIX wire contract portable on Windows. No aiohttp,
listener, model, provider, mounted profile or real kernel confinement is needed.
"""
import asyncio
import copy
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]
import execution_boundary as execution
import gateway_prepared_consumer as consumer
import gateway_service_control as control
import gateway_service_factory as factory
import gateway_service_handoff as handoff
import gateway_service_profile as profile
import gateway_store_startup as startup
import host_principal
import service_profile_fixtures_r161a1 as profiles
import test_service_profile_binding_r161a1 as original

SID = 'a' * 32
INSTANCE = 'r162-fixture-new'


def document():
    return {
        'model': {'provider': 'custom', 'default': 'fixture-model',
            'base_url': 'http://127.0.0.1:45550/alaz/provider/v1', 'api_key': 'p' * 32},
        'gateway': {'multiplex_profiles': False, 'write_sessions_json': False,
            'loop_watchdog': False, 'systemd_watchdog_seconds': 0},
        'platform_toolsets': {'api_server': ['file']},
        'platforms': {'api_server': {'enabled': True, 'extra': {
            'host': '127.0.0.1', 'port': 45550, 'key': 'k' * 32,
            'model_name': 'fixture-model'}}},
        'plugins': {'enabled': [], 'entries': {'alaz-host-gate': {
            'allow_tool_override': True, 'settings': {
                'policy': {'allowed_models': ['fixture-model'], 'max_issued': 4,
                    'max_dispatches': 2, 'validity_seconds': 30},
                'execution': {'policy': {
                    'model': 'fixture-model', 'max_provider_calls': 3, 'max_tool_calls': 2,
                    'input_ceiling_tokens': 100, 'output_ceiling_tokens': 20,
                    'total_token_limit': 360, 'total_cost_microusd': 900,
                    'input_rate_microusd_per_million': 2000000,
                    'output_rate_microusd_per_million': 5000000},
                    'provider_bearer': 'p' * 32,
                    'allowed_read_files': ['/readonly/fixture.txt'],
                    'provider_broker': {'socket_path': '/run/alaz-broker/egress.sock',
                        'broker_id': 'b' * 32, 'route_fingerprint': 'c' * 64,
                        'signing_key': 'd' * 64, 'principal_contract': {
                            'version': 1, 'enabled': True, 'gatewayUid': 1001,
                            'brokerUid': 1002, 'socketGroupGid': 1003,
                            'hostUserNamespace': 'user:[123]'}}}}}}},
    }


class NativeConfigPorts:
    """Constructor/get_config contract doubles from the selected native sources."""
    def __init__(self, home, selected):
        self.home, self.selected = home, copy.deepcopy(selected)
        self.effective = copy.deepcopy(selected)
        self.context_settings = None
        self.calls = []
        self.proof = {'nativeSourcePort': True}
        outer = self

        class GatewayConfig:
            def __init__(self, **kwargs):
                outer.calls.append(('gateway', kwargs))
                self.__dict__.update(kwargs)

        class PlatformConfig:
            def __init__(self, **kwargs):
                outer.calls.append(('platform', kwargs))
                self.__dict__.update(kwargs)

        class PluginManager:
            def __init__(self, *, scope_key):
                outer.calls.append(('manager', scope_key))
                self.scope_key = str(Path(scope_key).resolve())

        class PluginManifest:
            def __init__(self, **kwargs):
                outer.calls.append(('manifest', kwargs))
                self.__dict__.update(kwargs)

        class PluginContext:
            def __init__(self, manifest, manager):
                outer.calls.append(('context', manifest, manager))
                self.manifest, self._manager = manifest, manager

            @property
            def plugin_id(self):
                return self.manifest.key or self.manifest.name

            def get_config(self, key, default=None):
                outer.calls.append(('get_config', key))
                value = outer.context_settings
                if value is None:
                    value = outer.effective['plugins']['entries'][factory.PLUGIN_ID]['settings']
                return value.get(key, default)

        self.types = GatewayConfig, PlatformConfig, PluginManager, PluginManifest, PluginContext
        self.config = SimpleNamespace(get_config_path=lambda: Path(self.home) / profile.CONFIG_NAME,
            _worker_config_snapshot=lambda: None,
            load_config_readonly=Mock(side_effect=lambda: self.effective))

    def components(self, attempt):
        attempt.source_proof = self.proof
        return (*self.types, self.config)

    def modules(self):
        package = ModuleType('hermes_cli'); package.__path__ = []
        plugins = ModuleType('hermes_cli.plugins')
        plugins.PluginManager, plugins.PluginManifest, plugins.PluginContext = self.types[2:]
        package.plugins, package.config = plugins, self.config
        return {'hermes_cli': package, 'hermes_cli.plugins': plugins,
                'hermes_cli.config': self.config}


class NativeBusy(RuntimeError):
    pass


class MemoryChannel:
    """Only the FD transport is doubled; real R160 frame/control logic runs."""
    def __init__(self, actions=('status', 'drain', 'close')):
        self.actions = iter(enumerate(actions, 1))
        self.frames = []
        self.before_read = None

    async def write(self, frame):
        self.frames.append(control.validate_frame(copy.deepcopy(frame), service_id=SID))

    async def read(self):
        if self.before_read is not None:
            self.before_read()
        sequence, action = next(self.actions)
        return {'protocol': control.PROTOCOL, 'serviceId': SID, 'sequence': sequence,
                'requestId': control.request_id(SID, sequence), 'action': action}


def set_up(case):
    original.set_up_startup(case)
    case.document = document()
    case.config_bytes = profiles.canonical(case.document)
    (case.home / profile.CONFIG_NAME).write_bytes(case.config_bytes)
    case.expectation = replace(case.expectation, config_size=len(case.config_bytes),
        config_sha256=hashlib.sha256(case.config_bytes).hexdigest())
    case.record = handoff.ServiceStartup(case.expected, case.want, case.expectation)
    case.attempt = factory._Attempt(case.record, case.mount, INSTANCE, SID)
    case.attempt.settings = factory.validate_settings(case.document)
    case.loop = asyncio.new_event_loop(); case.attempt.loop = case.loop
    case.addCleanup(lambda: dispose_test_loop(case.loop))
    case.stack.enter_context(patch.object(factory, '_attempt', case.attempt))
    case.stack.enter_context(patch.object(control, '_attempt', None))
    case.reserve = case.stack.enter_context(patch.object(startup.live.profiles,
        'reserve_profile', return_value=case.held))
    case.held._finished = False; case.held._owner.homes = (str(case.home),)
    def finish():
        case.events.append('lease')
        case.held._finished = True; case.held._owner.homes = ()
    case.finish.side_effect = finish
    actual_start = startup.NativeStoreStartup.start
    case.start = case.stack.enter_context(patch.object(startup.NativeStoreStartup,
        'start', autospec=True, side_effect=actual_start))
    case.native_config = NativeConfigPorts(str(case.home), case.document)
    def components(attempt):
        case.events.append('native-config')
        case.assertEqual(attempt.owner._stage, 'VERIFIED')
        return case.native_config.components(attempt)
    case.components = case.stack.enter_context(patch.object(factory, '_native_components',
                                                           side_effect=components))
    case.stack.enter_context(patch.dict(os.environ, HERMES_HOME=str(case.home)))
    case.stack.enter_context(patch.dict(sys.modules, case.native_config.modules()))
    case.principal = case.stack.enter_context(patch.object(host_principal, 'gateway_identity'))
    case.stack.enter_context(patch.object(execution, 'scoped_file', side_effect=lambda name, _: name))
    case.verify = case.stack.enter_context(patch.object(consumer, 'verify_imports'))
    case.ready = case.stack.enter_context(patch.object(execution.ExecutionBoundary,
        'require_ready', new=AsyncMock()))
    case.busy_close = False; case.cleanup_error = False
    case.channel = MemoryChannel()
    case.fd = case.stack.enter_context(patch.object(control, 'FDChannel', return_value=case.channel))

    def bind(app, adapter, policy, **kwargs):
        case.events.append('host-bind')
        case.host_binding = (app, adapter, policy, kwargs)
    module = ModuleType('host_gate_plugin'); module.bind_host_gate = bind
    case.stack.enter_context(patch.dict(sys.modules, {module.__name__: module}))

    async def prepare(owner, gateway_config, api_config, **options):
        case.events.append('prepare')
        case.prepare_inputs = (owner, gateway_config, api_config, options)
        value = consumer.PreparedRuntimeConsumer(owner, **options)
        owner._prepared_consumer = value
        original.attach_native_cleanup_fixture(case, value)
        case.consumer = value
        binding, bundle = value._binding, value._bundle
        value._source_proof = case.native_config.proof
        def transition(phase, label):
            case.events.append(label); binding._stage = phase
            return {'state': phase}
        def publish():
            case.events.append('publish')
            value._publication_phase = bundle._publication_state = 'PUBLISHED'
            bundle._publication_registry = value._runner.adapters
            bundle._publication_profiles = value._runner._profile_adapters
            bundle._publication_loop = binding._admission_loop = value._loop
            bundle._publication_config = value._adapter.config = api_config
            value._adapter._owner_profile = value._adapter._shared_listener_profile = None
        value.publish_api_adapter = publish
        bundle.activate_admission = lambda: transition('ACTIVE', 'activate')
        bundle.begin_drain = lambda: transition('DRAINING', 'drain')
        bundle.finish_drain = lambda: transition('DRAINED', 'finish-drain')
        async def runtime():
            case.events.append('runtime'); return {'state': 'IDLE_RUNTIME_RETIRED'}
        value.retire_idle_runtime = runtime
        value.retire_idle_api_sessions = lambda: (
            case.events.append('api') or {'state': 'IDLE_API_SESSIONS_RETIRED'})
        disconnect = value._adapter.disconnect
        async def withdraw():
            await disconnect(); bundle._publication_state = 'WITHDRAWN'
        value._adapter.disconnect = withdraw

        class Transport:
            def __init__(self, native_bundle, *, configure_app):
                case.assertIs(native_bundle, bundle)
                self.configure = configure_app; self.phase = 'NEW'; self.app = {}
            async def start(self):
                self.configure(self.app, value._adapter, self)
                case.events.append('listener'); self.phase = 'READY'
                return {'state': 'READY', 'listenerAuthorized': True,
                        'endpoint': 'http://127.0.0.1:45550'}
            def status(self):
                phase = ('DRAINING' if self.phase == 'READY' and
                         binding._stage == 'DRAINING' else self.phase)
                return {'state': phase}
            def check_binding(self, *, for_admission=False, app=None, adapter=None):
                if app is not None:case.assertIs(app, self.app)
                if adapter is not None:case.assertIs(adapter, value._adapter)
                if for_admission and binding._stage != 'ACTIVE':
                    raise NativeBusy('fixture_admission_closed')
                return binding._authority
            def check(self, **kwargs):
                return self.check_binding(**kwargs)
            async def retire_idle(self):
                case.events.append('transport')
                if case.busy_close:
                    case.busy_close = False
                    raise NativeBusy('fixture_transport_busy')
                if case.cleanup_error:
                    self.phase = 'UNKNOWN'
                    raise NativeBusy('fixture_transport_unknown')
                self.phase = 'RETIRED'
                return {'state': 'RETIRED', 'callerStoresClosed': False}

        module = ModuleType('gateway.platforms.api_server_borrowed_transport')
        module.BorrowedHTTPTransport = Transport
        case.stack.enter_context(patch.dict(sys.modules, {module.__name__: module}))
        native = sys.modules['gateway.platforms.api_server_borrowed']
        native.BorrowedStoreRejected = NativeBusy; native.BorrowedAPIStores = type(bundle)
        module = ModuleType('gateway.config')
        module.Platform = SimpleNamespace(API_SERVER=object())
        value._adapter.platform = module.Platform.API_SERVER
        case.stack.enter_context(patch.dict(sys.modules, {module.__name__: module}))
        return value
    case.prepare = case.stack.enter_context(patch.object(startup.NativeStoreStartup,
        'prepare_runtime', autospec=True, side_effect=prepare))
    async def join():case.events.append('executor')
    case.stack.enter_context(patch.object(case.loop, 'shutdown_default_executor', side_effect=join))


def run(case):
    case.attempt.task = case.loop.create_task(factory._run(case.attempt))
    # Test-only bounded observation; this callback is not a background task and
    # does not become part of the product's loop/retirement contract.
    stop = case.loop.call_later(15, case.loop.stop)
    try:
        return case.loop.run_until_complete(case.attempt.task)
    except RuntimeError as exc:
        state = case.attempt
        driver = control._attempt
        service = state.service
        raise AssertionError(('fixture composition did not terminate', state.stage,
            state.reason, getattr(driver, 'reason', None),
            getattr(service, '_state', None), getattr(service, '_last_reason', None))) from exc
    finally:
        stop.cancel()


def advance(case, predicate):
    for _ in range(80):
        if predicate():return
        case.loop.run_until_complete(asyncio.sleep(0))
    raise AssertionError('fixture state did not arrive within bounded loop turns')


def dispose_test_loop(loop):
    """Test teardown only; production deliberately has no such cancellation."""
    if loop.is_closed():return
    for _ in range(3):
        tasks = asyncio.all_tasks(loop)
        if not tasks:break
        for task in tasks:task.cancel()
        loop.run_until_complete(asyncio.sleep(0))
    if asyncio.all_tasks(loop):raise AssertionError('fixture pending task leak')
    loop.close()
