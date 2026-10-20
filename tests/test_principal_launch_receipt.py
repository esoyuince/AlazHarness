"""Verify scoped unprivileged launcher evidence, never two-host-UID acceptance."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
SOURCES = {'packages/claw-hermes/principal_launch.py', 'scripts/run_principal_broker.py',
           'tests/test_principal_launch.py', 'scripts/qa/principal_launch_linux.py',
           'packages/claw-hermes/host_principal.py', 'packages/claw-hermes/linux_netns.py'}
CHECKS = {'kernel_ids_match_current_process', 'current_user_not_accepted_as_controller',
          'gateway_role_cannot_bypass_projection', 'contract_not_read_without_host_root',
          'real_cli_refuses_without_target_exec', 'real_inherited_socket_fd_closed_in_child',
          'real_socket_stdio_refused', 'parent_owns_socket_after_child_cleanup',
          'untrusted_directory_is_not_adopted', 'fixture_bytes_unchanged',
          'owned_temporary_directory_removed', 'observer_identity_and_namespace_unchanged',
          'source_bytes_unchanged'}

class PrincipalLaunchReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads((ROOT/'evidence/d3b-principal-launch-21oct/native-unprivileged-postexec-001.json').read_text(encoding='utf-8'))

    def test_current_source_pins(self):
        r = self.r
        self.assertEqual(set(r['sourceSha256']), SOURCES)
        self.assertEqual(r['sourceSha256'], r['sourceAfterSha256'])
        for name, wanted in r['sourceSha256'].items():
            with self.subTest(source=name):
                data = (ROOT/name).read_bytes()
                if hashlib.sha256(data).hexdigest() != wanted:
                    # Only these unchanged historical checkout files have CRLF
                    # native evidence. New implementation/test bytes are exact LF.
                    self.assertIn(name, {'packages/claw-hermes/host_principal.py',
                                         'packages/claw-hermes/linux_netns.py'})
                    self.assertNotIn(b'\r', data)
                    self.assertEqual(hashlib.sha256(data.replace(b'\n', b'\r\n')).hexdigest(), wanted)

    def test_exact_native_check_set_passed(self):
        self.assertEqual(self.r['result'], 'PASS_SCOPED_UNPRIVILEGED')
        self.assertEqual(set(self.r['checks']), CHECKS)
        self.assertEqual(self.r['checkCount'], len(CHECKS))
        self.assertTrue(all(v is True for v in self.r['checks'].values()))
        self.assertEqual(self.r['errors'], {})

    def test_no_privileged_or_two_uid_claim(self):
        for key in ('privilegedSyscallsExecuted', 'positiveUidTransitionTested',
                    'gatewayBrokerTwoUidTested', 'ipcV2MountTested', 'fullD3BAccepted'):
            self.assertIs(self.r[key], False)
        self.assertEqual(self.r['realModelCalls'], 0)
        self.assertGreater(self.r['observedUid'], 0)
        self.assertGreater(self.r['observedGid'], 0)

if __name__ == '__main__': unittest.main()
