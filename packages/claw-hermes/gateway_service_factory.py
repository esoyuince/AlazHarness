"""Fixed composition of the selected profile, original owner and R160 driver.

Only the sibling projected receiver calls ``execute``. The private selected
config is read with the service profile's bounded FD rules; it is never carried
in a control frame. This module does not discover plugins, load a caller-named
factory, construct another runner/store, or perform a model/provider request.

Raw config validation precedes ownership. After profile reservation is attempted,
errors retain this process's one attempt and event loop, including failures before
the control driver exists. Only the original driver's clean final permits return
and loop closure. The image lease remains the supervisor's responsibility.
"""
from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import threading

import gateway_service_handoff as handoff
import gateway_service_profile as profile
import gateway_store_startup as startup
import gateway_service_control as control
from gateway_service_runtime import BorrowedServiceOwner
from host_gate import HostGatePolicy
from execution_boundary import ExecutionBoundary
from execution_budget import ExecutionPolicy
from provider_egress import BrokerLink

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ID = 'alaz-host-gate'
_attempt = None


class ServiceFactoryRejected(RuntimeError):
    """Bounded diagnostics; no config values, paths or credentials."""


def require(value, reason):
    if not value:
        raise ServiceFactoryRejected(reason)


def _copy(value):
    return json.loads(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                 ensure_ascii=True, allow_nan=False))


def _same(value, expected):
    # Python equality considers True == 1, including nested dictionaries.
    # Config identity must retain JSON types as well as their values.
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False))


def _keys(value, names, reason):
    require(type(value) is dict and set(value) == set(names), reason)


def _reason(exc):
    # Native exceptions can contain credentials even when their text happens to
    # match a bounded lowercase token. Only this module's own constant refusal
    # codes may become diagnostics; stages retain the failure location privately.
    if type(exc) is not ServiceFactoryRejected:
        return 'service_factory_unavailable'
    try:
        text = str(exc)
    except BaseException:
        return 'service_factory_unavailable'
    return text if re.fullmatch('[a-z][a-z0-9_]{0,95}', text) else 'service_factory_unavailable'


@dataclass(frozen=True)
class ServiceSettings:
    """Private validated inputs, not a transferable authority or receipt."""
    document: dict
    policy: HostGatePolicy
    execution: dict
    api: dict


