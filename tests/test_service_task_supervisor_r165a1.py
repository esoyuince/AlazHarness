"""Original supervisor custody with actual task/lifecycle child pipes.

The child emits explicit synthetic owner/HTTP receipts. Worker, namespace,
mount, cgroup and lease ports use the documented R164 fixture doubles; actual
original stop/finish implementations remain counted. No installed/native,
kernel or model acceptance is claimed.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch

from service_closure_fixtures_r164a1 import ClosureHarness, g
from test_service_task_channel_r165a1 import CHILD
from test_service_task_protocol_r165a1 import http_request

ROOT = Path(__file__).resolve().parents[1]
_POPEN = subprocess.Popen


class TaskHarness(ClosureHarness):
    def _spawn(self, *args, **kwargs):
        self.launch_calls.append((args, kwargs))
        script = CHILD
        if self.mode == 'exit_on_release':
            marker = '  else:emit(data)\n else:'
            assert script.count(marker) == 1
            script = script.replace(marker, '  else:emit(data)\n'
                "  while not pathlib.Path(journal+'.exit').exists():time.sleep(.001)\n"
                '  raise SystemExit(1)\n else:')
        process = _POPEN([sys.executable, '-u', '-c', script, str(ROOT), self.mode,
                          str(self.journal)], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.children.append(process)
        return process


@unittest.skipUnless(os.name == 'posix', 'requires selectable POSIX child pipes and directory fsync')
class TaskSupervisorTests(unittest.TestCase):
    def ready(self, harness):
        self.assertEqual(harness.start_observed()['state'], 'READY')
        return harness.volume._service_child

    def counts(self, harness):
        return (harness.stop_calls, harness.stop_writes, harness.finish_calls,
                harness.loop_closes, harness.lease_closes)

    def close_original(self, harness):
        result = harness.close_service()
        deadline = time.monotonic() + 3
        while result['state'] != 'COMPLETED' and time.monotonic() < deadline:
            result = harness.observe(timeout=.05)
        if result['state'] == 'COMPLETED' and result['volumeClosure']['state'] == 'NOT_STARTED':
            result = harness.close_service()
        self.assertEqual(result['state'], 'COMPLETED')
        self.assertEqual(result['volumeClosure']['state'], 'CLOSED')
        return result

    def test_task_status_task_close_share_original_owner_sequence_and_cleanup(self):
        with TaskHarness() as h:
            child = self.ready(h)
            refs = child, child.process, child.channel, h.volume.worker, h.volume.lease
            first = h.volume.task_service(http_request(), timeout=2)
            self.assertIsNone(first['error'])
            self.assertEqual(first['response']['status'], 200)
            observed = h.observe()
            self.assertEqual(observed['state'], 'READY')
            self.assertNotIn('bodyBase64', json.dumps(observed))
            self.assertNotIn('authorization', json.dumps(observed))
            child.channel.command('status', timeout=2)
            second = h.volume.task_service(http_request(), timeout=2)
            self.assertIsNone(second['error'])
            self.assertEqual(child.channel.task_reply['sequence'], 3)
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.close_original(h)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))
            self.assertEqual(refs, (h.volume._service_child, child.process, child.channel,
                                    h.volume.worker, h.volume.lease))
            self.assertEqual(h.lines(), [{'action': 'http', 'sequence': 1},
                {'action': 'status', 'sequence': 2}, {'action': 'http', 'sequence': 3},
                {'action': 'close', 'sequence': 4}])
            self.assertEqual(h.popen.call_count, 1)

    def test_custody_or_process_identity_drift_refuses_before_transmission(self):
        for field in ('start_ticks', 'channel', 'process', 'binding', 'lease'):
            with self.subTest(field=field), TaskHarness() as h:
                child = self.ready(h)
                original = child, child.process_anchor, child.channel_anchor, child.custody.lease
                if field == 'start_ticks':
                    child.start_ticks += 1
                elif field == 'channel':
                    replacement = object.__new__(g.ServiceChannel)
                    replacement.__dict__.update(child.channel.__dict__)
                    child.channel = replacement
                elif field == 'process':
                    child.process = Mock(pid=child.pid)
                elif field == 'binding':
                    child.binding = replace(child.binding)
                else:
                    h.volume.lease = Mock()
                result = h.volume.task_service(http_request(), timeout=2)
                self.assertEqual(result, {'response': None, 'error': 'service_task_identity_unknown'})
                self.assertTrue(child.blocked)
                self.assertEqual(h.lines(), [])
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
                self.assertEqual(original, (h.volume._service_child_anchor, child.process_anchor,
                                             child.channel_anchor, child.custody.lease))

    def test_pending_task_is_only_observed_and_not_retransmitted(self):
        with TaskHarness('delayed') as h:
            child = self.ready(h)
            first = h.volume.task_service(http_request(), timeout=.01)
            self.assertEqual(first['error'], 'service_task_outcome_unknown')
            self.assertIsNotNone(child.channel.pending)
            repeated = h.volume.task_service(http_request(), timeout=.01)
            self.assertEqual(repeated['error'], 'service_task_exchange_pending')
            self.assertEqual(child.channel.sequence, 1)
            deadline = time.monotonic() + 3
            while child.channel.pending is not None and time.monotonic() < deadline:
                h.observe(timeout=.05)
            self.assertIsNone(child.channel.pending)
            self.assertEqual(h.observe()['state'], 'READY')
            self.assertEqual(h.lines(), [{'action': 'http', 'sequence': 1}])
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            fresh = h.volume.task_service(http_request(path='/alaz/host/v1/requests/' + 'b' * 32),
                                          timeout=2)
            self.assertIsNone(fresh['error'])
            self.close_original(h)
            self.assertEqual([row['sequence'] for row in h.lines()], [1, 2, 3])

    def test_custody_loss_during_completed_http_exchange_refuses_its_response(self):
        for field in ('worker', 'lease'):
            with self.subTest(field=field), TaskHarness() as h:
                child = self.ready(h)
                channel = child.channel
                original = child, child.process_anchor, child.channel_anchor, child.custody.lease
                actual_task = channel.task
                def exchange_then_drift(http, *, timeout):
                    result = actual_task(http, timeout=timeout)
                    if field == 'worker':
                        h._worker_code = 1
                        h.volume.worker.returncode = 1
                    else:
                        h.volume.lease = Mock()
                    return result
                with patch.object(channel, 'task', side_effect=exchange_then_drift):
                    result = h.volume.task_service(http_request(), timeout=2)
                self.assertEqual(result, {'response': None, 'error': 'service_task_identity_unknown'})
                self.assertTrue(child.blocked)
                self.assertEqual(child.phase, 'UNKNOWN')
                self.assertEqual(h.lines(), [{'action': 'http', 'sequence': 1}])
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
                self.assertEqual(original, (h.volume._service_child_anchor, child.process_anchor,
                                             child.channel_anchor, child.custody.lease))
                self.assertEqual(h.popen.call_count, 1)

    def test_valid_task_reply_followed_by_actual_child_exit_is_not_success(self):
        with TaskHarness('exit_on_release') as h:
            child = self.ready(h)
            channel = child.channel
            actual_task = channel.task
            def exchange_then_exit(http, *, timeout):
                result = actual_task(http, timeout=timeout)
                self.assertEqual(result['state'], 'READY')
                self.assertIsNotNone(channel.task_reply)
                Path(str(h.journal) + '.exit').write_text('release test child')
                self.assertEqual(child.process.wait(timeout=2), 1)
                # Reproduce _wait's reply-accepted/exit-known window before
                # either EOF is observed. _reap marks UNKNOWN without raising.
                self.assertFalse(channel.stdout_eof or channel.stderr_eof)
                channel._reap()
                self.assertEqual(channel.phase, 'UNKNOWN')
                self.assertIsNotNone(channel.task_reply)
                return result
            with patch.object(channel, 'task', side_effect=exchange_then_exit):
                result = h.volume.task_service(http_request(), timeout=2)
            self.assertEqual(result, {'response': None, 'error': 'service_task_outcome_unknown'})
            self.assertEqual(child.phase, 'UNKNOWN')
            self.assertEqual(h.lines(), [{'action': 'http', 'sequence': 1}])
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertIs(h.volume._service_child_anchor, child)
            self.assertIs(child.channel_anchor, channel)
            self.assertIs(g.volume._RETAINED[h.volume.token], h.volume)

    def test_partial_task_input_cannot_be_completed_by_observation_or_close(self):
        with TaskHarness('partial_input') as h:
            child = self.ready(h)
            http = http_request('POST', '/alaz/host/v1/intents', b'x' * 200000)
            result = h.volume.task_service(http, timeout=.01)
            self.assertEqual(result['error'], 'service_task_outcome_unknown')
            written = child.channel.input_written
            self.assertGreater(written, 0)
            self.assertLess(written, len(child.channel.input_bytes))
            h.observe(timeout=.01)
            h.close_service(timeout=.01)
            self.assertEqual(h.volume.task_service(http_request(), timeout=.01)['error'],
                             'service_task_exchange_pending')
            self.assertEqual(child.channel.input_written, written)
            self.assertEqual(child.channel.sequence, 1)
            self.assertEqual(h.lines(), [])
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertIs(g.volume._RETAINED[h.volume.token], h.volume)

    def test_http_uncertainty_preserves_ready_owner_and_explicit_close(self):
        with TaskHarness('http_error') as h:
            child = self.ready(h)
            result = h.volume.task_service(http_request(), timeout=2)
            self.assertEqual(result, {'response': None, 'error': 'service_task_http_outcome_unknown'})
            self.assertEqual(h.observe()['state'], 'READY')
            self.assertIsNone(child.channel.failure)
            self.assertFalse(child.blocked)
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.close_original(h)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))

    def test_changed_reply_owner_or_sequence_retains_original_custody(self):
        for mode in ('bad_owner', 'bad_sequence', 'trailing_partial'):
            with self.subTest(mode=mode), TaskHarness(mode) as h:
                child = self.ready(h)
                result = h.volume.task_service(http_request(), timeout=2)
                self.assertEqual(result['error'], 'service_task_outcome_unknown')
                self.assertEqual(h.observe()['state'], 'UNKNOWN')
                self.assertIsNone(child.channel.task_reply)
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
                self.assertIs(h.volume._service_child, child)
                self.assertIs(g.volume._RETAINED[h.volume.token], h.volume)

    def test_tasks_after_closed_volume_cannot_repeat_cleanup(self):
        with TaskHarness() as h:
            self.ready(h)
            self.close_original(h)
            result = h.volume.task_service(http_request(), timeout=2)
            self.assertEqual(result, {'response': None, 'error': 'service_task_service_closing'})
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))
            self.assertEqual(h.lines(), [{'action': 'close', 'sequence': 1}])

    def test_unstarted_and_foreign_actor_cannot_launch_or_forward_tasks(self):
        with TaskHarness() as h:
            self.assertEqual(h.volume.task_service(http_request(), timeout=2),
                             {'response': None, 'error': 'service_task_not_started'})
            self.assertEqual(h.popen.call_count, 0)
            self.ready(h)
            errors = []
            def foreign():
                try:
                    h.volume.task_service(http_request(), timeout=2)
                except g.SupervisedServiceRejected as exc:
                    errors.append(str(exc))
            thread = threading.Thread(target=foreign)
            thread.start(); thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ['service_supervised_original_actor'])
            self.assertEqual(h.lines(), [])
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.close_original(h)


if __name__ == '__main__':
    unittest.main()
