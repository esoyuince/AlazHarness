"""R163 owner/delegation contracts and actual synthetic child-pipe evidence.

Kernel, mounted volume, lease and native ports are explicit doubles. No native
service, model, namespace entry, image attach or volume release is accepted by
these tests. Only test-owned synthetic subprocesses are terminated in teardown.
"""
from contextlib import ExitStack
from dataclasses import asdict, replace
import importlib.util
import io
import json
import os
from pathlib import PurePosixPath
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from service_supervisor_fixtures_r163a1 import (
    Harness, ROOT, SID, INSTANCE, SCRATCH, g, sv, launch_values, projection_fixture)

_BINDING = g._binding


class PlanContracts(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(g, 'ROOT', PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(g.mapping.os, 'makedev',
            side_effect=lambda major, minor: 1792 + minor, create=True))
        self.ipc, self.fs, self.record, self.scratch, self.instance, self.sid = launch_values()

    def frozen(self, **kw):
        values = dict(scratch=self.scratch, instance_id=self.instance, service_id=self.sid)
        values.update(kw)
        return g.freeze_launch(self.ipc, self.fs, self.record, **values)

    def bootstrap(self):
        return g._bytes({'protocol': g.PROTOCOL, 'binding': asdict(projection_fixture.binding()),
                         'namespaceFd': 9, 'plan': self.frozen().decode('ascii')})

    def test_plan_is_detached_canonical_typed_and_pure(self):
        with patch.object(g.volume, 'trusted', side_effect=AssertionError('no I/O')), \
                patch.object(g.kernel, '_open_namespace', side_effect=AssertionError('no namespace')), \
                patch.object(g.subprocess, 'Popen', side_effect=AssertionError('no process')):
            raw = self.frozen()
            one = g.decode_launch(raw); two = g.decode_launch(raw)
        self.assertEqual(len(one), 6); self.assertEqual(one[2], self.record)
        self.assertIs(type(one[2]), g.handoff.ServiceStartup)
        self.assertIsNot(one[0], two[0]); self.assertIsNot(one[1], two[1])
        self.ipc['principalContract']['gatewayUid'] = 999
        self.fs['readonly'].append('/tmp/extra'); one[0]['principalContract']['gatewayUid'] = 111
        self.assertEqual(g.decode_launch(raw)[0]['principalContract']['gatewayUid'], 23001)
        self.assertNotIn('/tmp/extra', g.decode_launch(raw)[1]['readonly'])
        self.assertEqual(g._bytes(json.loads(raw)), raw)

    def test_plan_shape_canonical_bounds_and_duplicates_rejected(self):
        raw = self.frozen(); value = json.loads(raw)
        candidates = [None, '{}', bytearray(raw), b'', b'\xff', raw + b'\n', b' ' + raw,
            b'x' * (g.MAX_BOOTSTRAP + 1), b'[' * 1500 + b']' * 1500,
            raw.replace(b'"protocol":', b'"protocol":"duplicate","protocol":')]
        for key in tuple(value):
            changed = dict(value); del changed[key]; candidates.append(g._bytes(changed))
        candidates.extend((g._bytes({**value, 'extra': 1}),
                           g._bytes({**value, 'protocol': g.kernel.PROTOCOL}),
                           g._bytes({**value, 'record': True})))
        for candidate in candidates:
            with self.subTest(value=type(candidate).__name__), self.assertRaises(g.SupervisedServiceRejected):
                g.decode_launch(candidate)

    def test_instance_service_scratch_and_readonly_contracts(self):
        for name, values in (
                ('instance_id', ('previous-native-owner', '', 'x' * 129, None, '../bad')),
                ('service_id', ('a' * 31, 'A' * 32, True, None, 'g' * 32)),
                ('scratch', ('/dev/null', '/srv/test/missing', '/srv//test/scratch'))):
            for value in values:
                with self.subTest(name=name, value=value), self.assertRaises(g.SupervisedServiceRejected):
                    self.frozen(**{name: value})
        self.fs['readonly'] = ['/usr/bin']
        with self.assertRaisesRegex(g.SupervisedServiceRejected, 'entry_not_readonly'):
            self.frozen()

    def test_bootstrap_binds_volume_profile_and_rejects_retained_wire(self):
        raw = self.bootstrap(); data, binding, plan = g.decode(raw)
        self.assertEqual(plan[2], self.record)
        self.assertEqual(binding, projection_fixture.binding())
        for key, value in (('protocol', g.kernel.PROTOCOL), ('namespaceFd', True),
                           ('namespaceFd', 2), ('namespaceFd', 2**20), ('plan', {})):
            with self.subTest(key=key), self.assertRaises(g.SupervisedServiceRejected):
                g.decode(g._bytes({**data, key: value}))
        changed = dict(data); changed['binding'] = dict(data['binding'], profile_inode=999)
        with self.assertRaises(g.SupervisedServiceRejected): g.decode(g._bytes(changed))
        changed = dict(data); changed['binding'] = dict(data['binding'], mountpoint='/srv/test/other')
        with self.assertRaises(g.SupervisedServiceRejected): g.decode(g._bytes(changed))

    def test_export_overlap_is_rejected_before_bootstrap_effects(self):
        self.fs['readonly'].append('/srv/test/volume/profile')
        with self.assertRaises(g.SupervisedServiceRejected): g.decode(self.bootstrap())

    def test_epoch_exhaustion_is_known_before_namespace_and_spawn(self):
        state = replace(self.record.state, epoch=2**63 - 1)
        record = replace(self.record, state=state, service=replace(self.record.service, epoch=state.epoch))
        g.handoff.validate(record, expected_home=record.service.home)
        with Harness() as h:
            h.record = record
            with patch.object(g.kernel, '_open_namespace') as opened, \
                    self.assertRaisesRegex(g.SupervisedServiceRejected, 'epoch_exhausted'):
                h.launch()
            opened.assert_not_called(); h.popen.assert_not_called()
            self.assertIsNone(h.volume._service_child)


class ChildBootstrap(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close); self.events = []
        self.stack.enter_context(patch.object(g, 'ROOT', PurePosixPath('/opt/owned')))
        self.stack.enter_context(patch.object(g.mapping.os, 'makedev',
            side_effect=lambda major, minor: 1792 + minor, create=True))
        ipc, fs, record, scratch, instance, sid = launch_values()
        plan = g.freeze_launch(ipc, fs, record, scratch=scratch, instance_id=instance, service_id=sid)
        self.binding = projection_fixture.binding()
        self.raw = g._bytes({'protocol': g.PROTOCOL, 'binding': asdict(self.binding),
                            'namespaceFd': 9, 'plan': plan.decode('ascii')})
        self.os = SimpleNamespace(environ=dict(g.ENVIRONMENT), getpid=lambda: 30,
            getppid=lambda: 10, stat=lambda path: SimpleNamespace(st_ino=1000))
        self.stack.enter_context(patch.object(g, 'os', self.os))
        self.stack.enter_context(patch.object(g, 'sys', SimpleNamespace(executable=g.PYTHON,
            flags=SimpleNamespace(isolated=1), dont_write_bytecode=True)))
        self.stack.enter_context(patch.object(g.volume, 'actor', side_effect=self.mark('actor')))
        self.parent = self.stack.enter_context(patch.object(g.projection, '_live_root',
                                                           side_effect=self.mark('parent')))
        for name, label in (('_namespace_descriptor', 'descriptor'), ('_members', 'members'),
                            ('_enroll', 'enroll'), ('_join_namespace', 'join'),
                            ('_close_namespace', 'close_fd')):
            setattr(self, label, self.stack.enter_context(patch.object(g.kernel, name,
                                                              side_effect=self.mark(label))))
        self.launch = self.stack.enter_context(patch.object(g.launch, 'launch', side_effect=self.mark('launch')))

    def mark(self, label):
        def run(*args, **kw): self.events.append(label)
        return run

    def test_enrolls_before_join_and_fixed_r162_launch_on_same_binding(self):
        with self.assertRaisesRegex(g.SupervisedServiceRejected, 'launch_returned'):
            g.child_main(self.raw)
        self.assertEqual(self.events, ['actor', 'parent', 'descriptor', 'members',
            'enroll', 'members', 'join', 'close_fd', 'launch'])
        self.parent.assert_called_once_with(10, 100)
        self.assertEqual([call.args[1] for call in self.members.call_args_list], [{11}, {11, 30}])
        args, kw = self.launch.call_args
        self.assertEqual(args[2], self.binding); self.assertIs(type(args[3]), g.handoff.ServiceStartup)
        self.assertEqual(kw, dict(scratch=SCRATCH, instance_id=INSTANCE, service_id=SID))
        self.close_fd.assert_called_once_with(9)

    def test_wrong_parent_and_fixed_environment_refuse_before_enrollment(self):
        self.os.getppid = lambda: 999
        with self.assertRaisesRegex(g.SupervisedServiceRejected, 'direct_parent'): g.child_main(self.raw)
        self.enroll.assert_not_called(); self.launch.assert_not_called()
        self.os.getppid = lambda: 10; self.os.environ['EXTRA'] = 'secret'
        with self.assertRaisesRegex(g.SupervisedServiceRejected, 'fixed_child'): g.child_main(self.raw)
        self.enroll.assert_not_called()

    def test_changed_controller_or_namespace_cannot_reach_enrollment(self):
        for mock in (self.parent, self.descriptor):
            mock.side_effect = RuntimeError('untrusted details')
            with self.assertRaises(RuntimeError): g.child_main(self.raw)
            self.enroll.assert_not_called(); self.launch.assert_not_called()
            mock.side_effect = self.mark('parent' if mock is self.parent else 'descriptor')

    def test_enrollment_or_join_failure_closes_only_known_namespace_fd(self):
        for mock in (self.enroll, self.join):
            mock.side_effect = RuntimeError('failed')
            with self.assertRaises(RuntimeError): g.child_main(self.raw)
            self.close_fd.assert_called_once_with(9); self.launch.assert_not_called()
            self.close_fd.reset_mock()
            mock.side_effect = self.mark('enroll' if mock is self.enroll else 'join')

    def test_unconfirmed_join_cannot_reach_projection_or_receiver(self):
        self.os.stat = lambda path: SimpleNamespace(st_ino=999)
        with self.assertRaisesRegex(g.SupervisedServiceRejected, 'join_unconfirmed'): g.child_main(self.raw)
        self.close_fd.assert_called_once_with(9); self.launch.assert_not_called()


class ControllerPreflight(unittest.TestCase):
    def test_original_begin_initializes_one_slot_and_forbids_subclass(self):
        owner = object.__new__(sv.ServiceVolumeSupervisor)
        with patch.object(g.volume.VolumeSupervisor, 'begin', return_value=owner) as begun:
            self.assertIs(sv.ServiceVolumeSupervisor.begin('pin', 'scope', 'point'), owner)
            self.assertIsNone(owner._service_child); begun.assert_called_once()
            class Other(sv.ServiceVolumeSupervisor): pass
            with self.assertRaisesRegex(g.volume.SupervisorRejected, 'exact_owner'):
                Other.begin('pin', 'scope', 'point')
            self.assertEqual(begun.call_count, 1)

    def test_no_attempt_observation_and_close_have_no_child_effect(self):
        with Harness() as h:
            self.assertEqual(h.observe()['state'], 'NEW')
            self.assertEqual(h.close_service()['state'], 'NEW')
            self.assertIsNone(h.volume._service_child); h.popen.assert_not_called()

    def test_invalid_wait_or_plan_does_not_consume_attempt(self):
        with Harness() as h:
            for value in (True, 0, -1, 61, float('nan'), float('inf')):
                with self.subTest(value=value), self.assertRaises(g.SupervisedServiceRejected):
                    h.launch(timeout=value)
            h.service_id = 'x'
            with self.assertRaises(g.SupervisedServiceRejected): h.launch()
            self.assertIsNone(h.volume._service_child); h.popen.assert_not_called()
            h.close_namespace.assert_not_called()

    def test_owner_worker_running_and_source_preconditions_precede_spawn(self):
        with Harness() as h:
            for field, value in (('stage', 'ATTACHED'), ('spawn_uncertain', True)):
                original = getattr(h.volume, field); setattr(h.volume, field, value)
                with self.assertRaises(g.SupervisedServiceRejected): h.launch()
                setattr(h.volume, field, original)
            h.volume.worker.poll.return_value = 1
            with self.assertRaises(g.SupervisedServiceRejected): h.launch()
            h.volume.worker.poll.return_value = None
            with patch.object(g.volume, 'trusted', side_effect=RuntimeError('untrusted source')), \
                    self.assertRaises(RuntimeError): h.launch()
            self.assertIsNone(h.volume._service_child); h.popen.assert_not_called()

    def test_bootstrap_mismatch_closes_namespace_without_reserving_child(self):
        with Harness() as h:
            with patch.object(g, '_binding', return_value=replace(h.binding, profile_inode=99)), \
                    self.assertRaises(g.SupervisedServiceRejected): h.launch()
            self.assertIsNone(h.volume._service_child); h.popen.assert_not_called()
            h.close_namespace.assert_called_once_with(9)

    def test_binding_captures_original_worker_parent_fence_and_private_namespace(self):
        with Harness() as h:
            with patch.object(g, 'os', SimpleNamespace(fstat=lambda fd: SimpleNamespace(st_ino=1000),
                                                       readlink=lambda path: 'mnt:[900]')), \
                    patch.object(g.kernel, '_namespace_descriptor') as descriptor, \
                    patch.object(g.kernel, '_members') as members:
                binding = _BINDING(h.volume, h.record, 9)
            self.assertEqual(binding, h.binding)
            self.assertIs(binding.image, h.volume.pin)
            descriptor.assert_called_once_with(9, binding)
            members.assert_called_once_with(binding, {h.volume.worker.pid})

    def test_spawn_exception_retains_attempt_and_permanently_blocks_volume_closure(self):
        with Harness() as h:
            def failed(*args, **kw):
                self.assertIsNotNone(h.volume._service_child)
                raise OSError('credential must not appear')
            h.popen.side_effect = failed
            result = h.launch(); child = h.volume._service_child
            self.assertEqual(result['state'], 'UNKNOWN'); self.assertIsNone(child.process)
            self.assertNotIn('credential', json.dumps(result))
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'already_attempted'): h.launch()
            before = h.owned_calls; self.assertEqual(h.observe()['state'], 'UNKNOWN')
            self.assertGreater(h.owned_calls, before); self.assertIs(h.volume._service_child, child)
            with patch.object(g.volume.VolumeSupervisor, 'stop') as stop, \
                    patch.object(g.volume.VolumeSupervisor, 'finish') as finish:
                with self.assertRaisesRegex(g.SupervisedServiceRejected, 'child_completion_required'):
                    h.volume.stop()
                with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                    h.volume.finish()
                stop.assert_not_called(); finish.assert_not_called()
            self.assertEqual(h.popen.call_count, 1)

    def test_returned_popen_is_retained_when_start_identity_fails(self):
        with Harness() as h:
            process = Mock(pid=30); h.popen.return_value = process; h.popen.side_effect = None
            with patch.object(g.projection, 'process_start', side_effect=OSError('not observed')):
                result = h.launch()
            child = h.volume._service_child
            self.assertEqual(result['state'], 'UNKNOWN'); self.assertIs(child.process, process)
            self.assertIsNone(child.start_ticks); self.assertIsNone(child.channel)
            process.terminate.assert_not_called(); process.kill.assert_not_called()

    def test_channel_constructor_or_namespace_close_failure_keeps_popen(self):
        for failure in ('channel', 'namespace'):
            with self.subTest(failure=failure), Harness() as h:
                process = Mock(pid=30); h.popen.return_value = process; h.popen.side_effect = None
                if failure == 'channel':
                    with patch.object(g, 'ServiceChannel', side_effect=RuntimeError('constructor')):
                        result = h.launch()
                else:
                    h.close_namespace.side_effect = OSError('close')
                    result = h.launch()
                self.assertEqual(result['state'], 'UNKNOWN')
                self.assertIs(h.volume._service_child.process, process)
                if failure == 'namespace': self.assertFalse(h.volume._service_child.channel.input_started)
                process.terminate.assert_not_called(); process.kill.assert_not_called()


