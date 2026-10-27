"""Service launch/receive contracts with explicit kernel, exec and factory ports.

Canonical codecs, policy checks and fixed entry code are real. Confinement is
not performed. A separate group uses real temporary profile/config files with
the existing root-owner fixture mapping; it still doubles the fixed target,
live kernel checks and mount observation. No native runtime/listener/model runs.
"""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages/claw-hermes'), str(ROOT / 'tests')]
import gateway_service_launch as launch
import test_gateway_state_projection as old
import test_service_handoff_r161a1 as fixture
import test_service_child_control_r160a1 as control_fixture

SID = 'a' * 32


class ExecTransferred(BaseException):
    pass


class Fixtures:
    def configure(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        fixture.ServiceHandoffContract.setUp(self)
        self.stack.enter_context(patch.object(launch, 'ROOT', PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(launch.os, 'makedev',
            side_effect=lambda major, minor: 1792 + minor, create=True))
        self.b = old.binding()
        self.principal = dict(old.P)
        self.namespaces = {'user': 'user:[1]', 'mnt': 'mnt:[2]',
                           'net': 'net:[3]', 'ipc': 'ipc:[4]'}
        self.mount = launch.mounts.ExpectedMount(40, (7, 0), '/profile',
            launch.handoff.TARGET, 'ext4')
        self.projected = fixture.ServiceHandoffContract.projected(self)
        self.context = {'protocol': launch.PROTOCOL, 'pid': os.getpid(),
            'principal': self.principal, 'namespaces': self.namespaces,
            'mount': asdict(self.mount), 'scratch': '/srv/test/scratch',
            'instanceId': 'next-owner', 'serviceId': SID,
            'wireSha256': hashlib.sha256(self.raw).hexdigest()}
        self.env = launch._environment(self.raw, self.context)

    def changed(self, change):
        context = copy.deepcopy(self.context)
        change(context)
        return {**self.env, launch.CONTEXT_ENV: launch._bytes(context).decode('ascii')}

    def changed_wire(self, record):
        raw = launch.handoff.encode(record, expected_home=record.service.home)
        context = dict(self.context, wireSha256=hashlib.sha256(raw).hexdigest())
        return launch._environment(raw, context)

    def interpreter(self):
        return self.stack.enter_context(patch.object(launch, 'sys', SimpleNamespace(
            platform='linux', executable=launch.PYTHON,
            flags=SimpleNamespace(isolated=1), dont_write_bytecode=True)))


class LaunchContracts(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()
        self.events = []
        self.validate = self.stack.enter_context(patch.object(launch.state.gp, 'validate',
            return_value=(copy.deepcopy(old.V), copy.deepcopy(old.FS))))
        self.enter = self.stack.enter_context(patch.object(launch.state, 'enter',
            side_effect=lambda *a, **k: (self.events.append('projection') or self.projected)))
        self.stack.enter_context(patch.object(launch, '_namespaces', return_value=self.namespaces))
        self.live = self.stack.enter_context(patch.object(launch, '_live',
            side_effect=lambda *a: self.events.append('live')))
        self.mountfn = self.stack.enter_context(patch.object(launch, '_mount',
            side_effect=lambda: (self.events.append('mount') or self.mount)))
        self.exec = self.stack.enter_context(patch.object(launch.os, 'execve',
            side_effect=ExecTransferred(), create=True))

    def invoke(self, **options):
        return launch.launch(old.V, old.FS, self.b, self.value,
            scratch=options.pop('scratch', '/srv/test/scratch'),
            instance_id=options.pop('instance_id', 'next-owner'),
            service_id=options.pop('service_id', SID), **options)

    def test_exact_service_selection_and_scrubbed_fixed_exec(self):
        with patch.dict(os.environ, {'HOST_SECRET': 'fixture-secret', 'PYTHONPATH': '/foreign'}), \
                self.assertRaises(ExecTransferred):
            self.invoke()
        executable, argv, environment = self.exec.call_args.args
        self.assertEqual(executable, launch.PYTHON)
        self.assertEqual(argv, [launch.PYTHON, '-I', '-B', '/opt/owned/' + launch.ENTRY])
        self.assertEqual(set(environment), set(self.env))
        self.assertNotIn('HOST_SECRET', environment)
        self.assertNotIn(launch.common.WIRE_ENV, environment)
        self.assertEqual(launch.handoff.decode_projected(environment[launch.WIRE_ENV].encode()), self.value)
        self.assertEqual(json.loads(environment[launch.CONTEXT_ENV]),
                         json.loads(json.dumps(self.context)))
        self.assertEqual(self.enter.call_args.kwargs, dict(observe_self_mount=True,
            observe_self_identity=True, profile_layout=launch.state.NATIVE_SERVICE_LAYOUT,
            service_profile=self.receipt))
        self.assertEqual(self.events, ['projection', 'live', 'mount'])

    def test_data_or_retained_record_never_enters_projection(self):
        for record in (asdict(self.value), object(), None):
            self.value = record
            with self.assertRaises(launch.ServiceLaunchRejected): self.invoke()
        self.enter.assert_not_called()
        self.exec.assert_not_called()

    def test_invalid_instance_and_service_identity_refuse_before_projection(self):
        for instance in ('previous-native-owner', '', True, 'a/b', 'x' * 129):
            with self.subTest(instance=instance), self.assertRaises(launch.ServiceLaunchRejected):
                self.invoke(instance_id=instance)
        for service_id in ('', True, None, 'a' * 31, 'a' * 33, 'A' * 32, 'g' * 32):
            with self.subTest(service_id=service_id), self.assertRaises(launch.ServiceLaunchRejected):
                self.invoke(service_id=service_id)
        self.enter.assert_not_called()

    def test_wrong_original_volume_or_config_identity_never_projects(self):
        self.b = replace(self.b, profile_inode=99)
        with self.assertRaises(launch.state.StateProjectionRejected): self.invoke()
        self.b = old.binding()
        self.value = replace(self.value, service=replace(self.receipt, config_identity=(1792, 21)))
        with self.assertRaises((launch.handoff.HandoffRejected, launch.handoff.profile.ServiceProfileRejected)):
            self.invoke()
        self.enter.assert_not_called()

    def test_scratch_must_be_exact_export(self):
        for scratch in ('/dev/null', '/foreign', '/srv//test/scratch', launch.handoff.TARGET):
            with self.subTest(scratch=scratch), self.assertRaises((
                    launch.ServiceLaunchRejected, launch.handoff.HandoffRejected)):
                self.invoke(scratch=scratch)
        self.enter.assert_not_called()

    def test_entry_python_and_install_root_must_be_readonly_exports(self):
        for readonly in (['/usr/bin'], ['/opt/owned'], ['/opt/owned/scripts', '/usr/bin']):
            self.validate.return_value = (old.V, {**old.FS, 'readonly': readonly})
            with self.assertRaisesRegex(launch.ServiceLaunchRejected, 'entry_not_readonly'):
                self.invoke()
        self.enter.assert_not_called()

    def test_projection_failure_never_encodes_or_executes(self):
        self.enter.side_effect = RuntimeError('projection effect unknown')
        with patch.object(launch.handoff, 'encode_projected') as encode, self.assertRaises(RuntimeError):
            self.invoke()
        encode.assert_not_called()
        self.live.assert_not_called()
        self.exec.assert_not_called()

    def test_incomplete_or_wrong_service_projection_never_executes(self):
        for change in ({'rootPrivilegesDropped': False}, {'serviceProjectionVerified': False},
                       {'profileInode': 99}, {'retainedProfile': self.receipt}):
            self.projected = fixture.ServiceHandoffContract.projected(self) | change
            with self.assertRaises(launch.handoff.HandoffRejected): self.invoke()
        self.exec.assert_not_called()

    def test_live_identity_or_mount_change_blocks_exec(self):
        self.live.side_effect = launch.ServiceLaunchRejected('projected_live_identity')
        with self.assertRaises(launch.ServiceLaunchRejected): self.invoke()
        self.mountfn.assert_not_called()
        self.live.side_effect = None
        for expected in (replace(self.mount, root='/wrong'),
                         replace(self.mount, mount_point='/wrong'),
                         replace(self.mount, device=(7, 1))):
            self.mountfn.side_effect = None
            self.mountfn.return_value = expected
            with self.assertRaises(launch.ServiceLaunchRejected): self.invoke()
        self.exec.assert_not_called()

    def test_returned_or_failed_exec_never_retries(self):
        self.exec.side_effect = None
        with self.assertRaisesRegex(launch.ServiceLaunchRejected, 'exec_returned'): self.invoke()
        self.assertEqual(self.exec.call_count, 1)
        self.exec.reset_mock()
        self.exec.side_effect = OSError('fixture exec failure')
        with self.assertRaises(OSError): self.invoke()
        self.assertEqual(self.exec.call_count, 1)


class ReceiveContracts(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()
        self.interpreter()
        self.events = []
        self.live = self.stack.enter_context(patch.object(launch, '_live',
            side_effect=lambda *a: self.events.append('live')))
        self.mountfn = self.stack.enter_context(patch.object(launch, '_mount',
            side_effect=lambda: (self.events.append('mount') or self.mount)))
        self.inspect = self.stack.enter_context(patch.object(launch.handoff.profile, 'inspect_profile',
            side_effect=lambda *a, **k: self.events.append('profile')))

    def refuse(self, environment):
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(environment)

    def test_typed_result_and_readonly_profile_follow_actual_live_and_mount_checks(self):
        record, expected, instance, service_id = launch.receive(self.env)
        self.assertEqual((record, expected, instance, service_id),
                         (self.value, self.mount, 'next-owner', SID))
        self.assertIs(type(record), launch.handoff.ServiceStartup)
        self.assertEqual(self.events, ['live', 'mount', 'profile'])
        self.inspect.assert_called_once_with(Path(launch.handoff.TARGET),
            uid=23001, gid=23003, device=1792, expectation=record.service)
        self.assertIsNot(record, self.value)

    def test_wrong_interpreter_or_flags_refuse_before_payload_or_profile(self):
        for key, value in (('platform', 'win32'), ('executable', '/foreign/python'),
                           ('dont_write_bytecode', False)):
            with patch.object(launch.sys, key, value): self.refuse(self.env)
        with patch.object(launch.sys, 'flags', SimpleNamespace(isolated=0)): self.refuse(self.env)
        self.live.assert_not_called()
        self.inspect.assert_not_called()

    def test_extra_missing_and_other_mode_environment_refuse_before_live(self):
        for env in (None, {**self.env, 'PYTHONPATH': '/foreign'},
                    {k: v for k, v in self.env.items() if k != 'LANG'},
                    {**self.env, launch.common.FINITE_WORK_ENV: '{}'},
                    {**self.env, launch.common.WIRE_ENV: self.env[launch.WIRE_ENV]}):
            self.refuse(env)
        self.live.assert_not_called()
        self.inspect.assert_not_called()

    def test_bound_text_types_and_lengths_refuse_before_parsing(self):
        for key, maximum in ((launch.WIRE_ENV, launch.handoff.MAX_BYTES),
                             (launch.CONTEXT_ENV, launch.MAX_CONTEXT)):
            for value in ('', True, None, 'x' * (maximum + 1)):
                with self.subTest(key=key, value=str(value)[:10]):
                    self.refuse({**self.env, key: value})
        self.live.assert_not_called()

    def test_noncanonical_duplicate_unknown_or_wrong_context_protocol_refused(self):
        raw = self.env[launch.CONTEXT_ENV]
        for value in (' ' + raw, raw + '\n', raw[:-1] + ',"pid":1}', '[]'):
            self.refuse({**self.env, launch.CONTEXT_ENV: value})
        for change in (lambda c: c.update(extra='caller-command'),
                       lambda c: c.pop('serviceId'),
                       lambda c: c.update(protocol=launch.common.PROTOCOL),
                       lambda c: c.update(protocol=launch.common.FINITE_PROTOCOL)):
            self.refuse(self.changed(change))
        self.live.assert_not_called()

    def test_current_pid_wire_hash_instance_and_service_id_are_bound(self):
        for change in (lambda c: c.update(pid=os.getpid() + 1),
                       lambda c: c.update(pid=True),
                       lambda c: c.update(wireSha256='0' * 64),
                       lambda c: c.update(instanceId='previous-native-owner'),
                       lambda c: c.update(serviceId='A' * 32),
                       lambda c: c.update(serviceId=True)):
            self.refuse(self.changed(change))
        self.live.assert_not_called()

    def test_wire_requires_service_protocol_config_shape_and_fixed_home(self):
        for raw in ('{}', '[]', '\xff', ' ' + self.env[launch.WIRE_ENV],
                    self.env[launch.WIRE_ENV].replace(launch.handoff.PROTOCOL,
                                                   launch.common.handoff.PROTOCOL)):
            self.refuse({**self.env, launch.WIRE_ENV: raw})
        changed = replace(self.value, service=replace(self.receipt, home='/other/profile'))
        self.refuse(self.changed_wire(changed))
        self.live.assert_not_called()

    def test_changed_config_or_source_data_cannot_reuse_old_wire_digest(self):
        for receipt in (replace(self.receipt, config_sha256='e' * 64),
                        replace(self.receipt, config_size=41),
                        replace(self.receipt, selection=replace(
                            self.receipt.selection, selection_sha256='e' * 64))):
            raw = launch.handoff.encode(replace(self.value, service=receipt),
                                        expected_home=launch.handoff.TARGET)
            self.refuse({**self.env, launch.WIRE_ENV: raw.decode('ascii')})
        self.live.assert_not_called()

    def test_principal_and_namespace_schema_refuse_before_live(self):
        for change in (lambda c: c['principal'].update(gatewayUid=True),
                       lambda c: c['principal'].update(brokerUid=23001),
                       lambda c: c['namespaces'].pop('ipc'),
                       lambda c: c['namespaces'].update(net='mnt:[3]')):
            self.refuse(self.changed(change))
        self.live.assert_not_called()

    def test_environment_path_home_temp_and_locale_cannot_drift(self):
        for key, value in (('PATH', '/foreign'), ('HOME', '/host'),
                           ('HERMES_HOME', '/host'), ('TMPDIR', '/other'),
                           ('TEMP', '/other'), ('LANG', 'C')):
            self.refuse({**self.env, key: value})
        self.live.assert_not_called()

    def test_scratch_alias_and_profile_overlap_refused(self):
        for value in ('/', '/dev/null', launch.handoff.TARGET,
                      launch.handoff.TARGET + '/tmp', '/run/alaz-state', '/x//y'):
            self.refuse(self.changed(lambda c: c.update(scratch=value)))
        self.live.assert_not_called()

    def test_mount_schema_identity_or_live_change_blocks_profile(self):
        for change in (lambda c: c['mount'].update(device=True),
                       lambda c: c['mount'].update(mount_id=True),
                       lambda c: c['mount'].update(extra=1),
                       lambda c: c['mount'].update(root='/other')):
            self.refuse(self.changed(change))
        self.live.assert_not_called()
        self.mountfn.side_effect = None
        self.mountfn.return_value = replace(self.mount, mount_id=41)
        self.refuse(self.env)
        self.inspect.assert_not_called()

    def test_live_refusal_never_reads_profile(self):
        self.live.side_effect = launch.ServiceLaunchRejected('projected_live_identity')
        self.refuse(self.env)
        self.mountfn.assert_not_called()
        self.inspect.assert_not_called()

    def test_profile_source_or_config_drift_blocks_fixed_factory(self):
        executor = Mock(side_effect=AssertionError('factory must not run'))
        for reason in ('service_profile_source_changed', 'service_config_content_changed',
                       'service_profile_database_identity'):
            self.inspect.side_effect = launch.handoff.profile.ServiceProfileRejected(reason)
            with patch.dict(os.environ, self.env, clear=True), \
                    patch.dict(sys.modules, {'gateway_service_factory': SimpleNamespace(execute=executor)}), \
                    self.assertRaises(launch.ServiceLaunchRejected):
                launch.target_main()
        executor.assert_not_called()

    def test_fixed_factory_called_only_after_real_receiver_checks(self):
        expected_result = control_fixture.frame('final', 'CLOSED', 1)
        executor = Mock(side_effect=lambda *args: (self.events.append('factory') or expected_result))
        with patch.dict(os.environ, self.env, clear=True), \
                patch.dict(sys.modules, {'gateway_service_factory': SimpleNamespace(execute=executor)}):
            self.assertEqual(launch.target_main(), expected_result)
        self.assertEqual(self.events, ['live', 'mount', 'profile', 'factory'])
        self.assertEqual(executor.call_args.args, (self.value, self.mount, 'next-owner', SID))


class OriginalLiveChecks(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()
        self.interpreter()
        self.actor = {'pid': os.getpid(), 'uids': (23001,) * 4, 'gids': (23003,) * 4,
            'groups': (), 'threads': 1, 'nnp': 1,
            'caps': {k: 0 for k in launch.state.gp.launch.CAPS},
            'userns': 'user:[1]', 'uidMap': ['0', '0', '4294967295'],
            'gidMap': ['0', '0', '4294967295']}
        self.stack.enter_context(patch.object(launch.state.gp.hp, 'gateway_identity'))
        self.stack.enter_context(patch.object(launch.state.gp.launch, 'observation', return_value=self.actor))
        self.filter = self.stack.enter_context(patch.object(launch.state.gp.net, 'status', return_value={'Seccomp': '2'}))
        self.ns = self.stack.enter_context(patch.object(launch.common, '_namespaces', return_value=self.namespaces))
        self.mountfn = self.stack.enter_context(patch.object(launch, '_mount', return_value=self.mount))
        self.inspect = self.stack.enter_context(patch.object(launch.handoff.profile, 'inspect_profile'))

    def test_service_receiver_reuses_original_live_identity_checks(self):
        self.assertIs(launch._live, launch.common._live)
        self.assertEqual(launch.receive(self.env), (self.value, self.mount, 'next-owner', SID))
        self.inspect.reset_mock()
        for key, value in (('uids', (0,) * 4), ('gids', (0,) * 4), ('groups', (23003,)),
                           ('threads', 2), ('nnp', 0), ('pid', os.getpid() + 1),
                           ('userns', 'user:[99]'), ('uidMap', ['0', '23001', '1']),
                           ('gidMap', ['0', '23003', '1'])):
            with patch.dict(self.actor, {key: value}), self.assertRaises(launch.ServiceLaunchRejected):
                launch.receive(self.env)
        for name in self.actor['caps']:
            with patch.dict(self.actor['caps'], {name: 1}), self.assertRaises(launch.ServiceLaunchRejected):
                launch.receive(self.env)
        self.inspect.assert_not_called()

    def test_private_namespace_and_filter_loss_refuse_before_profile(self):
        self.ns.return_value = {**self.namespaces, 'mnt': 'mnt:[99]'}
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(self.env)
        self.ns.return_value = self.namespaces
        self.filter.return_value = {'Seccomp': '0'}
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(self.env)
        self.inspect.assert_not_called()


@unittest.skipUnless(sys.platform == 'linux', 'temporary POSIX target with real profile files')
class RealProfileReceiver(unittest.TestCase):
    """Real profile data, explicit target/mount/kernel fixture replacements."""
    def setUp(self):
        import service_profile_fixtures_r161a1 as files
        files.set_up_profile(self)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(launch.handoff, 'TARGET', str(self.home)))
        self.stack.enter_context(patch.object(launch.common.handoff, 'TARGET', str(self.home)))
        self.stack.enter_context(patch.object(launch.os, 'makedev', return_value=self.device, create=True))
        Fixtures.interpreter(self)
        self.stack.enter_context(patch.object(launch, '_live'))
        self.mount = launch.mounts.ExpectedMount(40, (7, 0), '/profile', str(self.home), 'ext4')
        self.stack.enter_context(patch.object(launch, '_mount', return_value=self.mount))
        state = launch.handoff.preopen.live.PreparedStoreExpectation(
            launch.handoff.preopen.live.NATIVE_PIN, 'a' * 64, 'b' * 64,
            '12345678-1234-4234-8234-123456789012', 123,
            self.expectation.database_identities[0], self.expectation.database_identities[1],
            1, self.expectation.instance_id)
        reply = launch.handoff.response.PreparedResponseExpectation(
            launch.handoff.response.NATIVE_FEATURE, launch.handoff.response.SCHEMA_SHA256,
            self.expectation.database_identities[2])
        self.value = launch.handoff.ServiceStartup(state, reply, self.expectation)

    def environment(self, record=None):
        record = self.value if record is None else record
        raw = launch.handoff.encode(record, expected_home=str(self.home))
        context = {'protocol': launch.PROTOCOL, 'pid': os.getpid(),
            'principal': {'version': 1, 'enabled': True, 'gatewayUid': self.uid,
                'brokerUid': self.uid + 1, 'socketGroupGid': self.gid, 'hostUserNamespace': 'user:[1]'},
            'namespaces': {'user': 'user:[1]', 'mnt': 'mnt:[2]', 'net': 'net:[3]', 'ipc': 'ipc:[4]'},
            'mount': asdict(self.mount), 'scratch': '/srv/test/scratch',
            'instanceId': 'next-owner', 'serviceId': SID, 'wireSha256': hashlib.sha256(raw).hexdigest()}
        return launch._environment(raw, context)

    def test_real_profile_bytes_and_source_selection_pass_without_sql_or_factory(self):
        with patch('sqlite3.connect', side_effect=AssertionError('receiver must not open SQL')):
            self.assertEqual(launch.receive(self.environment()),
                             (self.value, self.mount, 'next-owner', SID))

    def test_changed_real_config_content_refused_before_factory(self):
        (self.home / 'config.yaml').write_bytes(b'{}')
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(self.environment())

    def test_replaced_real_config_inode_refused_even_with_same_bytes(self):
        replacement = self.home / 'replacement.tmp'
        replacement.write_bytes(self.config_bytes)
        replacement.chmod(0o600)
        replacement.replace(self.home / 'config.yaml')
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(self.environment())

    def test_self_consistent_wire_cannot_select_other_installed_source(self):
        receipt = replace(self.expectation, selection=replace(
            self.selection, selection_sha256='e' * 64))
        record = replace(self.value, service=receipt)
        with self.assertRaises(launch.ServiceLaunchRejected): launch.receive(self.environment(record))


class FixedEntry(unittest.TestCase):
    def setUp(self):
        script = ROOT / launch.ENTRY
        spec = importlib.util.spec_from_file_location('service_projected_entry_fixture', script)
        self.entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.entry)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def run_entry(self, target, argv=None):
        with patch.object(self.entry, 'target_main', target), \
                patch.object(self.entry.sys, 'argv', ['fixed-entry'] if argv is None else argv), \
                redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            return self.entry.main()

    def test_final_already_written_by_driver_is_not_emitted_twice(self):
        final = control_fixture.frame('final', 'CLOSED', 1)
        def completed():
            print(json.dumps(final, sort_keys=True, separators=(',', ':')))
            return final
        self.assertEqual(self.run_entry(completed), 0)
        self.assertEqual(len(self.stdout.getvalue().splitlines()), 1)
        self.assertEqual(json.loads(self.stdout.getvalue()), final)
        self.assertEqual(self.stderr.getvalue(), '')

    def test_extra_arguments_never_enter_factory_and_diagnostics_use_stderr(self):
        target = Mock()
        self.assertEqual(self.run_entry(target, ['fixed-entry', '/caller/command']), 2)
        target.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), '')
        self.assertEqual(json.loads(self.stderr.getvalue())['reason'], 'service_projected_extra_arguments')

    def test_exception_payload_is_bounded_and_never_echoed_to_control_stdout(self):
        target = Mock(side_effect=RuntimeError('SECRET payload ' + 'x' * 10000))
        self.assertEqual(self.run_entry(target), 2)
        self.assertEqual(self.stdout.getvalue(), '')
        self.assertNotIn('SECRET', self.stderr.getvalue())
        self.assertLess(len(self.stderr.getvalue()), 256)
        target.assert_called_once_with()

    def test_nonfinal_or_foreign_pid_return_cannot_exit_successfully(self):
        for value in (None, {'type': 'final'}, control_fixture.frame(),
                      control_fixture.frame('reply', 'READY', 1),
                      {**control_fixture.frame('final', 'CLOSED', 1),
                       'owner': {**control_fixture.owner_receipt('CLOSED'), 'pid': os.getpid() + 1}}):
            with self.subTest(value=value):
                self.assertEqual(self.run_entry(Mock(return_value=value)), 2)
        self.assertEqual(self.stdout.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
