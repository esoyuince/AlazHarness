"""Original service closure through the production private Unix endpoint.

Real Unix sockets, SO_PEERCRED, request EOF and fixture child Popen/pipes are
used. ClosureHarness runs the original stop/finish methods against explicit
kernel/mount/loop/lease doubles. These are source tests, not installed native,
kernel-confinement or model acceptance. Test teardown owns only its fixtures.
"""
from __future__ import annotations

import copy
import json
import os
import socket
import sys
import threading
import unittest
from unittest.mock import patch

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import service_control_server as server
import test_service_control_server_r163a1 as previous
from service_closure_fixtures_r164a1 import ClosureHarness

UNIX = sys.platform == 'linux' and hasattr(socket, 'SO_PEERCRED')
RID, SECOND, THIRD = previous.RID, previous.SECOND, previous.THIRD


def closure(state='NOT_STARTED', *, unmounted=False, fence=False, lease=False):
    return {'state': state, 'volumeUnmounted': unmounted,
            'fenceRemovedAfterCleanup': fence, 'imageLeaseReleased': lease}


class VolumeSnapshotTests(unittest.TestCase):
    def test_exact_fields_and_detached_result(self):
        value = closure()
        result = server._volume_closure(value)
        self.assertEqual(result, value)
        result['state'] = 'UNKNOWN'
        self.assertEqual(value['state'], 'NOT_STARTED')
        variants = [{**value, 'permission': True}, None, [], 'CLOSED']
        for name in value:
            changed = dict(value); del changed[name]; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(server.ServiceControlServerRejected):
                server._volume_closure(changed)

    def test_flags_are_exact_booleans_and_states_are_fixed(self):
        for name in server._VOLUME_FLAGS:
            for changed in (0, 1, None, 'true'):
                with self.subTest(name=name, changed=changed), self.assertRaises(server.ServiceControlServerRejected):
                    server._volume_closure({**closure(), name: changed})
        for state in ('COMPLETED', '', True, 1, None):
            with self.subTest(state=state), self.assertRaises(server.ServiceControlServerRejected):
                server._volume_closure(closure(state))

    def test_closed_requires_every_ordered_volume_proof(self):
        self.assertEqual(server._volume_closure(closure('CLOSED', unmounted=True, fence=True, lease=True))['state'],
                         'CLOSED')
        for name in server._VOLUME_FLAGS:
            changed = closure('CLOSED', unmounted=True, fence=True, lease=True)
            changed[name] = False
            with self.subTest(name=name), self.assertRaises(server.ServiceControlServerRejected):
                server._volume_closure(changed)

    def test_unknown_cannot_claim_image_release_or_reversed_order(self):
        self.assertTrue(server._volume_closure(closure('UNKNOWN', unmounted=True))['volumeUnmounted'])
        for value in (closure('UNKNOWN', fence=True), closure('UNKNOWN', lease=True),
                      closure('UNKNOWN', unmounted=True, fence=True, lease=True),
                      closure('NOT_STARTED', unmounted=True), closure('STOPPING', unmounted=True)):
            with self.subTest(value=value), self.assertRaises(server.ServiceControlServerRejected):
                server._volume_closure(value)


