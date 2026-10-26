"""Owned contract/state tests; no root, WSL, mount, UID change or native code."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/qa/r155a1_linux_accept.py'
SPEC = importlib.util.spec_from_file_location('_r155_caller_owned_tests', SOURCE)
caller = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = caller
SPEC.loader.exec_module(caller)


def fixture():
    """Synthetic handoff double: never an acceptance record or kernel evidence."""
    context = {'pid': 123, 'parentPid': 100, 'startTicks': 456, 'namespaceInode': 789,
               'loopNumber': 9, 'profileIdentity': [1801, 20],
               'databaseIdentities': [[1801, 21], [1801, 22], [1801, 23]]}
    wire = '{"owned-test-double":true}'
    value = {'kind': 'R155A1_TASK_FREE_RETAINED_SEED', 'result': 'PASS',
        'state': 'RETAINED_SEED_CREATED', 'phase': 'COMPLETE', 'home': str(caller.PROFILE),
        'pid': 123, 'parentPid': 100, 'startTicks': 456, 'gatewayUid': 23001,
        'socketGroupGid': 23003, 'supplementaryGroups': [], 'resUid': [23001] * 3,
        'resGid': [23003] * 3, 'mountNamespaceInode': 789, 'mountNamespace': 'mnt:[789]',
        'profileIdentity': [1801, 20], 'databaseIdentities': deepcopy(context['databaseIdentities']),
        'mount': {'mount_id': 10, 'device': [7, 9], 'root': '/',
                  'mount_point': str(caller.MOUNT), 'filesystem': 'ext4'},
        'handoff': wire, 'handoffSha256': caller.digest(wire.encode()), 'previousEpoch': 1,
        'instanceId': caller.SEED_INSTANCE, 'ownerState': 'CLOSED', 'consumerState': 'DETACHED',
        'allThreeConnectionsPhysicallyClosed': True, 'profileLeaseReleasedNormally': True,
        'retainedCapturedWhileLeaseHeld': True, 'normalLoopShutdown': True,
        'outstandingAsyncTasks': 0, 'outstandingThreads': 0, 'completedChecks': list(caller.CHECKS),
        'coldHelperCalls': [{'phase': 'START_OWNER', 'script': name}
                           for name in ('run_store_preopen.py', 'run_response_preopen.py')],
        'sqliteOpenCount': 6, 'qualifiedNativeSourceCount': 500,
        'auxiliaryInitialization': {'sourceDerivedCacheEntries': 75,
            'sourceDerivedCacheSha256': 'a' * 64, 'completeToolRegistrationPerformed': False,
            'blockedIpv6CapabilityProbe': {'count': 1, 'socketClosed': True, 'bindPerformed': False},
            'activeSessionEntries': 0},
        'executedTasks': 0, 'realModelCalls': 0, 'listenersCreated': 0, 'apiAdmissionPublished': False,
        'installationReceiptSha256': caller.RECEIPT_SHA, 'harnessCommit': caller.HARNESS,
        'nativeFeature': caller.NATIVE, 'verificationMillis': 1000, 'nativeMillis': 2000,
        'totalMillis': 3000, 'projectedReadinessAccepted': False, 'fullD3BAccepted': False,
        'automaticCleanup': False, 'automaticRetry': False}
    record = SimpleNamespace(state=SimpleNamespace(epoch=1, instance_id=caller.SEED_INSTANCE),
        retained=SimpleNamespace(home_identity=(1801, 20),
            database_identities=tuple(tuple(x) for x in context['databaseIdentities']),
            discovery_sha256='a' * 64))
    handoff = SimpleNamespace(decode=Mock(return_value=record))
    return value, context, handoff


class SeedContractTests(unittest.TestCase):
    def validate(self, value, context=None, handoff=None):
        _, default_context, default_handoff = fixture()
        return caller.validate_seed(caller.canonical(value), context or default_context,
                                    handoff or default_handoff)

    def test_valid_contract_uses_fixed_expected_home(self):
        value, context, handoff = fixture()
        result, record = self.validate(value, context, handoff)
        self.assertEqual(value, result)
        self.assertIs(record, handoff.decode.return_value)
        handoff.decode.assert_called_once_with(value['handoff'].encode('ascii'),
                                               expected_home=str(caller.PROFILE))

    def test_every_success_field_is_required(self):
        for name in caller.SEED_FIELDS:
            with self.subTest(name=name):
                value, _, _ = fixture()
                del value[name]
                with self.assertRaises(caller.AcceptanceRejected):
                    self.validate(value)

    def test_capability_probe_requires_exact_block_and_physical_socket_close(self):
        for key, bad in (('count', True), ('count', 0), ('count', 2),
                         ('socketClosed', False), ('bindPerformed', True)):
            value, _, _ = fixture()
            value['auxiliaryInitialization']['blockedIpv6CapabilityProbe'][key] = bad
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value)

    def test_unexpected_claim_is_rejected(self):
        value, _, _ = fixture()
        value['kernelAccepted'] = True
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)

    def test_pid_parent_generation_and_namespace_cannot_be_rebound(self):
        mutations = {'pid': 124, 'parentPid': 101, 'startTicks': 455,
            'mountNamespaceInode': 790, 'mountNamespace': 'mnt:[790]',
            'previousEpoch': 2, 'instanceId': 'other', 'home': '/tmp/other',
            'installationReceiptSha256': 'b' * 64, 'nativeFeature': 'b' * 40}
        for name, bad in mutations.items():
            with self.subTest(name=name):
                value, _, _ = fixture()
                value[name] = bad
                with self.assertRaises(caller.AcceptanceRejected):
                    self.validate(value)

    def test_same_image_requires_exact_dropped_identity_and_empty_groups(self):
        for key, bad in (('supplementaryGroups', [23003]), ('resUid', [0] * 3),
                         ('resGid', [23003, 0, 23003]), ('gatewayUid', 23002)):
            value, _, _ = fixture()
            value[key] = bad
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value)

    def test_bool_is_not_an_integer_proof(self):
        for name in ('pid', 'previousEpoch', 'outstandingAsyncTasks', 'executedTasks',
                     'realModelCalls', 'sqliteOpenCount', 'verificationMillis'):
            value, _, _ = fixture()
            value[name] = True if value[name] else False
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value)

    def test_close_and_scope_claims_must_be_exact(self):
        for name in ('allThreeConnectionsPhysicallyClosed', 'profileLeaseReleasedNormally',
                     'retainedCapturedWhileLeaseHeld', 'normalLoopShutdown',
                     'apiAdmissionPublished', 'projectedReadinessAccepted',
                     'fullD3BAccepted', 'automaticRetry', 'automaticCleanup'):
            value, _, _ = fixture()
            value[name] = not value[name]
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value)

    def test_actual_database_and_profile_identities_must_match(self):
        for name in ('profileIdentity', 'databaseIdentities'):
            value, context, handoff = fixture()
            if name == 'profileIdentity':
                context[name][1] += 1
            else:
                context[name][1][1] += 1
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value, context, handoff)

    def test_actual_mount_loop_and_filesystem_must_match(self):
        for key, bad in (('device', [7, 10]), ('root', '/subtree'),
                         ('mount_point', '/other'), ('filesystem', 'tmpfs')):
            value, _, _ = fixture()
            value['mount'][key] = bad
            with self.assertRaises(caller.AcceptanceRejected):
                self.validate(value)

    def test_unedited_handoff_and_source_cache_identity_required(self):
        value, _, _ = fixture()
        value['handoff'] += ' '
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)
        value, _, _ = fixture()
        value['auxiliaryInitialization']['sourceDerivedCacheSha256'] = 'b' * 64
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)

    def test_six_checks_helper_order_and_scope_are_fixed(self):
        value, _, _ = fixture()
        value['completedChecks'].reverse()
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)
        value, _, _ = fixture()
        value['coldHelperCalls'].reverse()
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)
        value, _, _ = fixture()
        value['auxiliaryInitialization']['completeToolRegistrationPerformed'] = True
        with self.assertRaises(caller.AcceptanceRejected):
            self.validate(value)

    def test_duplicate_noncanonical_multiple_and_oversize_frames_rejected(self):
        raw = caller.canonical(fixture()[0])
        bad = (raw + raw, raw[:-1], b' ' + raw, b'{"x":1,"x":2}\n', b'{"x":NaN}\n',
               b'{"x":1.0}\n', b'\xff\n', b'x' * 32769)
        for data in bad:
            with self.subTest(data=data[:20]):
                with self.assertRaises(caller.AcceptanceRejected):
                    caller.frame(data, 32768)


class OwnedProcessTests(unittest.TestCase):
    def test_any_unresolved_seed_blocks_readiness_and_normal_close(self):
        for state in (None, 'SPAWNING', 'RUNNING', 'UNKNOWN'):
            owned = caller.Controller()
            owned.volume = Mock()
            owned.seed = None if state is None else {'phase': state}
            owned.readiness = {'state': 'SUPERVISED_PROJECTED_OWNER_CLOSED', 'volumeMayClose': True}
            with self.assertRaises(caller.AcceptanceRejected):
                owned.close_volume()
            owned.volume.stop.assert_not_called()
            owned.volume.finish.assert_not_called()
            with self.assertRaises(caller.AcceptanceRejected):
                owned.run_readiness({}, {}, object())
            owned.volume.run_retained.assert_not_called()

    def test_readiness_unknown_blocks_stop_even_after_valid_seed(self):
        owned = caller.Controller()
        owned.volume = Mock()
        owned.seed = {'phase': 'COMPLETED'}
        owned.volume.run_retained.side_effect = RuntimeError('owned readiness unknown')
        with self.assertRaises(RuntimeError):
            owned.run_readiness({}, {}, object())
        with self.assertRaises(caller.AcceptanceRejected):
            owned.close_volume()
        owned.volume.stop.assert_not_called()
        owned.volume.finish.assert_not_called()

    def test_normal_finish_only_after_stop_with_both_children_complete(self):
        owned = caller.Controller()
        events = []
        owned.volume = Mock()
        owned.seed = {'phase': 'COMPLETED'}
        owned.readiness = {'state': 'SUPERVISED_PROJECTED_OWNER_CLOSED', 'volumeMayClose': True}
        owned.volume.stop.side_effect = lambda: events.append('stop') or {'state': 'UNMOUNTED'}
        owned.volume.finish.side_effect = lambda: events.append('finish') or {
            'state': 'CLOSED', 'ownedUsersGone': True, 'loopAttachmentGone': True,
            'fenceRemovedAfterCleanup': True, 'leaseReleasedLast': True}
        owned.close_volume()
        self.assertEqual(events, ['stop', 'finish'])

    def test_stop_failure_never_attempts_finish(self):
        owned = caller.Controller()
        owned.volume = Mock()
        owned.seed = {'phase': 'COMPLETED'}
        owned.readiness = {'state': 'SUPERVISED_PROJECTED_OWNER_CLOSED', 'volumeMayClose': True}
        owned.volume.stop.side_effect = RuntimeError('owned stop unknown')
        with self.assertRaises(RuntimeError):
            owned.close_volume()
        owned.volume.finish.assert_not_called()

    def test_seed_spawn_uncertainty_is_recorded_before_popen_and_blocks_close(self):
        owned = caller.Controller()
        owned.volume = SimpleNamespace(stage='RUNNING', _worker_deadline=1000,
                                       worker=SimpleNamespace(pid=321))
        owned.scope_only_worker = Mock()
        owned.seed_contract = Mock(return_value={'namespace': {'inode': 789}})
        owned.modules = SimpleNamespace(capture=SimpleNamespace(PipeCapture=Mock(return_value=object())))
        protocol = SimpleNamespace(encode_contract=Mock(return_value=b'owned\n'))
        manifest = {'files': {caller.CHILD_ENTRY: {'sha256': caller.digest(b'owned')}}}
        def uncertain(*args, **kwargs):
            self.assertEqual(owned.seed['phase'], 'SPAWNING')
            raise OSError('owned spawn uncertainty')
        with patch.object(caller, 'trusted_read', return_value=b'owned'), \
                patch.object(caller.time, 'monotonic', return_value=1), \
                patch.object(caller.os, 'O_CLOEXEC', getattr(caller.os, 'O_CLOEXEC', 0), create=True), \
                patch.object(caller.os, 'open', return_value=8), \
                patch.object(caller.os, 'close') as close, \
                patch.object(caller.subprocess, 'Popen', side_effect=uncertain):
            with self.assertRaises(OSError):
                owned.run_seed(manifest, protocol)
        self.assertEqual(owned.seed['phase'], 'UNKNOWN')
        close.assert_called_once_with(8)
        with self.assertRaises(caller.AcceptanceRejected):
            owned.close_volume()

    def test_formatter_timeout_retains_owned_process_without_kill_or_retry(self):
        owned = caller.Controller()
        process = Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired('owned formatter', 20, b'partial', b'err')
        with patch.object(caller.subprocess, 'Popen', return_value=process) as spawn:
            with self.assertRaises(subprocess.TimeoutExpired):
                owned.format_image()
        self.assertIs(owned.formatter['process'], process)
        self.assertEqual(owned.formatter['phase'], 'UNKNOWN')
        self.assertEqual(owned.formatter['stdout'], b'partial')
        process.kill.assert_not_called()
        process.terminate.assert_not_called()
        self.assertEqual(spawn.call_count, 1)

    def test_unknown_retains_same_controller_and_only_closes_known_stdio(self):
        owned = caller.Controller()
        owned.effects = True
        owned.volume = Mock()
        class StopOwnedWait(BaseException):
            pass
        with patch.object(caller.os, 'close') as close, \
                patch.object(caller.signal, 'pause', create=True, side_effect=StopOwnedWait):
            with self.assertRaises(StopOwnedWait):
                caller.retain_alive(owned)
        self.assertEqual([c.args for c in close.call_args_list], [(0,), (1,), (2,)])
        owned.volume.stop.assert_not_called()
        owned.volume.finish.assert_not_called()

    def test_diagnostic_failure_still_enters_same_controller_retention(self):
        owned = caller.Controller()
        owned.effects = True
        owned.snapshot = Mock(side_effect=RuntimeError('owned diagnostic failure'))
        class Retained(BaseException):
            pass
        with patch.object(caller, 'Controller', return_value=owned), \
                patch.object(caller, 'execute', side_effect=RuntimeError('owned effect failure')), \
                patch.object(caller, 'retain_alive', side_effect=Retained) as retain:
            with self.assertRaises(Retained):
                caller.main(['--manifest-sha256', 'a' * 64])
        retain.assert_called_once_with(owned)


class InputTests(unittest.TestCase):
    def test_input_manifest_forbids_commands_paths_and_extra_files(self):
        good = {'protocol': 'alaz-r155a1-input-v1', 'files': {
            key: {'sha256': 'a' * 64, 'size': 12} for key in caller.INPUT_FILES}}
        self.assertEqual(caller.validate_manifest(good), good)
        for name in ('command', 'destination', 'retry'):
            bad = deepcopy(good)
            bad[name] = '/bin/sh'
            with self.assertRaises(caller.AcceptanceRejected):
                caller.validate_manifest(bad)
        bad = deepcopy(good)
        bad['files']['../../other'] = {'sha256': 'b' * 64, 'size': 12}
        with self.assertRaises(caller.AcceptanceRejected):
            caller.validate_manifest(bad)

    def test_manifest_size_digest_and_bool_are_rejected(self):
        good = {'protocol': 'alaz-r155a1-input-v1', 'files': {
            key: {'sha256': 'a' * 64, 'size': 12} for key in caller.INPUT_FILES}}
        for key, value in (('size', True), ('size', 0), ('size', caller.MAX_SOURCE + 1),
                           ('sha256', 'A' * 64), ('sha256', 'a' * 63)):
            bad = deepcopy(good)
            bad['files'][caller.SEED_ENTRY][key] = value
            with self.assertRaises(caller.AcceptanceRejected):
                caller.validate_manifest(bad)

    def test_projected_exports_do_not_include_inputs_or_image_parent(self):
        view, fs = caller.projection_contract()
        self.assertEqual(view['principalContract'], caller.PRINCIPAL)
        self.assertIn('/etc/mime.types', fs['readonly'])
        self.assertNotIn(str(caller.INPUT), fs['readonly'])
        self.assertEqual(fs['writable'], ['/dev/null', str(caller.SCRATCH)])
        self.assertNotIn('HOME', caller.ENV)


if __name__ == '__main__':
    unittest.main()
