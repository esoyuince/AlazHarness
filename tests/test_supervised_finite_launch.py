"""Fixed finite dispatch with explicit synthetic process/kernel receipts.

These tests execute the real pure work/result codecs and original policy/handoff
validators. Process, namespace, projection, native work and lease boundaries are
test doubles: no installed, privileged, native-model or volume acceptance occurs.
"""
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import gateway_supervised_launch as g
import gateway_finite_protocol as finite
import test_supervised_retained_launch as readiness


def qualification_work():
    return {'protocol': finite.WORK_PROTOCOL, 'sessionId': 'finite-session',
            'requestIds': {'normal': 'request-a', 'new': 'request-b', 'error': 'request-c'}}


def qualification_result(work, *, pid=30, epoch=2):
    """Synthetic full receipt, validated as data only by the real pure codec."""
    normal = {'kind': 'normal', 'requestId': work['requestIds']['normal'],
              'admissionId': 'admission-a', 'outcome': 'completed',
              'apiResultSha256': 'a' * 64, 'storedResultSha256': 'b' * 64,
              'computationCount': 1}
    cases = [normal, {**normal, 'kind': 'replay'}]
    for kind, count, name in (('new', 2, 'b'), ('error', 3, 'c')):
        cases.append({'kind': kind, 'requestId': work['requestIds'][kind],
                      'admissionId': 'admission-' + name,
                      'outcome': 'failed' if kind == 'error' else 'completed',
                      'apiResultSha256': 'c' * 64, 'storedResultSha256': 'd' * 64,
                      'computationCount': count})
    return {'protocol': finite.RESULT_PROTOCOL, 'state': 'PROJECTED_FINITE_OWNER_CLOSED',
            'pid': pid, 'epoch': epoch, 'completedChecks': list(finite.COMPLETED_CHECKS),
            'workSha256': finite.work_digest(work), 'caseReceipts': cases,
            'nativeProfileCallEvents': {name: 1 for name in finite.PROFILE_FUNCTIONS},
            'close': {'consumerState': 'DETACHED', 'ownerState': 'CLOSED',
                      'sameThreeConnections': True, 'registryRefcounts': 0,
                      'physicalConnectionsClosed': 3, 'modelInstancesClosed': True,
                      'rowsChangedByRetirement': 0, 'callerLeaseReleased': True},
            'model': {'kind': 'scripted-factory-fixture',
                      'factoryComputationCloseDoubled': True,
                      'realProviderCalls': 0, 'modelInvocations': 3},
            'localAdmissionActivated': True, 'canonicalApiPublished': True,
            'serviceStarted': False, 'runtimeAdmissionAuthorized': False,
            'finiteWorkExecuted': True, 'fullD3BAccepted': False}


class FiniteFixtures(readiness.Fixtures):
    def configure(self):
        super().configure()
        self.work = qualification_work()
        self.data.update(protocol=g.FINITE_PROTOCOL, work=copy.deepcopy(self.work))
        self.raw = g._json_bytes(self.data)


