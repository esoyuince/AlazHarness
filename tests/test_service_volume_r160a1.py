"""Service worker framing/ownership: real pipes; mount/root boundaries doubled.

No mount, cgroup, privilege change, installed runtime or model is exercised.
"""
from contextlib import ExitStack
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import service_volume_supervisor as service
import state_volume_supervisor as volume

spec = importlib.util.spec_from_file_location('owned_service_worker_test',
                                            ROOT / 'scripts/run_service_volume_worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class IdleFrameTests(unittest.TestCase):
    def test_idle_wait_has_no_deadline_until_first_byte(self):
        waits = []
        def wait(read, write, errors, timeout):
            waits.append(timeout)
            return read, [], []
        with patch.object(worker.select, 'select', side_effect=wait), \
                patch.object(worker.os, 'read', side_effect=[b'S', b'T', b'O', b'P', b'\n']):
            self.assertEqual(worker.line(), 'STOP')
        self.assertIsNone(waits[0])
        self.assertTrue(all(0 < n <= worker.FRAME_SECONDS for n in waits[1:]))

    def test_bootstrap_still_has_a_finite_deadline_before_any_byte(self):
        with patch.object(worker.select, 'select', return_value=([], [], [])) as wait, \
                self.assertRaisesRegex(volume.SupervisorRejected, 'input_timeout'):
            worker.line(15)
        self.assertGreater(wait.call_args.args[3], 0)
        self.assertLessEqual(wait.call_args.args[3], 15)

    def test_half_written_frame_times_out_without_stop_or_unmount(self):
        with patch.object(worker.select, 'select', side_effect=[([0], [], []), ([], [], [])]), \
                patch.object(worker.os, 'read', return_value=b'S'), \
                self.assertRaisesRegex(volume.SupervisorRejected, 'input_timeout'):
            worker.line()

    def test_controller_eof_is_not_a_clean_stop(self):
        with patch.object(worker.select, 'select', return_value=([0], [], [])), \
                patch.object(worker.os, 'read', return_value=b''), \
                self.assertRaisesRegex(volume.SupervisorRejected, 'controller_gone'):
            worker.line()

    def test_frame_has_a_hard_byte_bound(self):
        with patch.object(worker.select, 'select', return_value=([0], [], [])), \
                patch.object(worker.os, 'read', return_value=b'x'), \
                self.assertRaisesRegex(volume.SupervisorRejected, 'input_bound'):
            worker.line()

    @unittest.skipUnless(os.name == 'posix', 'POSIX pipe select required')
    def test_real_idle_pipe_survives_then_reads_exact_stop(self):
        script = (
            'import importlib.util,sys;'
            f's=importlib.util.spec_from_file_location("worker",{str(ROOT / "scripts/run_service_volume_worker.py")!r});'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m);'
            'm.FRAME_SECONDS=.05;print(m.line(),flush=True)')
        child = subprocess.Popen([sys.executable, '-B', '-c', script],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(.15)  # Longer than a started frame's deadline, while idle.
            self.assertIsNone(child.poll())
            out, err = child.communicate(b'STOP exact-owned-token\n', timeout=5)
            self.assertEqual((child.returncode, out, err), (0, b'STOP exact-owned-token\n', b''))
        finally:
            if child.poll() is None:
                child.kill()  # This test's disposable pipe fixture only.
                child.communicate()


class ServiceWorkerStart(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.target = self.root / 'target'
        self.scope = self.root / 'scope'
        self.target.mkdir(); self.scope.mkdir()
        (self.scope / 'cgroup.procs').write_text('123\n')
        self.value = object.__new__(service.ServiceVolumeSupervisor)
        self.value.stage = 'ATTACHED'; self.value.worker = None
        self.value.target = self.target; self.value.target_id = (1, 2)
        self.value.scope = self.scope; self.value.scope_id = (1, 3)
        self.value.token = 'a' * 32; self.value.who = (42, 7)
        self.value.loop_number = 9
        self.value.pin = SimpleNamespace(device=5, inode=6)
        self.process = Mock(pid=123)
        self.process.stdin = io.BytesIO()
        self.process.poll.return_value = None
        self.ready = {'state': 'MOUNTED', 'pid': 123, 'token': 'a' * 32,
                      'loopNumber': 9, 'mountNamespace': 'mnt:[123]',
                      'lifetime': 'owned-service'}
        stack = ExitStack(); self.addCleanup(stack.close)
        self.owned = stack.enter_context(patch.object(self.value, '_owned'))
        stack.enter_context(patch.object(service, 'trusted', return_value=(1, 2)))
        self.spawn = stack.enter_context(patch.object(service.subprocess, 'Popen', return_value=self.process))
        self.read = stack.enter_context(patch.object(service, 'read_line', return_value=self.ready))
        stack.enter_context(patch.object(service.os, 'readlink', side_effect=lambda path:
            'mnt:[456]' if path == '/proc/self/ns/mnt' else 'mnt:[123]'))
        stack.enter_context(patch.object(service.os.path, 'ismount', return_value=False))

    def test_opt_in_worker_starts_once_with_versioned_fixed_entry(self):
        result = self.value.start()
        self.assertEqual(result['lifetime'], 'owned-service')
        self.assertEqual(self.value.stage, 'RUNNING')
        args, kwargs = self.spawn.call_args
        self.assertEqual(args[0][-1], str(service.ROOT / 'scripts/run_service_volume_worker.py'))
        self.assertTrue(kwargs['close_fds'])
        self.assertEqual(kwargs['env'], {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        data = json.loads(self.process.stdin.getvalue())
        self.assertEqual(data['version'], 2)
        self.assertEqual(data['controllerPid'], 42)
        with self.assertRaisesRegex(volume.SupervisorRejected, 'start_once'):
            self.value.start()
        self.assertEqual(self.spawn.call_count, 1)

    def test_finite_worker_ack_cannot_claim_service_lifetime(self):
        self.ready.pop('lifetime')
        with self.assertRaisesRegex(volume.SupervisorRejected, 'ready_mismatch'):
            self.value.start()
        self.assertEqual(self.value.stage, 'STARTING')
        self.assertIs(self.value.worker, self.process)
        self.process.terminate.assert_not_called()

    def test_unknown_spawn_is_retained_before_effect(self):
        self.spawn.side_effect = OSError('synthetic ambiguous spawn')
        with self.assertRaises(OSError):
            self.value.start()
        self.assertEqual(self.value.stage, 'STARTING')
        self.assertTrue(self.value.spawn_uncertain)

    def test_unconfirmed_namespace_never_becomes_running(self):
        self.ready['mountNamespace'] = 'mnt:[456]'
        with self.assertRaisesRegex(volume.SupervisorRejected, 'not_private'):
            self.value.start()
        self.assertEqual(self.value.stage, 'STARTING')

    def test_missing_cgroup_member_never_becomes_running(self):
        (self.scope / 'cgroup.procs').write_text('')
        with self.assertRaisesRegex(volume.SupervisorRejected, 'outside_scope'):
            self.value.start()
        self.assertEqual(self.value.stage, 'STARTING')

    def test_unknown_service_worker_does_not_enable_original_volume_finish(self):
        self.spawn.side_effect = OSError('synthetic ambiguous spawn')
        with self.assertRaises(OSError):
            self.value.start()
        with self.assertRaisesRegex(volume.SupervisorRejected, 'spawn_unknown'):
            self.value.finish()


if __name__ == '__main__':
    unittest.main()
