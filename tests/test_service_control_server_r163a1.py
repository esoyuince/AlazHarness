"""Production Unix server/parser/cache with explicit privileged fixture bounds.

Sockets, peer credentials, partial writes, EOF, deadlines and child subprocess
pipes are real. Harness uses the original ServiceVolumeSupervisor delegation,
ServiceChannel and typed frozen launch data; kernel/mount/lease/source-trust
ports and native service receipts are doubles. Test teardown terminates only
fixture children. No installed service, native stores, model or volume cleanup
acceptance is claimed. Node-to-server interop is covered in a separate suite.
"""
from contextlib import ExitStack
import copy
import json
import os
from pathlib import Path
import socket
import struct
import sys
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import service_control_server as server
from service_supervisor_fixtures_r163a1 import Harness

SID = 'a' * 32
RID = 'b' * 32
SECOND = 'c' * 32
THIRD = 'd' * 32
OWNER = {'pid': 1234, 'startTicks': 5678, 'token': 'e' * 32}
UNIX = sys.platform == 'linux' and hasattr(socket, 'SO_PEERCRED')


def request(command='start', request_id=RID, *, owner=None, service_id=SID):
    return {'command': command, 'expectedOwner': dict(OWNER if owner is None else owner),
            'protocol': server.PROTOCOL, 'requestId': request_id, 'serviceId': service_id}