class FiniteDataContracts(unittest.TestCase, FiniteFixtures):
    def setUp(self):
        self.configure()

    def test_typed_roundtrip_adds_separate_validated_work_without_launch_authority(self):
        with patch.object(g.subprocess, 'Popen') as spawn, patch.object(g.volume, 'actor') as actor:
            data, binding, record, view, fs, work = g.decode_finite(self.raw)
        self.assertEqual(binding, self.b)
        self.assertEqual(record, self.value)
        self.assertEqual(view['principalContract'], readiness.fixture.P)
        self.assertEqual(fs['writable'], readiness.fixture.FS['writable'])
        self.assertEqual(work, self.work)
        work['requestIds']['normal'] = 'changed'
        self.assertEqual(data['work'], self.work)
        spawn.assert_not_called()
        actor.assert_not_called()

    def test_readiness_and_finite_payloads_cannot_select_each_others_decoder(self):
        with self.assertRaises(g.SupervisedLaunchRejected):
            g.decode(self.raw)
        data = copy.deepcopy(self.data)
        data.pop('work')
        data['protocol'] = g.PROTOCOL
        self.assertEqual(len(g.decode(g._json_bytes(data))), 5)
        with self.assertRaises(g.SupervisedLaunchRejected):
            g.decode_finite(g._json_bytes(data))
        for changes in ({'protocol': g.PROTOCOL}, {'entry': '/bin/sh'}, {'operation': 'readiness'}):
            with self.subTest(changes=changes), self.assertRaises(g.SupervisedLaunchRejected):
                g.decode_finite(g._json_bytes({**self.data, **changes}))

    def test_invalid_work_refuses_with_bounded_reason(self):
        for work in (None, [], {}, {**self.work, 'prompt': 'sensitive-example'},
                     {**self.work, 'sessionId': '/arbitrary/path'},
                     {**self.work, 'requestIds': {'normal': 'same', 'new': 'same', 'error': 'c'}},
                     {**self.work, 'requestIds': {'normal': True, 'new': 'b', 'error': 'c'}}):
            data = {**self.data, 'work': work}
            with self.subTest(work=work), self.assertRaisesRegex(
                    g.SupervisedLaunchRejected, '^supervised_finite_work_invalid$'):
                g.decode_finite(g._json_bytes(data))

    def test_finite_payload_still_enforces_original_binding_policy_and_canonical_bytes(self):
        changes = [lambda d: d['binding'].update(profile_inode=13),
                   lambda d: d['filesystem'].update(enabled=False),
                   lambda d: d.update(namespaceFd=True),
                   lambda d: d.update(instanceId='prior-owner')]
        for change in changes:
            data = copy.deepcopy(self.data)
            change(data)
            with self.assertRaises(g.SupervisedLaunchRejected):
                g.decode_finite(g._json_bytes(data))
        for raw in (b' ' + self.raw, self.raw + b'\n',
                    self.raw[:-1] + b',"work":{}}', b'x' * (g.MAX_INPUT + 1)):
            with self.assertRaises(g.SupervisedLaunchRejected):
                g.decode_finite(raw)


class FiniteChildSequence(unittest.TestCase, FiniteFixtures):
    def setUp(self):
        readiness.ChildSequence.setUp(self)

        def launch(*args, **kwargs):
            self.events.append('fixed-finite-launch')
            raise readiness.ExecTransferred()

        self.finite_launch = self.stack.enter_context(
            patch.object(g.retained_launch, 'launch_finite', side_effect=launch))

    def test_original_guards_enroll_join_close_before_fixed_finite_dispatch(self):
        with self.assertRaises(readiness.ExecTransferred):
            g.finite_child_main(self.raw)
        self.assertEqual(self.events, ['actor', 'parent', 'descriptor',
            ('members', frozenset({11})), 'enroll', ('members', frozenset({11, 30})),
            'join', 'close-known-fd', 'fixed-finite-launch'])
        args, kwargs = self.finite_launch.call_args
        self.assertEqual(args[2:], (self.b, self.value, self.work))
        self.assertEqual(kwargs, {'scratch': '/srv/test/scratch', 'instance_id': 'next-owner'})
        self.launch.assert_not_called()

    def test_foreign_parent_or_namespace_descriptor_never_enrolls_or_dispatches(self):
        with patch.object(g.os, 'getppid', return_value=999), self.assertRaises(g.SupervisedLaunchRejected):
            g.finite_child_main(self.raw)
        self.descriptor.side_effect = g.SupervisedLaunchRejected('descriptor')
        with self.assertRaises(g.SupervisedLaunchRejected):
            g.finite_child_main(self.raw)
        self.enroll.assert_not_called()
        self.join.assert_not_called()
        self.launch.assert_not_called()
        self.finite_launch.assert_not_called()

    def test_wrong_environment_interpreter_or_work_refuses_before_parent(self):
        with patch.dict(os.environ, {'PYTHONPATH': '/foreign'}), self.assertRaises(g.SupervisedLaunchRejected):
            g.finite_child_main(self.raw)
        with patch.object(g.sys, 'executable', '/other/python'), self.assertRaises(g.SupervisedLaunchRejected):
            g.finite_child_main(self.raw)
        data = {**self.data, 'work': {**self.work, 'command': '/bin/sh'}}
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'finite_work_invalid'):
            g.finite_child_main(g._json_bytes(data))
        self.parent.assert_not_called()
        self.enroll.assert_not_called()
        self.finite_launch.assert_not_called()

    def test_partial_enrollment_or_join_failure_closes_only_known_fd_and_never_dispatches(self):
        for boundary in (self.enroll, self.join):
            boundary.side_effect = OSError('owned synthetic boundary')
            self.close.reset_mock()
            with self.assertRaises(OSError):
                g.finite_child_main(self.raw)
            self.close.assert_called_once_with(9)
            self.launch.assert_not_called()
            self.finite_launch.assert_not_called()
            boundary.side_effect = None

    def test_unconfirmed_join_and_returning_finite_launcher_fail_closed(self):
        with patch.object(g.os, 'stat', return_value=SimpleNamespace(st_ino=999)), self.assertRaises(g.SupervisedLaunchRejected):
            g.finite_child_main(self.raw)
        self.finite_launch.assert_not_called()
        self.finite_launch.side_effect = None
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'launch_returned'):
            g.finite_child_main(self.raw)
        self.launch.assert_not_called()