class BootstrapEntry(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('r163_test_entry', ROOT / 'scripts/run_supervised_service.py')
        self.entry = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.entry)

    def test_newline_finishes_without_eof_or_buffered_read_ahead(self):
        unread = bytearray(b'bootstrap\nnext-command\n'); read_sizes = []
        def read(fd, size):
            self.assertEqual(fd, 0); read_sizes.append(size)
            data = bytes(unread[:size]); del unread[:size]; return data
        with patch.object(self.entry.os, 'read', side_effect=read), \
                patch.object(self.entry.select, 'select', return_value=([0], [], [])):
            self.assertEqual(self.entry.read_frame(), b'bootstrap')
        self.assertEqual(unread, b'next-command\n'); self.assertTrue(all(size == 1 for size in read_sizes))

    def test_bootstrap_eof_empty_bound_and_deadline_refuse_without_receiver(self):
        for chunks, bound, selectable in (([b''], 10, True), ([b'\n'], 10, True),
                                         ([b'x'] * 4, 2, True), ([], 10, False)):
            with self.subTest(chunks=chunks), patch.object(self.entry, 'MAX_BOOTSTRAP', bound), \
                    patch.object(self.entry.os, 'read', side_effect=chunks), \
                    patch.object(self.entry.select, 'select', return_value=([0] if selectable else [], [], [])), \
                    self.assertRaises(ValueError): self.entry.read_frame()

    def test_refusal_stays_on_stderr_even_when_diagnostics_fail(self):
        for stderr in (io.StringIO(), Mock(write=Mock(side_effect=BrokenPipeError('secret')))):
            stdout = io.StringIO()
            with patch.object(self.entry, 'read_frame', side_effect=RuntimeError('secret')), \
                    patch.object(self.entry.sys, 'argv', ['fixed']), \
                    patch.object(self.entry.sys, 'stderr', stderr), \
                    patch.object(self.entry.sys, 'stdout', stdout):
                self.assertEqual(self.entry.main(), 2)
            self.assertEqual(stdout.getvalue(), '')
            if isinstance(stderr, io.StringIO): self.assertNotIn('secret', stderr.getvalue())


