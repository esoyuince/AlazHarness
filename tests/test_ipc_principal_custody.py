"""IPC v2 snapshot consistency, not mount or two-host-UID acceptance."""
import copy
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/claw-hermes'))
import ipc_view as ipc
import host_principal as hp

def fixture():
    fs = {'version': 1, 'enabled': True, 'readonly': ['/usr'],
          'writable': ['/dev/null'], 'protected': ['/owned/key']}
    principal = {'version': 1, 'enabled': True, 'gatewayUid': 1000,
                 'brokerUid': 1001, 'socketGroupGid': 100,
                 'hostUserNamespace': 'user:[4026531837]'}
    value = {'version': 2, 'mode': 'projected_root_principal',
             'root': '/tmp/alaz-ipc-custody',
             'brokerSocket': '/owned/broker/egress.sock',
             'principalContract': principal}
    proof = {'directory': (1, 2, 1001, 100, 0o710),
             'socket': (1, 3, 1001, 100, 0o660)}
    return value, fs, proof, (1, 3, stat.S_IFSOCK, 1001, 100)

class PrincipalSnapshotCustodyTests(unittest.TestCase):
    def test_consistent_proof_does_not_authorize_mount(self):
        value, fs, proof, observed = fixture()
        with (patch.object(hp, 'socket_identity', return_value=proof),
              patch.object(ipc, 'identity', return_value=observed),
              patch.object(ipc.ctypes, 'CDLL') as kernel):
            result = ipc.inspect_principal_socket(value, fs)
        self.assertEqual(result['socketIdentity'], observed)
        self.assertEqual(result['socketPrincipal'], proof)
        self.assertIs(result['mountAuthorized'], False)
        kernel.assert_not_called()

    def test_inode_rebind_between_identity_reads_is_refused(self):
        value, fs, first, observed = fixture()
        after = copy.deepcopy(first)
        after['socket'] = (1, 4, 1001, 100, 0o660)
        with (patch.object(hp, 'socket_identity', side_effect=[first, after]),
              patch.object(ipc, 'identity', return_value=(1, 4, *observed[2:]))):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_changed'):
                ipc.inspect_principal_socket(value, fs)

    def test_rebind_after_middle_read_is_refused(self):
        value, fs, first, observed = fixture()
        after = copy.deepcopy(first)
        after['socket'] = (1, 4, 1001, 100, 0o660)
        with (patch.object(hp, 'socket_identity', side_effect=[first, after]),
              patch.object(ipc, 'identity', return_value=observed)):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_changed'):
                ipc.inspect_principal_socket(value, fs)

    def test_parent_directory_rebind_is_refused(self):
        value, fs, first, observed = fixture()
        after = copy.deepcopy(first)
        after['directory'] = (1, 9, 1001, 100, 0o710)
        with (patch.object(hp, 'socket_identity', side_effect=[first, after]),
              patch.object(ipc, 'identity', return_value=observed)):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_changed'):
                ipc.inspect_principal_socket(value, fs)

    def test_middle_observation_must_match_type_owner_group_and_device(self):
        value, fs, proof, observed = fixture()
        for position, number in [(0, 2), (2, stat.S_IFREG), (3, 1002), (4, 101)]:
            changed = list(observed)
            changed[position] = number
            with (self.subTest(field=position),
                  patch.object(hp, 'socket_identity', return_value=proof),
                  patch.object(ipc, 'identity', return_value=tuple(changed))):
                with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_changed'):
                    ipc.inspect_principal_socket(value, fs)

    def test_disappearance_during_middle_read_is_normalized(self):
        value, fs, proof, _ = fixture()
        with (patch.object(hp, 'socket_identity', return_value=proof),
              patch.object(ipc, 'identity', side_effect=FileNotFoundError('owned fixture'))):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_invalid'):
                ipc.inspect_principal_socket(value, fs)

    def test_mode_denial_on_final_read_is_not_ignored(self):
        value, fs, proof, observed = fixture()
        with (patch.object(hp, 'socket_identity', side_effect=[
                  proof, hp.PrincipalRejected('principal_path_owner_mode')]),
              patch.object(ipc, 'identity', return_value=observed)):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_invalid'):
                ipc.inspect_principal_socket(value, fs)

    def test_io_failure_on_final_read_is_normalized(self):
        value, fs, proof, observed = fixture()
        with (patch.object(hp, 'socket_identity', side_effect=[
                  proof, PermissionError('owned fixture')]),
              patch.object(ipc, 'identity', return_value=observed)):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_invalid'):
                ipc.inspect_principal_socket(value, fs)

    def test_validated_principal_is_not_aliased_to_caller(self):
        value, fs, _, _ = fixture()
        validated, _ = ipc.validate(value, fs)
        value['principalContract']['brokerUid'] = 1002
        self.assertEqual(validated['principalContract']['brokerUid'], 1001)

    def test_validated_principal_mutation_does_not_change_caller(self):
        value, fs, _, _ = fixture()
        validated, _ = ipc.validate(value, fs)
        validated['principalContract']['brokerUid'] = 1002
        self.assertEqual(value['principalContract']['brokerUid'], 1001)

    def test_callback_mutation_cannot_retarget_frozen_principal(self):
        value, fs, proof, observed = fixture()
        inspected = []
        def inspect(principal, path):
            value['principalContract']['brokerUid'] = 1002
            inspected.append(principal['brokerUid'])
            return proof
        with (patch.object(hp, 'socket_identity', side_effect=inspect),
              patch.object(ipc, 'identity', return_value=observed)):
            ipc.inspect_principal_socket(value, fs)
        self.assertTrue(inspected)
        self.assertEqual(set(inspected), {1001})

    def test_returned_proof_is_detached_from_source_object(self):
        value, fs, proof, observed = fixture()
        with (patch.object(hp, 'socket_identity', return_value=proof),
              patch.object(ipc, 'identity', return_value=observed)):
            result = ipc.inspect_principal_socket(value, fs)
        proof['socket'] = (1, 4, 1001, 100, 0o660)
        self.assertEqual(result['socketPrincipal']['socket'][1], 3)

    def test_mutated_same_proof_object_between_reads_is_detected(self):
        value, fs, proof, observed = fixture()
        def middle(path):
            proof['directory'] = (1, 9, 1001, 100, 0o710)
            return observed
        with (patch.object(hp, 'socket_identity', return_value=proof),
              patch.object(ipc, 'identity', side_effect=middle)):
            with self.assertRaisesRegex(ipc.IPCViewRejected, 'ipc_principal_socket_changed'):
                ipc.inspect_principal_socket(value, fs)

    def test_no_silent_retry_after_changed_snapshot(self):
        value, fs, proof, observed = fixture()
        after = copy.deepcopy(proof)
        after['directory'] = (1, 9, 1001, 100, 0o710)
        with (patch.object(hp, 'socket_identity', side_effect=[proof, after]) as inspect,
              patch.object(ipc, 'identity', return_value=observed)):
            with self.assertRaises(ipc.IPCViewRejected):
                ipc.inspect_principal_socket(value, fs)
        self.assertEqual(inspect.call_count, 2)

    def test_successful_inspection_cannot_open_v2_runtime_gate(self):
        value, fs, proof, observed = fixture()
        with (patch.object(hp, 'socket_identity', return_value=proof),
              patch.object(ipc, 'identity', return_value=observed)):
            ipc.inspect_principal_socket(value, fs)
        with self.assertRaisesRegex(ipc.IPCViewRejected, 'runtime_not_integrated'):
            ipc.prepare(value, fs)
        with self.assertRaisesRegex(ipc.IPCViewRejected, 'runtime_not_integrated'):
            ipc.project({'ipc': value, 'filesystem': fs})

if __name__ == '__main__':
    unittest.main(verbosity=2)