def validate_settings(document):
    """One explicit native-shaped configuration, with no fallback/discovery path.

    Native defaults/managed overlays are not globally qualified here. The fixed
    fields consumed by this factory are compared against the actual native loader
    later, after the original startup layout check and epoch transition.
    """
    try:
        _keys(document, ('model', 'gateway', 'platform_toolsets', 'platforms', 'plugins'),
              'service_factory_config_fields')
        model = document['model']
        _keys(model, ('provider', 'default', 'base_url', 'api_key'),
              'service_factory_model_fields')
        gateway = document['gateway']
        _keys(gateway, ('multiplex_profiles', 'write_sessions_json', 'loop_watchdog',
                        'systemd_watchdog_seconds'), 'service_factory_gateway_fields')
        require(all(gateway[name] is False for name in
                    ('multiplex_profiles', 'write_sessions_json', 'loop_watchdog'))
                and type(gateway['systemd_watchdog_seconds']) is int
                and gateway['systemd_watchdog_seconds'] == 0,
                'service_factory_gateway_scope')
        require(_same(document['platform_toolsets'], {'api_server': ['file']}),
                'service_factory_tool_scope')
        _keys(document['platforms'], ('api_server',), 'service_factory_platforms')
        platform = document['platforms']['api_server']
        _keys(platform, ('enabled', 'extra'), 'service_factory_api_fields')
        require(platform['enabled'] is True, 'service_factory_api_disabled')
        api = platform['extra']
        _keys(api, ('host', 'port', 'key', 'model_name'), 'service_factory_api_extra')
        require(api['host'] == '127.0.0.1' and type(api['port']) is int
                and 1 <= api['port'] <= 65535, 'service_factory_private_endpoint')
        require(type(api['key']) is str
                and re.fullmatch('[A-Za-z0-9._~-]{32,256}', api['key']) is not None,
                'service_factory_api_credential')
        plugins = document['plugins']
        _keys(plugins, ('enabled', 'entries'), 'service_factory_plugin_fields')
        require(type(plugins['enabled']) is list and not plugins['enabled'],
                'service_factory_plugin_discovery_not_qualified')
        _keys(plugins['entries'], (PLUGIN_ID,), 'service_factory_plugin_entries')
        entry = plugins['entries'][PLUGIN_ID]
        _keys(entry, ('allow_tool_override', 'settings'), 'service_factory_plugin_entry')
        require(entry['allow_tool_override'] is True, 'service_factory_explicit_override_required')
        settings = entry['settings']
        _keys(settings, ('policy', 'execution'), 'service_factory_plugin_settings')
        host = settings['policy']
        _keys(host, ('allowed_models', 'max_issued', 'max_dispatches', 'validity_seconds'),
              'service_factory_host_policy')
        require(type(host['allowed_models']) is list and len(host['allowed_models']) == 1
                and type(host['allowed_models'][0]) is str, 'service_factory_single_model')
        policy = HostGatePolicy(frozenset(host['allowed_models']), host['max_issued'],
                                host['max_dispatches'], host['validity_seconds'])
        execution = settings['execution']
        _keys(execution, ('policy', 'provider_bearer', 'allowed_read_files', 'provider_broker'),
              'service_factory_execution_fields')
        require(type(execution['policy']) is dict, 'service_factory_execution_policy')
        execution_policy = ExecutionPolicy(**execution['policy'])
        require(policy.allowed_models == frozenset((execution_policy.model,))
                and api['model_name'] == model['default'] == execution_policy.model
                and model['provider'] == 'custom'
                and model['base_url'] == 'http://127.0.0.1:' + str(api['port']) + '/alaz/provider/v1',
                'service_factory_model_binding')
        bearer = execution['provider_bearer']
        require(type(bearer) is str and re.fullmatch(r'[\x21-\x7e]{32,256}', bearer)
                and model['api_key'] == bearer, 'service_factory_provider_credential')
        broker = execution['provider_broker']
        _keys(broker, ('socket_path', 'broker_id', 'route_fingerprint', 'signing_key',
                       'principal_contract'), 'service_factory_broker_fields')
        require(type(broker['principal_contract']) is dict,
                'service_factory_broker_principal_required')
        link = BrokerLink(**broker)
        require(len({api['key'], bearer, link.signing_key}) == 3,
                'service_factory_separate_credentials')
        allowed = execution['allowed_read_files']
        require(type(allowed) is list and 1 <= len(allowed) <= 32
                and all(type(name) is str and len(name) <= 4096 and '\x00' not in name
                        and name.startswith('/') and not name.startswith('//')
                        and '\\' not in name and str(PurePosixPath(name)) == name
                        and '..' not in PurePosixPath(name).parts
                        and PurePosixPath(name).suffix == '.txt' for name in allowed)
                and len(set(allowed)) == len(allowed), 'service_factory_read_files')
        frozen = _copy(document)
        return ServiceSettings(frozen, policy,
            frozen['plugins']['entries'][PLUGIN_ID]['settings']['execution'],
            frozen['platforms']['api_server']['extra'])
    except ServiceFactoryRejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ServiceFactoryRejected('service_factory_config_invalid') from None


class _Attempt:
    def __init__(self, record, expected_mount, instance_id, service_id):
        self.record, self.expected_mount = record, expected_mount
        self.instance_id, self.service_id = instance_id, service_id
        self.stage = 'RESERVED'
        self.failed_stage = self.reason = None
        self.effects_started = False
        self.settings = self.held = self.owner = self.service = None
        self.loop = self.task = self.retained = None
        self.parked = None
        self.source_proof = self.manager = self.manifest = self.context = None
        self.gateway_config = self.api_config = self.execution = None
        self.final = None


