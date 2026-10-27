"""Original child-to-volume closure, with explicit worker/kernel/lease doubles.

Actual owned Popen pipes and unchanged channel/volume/kernel-members functions
execute. This suite does not establish a real mounted/native installation.
"""
from dataclasses import replace
import json
import os
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from service_closure_fixtures_r164a1 import ClosureHarness, g, sv


@unittest.skipUnless(os.name == 'posix', 'requires selectable POSIX child pipes and directory fsync')
class ServiceClosureTests(unittest.TestCase):
    def ready(self, h):
        result = h.start_observed()
        self.assertEqual(result['state'], 'READY')
        self.assertEqual(result['volumeClosure'], {'state': 'NOT_STARTED',
            'volumeUnmounted': False, 'fenceRemovedAfterCleanup': False, 'imageLeaseReleased': False})
        return h.volume._service_child

    def until(self, h, expected):
        end = time.monotonic() + 3
        while time.monotonic() < end:
            result = h.observe(timeout=.02)
            if result['state'] == expected:
                return result
        self.fail('original child did not reach ' + expected)

    def child_done(self, h):
        child = self.ready(h)
        child.channel.command('close', timeout=2)
        result = self.until(h, 'COMPLETED')
        self.assertEqual(result['volumeClosure']['state'], 'NOT_STARTED')
        self.assertEqual((h.stop_calls, h.finish_calls, h.loop_closes, h.lease_closes), (0, 0, 0, 0))
        return child

    def counts(self, h):
        return h.stop_calls, h.stop_writes, h.finish_calls, h.loop_closes, h.lease_closes

    def stable_unknown(self, h, *, unmounted=False):
        child = h.volume._service_child
        result = h.observe()
        self.assertEqual(result['state'], 'COMPLETED')
        self.assertTrue(result['childExited'])
        self.assertEqual(result['volumeClosure'], {'state': 'UNKNOWN',
            'volumeUnmounted': unmounted, 'fenceRemovedAfterCleanup': False, 'imageLeaseReleased': False})
        before = self.counts(h)
        for operation in (h.observe, h.close_service, h.observe, h.close_service):
            result = operation()
            self.assertEqual(result['volumeClosure']['state'], 'UNKNOWN')
        self.assertEqual(self.counts(h), before)
        self.assertIs(h.volume._service_child, child)
        self.assertIs(h.volume._service_child_anchor, child)
        self.assertIs(g.volume._RETAINED[h.volume.token], h.volume)
        self.assertEqual([row.get('action') for row in h.lines()], [None, 'close'])

    def test_explicit_close_uses_original_stop_finish_and_preserves_every_owner(self):
        with ClosureHarness() as h:
            child = self.ready(h)
            refs = child, child.process, child.channel, h.volume.worker, h.volume.pin, h.volume.lease
            result = h.close_service()
            self.assertEqual(result['state'], 'COMPLETED')
            self.assertEqual(result['volumeClosure'], {'state': 'CLOSED', 'volumeUnmounted': True,
                'fenceRemovedAfterCleanup': True, 'imageLeaseReleased': True})
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))
            self.assertEqual(h.volume.stage, 'CLOSED')
            self.assertFalse(h.scope_path.exists()); self.assertFalse(h.fence_path.exists())
            self.assertEqual(refs, (h.volume._service_child, child.process, child.channel,
                h.volume.worker, h.volume.pin, h.volume.lease))
            self.assertIs(child.custody.lease, h.volume.lease)
            self.assertIs(child.process_anchor, child.process)
            self.assertIs(child.channel_anchor, child.channel)
            self.assertFalse(result['volumeMayClose']); self.assertFalse(result['retryAllowed'])
            self.assertFalse(result['fullD3BAccepted'])

    def test_cleanup_sequence_closes_loop_before_inventory_fence_then_lease_last(self):
        with ClosureHarness() as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.events, ['members_worker', 'original_stop', 'worker_stop_write',
                'worker_stop_flush', 'worker_unmounted', 'worker_exit_0', 'members_empty',
                'original_finish', 'empty_scope', 'loop_close', 'attachments', 'empty_scope',
                'scope_remove', 'fence_unlink', 'fence_fsync', 'lease_close',
                'worker_stdin_close', 'worker_stdout_close', 'worker_stderr_close'])
            self.assertNotIn(h.volume.token, g.volume._RETAINED)

    def test_child_completion_and_status_never_start_volume_cleanup(self):
        with ClosureHarness() as h:
            child = self.child_done(h)
            for _ in range(3):
                self.assertEqual(h.observe()['volumeClosure']['state'], 'NOT_STARTED')
                self.assertEqual(g.check_service_owner(h.volume)['state'], 'NOT_STARTED')
            self.assertIsNone(child.closure)
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertEqual(h.close_service()['volumeClosure']['state'], 'CLOSED')
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))

    def test_direct_stop_then_finish_requires_and_stores_original_receipts(self):
        with ClosureHarness() as h:
            child = self.child_done(h)
            stopped = h.volume.stop()
            self.assertEqual(stopped, {'state': 'UNMOUNTED', 'pid': h.volume.worker.pid,
                                       'token': h.volume.token})
            self.assertEqual(json.loads(child.closure.stop_reply), stopped)
            self.assertEqual(h.observe()['volumeClosure']['state'], 'STOPPED')
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0))
            result = h.volume.finish()
            self.assertEqual(result, g._FINISH_RESULT)
            self.assertEqual(json.loads(child.closure.finish_reply), result)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'stop_already_attempted'):
                h.volume.stop()
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                h.volume.finish()
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1))

    def test_direct_finish_cannot_use_a_child_final_in_place_of_stop_proof(self):
        with ClosureHarness() as h:
            self.child_done(h)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                h.volume.finish()
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertTrue(h.fence_path.exists()); self.assertFalse(h.volume.lease.closed)

    def test_running_child_cannot_authorize_direct_stop_or_finish(self):
        with ClosureHarness() as h:
            child = self.ready(h)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'child_completion_required'):
                h.volume.stop()
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                h.volume.finish()
            self.assertIsNone(child.closure); self.assertEqual(h.events, [])

    def test_lost_child_close_only_observes_then_fresh_explicit_close_starts_cleanup(self):
        with ClosureHarness('delayed_reply') as h:
            self.ready(h)
            self.assertEqual(h.close_service(timeout=.01)['state'], 'UNKNOWN')
            self.assertEqual(h.close_service(timeout=.01)['state'], 'UNKNOWN')
            self.assertEqual(h.volume._service_child.channel.sequence, 1)
            result = self.until(h, 'COMPLETED')
            self.assertEqual(result['volumeClosure']['state'], 'NOT_STARTED')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertEqual(h.close_service()['volumeClosure']['state'], 'CLOSED')
            self.assertEqual([row.get('action') for row in h.lines()], [None, 'close'])

    def test_final_and_both_pipe_eofs_do_not_replace_actual_child_exit(self):
        with ClosureHarness('final_alive_eof') as h:
            self.ready(h)
            result = h.close_service(timeout=.01)
            self.assertNotEqual(result['volumeClosure']['state'], 'CLOSED')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.until(h, 'COMPLETED')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertEqual(h.close_service()['volumeClosure']['state'], 'CLOSED')

    def test_nonzero_child_and_trailing_output_never_reach_original_stop(self):
        for mode in ('nonzero_final', 'trailing_final'):
            with self.subTest(mode=mode), ClosureHarness(mode) as h:
                self.ready(h)
                result = h.close_service()
                self.assertEqual(result['state'], 'UNKNOWN')
                for _ in range(2): h.observe(); h.close_service()
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
                self.assertTrue(h.fence_path.exists()); self.assertFalse(h.volume.lease.closed)

    def test_incomplete_or_changed_original_channel_proof_blocks_direct_stop(self):
        for field, value in (('stdout_eof', False), ('stderr_eof', False), ('pending', {}),
                             ('stdout', bytearray(b'trailing')), ('stdin_closed', False)):
            with self.subTest(field=field), ClosureHarness() as h:
                child = self.child_done(h)
                setattr(child.channel, field, value)
                with self.assertRaises(g.SupervisedServiceRejected): h.volume.stop()
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_final_receipt_native_store_or_lease_incompleteness_blocks_stop(self):
        for field, value in (('physicalStoresClosed', 2), ('callerLeaseReleased', False),
                             ('transportRetired', False), ('defaultExecutorJoined', False)):
            with self.subTest(field=field), ClosureHarness() as h:
                child = self.child_done(h)
                child.channel.final_frame['owner']['close'][field] = value
                with self.assertRaises(Exception): h.volume.stop()
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_extra_cgroup_pid_is_rejected_before_stop_and_retained(self):
        with ClosureHarness(failure='preflight_members') as h:
            self.ready(h); h.close_service()
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.stable_unknown(h)

    def test_nested_cgroup_is_rejected_before_stop_and_retained(self):
        with ClosureHarness(failure='preflight_nested') as h:
            self.ready(h); h.close_service()
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.stable_unknown(h)

    def test_original_lease_worker_pin_and_paths_cannot_be_replaced(self):
        fields = ('lease', 'worker', 'pin', 'scope', 'target', 'fence')
        for field in fields:
            with self.subTest(field=field), ClosureHarness() as h:
                self.child_done(h)
                setattr(h.volume, field, Mock())
                with self.assertRaises(Exception): h.volume.stop()
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_original_pid_start_ticks_channel_and_binding_are_not_adopted(self):
        for field in ('start_ticks', 'channel', 'binding'):
            with self.subTest(field=field), ClosureHarness() as h:
                child = self.child_done(h)
                if field == 'start_ticks': child.start_ticks += 1
                elif field == 'channel':
                    replacement = object.__new__(g.ServiceChannel)
                    replacement.__dict__.update(child.channel.__dict__)
                    child.channel = replacement
                else: child.binding = replace(child.binding)
                with self.assertRaises(g.SupervisedServiceRejected): h.volume.stop()
                self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_erased_child_slot_cannot_reenable_launch_or_generic_finish(self):
        with ClosureHarness() as h:
            child = self.ready(h)
            h.volume._service_child = None
            for operation in (h.volume.stop, h.volume.finish, h.launch, h.observe):
                with self.assertRaises(Exception): operation()
            self.assertIs(h.volume._service_child_anchor, child)
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertEqual(h.popen.call_count, 1)

    def test_foreign_actor_cannot_create_or_change_closure_attempt(self):
        with ClosureHarness() as h:
            child = self.child_done(h); errors = []
            def foreign():
                for operation in (h.volume.stop, h.volume.finish, h.close_service, h.observe):
                    try: operation()
                    except g.SupervisedServiceRejected as exc: errors.append(str(exc))
            thread = threading.Thread(target=foreign); thread.start(); thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, ['service_supervised_original_actor'] * 4)
            self.assertIsNone(child.closure); self.assertEqual(child.phase, 'COMPLETED')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_unknown_child_start_identity_keeps_original_owner_status_observable(self):
        with ClosureHarness() as h:
            original = h._start
            def ticks(pid):
                if pid not in (os.getpid(), h.volume.worker.pid):
                    raise OSError('fixture unobserved child start')
                return original(pid)
            with patch.object(g.projection, 'process_start', side_effect=ticks):
                result = h.launch()
            self.assertEqual(result['state'], 'UNKNOWN')
            self.assertIs(h.volume._service_child.process, h.children[0])
            self.assertEqual(g.check_service_owner(h.volume)['state'], 'NOT_STARTED')
            self.assertEqual(h.observe()['state'], 'UNKNOWN')
            self.assertEqual(h.close_service()['state'], 'UNKNOWN')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))
            self.assertEqual(h.popen.call_count, 1)

    def test_lost_original_worker_keeps_unknown_observation_without_cleanup(self):
        with ClosureHarness() as h:
            child = self.ready(h)
            h._worker_code = 1; h.volume.worker.returncode = 1
            self.assertEqual(g.check_service_owner(h.volume)['state'], 'NOT_STARTED')
            self.assertEqual(h.observe()['state'], 'UNKNOWN')
            self.assertTrue(child.blocked)
            self.assertEqual(h.close_service()['state'], 'UNKNOWN')
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_stop_write_failure_is_reserved_before_effect_and_never_replayed(self):
        with ClosureHarness(failure='stop_write') as h:
            self.ready(h); h.close_service()
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0))
            self.assertEqual(h.volume.stage, 'STOPPING'); self.stable_unknown(h)

    def test_stop_flush_failure_does_not_send_another_stop(self):
        with ClosureHarness(failure='stop_flush') as h:
            self.ready(h); h.close_service()
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0))
            self.stable_unknown(h)

    def test_lost_stop_reply_cannot_infer_success_from_worker_exit(self):
        with ClosureHarness(failure='stop_lost_reply') as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.volume.worker.poll(), 0)
            self.assertIsNone(h.volume._service_child.closure.stop_reply)
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0)); self.stable_unknown(h)

    def test_busy_stop_retains_original_owner_without_implicit_retry(self):
        with ClosureHarness(failure='stop_busy') as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.volume.stage, 'STOP_REFUSED')
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0)); self.stable_unknown(h)

    def test_foreign_stop_token_and_pid_never_authorize_finish(self):
        for failure in ('stop_foreign', 'stop_foreign_pid'):
            with self.subTest(failure=failure), ClosureHarness(failure=failure) as h:
                self.ready(h); h.close_service()
                self.assertEqual(self.counts(h), (1, 1, 0, 0, 0)); self.stable_unknown(h)

    def test_unmounted_reply_with_nonzero_worker_exit_does_not_finish(self):
        with ClosureHarness(failure='stop_exit') as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.volume.worker.poll(), 2)
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0)); self.stable_unknown(h)

    def test_surviving_pid_or_nested_cgroup_after_stop_prevents_finish(self):
        for failure in ('finish_members', 'finish_nested'):
            with self.subTest(failure=failure), ClosureHarness(failure=failure) as h:
                self.ready(h); h.close_service()
                self.assertEqual(self.counts(h), (1, 1, 0, 0, 0)); self.stable_unknown(h, unmounted=True)

    def test_populated_cgroup_prevents_original_loop_close(self):
        with ClosureHarness(failure='finish_populated') as h:
            self.ready(h); h.close_service()
            self.assertEqual(self.counts(h), (1, 1, 1, 0, 0)); self.stable_unknown(h, unmounted=True)

    def test_host_mount_or_nonempty_original_target_prevents_loop_close(self):
        for failure in ('finish_hostmount', 'finish_target_nonempty'):
            with self.subTest(failure=failure), ClosureHarness(failure=failure) as h:
                self.ready(h); h.close_service()
                self.assertEqual(self.counts(h), (1, 1, 1, 0, 0)); self.stable_unknown(h, unmounted=True)

    def test_loop_close_failure_is_not_retried_or_interpreted_as_detachment(self):
        with ClosureHarness(failure='finish_loop_close') as h:
            self.ready(h); h.close_service()
            self.assertIsNone(h.volume.loop_fd)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 0)); self.stable_unknown(h, unmounted=True)

    def test_global_attachment_blocks_fence_and_lease_without_reclose(self):
        with ClosureHarness(failure='finish_attachment') as h:
            self.ready(h); h.close_service()
            self.assertTrue(h.fence_path.exists()); self.assertTrue(h.scope_path.exists())
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 0))
            h.failure = None  # A later empty inventory is not automatic retry permission.
            self.stable_unknown(h, unmounted=True)

    def test_inventory_failure_is_not_an_empty_global_attachment_inventory(self):
        with ClosureHarness(failure='finish_inventory') as h:
            self.ready(h); h.close_service()
            self.assertTrue(h.fence_path.exists()); self.assertTrue(h.scope_path.exists())
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 0)); self.stable_unknown(h, unmounted=True)

    def test_cgroup_remove_failure_cannot_remove_fence_or_release_lease(self):
        with ClosureHarness(failure='finish_scope') as h:
            self.ready(h); h.close_service()
            self.assertNotIn('fence_unlink', h.events); self.assertNotIn('lease_close', h.events)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 0)); self.stable_unknown(h, unmounted=True)

    def test_fence_changed_after_cgroup_removal_is_preserved(self):
        with ClosureHarness(failure='finish_fence') as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.fence_path.read_bytes(), b'fixture changed fence')
            self.assertNotIn('fence_unlink', h.events); self.assertNotIn('lease_close', h.events)
            self.stable_unknown(h, unmounted=True)

    def test_parent_fsync_failure_retains_lease_and_does_not_recreate_fence(self):
        with ClosureHarness(failure='finish_fsync') as h:
            self.ready(h); h.close_service()
            self.assertFalse(h.fence_path.exists()); self.assertFalse(h.volume.lease.closed)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 0)); self.stable_unknown(h, unmounted=True)

    def test_lease_close_uncertainty_never_reports_outer_closed(self):
        with ClosureHarness(failure='finish_lease') as h:
            self.ready(h); h.close_service()
            self.assertTrue(h.volume.lease.closed)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1)); self.stable_unknown(h, unmounted=True)

    def test_tail_stream_close_failure_retains_proof_even_after_generic_closed_stage(self):
        with ClosureHarness(failure='finish_stream_close') as h:
            self.ready(h); h.close_service()
            self.assertEqual(h.volume.stage, 'CLOSED')
            self.assertTrue(h.volume.lease.closed)
            self.assertIsNone(h.volume._service_child.closure.finish_reply)
            self.assertEqual(self.counts(h), (1, 1, 1, 1, 1)); self.stable_unknown(h, unmounted=True)

    def test_closed_observation_needs_no_running_worker_live_lease_or_generic_owned(self):
        with ClosureHarness() as h:
            self.ready(h); h.close_service(); before = self.counts(h)
            with patch.object(h.volume, '_owned', side_effect=AssertionError('already retired')), \
                    patch.object(h.volume, 'stop', side_effect=AssertionError('no STOP replay')), \
                    patch.object(h.volume, 'finish', side_effect=AssertionError('no finish replay')):
                for operation in (h.observe, h.close_service, h.observe):
                    self.assertEqual(operation()['volumeClosure']['state'], 'CLOSED')
                self.assertEqual(g.check_service_owner(h.volume)['state'], 'CLOSED')
            self.assertEqual(self.counts(h), before)

    def test_detached_closed_snapshot_cannot_mutate_original_proof(self):
        with ClosureHarness() as h:
            self.ready(h); value = h.close_service()
            value['volumeClosure']['state'] = 'UNKNOWN'
            value['owner']['close']['physicalStoresClosed'] = 0
            self.assertEqual(h.observe()['volumeClosure']['state'], 'CLOSED')
            self.assertEqual(h.observe()['owner']['close']['physicalStoresClosed'], 3)

    def test_caller_struct_or_boolean_flags_cannot_replace_typed_closure_receipt(self):
        with ClosureHarness() as h:
            child = self.child_done(h)
            child.closure = SimpleNamespace(state='CLOSED', volumeUnmounted=True,
                fenceRemovedAfterCleanup=True, imageLeaseReleased=True)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'closure_custody_changed'):
                g.check_service_owner(h.volume)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'successful_stop_required'):
                h.volume.finish()
            self.assertEqual(self.counts(h), (0, 0, 0, 0, 0))

    def test_changed_stop_receipt_cannot_authorize_finish(self):
        with ClosureHarness() as h:
            child = self.child_done(h); h.volume.stop()
            child.closure.stop_reply = g._bytes({'state': 'UNMOUNTED', 'pid': h.volume.worker.pid,
                                                'token': 'foreign'})
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'stop_receipt'):
                g.check_service_owner(h.volume)
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'volume_finish_unknown'):
                h.volume.finish()
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0))

    def test_closed_requires_returned_finish_receipt_and_original_stage(self):
        with ClosureHarness() as h:
            child = self.child_done(h); h.volume.stop()
            child.closure.state = 'CLOSED'
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'closed_unconfirmed'):
                g.check_service_owner(h.volume)
            self.assertEqual(self.counts(h), (1, 1, 0, 0, 0))

    def test_post_closed_custody_change_is_rejected_without_cleanup_replay(self):
        with ClosureHarness() as h:
            child = self.ready(h); h.close_service(); before = self.counts(h)
            h.volume.lease = Mock()
            with self.assertRaisesRegex(g.SupervisedServiceRejected, 'owner_changed'):
                g.check_service_owner(h.volume)
            self.assertEqual(h.observe()['volumeClosure']['state'], 'UNKNOWN')
            self.assertIsNotNone(child.closure.finish_reply)
            self.assertEqual(self.counts(h), before)


if __name__ == '__main__':
    unittest.main()
