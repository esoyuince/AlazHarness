"""Real owned subprocess/pipe I/O; no Gateway, model, root or namespace work."""
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
from supervised_pipe_capture import CaptureRejected, PipeCapture


@unittest.skipUnless(sys.platform == 'linux', 'fixed Linux product pipe transport')
class RealPipeContracts(unittest.TestCase):
    def child(self, source):
        process = subprocess.Popen([sys.executable, '-I', '-B', '-u', '-c', source],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        def fixture_cleanup():
            # Fixture-only cleanup, never product retirement or volume acceptance.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
        self.addCleanup(fixture_cleanup)
        return process

    def test_large_input_and_two_output_pipes_do_not_deadlock(self):
        process = self.child("import sys; sys.stdout.buffer.write(b'o'*40000); "
            "sys.stderr.buffer.write(b'e'*40000); data=sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(data[:2])")
        capture = PipeCapture()
        payload = b'xy' + b'z' * 60000 + b'\n'
        capture.send_once(process, payload, 5)
        self.assertEqual(process.returncode, 0)
        self.assertTrue(capture.complete)
        self.assertEqual(capture.input_written, len(payload))
        self.assertEqual(capture.stdout_bytes, b'o' * 40000 + b'xy')
        self.assertEqual(capture.stderr_bytes, b'e' * 40000)
        with self.assertRaises(CaptureRejected):
            capture.send_once(process, payload, 5)

    def test_output_overflow_is_bounded_and_does_not_signal_owned_child(self):
        process = self.child("import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(b'x'*129)")
        capture = PipeCapture(limit=128)
        with patch.object(process, 'terminate', wraps=process.terminate) as terminate, \
             patch.object(process, 'kill', wraps=process.kill) as kill:
            with self.assertRaisesRegex(CaptureRejected, 'output_bound'):
                capture.send_once(process, b'owned\n', 5)
            terminate.assert_not_called()
            kill.assert_not_called()
        self.assertEqual(len(capture.stdout_bytes), 128)
        self.assertTrue(capture.overflowed)
        self.assertFalse(capture.complete)
        with self.assertRaises(CaptureRejected):
            capture.drain_available(process)

    def test_timeout_then_explicit_read_observation_never_resends(self):
        process = self.child("import sys,time; data=sys.stdin.buffer.read(); "
            "time.sleep(2); sys.stdout.buffer.write(data)")
        capture = PipeCapture()
        with patch.object(process, 'terminate', wraps=process.terminate) as terminate, \
             patch.object(process, 'kill', wraps=process.kill) as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                capture.send_once(process, b'once\n', 1)
            terminate.assert_not_called()
            kill.assert_not_called()
        self.assertEqual(capture.input_written, 5)
        with self.assertRaises(CaptureRejected):
            capture.send_once(process, b'once\n', 1)
        process.wait(timeout=5)
        with patch('supervised_pipe_capture.os.write', side_effect=AssertionError('no second send')):
            capture.drain_available(process)
        self.assertTrue(capture.complete)
        self.assertEqual(capture.stdout_bytes, b'once\n')

    def test_invalid_bounds_refuse_before_any_pipe_operation(self):
        for limit in (True, 0, 65537, -1):
            with self.assertRaises(CaptureRejected):
                PipeCapture(limit=limit)
        process = object()
        for payload, timeout in ((b'', 1), (b'x' * 65538, 1), (b'x', True), (b'x', 61)):
            capture = PipeCapture()
            with self.assertRaises(CaptureRejected):
                capture.send_once(process, payload, timeout)
            self.assertFalse(capture.send_started)


if __name__ == '__main__':
    unittest.main()