def _config_check(attempt):
    receipt = attempt.record.service
    actor = startup.live.profiles._actor()
    require(actor[0] == os.getpid(), 'service_factory_other_actor')
    return profile.check_config(Path(receipt.home), uid=actor[1], gid=actor[2],
                                device=receipt.home_identity[0], expectation=receipt)


def read_document(attempt):
    """Return only the bytes read through the existing selected bounded FD path."""
    try:
        _config_check(attempt)
        receipt = attempt.record.service
        actor = startup.live.profiles._actor()
        home = Path(receipt.home)
        snapshot = {
            'profile': profile.layout._private(home.lstat(), actor[1], actor[2],
                                               receipt.home_identity[0], True),
            profile.CONFIG_NAME: profile.layout._private((home / profile.CONFIG_NAME).lstat(),
                actor[1], actor[2], receipt.home_identity[0], False),
        }
        metadata = snapshot[profile.CONFIG_NAME]
        require(metadata[:2] == receipt.config_identity and metadata[6] == receipt.config_size,
                'service_factory_config_identity')
        raw = profile._read_aux(home, profile.CONFIG_NAME, snapshot, profile.MAX_CONFIG_BYTES)
        require(hashlib.sha256(raw).hexdigest() == receipt.config_sha256,
                'service_factory_config_changed')
        profile._config_document(raw)
        value = json.loads(raw.decode('utf-8'))
        _config_check(attempt)
        return value
    except ServiceFactoryRejected:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ServiceFactoryRejected('service_factory_config_unavailable') from None


def _native_components(attempt):
    """Selected installed source qualification precedes new native config imports."""
    import gateway_prepared_consumer as consumer
    attempt.source_proof = consumer.qualify_sources(local_admission=True, canonical_api=True,
        finite_turn=True, service_selection=attempt.record.service.selection)
    _config_check(attempt)
    from gateway.config import GatewayConfig, PlatformConfig
    from hermes_cli.plugins import PluginManager, PluginManifest, PluginContext
    from hermes_cli import config
    consumer.verify_imports(attempt.source_proof)
    _config_check(attempt)
    return GatewayConfig, PlatformConfig, PluginManager, PluginManifest, PluginContext, config


def _native_home(attempt, config):
    home = attempt.record.service.home
    require(os.environ.get('HERMES_HOME') == home
            and str(config.get_config_path()) == str(Path(home) / profile.CONFIG_NAME)
            and config._worker_config_snapshot() is None,
            'service_factory_native_config_path')


def _native_settings(attempt, config):
    """Compare only the explicit factory inputs; never mutate the native cache."""
    _config_check(attempt)
    _native_home(attempt, config)
    try:
        effective = config.load_config_readonly()
        raw = attempt.settings.document
        require(type(effective) is dict, 'service_factory_native_config_shape')
        for section in ('model', 'gateway'):
            actual = effective.get(section)
            require(type(actual) is dict and all(type(actual.get(key)) is type(value)
                    and actual.get(key) == value for key, value in raw[section].items()),
                    'service_factory_native_config_changed')
        require(_same(effective.get('platform_toolsets', {}).get('api_server'), ['file']),
                'service_factory_native_tool_scope')
        platform = effective.get('platforms', {}).get('api_server')
        require(type(platform) is dict and platform.get('enabled') is True
                and _same(platform.get('extra'), attempt.settings.api),
                'service_factory_native_api_changed')
        plugins = effective.get('plugins')
        require(type(plugins) is dict and type(plugins.get('enabled')) is list
                and not plugins['enabled'], 'service_factory_native_plugin_scope')
        entry = plugins.get('entries', {}).get(PLUGIN_ID)
        require(type(entry) is dict and entry.get('allow_tool_override') is True
                and _same(entry.get('settings'), raw['plugins']['entries'][PLUGIN_ID]['settings']),
                'service_factory_native_plugin_settings')
        require(_same(attempt.context.get_config('execution'), attempt.settings.execution)
                and _same(attempt.context.get_config('policy'),
                    raw['plugins']['entries'][PLUGIN_ID]['settings']['policy']),
                'service_factory_native_context_settings')
    finally:
        _native_home(attempt, config)
        _config_check(attempt)


