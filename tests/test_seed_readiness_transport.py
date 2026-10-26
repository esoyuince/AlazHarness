"""Owned transport contracts. No caller, native code, WSL or root operation runs."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/qa/r155a1_linux_transport.py'
SPEC = importlib.util.spec_from_file_location('owned_r155_transport', SOURCE)
transport = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transport)


class OwnedProcess:
    pid = 12345

    def __init__(self, exit_code=None, allow_wait=False):
        self.exit_code = exit_code
        self.allow_wait = allow_wait
        self.wait_calls = []
        self.poll_calls = 0

    def poll(self):
        self.poll_calls += 1
        return self.exit_code

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        if not self.allow_wait:
            raise AssertionError('A retained or unknown fixture must never wait')
        if self.exit_code is None:
            raise subprocess.TimeoutExpired('owned-process', timeout)
        return self.exit_code

    def terminate(self):
        raise AssertionError('No transport path may terminate an owned process')

    def kill(self):
        raise AssertionError('No transport path may kill an owned process')


class CustodyTests(unittest.TestCase):
    def identity(self):
        return {'pid': OwnedProcess.pid, 'startTicks': 999}

    def failure(self, custody=True):
        value = {'kind': 'R155A1_SAME_IMAGE_SEED_READINESS', 'result': 'NOT_ACCEPTED',
                 'state': 'OUTCOME_UNKNOWN' if custody else 'REFUSED'}
        if custody:
            value['custody'] = {'state': 'RETAINED_CONTROLLER', **self.identity()}
        return value

    def test_live_custodian_is_not_waited_for(self):
        process = OwnedProcess()
        with patch.object(transport, 'process_identity', return_value=self.identity()):
            value = transport.classify(process, self.identity(), b'', transport.canonical(self.failure()))
        self.assertEqual(value['state'], 'CALLER_RETAINED_OUTCOME_UNKNOWN')
        self.assertIs(value['verifiedLiveCustody'], True)
        self.assertIs(value['callerTerminalObserved'], False)
        self.assertEqual(process.wait_calls, [])

    def test_wrong_pid_ticks_dead_or_changed_custodian_never_accepts_or_waits(self):
        for fault in ('pid', 'ticks', 'dead', 'changed'):
            with self.subTest(fault=fault):
                process = OwnedProcess(exit_code=2 if fault == 'dead' else None)
                value = self.failure()
                if fault == 'pid':
                    value['custody']['pid'] += 1
                if fault == 'ticks':
                    value['custody']['startTicks'] += 1
                observed = self.identity()
                if fault == 'changed':
                    observed['startTicks'] += 1
                with patch.object(transport, 'process_identity', return_value=observed):
                    with self.assertRaises(transport.TransportRejected):
                        transport.classify(process, self.identity(), b'', transport.canonical(value))
                self.assertEqual(process.wait_calls, [])

    def test_unknown_without_custody_never_waits(self):
        process = OwnedProcess()
        value = self.failure(custody=False)
        value['state'] = 'OUTCOME_UNKNOWN'
        with self.assertRaises(transport.TransportRejected):
            transport.classify(process, self.identity(), b'', transport.canonical(value))
        self.assertEqual(process.wait_calls, [])

    def test_early_refusal_requires_actual_exit_two(self):
        for exit_code in (0, 2, None):
            with self.subTest(exit_code=exit_code):
                process = OwnedProcess(exit_code=exit_code, allow_wait=True)
                raw = transport.canonical(self.failure(custody=False))
                if exit_code == 2:
                    result = transport.classify(process, self.identity(), b'', raw)
                    self.assertEqual(result['state'], 'CALLER_TERMINAL_REFUSED')
                else:
                    with self.assertRaises((transport.TransportRejected, subprocess.TimeoutExpired)):
                        transport.classify(process, self.identity(), b'', raw)
                self.assertEqual(process.wait_calls, [5])

    def test_mixed_or_malformed_frames_never_wait(self):
        for out, err in ((b'{}\n', b'{}\n'), (b'', b''), (b'', b'{}\n{}\n'),
                         (b'', b'{"result":"NOT_ACCEPTED","result":"PASS"}\n')):
            with self.subTest(out=out, err=err):
                process = OwnedProcess()
                with self.assertRaises(transport.TransportRejected):
                    transport.classify(process, self.identity(), out, err)
                self.assertEqual(process.wait_calls, [])


@unittest.skipUnless(sys.platform == 'linux', 'Linux selectable pipe contract')
class PipeCollectionTests(unittest.TestCase):
    def process_with_owned_pipes(self, stdout=b'', stderr=b''):
        process = OwnedProcess()
        for name, raw in (('stdout', stdout), ('stderr', stderr)):
            read_fd, write_fd = os.pipe()
            try:
                if raw:
                    os.write(write_fd, raw)
            finally:
                os.close(write_fd)
            stream = os.fdopen(read_fd, 'rb', buffering=0)
            setattr(process, name, stream)
            self.addCleanup(stream.close)
        return process

    def test_eof_is_complete_even_when_caller_remains_live(self):
        process = self.process_with_owned_pipes(stderr=b'owned-diagnostic\n')
        observation = {'pipesComplete': False}
        self.assertEqual(transport.collect(process, observation, seconds=1), (b'', b'owned-diagnostic\n'))
        self.assertTrue(observation['pipesComplete'])
        self.assertEqual(process.poll_calls, 0)
        self.assertEqual(process.wait_calls, [])

    def test_overflow_is_bounded_and_does_not_wait_or_mark_complete(self):
        process = self.process_with_owned_pipes(stdout=b'123456789')
        observation = {'pipesComplete': False}
        with patch.object(transport, 'MAX_OUTPUT', 8):
            with self.assertRaisesRegex(transport.TransportRejected, 'overflow_unknown'):
                transport.collect(process, observation, seconds=1)
        self.assertEqual(bytes(observation['buffers']['stdout']), b'12345678')
        self.assertFalse(observation['pipesComplete'])
        self.assertEqual(process.wait_calls, [])

    def test_timeout_preserves_unknown_without_wait(self):
        process = self.process_with_owned_pipes()
        observation = {'pipesComplete': False}
        with self.assertRaisesRegex(transport.TransportRejected, 'timeout_unknown'):
            transport.collect(process, observation, seconds=0)
        self.assertFalse(observation['pipesComplete'])
        self.assertEqual(process.wait_calls, [])


class BundleTests(unittest.TestCase):
    def fixture(self):
        sources = {name: ('# owned fixture ' + name + '\n').encode() for name in transport.FILES}
        rows = {name: {'sha256': transport.sha(raw), 'size': len(raw)} for name, raw in sources.items()}
        manifest = transport.canonical({'protocol': 'alaz-r155a1-input-v1', 'files': rows})
        data = {**sources, 'manifest.json': manifest}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, raw in sorted(data.items()):
                archive.writestr(name, raw)
        bundle = buffer.getvalue()
        intent = {'kind': 'R155A1_SAME_IMAGE_ACCEPT_INTENT', 'lab': transport.LAB,
                  'inputRoot': str(transport.INPUT), 'stateRoot': '/srv/alaz-r155a1',
                  'manifestSha256': transport.sha(manifest), 'bundleSha256': transport.sha(bundle),
                  'bundleBytes': len(bundle), 'transportSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  'hostRunnerSha256': '1' * 64, 'ordinaryProofSha256': '2' * 64,
                  'ordinaryProducerSha256': rows[transport.SEED]['sha256'],
                  'sourceFiles': rows, 'baseCommit': '3' * 40}
        return bundle, intent, data

    def test_exact_owned_bundle_is_returned_without_staging(self):
        bundle, intent, data = self.fixture()
        self.assertEqual(transport.unpack(bundle, intent), data)

    def test_wrong_bundle_or_ordinary_producer_digest_is_rejected(self):
        for fault in ('bundle', 'producer'):
            with self.subTest(fault=fault):
                bundle, intent, _ = self.fixture()
                intent['bundleSha256' if fault == 'bundle' else 'ordinaryProducerSha256'] = '0' * 64
                with self.assertRaises(transport.TransportRejected):
                    transport.unpack(bundle, intent)


if __name__ == '__main__':
    unittest.main()