@unittest.skipUnless(UNIX, 'Linux Unix sockets and original peer credentials required')
class ServerClosureTests(unittest.TestCase):
    # Reuse only the earlier socket exchange utilities, not its test methods.
    _close_listeners = previous.ServerTests._close_listeners
    make = previous.ServerTests.make
    body = previous.ServerTests.body
    exchange = previous.ServerTests.exchange
    start = previous.ServerTests.start

    def setUp(self):
        self.harness = ClosureHarness()
        self.harness.__enter__()
        self.instances = []
        self.addCleanup(self.harness.__exit__, None, None, None)
        self.addCleanup(self._close_listeners)

    def counts(self):
        h = self.harness
        return (h.stop_writes, h.stop_calls, h.finish_calls, h.loop_closes, h.lease_closes)

    def close(self, instance):
        reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(reply['state'], 'CLOSED')
        self.assertIsNone(reply['error'])
        self.assertIsNone(reply['endpoint'])
        self.assertIsNone(reply['endpointScope'])
        self.assertEqual(reply['completion']['physicalStoresClosed'], 3)
        self.assertTrue(all(reply['completion'][name] for name in server._COMPLETION_FLAGS))
        return reply

    def test_full_original_close_reports_closed_and_retains_original_objects(self):
        instance = self.make()
        before = instance.connection()
        self.start(instance)
        original = self.harness.volume._service_child
        process, channel = original.process, original.channel
        reply = self.close(instance)
        self.assertEqual(self.harness.volume.stage, 'CLOSED')
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))
        self.assertIs(self.harness.volume._service_child, original)
        self.assertIs(original.process, process)
        self.assertIs(original.channel, channel)
        self.assertIs(channel.process, process)
        self.assertEqual(instance.connection(), before)
        self.assertEqual(reply['owner'], before['owner'])
        self.assertEqual([line.get('action') for line in self.harness.lines()], [None, 'close'])
        self.assertIs(type(instance._terminal_view), bytes)
        self.assertIs(instance._terminal_child, original)

    def test_post_closed_observation_avoids_live_volume_and_cleanup_methods(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        counts = self.counts()
        with patch.object(self.harness.volume, '_owned', side_effect=AssertionError('retired live-volume gate')), \
             patch.object(self.harness.volume, 'observe_service', side_effect=AssertionError('sealed view available')), \
             patch.object(self.harness.volume, 'close_service', side_effect=AssertionError('no close replay')), \
             patch.object(self.harness.volume, 'stop', side_effect=AssertionError('no stop replay')), \
             patch.object(self.harness.volume, 'finish', side_effect=AssertionError('no finish replay')):
            for command, request_id in (('status', THIRD), ('close', SECOND), ('close', THIRD), ('start', RID)):
                reply, diagnostic, _ = self.exchange(instance, self.body(instance, command, request_id))
                self.assertEqual(reply['state'], 'CLOSED')
                self.assertIsNone(reply['error'])
                self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(self.counts(), counts)

    def test_lost_final_reply_recovers_sealed_closed_without_cleanup_replay(self):
        instance = self.make()
        self.start(instance)
        with patch.object(instance, '_write', side_effect=BrokenPipeError('PRIVATE_FINAL_REPLY')):
            reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertTrue(diagnostic['requestDispatched'])
        self.assertEqual(instance._view['state'], 'UNKNOWN')
        sealed = instance._terminal_view
        self.assertIs(type(sealed), bytes)
        counts = self.counts()
        with patch.object(self.harness.volume, 'close_service', side_effect=AssertionError('no retry')):
            observed, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
            replay, _, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
        self.assertEqual(observed['state'], 'CLOSED')
        self.assertEqual(replay['state'], 'CLOSED')
        self.assertEqual(instance._terminal_view, sealed)
        self.assertEqual(self.counts(), counts)
        self.assertNotIn('PRIVATE_FINAL_REPLY', json.dumps(diagnostic))
        self.assertNotIn(self.harness.volume.token, json.dumps(diagnostic))

    def test_post_cleanup_snapshot_failure_recovers_from_original_typed_receipt(self):
        instance = self.make()
        self.start(instance)
        with patch.object(instance, '_snapshot', side_effect=RuntimeError('PRIVATE_SNAPSHOT')):
            reply, _, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
        self.assertEqual(reply['state'], 'UNKNOWN')
        self.assertEqual(self.harness.volume.stage, 'CLOSED')
        self.assertIsNone(instance._terminal_view)
        counts = self.counts()
        with patch.object(self.harness.volume, 'close_service', side_effect=AssertionError('no retry')):
            observed, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
        self.assertEqual(observed['state'], 'CLOSED')
        self.assertIs(type(instance._terminal_view), bytes)
        self.assertEqual(self.counts(), counts)

    def test_post_cleanup_reply_exception_retains_dispatch_and_sealed_result(self):
        instance = self.make()
        self.start(instance)
        with patch.object(instance, '_reply', side_effect=RuntimeError('PRIVATE_POST_CLOSE')):
            reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertTrue(instance._mutations[SECOND]['dispatched'])
        self.assertIs(type(instance._terminal_view), bytes)
        observed, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
        self.assertEqual(observed['state'], 'CLOSED')
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_reply_snapshot_is_detached_from_sealed_terminal_result(self):
        instance = self.make()
        self.start(instance)
        reply = self.close(instance)
        reply['completion']['imageLeaseReleased'] = False
        reply['owner']['token'] = 'f' * 32
        observed, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
        self.assertTrue(observed['completion']['imageLeaseReleased'])
        self.assertEqual(observed['owner']['token'], self.harness.volume.token)
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_child_completion_status_and_same_start_id_do_not_initiate_volume_close(self):
        instance = self.make()
        self.start(instance)
        child = self.harness.volume._service_child
        child.channel.command('close', timeout=2)
        with patch.object(self.harness.volume, 'stop', side_effect=AssertionError('readonly stop')), \
             patch.object(self.harness.volume, 'finish', side_effect=AssertionError('readonly finish')):
            for action, request_id in (('status', THIRD), ('start', RID)):
                reply, _, _ = self.exchange(instance, self.body(instance, action, request_id))
                self.assertEqual(reply['state'], 'DRAINING')
                self.assertTrue(reply['completion']['childExited'])
                self.assertFalse(reply['completion']['volumeUnmounted'])
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))
        self.close(instance)  # A fresh explicit close may begin the first volume closure.
        self.assertEqual(child.channel.sequence, 1)
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_claimed_volume_completion_must_match_original_retained_receipt(self):
        instance = self.make()
        self.start(instance)
        child = self.harness.volume._service_child
        child.channel.command('close', timeout=2)
        observed = self.harness.observe()
        self.assertEqual(observed['state'], 'COMPLETED')
        for claimed in (closure('CLOSED', unmounted=True, fence=True, lease=True),
                        closure('STOPPED', unmounted=True), closure('UNKNOWN', unmounted=True)):
            value = {**copy.deepcopy(observed), 'volumeClosure': claimed}
            with patch.object(self.harness.volume, 'observe_service', return_value=value):
                reply, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
            self.assertEqual(reply['state'], 'UNKNOWN')
            self.assertFalse(reply['completion']['imageLeaseReleased'])
        self.assertIsNone(instance._terminal_view)
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))

    def test_closed_stage_label_without_typed_completion_cannot_unlock_endpoint(self):
        instance = self.make()
        self.start(instance)
        sealed = instance._terminal_view
        with patch.object(self.harness.volume, 'stage', 'CLOSED'):
            with self.assertRaises(server.ServiceControlServerRejected):
                instance.serve_one(timeout=0)
        self.assertIs(instance._terminal_view, sealed)
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))

    def test_unknown_child_start_identity_remains_observable_without_second_launch(self):
        instance = self.make()
        original_start = self.harness._start
        def missing_child_start(pid):
            if pid not in (os.getpid(), self.harness.volume.worker.pid):
                raise OSError('fixture child start identity unavailable')
            return original_start(pid)
        with patch.object(server.launch.projection, 'process_start', side_effect=missing_child_start):
            started, diagnostic, _ = self.exchange(instance, self.body(instance))
        original = self.harness.volume._service_child
        self.assertEqual(started['state'], 'UNKNOWN')
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertIsNotNone(original.process)
        self.assertIsNone(original.start_ticks)
        self.assertIsNone(original.channel)
        self.assertIsNone(original.process.poll())
        for command, request_id in (('status', THIRD), ('start', RID), ('close', SECOND)):
            observed, diagnostic, _ = self.exchange(instance, self.body(instance, command, request_id))
            self.assertEqual(diagnostic['state'], 'REPLIED')
            self.assertEqual(observed['state'], 'UNKNOWN')
            self.assertFalse(observed['completion']['childExited'])
            self.assertFalse(observed['completion']['imageLeaseReleased'])
        refused, _, _ = self.exchange(instance, self.body(instance, 'start', THIRD))
        self.assertEqual(refused['error'], 'service_server_start_already_attempted')
        self.assertIs(self.harness.volume._service_child, original)
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(self.harness.lines(), [])
        self.assertEqual(self.counts(), (0, 0, 0, 0, 0))
        self.assertIsNone(instance._terminal_view)

    def test_terminal_child_slot_replacement_is_refused_before_request(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        sealed = instance._terminal_view
        original = self.harness.volume._service_child
        with patch.object(self.harness.volume, '_service_child', object()):
            with self.assertRaises(server.ServiceControlServerRejected):
                instance.serve_one(timeout=0)
        self.assertIs(self.harness.volume._service_child, original)
        self.assertEqual(instance._terminal_view, sealed)
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_stale_owner_and_service_after_closed_never_dispatch(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        counts = self.counts()
        for action in ('status', 'close', 'start'):
            for field, value in (('pid', os.getpid() + 1), ('startTicks', self.harness.controller_ticks + 1),
                                 ('token', 'f' * 32)):
                body = self.body(instance, action, THIRD)
                body['expectedOwner'][field] = value
                reply, diagnostic, _ = self.exchange(instance, body)
                self.assertIsNone(reply)
                self.assertEqual(diagnostic['state'], 'REFUSED')
                self.assertFalse(diagnostic['requestDispatched'])
            reply, diagnostic, _ = self.exchange(instance,
                self.body(instance, action, THIRD, serviceId='f' * 32))
            self.assertIsNone(reply)
            self.assertFalse(diagnostic['requestDispatched'])
        self.assertEqual(self.counts(), counts)

    def test_post_closed_socket_replacement_is_not_adopted(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        sealed = instance._terminal_view
        instance._path.rename(self.harness.path / 'original-closed.sock')
        foreign = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(foreign.close)
        foreign.bind(str(instance._path)); os.chmod(instance._path, 0o600)
        identity = instance._path.stat().st_ino
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        self.assertEqual(instance._terminal_view, sealed)
        self.assertEqual(instance._path.stat().st_ino, identity)
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_post_closed_parent_and_controller_identity_still_gate_observation(self):
        parent = self.harness.path / 'private'
        parent.mkdir(mode=0o700)
        instance = self.make(socket_path=str(parent / 'control.sock'))
        self.start(instance); self.close(instance)
        os.chmod(parent, 0o755)
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        os.chmod(parent, 0o700)
        self.harness.controller_ticks += 1
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        self.harness.controller_ticks -= 1
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))

    def test_wrong_thread_and_reentry_cannot_change_terminal_view_or_marker(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        expected = copy.deepcopy(instance._view)
        sealed = instance._terminal_view
        failures = []
        def other_actor():
            try:
                instance.serve_one(timeout=0)
            except server.ServiceControlServerRejected as exc:
                failures.append(str(exc))
        thread = threading.Thread(target=other_actor)
        thread.start(); thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, ['service_server_original_actor'])
        with patch.object(instance, '_serving', True):
            with self.assertRaisesRegex(server.ServiceControlServerRejected, 'reentrant'):
                instance.serve_one(timeout=0)
        self.assertEqual(instance._view, expected)
        self.assertEqual(instance._terminal_view, sealed)
        self.assertTrue(instance._request_dispatched)

    def test_listener_close_keeps_completed_receipt_and_original_socket(self):
        instance = self.make()
        self.start(instance); self.close(instance)
        sealed = instance._terminal_view
        identity = instance._path.stat().st_ino
        result = instance.close_listener()
        self.assertEqual(result, {'state': 'LISTENER_CLOSED', 'ownerRetained': True,
                                  'volumeCleanupStarted': False})
        self.assertEqual(instance._terminal_view, sealed)
        self.assertEqual(instance._path.stat().st_ino, identity)
        self.assertIs(self.harness.volume._service_control_server, instance)
        self.assertEqual(self.counts(), (1, 1, 1, 1, 1))


@unittest.skipUnless(UNIX, 'Linux Unix sockets and original peer credentials required')
class ServerClosureFailureTests(unittest.TestCase):
    _close_listeners = previous.ServerTests._close_listeners
    make = previous.ServerTests.make
    body = previous.ServerTests.body
    exchange = previous.ServerTests.exchange
    start = previous.ServerTests.start
    setUp = ServerClosureTests.setUp
    counts = ServerClosureTests.counts

    def test_unknown_stop_reply_and_busy_never_retry_stop_or_report_closed(self):
        for failure in ('stop_lost_reply', 'stop_busy'):
            with self.subTest(failure=failure), ClosureHarness(failure=failure) as h:
                old = self.harness; self.harness = h
                try:
                    instance = self.make()
                    self.start(instance)
                    reply, _, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
                    self.assertEqual(reply['state'], 'UNKNOWN')
                    self.assertTrue(reply['completion']['childExited'])
                    self.assertFalse(reply['completion']['volumeUnmounted'])
                    self.assertFalse(reply['completion']['imageLeaseReleased'])
                    counts = self.counts()
                    for command, request_id in (('status', THIRD), ('close', SECOND), ('close', THIRD)):
                        observed, _, _ = self.exchange(instance, self.body(instance, command, request_id))
                        self.assertEqual(observed['state'], 'UNKNOWN')
                        self.assertFalse(observed['completion']['imageLeaseReleased'])
                    self.assertEqual(self.counts(), counts)
                    self.assertEqual((h.stop_writes, h.finish_calls, h.lease_closes), (1, 0, 0))
                    self.assertIsNone(instance._terminal_view)
                    instance.close_listener()
                finally:
                    self.harness = old

    def test_unknown_finish_preserves_unmount_proof_without_repeating_cleanup(self):
        with ClosureHarness(failure='finish_attachment') as h:
            old = self.harness; self.harness = h
            try:
                instance = self.make()
                self.start(instance)
                reply, _, _ = self.exchange(instance, self.body(instance, 'close', SECOND))
                self.assertEqual(reply['state'], 'UNKNOWN')
                self.assertTrue(reply['completion']['childExited'])
                self.assertTrue(reply['completion']['volumeUnmounted'])
                self.assertFalse(reply['completion']['fenceRemovedAfterCleanup'])
                self.assertFalse(reply['completion']['imageLeaseReleased'])
                counts = self.counts()
                for command, request_id in (('status', THIRD), ('close', SECOND), ('close', THIRD)):
                    observed, _, _ = self.exchange(instance, self.body(instance, command, request_id))
                    self.assertEqual(observed['state'], 'UNKNOWN')
                    self.assertTrue(observed['completion']['volumeUnmounted'])
                    self.assertFalse(observed['completion']['imageLeaseReleased'])
                self.assertEqual(self.counts(), counts)
                self.assertEqual((h.stop_calls, h.finish_calls, h.loop_closes, h.lease_closes), (1, 1, 1, 0))
                self.assertIsNone(instance._terminal_view)
                instance.close_listener()
            finally:
                self.harness = old

if __name__ == '__main__':
    unittest.main()