def _configure(attempt):
    Config, Platform, Manager, Manifest, Context, config = _native_components(attempt)
    home = attempt.record.service.home
    # Direct typed construction: no environment gateway loader or plugin discovery.
    attempt.gateway_config = Config(multiplex_profiles=False, write_sessions_json=False,
        loop_watchdog=False, systemd_watchdog_seconds=0, sessions_dir=Path(home) / 'sessions')
    attempt.api_config = Platform(enabled=True, extra=_copy(attempt.settings.api))
    attempt.manager = Manager(scope_key=home)
    attempt.manifest = Manifest(name=PLUGIN_ID, key=PLUGIN_ID, source='project',
                                path=str(ROOT / 'packages/claw-hermes'))
    attempt.context = Context(attempt.manifest, attempt.manager)
    require(type(attempt.gateway_config) is Config and type(attempt.api_config) is Platform
            and type(attempt.manager) is Manager and type(attempt.manifest) is Manifest
            and type(attempt.context) is Context and attempt.context._manager is attempt.manager
            and attempt.context.manifest is attempt.manifest and attempt.context.plugin_id == PLUGIN_ID
            and str(Path(attempt.manager.scope_key).resolve()) == home
            and attempt.manifest.source == 'project', 'service_factory_native_objects_changed')
    _native_settings(attempt, config)
    # The broker's actual host principal is checked here and again by its client.
    import host_principal
    host_principal.gateway_identity(attempt.settings.execution['provider_broker']['principal_contract'])
    attempt.execution = ExecutionBoundary(_copy(attempt.settings.execution))
    _config_check(attempt)
    import gateway_prepared_consumer as consumer
    consumer.verify_imports(attempt.source_proof)


def _unknown(attempt, exc):
    if attempt.stage != 'UNKNOWN':
        attempt.failed_stage = attempt.stage
    attempt.stage, attempt.reason = 'UNKNOWN', _reason(exc)
    # No config, exception traceback, payload or credential is sent to stdout.
    try:
        print(json.dumps({'state': 'SERVICE_FACTORY_UNKNOWN', 'reason': attempt.reason},
                         sort_keys=True, separators=(',', ':')), file=sys.stderr, flush=True)
    except BaseException:
        # Losing the diagnostic pipe cannot end custody of the original owner.
        pass


async def _hold_unknown(attempt):
    attempt.retained = attempt.loop.create_future()
    await attempt.retained
    raise ServiceFactoryRejected('service_factory_unknown_wait_returned')


def _validate_final(attempt, value):
    identity = (os.getpid(), attempt.record.state.epoch + 1, attempt.instance_id)
    value = control.validate_frame(value, service_id=attempt.service_id, identity=identity)
    driver = control._attempt
    require(value['type'] == 'final' and type(driver) is control.ServiceControl
            and driver.service is attempt.service and driver.final == value
            and attempt.service._control_owner is driver
            and attempt.service._owner is attempt.owner and attempt.owner._service_owner is attempt.service
            and attempt.service._held is attempt.held and attempt.owner._held is attempt.held
            and attempt.service.status() == value['owner'] and attempt.owner._stage == 'CLOSED'
            and attempt.owner.status()['callerLeaseMayBeReleased'] is True
            and attempt.held._finished and not attempt.held._owner.homes,
            'service_factory_final_not_original')
    return value