@unittest.skipUnless(os.name == 'posix', 'requires selectable POSIX subprocess pipes')
class ActualChildPipes(unittest.TestCase):
    def until(self, h, state):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            result = h.observe(timeout=.03)
            if result['state'] == state: return result
        self.fail('original child did not reach ' + state)

    def test_same_owner_popen_channel_final_without_kernel_custody_cannot_release_volume(self):
        with Harness() as h:
            self.assertEqual(h.start_observed()['state'], 'READY')
            child = h.volume._service_child; channel = child.channel; process = child.process
            self.assertIs(channel.process, process); self.assertIs(child.owner, h.volume)
            args, kw = h.launch_calls[0]
            self.assertEqual(args[0], [g.PYTHON, '-I', '-B', '/opt/owned/' + g.ENTRY])
            self.assertEqual(kw['env'], g.ENVIRONMENT)
            self.assertEqual(kw['pass_fds'], (9,)); self.assertTrue(kw['close_fds'])
            self.assertEqual(kw['cwd'], '/'); self.assertEqual(kw['bufsize'], 0)
            self.assertEqual(h.observe()['state'], 'READY')
            final = h.close_service()
            self.assertEqual(final['state'], 'COMPLETED'); self.assertTrue(final['childExited'])
            self.assertFalse(final['volumeMayClose']); self.assertEqual(process.returncode, 0)
            self.assertIs(h.volume._service_child, child); self.assertIs(child.channel, channel)
            self.assertIs(child.process, process); self.assertEqual(h.popen.call_count, 1)
            self.assertEqual([row.get('action') for row in h.lines()], [None, 'close'])
            # R164 connects normal teardown, but this R163 child-only fixture
            # deliberately supplies no valid original cgroup/volume proof.
            self.assertEqual(final['volumeClosure']['state'], 'UNKNOWN')
            self.assertFalse(final['volumeClosure']['volumeUnmounted'])
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'stop_already_attempted'):
                h.volume.stop()
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                h.volume.finish()
            self.assertEqual(h.close_service()['state'], 'COMPLETED')
            self.assertEqual(len(h.lines()), 2)

    def test_lost_ready_observes_original_reply_without_bootstrap_resend(self):
        with Harness('delayed_ready') as h:
            self.assertEqual(h.launch(timeout=.01)['state'], 'UNKNOWN')
            child = h.volume._service_child; process = child.process
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'already_attempted'): h.launch()
            result = self.until(h, 'READY')
            self.assertTrue(result['observedAfterUnknown']); self.assertIs(child.process, process)
            self.assertEqual(len(h.lines()), 1); self.assertEqual(h.popen.call_count, 1)
            self.assertEqual(h.close_service()['state'], 'COMPLETED')

    def test_lost_close_is_observed_without_new_sequence_or_command(self):
        with Harness('delayed_reply') as h:
            self.assertEqual(h.start_observed()['state'], 'READY')
            self.assertEqual(h.close_service(timeout=.01)['state'], 'UNKNOWN')
            child = h.volume._service_child; channel = child.channel
            self.assertEqual(channel.sequence, 1)
            h.close_service(timeout=.01)
            self.assertEqual(channel.sequence, 1)
            self.assertEqual(self.until(h, 'COMPLETED')['state'], 'COMPLETED')
            self.assertEqual([row.get('action') for row in h.lines()], [None, 'close'])

    def test_partial_bootstrap_observe_and_close_never_flush_remaining_input(self):
        with Harness() as h:
            real_write = os.write; count = 0
            def short(fd, data):
                nonlocal count
                if count:
                    raise BlockingIOError()
                count += 1
                return real_write(fd, data[:1])
            with patch.object(os, 'write', side_effect=short):
                self.assertEqual(h.launch(timeout=.01)['state'], 'UNKNOWN')
            channel = h.volume._service_child.channel
            self.assertEqual(channel.input_written, 1)
            with patch.object(os, 'write', side_effect=AssertionError('observation wrote input')):
                self.assertEqual(h.observe(timeout=.01)['state'], 'UNKNOWN')
                self.assertEqual(h.close_service(timeout=.01)['state'], 'UNKNOWN')
            self.assertEqual(channel.input_written, 1); self.assertEqual(channel.sequence, 0)
            self.assertEqual(h.lines(), [])

    def test_foreign_ready_and_exited_child_cannot_admit_another_attempt(self):
        for mode in ('foreign_epoch', 'ready_exit'):
            with self.subTest(mode=mode), Harness(mode) as h:
                result = h.start_observed()
                if result['state'] == 'READY': result = self.until(h, 'UNKNOWN')
                self.assertEqual(result['state'], 'UNKNOWN')
                child = h.volume._service_child
                with self.assertRaises(g.SupervisedServiceRejected): h.launch()
                h.close_service(); self.assertIs(h.volume._service_child, child)
                self.assertEqual(h.popen.call_count, 1)
                self.assertEqual([row.get('action') for row in h.lines()], [None])

    def test_worker_controller_child_and_channel_identity_changes_block_commands(self):
        for changed in ('worker', 'token', 'parent_ticks', 'child_ticks', 'channel'):
            with self.subTest(changed=changed), Harness() as h:
                self.assertEqual(h.start_observed()['state'], 'READY')
                child = h.volume._service_child
                if changed == 'worker':
                    h.volume.worker = Mock(pid=11); h.volume.worker.poll.return_value = None
                elif changed == 'token': h.volume.token = 'b' * 32
                elif changed == 'channel': child.channel.process = Mock(pid=child.pid)
                else:
                    target = os.getpid() if changed == 'parent_ticks' else child.pid
                    h.stack.enter_context(patch.object(g.projection, 'process_start',
                        side_effect=lambda pid: h._start(pid) + (1 if pid == target else 0)))
                self.assertEqual(h.close_service()['state'], 'UNKNOWN')
                self.assertTrue(child.blocked); self.assertEqual(len(h.lines()), 1)
                self.assertIs(h.volume._service_child, child)

    def test_other_actor_cannot_operate_original_child(self):
        with Harness() as h:
            self.assertEqual(h.start_observed()['state'], 'READY')
            results = []
            def foreign():
                try: h.close_service()
                except g.SupervisedServiceRejected as exc: results.append(str(exc))
            thread = threading.Thread(target=foreign)
            thread.start(); thread.join(timeout=2)
            self.assertFalse(thread.is_alive()); self.assertEqual(results, ['service_supervised_original_actor'])
            self.assertFalse(h.volume._service_child.blocked)
            self.assertEqual(h.volume._service_child.phase, 'READY')
            self.assertEqual(len(h.lines()), 1)
            self.assertEqual(h.close_service()['state'], 'COMPLETED')


if __name__ == '__main__':
    unittest.main()