def frame(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode('ascii') + b'\n'


class RequestParserTests(unittest.TestCase):
    def test_compact_request_and_permuted_owner_order_match_node_contract(self):
        value = request(owner={'token': OWNER['token'], 'pid': 1234, 'startTicks': 5678})
        decoded = server.decode_request(frame(value))
        self.assertEqual(decoded, value)
        decoded['expectedOwner']['pid'] = 999
        self.assertEqual(value['expectedOwner']['pid'], 1234)

    def test_exact_root_and_owner_schema_rejects_extensions_and_missing_fields(self):
        base = request()
        variants = []
        for key in base:
            value = copy.deepcopy(base); del value[key]; variants.append(value)
        variants.append({**base, 'config': {}})
        for key in OWNER:
            value = copy.deepcopy(base); del value['expectedOwner'][key]; variants.append(value)
        value = copy.deepcopy(base); value['expectedOwner']['uid'] = 0; variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(server.ServiceControlServerRejected):
                server.decode_request(frame(value))

    def test_identity_numbers_are_exact_bounded_safe_integers(self):
        for field, values in (('pid', (True, False, 0, -1, 1.0, 2**31, '1234')),
                              ('startTicks', (True, 0, -1, 1.0, 2**53, '5678'))):
            for value in values:
                body = request(); body['expectedOwner'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(server.ServiceControlServerRejected):
                    server.decode_request(frame(body))
        body = request(owner={**OWNER, 'pid': 2**31 - 1, 'startTicks': 2**53 - 1})
        self.assertEqual(server.decode_request(frame(body)), body)

    def test_fixed_protocol_action_and_three_ids(self):
        for key, values in (('command', ('drain', 'exec', '', True)),
                            ('protocol', ('other', None)),
                            ('requestId', ('b' * 31, 'B' * 32, True)),
                            ('serviceId', ('a' * 33, '', 2))):
            for value in values:
                body = request(); body[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(server.ServiceControlServerRejected):
                    server.decode_request(frame(body))
        for value in ('e' * 31, 'E' * 32, False):
            body = request(); body['expectedOwner']['token'] = value
            with self.assertRaises(server.ServiceControlServerRejected):
                server.decode_request(frame(body))

    def test_noncompact_duplicate_unicode_and_multiple_frames_refused(self):
        raw = frame(request())
        invalid = [raw[:-1], raw + b'\n', raw + raw, b' ' + raw, raw[:-1] + b'\r\n',
                   raw.replace(b'1234', b'1.234e3'), raw.replace(b'5678', b'NaN'),
                   raw.replace(b'"command":"start"', b'"command":"start","command":"start"'),
                   raw.replace(b'"pid":1234', b'"pid":1234,"pid":1234'),
                   raw.replace(b'"start"', b'"st\\u0061rt"'), b'\xff\n', b'[]\n',
                   b'x' * server.MAX_FRAME + b'\n']
        for index, value in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(server.ServiceControlServerRejected):
                server.decode_request(value)

    def test_foreign_exception_string_is_never_evaluated(self):
        class Foreign(RuntimeError):
            def __str__(self):
                raise AssertionError('must not format foreign exception')
        self.assertEqual(server._reason(Foreign()), 'service_server_unavailable')
        self.assertEqual(server._reason(RuntimeError('private_credential')), 'service_server_unavailable')


@unittest.skipUnless(UNIX, 'Linux Unix sockets and peer credentials required')
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.harness = Harness()
        self.harness.__enter__()
        self.instances = []
        self.addCleanup(self.harness.__exit__, None, None, None)
        self.addCleanup(self._close_listeners)

    def _close_listeners(self):
        for instance in self.instances:
            if instance._listener is not None:
                instance._listener.close()  # test-owned endpoint only

    def make(self, *, bind=True, **options):
        h = self.harness
        arguments = {'socket_path': str(h.path / 'control.sock'), 'scratch': h.scratch,
                     'instance_id': h.instance_id, 'service_id': h.service_id,
                     'request_seconds': .15, 'response_seconds': .15, 'operation_seconds': 2}
        arguments.update(options)
        instance = server.ServiceControlServer(h.volume, h.ipc, h.filesystem, h.record, **arguments)
        self.instances.append(instance)
        if bind:
            instance.bind()
        return instance

    def body(self, instance, command='start', request_id=RID, **patches):
        return {**request(command, request_id, owner=instance.connection()['owner']), **patches}

    def exchange(self, instance, value, *, eof=True, disconnect=False, pieces=None):
        raw = frame(value) if type(value) is dict else value
        observed = {'data': b'', 'error': None}
        def client():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
                    peer.settimeout(3)
                    peer.connect(str(instance._path))
                    for part in (pieces if pieces is not None else (raw,)):
                        peer.sendall(part)
                    if eof:
                        peer.shutdown(socket.SHUT_WR)
                    if disconnect:
                        return
                    while True:
                        part = peer.recv(4096)
                        if not part:
                            return
                        observed['data'] += part
            except OSError as exc:
                observed['error'] = type(exc).__name__
        thread = threading.Thread(target=client, daemon=True)
        thread.start()
        diagnostic = instance.serve_one(timeout=2)
        thread.join(4)
        self.assertFalse(thread.is_alive(), 'fixture client did not terminate')
        response = json.loads(observed['data']) if observed['data'] else None
        if response is not None:
            self.assertLessEqual(len(observed['data']), server.MAX_FRAME)
            self.assertEqual(observed['data'].count(b'\n'), 1)
            self.assertEqual(server._compact(response, sorted_keys=True) + b'\n', observed['data'])
        return response, diagnostic, observed

    def start(self, instance):
        reply, diagnostic, _ = self.exchange(instance, self.body(instance))
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(reply['state'], 'READY')
        self.assertEqual(reply['error'], None)
        return reply

    def test_bind_private_socket_and_original_private_connection_without_launch(self):
        instance = self.make()
        value = instance.connection()
        self.assertEqual(value['owner']['pid'], os.getpid())
        self.assertEqual(value['owner']['startTicks'], self.harness.controller_ticks)
        self.assertEqual(value['owner']['token'], self.harness.volume.token)
        self.assertEqual(value['serviceId'], SID)
        self.assertEqual(os.stat(instance._path).st_mode & 0o777, 0o600)
        self.assertIs(self.harness.volume._service_control_server, instance)
        self.assertIsNone(self.harness.volume._service_child)
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_one_real_child_and_eof_terminated_ready_response(self):
        instance = self.make()
        reply = self.start(instance)
        self.assertEqual(reply['endpointScope'], 'private-service-loopback')
        self.assertTrue(all(not reply['completion'][key] for key in server._COMPLETION_FLAGS))
        self.assertEqual(reply['completion']['physicalStoresClosed'], 0)
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(len(self.harness.lines()), 1)
        self.assertIs(self.harness.volume._service_child.channel.process, self.harness.children[0])

    def test_owner_mismatch_for_every_action_precedes_all_lifecycle_dispatch(self):
        instance = self.make()
        with patch.object(type(self.harness.volume), 'launch_service') as launch_method, \
             patch.object(type(self.harness.volume), 'observe_service') as observe_method, \
             patch.object(type(self.harness.volume), 'close_service') as close_method:
            for command in ('start', 'close', 'status'):
                for field, changed in (('pid', os.getpid() + 1), ('startTicks', 101), ('token', 'f' * 32)):
                    body = self.body(instance, command)
                    body['expectedOwner'][field] = changed
                    reply, diagnostic, _ = self.exchange(instance, body)
                    self.assertIsNone(reply)
                    self.assertEqual(diagnostic['state'], 'REFUSED')
                    self.assertFalse(diagnostic['requestDispatched'])
            launch_method.assert_not_called(); observe_method.assert_not_called(); close_method.assert_not_called()
        self.assertEqual(instance._mutations, {})

    def test_wrong_service_and_malformed_request_have_no_effect(self):
        instance = self.make()
        raw = frame(self.body(instance))
        invalid = [frame(self.body(instance, serviceId='f' * 32)), raw + raw,
                   raw.replace(b'"command":"start"', b'"command":"start","command":"start"'),
                   raw[:-1], b'\xff\n', b'x' * (server.MAX_FRAME + 1)]
        for value in invalid:
            reply, diagnostic, _ = self.exchange(instance, value)
            self.assertIsNone(reply)
            self.assertEqual(diagnostic['state'], 'REFUSED')
        self.assertIsNone(self.harness.volume._service_child)
        self.assertEqual(self.harness.popen.call_count, 0)
        self.assertEqual(instance._mutations, {})

    def test_complete_newline_without_request_eof_never_dispatches(self):
        instance = self.make(request_seconds=.03)
        reply, diagnostic, _ = self.exchange(instance, self.body(instance), eof=False)
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['reason'], 'service_server_connection_timeout')
        self.assertFalse(diagnostic['requestDispatched'])
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_fragmented_request_dispatches_only_after_complete_eof(self):
        instance = self.make()
        raw = frame(self.body(instance))
        reply, diagnostic, _ = self.exchange(instance, raw, pieces=[raw[:3], raw[3:29], raw[29:-1], raw[-1:]])
        self.assertEqual(reply['state'], 'READY')
        self.assertEqual(diagnostic['state'], 'REPLIED')
        self.assertEqual(self.harness.popen.call_count, 1)

    def test_status_same_id_is_read_only_and_does_not_consume_mutation_cache(self):
        instance = self.make()
        before, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(before['state'], 'NEW')
        self.assertEqual(instance._mutations, {})
        self.start(instance)
        original = self.harness.volume._service_child
        with patch.object(original.channel, 'command', side_effect=AssertionError('status must not write')):
            reply, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(reply['state'], 'READY')
        self.assertEqual(len(instance._mutations), 1)
        self.assertEqual(len(self.harness.lines()), 1)
        self.assertIs(self.harness.volume._service_child, original)

    def test_same_start_request_observes_without_a_second_child(self):
        instance = self.make()
        self.start(instance)
        original = self.harness.volume._service_child
        reply, _, _ = self.exchange(instance, self.body(instance))
        self.assertEqual(reply['state'], 'READY')
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(len(self.harness.lines()), 1)
        self.assertIs(self.harness.volume._service_child, original)

    def test_conflicting_request_id_does_not_dispatch_close_or_observe(self):
        instance = self.make()
        self.start(instance)
        with patch.object(type(self.harness.volume), 'close_service') as close_method, \
             patch.object(type(self.harness.volume), 'observe_service') as observe_method:
            reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close'))
            close_method.assert_not_called(); observe_method.assert_not_called()
        self.assertEqual(reply['error'], 'service_server_request_conflict')
        self.assertEqual(reply['state'], 'READY')
        self.assertFalse(diagnostic['requestDispatched'])

    def test_different_start_id_is_retained_refusal_without_second_launch(self):
        instance = self.make()
        self.start(instance)
        reply, diagnostic, _ = self.exchange(instance, self.body(instance, request_id=SECOND))
        self.assertEqual(reply['error'], 'service_server_start_already_attempted')
        self.assertFalse(diagnostic['requestDispatched'])
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(instance._mutations[SECOND]['dispatched'], False)

    def test_capacity_never_evicts_or_reenables_previous_mutations(self):
        instance = self.make(max_mutations=2)
        self.start(instance)
        self.exchange(instance, self.body(instance, request_id=SECOND))
        reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close', THIRD))
        self.assertEqual(reply['error'], 'service_server_request_capacity')
        self.assertFalse(diagnostic['requestDispatched'])
        self.assertEqual(set(instance._mutations), {RID, SECOND})
        self.exchange(instance, self.body(instance))
        observed, _, _ = self.exchange(instance, self.body(instance, 'status', THIRD))
        self.assertEqual(observed['state'], 'READY')
        self.assertEqual(set(instance._mutations), {RID, SECOND})
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(len(self.harness.lines()), 1)

    def test_close_before_start_is_cached_refusal_without_volume_cleanup(self):
        instance = self.make()
        with patch.object(type(self.harness.volume), 'close_service') as close_method:
            reply, diagnostic, _ = self.exchange(instance, self.body(instance, 'close'))
            self.assertEqual(reply['state'], 'NEW')
            self.assertEqual(reply['error'], 'service_server_not_started')
            self.assertFalse(diagnostic['requestDispatched'])
            close_method.assert_not_called()
        self.assertIsNone(self.harness.volume._service_child)

    def test_observing_child_final_exit_and_eof_never_starts_volume_closure(self):
        instance = self.make()
        self.start(instance)
        original = self.harness.volume._service_child
        with patch.object(type(self.harness.volume), 'stop', side_effect=AssertionError('no volume stop')), \
             patch.object(type(self.harness.volume), 'finish', side_effect=AssertionError('no volume finish')):
            # R164 connects explicit close to the volume. Exercise only the
            # existing child's final/exit/EOF observation here; that remains
            # read-only and cannot initiate the new volume closure path.
            original.channel.command('close', timeout=2)
            reply, _, _ = self.exchange(instance, self.body(instance, 'status', SECOND))
            self.assertEqual(reply['state'], 'DRAINING')
            self.assertIsNone(reply['endpoint'])
            done = reply['completion']
            self.assertEqual(done['physicalStoresClosed'], 3)
            self.assertTrue(done['profileLeaseReleased'] and done['childExited'])
            self.assertFalse(done['volumeUnmounted'] or done['imageLeaseReleased'] or done['fenceRemovedAfterCleanup'])
            self.exchange(instance, self.body(instance, 'start', RID))
            self.exchange(instance, self.body(instance, 'status', SECOND))
        self.assertIs(self.harness.volume._service_child, original)
        self.assertEqual([line.get('action') for line in self.harness.lines()], [None, 'close'])
        self.assertEqual(self.harness.volume.stage, 'RUNNING')

    def test_unexpected_snapshot_closed_or_boolean_identity_is_unknown(self):
        instance = self.make()
        self.start(instance)
        observed = self.harness.observe()
        for change in ({'state': 'CLOSED'}, {'pid': True}, {'epoch': True}, {'childStartTicks': True}):
            value = {**copy.deepcopy(observed), **change}
            with patch.object(type(self.harness.volume), 'observe_service', return_value=value):
                reply, _, _ = self.exchange(instance, self.body(instance, 'status'))
            self.assertEqual(reply['state'], 'UNKNOWN')
            self.assertEqual(reply['error'], 'service_server_observation_unknown')
            self.assertFalse(reply['completion']['imageLeaseReleased'])

    def test_lost_response_preserves_same_request_owner_and_child(self):
        instance = self.make()
        with patch.object(instance, '_write', side_effect=BrokenPipeError('PRIVATE_RESPONSE_SECRET')):
            reply, diagnostic, _ = self.exchange(instance, self.body(instance))
        original = self.harness.volume._service_child
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertTrue(diagnostic['requestDispatched'])
        self.assertEqual(instance._view['state'], 'UNKNOWN')
        observed, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(observed['state'], 'READY')
        self.exchange(instance, self.body(instance))
        self.assertIs(self.harness.volume._service_child, original)
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(len(self.harness.lines()), 1)
        self.assertNotIn('PRIVATE_RESPONSE_SECRET', json.dumps(diagnostic))
        self.assertNotIn(self.harness.volume.token, json.dumps(diagnostic))

    def test_actual_client_disconnect_after_complete_request_retains_effect(self):
        instance = self.make()
        self.exchange(instance, self.body(instance), disconnect=True)
        original = self.harness.volume._service_child
        self.assertIsNotNone(original)
        self.assertEqual(self.harness.popen.call_count, 1)
        observed, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(observed['state'], 'READY')
        self.assertIs(self.harness.volume._service_child, original)

    def test_post_mutation_reply_exception_cannot_claim_no_dispatch(self):
        instance = self.make()
        with patch.object(instance, '_reply', side_effect=RuntimeError('PRIVATE_REPLY_SECRET')):
            reply, diagnostic, _ = self.exchange(instance, self.body(instance))
        self.assertIsNone(reply)
        self.assertEqual(self.harness.popen.call_count, 1)
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertTrue(diagnostic['requestDispatched'])
        self.assertEqual(instance._view['state'], 'UNKNOWN')
        self.assertTrue(instance._mutations[RID]['dispatched'])
        self.assertNotIn('PRIVATE_REPLY_SECRET', json.dumps(diagnostic))

    def test_operation_baseexception_keeps_slot_and_sanitizes_diagnostics(self):
        instance = self.make()
        original = type(self.harness.volume).launch_service
        class Broken(BaseException):
            def __str__(self):
                raise AssertionError('foreign exception formatted')
        def interrupted(volume, *args, **kwargs):
            original(volume, *args, **kwargs)
            raise Broken()
        with patch.object(type(self.harness.volume), 'launch_service', interrupted):
            reply, diagnostic, _ = self.exchange(instance, self.body(instance))
        child = self.harness.volume._service_child
        self.assertEqual(reply['state'], 'UNKNOWN')
        self.assertEqual(reply['error'], 'service_server_operation_unknown')
        self.assertTrue(diagnostic['requestDispatched'])
        observed, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(observed['state'], 'READY')
        self.assertIs(self.harness.volume._service_child, child)
        self.assertEqual(self.harness.popen.call_count, 1)

    def test_frozen_launch_is_unchanged_by_original_mutable_inputs(self):
        instance = self.make()
        raw = instance._launch
        self.harness.ipc['unexpected'] = 'caller mutation'
        self.harness.filesystem['readonly'] = []
        self.start(instance)
        self.assertEqual(instance._launch, raw)
        self.assertEqual(self.harness.popen.call_count, 1)

    def test_status_does_not_complete_partial_child_input_after_timeout(self):
        instance = self.make()
        self.start(instance)
        channel = self.harness.volume._service_child.channel
        channel.phase = 'UNKNOWN'
        channel.pending = {'type': 'reply', 'sequence': 1, 'requestId': 'f' * 32, 'action': 'close'}
        channel.input_bytes = b'partially transmitted fixture'
        channel.input_written = 3
        with patch.object(channel, 'command', side_effect=AssertionError('must not issue command')), \
             patch('supervised_service_channel.os.write', side_effect=AssertionError('must not finish input')):
            reply, _, _ = self.exchange(instance, self.body(instance, 'status'))
        self.assertEqual(reply['state'], 'UNKNOWN')
        self.assertEqual(channel.input_written, 3)
        self.assertEqual(len(self.harness.lines()), 1)

    def test_existing_regular_file_and_stale_socket_are_never_removed(self):
        instance = self.make(bind=False)
        instance._path.write_bytes(b'foreign fixture')
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'existing_socket_path'):
            instance.bind()
        self.assertEqual(instance._path.read_bytes(), b'foreign fixture')
        instance._path.unlink()  # fixture only: product never removes it
        foreign = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        foreign.bind(str(instance._path)); foreign.close()
        identity = instance._path.stat().st_ino
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'existing_socket_path'):
            instance.bind()
        self.assertEqual(instance._path.stat().st_ino, identity)
        self.assertFalse(instance._bind_attempted)

    def test_symlink_and_nonprivate_parent_are_refused(self):
        parent = self.harness.path / 'parent'
        parent.mkdir(mode=0o700)
        link = self.harness.path / 'alias'
        link.symlink_to(parent, target_is_directory=True)
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'parent_path'):
            self.make(socket_path=str(link / 'control.sock'))
        os.chmod(parent, 0o755)
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'private_parent'):
            self.make(socket_path=str(parent / 'control.sock'))

    def test_replaced_socket_is_refused_and_close_listener_does_not_unlink_it(self):
        instance = self.make()
        instance._path.rename(self.harness.path / 'original.sock')
        foreign = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(foreign.close)
        foreign.bind(str(instance._path)); os.chmod(instance._path, 0o600)
        identity = instance._path.stat().st_ino
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        result = instance.close_listener()
        self.assertTrue(result['ownerRetained'])
        self.assertFalse(result['volumeCleanupStarted'])
        self.assertEqual(instance._path.stat().st_ino, identity)
        self.assertIs(self.harness.volume._service_control_server, instance)

    def test_changed_parent_permissions_or_identity_refuse_endpoint(self):
        parent = self.harness.path / 'private'
        parent.mkdir(mode=0o700)
        instance = self.make(socket_path=str(parent / 'control.sock'))
        os.chmod(parent, 0o755)
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        os.chmod(parent, 0o700)
        parent.rename(self.harness.path / 'old-private')
        parent.mkdir(mode=0o700)
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_uncertain_bind_retains_original_descriptor_and_never_retries(self):
        instance = self.make(bind=False)
        with patch.object(server.os, 'chmod', side_effect=OSError('PRIVATE_BIND_SECRET')):
            with self.assertRaisesRegex(server.ServiceControlServerRejected, '^service_server_bind_unknown$'):
                instance.bind()
        self.assertIsNotNone(instance._listener)
        self.assertGreaterEqual(instance._listener.fileno(), 0)
        self.assertTrue(instance._path.exists())
        self.assertIs(self.harness.volume._service_control_server, instance)
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'bind_once'):
            instance.bind()
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_second_server_on_original_volume_is_rejected(self):
        instance = self.make()
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'already_owned'):
            self.make(socket_path=str(self.harness.path / 'second.sock'))
        self.assertIs(self.harness.volume._service_control_server, instance)
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'bind_once'):
            instance.bind()

    def test_actor_and_volume_token_and_start_ticks_rechecked(self):
        instance = self.make()
        for field, changed in (('token', 'f' * 32), ('who', (os.getpid() + 1, threading.get_ident()))):
            with patch.object(self.harness.volume, field, changed):
                with self.assertRaises(server.ServiceControlServerRejected):
                    instance.serve_one(timeout=0)
        self.harness.controller_ticks += 1
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        self.harness.controller_ticks -= 1
        failures = []
        def wrong_thread():
            try:
                instance.serve_one(timeout=0)
            except server.ServiceControlServerRejected as exc:
                failures.append(str(exc))
        thread = threading.Thread(target=wrong_thread); thread.start(); thread.join(2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_wrong_thread_cannot_reset_active_dispatch_or_change_ready_view(self):
        instance = self.make()
        self.start(instance)
        original = self.harness.volume._service_child
        expected = copy.deepcopy(instance._view)
        self.assertTrue(instance._request_dispatched)
        failures = []
        def wrong_thread():
            for call in (lambda: instance.serve_one(timeout=0), instance.serve_forever):
                try:
                    call()
                except server.ServiceControlServerRejected as exc:
                    failures.append(str(exc))
        with patch.object(type(self.harness.volume), 'observe_service') as observe, \
             patch.object(type(self.harness.volume), 'launch_service') as launch_method, \
             patch.object(type(self.harness.volume), 'close_service') as close:
            thread = threading.Thread(target=wrong_thread, daemon=True)
            thread.start(); thread.join(2)
            self.assertFalse(thread.is_alive())
            observe.assert_not_called(); launch_method.assert_not_called(); close.assert_not_called()
        self.assertEqual(failures, ['service_server_original_actor'] * 2)
        self.assertTrue(instance._request_dispatched)
        self.assertEqual(instance._view, expected)
        self.assertIs(self.harness.volume._service_child, original)

    def test_reentrant_main_thread_cannot_reset_mutation_dispatch_marker(self):
        instance = self.make()
        original = type(self.harness.volume).launch_service
        refused = []
        def during_launch(volume, *args, **kwargs):
            self.assertTrue(instance._request_dispatched)
            for call in (lambda: instance.serve_one(timeout=0), instance.serve_forever):
                try:
                    call()
                except server.ServiceControlServerRejected as exc:
                    refused.append(str(exc))
            self.assertTrue(instance._request_dispatched)
            return original(volume, *args, **kwargs)
        with patch.object(type(self.harness.volume), 'launch_service', during_launch), \
             patch.object(instance, '_reply', side_effect=RuntimeError('fixture post-dispatch failure')):
            _, diagnostic, _ = self.exchange(instance, self.body(instance))
        self.assertEqual(refused, ['service_server_reentrant_request'] * 2)
        self.assertTrue(diagnostic['requestDispatched'])
        self.assertEqual(diagnostic['state'], 'REPLY_LOST')
        self.assertEqual(instance._view['state'], 'UNKNOWN')
        self.assertFalse(instance._serving)
        self.assertEqual(self.harness.popen.call_count, 1)

    def test_peer_credentials_must_match_original_host_actor(self):
        instance = self.make()
        class Peer:
            def __init__(self, credentials):
                self.credentials = credentials
            def getsockopt(self, level, option, size):
                self.args = level, option, size
                return struct.pack('3i', *self.credentials)
        for credentials in ((0, instance._uid, instance._gid),
                            (123, instance._uid + 1, instance._gid),
                            (123, instance._uid, instance._gid + 1)):
            with self.assertRaises(server.ServiceControlServerRejected):
                instance._peer(Peer(credentials))
        peer = Peer((123, instance._uid, instance._gid))
        instance._peer(peer)
        self.assertEqual(peer.args, (socket.SOL_SOCKET, socket.SO_PEERCRED, 12))

    def test_peer_refusal_happens_before_read_or_dispatch(self):
        instance = self.make()
        with patch.object(instance, '_peer', side_effect=server.ServiceControlServerRejected('service_server_peer_identity')), \
             patch.object(instance, '_read') as read:
            reply, diagnostic, _ = self.exchange(instance, self.body(instance))
            read.assert_not_called()
        self.assertIsNone(reply)
        self.assertEqual(diagnostic['state'], 'REFUSED')
        self.assertFalse(diagnostic['requestDispatched'])
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_bound_socket_mode_drift_is_not_adopted(self):
        instance = self.make()
        os.chmod(instance._path, 0o666)
        with self.assertRaises(server.ServiceControlServerRejected):
            instance.serve_one(timeout=0)
        self.assertEqual(self.harness.popen.call_count, 0)

    def test_nonblocking_accept_and_timeout_limits_are_explicit(self):
        for key in ('request_seconds', 'response_seconds', 'operation_seconds'):
            for value in (0, -1, 61, True, float('nan'), float('inf')):
                with self.subTest(key=key, value=value), self.assertRaises(server.ServiceControlServerRejected):
                    self.make(**{key: value})
        for value in (0, 65, True, 1.0):
            with self.assertRaises(server.ServiceControlServerRejected):
                self.make(max_mutations=value)
        instance = self.make()
        self.assertEqual(instance.serve_one(timeout=0)['state'], 'IDLE')
        for value in (-1, 61, True, float('nan'), float('inf')):
            with self.assertRaises(server.ServiceControlServerRejected):
                instance.serve_one(timeout=value)

    def test_absolute_canonical_short_socket_path_is_required(self):
        for value in ('relative.sock', '/tmp/../control.sock', '//tmp/control.sock',
                      '/tmp/control\n.sock', '/tmp/' + 'x' * 104):
            with self.subTest(value=value), self.assertRaises(server.ServiceControlServerRejected):
                self.make(socket_path=value)

    def test_socket_backpressure_has_one_bounded_write_deadline(self):
        instance = self.make(response_seconds=.03)
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(left.close); self.addCleanup(right.close)
        left.setblocking(False)
        while True:
            try:
                left.send(b'x' * 16384)
            except BlockingIOError:
                break
        with self.assertRaisesRegex(server.ServiceControlServerRejected, 'connection_timeout'):
            instance._write(left, {'test': 'bounded transport fixture'})

    def test_listener_close_retains_live_child_and_existing_path_without_cleanup(self):
        instance = self.make()
        self.start(instance)
        child = self.harness.volume._service_child
        with patch.object(type(self.harness.volume), 'stop') as stop, \
             patch.object(type(self.harness.volume), 'finish') as finish:
            result = instance.close_listener()
            stop.assert_not_called(); finish.assert_not_called()
        self.assertEqual(result['state'], 'LISTENER_CLOSED')
        self.assertTrue(instance._path.exists())
        self.assertIs(self.harness.volume._service_child, child)
        self.assertIsNone(child.process.poll())
        self.assertIs(self.harness.volume._service_control_server, instance)


if __name__ == '__main__':
    unittest.main()
