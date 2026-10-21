"""Current-source post-exec evidence. Not a positive host UID transition."""
import hashlib
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCES={'packages/claw-hermes/principal_launch.py','packages/claw-hermes/principal_target.py',
         'packages/claw-hermes/host_principal.py','packages/claw-hermes/linux_netns.py',
         'scripts/run_principal_broker_target.py','scripts/run_principal_broker.py',
         'scripts/run_provider_broker.py','scripts/qa/principal_postexec_linux.py',
         'tests/test_principal_target.py','tests/test_principal_postexec_binding.py'}
CHECKS={'actual_target_cli_refused','bounded_diagnostic_no_fallback','owned_exec_child_completed',
        'same_pid_across_exec','same_real_host_identity_across_exec','same_namespace_across_exec',
        'no_new_privs_inherited','seccomp_filter_mode_inherited','known_recvmsg_deny_inherited',
        'target_rejects_wrong_host_uid_after_exec','private_config_not_opened',
        'broker_directory_never_created','fixture_bytes_unchanged','temporary_fixture_removed',
        'parent_identity_privileges_unchanged','source_bytes_unchanged'}

class PostexecReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record=json.loads((ROOT/'evidence/d3b-postexec-21oct/native-postexec-import-r52a.json').read_text(encoding='utf-8'))

    def test_exact_current_source_custody(self):
        r=self.record
        self.assertEqual(set(r['sourceSha256']),SOURCES)
        self.assertEqual(r['sourceSha256'],r['sourceAfterSha256'])
        for name,want in r['sourceSha256'].items():
            with self.subTest(path=name):
                raw=(ROOT/name).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=want:
                    # Only unchanged pre-existing Windows checkout text files.
                    self.assertIn(name,{'packages/claw-hermes/host_principal.py',
                                        'packages/claw-hermes/linux_netns.py',
                                        'scripts/run_provider_broker.py'})
                    self.assertNotIn(b'\r',raw)
                    self.assertEqual(hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest(),want)

    def test_all_actual_exec_refusal_checks_passed(self):
        r=self.record
        self.assertEqual(r['result'],'PASS_SCOPED_POSTEXEC')
        self.assertEqual(set(r['checks']),CHECKS)
        self.assertEqual(r['checkCount'],len(CHECKS))
        self.assertTrue(all(v is True for v in r['checks'].values()))
        self.assertIsNone(r['errorType'])
        self.assertEqual(r['details']['recvmsgErrno'],1)
        self.assertGreater(r['details']['pid'],0)
        self.assertEqual(r['details']['uid'],r['observerUid'])

    def test_no_broader_positive_acceptance(self):
        r=self.record
        for key in ('positiveUidTransitionTested','brokerStarted','gatewayBrokerTwoUidTested',
                    'ipcV2MountTested','fullD3BAccepted'):
            self.assertIs(r[key],False)
        self.assertEqual(r['realModelCalls'],0)
        self.assertGreater(r['observerUid'],0)

if __name__=='__main__':unittest.main()