class FiniteControllerLifecycle(unittest.TestCase, FiniteFixtures):
    # Reuse process/pipe/kernel boundaries without inheriting readiness tests.
    setUp = readiness.ControllerLifecycle.setUp
    close_logs = readiness.ControllerLifecycle.close_logs
    capture = readiness.ControllerLifecycle.capture
    capture_timeout = readiness.ControllerLifecycle.capture_timeout
    assert_retained = readiness.ControllerLifecycle.assert_retained

    def result(self):
        return qualification_result(self.work)

    def invoke(self, **kwargs):
        return self.v.run_finite(readiness.IPC, readiness.fixture.FS, self.value,
            self.work, scratch='/srv/test/scratch', instance_id='next-owner', **kwargs)

    def invoke_readiness(self):
        return self.v.run_retained(readiness.IPC, readiness.fixture.FS, self.value,
            scratch='/srv/test/scratch', instance_id='next-owner')

    def test_fixed_dispatch_complete_bound_receipt_then_original_close(self):
        with patch.dict(os.environ, {'AMBIENT_SECRET': 'owned-test', 'PYTHONPATH': '/other'}):
            result = self.invoke()
        args, kwargs = self.spawn.call_args
        self.assertEqual(args[0], [g.PYTHON, '-I', '-B', '/opt/owned/' + g.FINITE_ENTRY])
        self.assertEqual(kwargs['env'], g.ENVIRONMENT)
        self.assertEqual(kwargs['pass_fds'], (9,))
        self.assertTrue(kwargs['close_fds'])
        self.assertEqual(kwargs['cwd'], '/')
        self.assertEqual(kwargs['stdin'], subprocess.PIPE)
        self.assertEqual(kwargs['stdout'], subprocess.PIPE)
        self.assertEqual(kwargs['stderr'], subprocess.PIPE)
        self.assertEqual(kwargs['bufsize'], 0)
        self.close_ns.assert_called_once_with(9)
        sent = self.send.call_args.args
        self.assertEqual(sent[3], 60)
        decoded = g.decode_finite(sent[2][:-1])
        self.assertEqual(decoded[2], self.value)
        self.assertEqual(decoded[5], self.work)
        self.assertEqual(self.v._retained_child.operation, g.FINITE)
        self.assertEqual(result['state'], 'SUPERVISED_PROJECTED_FINITE_OWNER_CLOSED')
        self.assertEqual(result['owner'], self.result())
        self.assertEqual(result['owner']['caseReceipts'][-1]['outcome'], 'failed')
        self.assertEqual(result['inputSha256'], hashlib.sha256(sent[2][:-1]).hexdigest())
        self.assertEqual(result['stdoutSha256'], hashlib.sha256(g._json_bytes(self.result()) + b'\n').hexdigest())
        self.assertEqual(result['stderrSha256'], hashlib.sha256(b'preserved native warning\n').hexdigest())
        self.assertTrue(result['childExited'])
        self.assertTrue(result['volumeMayClose'])
        self.assertTrue(result['finiteWorkExecuted'])
        self.assertFalse(result['fullD3BAccepted'])
        trusted = {str(call.args[0]) for call in self.trusted.call_args_list}
        self.assertTrue({'/opt/owned/' + name for name in (
            g.FINITE_ENTRY, g.FINITE_TARGET_ENTRY,
            'packages/claw-hermes/gateway_supervised_launch.py',
            'packages/claw-hermes/gateway_finite_protocol.py',
            'packages/claw-hermes/gateway_finite_runtime.py')} <= trusted)
        self.process.wait.assert_called_once_with(timeout=0)
        self.members.assert_called_once_with(self.b, {11})
        self.assertEqual(self.v.stop(), {'base': 'stop'})
        self.assertEqual(self.v.finish(), {'base': 'finish'})

    def test_invalid_work_rejected_before_namespace_or_attempt_slot(self):
        self.work['requestIds']['new'] = self.work['requestIds']['normal']
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, '^supervised_finite_work_invalid$'):
            self.invoke()
        self.assertIsNone(self.v._retained_child)
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()
        self.send.assert_not_called()

    def test_finite_sources_must_be_trusted_before_namespace(self):
        def trust(path, **kwargs):
            if str(path).endswith('gateway_finite_runtime.py'):
                raise g.volume.SupervisorRejected('untrusted fixture')
        self.trusted.side_effect = trust
        with self.assertRaises(g.volume.SupervisorRejected):
            self.invoke()
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()
        self.assertIsNone(self.v._retained_child)

    def test_original_worker_wait_bounds_and_deadline_apply_to_finite(self):
        for timeout in (True, 0, -1, 61, 1.5):
            with self.assertRaises(g.SupervisedLaunchRejected):
                self.invoke(timeout=timeout)
        self.v._worker_deadline = g.time.monotonic() + 60
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'deadline_insufficient'):
            self.invoke()
        self.v.worker.poll.return_value = 2
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'worker_not_running'):
            self.invoke()
        self.open_ns.assert_not_called()
        self.spawn.assert_not_called()

    def test_deadline_rechecked_after_full_decode_before_child_attempt(self):
        with patch.object(self.v, '_time_budget', side_effect=[None,
                g.SupervisedLaunchRejected('supervised_worker_deadline_insufficient')]):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'deadline_insufficient'):
                self.invoke()
        self.close_ns.assert_called_once_with(9)
        self.spawn.assert_not_called()
        self.send.assert_not_called()
        self.assertIsNone(self.v._retained_child)

    def test_completed_finite_consumes_shared_slot_and_wrong_observer_cannot_read_cache(self):
        self.invoke()
        for launch in (self.invoke, self.invoke_readiness):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
                launch()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'operation_mismatch'):
            self.v.observe_retained()
        self.assertEqual(self.v._retained_child.phase, 'COMPLETED')
        self.assertEqual(self.spawn.call_count, 1)
        self.assertEqual(self.send.call_count, 1)

    def test_completed_readiness_consumes_same_slot_and_cannot_be_observed_as_finite(self):
        with patch.object(self, 'result', return_value=readiness.ControllerLifecycle.result(self)):
            result = self.invoke_readiness()
        self.assertFalse(result['finiteWorkExecuted'])
        for launch in (self.invoke, self.invoke_readiness):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
                launch()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'operation_mismatch'):
            self.v.observe_finite()
        self.assertEqual(self.spawn.call_count, 1)

    def test_spawn_exception_keeps_shared_attempt_and_never_signals_or_releases(self):
        self.spawn.side_effect = OSError('unknown child creation')
        with self.assertRaises(OSError):
            self.invoke()
        child = self.v._retained_child
        self.assertEqual(child.phase, 'UNKNOWN')
        self.assertEqual(child.expected_work, self.work)
        self.assert_retained()
        self.close_ns.assert_called_once_with(9)
        for launch in (self.invoke, self.invoke_readiness):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
                launch()
        self.assertIs(self.v._retained_child, child)
        self.assertEqual(self.spawn.call_count, 1)

    def test_unconfirmed_process_identity_retains_same_child(self):
        self.start.side_effect = OSError('starttime unavailable')
        with self.assertRaises(OSError):
            self.invoke()
        self.assertIs(self.v._retained_child.process, self.process)
        self.assertEqual(self.v._retained_child.phase, 'UNKNOWN')
        self.assert_retained()
        self.send.assert_not_called()

    def test_unknown_finite_can_only_observe_same_child_without_resend(self):
        self.send.side_effect = self.capture_timeout
        self.process.poll.return_value = None
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(timeout=2)
        child = self.v._retained_child
        self.assert_retained()
        for launch in (self.invoke, self.invoke_readiness):
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
                launch()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'operation_mismatch'):
            self.v.observe_retained()
        running = self.v.observe_finite()
        self.assertEqual(running['state'], 'SUPERVISED_CHILD_RUNNING')
        self.assertFalse(running['volumeMayClose'])
        self.assertIs(self.v._retained_child, child)
        self.assertEqual(child.phase, 'UNKNOWN')
        self.process.poll.return_value = 0
        result = self.v.observe_finite()
        self.assertTrue(result['observedAfterUnknown'])
        self.assertEqual(self.spawn.call_count, 1)
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(self.v.finish(), {'base': 'finish'})

    def test_unknown_readiness_cannot_admit_finite_or_change_observer(self):
        self.send.side_effect = self.capture_timeout
        self.process.poll.return_value = None
        with patch.object(self, 'result', return_value=readiness.ControllerLifecycle.result(self)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.invoke_readiness()
        self.assert_retained()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'already_attempted'):
            self.invoke()
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'operation_mismatch'):
            self.v.observe_finite()
        self.assertEqual(self.spawn.call_count, 1)
        self.assertEqual(self.send.call_count, 1)

    def test_nonzero_child_is_not_a_logical_application_failure_completion(self):
        self.process.returncode = self.process.poll.return_value = 2
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'child_failed'):
            self.invoke()
        self.assert_retained()

    def test_readiness_receipt_cannot_complete_finite(self):
        self.output_bytes_override = g._json_bytes(readiness.ControllerLifecycle.result(self)) + b'\n'
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, '^supervised_finite_result_invalid$'):
            self.invoke()
        self.assert_retained()

    def test_finite_receipt_cannot_complete_readiness(self):
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'result_identity'):
            self.invoke_readiness()
        self.assert_retained()

    def test_mismatched_work_process_epoch_or_incomplete_original_close_retains_volume(self):
        cases = [lambda r: r.update(workSha256='0' * 64),
                 lambda r: r.update(pid=31), lambda r: r.update(epoch=1),
                 lambda r: r['caseReceipts'][1].update(computationCount=2),
                 lambda r: r['caseReceipts'][-1].update(outcome='completed'),
                 lambda r: r['close'].update(callerLeaseReleased=False),
                 lambda r: r['close'].update(registryRefcounts=1),
                 lambda r: r['close'].update(physicalConnectionsClosed=2),
                 lambda r: r.update(fullD3BAccepted=True)]
        for change in cases:
            self.v._retained_child = None  # Fresh synthetic controller fixture only.
            receipt = self.result()
            change(receipt)
            self.output_bytes_override = g._json_bytes(receipt) + b'\n'
            with self.assertRaisesRegex(g.SupervisedLaunchRejected, '^supervised_finite_result_invalid$'):
                self.invoke()
            self.assertEqual(self.v._retained_child.phase, 'UNKNOWN')
            self.assert_retained()

    def test_forged_multiple_incomplete_or_overflowed_frames_retain_custody(self):
        for raw in (b'{}\n{}\n', b'not-json\n', b'{}', b'x' * (g.MAX_OUTPUT + 1)):
            self.v._retained_child = None
            self.output_bytes_override = raw
            with self.assertRaises((g.SupervisedLaunchRejected, ValueError, RuntimeError)):
                self.invoke()
            self.assert_retained()

    def test_live_mount_worker_and_empty_child_cgroup_required_after_valid_receipt(self):
        self.v.worker.poll.side_effect = [None, 2]
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'mount_worker_lost'):
            self.invoke()
        self.assert_retained()
        self.members.assert_not_called()
        self.v._retained_child = None
        self.v.worker.poll.side_effect = None
        self.v.worker.poll.return_value = None
        self.members.side_effect = g.SupervisedLaunchRejected('lingering child')
        with self.assertRaisesRegex(g.SupervisedLaunchRejected, 'lingering child'):
            self.invoke()
        self.assert_retained()

    def test_work_and_nested_result_cannot_be_rebound_after_dispatch(self):
        original = copy.deepcopy(self.work)
        result = self.invoke()
        self.work['requestIds']['normal'] = 'changed-input'
        result['owner']['caseReceipts'][0]['requestId'] = 'changed-output'
        result['owner']['close']['callerLeaseReleased'] = False
        self.assertEqual(self.v._retained_child.expected_work, original)
        observed = self.v.observe_finite()
        self.assertEqual(observed['owner']['caseReceipts'][0]['requestId'], original['requestIds']['normal'])
        self.assertTrue(observed['owner']['close']['callerLeaseReleased'])


