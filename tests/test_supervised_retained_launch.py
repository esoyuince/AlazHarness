"""Product dispatch contracts with explicit process/kernel boundary doubles.

No privileged operation, namespace, native store, model or installed candidate is
executed by these tests. Original typed codecs/policy validators are exercised.
"""
from contextlib import ExitStack
from dataclasses import asdict, replace
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_supervised_launch as g
import test_retained_handoff_t143a7 as prior
import test_gateway_state_projection as fixture

IPC = {**fixture.V, 'version': 2, 'mode': 'projected_root_principal'}


class ExecTransferred(BaseException):
    pass


class Fixtures:
    def configure(self):
        prior.HandoffContract.setUp(self)
        self.stack.enter_context(patch.object(g.os, 'makedev',
            side_effect=lambda major, minor: 1792 + minor, create=True))
        self.b = fixture.binding()
        self.value = replace(self.value, retained=replace(self.receipt,
                            home=self.b.mountpoint + '/profile'))
        self.data = {'protocol': g.PROTOCOL, 'binding': asdict(self.b),
            'ipc': copy.deepcopy(IPC), 'filesystem': copy.deepcopy(fixture.FS),
            'record': g.handoff.encode(self.value,
                expected_home=self.b.mountpoint + '/profile').decode('ascii'),
            'namespaceFd': 9, 'scratch': '/srv/test/scratch', 'instanceId': 'next-owner'}
        # Dataclass tuples acquire their wire list shape through actual JSON.
        self.data = json.loads(g._json_bytes(self.data))
        self.raw = g._json_bytes(self.data)