async def _run(attempt):
    try:
        # Reserve BEFORE entering the first operation with possible ownership effects.
        attempt.stage, attempt.effects_started = 'PROFILE_RESERVING', True
        attempt.held = startup.live.profiles.reserve_profile(
            Path(attempt.record.service.home), attempt.expected_mount)
        attempt.stage = 'OWNER_CONSTRUCTING'
        attempt.owner = startup.NativeStoreStartup(attempt.held, attempt.expected_mount,
            attempt.record.state, instance_id=attempt.instance_id,
            response_expected=attempt.record.response, prepared_layout=True,
            service_profile=attempt.record.service)
        attempt.stage = 'OWNER_STARTING'
        attempt.owner.start()
        # Native readonly config can create native backups. It must follow the
        # original strict startup layout check, not precede it. Restart/backup
        # qualification remains a separate installed-service acceptance gate.
        attempt.stage = 'NATIVE_CONFIGURING'
        _configure(attempt)
        attempt.stage = 'SERVICE_CONSTRUCTING'
        attempt.service = BorrowedServiceOwner(attempt.owner, host_policy=attempt.settings.policy,
                                              execution=attempt.execution, context=attempt.context)
        attempt.stage = 'CONTROL_DRIVING'
        result = await control.drive_service(attempt.service, attempt.service_id,
                                             attempt.gateway_config, attempt.api_config)
        attempt.final = _validate_final(attempt, result)
        attempt.stage = 'CLOSED'
        return attempt.final
    except BaseException as exc:
        _unknown(attempt, exc)
        # No close/detach/lease finish/cancel or replacement owner follows.
        return await _hold_unknown(attempt)


def _park_without_loop(attempt):
    """Last-resort process custody if the original loop was lost externally.

    A closed loop cannot resume its work. Keep its original references and the
    process alive for operator resolution, without inventing a replacement loop,
    task, thread or service. This Event is only a blocking wait on this thread.
    """
    attempt.parked = threading.Event()
    while True:
        try:
            attempt.parked.wait()
        except BaseException:
            continue


def _retain_loop(attempt):
    """Unexpected outer-loop interruption is not permission to tear down work."""
    while True:
        if attempt.loop.is_closed():
            return _park_without_loop(attempt)
        try:
            attempt.loop.run_forever()
        except BaseException:
            continue


def execute(record, expected_mount, instance_id, service_id):
    """One fixed dedicated-process attempt; returns only after the original final.

    No callback/channel/config argument is accepted from the caller. Schema and
    selected-byte failures before profile reservation are safe bounded refusals.
    Once ownership may exist, the same task/loop is retained on every failure.
    """
    global _attempt
    require(_attempt is None, 'service_factory_process_already_owned')
    handoff.validate(record, expected_home=handoff.TARGET)
    require(type(expected_mount) is startup.live.mounts.ExpectedMount,
            'service_factory_mount_required')
    expected_mount.__post_init__()
    require(expected_mount.mount_point == handoff.TARGET and expected_mount.root == '/profile'
            and expected_mount.filesystem == 'ext4'
            and os.makedev(*expected_mount.device) == record.service.home_identity[0],
            'service_factory_mount_binding')
    require(type(instance_id) is str and re.fullmatch('[A-Za-z0-9._-]{1,128}', instance_id)
            and instance_id != record.state.instance_id, 'service_factory_new_instance')
    control.request_id(service_id, 1)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise ServiceFactoryRejected('service_factory_dedicated_loop_required')
    _attempt = attempt = _Attempt(record, expected_mount, instance_id, service_id)
    # Python diagnostics use stderr; the R160 FDChannel writes canonical frames
    # directly to fd 1. There is no second print of the returned final frame.
    with contextlib.redirect_stdout(sys.stderr):
        attempt.stage = 'CONFIG_VALIDATING'
        try:
            attempt.settings = validate_settings(read_document(attempt))
        except Exception as exc:
            attempt.failed_stage, attempt.stage = attempt.stage, 'REFUSED'
            attempt.reason = _reason(exc)
            raise ServiceFactoryRejected(attempt.reason) from None
        attempt.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(attempt.loop)
        attempt.task = attempt.loop.create_task(_run(attempt))
        try:
            result = attempt.loop.run_until_complete(attempt.task)
            require(attempt.stage == 'CLOSED' and attempt.final == result
                    and not asyncio.all_tasks(attempt.loop), 'service_factory_loop_not_terminal')
        except BaseException as exc:
            _unknown(attempt, exc)
            return _retain_loop(attempt)
        attempt.loop.close()
        asyncio.set_event_loop(None)
        return result