class FixedFiniteEntry(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('fixed_supervised_finite_fixture',
            ROOT / g.FINITE_ENTRY)
        self.entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.entry)

    def invoke(self, raw, *, args=None, error=None):
        output = io.StringIO()
        process = SimpleNamespace(argv=['fixed-entry'] if args is None else args,
                                  stdin=SimpleNamespace(buffer=io.BytesIO(raw)))
        with patch.object(self.entry, 'sys', process), redirect_stdout(output), \
                patch.object(self.entry, 'finite_child_main', side_effect=error) as launch:
            status = self.entry.main()
        return status, json.loads(output.getvalue()), launch

    def test_arguments_missing_newline_trailing_data_or_size_fail_before_child(self):
        cases = [(b'{}\n', ['fixed-entry', '/bin/sh']), (b'{}', None),
                 (b'{}\n{}\n', None), (b'x' * (g.MAX_INPUT + 1) + b'\n', None)]
        for raw, args in cases:
            status, result, launch = self.invoke(raw, args=args)
            self.assertEqual(status, 2)
            self.assertEqual(result, {'state': 'SUPERVISED_FINITE_REFUSED', 'type': 'ValueError'})
            launch.assert_not_called()

    def test_valid_frame_only_reaches_fixed_finite_function_and_return_fails_closed(self):
        status, result, launch = self.invoke(b'{}\n')
        launch.assert_called_once_with(b'{}')
        self.assertEqual(status, 2)
        self.assertEqual(result, {'state': 'SUPERVISED_FINITE_REFUSED', 'type': 'RuntimeError'})

    def test_child_error_does_not_echo_sensitive_payload_or_exception_message(self):
        status, result, launch = self.invoke(b'private-fixture\n',
            error=g.SupervisedLaunchRejected('sensitive detail'))
        self.assertEqual(status, 2)
        self.assertEqual(result, {'state': 'SUPERVISED_FINITE_REFUSED',
                                  'type': 'SupervisedLaunchRejected'})
        launch.assert_called_once_with(b'private-fixture')


if __name__ == '__main__':
    unittest.main()
