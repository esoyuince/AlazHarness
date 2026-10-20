"""Fresh joint evidence: historical success never certifies current code."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/d3b-joint-21oct-4c21'
CLI='evidence/d3b-principal-startup-20oct/native-cli-joint-4c21.json'
CUSTODY='evidence/d3b-ipc-custody-cf57/joint-native-4c21.json'
DENIAL='evidence/d3b-host-principal-7a19/native-denial-joint-4c21.json'
KERNEL='evidence/d3b-integration-19oct/kernel-joint-4c21.json'
SOURCE_SETS={
    CLI:{'scripts/run_provider_broker.py','packages/claw-hermes/provider_broker.py',
         'packages/claw-hermes/provider_egress.py','packages/claw-hermes/host_principal.py',
         'scripts/qa/native_principal_startup.py'},
    CUSTODY:{'packages/claw-hermes/ipc_view.py','packages/claw-hermes/host_principal.py',
             'scripts/qa/ipc_principal_custody_linux.py','tests/test_ipc_principal_custody.py'},
    DENIAL:{'packages/claw-hermes/host_principal.py','packages/claw-hermes/provider_broker.py',
            'packages/claw-hermes/provider_egress.py','scripts/qa/principal_denial_linux.py'},
    KERNEL:{'packages/claw-hermes/ipc_view.py','packages/claw-hermes/combined_guard.py',
            'packages/claw-hermes/linux_netns.py'},
}
EOL_PAIRS={'packages/claw-hermes/host_principal.py','packages/claw-hermes/provider_egress.py',
           'scripts/qa/principal_denial_linux.py','packages/claw-hermes/combined_guard.py',
           'packages/claw-hermes/linux_netns.py'}

def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))

class JointEvidence(unittest.TestCase):
    def sources(self,name,record):
        self.assertEqual(set(record['sourceSha256']),SOURCE_SETS[name])
        for path,want in record['sourceSha256'].items():
            self.assertRegex(want,r'^[0-9a-f]{64}$')
            raw=(ROOT/path).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=want:
                # Only an exact native-CRLF/Git-LF pair for these unchanged paths.
                self.assertIn(path,EOL_PAIRS)
                self.assertNotIn(b'\r',raw)
                self.assertEqual(hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest(),want,path)

    def checks(self,values,expected):
        self.assertEqual(set(values),set(expected))
        self.assertTrue(all(v is True for v in values.values()))

    def test_current_cli_real_process_and_cleanup(self):
        r=read(CLI);self.sources(CLI,r)
        self.assertEqual(r['result'],'PASS_SCOPED')
        self.assertEqual(r['sourceSha256'],r['sourceAfterSha256'])
        self.assertEqual(r['checkCount'],23)
        self.checks(r['checks'],{
            'ready_matches_owned_pid','legacy_directory_0700','legacy_socket_0600',
            'private_complete_ready_receipt','actual_client_ping','wrong_local_principal_refused',
            'prepared_wrong_broker_refused','prepared_no_socket_or_receipt','prepared_no_provisioning',
            'missing_wrong_broker_refused','missing_no_socket_or_receipt','missing_no_provisioning',
            'owned_process_exited_cleanly','shutdown_matches_owned_pid','socket_removed',
            'no_active_requests','exactly_one_ping','zero_provider_attempts','private_shutdown_receipt',
            'config_unchanged','no_staging_files','temporary_root_removed','source_unchanged'})
        self.assertIsNone(r['errorType']);self.assertIs(r['forcedCleanup'],False)
        self.assertEqual(r['realModelCalls'],0)
        for key in ('realGatewayTested','separateHostUidVerified','ipcV2ProjectionTested','fullD3BAccepted'):
            self.assertIs(r[key],False)

    def test_current_custody_real_socket_mutations(self):
        r=read(CUSTODY);self.sources(CUSTODY,r)
        self.assertEqual(r['result'],'PASS_SCOPED_METADATA')
        self.assertEqual(r['sourceSha256'],r['sourceSha256After'])
        self.assertEqual(r['checkCount'],7)
        self.checks(r['checks'],{'stable_owned_metadata_only','actual_socket_inode_rebind_refused',
            'actual_socket_mode_drift_refused','actual_parent_mode_drift_refused',
            'successful_metadata_cannot_open_mount_gate','owned_temporary_paths_removed',
            'source_bytes_unchanged_during_run'})
        self.assertEqual(r['errors'],{});self.assertGreater(r['observerUid'],0)
        self.assertIs(r['declaredGatewayIsNotAnObservedProcess'],True)
        self.assertEqual(r['realModelCalls'],0)
        for key in ('separateHostUidVerified','gatewayBrokerTransportTested','mountPerformed','fullD3BAccepted'):
            self.assertIs(r[key],False)

    def test_current_principal_denial(self):
        r=read(DENIAL);self.sources(DENIAL,r)
        self.assertEqual(r['result'],'PASS_DENIAL_ONLY');self.assertEqual(r['checkCount'],8)
        self.checks(r['checks'],{'same_uid_budget_file_rejected','same_uid_socket_owner_rejected',
            'same_uid_peer_rejected','symlink_budget_refused','broker_start_fails_closed_same_uid',
            'no_broker_socket_created','no_physical_provider_attempt','owned_temp_removed'})
        self.assertGreater(r['observedUid'],0);self.assertEqual(r['realModelCalls'],0)
        for key in ('separateHostUidVerified','nativeTwoUidGatewayBrokerTested','fullD3BAccepted','mainMerged'):
            self.assertIs(r[key],False)

    def test_current_kernel_not_replaced_by_historical_receipt(self):
        r=read(KERNEL);self.sources(KERNEL,r)
        self.assertEqual((r['result'],r['exitCode']),('PASS',0))
        self.assertIs(r['positiveControlsAllLive'],True)
        self.checks(r['probe']['checks'],{
            'source_read','runtime_write','parent_process_hidden','host_mounts_hidden',
            'old_root_detached','broker_parent_private','secret_unreadable','original_path_blocked',
            'proc_parent_root_blocked','symlink_blocked','explicit_broker_works','host_abstract_blocked',
            'host_tcp_blocked','private_loopback_works','runtime_socket_works','mount_forbidden',
            'chroot_forbidden','namespace_join_forbidden','fd_receive_forbidden','raw_connect_blocked',
            'inherited_secret_closed','inherited_host_socket_closed','exec_child_host_denied',
            'exec_child_broker_allowed'})
        self.assertEqual(set(r['startupRefusals']),{'extra_socket_in_runtime','symlink_broker',
            'wide_broker_permissions','nonempty_anchor','command_mismatch'})
        self.assertTrue(all(v['refused'] is True and v['exitCode']!=0 for v in r['startupRefusals'].values()))
        self.assertEqual(r['ownedServerCounts'],{'broker':2,'blocked':0,'tcp':0,'abstract':0})
        self.assertIs(r['temporaryRootsRemoved'],True);self.assertIs(r['protectedUnchanged'],True)
        self.assertIs(r['completeD3B'],False);self.assertEqual(r['realModelCalls'],0)
        self.assertEqual(r['probe']['guard']['pathnameIpcView']['version'],1)

    def test_four_runs_share_unchanged_source_freeze(self):
        r=json.loads((EVIDENCE/'native-run-summary.json').read_text(encoding='utf-8'))
        self.assertEqual(r['result'],'PASS_SCOPED')
        self.assertIs(r['sourceUnchanged'],True)
        self.assertGreater(r['sourceFileCount'],300)
        self.assertEqual({v['receipt'] for v in r['runs']},set(SOURCE_SETS))
        self.assertTrue(all(v['exitCode']==0 for v in r['runs']))
        self.assertIs(r['fullD3BAccepted'],False)

    def test_missing_source_pin_refuses(self):
        r=read(CLI);r['sourceSha256'].pop('scripts/run_provider_broker.py')
        with self.assertRaises(AssertionError):self.sources(CLI,r)

    def test_changed_source_digest_refuses(self):
        r=read(CLI);r['sourceSha256']['scripts/run_provider_broker.py']='0'*64
        with self.assertRaises(AssertionError):self.sources(CLI,r)

    def test_empty_checks_never_pass(self):
        with self.assertRaises(AssertionError):self.checks({}, {'explicit_broker_works'})

    def test_truthy_integer_is_not_true_check(self):
        with self.assertRaises(AssertionError):self.checks({'observed':1},{'observed'})

if __name__=='__main__':unittest.main()
