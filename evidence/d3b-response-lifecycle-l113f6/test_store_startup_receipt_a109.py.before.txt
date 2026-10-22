"""A109 real full-confinement product startup proof, not additional executions."""
import hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence/d3b-store-startup-a109'
class StartupReceipt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer=json.loads((E/'native-003-stdout.txt').read_bytes())
        cls.proof=json.loads(cls.outer['nativeStdout'])
        cls.targets=[e for e in cls.proof['events'] if e.get('state')=='RESULT']
    def test_terminal_source_identity_and_real_native_imports(self):
        self.assertEqual(json.loads((E/'native-003-result.json').read_text())['exitCode'],0)
        self.assertEqual((self.outer['unitsExitCode'],self.outer['nativeExitCode']),(0,0))
        self.assertIs(self.outer['sourcesUnchanged'],True)
        self.assertEqual(self.proof['sourceSha256'],json.loads((E/'native-003-intent.json').read_text())['sources'])
        inv=json.loads((ROOT/'evidence/d3b-native-stores-h105e/native-source-inventory.json').read_text())
        for n,h in self.proof['sourceSha256'].items():
            if n.startswith(('packages/','scripts/','tests/')):
                self.assertEqual(hashlib.sha256((ROOT/n).read_bytes()).hexdigest(),h,n)
            elif n.startswith('vendor-native/'):
                self.assertEqual(inv['nativeSources'][n.removeprefix('vendor-native/')]['sha256'],h,n)
            elif n.startswith('dependencies/'):
                self.assertEqual(inv['dependency']['sourceSha256'][n.removeprefix('dependencies/')],h,n)
            else:self.fail(n)
        for t in self.targets:
            for n,h in t['nativeSources'].items():self.assertEqual(self.proof['sourceSha256'][n],h,n)
            for n in ('packages/claw-hermes/gateway_store_startup.py','packages/claw-hermes/gateway_store_preopen.py','vendor-native/hermes_state.py','vendor-native/gateway/platforms/api_server_run_idempotency.py'):
                self.assertIn(n,t['nativeSources'])
    def test_two_mounts_start_product_and_clean_epochs(self):
        self.assertEqual(self.proof['result'],'PASS_SCOPED_NATIVE_STORE_LAYOUT');self.assertIsNone(self.proof['error'])
        self.assertEqual(self.proof['checkCount'],42);self.assertTrue(all(v is True for v in self.proof['checks'].values()))
        self.assertEqual([t['mode'] for t in self.targets],['write','read'])
        self.assertEqual([t['checkCount'] for t in self.targets],[31,36])
        self.assertEqual([t['epoch'] for t in self.targets],[1,2])
        self.assertEqual(len({t['pid'] for t in self.targets}),2)
        for t in self.targets:
            self.assertTrue(all(v is True for v in t['checks'].values()))
            p=t['productStartup'];self.assertEqual(p['state'],'VERIFIED')
            self.assertEqual(p['completedChecks'],['preflight','before_epoch','after_epoch'])
            self.assertEqual(p['epochObserved'],t['epoch']);self.assertTrue(p['storageReady'])
            self.assertEqual(p['recoveryPolicy'],'REFUSE_PENDING_NO_REPLAY');self.assertFalse(p['automaticRecoveryPerformed'])
            for key in ('runtimeAdmissionAuthorized','pairedRecoveryVerified','fullD3BAccepted'):self.assertIs(p[key],False)
            self.assertIs(t['productStorageStartup'],True);self.assertIs(t['realHermesGateway'],False)
    def test_unfinished_work_refuses_before_epoch_and_no_retry(self):
        self.assertIsNone(self.targets[0]['blockedStartup']);t=self.targets[1];b=t['blockedStartup']
        self.assertEqual(b['state'],'FAILED');self.assertEqual(b['epochObserved'],2)
        self.assertIs(b['epochMayHaveAdvanced'],False);self.assertIs(b['storageReady'],False)
        self.assertEqual(b['completedChecks'],['preflight'])
        for k in ('pending_work_blocks_product_start','failed_start_cannot_repeat','refused_start_preserves_epoch_and_started_row'):
            self.assertIs(t['checks'][k],True)
    def test_native_data_and_isolation_preserved(self):
        a,b=self.targets
        for n in ('state.db','runs_idempotency.db'):
            self.assertEqual(a['stores'][n]['inode'],b['stores'][n]['inode'])
            self.assertEqual(a['stores'][n]['rows'],b['stores'][n]['rows'])
            self.assertIs(b['stores'][n]['duplicateRefused'],True)
        for t in self.targets:
            for k in ('final_uid_gid','no_groups_or_caps','nnp_seccomp_after_exec','private_namespace_preserved','other_host_endpoints_denied','host_paths_private_state_hidden','inherited_fd_closed','canary_read_write_denied','active_transaction_blocks_product_close','refused_close_keeps_transaction_and_store'):
                self.assertIs(t['checks'][k],True)
        for mode in ('write','read'):
            for suffix in ('live_confined_user_blocks_stop','image_retained_after_profile_release','detach_before_release','native_other_process_refused'):
                self.assertIs(self.proof['checks'][mode+'_'+suffix],True)
        self.assertIs(self.proof['checks']['exactly_two_authenticated_pings'],True)
        self.assertIs(self.proof['checks']['zero_physical_provider_attempts'],True)
        self.assertIs(self.proof['checks']['broker_private_files_unchanged'],True)
    def test_first_failed_transport_retained_and_own_runtime_clean(self):
        first=json.loads((E/'native-001-stdout.txt').read_bytes());p=json.loads(first['nativeStdout'])
        self.assertEqual(first['nativeExitCode'],1);self.assertEqual(p['error']['reason'],'broker_not_ready')
        second=json.loads((E/'native-002-stdout.txt').read_bytes())
        for n,h in first['sources'].items():self.assertEqual(second['sources'][n],h,n)
        oldhash=hashlib.sha256((E/'startup-before-transaction-guard.py.txt').read_bytes()).hexdigest()
        self.assertEqual(second['sources']['packages/claw-hermes/gateway_store_startup.py'],oldhash)
        self.assertNotEqual(self.proof['sourceSha256']['packages/claw-hermes/gateway_store_startup.py'],oldhash)
        self.assertIn('FAILED (failures=2)',(E/'close-transaction-before.txt').read_text())
        cleanup=json.loads((E/'cleanup.json').read_text());self.assertEqual(cleanup['result'],'CLEAN_OWNED_RUNTIME')
        self.assertTrue(all(v is True for v in cleanup['checks'].values()))
        self.assertFalse(cleanup['otherWorkTouched']);self.assertFalse(cleanup['labTerminated'])

if __name__=='__main__':unittest.main()