class DataContracts(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()

    def refuse(self, change):
        value = copy.deepcopy(self.data)
        change(value)
        with self.assertRaises(g.SupervisedLaunchRejected):
            g.decode(g._json_bytes(value))

    def test_exact_typed_roundtrip_without_launch_authority(self):
        with patch.object(g.subprocess, 'Popen') as spawn, patch.object(g.volume, 'actor') as actor:
            _, binding, record, view, fs = g.decode(self.raw)
        self.assertEqual(binding, self.b)
        self.assertEqual(record, self.value)
        self.assertEqual(view['principalContract'], fixture.P)
        self.assertEqual(fs['writable'], fixture.FS['writable'])
        spawn.assert_not_called()
        actor.assert_not_called()

    def test_unknown_or_missing_fields_refuse(self):
        self.refuse(lambda d: d.update(command=['/bin/sh']))
        self.refuse(lambda d: d.pop('namespaceFd'))
        self.refuse(lambda d: d['binding'].update(extra=True))
        self.refuse(lambda d: d['binding']['image'].update(extra=True))

    def test_duplicate_keys_and_noncanonical_bytes_refuse(self):
        for raw in (b' ' + self.raw, self.raw + b'\n',
                    self.raw[:-1] + b',"protocol":"' + g.PROTOCOL.encode() + b'"}',
                    json.dumps(self.data, indent=2).encode()):
            with self.subTest(raw=raw[:35]), self.assertRaises(g.SupervisedLaunchRejected):
                g.decode(raw)

    def test_input_size_encoding_depth_and_type_bounds(self):
        for raw in (None, '', bytearray(self.raw), b'', b'\xff', b'{' ,
                    b'[' * 1400 + b']' * 1400, b'x' * (g.MAX_INPUT + 1)):
            with self.assertRaises(g.SupervisedLaunchRejected):
                g.decode(raw)

    def test_descriptor_bool_stdio_negative_and_huge_refuse(self):
        for value in (True, 0, 1, 2, -1, 2**20, 9.0, '9'):
            self.refuse(lambda d, v=value: d.update(namespaceFd=v))

    def test_volume_image_and_profile_cannot_be_rebound(self):
        self.refuse(lambda d: d['binding'].update(profile_inode=13))
        self.refuse(lambda d: d['binding'].update(loop_number=1))
        self.refuse(lambda d: d['binding'].update(mountpoint='/srv/other'))
        self.refuse(lambda d: d['binding']['image'].update(uid=23001))

    def test_scope_identity_and_process_ids_are_typed(self):
        for value in ([True, 50], [23], [0, 50], '23,50'):
            self.refuse(lambda d, v=value: d['binding'].update(scope_identity=v))
        self.refuse(lambda d: d['binding'].update(worker_pid=True))

    def test_retained_source_epoch_and_new_instance_are_bound(self):
        self.refuse(lambda d: d.update(instanceId='prior-owner'))
        self.refuse(lambda d: d.update(instanceId='other/program'))
        self.refuse(lambda d: d.update(record=d['record'].replace('prior-owner', 'foreign-owner', 1)))

    def test_scratch_and_policy_must_pass_original_validators(self):
        for value in ('/dev/null', '/tmp/not-exported', '/srv//test/scratch'):
            self.refuse(lambda d, v=value: d.update(scratch=v))
        self.refuse(lambda d: d['filesystem'].update(enabled=False))


class ChildSequence(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()
        self.events = []
        self.stack.enter_context(patch.object(g.volume, 'actor', side_effect=lambda: self.events.append('actor')))
        self.stack.enter_context(patch.object(g, 'sys', SimpleNamespace(executable=g.PYTHON,
            flags=SimpleNamespace(isolated=1), dont_write_bytecode=True)))
        self.stack.enter_context(patch.dict(os.environ, g.ENVIRONMENT, clear=True))
        # Replace only this module's OS boundary, preserving real os.stat for
        # unittest traceback rendering and the unchanged pure policy validators.
        self.stack.enter_context(patch.object(g, 'os', SimpleNamespace(
            environ=os.environ, getppid=Mock(return_value=self.b.controller_pid),
            getpid=Mock(return_value=30), stat=Mock(return_value=SimpleNamespace(st_ino=1000)))))
        self.parent = self.stack.enter_context(patch.object(g.projection, '_live_root',
            side_effect=lambda *a: self.events.append('parent')))
        self.descriptor = self.stack.enter_context(patch.object(g, '_namespace_descriptor',
            side_effect=lambda *a: self.events.append('descriptor')))
        self.members = self.stack.enter_context(patch.object(g, '_members',
            side_effect=lambda b, members: self.events.append(('members', frozenset(members)))))
        self.enroll = self.stack.enter_context(patch.object(g, '_enroll',
            side_effect=lambda *a: self.events.append('enroll')))
        self.join = self.stack.enter_context(patch.object(g, '_join_namespace',
            side_effect=lambda *a: self.events.append('join')))
        self.close = self.stack.enter_context(patch.object(g, '_close_namespace',
            side_effect=lambda *a: self.events.append('close-known-fd')))
        def launch(*a, **kw):
            self.events.append('original-launch')
            raise ExecTransferred()
        self.launch = self.stack.enter_context(patch.object(g.retained_launch, 'launch', side_effect=launch))

    def test_enroll_then_join_then_close_known_fd_then_original_launch(self):
        with self.assertRaises(ExecTransferred):
            g.child_main(self.raw)
        self.assertEqual(self.events, ['actor', 'parent', 'descriptor',
            ('members', frozenset({11})), 'enroll', ('members', frozenset({11, 30})),
            'join', 'close-known-fd', 'original-launch'])
        args, kw = self.launch.call_args
        self.assertEqual(args[2:], (self.b, self.value))
        self.assertEqual(kw, {'scratch': '/srv/test/scratch', 'instance_id': 'next-owner'})

    def test_foreign_parent_refuses_before_enrollment(self):
        with patch.object(g.os, 'getppid', return_value=999), self.assertRaises(g.SupervisedLaunchRejected):
            g.child_main(self.raw)
        self.enroll.assert_not_called()
        self.join.assert_not_called()
        self.launch.assert_not_called()

    def test_wrong_environment_or_interpreter_refuses_before_parent(self):
        with patch.dict(os.environ, {'PYTHONPATH': '/foreign'}), self.assertRaises(g.SupervisedLaunchRejected):
            g.child_main(self.raw)
        with patch.object(g.sys, 'executable', '/other/python'), self.assertRaises(g.SupervisedLaunchRejected):
            g.child_main(self.raw)
        self.parent.assert_not_called()
        self.enroll.assert_not_called()

    def test_wrong_namespace_descriptor_refuses_before_enrollment(self):
        self.descriptor.side_effect = g.SupervisedLaunchRejected('descriptor')
        with self.assertRaises(g.SupervisedLaunchRejected):
            g.child_main(self.raw)
        self.enroll.assert_not_called()
        self.join.assert_not_called()

    def test_enrollment_or_namespace_failure_never_launches(self):
        for boundary in (self.enroll, self.join):
            boundary.side_effect = OSError('owned fixture')
            self.close.reset_mock()
            with self.assertRaises(OSError):
                g.child_main(self.raw)
            self.close.assert_called_once_with(9)
            self.launch.assert_not_called()
            boundary.side_effect = None

    def test_unconfirmed_join_and_returning_launcher_are_refused(self):
        with patch.object(g.os, 'stat', return_value=SimpleNamespace(st_ino=999)), self.assertRaises(g.SupervisedLaunchRejected):
            g.child_main(self.raw)
        self.launch.assert_not_called()
        self.launch.side_effect = None
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'launch_returned'):
            g.child_main(self.raw)


class ControllerLifecycle(unittest.TestCase, Fixtures):
    def setUp(self):
        self.configure()
        self.v = object.__new__(g.RetainedVolumeSupervisor)
        self.v._retained_child = None
        self.v.stage = 'RUNNING'
        self.v.spawn_uncertain = False
        self.v._worker_deadline = g.time.monotonic() + 120
        self.v.worker = Mock(pid=11)
        self.v.worker.poll.return_value = None
        self.v.scope = PurePosixPath(self.b.scope)
        self.v.scope_id = self.b.scope_identity
        self.stack.enter_context(patch.object(self.v, '_owned'))
        self.stack.enter_context(patch.object(self.v, '_launch_binding', return_value=self.b))
        self.stack.enter_context(patch.object(g, 'ROOT', PurePosixPath('/opt/owned')))
        self.trusted = self.stack.enter_context(patch.object(g.volume, 'trusted'))
        self.open_ns = self.stack.enter_context(patch.object(g, '_open_namespace', return_value=9))
        self.close_ns = self.stack.enter_context(patch.object(g, '_close_namespace'))
        self.start = self.stack.enter_context(patch.object(g.projection, 'process_start', return_value=300))
        self.members = self.stack.enter_context(patch.object(g, '_members'))
        self.process = Mock(pid=30)
        self.process.returncode = 0
        self.process.poll.return_value = 0
        self.spawn = self.stack.enter_context(patch.object(g.subprocess, 'Popen', return_value=self.process))
        self.send = self.stack.enter_context(patch.object(g.PipeCapture, 'send_once', autospec=True, side_effect=self.capture))
        self.drain = self.stack.enter_context(patch.object(g.PipeCapture, 'drain_available', autospec=True))
        self.output_bytes_override = None
        self.base_stop = self.stack.enter_context(patch.object(g.volume.VolumeSupervisor, 'stop', return_value={'base': 'stop'}))
        self.base_finish = self.stack.enter_context(patch.object(g.volume.VolumeSupervisor, 'finish', return_value={'base': 'finish'}))
        self.addCleanup(self.close_logs)

    def close_logs(self):
        pass  # no OS process/pipe is created by the controller fixtures

    def result(self):
        return {'state': 'PROJECTED_RETAINED_OWNER_CLOSED', 'pid': 30, 'epoch': 2,
                'completedChecks': ['preflight', 'response_preflight', 'before_epoch',
                    'response_before_epoch', 'after_epoch', 'response_after_epoch'],
                'serviceStarted': False, 'runtimeAdmissionAuthorized': False,
                'finiteWorkExecuted': False, 'fullD3BAccepted': False}

    def capture(self, capture, process, payload, timeout):
        capture.send_started = True
        capture.input_written = len(payload)
        capture.stdin_closed = capture.stdout_eof = capture.stderr_eof = True
        raw = self.output_bytes_override
        capture.stdout_bytes.extend(g._json_bytes(self.result()) + b'\n' if raw is None else raw)
        capture.stderr_bytes.extend(b'preserved native warning\n')
        if len(capture.stdout_bytes) > g.MAX_OUTPUT:
            capture.overflowed = True
            raise RuntimeError('bounded capture fixture')

    def capture_timeout(self, capture, process, payload, timeout):
        self.capture(capture, process, payload, timeout)
        raise subprocess.TimeoutExpired('fixed child', timeout)

    def invoke(self, **kw):
        return self.v.run_retained(IPC, fixture.FS, self.value,
            scratch='/srv/test/scratch', instance_id='next-owner', **kw)

    def assert_retained(self):
        self.assertIsNotNone(self.v._retained_child)
        for method in (self.v.stop, self.v.finish):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'child_unresolved'):
                method()
        self.base_stop.assert_not_called()
        self.base_finish.assert_not_called()
        self.process.terminate.assert_not_called()
        self.process.kill.assert_not_called()

    def test_fixed_dispatch_and_clean_child_before_original_volume_close(self):
        with patch.dict(os.environ, {'AMBIENT_SECRET': 'owned-test', 'PYTHONPATH': '/other'}):
            result = self.invoke()
        args, kw = self.spawn.call_args
        self.assertEqual(args[0], [g.PYTHON, '-I', '-B', '/opt/owned/' + g.ENTRY])
        self.assertEqual(kw['env'], g.ENVIRONMENT)
        self.assertEqual(kw['pass_fds'], (9,))
        self.assertTrue(kw['close_fds'])
        self.close_ns.assert_called_once_with(9)
        sent = self.send.call_args.args
        self.assertEqual(sent[3], 60)
        self.assertEqual(g.decode(sent[2][:-1])[2], self.value)
        self.assertEqual(kw['stdout'], subprocess.PIPE)
        self.assertEqual(kw['stderr'], subprocess.PIPE)
        self.assertEqual(kw['bufsize'], 0)
        self.assertEqual(result['state'], 'SUPERVISED_PROJECTED_OWNER_CLOSED')
        self.assertEqual(result['stderrSha256'], hashlib.sha256(b'preserved native warning\n').hexdigest())
        self.assertFalse(result['finiteWorkExecuted'])
        self.assertFalse(result['fullD3BAccepted'])
        self.assertEqual(self.v.stop(), {'base': 'stop'})
        self.assertEqual(self.v.finish(), {'base': 'finish'})

    def test_invalid_timeout_or_dead_worker_has_no_spawn(self):
        for timeout in (True, 0, -1, 61, 1.5):
            with self.assertRaises(g.SupervisedLaunchRejected):
                self.invoke(timeout=timeout)
        self.v.worker.poll.return_value = 2
        with self.assertRaises(g.SupervisedLaunchRejected):
            self.invoke()
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()

    def test_original_install_trust_failure_has_no_namespace_or_spawn(self):
        self.trusted.side_effect = g.volume.SupervisorRejected('untrusted fixture')
        with self.assertRaises(g.volume.SupervisorRejected):
            self.invoke()
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()

    def test_successful_or_unknown_attempt_cannot_spawn_again(self):
        self.invoke()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
            self.invoke()
        self.assertEqual(self.spawn.call_count, 1)

    def test_spawn_exception_retains_original_volume_and_does_not_retry(self):
        self.spawn.side_effect = OSError('unknown child creation')
        with self.assertRaises(OSError):
            self.invoke()
        self.assert_retained()
        self.close_ns.assert_called_once_with(9)
        with self.assertRaises(g.SupervisedLaunchRejected):
            self.invoke()
        self.assertEqual(self.spawn.call_count, 1)

    def test_child_identity_read_failure_after_spawn_retains_process(self):
        self.start.side_effect = OSError('starttime unavailable')
        with self.assertRaises(OSError):
            self.invoke()
        self.assertIs(self.v._retained_child.process, self.process)
        self.assert_retained()

    def test_timeout_retains_process_and_does_not_stop_or_resend(self):
        self.send.side_effect = self.capture_timeout
        self.process.poll.return_value = None
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(timeout=2)
        self.assert_retained()
        self.assertEqual(self.v.observe_retained()['state'], 'SUPERVISED_CHILD_RUNNING')
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.spawn.call_count, 1)

    def test_explicit_late_observation_reads_same_child_without_reexecution(self):
        self.send.side_effect = self.capture_timeout
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(timeout=2)
        self.assert_retained()
        result = self.v.observe_retained()
        self.assertTrue(result['observedAfterUnknown'])
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.spawn.call_count, 1)
        self.assertEqual(self.v.finish(), {'base': 'finish'})

    def test_nonzero_child_never_releases_volume(self):
        self.process.returncode = 2
        self.process.poll.return_value = 2
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'child_failed'):
            self.invoke()
        self.assert_retained()

    def test_forged_success_identity_scope_or_check_receipt_retains_volume(self):
        cases = [dict(pid=31), dict(epoch=1), dict(pid=True),
                 dict(finiteWorkExecuted=True), dict(serviceStarted=True),
                 dict(fullD3BAccepted=True), dict(runtimeAdmissionAuthorized=True),
                 dict(completedChecks=['x'] * 6), dict(completedChecks=list('abcdef')),
                 dict(completedChecks=list(reversed(g.COMPLETED_CHECKS))), dict(extra='foreign')]
        for changes in cases:
            with self.subTest(changes=changes):
                self.close_logs()
                self.v._retained_child = None  # fresh synthetic controller fixture
                original = self.result()
                self.result = lambda result={**original, **changes}: result
                with self.assertRaises(g.SupervisedLaunchRejected):
                    self.invoke()
                self.assert_retained()
                del self.result

    def test_excess_output_multiple_frames_or_malformed_json_retains_volume(self):
        for raw in (b'x' * (g.MAX_OUTPUT + 1), b'{}\n{}\n', b'not-json\n'):
            self.v._retained_child = None
            self.output_bytes_override = raw
            with self.assertRaises((g.SupervisedLaunchRejected, ValueError, RuntimeError)):
                self.invoke()
            self.assert_retained()

    def test_expired_worker_budget_refuses_before_namespace_or_spawn(self):
        self.v._worker_deadline = g.time.monotonic() + 60
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'deadline_insufficient'):
            self.invoke()
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()

    def test_returned_result_cannot_mutate_stored_success(self):
        result = self.invoke()
        result['owner']['epoch'] = 999
        self.assertEqual(self.v.observe_retained()['owner']['epoch'], 2)

    def test_lost_worker_or_lingering_cgroup_member_retains_volume(self):
        self.members.side_effect = g.SupervisedLaunchRejected('lingering child')
        with self.assertRaises(g.SupervisedLaunchRejected):
            self.invoke()
        self.assert_retained()


if __name__ == '__main__':
    unittest.main()
