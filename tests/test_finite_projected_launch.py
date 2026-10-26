"""Projection-transfer contracts with explicit OS/exec boundary doubles.

Original typed handoff/policy codecs run; no namespace, native store, lease,
model, installed target or actual exec is exercised here.
"""
from dataclasses import asdict, replace
from contextlib import redirect_stdout
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
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_retained_launch as launch
import gateway_finite_protocol as protocol
import test_supervised_retained_launch as prior
from test_supervised_finite_launch import qualification_work


class ProjectedTransfer(unittest.TestCase, prior.Fixtures):
    def setUp(self):
        self.configure()
        self.work = qualification_work()
        self.namespaces = {'user': 'user:[1]', 'mnt': 'mnt:[2]',
                           'net': 'net:[3]', 'ipc': 'ipc:[4]'}
        self.expected = launch.mounts.ExpectedMount(123, (7, 0), '/profile',
            launch.handoff.TARGET, 'ext4')
        self.projected = {'version': 1, 'pid': os.getpid(), 'stateDirectoryCount': 1,
            'ambientHostDirectoriesBound': 0, 'hostUserNamespacePreserved': True,
            'legacyIpcV2Activated': False, 'fullD3BAccepted': False,
            'state': 'confined_state_profile', 'profile': launch.handoff.TARGET,
            'profileLayout': 'hermes-native-retained-three-stores-v1',
            'retainedProjectionVerified': True, 'persistentProfileProjected': True,
            'rootPrivilegesDropped': True, 'profileOwnershipAcquired': False,
            'nativeHermesStoresOpened': False,
            'retainedProfile': replace(self.value.retained, home=launch.handoff.TARGET),
            'profileDevice': 1792, 'profileInode': 12}
        self.stack.enter_context(patch.object(launch, 'ROOT', PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(launch, 'sys', SimpleNamespace(platform='linux',
            executable=launch.PYTHON, flags=SimpleNamespace(isolated=1), dont_write_bytecode=True)))
        self.enter = self.stack.enter_context(patch.object(launch.state, 'enter', return_value=self.projected))
        self.live = self.stack.enter_context(patch.object(launch, '_live'))
        self.mount = self.stack.enter_context(patch.object(launch, '_mount', return_value=self.expected))
        self.stack.enter_context(patch.object(launch, '_namespaces', return_value=self.namespaces))
        self.exec = self.stack.enter_context(patch.object(launch.os, 'execve',
            side_effect=prior.ExecTransferred(), create=True))

    def transfer(self, finite=True):
        with self.assertRaises(prior.ExecTransferred):
            if finite:
                launch.launch_finite(prior.IPC, prior.fixture.FS, self.b, self.value, self.work,
                    scratch='/srv/test/scratch', instance_id='next-owner')
            else:
                launch.launch(prior.IPC, prior.fixture.FS, self.b, self.value,
                    scratch='/srv/test/scratch', instance_id='next-owner')
        return copy.deepcopy(self.exec.call_args.args[2])

    def change_context(self, environment, change):
        result = copy.deepcopy(environment)
        context = json.loads(result[launch.CONTEXT_ENV])
        change(context)
        result[launch.CONTEXT_ENV] = launch._bytes(context).decode('ascii')
        return result

    def test_finite_exec_uses_fixed_target_and_bound_work_in_exact_environment(self):
        with patch.dict(os.environ, {'HOST_SECRET': 'fixture-only', 'PYTHONPATH': '/foreign'}):
            env = self.transfer()
        executable, argv, _ = self.exec.call_args.args
        self.assertEqual(executable, launch.PYTHON)
        self.assertEqual(argv, [launch.PYTHON, '-I', '-B', '/opt/owned/' + launch.FINITE_ENTRY])
        self.assertEqual(set(env), {'PATH', 'LANG', 'HOME', 'HERMES_HOME', 'TMPDIR', 'TMP', 'TEMP',
            launch.WIRE_ENV, launch.CONTEXT_ENV, launch.FINITE_WORK_ENV})
        context = json.loads(env[launch.CONTEXT_ENV])
        self.assertEqual(context['protocol'], launch.FINITE_PROTOCOL)
        self.assertEqual(context['workSha256'], protocol.work_digest(self.work))
        self.assertEqual(context['wireSha256'], hashlib.sha256(env[launch.WIRE_ENV].encode('ascii')).hexdigest())
        self.assertEqual(context['mount'], json.loads(json.dumps(asdict(self.expected))))
        self.assertEqual(json.loads(env[launch.FINITE_WORK_ENV]), self.work)
        _, kwargs = self.enter.call_args
        self.assertEqual(kwargs, {'observe_self_mount': True, 'observe_self_identity': True,
            'profile_layout': launch.state.NATIVE_RETAINED_LAYOUT, 'retained_profile': self.value.retained})

    def test_finite_receive_rechecks_transfer_live_identity_and_mount_before_native_work(self):
        env = self.transfer()
        self.live.reset_mock()
        self.mount.reset_mock()
        record, expected, instance, work = launch.receive_finite(env)
        self.assertEqual(record.retained, self.projected['retainedProfile'])
        self.assertEqual(expected, self.expected)
        self.assertEqual(instance, 'next-owner')
        self.assertEqual(work, self.work)
        self.live.assert_called_once_with(prior.fixture.P, self.namespaces, os.getpid())
        self.mount.assert_called_once_with()
        work['requestIds']['normal'] = 'changed'
        self.assertEqual(json.loads(env[launch.FINITE_WORK_ENV]), self.work)

    def test_readiness_transfer_and_three_value_receive_remain_exact(self):
        env = self.transfer(finite=False)
        self.assertEqual(self.exec.call_args.args[1],
            [launch.PYTHON, '-I', '-B', '/opt/owned/' + launch.ENTRY])
        self.assertNotIn(launch.FINITE_WORK_ENV, env)
        context = json.loads(env[launch.CONTEXT_ENV])
        self.assertEqual(set(context), {'protocol', 'pid', 'principal', 'namespaces',
            'mount', 'scratch', 'instanceId', 'wireSha256'})
        self.assertEqual(context['protocol'], launch.PROTOCOL)
        received = launch.receive(env)
        self.assertEqual(len(received), 3)
        self.assertEqual(received[1:], (self.expected, 'next-owner'))

    def test_modes_cannot_consume_each_others_transfer_or_context_protocol(self):
        finite_env = self.transfer()
        ready_env = self.transfer(finite=False)
        for receive, env in ((launch.receive, finite_env), (launch.receive_finite, ready_env)):
            with self.assertRaises(launch.ProjectedLaunchRejected):
                receive(env)
        wrong = self.change_context(finite_env, lambda c: c.update(protocol=launch.PROTOCOL))
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'context_canonical'):
            launch.receive_finite(wrong)
        wrong = self.change_context(ready_env, lambda c: c.update(protocol=launch.FINITE_PROTOCOL))
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'context_canonical'):
            launch.receive(wrong)

    def test_changed_work_hash_pid_wire_or_unknown_context_fields_refuse_before_live(self):
        env = self.transfer()
        changes = [lambda c: c.update(workSha256='0' * 64),
                   lambda c: c.update(pid=os.getpid() + 1),
                   lambda c: c.update(wireSha256='0' * 64),
                   lambda c: c.update(command='/bin/sh')]
        self.live.reset_mock()
        for change in changes:
            with self.assertRaises(launch.ProjectedLaunchRejected):
                launch.receive_finite(self.change_context(env, change))
        changed_work = copy.deepcopy(self.work)
        changed_work['requestIds']['new'] = 'another-request'
        changed_env = {**env, launch.FINITE_WORK_ENV: protocol.canonical(changed_work).decode('ascii')}
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'work_binding'):
            launch.receive_finite(changed_env)
        self.live.assert_not_called()

    def test_noncanonical_duplicate_or_unbounded_work_is_refused_before_live(self):
        env = self.transfer()
        self.live.reset_mock()
        raw = env[launch.FINITE_WORK_ENV]
        for value in (' ' + raw, raw[:-1] + ',"sessionId":"again"}',
                      'x' * (protocol.MAX_WORK + 1)):
            with self.assertRaises((launch.ProjectedLaunchRejected, protocol.FiniteProtocolRejected)):
                launch.receive_finite({**env, launch.FINITE_WORK_ENV: value})
        self.live.assert_not_called()

    def test_invalid_work_or_missing_readonly_export_never_enters_projection(self):
        bad_work = {**self.work, 'model': 'caller-model'}
        with self.assertRaises(protocol.FiniteProtocolRejected):
            launch.launch_finite(prior.IPC, prior.fixture.FS, self.b, self.value, bad_work,
                scratch='/srv/test/scratch', instance_id='next-owner')
        fs = {**prior.fixture.FS, 'readonly': ['/usr/bin']}
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'entry_not_readonly'):
            launch.launch_finite(prior.IPC, fs, self.b, self.value, self.work,
                scratch='/srv/test/scratch', instance_id='next-owner')
        self.enter.assert_not_called()
        self.exec.assert_not_called()

    def test_changed_live_mount_or_identity_refuses_after_exec(self):
        env = self.transfer()
        self.mount.return_value = replace(self.expected, mount_id=124)
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'mount_changed_after_exec'):
            launch.receive_finite(env)
        self.mount.return_value = self.expected
        self.live.side_effect = launch.ProjectedLaunchRejected('projected_live_identity')
        with self.assertRaisesRegex(launch.ProjectedLaunchRejected, 'live_identity'):
            launch.receive_finite(env)

    def test_finite_target_validates_projection_before_runtime_import_or_execute(self):
        env = self.transfer()
        executor = Mock(return_value={'synthetic': 'runtime'})
        module = SimpleNamespace(execute=executor)
        with patch.dict(sys.modules, {'gateway_finite_runtime': module}), \
                patch.dict(os.environ, env, clear=True):
            result = launch.finite_target_main()
        self.assertEqual(result, {'synthetic': 'runtime'})
        record, expected, instance, work = executor.call_args.args
        self.assertEqual((expected, instance, work), (self.expected, 'next-owner', self.work))
        self.assertEqual(record.retained, self.projected['retainedProfile'])
        executor.reset_mock()
        with patch.dict(sys.modules, {'gateway_finite_runtime': module}), \
                patch.object(launch, 'receive_finite', side_effect=launch.ProjectedLaunchRejected('invalid')):
            with self.assertRaises(launch.ProjectedLaunchRejected):
                launch.finite_target_main()
        executor.assert_not_called()


class FixedProjectedEntry(unittest.TestCase):
    def test_extra_arguments_never_execute_and_error_text_is_bounded(self):
        script = Path(launch.__file__).resolve().parents[2] / launch.FINITE_ENTRY
        spec = importlib.util.spec_from_file_location('finite_projected_entry_fixture', script)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        output = io.StringIO()
        with patch.object(entry, 'sys', SimpleNamespace(argv=['fixed-entry', 'caller-command'], modules={})), \
                patch.object(entry, 'finite_target_main') as target, redirect_stdout(output):
            status = entry.main()
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue()),
            {'state': 'PROJECTED_FINITE_REFUSED', 'type': 'ValueError',
             'phase': 'TRANSFER', 'reason': 'finite_target_rejected'})
        target.assert_not_called()


if __name__ == '__main__':
    unittest.main()
